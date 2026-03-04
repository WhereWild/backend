"""Fit per-species temperature scaling using a validation split.

This script performs model-level calibration for one species by fitting a
single temperature parameter on validation scores and reporting before/after
metrics on both val and test splits.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

try:
    from scripts.machine_learning.evaluate_calibration import (
        compute_metrics,
        load_split_rows,
        predict_species_scores,
    )
    from util import inference
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from scripts.machine_learning.evaluate_calibration import (
        compute_metrics,
        load_split_rows,
        predict_species_scores,
    )
    from util import inference


def _parse_args() -> argparse.Namespace:
    """Parse CLI flags for bundle path, dataset, target species, and outputs."""
    parser = argparse.ArgumentParser(description="Fit temperature scaling for one species.")
    parser.add_argument("--bundle", required=True, help="Path to exported inference bundle (.pt).")
    parser.add_argument("--data-root", required=True, help="Path to preprocessed partitioned parquet dataset.")
    parser.add_argument("--species-key", required=True, type=int, help="Species key to calibrate.")
    parser.add_argument(
        "--val-split", default="val", choices=["train", "val", "test"], help="Split used to fit temperature."
    )
    parser.add_argument(
        "--eval-split", default="test", choices=["train", "val", "test"], help="Secondary split for holdout evaluation."
    )
    parser.add_argument("--bins", default=20, type=int, help="Number of reliability bins for metrics.")
    parser.add_argument("--batch-size", default=4096, type=int, help="Batch size for inference.predict_batch.")
    parser.add_argument("--max-rows", default=0, type=int, help="Optional cap per split (0 = all).")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    parser.add_argument(
        "--temperature-json",
        default="",
        help="Optional path to write species->temperature map JSON for export/runtime wiring.",
    )
    return parser.parse_args()


def _apply_temperature(scores: np.ndarray, temperature: float) -> np.ndarray:
    """Apply logistic temperature scaling to probability scores."""
    eps = 1e-6
    p = np.clip(scores, eps, 1.0 - eps)
    logits = np.log(p / (1.0 - p))
    scaled = logits / temperature
    return 1.0 / (1.0 + np.exp(-scaled))


def _weighted_bce(scores: np.ndarray, labels: np.ndarray, weights: np.ndarray) -> float:
    """Compute weighted binary cross-entropy used as calibration objective."""
    eps = 1e-8
    p = np.clip(scores, eps, 1.0 - eps)
    y = labels.astype(np.float64)
    w = np.clip(weights.astype(np.float64), 0.0, None)
    if float(w.sum()) == 0.0:
        w = np.ones_like(w)
    losses = -(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
    return float(np.average(losses, weights=w))


def _fit_temperature(scores: np.ndarray, labels: np.ndarray, weights: np.ndarray) -> float:
    """Search for the temperature that minimizes weighted BCE on fit data."""
    coarse = np.logspace(math.log10(0.5), math.log10(20.0), num=81)
    best_t = 1.0
    best_loss = float("inf")

    for t in coarse:
        calibrated = _apply_temperature(scores, float(t))
        loss = _weighted_bce(calibrated, labels, weights)
        if loss < best_loss:
            best_loss = loss
            best_t = float(t)

    fine_lo = max(0.25, best_t / 1.8)
    fine_hi = min(40.0, best_t * 1.8)
    fine = np.linspace(fine_lo, fine_hi, num=121)
    for t in fine:
        calibrated = _apply_temperature(scores, float(t))
        loss = _weighted_bce(calibrated, labels, weights)
        if loss < best_loss:
            best_loss = loss
            best_t = float(t)

    return best_t


def _metrics_payload(scores: np.ndarray, labels: np.ndarray, weights: np.ndarray, bins: int) -> dict[str, float | int]:
    """Build a JSON-serializable metrics payload for one score vector."""
    m, _ = compute_metrics(scores, labels, weights, bins=bins)
    return {
        "n_rows": m.n_rows,
        "n_positives": m.n_positives,
        "positive_rate": m.positive_rate,
        "brier": m.brier,
        "ece": m.ece,
    }


def main() -> None:
    """Fit species temperature on one split and report before/after metrics."""
    args = _parse_args()

    inference.load_bundle(args.bundle)

    val_coords, val_labels, val_weights = load_split_rows(
        data_root=args.data_root,
        split=args.val_split,
        species_key=args.species_key,
        max_rows=args.max_rows,
    )
    eval_coords, eval_labels, eval_weights = load_split_rows(
        data_root=args.data_root,
        split=args.eval_split,
        species_key=args.species_key,
        max_rows=args.max_rows,
    )

    val_scores_raw = predict_species_scores(val_coords, args.species_key, args.batch_size)
    eval_scores_raw = predict_species_scores(eval_coords, args.species_key, args.batch_size)

    temperature = _fit_temperature(val_scores_raw, val_labels, val_weights)
    val_scores_cal = _apply_temperature(val_scores_raw, temperature)
    eval_scores_cal = _apply_temperature(eval_scores_raw, temperature)

    payload = {
        "species_key": args.species_key,
        "bundle": str(args.bundle),
        "data_root": str(args.data_root),
        "temperature": temperature,
        "fit_split": args.val_split,
        "eval_split": args.eval_split,
        "bins": args.bins,
        "max_rows": args.max_rows,
        "metrics": {
            args.val_split: {
                "before": _metrics_payload(val_scores_raw, val_labels, val_weights, args.bins),
                "after": _metrics_payload(val_scores_cal, val_labels, val_weights, args.bins),
            },
            args.eval_split: {
                "before": _metrics_payload(eval_scores_raw, eval_labels, eval_weights, args.bins),
                "after": _metrics_payload(eval_scores_cal, eval_labels, eval_weights, args.bins),
            },
        },
    }

    print(json.dumps(payload, indent=2))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.temperature_json:
        temp_path = Path(args.temperature_json)
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        mapping = {str(args.species_key): float(temperature)}
        temp_path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
