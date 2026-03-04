"""Stage B: Self-supervised encoder pretraining (model card Section 4, Stage B)."""

from __future__ import annotations

import time
from contextlib import nullcontext
from pathlib import Path

import torch
import torch.nn as nn

try:
    from ._compat import import_local_symbol
except ImportError:
    from _compat import import_local_symbol

TrainingDataset = import_local_symbol("data", "TrainingDataset")
make_batches = import_local_symbol("data", "make_batches")
contrastive_loss = import_local_symbol("losses", "contrastive_loss")
reconstruction_loss = import_local_symbol("losses", "reconstruction_loss")
AuxDecoder = import_local_symbol("model", "AuxDecoder")
SharedEncoder = import_local_symbol("model", "SharedEncoder")

HEARTBEAT_INTERVAL_STEPS = 50


def train_encoder(
    data_root: str | Path,
    output_dir: str | Path,
    *,
    embed_dim: int = 128,
    hidden_dim: int = 256,
    epochs: int = 50,
    batch_size: int = 4096,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    recon_weight: float = 1.0,
    contrastive_weight: float = 0.5,
    contrastive_temperature: float = 0.1,
    use_amp: bool = True,
    device: str = "auto",
) -> Path:
    """Train shared encoder with self-supervised objectives.

    Multi-task objective (model card Stage B):
    - Auxiliary reconstruction of environmental features (MSE on observed values).
    - Spatial contrastive loss on cell_id proximity (NT-Xent).

    Args:
        data_root: path to preprocessed partitioned parquet dataset.
        output_dir: directory for saved encoder checkpoint.
        embed_dim: encoder embedding dimension.
        hidden_dim: encoder hidden layer dimension.
        epochs: training epochs.
        batch_size: effective mini-batch size.
        lr: peak learning rate.
        weight_decay: AdamW weight decay.
        recon_weight: loss weight for reconstruction term.
        contrastive_weight: loss weight for contrastive term.
        contrastive_temperature: temperature for NT-Xent.
        use_amp: use automatic mixed precision (bf16/fp16).
        device: "auto", "cuda", "mps", or "cpu".

    Returns:
        Path to saved encoder checkpoint.
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
    amp_enabled = use_amp and dev.type in ("cuda",)
    if amp_enabled:
        amp_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    else:
        amp_dtype = torch.float32

    print(f"Device: {dev} | AMP: {amp_enabled} ({amp_dtype})")
    print("Loading training split...")
    use_pin = dev.type == "cuda"
    train_ds = TrainingDataset(data_root, split="train")
    val_ds = TrainingDataset(data_root, split="val")
    if use_pin:
        train_ds.pin()
        val_ds.pin()
    input_dim = train_ds.feature_dim

    print(f"Train rows: {len(train_ds):,} | Val rows: {len(val_ds):,} | Input dim: {input_dim}")

    train_loader = make_batches(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = make_batches(val_ds, batch_size=batch_size, shuffle=False)

    encoder = SharedEncoder(input_dim, embed_dim=embed_dim, hidden_dim=hidden_dim).to(dev)
    aux_decoder = AuxDecoder(embed_dim, input_dim).to(dev)

    params = list(encoder.parameters()) + list(aux_decoder.parameters())
    optimizer = torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)

    total_steps = epochs * len(train_loader)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps)
    amp = getattr(torch, "amp")
    scaler = amp.GradScaler("cuda", enabled=amp_enabled)

    print(f"Encoder params: {sum(p.numel() for p in encoder.parameters()):,}")
    print(f"AuxDecoder params: {sum(p.numel() for p in aux_decoder.parameters()):,}")
    print(f"Total steps: {total_steps:,} | Epochs: {epochs}")

    best_val_loss = float("inf")
    best_epoch = -1

    for epoch in range(epochs):
        encoder.train()
        aux_decoder.train()
        epoch_start = time.perf_counter()
        train_loss_sum = 0.0
        train_steps = 0

        for step, batch in enumerate(train_loader):
            features = batch["features"].to(dev, non_blocking=use_pin)
            masks = batch["masks"].to(dev, non_blocking=use_pin)

            cell_id_hash = batch["cell_id_hash"].to(dev, non_blocking=use_pin)

            amp_context = amp.autocast("cuda", dtype=amp_dtype) if amp_enabled else nullcontext()
            with amp_context:
                z = encoder(features)
                recon = aux_decoder(z)
                loss_recon = reconstruction_loss(recon, features, masks)
                loss_contrastive = contrastive_loss(z, cell_id_hash, temperature=contrastive_temperature)

                loss = recon_weight * loss_recon + contrastive_weight * loss_contrastive

            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(params, max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            train_loss_sum += loss.item()
            train_steps += 1

            if (step + 1) % HEARTBEAT_INTERVAL_STEPS == 0:
                avg = train_loss_sum / train_steps
                lr_now = scheduler.get_last_lr()[0]
                print(
                    f"  Epoch {epoch + 1}/{epochs} | step {step + 1}/{len(train_loader)} | "
                    f"loss: {avg:.4f} | lr: {lr_now:.2e}"
                )

        # Validation
        encoder.eval()
        aux_decoder.eval()
        val_loss_sum = 0.0
        val_steps = 0
        with torch.no_grad():
            for batch in val_loader:
                features = batch["features"].to(dev, non_blocking=use_pin)
                masks = batch["masks"].to(dev, non_blocking=use_pin)
                cell_id_hash = batch["cell_id_hash"].to(dev, non_blocking=use_pin)
                amp_context = amp.autocast("cuda", dtype=amp_dtype) if amp_enabled else nullcontext()
                with amp_context:
                    z = encoder(features)
                    recon = aux_decoder(z)
                    loss_recon = reconstruction_loss(recon, features, masks)
                    loss_contrastive = contrastive_loss(z, cell_id_hash, temperature=contrastive_temperature)
                    loss = recon_weight * loss_recon + contrastive_weight * loss_contrastive
                val_loss_sum += loss.item()
                val_steps += 1

        train_avg = train_loss_sum / max(train_steps, 1)
        val_avg = val_loss_sum / max(val_steps, 1)
        epoch_seconds = time.perf_counter() - epoch_start

        improved = ""
        if val_avg < best_val_loss:
            best_val_loss = val_avg
            best_epoch = epoch
            checkpoint_path = output_dir / "encoder_best.pt"
            torch.save(
                {
                    "encoder_state_dict": encoder.state_dict(),
                    "aux_decoder_state_dict": aux_decoder.state_dict(),
                    "embed_dim": embed_dim,
                    "hidden_dim": hidden_dim,
                    "input_dim": input_dim,
                    "epoch": epoch,
                    "val_loss": val_avg,
                },
                checkpoint_path,
            )
            improved = " (new best)"

        print(
            f"Epoch {epoch + 1}/{epochs} | "
            f"train_loss: {train_avg:.4f} | val_loss: {val_avg:.4f}{improved} | "
            f"time: {epoch_seconds:.1f}s"
        )

    final_path = output_dir / "encoder_best.pt"
    print(f"Best encoder at epoch {best_epoch + 1} | val_loss: {best_val_loss:.4f}")
    print(f"Saved to: {final_path}")
    return final_path
