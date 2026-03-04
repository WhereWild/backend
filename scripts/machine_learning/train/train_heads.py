"""Stage C: Per-species PU head training (model card Section 4, Stage C)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol

import numpy as np
import torch

try:
    from ._compat import import_local_symbol
except ImportError:
    from _compat import import_local_symbol

TrainingDataset = import_local_symbol("data", "TrainingDataset")
nnpu_loss = import_local_symbol("losses", "nnpu_loss")
SharedEncoder = import_local_symbol("model", "SharedEncoder")
SpeciesHead = import_local_symbol("model", "SpeciesHead")


class _FeatureDataset(Protocol):
    features: torch.Tensor

    def __len__(self) -> int: ...

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


def estimate_prior(
    n_species_positives: int,
    n_total_rows: int,
    min_prior: float = 1e-4,
    max_prior: float = 0.5,
) -> float:
    """Estimate class prior pi_s for one species.

    pi_s = count(positives for species s) / count(all training rows).

    Uses the full dataset size as denominator rather than only rows sharing
    the same species_key, because background rows inherit species_key from
    their source file and would bias the denominator upward.

    Clamped to [min_prior, max_prior] for numerical stability.
    """
    if n_total_rows == 0:
        return min_prior
    return float(np.clip(n_species_positives / n_total_rows, min_prior, max_prior))


def train_species_heads(
    data_root: str | Path,
    encoder_checkpoint: str | Path,
    output_dir: str | Path,
    *,
    min_positives: int = 5,
    head_epochs: int = 100,
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
    print("Loading training data...")
    train_ds = TrainingDataset(data_root, split="train")
    val_ds = TrainingDataset(data_root, split="val")

    print("Computing training embeddings...")
    # Keep embeddings on CPU to avoid GPU OOM on large datasets;
    # per-species slices are moved to device during head training.
    train_z = compute_embeddings(encoder, train_ds, dev, batch_size=batch_size)
    train_species = train_ds.species_key
    train_labels = train_ds.presence_label
    train_weights = train_ds.sample_weight
    n_total_train = len(train_ds)

    print("Computing validation embeddings...")
    val_z = compute_embeddings(encoder, val_ds, dev, batch_size=batch_size)
    val_species = val_ds.species_key
    val_labels = val_ds.presence_label

    # Find species with enough positives
    unique_species = train_species.unique().tolist()
    eligible = []
    for sp in unique_species:
        sp_mask = train_species == sp
        n_pos = int((train_labels[sp_mask] == 1).sum().item())
        if n_pos >= min_positives:
            eligible.append(sp)
    print(f"Species total: {len(unique_species):,} | Eligible (>={min_positives} positives): {len(eligible):,}")

    head_states: dict[int, dict] = {}
    species_meta: dict[int, dict] = {}
    total_start = time.perf_counter()

    for idx, sp_key in enumerate(eligible):
        sp_train_mask = train_species == sp_key
        sp_z = train_z[sp_train_mask].to(dev)
        sp_labels = train_labels[sp_train_mask]
        sp_weights = train_weights[sp_train_mask].to(dev)

        pos_mask = sp_labels == 1
        unl_mask = sp_labels == 0
        n_pos = int(pos_mask.sum().item())
        n_unl = unl_mask.sum().item()

        if n_pos == 0 or n_unl == 0:
            continue

        prior_pi = estimate_prior(n_pos, n_total_train)

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
                    sp_val_mask = val_species == sp_key
                    if sp_val_mask.any():
                        sp_val_z = val_z[sp_val_mask].to(dev)
                        sp_val_labels = val_labels[sp_val_mask]
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
            "prior_pi": prior_pi,
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
