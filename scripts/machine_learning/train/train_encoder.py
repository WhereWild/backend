"""Stage B: Self-supervised encoder pretraining (model card Section 4, Stage B)."""

from __future__ import annotations

import time
from contextlib import nullcontext
from pathlib import Path

import torch
from torch import nn

try:
    from ._compat import import_local_symbol
except ImportError:
    from _compat import import_local_symbol

TrainingDataset = import_local_symbol("data", "TrainingDataset")
make_batches = import_local_symbol("data", "make_batches")
StreamingTrainingDataset = import_local_symbol("data", "StreamingTrainingDataset")
make_streaming_batches = import_local_symbol("data", "make_streaming_batches")
make_chunk_cached_batches = import_local_symbol("data", "make_chunk_cached_batches")
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
    batch_size: int = 32768,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    recon_weight: float = 1.0,
    use_amp: bool = True,
    device: str = "auto",
    data_mode: str = "chunk-cached",
    chunk_rows: int = 400_000,
    prefetch_chunks: int = 3,
    shuffle_mode: str = "block",
    shuffle_block_rows: int = 131_072,
    adaptive_prefetch: bool = True,
) -> Path:
    """Train shared encoder with masked reconstruction objective.

    Objective (model card Stage B):
    - Auxiliary reconstruction of environmental features (MSE on observed values).

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
        use_amp: use automatic mixed precision (bf16/fp16).
        device: "auto", "cuda", "mps", or "cpu".
        data_mode: "streaming" (lazy parquet scans), "chunk-cached"
            (bounded in-memory chunks), or "in-memory"
            (materialize split tensors in RAM for fastest iteration).
        chunk_rows: rows per in-memory chunk when data_mode="chunk-cached".
        prefetch_chunks: number of chunk-cached chunks to prefetch in background.
        shuffle_mode: encoder training shuffle mode: "global" or "block".
        shuffle_block_rows: block size when shuffle_mode="block".
        adaptive_prefetch: dynamically reduce prefetch depth under memory/swap pressure.

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
    use_pin = dev.type == "cuda"

    print(f"Device: {dev} | AMP: {amp_enabled} ({amp_dtype})")
    if data_mode not in {"streaming", "chunk-cached", "in-memory"}:
        raise ValueError(f"Unsupported data_mode={data_mode!r}. Expected 'streaming', 'chunk-cached', or 'in-memory'.")

    if data_mode in {"streaming", "chunk-cached"}:
        print(f"Probing training split ({data_mode} mode)...")
        train_ds = StreamingTrainingDataset(data_root, split="train")
        val_ds = StreamingTrainingDataset(data_root, split="val")
        input_dim = train_ds.feature_dim
        recon_dim = train_ds.recon_dim
        print(f"Train rows: {train_ds.row_count:,} | Val rows: {val_ds.row_count:,} | Input dim: {input_dim}")
        if data_mode == "streaming":
            train_loader = make_streaming_batches(
                train_ds,
                batch_size=batch_size,
                shuffle=True,
                shuffle_mode=shuffle_mode,
                shuffle_block_rows=shuffle_block_rows,
            )
            val_loader = make_streaming_batches(
                val_ds,
                batch_size=batch_size,
                shuffle=False,
                shuffle_mode=shuffle_mode,
                shuffle_block_rows=shuffle_block_rows,
            )
        else:
            print(
                f"Chunk-cached rows per chunk: {chunk_rows:,} | "
                f"prefetch chunks: {prefetch_chunks} | "
                f"shuffle mode: {shuffle_mode} | "
                f"adaptive prefetch: {adaptive_prefetch}"
            )
            train_loader = make_chunk_cached_batches(
                train_ds,
                batch_size=batch_size,
                shuffle=True,
                chunk_rows=chunk_rows,
                prefetch_chunks=prefetch_chunks,
                shuffle_mode=shuffle_mode,
                shuffle_block_rows=shuffle_block_rows,
                adaptive_prefetch=adaptive_prefetch,
            )
            val_loader = make_chunk_cached_batches(
                val_ds,
                batch_size=batch_size,
                shuffle=False,
                chunk_rows=chunk_rows,
                prefetch_chunks=prefetch_chunks,
                shuffle_mode=shuffle_mode,
                shuffle_block_rows=shuffle_block_rows,
                adaptive_prefetch=adaptive_prefetch,
            )
    else:
        print("Loading training split (in-memory mode)...")
        train_ds = TrainingDataset(data_root, split="train")
        val_ds = TrainingDataset(data_root, split="val")
        if use_pin:
            train_ds.pin()
            val_ds.pin()
        input_dim = train_ds.feature_dim
        recon_dim = train_ds.recon_dim
        print(f"Train rows: {train_ds.num_rows:,} | Val rows: {val_ds.num_rows:,} | Input dim: {input_dim}")

        train_loader = make_batches(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = make_batches(val_ds, batch_size=batch_size, shuffle=False)

    encoder = SharedEncoder(input_dim, embed_dim=embed_dim, hidden_dim=hidden_dim).to(dev)
    aux_decoder = AuxDecoder(embed_dim, recon_dim).to(dev)

    params = list(encoder.parameters()) + list(aux_decoder.parameters())
    optimizer = torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)

    use_per_step_scheduler = data_mode == "in-memory"
    if use_per_step_scheduler:
        total_steps = epochs * len(train_loader)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps)
    else:
        total_steps = None
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    amp = getattr(torch, "amp")
    scaler = amp.GradScaler("cuda", enabled=amp_enabled)

    print(f"Encoder params: {sum(p.numel() for p in encoder.parameters()):,}")
    print(f"AuxDecoder params: {sum(p.numel() for p in aux_decoder.parameters()):,}")
    if total_steps is not None:
        print(f"Total steps: {total_steps:,} | Epochs: {epochs}")
    else:
        print(
            "Total steps: dynamic (streaming/chunk-cached loaders can emit more "
            "batches than row_count/batch_size estimate) | "
            f"Epochs: {epochs}"
        )

    best_val_loss = float("inf")
    best_epoch = -1

    for epoch in range(epochs):
        encoder.train()
        aux_decoder.train()
        epoch_start = time.perf_counter()
        train_loss_sum = 0.0
        train_steps = 0
        heartbeat_last_time = epoch_start
        heartbeat_last_step = 0

        for step, batch in enumerate(train_loader):
            features = batch["features"].to(dev, non_blocking=use_pin)
            recon_target = batch["recon_target"].to(dev, non_blocking=use_pin)
            masks = batch["masks"].to(dev, non_blocking=use_pin)

            amp_context = amp.autocast("cuda", dtype=amp_dtype) if amp_enabled else nullcontext()
            with amp_context:
                z = encoder(features)
                recon = aux_decoder(z)
                loss_recon = reconstruction_loss(recon, recon_target, masks)
                loss = recon_weight * loss_recon

            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(params, max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
            if use_per_step_scheduler:
                scheduler.step()

            train_loss_sum += loss.item()
            train_steps += 1

            if (step + 1) % HEARTBEAT_INTERVAL_STEPS == 0:
                avg = train_loss_sum / train_steps
                lr_now = optimizer.param_groups[0]["lr"]
                now = time.perf_counter()
                step_delta = train_steps - heartbeat_last_step
                seconds_delta = max(now - heartbeat_last_time, 1e-9)
                steps_per_second = step_delta / seconds_delta
                heartbeat_last_time = now
                heartbeat_last_step = train_steps
                if use_per_step_scheduler:
                    print(
                        f"  Epoch {epoch + 1}/{epochs} | step {step + 1}/{len(train_loader)} | "
                        f"loss: {avg:.4f} | lr: {lr_now:.2e} | steps/s: {steps_per_second:.1f}"
                    )
                else:
                    print(
                        f"  Epoch {epoch + 1}/{epochs} | step {step + 1} | "
                        f"loss: {avg:.4f} | lr: {lr_now:.2e} | steps/s: {steps_per_second:.1f}"
                    )

        # Validation
        encoder.eval()
        aux_decoder.eval()
        val_loss_sum = 0.0
        val_steps = 0
        with torch.no_grad():
            for batch in val_loader:
                features = batch["features"].to(dev, non_blocking=use_pin)
                recon_target = batch["recon_target"].to(dev, non_blocking=use_pin)
                masks = batch["masks"].to(dev, non_blocking=use_pin)
                amp_context = amp.autocast("cuda", dtype=amp_dtype) if amp_enabled else nullcontext()
                with amp_context:
                    z = encoder(features)
                    recon = aux_decoder(z)
                    loss_recon = reconstruction_loss(recon, recon_target, masks)
                    loss = recon_weight * loss_recon
                val_loss_sum += loss.item()
                val_steps += 1

        train_avg = train_loss_sum / max(train_steps, 1)
        val_avg = val_loss_sum / max(val_steps, 1)
        epoch_seconds = time.perf_counter() - epoch_start

        if not use_per_step_scheduler:
            scheduler.step()

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
