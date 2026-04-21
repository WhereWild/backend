from __future__ import annotations

import copy
import hashlib
from threading import Lock
from typing import Any

import torch

from util import inference as _inf

DEFAULT_LR = 0.05
DEFAULT_STEPS = 5
DEFAULT_BASE_HEAD_REGULARIZATION = 0.01
DEFAULT_REINFORCED_LOGIT_DELTA_LIMIT = 1.75
MIN_FEEDBACK_TO_ACTIVATE = 5

_reinforced_heads: dict[tuple[str, int], torch.nn.Module] = {}
_reinforcement_feedback: dict[tuple[str, int], list[dict[str, Any]]] = {}
_activation_thresholds: dict[tuple[str, int], int] = {}
_reinforcement_tokens: dict[tuple[str, int], str] = {}
_reinforcement_lock = Lock()


def _normalize_client_key(client_key: str | None) -> str:
    normalized = (client_key or "").strip()
    if not normalized:
        raise ValueError("client_key is required.")
    return normalized


def _state_key(client_key: str | None, species_key: int) -> tuple[str, int]:
    return (_normalize_client_key(client_key), species_key)


def _set_trainable(module: torch.nn.Module, trainable: bool) -> None:
    for param in module.parameters():
        param.requires_grad_(trainable)


def _feedback_entry_public(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "lat": float(entry["lat"]),
        "lon": float(entry["lon"]),
        "present": bool(entry["present"]),
    }


def _feedback_count(client_key: str | None, species_key: int) -> int:
    return len(_reinforcement_feedback.get(_state_key(client_key, species_key), []))


def get_activation_threshold(species_key: int, client_key: str | None = None) -> int:
    return _activation_thresholds.get(_state_key(client_key, species_key), MIN_FEEDBACK_TO_ACTIVATE)


def is_reinforced_head_active(species_key: int, client_key: str | None = None) -> bool:
    state_key = _state_key(client_key, species_key)
    return state_key in _reinforced_heads and _feedback_count(client_key, species_key) >= get_activation_threshold(
        species_key,
        client_key,
    )


def reinforced_cache_token(species_key: int, client_key: str | None = None) -> str:
    state_key = _state_key(client_key, species_key)
    feedback_count = len(_reinforcement_feedback.get(state_key, []))
    active_token = "active" if is_reinforced_head_active(species_key, client_key) else "inactive"
    threshold = get_activation_threshold(species_key, client_key)
    normalized_client_key = _normalize_client_key(client_key)
    token = _reinforcement_tokens.get(state_key, "none")
    return f"{normalized_client_key}:{active_token}:{feedback_count}:{threshold}:{token}"


def normalize_reinforced_logit(
    original_logit: torch.Tensor,
    reinforced_logit: torch.Tensor,
    *,
    delta_limit: float = DEFAULT_REINFORCED_LOGIT_DELTA_LIMIT,
) -> torch.Tensor:
    if delta_limit <= 0:
        return reinforced_logit
    delta = reinforced_logit - original_logit
    limited_delta = delta_limit * torch.tanh(delta / delta_limit)
    return original_logit + limited_delta


