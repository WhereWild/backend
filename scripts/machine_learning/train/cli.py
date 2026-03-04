"""CLI entrypoint for Darwin SDM training pipeline.

Usage:

  # Stage B: Train shared encoder (self-supervised)
  uv run python scripts/machine_learning/train/cli.py encoder \
      --data-root ./data/species_observation_canary \
      --output-dir ./checkpoints/encoder

  # Stage C: Train per-species PU heads
  uv run python scripts/machine_learning/train/cli.py heads \
      --data-root ./data/species_observation_canary \
      --encoder-checkpoint ./checkpoints/encoder/encoder_best.pt \
      --output-dir ./checkpoints/heads

  # Both stages sequentially
  uv run python scripts/machine_learning/train/cli.py all \
      --data-root ./data/species_observation_canary \
      --output-dir ./checkpoints
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from ._compat import import_local_symbol
except ImportError:
    from _compat import import_local_symbol


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for training pipeline."""
    parser = argparse.ArgumentParser(
        description="Darwin SDM training pipeline.",
    )
    subparsers = parser.add_subparsers(dest="stage", required=True)

    # Shared arguments (all stages)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--data-root", type=Path, required=True, help="Preprocessed parquet dataset root.")
    shared.add_argument("--output-dir", type=Path, required=True, help="Output directory for checkpoints.")
    shared.add_argument("--device", type=str, default="auto", help="Device: auto, cuda, mps, cpu.")
    shared.add_argument("--batch-size", type=int, default=4096, help="Mini-batch size.")

    # Encoder-specific arguments
    encoder_args = argparse.ArgumentParser(add_help=False)
    encoder_args.add_argument("--embed-dim", type=int, default=128, help="Encoder embedding dimension.")
    encoder_args.add_argument("--hidden-dim", type=int, default=256, help="Encoder hidden layer dimension.")
    encoder_args.add_argument("--epochs", type=int, default=50, help="Training epochs.")
    encoder_args.add_argument("--lr", type=float, default=1e-3, help="Peak learning rate.")
    encoder_args.add_argument("--weight-decay", type=float, default=1e-4, help="AdamW weight decay.")
    encoder_args.add_argument("--recon-weight", type=float, default=1.0, help="Reconstruction loss weight.")
    encoder_args.add_argument("--contrastive-weight", type=float, default=0.5, help="Contrastive loss weight.")
    encoder_args.add_argument("--contrastive-temperature", type=float, default=0.1, help="NT-Xent temperature.")
    encoder_args.add_argument("--no-amp", action="store_true", help="Disable automatic mixed precision.")

    # Heads-specific arguments
    heads_args = argparse.ArgumentParser(add_help=False)
    heads_args.add_argument("--min-positives", type=int, default=5, help="Skip species with fewer positives.")
    heads_args.add_argument("--head-epochs", type=int, default=100, help="Epochs per species head.")
    heads_args.add_argument("--head-lr", type=float, default=1e-2, help="Species head learning rate.")
    heads_args.add_argument("--head-weight-decay", type=float, default=1e-3, help="Species head weight decay.")

    # Stage B: encoder
    subparsers.add_parser("encoder", parents=[shared, encoder_args], help="Stage B: train shared encoder.")

    # Stage C: species heads
    heads = subparsers.add_parser("heads", parents=[shared, heads_args], help="Stage C: train per-species PU heads.")
    heads.add_argument("--encoder-checkpoint", type=Path, required=True, help="Path to encoder_best.pt.")

    # Both stages
    subparsers.add_parser(
        "all", parents=[shared, encoder_args, heads_args], help="Run Stage B then Stage C sequentially."
    )

    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()

    if args.stage in ("encoder", "all"):
        train_encoder = import_local_symbol("train_encoder", "train_encoder")

        encoder_dir = args.output_dir / "encoder" if args.stage == "all" else args.output_dir
        encoder_path = train_encoder(
            data_root=args.data_root,
            output_dir=encoder_dir,
            embed_dim=args.embed_dim,
            hidden_dim=args.hidden_dim,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            weight_decay=args.weight_decay,
            recon_weight=args.recon_weight,
            contrastive_weight=args.contrastive_weight,
            contrastive_temperature=args.contrastive_temperature,
            use_amp=not args.no_amp,
            device=args.device,
        )
    else:
        encoder_path = None

    if args.stage in ("heads", "all"):
        train_species_heads = import_local_symbol("train_heads", "train_species_heads")

        if args.stage == "heads":
            checkpoint = args.encoder_checkpoint
        else:
            if encoder_path is None:
                raise RuntimeError("Encoder checkpoint was not produced in 'all' stage.")
            checkpoint = encoder_path

        heads_dir = args.output_dir / "heads" if args.stage == "all" else args.output_dir
        train_species_heads(
            data_root=args.data_root,
            encoder_checkpoint=checkpoint,
            output_dir=heads_dir,
            min_positives=args.min_positives,
            head_epochs=args.head_epochs,
            head_lr=args.head_lr,
            head_weight_decay=args.head_weight_decay,
            batch_size=args.batch_size,
            device=args.device,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
