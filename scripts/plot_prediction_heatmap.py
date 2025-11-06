#!/usr/bin/env python3
"""
Render a heatmap of modelled presence probabilities.

Usage example:
    venv/bin/python scripts/plot_prediction_heatmap.py \
        --predictions models/escobaria_vivipara/predictions.parquet \
        --grid grid.json \
        --output figures/predictions/escobaria_vivipara_four_corners.png

Pass --crop to zoom to the valid footprint, or --stride 5 (etc.) to downsample
large rasters when plotting CONUS.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # headless environments
from matplotlib import pyplot as plt  # noqa: E402


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot a presence-probability heatmap.")
    parser.add_argument(
        "--predictions",
        type=Path,
        required=True,
        help="Path to predictions Parquet/CSV with columns grid_x, grid_y, prob_presence.",
    )
    parser.add_argument(
        "--grid",
        type=Path,
        required=True,
        help="Path to grid.json (needed to size the full raster).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output PNG path.",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Optional plot title.",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=5,
        help="Downsampling stride when plotting (default: 5 for full CONUS). Use 1 for no downsample.",
    )
    parser.add_argument(
        "--crop",
        action="store_true",
        help="Crop to the bounding box of valid probabilities instead of plotting the full grid.",
    )
    parser.add_argument(
        "--vmin",
        type=float,
        help="Override colour scale minimum (default: min prob).",
    )
    parser.add_argument(
        "--vmax",
        type=float,
        help="Override colour scale maximum (default: max prob).",
    )
    return parser.parse_args(argv)


def load_grid_spec(path: Path) -> Tuple[float, float, float, float, float]:
    with path.open() as fp:
        spec = json.load(fp)
    bounds = spec["bounds"]
    pixel_size = float(spec["pixel_size"])
    xmin, ymin, xmax, ymax = bounds
    width = int(round((xmax - xmin) / pixel_size))
    height = int(round((ymax - ymin) / pixel_size))
    return xmin, ymin, xmax, ymax, pixel_size, width, height


def load_predictions(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".gz" or path.name.endswith(".csv.gz"):
        return pd.read_csv(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported predictions format: {path}")


def rasterise_predictions(
    df: pd.DataFrame,
    width: int,
    height: int,
) -> np.ndarray:
    arr = np.full((height, width), np.nan, dtype=np.float32)
    required_cols = {"grid_x", "grid_y", "prob_presence"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise KeyError(f"Predictions missing columns: {', '.join(sorted(missing))}")
    x = df["grid_x"].to_numpy(dtype=np.int64, copy=False)
    y = df["grid_y"].to_numpy(dtype=np.int64, copy=False)
    probs = df["prob_presence"].to_numpy(dtype=np.float32, copy=False)
    valid = (
        (x >= 0)
        & (x < width)
        & (y >= 0)
        & (y < height)
        & ~np.isnan(probs)
    )
    arr[y[valid], x[valid]] = probs[valid]
    return arr


def determine_crop(
    arr: np.ndarray,
) -> Tuple[int, int, int, int]:
    mask = ~np.isnan(arr)
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any() or not cols.any():
        return 0, arr.shape[0], 0, arr.shape[1]
    row_indices = np.where(rows)[0]
    col_indices = np.where(cols)[0]
    y_min = int(row_indices[0])
    y_max = int(row_indices[-1]) + 1
    x_min = int(col_indices[0])
    x_max = int(col_indices[-1]) + 1
    return y_min, y_max, x_min, x_max


def downsample(
    arr: np.ndarray,
    stride: int,
) -> np.ndarray:
    if stride <= 1:
        return arr
    return arr[::stride, ::stride]


def render(
    data: np.ndarray,
    output: Path,
    title: Optional[str],
    extent: Optional[Tuple[float, float, float, float]],
    vmin: Optional[float],
    vmax: Optional[float],
) -> None:
    plt.figure(figsize=(10, 6))
    im = plt.imshow(
        data,
        origin="upper",
        cmap="inferno",
        vmin=vmin,
        vmax=vmax,
        extent=extent,
        interpolation="none",
    )
    plt.colorbar(im, label="Presence probability")
    plt.title(title or "Modelled presence probability")
    plt.axis("equal" if extent else "off")
    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=200, bbox_inches="tight")
    plt.close()


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)

    xmin, ymin, xmax, ymax, pixel_size, width, height = load_grid_spec(args.grid)
    preds = load_predictions(args.predictions)
    arr = rasterise_predictions(preds, width, height)

    y_min, y_max, x_min, x_max = (0, height, 0, width)
    if args.crop:
        y_min, y_max, x_min, x_max = determine_crop(arr)

    cropped = arr[y_min:y_max, x_min:x_max]
    if cropped.size == 0 or np.all(np.isnan(cropped)):
        raise ValueError("No valid probabilities to plot.")

    down = downsample(cropped, args.stride)

    if extent := (
        xmin + x_min * pixel_size,
        xmin + x_max * pixel_size,
        ymax - y_max * pixel_size,
        ymax - y_min * pixel_size,
    ):
        pass  # extent computed for imshow (minX, maxX, minY, maxY)

    vmin = args.vmin if args.vmin is not None else float(np.nanmin(down))
    vmax = args.vmax if args.vmax is not None else float(np.nanmax(down))

    render(
        down,
        output=args.output,
        title=args.title,
        extent=extent,
        vmin=vmin,
        vmax=vmax,
    )
    print(f"Saved heatmap -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
