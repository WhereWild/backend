#!/usr/bin/env python3
"""
Project raster tiles/COGs into a canonical grid and emit a tiled COG with overviews.

Examples:
  # Single source file (or a VRT you built)
  python reproject_gis.py --src raw/dem/dem.vrt --dst processed/dem_100m_cog.tif --grid grid.json

  # Directory of GeoTIFF tiles (per-tile logging)
  python reproject_gis.py --src-dir raw/dem --dst processed/dem_100m_cog.tif --grid grid.json --resampling bilinear

  # Explicit list of files (per-tile logging)
  python reproject_gis.py --src-files raw/dem/n40w111.tif raw/dem/n41w111.tif --dst processed/dem_100m_cog.tif
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.shutil import copy as rio_copy
from rasterio.transform import Affine
from rasterio.warp import reproject

# CRS is coordinate reference system; EPSG:5070 is CONUS Albers (meters, equal-area).
DEFAULT_GRID = {
    "crs": "EPSG:5070",
    "pixel_size": 100,  # meters per pixel
    "bounds": [-3100000, 200000, 2900000, 3700000],
    "nodata": -9999,
    "dtype": "float32",
    "align": "target_aligned_pixels",  # snap to exact pixel edges
}

COMPRESS = "deflate"  # lossless compression
BLOCKSIZE = 512       # tile size in pixels


def load_grid(path: Path | None) -> dict:
    if path is None:
        return DEFAULT_GRID
    with path.open() as fp:
        return json.load(fp)


def compute_dimensions(bounds: Sequence[float], pixel_size: float) -> tuple[int, int]:
    xmin, ymin, xmax, ymax = bounds
    width = int(round((xmax - xmin) / pixel_size))
    height = int(round((ymax - ymin) / pixel_size))
    if width <= 0 or height <= 0:
        raise ValueError("Grid bounds/pixel_size produce non-positive dimensions.")
    return width, height


def build_transform(bounds: Sequence[float], pixel_size: float) -> Affine:
    # Affine maps (col,row) -> (x,y). For north-up rasters, b and d are 0.
    xmin, ymin, xmax, ymax = bounds
    return Affine(pixel_size, 0.0, xmin, 0.0, -pixel_size, ymax)


def pick_resampling(name: str) -> Resampling:
    mapping = {
        "nearest": Resampling.nearest,    # categorical
        "bilinear": Resampling.bilinear,  # continuous default
        "cubic": Resampling.cubic,
        "average": Resampling.average,
        "mode": Resampling.mode,
        "lanczos": Resampling.lanczos,
    }
    try:
        return mapping[name.lower()]
    except KeyError:
        raise ValueError(f"Unknown resampling method '{name}'.")


def normalize_sources(src: Path | None, src_dir: Path | None, src_files: list[Path]) -> tuple[list[Path], bool]:
    """
    Returns (list_of_sources, use_single_source_mode).
    Single-source mode = warp once (good for an already-built VRT or single file).
    Multi-source mode = iterate tiles with per-tile logging.
    """
    if src:
        return [src], True
    if src_dir:
        files = sorted(Path(src_dir).glob("*.tif"))
        if not files:
            raise FileNotFoundError(f"No .tif files found in {src_dir}")
        return files, False
    if src_files:
        return src_files, False
    raise ValueError("Provide --src or --src-dir or --src-files.")


def project_onto_grid(
    sources: list[Path],
    use_single_source: bool,
    dst_path: Path,
    grid_path: Path | None = None,
    resampling: str = "bilinear",
    overview_levels: Iterable[int] | None = None,
    write_cog: bool = True,
) -> Path:
    grid = load_grid(grid_path)
    bounds = grid["bounds"]
    px = float(grid["pixel_size"])
    width, height = compute_dimensions(bounds, px)
    transform = build_transform(bounds, px)
    nodata = float(grid.get("nodata", -9999))
    dtype = grid.get("dtype", "float32")
    resample_method = pick_resampling(resampling)
    overviews = list(overview_levels) if overview_levels else []

    tmp_dir = Path(tempfile.mkdtemp(prefix="project_grid_"))
    tmp_tif = tmp_dir / "reprojected.tif"

    with rasterio.Env(GDAL_NUM_THREADS="ALL_CPUS"):
        if use_single_source:
            src_path = sources[0]
            with rasterio.open(src_path) as src:
                if src.crs is None:
                    raise ValueError("Source raster is missing a CRS; assign it before reprojection.")
                profile = {
                    "driver": "GTiff",
                    "height": height,
                    "width": width,
                    "count": src.count,
                    "dtype": dtype,
                    "crs": grid["crs"],
                    "transform": transform,
                    "nodata": nodata,
                    "tiled": True,
                    "blockxsize": BLOCKSIZE,
                    "blockysize": BLOCKSIZE,
                    "compress": COMPRESS,
                    "predictor": 3 if "float" in dtype else 2,  # compression hint
                    "BIGTIFF": "IF_SAFER",
                }
                with rasterio.open(tmp_tif, "w", **profile) as dst:
                    for band_idx in range(1, src.count + 1):
                        print(f"Reprojecting band {band_idx}/{src.count}")
                        reproject(
                            source=rasterio.band(src, band_idx),
                            destination=rasterio.band(dst, band_idx),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            src_nodata=src.nodata,
                            dst_transform=transform,
                            dst_crs=grid["crs"],
                            dst_nodata=nodata,
                            resampling=resample_method,
                        )
                    if overviews:
                        dst.build_overviews(overviews, resampling=resample_method)
                        dst.update_tags(ns="rio_overview", resampling=resample_method.name)
        else:
            # Multi-tile path with per-tile logging
            with rasterio.open(sources[0]) as first:
                if first.crs is None:
                    raise ValueError("Source raster is missing a CRS; assign it before reprojection.")
                profile = {
                    "driver": "GTiff",
                    "height": height,
                    "width": width,
                    "count": first.count,
                    "dtype": dtype,
                    "crs": grid["crs"],
                    "transform": transform,
                    "nodata": nodata,
                    "tiled": True,
                    "blockxsize": BLOCKSIZE,
                    "blockysize": BLOCKSIZE,
                    "compress": COMPRESS,
                    "predictor": 3 if "float" in dtype else 2,
                    "BIGTIFF": "IF_SAFER",
                }
            with rasterio.open(tmp_tif, "w", **profile) as dst:
                # Pre-fill with nodata so untouched areas stay blank
                nodata_arr = np.array(nodata, dtype=dtype)
                for b in range(1, dst.count + 1):
                    for _, window in dst.block_windows(b):
                        dst.write(
                            np.full((window.height, window.width), nodata_arr, dtype=dtype),
                            b,
                            window=window,
                        )
                total = len(sources)
                for idx, tile_path in enumerate(sources, start=1):
                    print(f"[{idx}/{total}] Reprojecting {tile_path.name}")
                    with rasterio.open(tile_path) as src:
                        src_nodata = src.nodata
                        for band_idx in range(1, src.count + 1):
                            reproject(
                                source=rasterio.band(src, band_idx),
                                destination=rasterio.band(dst, band_idx),
                                src_transform=src.transform,
                                src_crs=src.crs,
                                src_nodata=src_nodata,
                                dst_transform=transform,
                                dst_crs=grid["crs"],
                                dst_nodata=nodata,
                                resampling=resample_method,
                                num_threads=0,  # 0 = all cores
                            )
                if overviews:
                    dst.build_overviews(overviews, resampling=resample_method)
                    dst.update_tags(ns="rio_overview", resampling=resample_method.name)

    if write_cog:
        cog_profile = {
            "compress": COMPRESS,
            "blocksize": BLOCKSIZE,
            "bigtiff": "IF_SAFER",
            "copy_src_overviews": True,
        }
        rio_copy(tmp_tif, dst_path, driver="COG", **cog_profile)
    else:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(tmp_tif, dst_path)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return dst_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Project a raster into a canonical grid and emit a COG/GeoTIFF.")
    p.add_argument("--src", type=Path, help="Single source raster/COG (must declare CRS).")
    p.add_argument("--src-dir", type=Path, help="Directory of GeoTIFF/COG tiles (per-tile logging).")
    p.add_argument("--src-files", type=Path, nargs="+", help="Explicit list of GeoTIFF/COG files (per-tile logging).")
    p.add_argument("--dst", type=Path, required=True, help="Destination path for the warped raster.")
    p.add_argument("--grid", type=Path, help="Path to grid.json (defaults to built-in 100 m EPSG:5070 CONUS grid).")
    p.add_argument(
        "--resampling",
        default="bilinear",
        choices=["nearest", "bilinear", "cubic", "average", "mode", "lanczos"],
        help="Resampling method.",
    )
    p.add_argument(
        "--overview-levels",
        type=int,
        nargs="+",
        default=[2, 4, 8, 16, 32],
        help="Overview decimation factors (2 4 8 16 32 ≈ levels 1–5).",
    )
    p.add_argument("--no-cog", dest="write_cog", action="store_false", help="Leave output as tiled GeoTIFF.")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        sources, use_single_source = normalize_sources(args.src, args.src_dir, args.src_files or [])
        out = project_onto_grid(
            sources=sources,
            use_single_source=use_single_source,
            dst_path=args.dst,
            grid_path=args.grid,
            resampling=args.resampling,
            overview_levels=args.overview_levels,
            write_cog=args.write_cog,
        )
        print(f"Wrote {out}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
