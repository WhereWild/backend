"""Sweep Stage C head-training hyperparameters and rank trials by validation loss."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from itertools import product
from pathlib import Path
from statistics import median
from typing import Any

import torch

try:
    from scripts.machine_learning.train.train_heads import train_species_heads
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from scripts.machine_learning.train.train_heads import train_species_heads


def _parse_numeric_list(raw: str, cast: type[int | float], name: str) -> list[int] | list[float]:
    """Parse a comma-separated numeric CLI list into typed values."""
    values: list[int] | list[float] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            values.append(cast(token))
        except ValueError as exc:
            raise ValueError(f"Invalid value {token!r} in --{name}") from exc
    if not values:
        raise ValueError(f"--{name} produced an empty list")
    return values


def _parse_species_keys(raw: str) -> list[int]:
    """Parse optional comma-separated species keys from CLI input."""
    keys: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        keys.append(int(token))
    return keys


def _slug(text: str) -> str:
    """Convert a trial label into a filesystem-safe slug."""
    return re.sub(r"[^a-zA-Z0-9_.=-]+", "-", text)


def _summarize_species_meta(
    species_meta: dict[int, dict[str, Any]],
    species_filter: set[int],
) -> dict[str, Any]:
    """Summarize validation-loss stats used to rank sweep trials."""
    losses: list[float] = []
    skipped_filter = 0

    for sp_key_raw, meta in species_meta.items():
        sp_key = int(sp_key_raw)
        if species_filter and sp_key not in species_filter:
            skipped_filter += 1
            continue
        loss = meta.get("val_loss")
        if loss is None:
            continue
        losses.append(float(loss))

    n_scored = len(losses)
    summary: dict[str, Any] = {
        "n_species_total": len(species_meta),
        "n_species_scored": n_scored,
        "n_species_skipped_by_filter": skipped_filter,
        "objective_median_val_loss": float("inf"),
        "mean_val_loss": None,
        "min_val_loss": None,
        "max_val_loss": None,
    }

    if n_scored == 0:
        return summary

    losses_sorted = sorted(losses)
    summary["objective_median_val_loss"] = float(median(losses_sorted))
    summary["mean_val_loss"] = float(sum(losses_sorted) / n_scored)
    summary["min_val_loss"] = float(losses_sorted[0])
    summary["max_val_loss"] = float(losses_sorted[-1])
    return summary


def _parse_args() -> argparse.Namespace:
    """Parse CLI flags for Stage C sweep configuration."""
    parser = argparse.ArgumentParser(
        description="Run a grid sweep over Stage C species-head training hyperparameters.",
    )
    parser.add_argument("--data-root", required=True, help="Path to preprocessed split-partitioned parquet dataset.")
    parser.add_argument(
        "--encoder-checkpoint", required=True, help="Path to encoder_best.pt used for Stage C training."
    )
    parser.add_argument(
        "--output-root", required=True, help="Directory where trial outputs and summary JSON are written."
    )
    parser.add_argument("--head-lr-grid", default="0.01,0.005,0.001", help="Comma-separated values for --head-lr.")
    parser.add_argument(
        "--head-weight-decay-grid",
        default="0.001,0.0003,0.0001",
        help="Comma-separated values for --head-weight-decay.",
    )
    parser.add_argument("--head-epochs-grid", default="80,120", help="Comma-separated values for --head-epochs.")
    parser.add_argument("--min-positives", default=5, type=int, help="Minimum positives required per species.")
    parser.add_argument("--batch-size", default=4096, type=int, help="Batch size passed to train_species_heads.")
    parser.add_argument("--device", default="auto", help="Device: auto, cuda, mps, cpu.")
    parser.add_argument(
        "--species-keys",
        default="",
        help="Optional comma-separated species keys. When set, only these species contribute to objective ranking.",
    )
    parser.add_argument(
        "--max-trials",
        default=0,
        type=int,
        help="Optional cap on number of generated trials (0 means run all combinations).",
    )
    parser.add_argument(
        "--results-json",
        default="",
        help="Optional explicit output file path for sweep summary JSON.",
    )
    return parser.parse_args()


def main() -> None:
    """Run grid trials, rank results, and write sweep summary JSON."""
    args = _parse_args()

    data_root = Path(args.data_root)
    encoder_checkpoint = Path(args.encoder_checkpoint)
    output_root = Path(args.output_root)

    if not data_root.exists():
        raise FileNotFoundError(f"data-root does not exist: {data_root}")
    if not encoder_checkpoint.exists():
        raise FileNotFoundError(f"encoder-checkpoint does not exist: {encoder_checkpoint}")

    lr_grid = [float(v) for v in _parse_numeric_list(args.head_lr_grid, float, "head-lr-grid")]
    wd_grid = [float(v) for v in _parse_numeric_list(args.head_weight_decay_grid, float, "head-weight-decay-grid")]
    epoch_grid = [int(v) for v in _parse_numeric_list(args.head_epochs_grid, int, "head-epochs-grid")]
    species_filter = set(_parse_species_keys(args.species_keys))

    trials = list(product(lr_grid, wd_grid, epoch_grid))
    if args.max_trials > 0:
        trials = trials[: args.max_trials]

    output_root.mkdir(parents=True, exist_ok=True)

    trial_rows: list[dict[str, Any]] = []

    for index, (head_lr, head_weight_decay, head_epochs) in enumerate(trials, start=1):
        trial_name = _slug(f"trial_{index:03d}_lr={head_lr}_wd={head_weight_decay}_ep={head_epochs}")
        trial_dir = output_root / trial_name
        trial_dir.mkdir(parents=True, exist_ok=True)

        print(
            f"[trial {index}/{len(trials)}] "
            f"head_lr={head_lr} head_weight_decay={head_weight_decay} head_epochs={head_epochs}"
        )

        heads_path = train_species_heads(
            data_root=data_root,
            encoder_checkpoint=encoder_checkpoint,
            output_dir=trial_dir,
            min_positives=args.min_positives,
            head_epochs=head_epochs,
            head_lr=head_lr,
            head_weight_decay=head_weight_decay,
            batch_size=args.batch_size,
            device=args.device,
        )

        checkpoint = torch.load(heads_path, map_location="cpu", weights_only=True)
        species_meta = checkpoint.get("species_meta", {})
        summary = _summarize_species_meta(species_meta, species_filter)

        trial_rows.append({
            "trial_index": index,
            "trial_name": trial_name,
            "head_lr": head_lr,
            "head_weight_decay": head_weight_decay,
            "head_epochs": head_epochs,
            "min_positives": args.min_positives,
            "batch_size": args.batch_size,
            "device": args.device,
            "heads_checkpoint": str(heads_path),
            "summary": summary,
        })

    ranked_rows = sorted(
        trial_rows,
        key=lambda row: (
            math.isinf(float(row["summary"]["objective_median_val_loss"])),
            float(row["summary"]["objective_median_val_loss"]),
        ),
    )

    best_trial = ranked_rows[0] if ranked_rows else None

    payload = {
        "data_root": str(data_root),
        "encoder_checkpoint": str(encoder_checkpoint),
        "output_root": str(output_root),
        "species_filter": sorted(species_filter),
        "grid": {
            "head_lr": lr_grid,
            "head_weight_decay": wd_grid,
            "head_epochs": epoch_grid,
        },
        "n_trials": len(ranked_rows),
        "best_trial": best_trial,
        "trials": ranked_rows,
    }

    out_path = Path(args.results_json) if args.results_json else output_root / "sweep_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
