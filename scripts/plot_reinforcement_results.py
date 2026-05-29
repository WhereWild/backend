from __future__ import annotations

import argparse
from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory produced by eval_reinforcement.py.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where figs/ and tables/ will be written.",
    )
    parser.add_argument(
        "--n-min-grid",
        type=int,
        nargs="+",
        default=[1, 5, 10, 20],
        help="Threshold steps to summarize from the per-species reinforcement curves.",
    )
    return parser.parse_args()


def _load_learning_curves(input_dir: Path) -> pd.DataFrame:
    per_species_dir = input_dir / "per_species"
    if not per_species_dir.exists():
        raise FileNotFoundError(f"Per-species directory not found: {per_species_dir}")
    csv_paths = sorted(
        path
        for path in per_species_dir.glob("species_*.csv")
        if re.fullmatch(r"species_\d+\.csv", path.name)
    )
    if not csv_paths:
        raise FileNotFoundError(f"No per-species CSVs found in {per_species_dir}")
    frames = [pd.read_csv(path) for path in csv_paths]
    return pd.concat(frames, ignore_index=True)


def _plot_learning_curve(curves: pd.DataFrame, *, metric: str, output_path: Path) -> None:
    mean_curve = curves.groupby("k", as_index=False)[metric].mean().sort_values("k")
    baseline_metric = metric.replace("_reinforced", "_baseline")
    baseline_mean = float(curves.groupby("species_key", as_index=False)[baseline_metric].first()[baseline_metric].mean())

    fig, ax = plt.subplots(figsize=(8, 5))
    for species_key, species_df in curves.groupby("species_key"):
        ordered = species_df.sort_values("k")
        ax.plot(ordered["k"], ordered[metric], color="#4C78A8", linewidth=1.2, alpha=0.25)
    ax.plot(mean_curve["k"], mean_curve[metric], color="#1F1F1F", linewidth=2.8)
    ax.axhline(baseline_mean, color="#D62728", linestyle="--", linewidth=1.6)

    ax.set_xlabel("Feedback step k")
    ax.set_ylabel(metric.replace("_", " ").upper())
    ax.set_title(f"Reinforcement learning curve: {metric.split('_')[0].upper()}")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def _build_threshold_table(curves: pd.DataFrame, n_min_grid: list[int]) -> pd.DataFrame:
    if any(value < 1 for value in n_min_grid):
        raise ValueError("--n-min-grid values must be >= 1.")

    per_species = {
        int(species_key): species_df.sort_values("k").reset_index(drop=True)
        for species_key, species_df in curves.groupby("species_key")
    }
    if not per_species:
        raise ValueError("No per-species learning curves were loaded.")

    baseline_rows = [species_df.iloc[0] for species_df in per_species.values()]
    bce_baseline_mean = float(pd.Series(row["bce_baseline"] for row in baseline_rows).mean())
    auc_baseline_mean = float(pd.Series(row["auc_baseline"] for row in baseline_rows).mean())

    threshold_rows: list[dict[str, float | int]] = []
    for n_min in sorted(set(n_min_grid)):
        sampled_rows = []
        for species_df in per_species.values():
            at_threshold = species_df[species_df["k"] == n_min]
            sampled_rows.append(at_threshold.iloc[0] if not at_threshold.empty else species_df.iloc[-1])
        threshold_rows.append(
            {
                "n_min": n_min,
                "bce_at_step_mean": float(pd.Series(row["bce_reinforced"] for row in sampled_rows).mean()),
                "auc_at_step_mean": float(pd.Series(row["auc_reinforced"] for row in sampled_rows).mean()),
                "bce_baseline_mean": bce_baseline_mean,
                "auc_baseline_mean": auc_baseline_mean,
                "species_count": len(sampled_rows),
            }
        )
    return pd.DataFrame(threshold_rows)


def _plot_threshold_sweep(threshold_table: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True)
    positions = range(len(threshold_table))

    axes[0].bar(positions, threshold_table["bce_at_step_mean"], color="#4C78A8", width=0.7)
    axes[0].axhline(float(threshold_table["bce_baseline_mean"].iloc[0]), color="#D62728", linestyle="--", linewidth=1.6)
    axes[0].set_xticks(list(positions), [str(int(value)) for value in threshold_table["n_min"]])
    axes[0].set_xlabel("n_min threshold")
    axes[0].set_ylabel("Mean held-out BCE")
    axes[0].set_title("BCE At Threshold")
    axes[0].grid(True, axis="y", alpha=0.2)

    axes[1].bar(positions, threshold_table["auc_at_step_mean"], color="#72B7B2", width=0.7)
    axes[1].axhline(float(threshold_table["auc_baseline_mean"].iloc[0]), color="#D62728", linestyle="--", linewidth=1.6)
    axes[1].set_xticks(list(positions), [str(int(value)) for value in threshold_table["n_min"]])
    axes[1].set_xlabel("n_min threshold")
    axes[1].set_ylabel("Mean held-out AUC")
    axes[1].set_title("AUC At Threshold")
    axes[1].grid(True, axis="y", alpha=0.2)

    fig.suptitle("Reinforcement Threshold Sweep")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def main() -> int:
    args = _parse_args()

    curves = _load_learning_curves(args.input_dir)

    figs_dir = args.output_dir / "figs"
    tables_dir = args.output_dir / "tables"
    figs_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    _plot_learning_curve(curves, metric="bce_reinforced", output_path=figs_dir / "learning_curve_bce.png")
    _plot_learning_curve(curves, metric="auc_reinforced", output_path=figs_dir / "learning_curve_auc.png")

    threshold_table = _build_threshold_table(curves, args.n_min_grid)
    threshold_table.to_csv(tables_dir / "threshold_sweep.csv", index=False)
    _plot_threshold_sweep(threshold_table, figs_dir / "threshold_sweep.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())