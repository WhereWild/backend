"""Stage C: Per-species PU head training (model card Section 4, Stage C)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import numpy as np
import torch
from numpy.typing import DTypeLike

try:
    from ._compat import import_local_symbol
except ImportError:
    from _compat import import_local_symbol

StreamingTrainingDataset = import_local_symbol("data", "StreamingTrainingDataset")
nnpu_loss = import_local_symbol("losses", "nnpu_loss")
SharedEncoder = import_local_symbol("model", "SharedEncoder")
SpeciesHead = import_local_symbol("model", "SpeciesHead")


class _FeatureDataset(Protocol):
    features: torch.Tensor

    def __len__(self) -> int: ...


class _StreamingSplitDataset(Protocol):
    row_count: int

    def _iter_record_batches(self) -> Iterator[dict[str, torch.Tensor]]: ...


HEARTBEAT_INTERVAL_SPECIES = 50


def compute_embeddings(
    encoder: torch.nn.Module,
    dataset: _FeatureDataset,
    device: torch.device,
    batch_size: int = 8192,
) -> torch.Tensor:
    """Compute encoder embeddings for entire dataset with frozen encoder."""
    encoder.eval()
    embeddings = []
    with torch.no_grad():
        for start in range(0, len(dataset), batch_size):
            end = min(start + batch_size, len(dataset))
            batch_features = dataset.features[start:end].to(device)
            z = encoder(batch_features)
            embeddings.append(z.cpu())
    return torch.cat(embeddings, dim=0)


def _materialize_split_embeddings(
    encoder: torch.nn.Module,
    split_ds: _StreamingSplitDataset,
    *,
    split_name: str,
    device: torch.device,
    batch_size: int,
    embed_dim: int,
    embedding_dtype: torch.dtype = torch.float16,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Stream one split and materialize embeddings + metadata tensors.

    This avoids loading full feature tables into RAM. Only the final embedding
    matrix and metadata vectors are kept in memory.
    """
    n_rows = int(split_ds.row_count)
    if n_rows <= 0:
        return (
            torch.empty((0, embed_dim), dtype=embedding_dtype),
            torch.empty((0,), dtype=torch.int64),
            torch.empty((0,), dtype=torch.int8),
            torch.empty((0,), dtype=torch.float32),
        )

    embeddings = torch.empty((n_rows, embed_dim), dtype=embedding_dtype)
    species = torch.empty((n_rows,), dtype=torch.int64)
    labels = torch.empty((n_rows,), dtype=torch.int8)
    weights = torch.empty((n_rows,), dtype=torch.float32)

    cursor = 0
    encoder.eval()
    with torch.no_grad():
        for rb in split_ds._iter_record_batches():
            rb_rows = int(rb["features"].shape[0])
            if rb_rows <= 0:
                continue

            rb_features = rb["features"]
            rb_embeddings = torch.empty((rb_rows, embed_dim), dtype=embedding_dtype)
            for start in range(0, rb_rows, batch_size):
                end = min(start + batch_size, rb_rows)
                batch_features = rb_features[start:end].to(device)
                z = encoder(batch_features)
                rb_embeddings[start:end] = z.to("cpu", dtype=embedding_dtype)

            next_cursor = cursor + rb_rows
            embeddings[cursor:next_cursor] = rb_embeddings
            species[cursor:next_cursor] = rb["species_key"].to(dtype=torch.int64)
            labels[cursor:next_cursor] = rb["presence_label"].to(dtype=torch.int8)
            weights[cursor:next_cursor] = rb["sample_weight"].to(dtype=torch.float32)
            cursor = next_cursor

    if cursor != n_rows:
        embeddings = embeddings[:cursor]
        species = species[:cursor]
        labels = labels[:cursor]
        weights = weights[:cursor]
    print(f"Materialized {split_name} embeddings: {cursor:,} rows | dtype={embedding_dtype}")
    return embeddings, species, labels, weights