def _serialize_feedback_signature(feedback: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for entry in feedback:
        parts.append(f"{entry['lat']:.6f}:{entry['lon']:.6f}:{1 if entry['present'] else 0}")
    return "|".join(parts)


def _serialize_head_signature(head: torch.nn.Module) -> str:
    parts: list[str] = []
    for parameter in head.parameters():
        flat = parameter.detach().cpu().reshape(-1).tolist()
        parts.append(",".join(f"{float(value):.8f}" for value in flat))
    return "|".join(parts)


def _build_reinforcement_token(
    state_key: tuple[str, int],
    feedback: list[dict[str, Any]],
    head: torch.nn.Module,
) -> str:
    client_key, species_key = state_key
    payload = "::".join(
        [
            client_key,
            str(species_key),
            str(get_activation_threshold(species_key, client_key)),
            _serialize_feedback_signature(feedback),
            _serialize_head_signature(head),
        ]
    )
    return hashlib.md5(payload.encode("utf-8")).hexdigest()[:16]


def _embed_point(lat: float, lon: float) -> torch.Tensor | None:
    if _inf._encoder is None:
        raise RuntimeError("Inference bundle not loaded.")
    if _inf._device is None:
        raise RuntimeError("Inference device unavailable.")

    valid_indices, feature_tensor, _ = _inf._prepare_feature_batch_for_coords(
        [(lat, lon)],
        resolution_hint=_inf._cell_size_deg,
        include_source=False,
        feature_mode="prefer_cell_table",
    )
    if feature_tensor is None or feature_tensor.numel() == 0 or not valid_indices:
        return None

    if feature_tensor.device != _inf._device:
        feature_tensor = feature_tensor.to(_inf._device)
    with torch.no_grad():
        embedding = _inf._encoder(feature_tensor[:1])
    return embedding.detach().cpu()


def _retrain_reinforced_head(
    species_key: int,
    feedback: list[dict[str, Any]],
    current_head: torch.nn.Module | None = None,
    *,
    lr: float = DEFAULT_LR,
    steps: int = DEFAULT_STEPS,
    base_head_regularization: float = DEFAULT_BASE_HEAD_REGULARIZATION,
) -> torch.nn.Module:
    """Fine-tune a private species-head clone on accumulated user feedback.

    This routine keeps the shared encoder frozen, retrieves or creates a
    private per-species head clone, and continues SGD updates on that clone
    using all accumulated binary corrections with inverse-frequency weighting.
    """
    if _inf._device is None:
        raise RuntimeError("Inference device unavailable.")
    if species_key not in _inf._heads:
        raise KeyError(f"Species {species_key} not in loaded bundle.")

    original_head = _inf._heads[species_key]
    starting_head = current_head if current_head is not None else original_head
    head = copy.deepcopy(starting_head).to(_inf._device)
    head.train()
    _set_trainable(head, True)

    reference_head = copy.deepcopy(original_head).to(_inf._device)
    reference_head.eval()
    _set_trainable(reference_head, False)
    reference_parameters = [parameter.detach().clone() for parameter in reference_head.parameters()]

    embeddings: list[torch.Tensor] = []
    labels: list[float] = []
    for item in feedback:
        embedding = item.get("_embedding")
        if embedding is None:
            continue
        embeddings.append(embedding.to(_inf._device))
        labels.append(1.0 if item["present"] else 0.0)

    if not embeddings:
        head.eval()
        _set_trainable(head, False)
        return head

    embedding_batch = torch.cat(embeddings, dim=0)
    label_batch = torch.tensor(labels, dtype=torch.float32, device=_inf._device)

    pos_count = int(label_batch.sum().item())
    neg_count = int(label_batch.numel()) - pos_count
    sample_weight_batch = torch.ones_like(label_batch)
    if pos_count > 0 and neg_count > 0:
        total_count = pos_count + neg_count
        pos_weight = total_count / (2.0 * pos_count)
        neg_weight = total_count / (2.0 * neg_count)
        sample_weight_batch = torch.where(label_batch > 0.5, pos_weight, neg_weight)

    optimizer = torch.optim.SGD(head.parameters(), lr=lr)
    with torch.enable_grad():
        for _ in range(steps):
            optimizer.zero_grad()
            logits = head(embedding_batch)
            prediction_loss = torch.nn.functional.binary_cross_entropy_with_logits(
                logits,
                label_batch,
                reduction="none",
            )
            prediction_loss = (prediction_loss * sample_weight_batch).mean()

            regularization_loss = torch.zeros((), device=_inf._device)
            if base_head_regularization > 0:
                for parameter, reference_parameter in zip(
                    head.parameters(),
                    reference_parameters,
                    strict=True,
                ):
                    regularization_loss = regularization_loss + torch.sum((parameter - reference_parameter) ** 2)

            loss = prediction_loss + (base_head_regularization * regularization_loss)
            loss.backward()
            optimizer.step()

    head.eval()
    _set_trainable(head, False)
    return head


def get_reinforced_head(species_key: int, client_key: str | None = None) -> torch.nn.Module | None:
    state_key = _state_key(client_key, species_key)
    if not is_reinforced_head_active(species_key, client_key):
        return None
    return _reinforced_heads.get(state_key)


def reinforce_head(
    client_key: str | None,
    species_key: int,
    lat: float,
    lon: float,
    present: bool,
    *,
    lr: float = DEFAULT_LR,
    steps: int = DEFAULT_STEPS,
    activation_threshold: int | None = None,
) -> dict[str, Any]:
    normalized_client_key = _normalize_client_key(client_key)
    if _inf._encoder is None:
        raise RuntimeError("Inference bundle not loaded.")
    if species_key not in _inf._heads:
        raise KeyError(f"Species {species_key} not in loaded bundle.")
    if lr <= 0:
        raise ValueError("lr must be positive.")
    if steps < 1:
        raise ValueError("steps must be >= 1.")
    if activation_threshold is not None and activation_threshold < 1:
        raise ValueError("activation_threshold must be >= 1.")

    embedding = _embed_point(lat, lon)
    if embedding is None:
        raise ValueError(f"Cannot resolve model-ready features for ({lat}, {lon}).")

    feedback_entry = {
        "lat": float(lat),
        "lon": float(lon),
        "present": bool(present),
        "_embedding": embedding,
    }

    with _reinforcement_lock:
        state_key = _state_key(normalized_client_key, species_key)
        if activation_threshold is not None:
            _activation_thresholds[state_key] = activation_threshold
        threshold = get_activation_threshold(species_key, normalized_client_key)
        feedback = _reinforcement_feedback.setdefault(state_key, [])
        feedback.append(feedback_entry)
        reinforced_head = _retrain_reinforced_head(
            species_key,
            feedback,
            current_head=_reinforced_heads.get(state_key),
            lr=lr,
            steps=steps,
        )
        _reinforced_heads[state_key] = reinforced_head
        feedback_count = len(feedback)
        _reinforcement_tokens[state_key] = _build_reinforcement_token(
            state_key,
            feedback,
            reinforced_head,
        )

    with torch.no_grad():
        embedding_device = embedding.to(_inf._device)
        original_logit = float(_inf._heads[species_key](embedding_device).item())
        raw_reinforced_logit = reinforced_head(embedding_device)
        reinforced_logit = float(
            normalize_reinforced_logit(
                torch.tensor(original_logit, device=_inf._device),
                raw_reinforced_logit,
            ).item()
        )

    return {
        "species_key": species_key,
        "feedback_count": feedback_count,
        "point": {"lat": float(lat), "lon": float(lon), "present": bool(present)},
        "original_score": round(_inf._sigmoid(original_logit), 6),
        "reinforced_score": round(_inf._sigmoid(reinforced_logit), 6),
        "active": feedback_count >= threshold,
        "activation_threshold": threshold,
    }


def list_reinforced_species() -> list[dict[str, Any]]:
    with _reinforcement_lock:
        return [
            {
                "species_key": species_key,
                "feedback_count": len(feedback),
                "active": len(feedback) >= get_activation_threshold(species_key, client_key),
                "activation_threshold": get_activation_threshold(species_key, client_key),
            }
            for (client_key, species_key), feedback in sorted(_reinforcement_feedback.items())
            if feedback
        ]


def list_reinforced_species_for_client(client_key: str | None) -> list[dict[str, Any]]:
    normalized_client_key = _normalize_client_key(client_key)
    with _reinforcement_lock:
        return [
            {
                "species_key": species_key,
                "feedback_count": len(feedback),
                "active": len(feedback) >= get_activation_threshold(species_key, normalized_client_key),
                "activation_threshold": get_activation_threshold(species_key, normalized_client_key),
            }
            for (stored_client_key, species_key), feedback in sorted(_reinforcement_feedback.items())
            if feedback and stored_client_key == normalized_client_key
        ]


def get_reinforcement_feedback(species_key: int, client_key: str | None = None) -> list[dict[str, Any]]:
    with _reinforcement_lock:
        feedback = list(_reinforcement_feedback.get(_state_key(client_key, species_key), []))
    return [_feedback_entry_public(entry) for entry in feedback]


def clear_reinforced_head(species_key: int, client_key: str | None = None) -> bool:
    state_key = _state_key(client_key, species_key)
    with _reinforcement_lock:
        existed = (
            state_key in _reinforced_heads
            or state_key in _reinforcement_feedback
            or state_key in _activation_thresholds
            or state_key in _reinforcement_tokens
        )
        _reinforced_heads.pop(state_key, None)
        _reinforcement_feedback.pop(state_key, None)
        _activation_thresholds.pop(state_key, None)
        _reinforcement_tokens.pop(state_key, None)
    return existed
