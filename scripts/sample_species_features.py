#!/usr/bin/env python3
"""
Sample raster-derived environmental features for a species presence table.

Given an observation CSV (produced by download_observations.py), this script
projects each record into the canonical grid and pulls elevation, terrain, and
land cover values from the processed rasters. It writes an enriched table plus
basic summary statistics for quick QA.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterable, Optional

try:
    import pandas as pd
except ModuleNotFoundError:
    raise SystemExit(
        "pandas is required for scripts/sample_species_features.py. "
        "Install with `pip install -r requirements.txt`."
    )

import numpy as np
import rasterio
from rasterio.transform import xy


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sample elevation / terrain / land cover values for species observations."
    )
    parser.add_argument(
        "--observations",
        type=Path,
        required=True,
        help="Path to presence CSV (e.g., processed/observations/<species>/<species>_presence_*.csv.gz).",
    )
    parser.add_argument(
        "--processed-root",
        type=Path,
        default=Path("processed"),
        help="Root processed directory containing dem, terrain, landcover rasters (default: processed).",
    )
    parser.add_argument(
        "--dem",
        type=Path,
        help="Override DEM raster path (default: processed/dem_100m_cog.tif).",
    )
    parser.add_argument(
        "--terrain",
        type=Path,
        help="Override terrain stack path (default: processed/terrain/terrain_stack.tif).",
    )
    parser.add_argument(
        "--landcover",
        type=Path,
        help="Override land cover raster path (default: processed/landcover/landcover_100m_cog.tif).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output CSV/Parquet path for enriched observations (default: alongside input, *_features.csv.gz).",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        help="Optional JSON summary output (default: *_summary.json next to output).",
    )
    parser.add_argument(
        "--parquet",
        action="store_true",
        help="Write the enriched table as Parquet instead of CSV (requires pyarrow).",
    )
    return parser.parse_args(argv)


def load_presence_table(path: Path) -> pd.DataFrame:
    print(f"Loading observations from {path}")
    df = pd.read_csv(path)
    required = {"grid_x", "grid_y"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Observation table missing columns: {sorted(missing)}")
    df["grid_x"] = df["grid_x"].astype(int)
    df["grid_y"] = df["grid_y"].astype(int)
    df["cell_id"] = df["grid_x"].astype(str) + "_" + df["grid_y"].astype(str)
    df["presence"] = 1
    return df


def sample_raster(dataset: rasterio.io.DatasetReader, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    samples = np.array(list(dataset.sample(zip(xs, ys))))
    if dataset.count == 1:
        samples = samples.reshape(-1)
    else:
        samples = samples.reshape(-1, dataset.count)
    nodata = dataset.nodata
    if nodata is not None:
        samples = np.where(np.isclose(samples, nodata), np.nan, samples)
    return samples


def enrich_with_features(
    df: pd.DataFrame,
    dem_path: Path,
    terrain_path: Path,
    landcover_path: Optional[Path],
) -> pd.DataFrame:
    rows = df["grid_y"].to_numpy()
    cols = df["grid_x"].to_numpy()

    with rasterio.open(dem_path) as dem_ds:
        xs, ys = xy(dem_ds.transform, rows, cols, offset="center")
        xs = np.array(xs)
        ys = np.array(ys)
        dem_samples = sample_raster(dem_ds, xs, ys)
        df["elevation_m"] = dem_samples.astype(np.float32)

    with rasterio.open(terrain_path) as terrain_ds:
        terrain_samples = sample_raster(terrain_ds, xs, ys)
        if terrain_samples.ndim != 2 or terrain_samples.shape[1] < 4:
            raise ValueError("Terrain stack must have at least four bands (elevation, slope, aspect, roughness).")
        df["slope_deg"] = terrain_samples[:, 1].astype(np.float32)
        df["aspect_deg"] = terrain_samples[:, 2].astype(np.float32)
        df["roughness"] = terrain_samples[:, 3].astype(np.float32)

    if landcover_path is not None and landcover_path.exists():
        with rasterio.open(landcover_path) as lc_ds:
            lc_samples = sample_raster(lc_ds, xs, ys)
            nodata = lc_ds.nodata
            if nodata is not None:
                lc_samples = np.where(np.isclose(lc_samples, nodata), np.nan, lc_samples)
            df["landcover_class"] = lc_samples.astype(np.float32)
    else:
        print("Land cover raster not found; filling landcover_class with NaN.")
        df["landcover_class"] = np.nan

    if "observed_at" in df.columns:
        observed_dt = pd.to_datetime(df["observed_at"], errors="coerce", utc=True)
        df["observed_at"] = observed_dt.dt.tz_localize(None)
        df["observed_month"] = df["observed_at"].dt.month
    else:
        df["observed_month"] = np.nan

    # Ensure phenology columns exist even if missing in the raw table
    for col in ["phenology_budding", "phenology_flowering", "phenology_fruiting", "phenology_stage"]:
        if col not in df.columns:
            df[col] = np.nan

    return df


def write_outputs(df: pd.DataFrame, output_path: Path, summary_path: Optional[Path], as_parquet: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if as_parquet:
        try:
            df.to_parquet(output_path, index=False)
        except Exception as exc:
            raise SystemExit(f"Failed to write Parquet output: {exc}") from exc
    else:
        df.to_csv(output_path, index=False)
    print(f"Wrote enriched observations -> {output_path}")

    numeric_cols = ["elevation_m", "slope_deg", "aspect_deg", "roughness"]
    summary = {
        "count": len(df),
        "numeric_summary": df[numeric_cols].describe().to_dict(),
        "landcover_value_counts": df["landcover_class"].value_counts(dropna=True).to_dict(),
    }

    phenology_cols = ["phenology_budding", "phenology_flowering", "phenology_fruiting"]
    if all(col in df.columns for col in phenology_cols):
        phenology_counts = {}
        for col in phenology_cols:
            phenology_counts[col] = float(df[col].sum(skipna=True))

        phenology_monthly: dict[str, dict[str, dict[str, float]]] = {}
        if "observed_month" in df.columns:
            month_df = df.dropna(subset=["observed_month"])
            if not month_df.empty:
                for col in phenology_cols:
                    grouped = (
                        month_df.groupby("observed_month")[col]
                        .agg(["count", "mean"])
                        .reindex(range(1, 13), fill_value=0)
                    )
                    phenology_monthly[col] = {
                        str(int(month)): {
                            "count": int(row["count"]),
                            "rate": float(row["mean"]),
                        }
                        for month, row in grouped.iterrows()
                    }

        summary["phenology_summary"] = {
            "totals": phenology_counts,
            "monthly": phenology_monthly,
        }

    if summary_path is None:
        summary_path = output_path.with_name(output_path.stem + "_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote summary statistics -> {summary_path}")


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    df = load_presence_table(args.observations)

    processed_root = args.processed_root
    dem_path = args.dem or processed_root / "dem_100m_cog.tif"
    terrain_path = args.terrain or processed_root / "terrain" / "terrain_stack.tif"
    landcover_path = args.landcover or processed_root / "landcover" / "landcover_100m_cog.tif"

    if not dem_path.exists():
        raise FileNotFoundError(f"DEM raster not found: {dem_path}")
    if not terrain_path.exists():
        raise FileNotFoundError(f"Terrain stack not found: {terrain_path}")

    enrich_with_features(df, dem_path, terrain_path, landcover_path if landcover_path.exists() else None)

    default_output = args.observations.with_name(args.observations.stem.replace("_presence", "_features") + ".csv.gz")
    output_path = args.output or default_output
    summary_path = args.summary

    write_outputs(df, output_path, summary_path, as_parquet=args.parquet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
