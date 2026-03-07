"""Evaluative reinforcement for species heads.

Allows users to submit (lat, lon, present/absent) feedback that nudges a
cloned copy of the original species head.  The original weights are never
modified.  Reinforced heads are auto-persisted to disk so they survive
server restarts.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from threading import Lock
from typing import Any

import torch

from util import inference as _inf

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_reinforced_heads: dict[int, torch.nn.Module] = {}
_reinforcement_feedback: dict[int, list[dict[str, Any]]] = {}
_reinforcement_lock = Lock()
_reinforced_dir: Path | None = None

DEFAULT_LR = 0.05
DEFAULT_STEPS = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reinforced_head_path(species_key: int) -> Path | None:
    """Return the on-disk path for a species' reinforced head, or None."""
    if _reinforced_dir is None:
        return None
    return _reinforced_dir / f"reinforced_{species_key}.pt"


def default_reinforced_head_path(species_key: int) -> Path | None:
    """Public accessor: return the auto-persist path for a species, or None."""
    return _reinforced_head_path(species_key)


def set_reinforced_dir(path: Path) -> None:
    """Set the directory used for auto-persistence of reinforced heads."""
    global _reinforced_dir  # noqa: PLW0603
    _reinforced_dir = path


def _embed_point(lat: float, lon: float) -> torch.Tensor | None:
    """Return a single-point embedding tensor for ``(lat, lon)``, or ``None``.

    The returned tensor keeps a batch dimension, i.e. shape ``(1, embed_dim)``.
    We explicitly add this with ``unsqueeze(0)`` because the encoder expects a
    batched input ``(batch, input_dim)`` even for one point.
    """
    if _inf._encoder is None:
        return None
    cell_id = _inf._bin_id(lat, lon, _inf._cell_size_deg)
    cell = _inf._cell_table.get(cell_id)
    if cell is None:
        cell = _inf._sample_point_features(lat, lon)
    if cell is None:
        return None
    # Keep a batch axis for encoder/head calls and later concatenation across
    # many feedback points.
    features = _inf._coerce_model_input(cell["features"], cell.get("mask")).unsqueeze(0).to(_inf._device)
    with torch.no_grad():
        return _inf._encoder(features)  # (1, embed_dim)


def _set_trainable(module: torch.nn.Module, trainable: bool) -> None:
    """Enable or disable grads for all parameters in a module."""
    for param in module.parameters():
        param.requires_grad_(trainable)


def _feedback_public_entry(feedback: dict[str, Any]) -> dict[str, Any]:
    """Return a feedback entry safe for API responses/checkpoints."""
    return {
        "lat": feedback["lat"],
        "lon": feedback["lon"],
        "present": feedback["present"],
    }


def _serialize_feedback(feedback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialize feedback entries without internal tensors."""
    return [_feedback_public_entry(item) for item in feedback]


def _validate_reinforcement_params(lr: float, steps: int) -> None:
    """Validate optimization hyperparameters for reinforcement updates."""
    if not isinstance(lr, (int, float)) or lr <= 0:
        raise ValueError("lr must be a positive number")
    if not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be an integer >= 1")


def _read_reinforced_checkpoint(path: str | Path) -> dict[str, Any]:
    """Read and return the serialized reinforced checkpoint payload."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Reinforced head file not found: {path}")
    saved = torch.load(str(p), map_location="cpu", weights_only=False)
    if not isinstance(saved, dict):
        raise ValueError(f"Invalid reinforced head file format: {path}")
    return saved


def _apply_loaded_reinforced_head(
    requested_species_key: int,
    path: str | Path,
    saved: dict[str, Any],
) -> dict[str, Any]:
    """Apply a loaded checkpoint payload to in-memory reinforcement state."""
    if _inf._encoder is None:
        raise RuntimeError("Inference bundle not loaded.")
    if _inf.SpeciesHead is None:
        raise RuntimeError("Model classes unavailable.")

    actual_key = int(saved.get("species_key", requested_species_key))
    if actual_key not in _inf._heads:
        raise KeyError(f"Species {actual_key} not in loaded bundle.")

    p = Path(path)
    if actual_key != requested_species_key:
        LOGGER.info(
            "Reinforced head file %s contains species %d (requested %d); using file's species key.",
            p.name,
            actual_key,
            requested_species_key,
        )

    embed_dim = _inf._heads[actual_key].linear.in_features  # type: ignore[union-attr]
    head = _inf.SpeciesHead(embed_dim=embed_dim).to(_inf._device)
    head.load_state_dict(saved["head_state_dict"])
    head.eval()
    _set_trainable(head, False)

    # Re-embed saved feedback so incremental reinforcement works.
    fb_entries: list[dict[str, Any]] = []
    for fb in saved.get("feedback", []):
        lat = fb.get("lat")
        lon = fb.get("lon")
        present = fb.get("present")
        if lat is None or lon is None or present is None:
            continue
        emb = _embed_point(lat, lon)
        fb_entries.append({
            "lat": lat,
            "lon": lon,
            "present": bool(present),
            "_embedding": emb.detach().cpu() if emb is not None else None,
        })

    with _reinforcement_lock:
        _reinforced_heads[actual_key] = head
        _reinforcement_feedback[actual_key] = fb_entries

    return {
        "species_key": actual_key,
        "feedback_count": len(fb_entries),
    }