def _materialize_split_embeddings_memmap(
    encoder: torch.nn.Module,
    split_ds: _StreamingSplitDataset,
    *,
    split_name: str,
    device: torch.device,
    batch_size: int,
    embed_dim: int,
    cache_dir: Path,
    embedding_dtype: DTypeLike = np.float16,
) -> tuple[np.memmap, np.memmap, np.memmap, np.memmap]:
    """Stream one split into on-disk memmaps (bounded RAM footprint)."""
    n_rows = int(split_ds.row_count)
    _torch_emb_dtype = torch.from_numpy(np.empty(0, dtype=embedding_dtype)).dtype
    cache_dir.mkdir(parents=True, exist_ok=True)

    emb_path = cache_dir / f"{split_name}_embeddings.f16.mmap"
    species_path = cache_dir / f"{split_name}_species.i64.mmap"
    labels_path = cache_dir / f"{split_name}_labels.i8.mmap"
    weights_path = cache_dir / f"{split_name}_weights.f32.mmap"

    embeddings = np.memmap(emb_path, mode="w+", dtype=embedding_dtype, shape=(n_rows, embed_dim))
    species = np.memmap(species_path, mode="w+", dtype=np.int64, shape=(n_rows,))
    labels = np.memmap(labels_path, mode="w+", dtype=np.int8, shape=(n_rows,))
    weights = np.memmap(weights_path, mode="w+", dtype=np.float32, shape=(n_rows,))

    cursor = 0
    encoder.eval()
    with torch.no_grad():
        for rb in split_ds._iter_record_batches():
            rb_rows = int(rb["features"].shape[0])
            if rb_rows <= 0:
                continue

            rb_features = rb["features"]
            rb_embeddings = np.empty((rb_rows, embed_dim), dtype=embedding_dtype)
            for start in range(0, rb_rows, batch_size):
                end = min(start + batch_size, rb_rows)
                batch_features = rb_features[start:end].to(device)
                z = encoder(batch_features)
                rb_embeddings[start:end] = z.to("cpu", dtype=_torch_emb_dtype).numpy()

            next_cursor = cursor + rb_rows
            embeddings[cursor:next_cursor] = rb_embeddings
            species[cursor:next_cursor] = rb["species_key"].to(dtype=torch.int64).numpy()
            labels[cursor:next_cursor] = rb["presence_label"].to(dtype=torch.int8).numpy()
            weights[cursor:next_cursor] = rb["sample_weight"].to(dtype=torch.float32).numpy()
            cursor = next_cursor

    embeddings.flush()
    species.flush()
    labels.flush()
    weights.flush()
    print(f"Materialized {split_name} embeddings on disk: {cursor:,} rows | dir={cache_dir}")
    return embeddings, species, labels, weights


def estimate_prior(
    n_species_positives: int,
    n_species_total_rows: int,
    global_positive_rate: float,
    smoothing_strength: float = 50.0,
    min_prior: float = 1e-4,
    max_prior: float = 0.5,
) -> float:
    """Estimate class prior pi_s for one species.

    Uses an empirical-Bayes shrinkage estimate:

        raw_s = n_pos_s / n_total_s
        pi_s = (n_pos_s + smoothing_strength * global_positive_rate)
               / (n_total_s + smoothing_strength)

    This keeps species-specific signal while stabilizing rare-species priors.
    The estimate is computed once per species from train-split counts, so
    runtime overhead is negligible relative to head optimization.

    Clamped to [min_prior, max_prior] for numerical stability.
    """
    if n_species_total_rows <= 0:
        return min_prior
    numerator = n_species_positives + smoothing_strength * global_positive_rate
    denominator = n_species_total_rows + smoothing_strength
    return float(np.clip(numerator / max(denominator, 1e-12), min_prior, max_prior))


