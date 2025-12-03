#!/usr/bin/env python3
"""Combine species probability rasters into a biodiversity richness surface."""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio


REPO_ROOT = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = REPO_ROOT / "processed" / "predictions"
OUTPUT_PATH = PREDICTIONS_DIR / "biodiversity_richness.tif"
PLOT_PATH = PREDICTIONS_DIR / "biodiversity_richness.png"

# Plot settings mirror scripts/predict_gbt.py for a consistent look.
PLOT_DOWNSAMPLE = 4
PLOT_MAX_NORTHING = 3_200_000
PLOT_MIN_SOUTHING: float | None = None


def list_probability_rasters() -> list[Path]:
    rasters = sorted(PREDICTIONS_DIR.glob("*_probability.tif"))
    if not rasters:
        raise SystemExit(
            f"No probability rasters found under {PREDICTIONS_DIR}. "
            "Run scripts/predict_gbt.py first."
        )
    return rasters


def build_richness_surface() -> Path:
    rasters = list_probability_rasters()
    with ExitStack() as stack:
        datasets = [stack.enter_context(rasterio.open(path)) for path in rasters]
        template = datasets[0]
        profile = template.profile
        profile.update(count=1, dtype="float32", nodata=np.nan, compress="lzw")
        with rasterio.open(OUTPUT_PATH, "w", **profile) as dst:
            for _, window in template.block_windows(1):
                sum_block = np.zeros((window.height, window.width), dtype="float64")
                count_block = np.zeros_like(sum_block)
                for dataset in datasets:
                    data = dataset.read(1, window=window).astype("float64")
                    valid = np.isfinite(data)
                    sum_block += np.where(valid, data, 0.0)
                    count_block += valid.astype("float64")
                block = np.divide(
                    sum_block,
                    count_block,
                    out=np.full_like(sum_block, np.nan),
                    where=count_block > 0,
                )
                dst.write(block.astype("float32"), 1, window=window)
    return OUTPUT_PATH


def plot_richness_raster(raster_path: Path, plot_path: Path) -> Path:
    with rasterio.open(raster_path) as src:
        data = src.read(
            1,
            out_shape=(
                max(1, src.height // PLOT_DOWNSAMPLE),
                max(1, src.width // PLOT_DOWNSAMPLE),
            ),
            resampling=rasterio.enums.Resampling.bilinear,
        ).astype("float32")
        data[data == src.nodata] = np.nan
        bounds = src.bounds
        pixel_height = (bounds.top - bounds.bottom) / data.shape[0]
    if PLOT_MAX_NORTHING is not None or PLOT_MIN_SOUTHING is not None:
        row_centers = np.linspace(
            bounds.top - pixel_height / 2,
            bounds.bottom + pixel_height / 2,
            data.shape[0],
        )
        mask = np.ones_like(row_centers, dtype=bool)
        if PLOT_MAX_NORTHING is not None:
            mask &= row_centers <= PLOT_MAX_NORTHING
        if PLOT_MIN_SOUTHING is not None:
            mask &= row_centers >= PLOT_MIN_SOUTHING
        data[~mask, :] = np.nan
    valid_mask = np.isfinite(data)
    row_mask = np.any(valid_mask, axis=1)
    if not np.any(row_mask):
        return plot_path
    top_idx = row_mask.argmax()
    bottom_idx = len(row_mask) - row_mask[::-1].argmax() - 1
    data = data[top_idx : bottom_idx + 1, :]
    valid_mask = valid_mask[top_idx : bottom_idx + 1, :]
    alpha = np.where(valid_mask, 1.0, 0.0)
    display = np.where(valid_mask, data, 0.0)
    top_bound = bounds.top - top_idx * pixel_height
    bottom_bound = bounds.top - (bottom_idx + 1) * pixel_height
    extent = [bounds.left, bounds.right, bottom_bound, top_bound]
    width = extent[1] - extent[0]
    height = extent[3] - extent[2]
    aspect = width / height if height else 1
    fig_width = 12
    fig_height = max(4, fig_width / max(aspect, 1e-6))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_aspect("equal")
    ax.imshow(
        display,
        origin="upper",
        extent=extent,
        cmap=plt.cm.viridis,
        vmin=0,
        vmax=1,
        alpha=alpha,
    )
    ax.set_axis_off()
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(plot_path, dpi=200, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return plot_path


def main() -> None:
    output_path = build_richness_surface()
    plot_path = plot_richness_raster(output_path, PLOT_PATH)
    rel_raster = output_path.relative_to(REPO_ROOT)
    rel_plot = plot_path.relative_to(REPO_ROOT)
    print(
        f"[DONE] Biodiversity richness raster written to {rel_raster}\n"
        f"[DONE] Richness plot written to {rel_plot}"
    )


if __name__ == "__main__":
    main()