def _retrain_reinforced_head(
    species_key: int,
    feedback: list[dict[str, Any]],
    *,
    lr: float = DEFAULT_LR,
    steps: int = DEFAULT_STEPS,
) -> torch.nn.Module:
    """Clone the original head and fine-tune it on all accumulated feedback.

    Always starts from the original head so that repeated calls converge
    to the same result given the same feedback set.
    """
    if _inf.SpeciesHead is None:
        raise RuntimeError("Model classes unavailable.")
    original = _inf._heads[species_key]

    head = copy.deepcopy(original)
    head.to(_inf._device)
    head.train()
    _set_trainable(head, True)

    embeddings: list[torch.Tensor] = []
    labels: list[float] = []
    for fb in feedback:
        emb = fb.get("_embedding")
        if emb is None:
            continue
        embeddings.append(emb.to(_inf._device))
        labels.append(1.0 if fb["present"] else 0.0)

    if not embeddings:
        head.eval()
        _set_trainable(head, False)
        return head

    emb_batch = torch.cat(embeddings, dim=0)  # (N, embed_dim)
    label_batch = torch.tensor(labels, dtype=torch.float32, device=_inf._device)

    # Compensate for imbalanced feedback when both classes are present.
    # For BCE-with-logits, pos_weight = n_neg / n_pos increases the loss
    # contribution of positive samples when positives are rare.
    pos_count = int(label_batch.sum().item())
    total_count = int(label_batch.numel())
    neg_count = total_count - pos_count
    pos_weight: torch.Tensor | None = None
    if pos_count > 0 and neg_count > 0:
        pos_weight = torch.tensor(neg_count / pos_count, dtype=torch.float32, device=_inf._device)

    # Use plain SGD here intentionally: heads are small, feedback batches are tiny,
    # and we want a simple, stable fine-tuning step without introducing adaptive
    # optimizer state or additional configuration complexity.
    optimizer = torch.optim.SGD(head.parameters(), lr=lr)
    with torch.enable_grad():
        for _ in range(steps):
            optimizer.zero_grad()
            logits = head(emb_batch)  # (N,)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(
                logits,
                label_batch,
                pos_weight=pos_weight,
            )
            loss.backward()
            optimizer.step()

    head.eval()
    _set_trainable(head, False)
    return head


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def reinforce_head(
    species_key: int,
    lat: float,
    lon: float,
    present: bool,
    *,
    lr: float = DEFAULT_LR,
    steps: int = DEFAULT_STEPS,
) -> dict[str, Any]:
    """Submit one evaluative feedback point for a species head.

    Clones the original head (or re-trains from scratch on all accumulated
    feedback) and stores the reinforced copy in memory.

    Returns a summary dict with the new feedback count and current score
    at the feedback point for both original and reinforced heads.
    """
    if _inf._encoder is None:
        raise RuntimeError("Inference bundle not loaded. Call load_bundle() first.")
    if species_key not in _inf._heads:
        raise KeyError(f"Species {species_key} not in loaded bundle.")
    _validate_reinforcement_params(lr, steps)

    embedding = _embed_point(lat, lon)
    if embedding is None:
        raise ValueError(f"Cannot compute features for ({lat}, {lon}); coordinate may be outside coverage.")

    fb_entry: dict[str, Any] = {
        "lat": lat,
        "lon": lon,
        "present": present,
        "_embedding": embedding.detach().cpu(),
    }

    with _reinforcement_lock:
        fb_list = _reinforcement_feedback.setdefault(species_key, [])
        fb_list.append(fb_entry)
        reinforced = _retrain_reinforced_head(species_key, fb_list, lr=lr, steps=steps)
        _reinforced_heads[species_key] = reinforced

    # Auto-save to disk so feedback survives restarts.
    auto_path = _reinforced_head_path(species_key)
    if auto_path is not None:
        try:
            save_reinforced_head(species_key, auto_path)
        except Exception:
            LOGGER.warning("Auto-save failed for reinforced head %d", species_key, exc_info=True)

    with torch.no_grad():
        emb_dev = embedding.to(_inf._device)
        orig_logit = float(_inf._heads[species_key](emb_dev).item())
        reinf_logit = float(reinforced(emb_dev).item())

    return {
        "species_key": species_key,
        "feedback_count": len(_reinforcement_feedback.get(species_key, [])),
        "point": {"lat": lat, "lon": lon, "present": present},
        "original_score": round(_inf._sigmoid(orig_logit), 6),
        "reinforced_score": round(_inf._sigmoid(reinf_logit), 6),
    }