def train_species_heads(
    data_root: str | Path,
    encoder_checkpoint: str | Path,
    output_dir: str | Path,
    *,
    min_positives: int = 50,
    head_epochs: int = 50,
    head_lr: float = 1e-2,
    head_weight_decay: float = 1e-3,
    batch_size: int = 4096,
    device: str = "auto",
) -> Path:
    """Train per-species PU logistic heads on frozen encoder embeddings.

    Args:
        data_root: path to preprocessed partitioned parquet dataset.
        encoder_checkpoint: path to saved encoder_best.pt from Stage B.
        output_dir: directory for saved species head weights.
        min_positives: skip species with fewer than this many positive samples.
        head_epochs: epochs per species head.
        head_lr: learning rate for head optimizer.
        head_weight_decay: weight decay for head optimizer.
        batch_size: batch size for embedding computation only (heads
            train full-batch per species, which is preferable for
            logistic regression convergence).
        device: "auto", "cuda", "mps", or "cpu".

    Returns:
        Path to saved heads checkpoint.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if device == "auto":
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    dev = torch.device(device)

    # Load encoder
    checkpoint = torch.load(encoder_checkpoint, map_location=dev, weights_only=True)
    input_dim = checkpoint["input_dim"]
    embed_dim = checkpoint["embed_dim"]
    hidden_dim = checkpoint["hidden_dim"]

    encoder = SharedEncoder(input_dim, embed_dim=embed_dim, hidden_dim=hidden_dim).to(dev)
    encoder.load_state_dict(checkpoint["encoder_state_dict"])
    encoder.eval()
    for param in encoder.parameters():
        param.requires_grad = False

    print(f"Loaded encoder from {encoder_checkpoint} (embed_dim={embed_dim})")
    print("Loading split metadata (streaming mode)...")
    train_ds = StreamingTrainingDataset(data_root, split="train")
    val_ds = StreamingTrainingDataset(data_root, split="val")
    print(f"Train rows: {train_ds.row_count:,} | Val rows: {val_ds.row_count:,}")

    print("Computing training embeddings...")
    train_cache_dir = output_dir / "_heads_train_cache"
    train_z, train_species, train_labels, train_weights = _materialize_split_embeddings_memmap(
        encoder,
        train_ds,
        split_name="train",
        device=dev,
        batch_size=batch_size,
        embed_dim=embed_dim,
        cache_dir=train_cache_dir,
    )
    n_total_positive_train = int(np.count_nonzero(train_labels == 1))
    n_total_rows_train = int(train_labels.shape[0])
    global_positive_rate = float(n_total_positive_train / n_total_rows_train) if n_total_rows_train > 0 else 0.0

    print("Computing validation embeddings...")
    val_cache_dir = output_dir / "_heads_val_cache"
    val_z, val_species, val_labels, _ = _materialize_split_embeddings_memmap(
        encoder,
        val_ds,
        split_name="val",
        device=dev,
        batch_size=batch_size,
        embed_dim=embed_dim,
        cache_dir=val_cache_dir,
    )

    # Find species with enough positives
    unique_species, species_total_counts = np.unique(train_species, return_counts=True)
    pos_species, species_pos_counts = np.unique(train_species[train_labels == 1], return_counts=True)
    species_pos_map = {
        int(sp): int(cnt) for sp, cnt in zip(pos_species.tolist(), species_pos_counts.tolist(), strict=True)
    }
    eligible = [
        int(sp)
        for sp, total_count in zip(unique_species.tolist(), species_total_counts.tolist(), strict=True)
        if species_pos_map.get(int(sp), 0) >= min_positives and int(total_count) > 0
    ]
    print(f"Species total: {len(unique_species):,} | Eligible (>={min_positives} positives): {len(eligible):,}")

    print("Indexing species rows for fast per-species slicing...")
    train_order = np.argsort(train_species, kind="stable")
    train_sorted_species = train_species[train_order]
    train_boundaries = np.flatnonzero(np.diff(train_sorted_species)) + 1
    train_keys = train_sorted_species[np.concatenate(([0], train_boundaries))]
    train_starts = np.concatenate(([0], train_boundaries))
    train_ends = np.concatenate((train_boundaries, [train_sorted_species.shape[0]]))
    train_ranges = {
        int(key): (int(start), int(end))
        for key, start, end in zip(train_keys.tolist(), train_starts.tolist(), train_ends.tolist(), strict=True)
    }

    val_order = np.argsort(val_species, kind="stable")
    val_sorted_species = val_species[val_order]
    if val_sorted_species.size > 0:
        val_boundaries = np.flatnonzero(np.diff(val_sorted_species)) + 1
        val_keys = val_sorted_species[np.concatenate(([0], val_boundaries))]
        val_starts = np.concatenate(([0], val_boundaries))
        val_ends = np.concatenate((val_boundaries, [val_sorted_species.shape[0]]))
        val_ranges = {
            int(key): (int(start), int(end))
            for key, start, end in zip(val_keys.tolist(), val_starts.tolist(), val_ends.tolist(), strict=True)
        }
    else:
        val_ranges = {}

    head_states: dict[int, dict] = {}
    species_meta: dict[int, dict] = {}
    total_start = time.perf_counter()

    for idx, sp_key in enumerate(eligible):
        train_range = train_ranges.get(int(sp_key))
        if train_range is None:
            continue
        train_start, train_end = train_range
        train_idx = train_order[train_start:train_end]

        sp_z_np = np.asarray(train_z[train_idx], dtype=np.float32)
        sp_labels_np = np.asarray(train_labels[train_idx], dtype=np.int8)
        sp_weights_np = np.asarray(train_weights[train_idx], dtype=np.float32)

        sp_z = torch.from_numpy(sp_z_np).to(dev)
        sp_labels = torch.from_numpy(sp_labels_np).to(dev)
        sp_weights = torch.from_numpy(sp_weights_np).to(dev)

        pos_mask = sp_labels == 1
        unl_mask = sp_labels == 0
        n_pos = int(pos_mask.sum().item())
        n_unl = int(unl_mask.sum().item())

        if n_pos == 0 or n_unl == 0:
            continue

        n_species_rows = n_pos + n_unl
        prior_pi = estimate_prior(
            n_pos,
            n_species_rows,
            global_positive_rate,
        )

        head = SpeciesHead(embed_dim=embed_dim).to(dev)
        optimizer = torch.optim.AdamW(head.parameters(), lr=head_lr, weight_decay=head_weight_decay)

        best_val_loss = float("inf")
        best_state = None

        for epoch in range(head_epochs):
            head.train()
            f_pos = head(sp_z[pos_mask])
            f_unl = head(sp_z[unl_mask])
            loss = nnpu_loss(
                f_pos,
                f_unl,
                prior_pi,
                weights_positive=sp_weights[pos_mask],
                weights_unlabeled=sp_weights[unl_mask],
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()

            # Val check every 10 epochs. Species absent from the val
            # split (common for rare species under spatial blocking) never
            # update best_state, so the final-epoch state is used as fallback.
            if (epoch + 1) % 10 == 0 or epoch == head_epochs - 1:
                head.eval()
                with torch.no_grad():
                    val_range = val_ranges.get(int(sp_key))
                    if val_range is not None:
                        val_start, val_end = val_range
                        val_idx = val_order[val_start:val_end]
                        sp_val_z_np = np.asarray(val_z[val_idx], dtype=np.float32)
                        sp_val_labels_np = np.asarray(val_labels[val_idx], dtype=np.int8)
                        sp_val_z = torch.from_numpy(sp_val_z_np).to(dev)
                        sp_val_labels = torch.from_numpy(sp_val_labels_np).to(dev)
                        val_pos = sp_val_labels == 1
                        val_unl = sp_val_labels == 0
                        if val_pos.any() and val_unl.any():
                            v_loss = nnpu_loss(
                                head(sp_val_z[val_pos]),
                                head(sp_val_z[val_unl]),
                                prior_pi,
                            ).item()
                            if v_loss < best_val_loss:
                                best_val_loss = v_loss
                                best_state = {k: v.clone() for k, v in head.state_dict().items()}

        if best_state is None:
            best_state = {k: v.clone() for k, v in head.state_dict().items()}

        head_states[sp_key] = best_state
        species_meta[sp_key] = {
            "n_positives": n_pos,
            "n_unlabeled": n_unl,
            "n_rows": n_species_rows,
            "prior_pi": prior_pi,
            "prior_global_positive_rate": global_positive_rate,
            "prior_smoothing_strength": 50.0,
            "val_loss": best_val_loss if best_val_loss < float("inf") else None,
        }

        if (idx + 1) % HEARTBEAT_INTERVAL_SPECIES == 0:
            elapsed = time.perf_counter() - total_start
            print(f"  Heads trained: {idx + 1:,}/{len(eligible):,} | elapsed: {elapsed:.1f}s")

    total_seconds = time.perf_counter() - total_start
    heads_path = output_dir / "species_heads.pt"
    torch.save(
        {
            "embed_dim": embed_dim,
            "head_states": head_states,
            "species_meta": species_meta,
        },
        heads_path,
    )
    print(f"Trained {len(head_states):,} species heads in {total_seconds:.1f}s")
    print(f"Saved to: {heads_path}")
    return heads_path
