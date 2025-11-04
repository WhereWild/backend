#!/usr/bin/env python3
"""
Derive slope, aspect, and roughness rasters from the canonical DEM.

The outputs maintain the 100 m EPSG:5070 grid so downstream layers line up
without resampling. Computation iterates over the DEM's internal block windows,
applying the Horn 3x3 gradient kernel for slope/aspect and a simple relief-based
roughness metric (max-min within each 3x3 neighborhood).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import rasterio
from rasterio.windows import Window

DEFAULT_DEM = Path("processed/dem_100m_cog.tif")
DEFAULT_GRID = Path("grid.json")
DEFAULT_OUTPUT_DIR = Path("processed/terrain")
DEFAULT_MANIFEST = Path("manifest.csv")


def load_grid(path: Path) -> Dict[str, float]:
    """Grab grid metadata so we know pixel size for slope calculations."""
    with path.open() as fp:
        import json

        grid = json.load(fp)
    return grid


def create_output_profile(
    base_profile: Dict[str, object],
    dtype: str = "float32",
    nodata: float = -9999.0,
    count: int = 1,
) -> Dict[str, object]:
    """Clone the DEM profile but swap in our own datatype and band count."""
    profile = base_profile.copy()
    profile.update(
        {
            "driver": "GTiff",
            "dtype": dtype,
            "nodata": nodata,
            "count": count,
            "compress": "deflate",
            "predictor": 3,
            "blockxsize": base_profile.get("blockxsize", 512),
            "blockysize": base_profile.get("blockysize", 512),
            "tiled": True,
            "BIGTIFF": "YES",
        }
    )
    return profile


def horn_gradients(block: np.ndarray, cellsize: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute dz/dx and dz/dy using Horn's 3x3 operator.

    Parameters
    ----------
    block : np.ndarray
        2D array that includes a one-pixel padded border on all sides.
    cellsize : float
        Grid spacing in meters.
    """

    z1 = block[:-2, :-2]
    z2 = block[:-2, 1:-1]
    z3 = block[:-2, 2:]
    z4 = block[1:-1, :-2]
    z5 = block[1:-1, 1:-1]
    z6 = block[1:-1, 2:]
    z7 = block[2:, :-2]
    z8 = block[2:, 1:-1]
    z9 = block[2:, 2:]

    dzdx = ((z3 + 2 * z6 + z9) - (z1 + 2 * z4 + z7)) / (8.0 * cellsize)
    dzdy = ((z7 + 2 * z8 + z9) - (z1 + 2 * z2 + z3)) / (8.0 * cellsize)

    return dzdx, dzdy


