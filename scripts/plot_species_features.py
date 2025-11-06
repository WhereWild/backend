#!/usr/bin/env python3
"""Plot distribution summaries for species feature tables."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    import pandas as pd
except ModuleNotFoundError:
    raise SystemExit(
        "pandas is required for scripts/plot_species_features.py. "
        "Install with `pip install -r requirements.txt`."
    )

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

NLCD_CLASSES = {
    11: "Open Water",
    12: "Perennial Ice/Snow",
    21: "Developed, Open Space",
    22: "Developed, Low Intensity",
    23: "Developed, Medium Intensity",
    24: "Developed, High Intensity",
    31: "Barren Land",
    41: "Deciduous Forest",
    42: "Evergreen Forest",
    43: "Mixed Forest",
    51: "Dwarf Scrub",
    52: "Shrub/Scrub",
    71: "Grassland/Herbaceous",
    72: "Sedge/Herbaceous",
    73: "Lichens",
    74: "Moss",
    81: "Pasture/Hay",
    82: "Cultivated Crops",
    90: "Woody Wetlands",
    95: "Herbaceous Wetlands",
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot elevation/slope/roughness distributions for a species feature table."
    )
    parser.add_argument(
        "--features",
        type=Path,
        required=True,
        help="Path to features CSV/Parquet (from sample_species_features.py).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory to save plots (default: show interactively).",
    )
    parser.add_argument(
        "--format",
        choices={"png", "pdf"},
        default="png",
        help="Output format when saving plots (default: png).",
    )
    parser.add_argument(
        "--kde",
        action="store_true",
        help="Add a KDE curve on top of the histogram/kde plot.",
    )
    parser.add_argument(
        "--phenology",
        action="store_true",
        help="Generate bloom/fruiting/budding monthly bar charts when phenology columns exist.",
    )
    return parser.parse_args(argv)


def load_features(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.endswith("gz") or path.suffix == ".csv":
        return pd.read_csv(path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported features file format: {path}")


def plot_distribution(df: pd.DataFrame, column: str, kde: bool, title: str, output_path: Path | None) -> None:
    plt.figure(figsize=(8, 6))
    sns.histplot(df[column].dropna(), kde=kde, stat="density", bins=40, color="steelblue", alpha=0.7)
    plt.title(title)
    plt.xlabel(column)
    plt.ylabel("Density")
    plt.grid(True, linestyle="--", alpha=0.4)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close()
        print(f"Saved {output_path}")
    else:
        plt.show()


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    df = load_features(args.features)
    if "aspect_deg" in df.columns:
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        aspect_mod = np.nan_to_num((df["aspect_deg"] % 360).to_numpy(), nan=0.0)
        idx = np.floor((aspect_mod + 22.5) / 45.0).astype(int) % 8
        df["aspect_compass"] = pd.Categorical([directions[i] for i in idx], categories=directions, ordered=True)

    if "landcover_class" in df.columns:
        df["landcover_label"] = df["landcover_class"].map(NLCD_CLASSES)

    numeric_cols = [
        col
        for col in ["elevation_m", "slope_deg", "roughness", "soil_sand_pct", "soil_silt_pct", "soil_clay_pct"]
        if col in df.columns
    ]
    if not numeric_cols:
        raise ValueError("No numeric feature columns found. Expected columns like elevation_m, slope_deg, roughness.")

    output_dir = args.output_dir
    for col in numeric_cols:
        title = f"{col} distribution"
        output_path = None
        if output_dir:
            output_path = output_dir / f"{Path(args.features).stem}_{col}.{args.format}"
        plot_distribution(df, col, kde=args.kde, title=title, output_path=output_path)

    if "aspect_compass" in df.columns:
        plt.figure(figsize=(8, 6))
        sns.countplot(x="aspect_compass", data=df, order=["N", "NE", "E", "SE", "S", "SW", "W", "NW"], color="steelblue")
        plt.title("Aspect (cardinal bins)")
        plt.xlabel("Aspect bin")
        plt.ylabel("Count")
        plt.grid(True, axis="y", linestyle="--", alpha=0.4)
        if output_dir:
            path = output_dir / f"{Path(args.features).stem}_aspect_bins.{args.format}"
            path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(path, dpi=200, bbox_inches="tight")
            print(f"Saved {path}")
        else:
            plt.show()
        plt.close()

    if "landcover_label" in df.columns:
        plt.figure(figsize=(10, 6))
        sns.countplot(y="landcover_label", data=df, order=df["landcover_label"].value_counts().index, color="slateblue")
        plt.title("Land cover classes")
        plt.xlabel("Count")
        plt.ylabel("Land cover")
        plt.grid(True, axis="x", linestyle="--", alpha=0.4)
        if output_dir:
            path = output_dir / f"{Path(args.features).stem}_landcover.{args.format}"
            path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(path, dpi=200, bbox_inches="tight")
            print(f"Saved {path}")
        else:
            plt.show()
        plt.close()

    if args.phenology and "observed_month" in df.columns:
        month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_index = range(1, 13)

        for col in ["phenology_budding", "phenology_flowering", "phenology_fruiting"]:
            if col not in df.columns:
                continue
            subset = df.dropna(subset=[col, "observed_month"])
            if subset.empty:
                rates = pd.Series(0.0, index=month_index)
                counts = pd.Series(0, index=month_index)
            else:
                rates = (
                    subset.groupby("observed_month")[col]
                    .apply(lambda s: s.astype(float).mean())
                    .reindex(month_index, fill_value=0.0)
                )
                counts = (
                    subset.groupby("observed_month")[col]
                    .count()
                    .reindex(month_index, fill_value=0)
                )
            plt.figure(figsize=(10, 4))
            sns.barplot(x=month_labels, y=rates.values, color="coral")
            plt.title(f"{col.replace('phenology_', '').capitalize()} rate by month")
            plt.ylabel("Proportion of observations")
            plt.xlabel("Month")
            for idx, (rate, count) in enumerate(zip(rates.values, counts.values)):
                plt.text(idx, rate + 0.01, f"n={int(count)}", ha="center", va="bottom", fontsize=8)
            plt.ylim(0, 1)
            plt.grid(True, axis="y", linestyle="--", alpha=0.3)
            if output_dir:
                path = output_dir / f"{Path(args.features).stem}_{col}_phenology.{args.format}"
                path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(path, dpi=200, bbox_inches="tight")
                print(f"Saved {path}")
            else:
                plt.show()
            plt.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