def list_reinforced_species() -> list[dict[str, Any]]:
    """Return metadata for all species that have reinforced heads."""
    results: list[dict[str, Any]] = []
    with _reinforcement_lock:
        for sp_key in sorted(_reinforced_heads.keys()):
            fb_count = len(_reinforcement_feedback.get(sp_key, []))
            results.append({"species_key": sp_key, "feedback_count": fb_count})
    return results


def get_reinforcement_feedback(species_key: int) -> list[dict[str, Any]]:
    """Return the feedback log for a species (without internal tensors)."""
    with _reinforcement_lock:
        fb_list = _reinforcement_feedback.get(species_key, [])
        return _serialize_feedback(fb_list)


def clear_reinforced_head(species_key: int) -> bool:
    """Remove the reinforced head and feedback for a species. Returns True if it existed."""
    with _reinforcement_lock:
        had = species_key in _reinforced_heads
        _reinforced_heads.pop(species_key, None)
        _reinforcement_feedback.pop(species_key, None)
    # Remove the persisted file too.
    auto_path = _reinforced_head_path(species_key)
    if auto_path is not None and auto_path.exists():
        try:
            auto_path.unlink()
        except OSError:
            LOGGER.warning("Failed to remove reinforced head file %s", auto_path, exc_info=True)
    return had


def save_reinforced_head(species_key: int, path: str | Path) -> Path:
    """Save a reinforced head's state dict and feedback log to disk."""
    with _reinforcement_lock:
        if species_key not in _reinforced_heads:
            raise KeyError(f"No reinforced head for species {species_key}.")
        head = _reinforced_heads[species_key]
        fb_list = _reinforcement_feedback.get(species_key, [])
        serializable_fb = _serialize_feedback(fb_list)

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "species_key": species_key,
            "head_state_dict": head.state_dict(),
            "feedback": serializable_fb,
        },
        str(out),
    )
    return out


def load_reinforced_head(species_key: int, path: str | Path) -> dict[str, Any]:
    """Load a previously saved reinforced head from disk.

    The species key embedded in the file is treated as the source of truth.
    If it differs from *species_key* the file's key is used (and the caller
    is informed via the return dict).

    Re-embeds the saved feedback points so future reinforcement calls can
    build on the existing feedback set.
    """
    saved = _read_reinforced_checkpoint(path)
    return _apply_loaded_reinforced_head(species_key, path, saved)


def get_reinforced_head(species_key: int) -> torch.nn.Module:
    """Return the reinforced head for a species, or raise KeyError."""
    with _reinforcement_lock:
        head = _reinforced_heads.get(species_key)
    if head is None:
        raise KeyError(f"No reinforced head for species {species_key}. Submit feedback via reinforce_head() first.")
    return head


def autoload_reinforced_heads() -> None:
    """Scan the reinforced_heads directory and load any saved heads."""
    if _reinforced_dir is None or not _reinforced_dir.is_dir():
        return
    count = 0
    for pt_file in sorted(_reinforced_dir.glob("reinforced_*.pt")):
        # Read the species key from inside the file rather than trusting
        # the filename, which may be stale after bundle switches or edits.
        try:
            saved = _read_reinforced_checkpoint(pt_file)
            sp_key = int(saved["species_key"])
        except Exception:
            LOGGER.warning("Cannot read reinforced head file %s, skipping", pt_file.name, exc_info=True)
            continue
        if sp_key not in _inf._heads:
            LOGGER.debug("Skipping reinforced head %s: species %d not in bundle", pt_file.name, sp_key)
            continue
        try:
            _apply_loaded_reinforced_head(sp_key, pt_file, saved)
            count += 1
        except Exception:
            LOGGER.warning("Failed to load reinforced head %s", pt_file.name, exc_info=True)
    if count:
        LOGGER.info("Auto-loaded %d reinforced head(s) from %s", count, _reinforced_dir)
