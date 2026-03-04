"""Evaluate species probability calibration from a labeled split.

Computes Brier score and Expected Calibration Error (ECE) for a single species
using the exported inference bundle and a preprocessed parquet split.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow.compute as pc
import pyarrow.dataset as ds

try:
    from util import inference
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from util import inference


@dataclass(frozen=True)
class CalibrationMetrics:
    brier: float
    ece: float
    positive_rate: float
    n_rows: int
    n_positives: int


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for split-level calibration evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate calibration (ECE/Brier) for one species on a split.")
    parser.add_argument("--bundle", required=True, help="Path to exported inference bundle (.pt).")
    parser.add_argument("--data-root", required=True, help="Path to preprocessed partitioned parquet dataset.")
    parser.add_argument("--species-key", required=True, type=int, help="Species key to evaluate.")
    parser.add_argument("--split", default="val", choices=["train", "val", "test"], help="Split to evaluate.")
    parser.add_argument("--bins", default=20, type=int, help="Number of reliability bins (default: 20).")
    parser.add_argument("--batch-size", default=4096, type=int, help="Batch size for inference.predict_batch.")
    parser.add_argument("--max-rows", default=0, type=int, help="Optional cap on evaluated rows (0 = all).")
    parser.add_argument("--output", default="", help="Optional output JSON path.")
    parser.add_argument("--reliability-csv", default="", help="Optional output CSV path for reliability bins.")
    return parser.parse_args()


def load_split_rows(
    data_root: str | Path,
    split: str,
    species_key: int,
    max_rows: int,
) -> tuple[list[tuple[float, float]], np.ndarray, np.ndarray]:
    """Load coordinates, labels, and weights for one species/split slice."""
    dataset = ds.dataset(str(data_root), format="parquet", partitioning="hive")
    filtered = dataset.filter((pc.field("split") == split) & (pc.field("species_key") == species_key))
    table = filtered.to_table(columns=["lat", "lon", "presence_label", "sample_weight"])

    if table.num_rows == 0:
        raise ValueError(f"No rows found for split={split!r}, species_key={species_key}.")

    df = table.to_pandas()
    if max_rows > 0:
        df = df.head(max_rows)

    coords = list(zip(df["lat"].astype(float).to_numpy(), df["lon"].astype(float).to_numpy(), strict=True))
    labels = df["presence_label"].astype(np.float32).to_numpy()
    weights = df["sample_weight"].astype(np.float64).to_numpy()

    return coords, labels, weights


def predict_species_scores(
    coords: list[tuple[float, float]],
    species_key: int,
    batch_size: int,
) -> np.ndarray:
    """Run batched inference and return one probability score per coordinate."""
    all_scores: list[float] = []
    for start in range(0, len(coords), batch_size):
        batch_coords = coords[start : start + batch_size]
        batch_preds = inference.predict_batch(
            batch_coords,
            species_filter=[species_key],
            top_k=0,
            score_threshold=0.0,
        )
        for preds in batch_preds:
            if preds:
                all_scores.append(float(preds[0]["score"]))
            else:
                all_scores.append(0.0)
    return np.asarray(all_scores, dtype=np.float64)


def compute_metrics(
    scores: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
    bins: int,
) -> tuple[CalibrationMetrics, list[dict[str, float | int]]]:
    """Compute weighted Brier/ECE plus per-bin reliability table."""
    if len(scores) != len(labels):
        raise ValueError("scores and labels must have matching lengths")
    if len(scores) == 0:
        raise ValueError("No rows to evaluate")

    labels64 = labels.astype(np.float64)
    w = np.clip(weights.astype(np.float64), 0.0, None)
    if float(w.sum()) == 0.0:
        w = np.ones_like(w)

    brier = float(np.average((scores - labels64) ** 2, weights=w))
    positive_rate = float(np.average(labels64, weights=w))

    bin_edges = np.linspace(0.0, 1.0, bins + 1)
    bin_ids = np.digitize(scores, bin_edges[1:-1], right=False)

    reliability_rows: list[dict[str, float | int]] = []
    ece_accum = 0.0
    total_weight = float(w.sum())

    for bin_idx in range(bins):
        mask = bin_ids == bin_idx
        if not np.any(mask):
            reliability_rows.append({
                "bin": int(bin_idx),
                "lower": float(bin_edges[bin_idx]),
                "upper": float(bin_edges[bin_idx + 1]),
                "count": 0,
                "weight": 0.0,
                "avg_pred": 0.0,
                "empirical_pos_rate": 0.0,
                "abs_gap": 0.0,
                "ece_contrib": 0.0,
            })
            continue

        bw = w[mask]
        weight_sum = float(bw.sum())
        avg_pred = float(np.average(scores[mask], weights=bw))
        emp_pos_rate = float(np.average(labels64[mask], weights=bw))
        abs_gap = abs(avg_pred - emp_pos_rate)
        ece_contrib = (weight_sum / total_weight) * abs_gap
        ece_accum += ece_contrib

        reliability_rows.append({
            "bin": int(bin_idx),
            "lower": float(bin_edges[bin_idx]),
            "upper": float(bin_edges[bin_idx + 1]),
            "count": int(mask.sum()),
            "weight": weight_sum,
            "avg_pred": avg_pred,
            "empirical_pos_rate": emp_pos_rate,
            "abs_gap": abs_gap,
            "ece_contrib": ece_contrib,
        })

    metrics = CalibrationMetrics(
        brier=brier,
        ece=float(ece_accum),
        positive_rate=positive_rate,
        n_rows=int(len(scores)),
        n_positives=int(labels64.sum()),
    )
    return metrics, reliability_rows


def _write_reliability_csv(path: Path, rows: list[dict[str, float | int]]) -> None:
    """Write reliability-bin rows to CSV for plotting/inspection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "bin",
        "lower",
        "upper",
        "count",
        "weight",
        "avg_pred",
        "empirical_pos_rate",
        "abs_gap",
        "ece_contrib",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    """Evaluate calibration metrics and emit JSON/optional CSV artifacts."""
    args = _parse_args()

    inference.load_bundle(args.bundle)
    coords, labels, weights = load_split_rows(
        data_root=args.data_root,
        split=args.split,
        species_key=args.species_key,
        max_rows=args.max_rows,
    )
    scores = predict_species_scores(coords, args.species_key, args.batch_size)
    metrics, reliability_rows = compute_metrics(scores, labels, weights, bins=args.bins)

    payload = {
        "species_key": args.species_key,
        "split": args.split,
        "bundle": str(args.bundle),
        "data_root": str(args.data_root),
        "bins": args.bins,
        "batch_size": args.batch_size,
        "max_rows": args.max_rows,
        "metrics": {
            "n_rows": metrics.n_rows,
            "n_positives": metrics.n_positives,
            "positive_rate": metrics.positive_rate,
            "brier": metrics.brier,
            "ece": metrics.ece,
        },
        "reliability": reliability_rows,
    }

    print(json.dumps(payload, indent=2))

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.reliability_csv:
        _write_reliability_csv(Path(args.reliability_csv), reliability_rows)


if __name__ == "__main__":
    main()
