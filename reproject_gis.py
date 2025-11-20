#!/usr/bin/env python3
"""
Reproject raster(s) onto a canonical grid and emit a COG.
- Preserves per-band nodata and dtype by default.
- Copies overviews if you build them before COG.
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
from rasterio.transform import Affine
from rasterio.warp import reproject

# Minimal defaults; override via --grid JSON.
DEFAULT_GRID = {
    "crs": "EPSG:5070",
    "pixel_size": 100,
    "bounds": [-3100000, 200000, 2900000, 3700000],
    "align": "target_aligned_pixels",
}

COMPRESS = "deflate"
BLOCKSIZE = 512
MAX_WARP_THREADS = 12
WARP_MEM_LIMIT_MB = 4096
CACHEMAX_MB = 4096


def load_grid(path: Path | None) -> dict:
    if path is None:
        return DEFAULT_GRID
    with path.open() as fp:
        return json.load(fp)


def dims(bounds: Sequence[float], px: float) -> tuple[int, int]:
    xmin, ymin, xmax, ymax = bounds
    w = int(round((xmax - xmin) / px))
    h = int(round((ymax - ymin) / px))
    if w <= 0 or h <= 0:
        raise ValueError("Non-positive output dimensions.")
    return w, h


def transform_from(bounds: Sequence[float], px: float) -> Affine:
    xmin, ymin, xmax, ymax = bounds
    return Affine(px, 0.0, xmin, 0.0, -px, ymax)


def resampling_from(name: str) -> Resampling:
    m = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
        "average": Resampling.average,
        "mode": Resampling.mode,
        "lanczos": Resampling.lanczos,
    }
    try:
        return m[name.lower()]
    except KeyError:
        raise ValueError(f"Unknown resampling '{name}'")


def resolve_src_nodata(src: rasterio.io.DatasetReader, override: float | None) -> float | None:
    if override is not None:
        return float(override)
    if src.nodata is not None:
        return float(src.nodata)
    if src.nodatavals:
        for v in src.nodatavals:
            if v is not None:
                return float(v)
    return None  # Caller may require it


def enforce_per_band_nodata(path: Path, nodata: float | None) -> None:
    """Set per-band nodata using GDAL to keep metadata consistent across stacks."""
    if nodata is None:
        return
    from osgeo import gdal

    gdal.UseExceptions()
    ds = gdal.Open(str(path), gdal.GA_Update)
    if ds is None:
        raise RuntimeError(f"GDAL failed to open {path} to set nodata")
    try:
        for i in range(1, ds.RasterCount + 1):
            band = ds.GetRasterBand(i)
            band.SetNoDataValue(float(nodata))
        ds.FlushCache()
    finally:
        ds = None


def verify_per_band_nodata(path: Path, nodata: float | None) -> None:
    if nodata is None:
        return
    from osgeo import gdal

    gdal.UseExceptions()
    ds = gdal.Open(str(path), gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"GDAL failed to open {path} to verify nodata")
    missing, mismatched = [], []
    try:
        for i in range(1, ds.RasterCount + 1):
            band = ds.GetRasterBand(i)
            v = band.GetNoDataValue()
            if v is None:
                missing.append(i)
            elif not np.isclose(v, nodata):
                mismatched.append(i)
    finally:
        ds = None
    if missing or mismatched:
        raise RuntimeError(f"{path} nodata check failed (missing {missing}, mismatched {mismatched})")


def to_cog(src: Path, dst: Path, nodata: float | None) -> None:
    from osgeo import gdal

    gdal.UseExceptions()
    opts = gdal.TranslateOptions(
        format="COG",
        creationOptions=[
            f"COMPRESS={COMPRESS.upper()}",
            f"BLOCKSIZE={BLOCKSIZE}",
            "BIGTIFF=YES",
        ],
        noData=(None if nodata is None else float(nodata)),
    )
    dst.unlink(missing_ok=True)
    ds = gdal.Open(str(src))
    if ds is None:
        raise RuntimeError(f"GDAL failed to open {src} for COG")
    try:
        gdal.Translate(str(dst), ds, options=opts)
    finally:
        ds = None


def collect_sources(src: Path | None, src_dir: Path | None, src_files: list[Path]) -> tuple[list[Path], bool]:
    if src:
        return [src], True
    if src_dir:
        files = sorted(Path(src_dir).glob("*.tif"))
        if not files:
            raise FileNotFoundError(f"No .tif in {src_dir}")
        return files, False
    if src_files:
        return src_files, False
    raise ValueError("Provide --src or --src-dir or --src-files.")


def reproject_to_grid(
    sources: list[Path],
    use_single_source: bool,
    dst_path: Path,
    grid_path: Path | None,
    pixel_size_override: float | None,
    src_nodata_override: float | None,
    resampling: str,
    overview_levels: Iterable[int],
    write_cog: bool,
) -> Path:
    grid = load_grid(grid_path)
    bounds = grid["bounds"]
    px = float(pixel_size_override if pixel_size_override is not None else grid["pixel_size"])
    width, height = dims(bounds, px)
    dst_transform = transform_from(bounds, px)
    dst_crs = grid["crs"]
    resample = resampling_from(resampling)

    tmpdir = Path(tempfile.mkdtemp(prefix="reproj_"))
    tmp_tif = tmpdir / "out.tif"

    with rasterio.Env(GDAL_NUM_THREADS="ALL_CPUS", GDAL_CACHEMAX=CACHEMAX_MB):
        # Inspect first source for dtype/count; we do not up/downcast unless explicitly asked.
        with rasterio.open(sources[0]) as first:
            if first.crs is None:
                raise ValueError("Source missing CRS")
            band_count = first.count
            dtype = first.dtypes[0]
            src_nodata = resolve_src_nodata(first, src_nodata_override)

        profile = {
            "driver": "GTiff",
            "height": height,
            "width": width,
            "count": band_count,
            "dtype": dtype,
            "crs": dst_crs,
            "transform": dst_transform,
            "tiled": True,
            "blockxsize": BLOCKSIZE,
            "blockysize": BLOCKSIZE,
            "compress": COMPRESS,
            "predictor": 3 if "float" in dtype else 2,
            "BIGTIFF": "YES",
            # Do not set nodata at write-time if unknown; we’ll enforce per-band with GDAL below.
            "nodata": src_nodata,
        }

        with rasterio.open(tmp_tif, "w", **profile) as dst:
            if use_single_source:
                with rasterio.open(sources[0]) as src:
                    s_nodata = resolve_src_nodata(src, src_nodata_override)
                    for b in range(1, band_count + 1):
                        reproject(
                            source=rasterio.band(src, b),
                            destination=rasterio.band(dst, b),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            src_nodata=s_nodata,
                            dst_transform=dst_transform,
                            dst_crs=dst_crs,
                            dst_nodata=s_nodata,
                            resampling=resample,
                            init_dest_nodata=True,
                            num_threads=MAX_WARP_THREADS,
                            warp_mem_limit=WARP_MEM_LIMIT_MB,
                        )
            else:
                # Simple tile stack into common grid; later tiles overwrite on overlaps.
                for tile in sources:
                    with rasterio.open(tile) as src:
                        if src.count != band_count:
                            raise ValueError("Band count mismatch across sources")
                        s_nodata = resolve_src_nodata(src, src_nodata_override)
                        for b in range(1, band_count + 1):
                            reproject(
                                source=rasterio.band(src, b),
                                destination=rasterio.band(dst, b),
                                src_transform=src.transform,
                                src_crs=src.crs,
                                src_nodata=s_nodata,
                                dst_transform=dst_transform,
                                dst_crs=dst_crs,
                                dst_nodata=s_nodata,
                                resampling=resample,
                                init_dest_nodata=False,
                                num_threads=MAX_WARP_THREADS,
                                warp_mem_limit=WARP_MEM_LIMIT_MB,
                            )

            # Optional internal overviews; kept when converting to COG with COPY_SRC_OVERVIEWS=YES.
            if overview_levels:
                dst.build_overviews(list(overview_levels), resampling=resample)
                dst.update_tags(ns="rio_overview", resampling=resample.name)

    # Normalize per-band nodata in metadata so COG has identical band flags.
    enforce_per_band_nodata(tmp_tif, src_nodata)
    verify_per_band_nodata(tmp_tif, src_nodata)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    if write_cog:
        to_cog(tmp_tif, dst_path, src_nodata)
        verify_per_band_nodata(dst_path, src_nodata)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return dst_path
    else:
        shutil.move(tmp_tif, dst_path)
        enforce_per_band_nodata(dst_path, src_nodata)
        verify_per_band_nodata(dst_path, src_nodata)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return dst_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reproject raster(s) → canonical grid → COG.")
    p.add_argument("--src", type=Path)
    p.add_argument("--src-dir", type=Path)
    p.add_argument("--src-files", type=Path, nargs="+")
    p.add_argument("--dst", type=Path, required=True)
    p.add_argument("--grid", type=Path, help="JSON with crs, pixel_size, bounds")
    p.add_argument("--pixel-size", type=float)
    p.add_argument("--src-nodata", type=float, help="Explicit nodata if sources lack it")
    p.add_argument("--resampling", default="bilinear")
    p.add_argument("--overview-levels", type=int, nargs="+", default=[])
    p.add_argument("--no-cog", dest="write_cog", action="store_false")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        sources, single = collect_sources(args.src, args.src_dir, args.src_files or [])
        out = reproject_to_grid(
            sources=sources,
            use_single_source=single,
            dst_path=args.dst,
            grid_path=args.grid,
            pixel_size_override=args.pixel_size,
            src_nodata_override=args.src_nodata,
            resampling=args.resampling,
            overview_levels=args.overview_levels,
            write_cog=args.write_cog,
        )
        print(out)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