def compute_metrics(block: np.ndarray, cellsize: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Given a padded block (height+2, width+2) with NaNs marking nodata, compute
    slope (degrees), aspect (degrees), and roughness (max-min).
    """

    dzdx, dzdy = horn_gradients(block, cellsize)

    # Stack 3x3 neighborhood to compute roughness and masks.
    neighborhoods = np.stack(
        [
            block[:-2, :-2],
            block[:-2, 1:-1],
            block[:-2, 2:],
            block[1:-1, :-2],
            block[1:-1, 1:-1],
            block[1:-1, 2:],
            block[2:, :-2],
            block[2:, 1:-1],
            block[2:, 2:],
        ],
        axis=0,
    )

    invalid = np.isnan(neighborhoods).any(axis=0)

    with np.errstate(divide="ignore", invalid="ignore"):
        slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
        aspect = np.degrees(np.arctan2(dzdy, -dzdx))

    # Convert aspect bearing to 0-360 clockwise from north, following GDAL.
    aspect = 90.0 - aspect
    aspect = np.where(aspect < 0.0, aspect + 360.0, aspect)
    aspect = np.where(aspect >= 360.0, aspect - 360.0, aspect)

    # GDAL sets aspect nodata where slope is zero.
    flat = np.isclose(slope, 0.0) | np.isnan(slope)
    aspect = np.where(flat, np.nan, aspect)

    neighborhood_max = np.nanmax(neighborhoods, axis=0)
    neighborhood_min = np.nanmin(neighborhoods, axis=0)
    roughness = neighborhood_max - neighborhood_min

    slope = np.where(invalid, np.nan, slope)
    aspect = np.where(invalid, np.nan, aspect)
    roughness = np.where(invalid, np.nan, roughness)

    return slope.astype(np.float32), aspect.astype(np.float32), roughness.astype(np.float32)


def expand_window(window: Window, padding: int = 1) -> Window:
    """Grow a Rasterio window by `padding` cells on all sides."""
    return Window(
        col_off=window.col_off - padding,
        row_off=window.row_off - padding,
        width=window.width + 2 * padding,
        height=window.height + 2 * padding,
    )


def write_block(
    dataset: rasterio.io.DatasetWriter,
    band_index: int,
    data: np.ndarray,
    window: Window,
    nodata: float,
) -> None:
    """Write a single block to disk, swapping NaNs for the nodata sentinel."""
    filled = np.where(np.isnan(data), nodata, data).astype(np.float32, copy=False)
    dataset.write(filled, band_index, window=window)


def derive_terrain(
    dem_path: Path,
    grid_path: Path,
    output_dir: Path,
    manifest_path: Optional[Path] = None,
) -> Dict[str, Path]:
    """Main driver: loop over DEM blocks, compute metrics, write outputs, log manifest."""
    grid = load_grid(grid_path)
    cellsize = float(grid["pixel_size"])

    output_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.Env(GDAL_NUM_THREADS="ALL_CPUS"):
        with rasterio.open(dem_path) as src:
            base_profile = create_output_profile(src.profile, count=4)
            nodata = float(base_profile["nodata"])
            dem_nodata = src.nodata if src.nodata is not None else nodata

            stack_path = output_dir / "terrain_stack.tif"
            stack_ds = rasterio.open(stack_path, "w", **base_profile)
            stack_ds.set_band_description(1, "elevation")
            stack_ds.set_band_description(2, "slope_deg")
            stack_ds.set_band_description(3, "aspect_deg")
            stack_ds.set_band_description(4, "roughness")

            try:
                total_blocks = sum(1 for _ in src.block_windows(1))
                for idx, (block_index, window) in enumerate(src.block_windows(1), start=1):
                    print(f"[{idx}/{total_blocks}] Processing block {block_index}", flush=True)
                    # Pull a padded block so Horn's kernel has neighbors along the edges.
                    padded_window = expand_window(window, padding=1)
                    block = src.read(
                        1,
                        window=padded_window,
                        boundless=True,
                        fill_value=nodata,
                    ).astype(np.float32, copy=False)

                    # Raster math is easier when nodata becomes NaN.
                    block[block == nodata] = np.nan

                    slope_block, aspect_block, roughness_block = compute_metrics(block, cellsize)

                    # Write the original DEM values alongside the derived metrics.
                    dem_block = src.read(1, window=window).astype(np.float32, copy=False)
                    dem_block = np.where(dem_block == dem_nodata, np.nan, dem_block)

                    write_block(stack_ds, 1, dem_block, window, nodata)
                    write_block(stack_ds, 2, slope_block, window, nodata)
                    write_block(stack_ds, 3, aspect_block, window, nodata)
                    write_block(stack_ds, 4, roughness_block, window, nodata)
            finally:
                stack_ds.close()

    legacy_files = [
        output_dir / "slope_deg.tif",
        output_dir / "aspect_deg.tif",
        output_dir / "roughness.tif",
    ]
    for legacy in legacy_files:
        try:
            legacy.unlink()
        except FileNotFoundError:
            pass
        # If removal succeeds we stay quiet—these files were transitional outputs.
        else:
            print(f"Removed outdated single-band file: {legacy}")

    artifact_paths = {
        "stack": stack_path,
    }
    append_manifest(manifest_path, artifact_paths)
    return artifact_paths


def append_manifest(manifest_path: Optional[Path], artifacts: Dict[str, Path]) -> None:
    """Record the terrain stack in the project manifest (unless we're told not to)."""
    if manifest_path is None:
        return

    fieldnames = ["dataset", "source_url", "license", "created_at", "notes"]
    manifest_exists = manifest_path.exists()

    seen_urls = set()
    if manifest_exists:
        with manifest_path.open(newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                if "source_url" in row:
                    seen_urls.add(row["source_url"])

    created_at = dt.datetime.now(dt.timezone.utc).date().isoformat()
    rows = [
        {
            "dataset": "terrain_stack",
            "source_url": artifacts["stack"].as_posix(),
            "license": "Derived from USGS 3DEP 1 arc-second (Public Domain)",
            "created_at": created_at,
            "notes": "Multi-band stack (elevation, slope, aspect, roughness) derived from WhereWild DEM.",
        }
    ]

    with manifest_path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if not manifest_exists:
            writer.writeheader()
        for row in rows:
            if row["source_url"] in seen_urls:
                continue
            writer.writerow(row)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Derive slope, aspect, and roughness rasters aligned to the WhereWild grid."
    )
    parser.add_argument(
        "--dem",
        type=Path,
        default=DEFAULT_DEM,
        help=f"Path to the canonical DEM raster (default: {DEFAULT_DEM}).",
    )
    parser.add_argument(
        "--grid",
        type=Path,
        default=DEFAULT_GRID,
        help=f"Path to the grid specification JSON (default: {DEFAULT_GRID}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for derived raster outputs (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Manifest CSV for provenance logging (default: {DEFAULT_MANIFEST}).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    try:
        derive_terrain(args.dem, args.grid, args.output_dir, args.manifest)
    except Exception as exc:  # pragma: no cover - CLI safeguard
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
