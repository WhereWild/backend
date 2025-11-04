#!/usr/bin/env python3
"""
Generate the canonical 100 m EPSG:5070 DEM mosaic from cached 3DEP tiles.

Flow:
  1. Read grid specification (pixel size, bounds, CRS, nodata, dtype) from grid.json.
  2. Discover GeoTIFF tiles under raw/dem/.
  3. Reproject each tile into the target grid and accumulate into a single raster.
  4. Write a compressed GeoTIFF (or COG if rio-cogeo is available).
  5. Append provenance metadata to manifest.csv.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import Affine
    from rasterio.warp import reproject
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "rasterio is required for scripts/process_elevation.py. "
        "Install with `pip install rasterio` or the equivalent package for your distro."
    ) from exc


def load_grid(path: Path) -> Dict[str, Any]:
    with path.open() as fp:
        grid: Dict[str, Any] = json.load(fp)

    required = {"crs", "pixel_size", "bounds"}
    missing = required - grid.keys()
    if missing:
        raise KeyError(f"grid specification missing keys: {sorted(missing)}")
    return grid


def compute_dimensions(bounds: Sequence[float], pixel_size: float) -> Tuple[int, int]:
    xmin, ymin, xmax, ymax = bounds
    width = int(round((xmax - xmin) / pixel_size))
    height = int(round((ymax - ymin) / pixel_size))
    if width <= 0 or height <= 0:
        raise ValueError("grid bounds / pixel size yield non-positive dimensions.")
    return width, height


def build_transform(bounds: Sequence[float], pixel_size: float) -> Affine:
    xmin, ymin, xmax, ymax = bounds
    return Affine(pixel_size, 0.0, xmin, 0.0, -pixel_size, ymax)


def iter_dem_tiles(raw_dir: Path) -> List[Path]:
    tiles = sorted(raw_dir.glob("*.tif"))
    if not tiles:
        raise FileNotFoundError(
            f"No DEM tiles found in {raw_dir}. "
            "Run `make download-dem` before generating the mosaic."
        )
    return tiles


def infer_src_nodata(src: rasterio.DatasetReader) -> float:
    if src.nodata is not None:
        return float(src.nodata)
    # USGS 3DEP 1 arc-second typically uses -32767 / -32768 as nodata.
    return -32767.0


def fill_dataset_with_nodata(dataset: rasterio.io.DatasetWriter, nodata: float) -> None:
    band_index = 1
    dtype = dataset.dtypes[band_index - 1]
    nodata_arr = np.array(nodata, dtype=dtype)
    for _, window in dataset.block_windows(band_index):
        block = np.full(
            (window.height, window.width),
            nodata_arr,
            dtype=dtype,
        )
        dataset.write(block, indexes=band_index, window=window)


def mosaic_tiles(
    tiles: Sequence[Path],
    output_path: Path,
    grid: Dict[str, Any],
) -> Path:
    bounds = grid["bounds"]
    pixel_size = float(grid["pixel_size"])
    width, height = compute_dimensions(bounds, pixel_size)
    transform = build_transform(bounds, pixel_size)
    crs = grid["crs"]
    nodata = float(grid.get("nodata", -9999))
    dtype = np.dtype(grid.get("dtype", "float32")).name

    tmp_dir = Path(tempfile.mkdtemp(prefix="dem_mosaic_"))
    tmp_tif = tmp_dir / "dem_100m.tif"

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": dtype,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "predictor": 3 if "float" in dtype else 2,
        "BIGTIFF": "YES",
    }

    print(f"Creating intermediate mosaic: {tmp_tif}")
    with rasterio.Env(GDAL_NUM_THREADS="ALL_CPUS"):
        with rasterio.open(tmp_tif, "w", **profile) as dest:
            fill_dataset_with_nodata(dest, nodata)
            total = len(tiles)
            for idx, tile_path in enumerate(tiles, start=1):
                print(f"[{idx}/{total}] Reprojecting {tile_path.name}")
                with rasterio.open(tile_path) as src:
                    src_nodata = infer_src_nodata(src)
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dest, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        src_nodata=src_nodata,
                        dst_transform=transform,
                        dst_crs=crs,
                        dst_nodata=nodata,
                        resampling=Resampling.bilinear,
                        num_threads=12,
                        warp_mem_limit=4096,
                        init_dest_nodata=False,
                    )

    final_path = convert_to_cog(tmp_tif, output_path, nodata)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return final_path


def convert_to_cog(tmp_tif: Path, output_path: Path, nodata: float) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from rio_cogeo.cogeo import cog_translate
        try:
            from rio_cogeo.profiles import get_profile
        except ImportError:  # rio-cogeo >=5 removed get_profile helper
            get_profile = None
            from rio_cogeo.profiles import cog_profiles
    except ModuleNotFoundError:
        print(
            "rio-cogeo not installed; leaving output as standard GeoTIFF.",
            "Install rio-cogeo for cloud-optimized output.",
        )
        shutil.move(tmp_tif, output_path)
        return output_path

    print(f"Converting to Cloud Optimized GeoTIFF: {output_path}")
    if get_profile is not None:
        profile = get_profile("deflate")
    else:
        profile_obj = cog_profiles.get("deflate")
        if profile_obj is None:
            profile = {}
        else:
            profile = dict(profile_obj)
    profile.update({"nodata": nodata})
    cog_translate(
        str(tmp_tif),
        str(output_path),
        profile,
        in_memory=False,
        quiet=True,
    )
    tmp_tif.unlink(missing_ok=True)
    return output_path


def append_manifest(manifest_path: Path, output_path: Path) -> None:
    if manifest_path is None:
        return

    fieldnames = ["dataset", "source_url", "license", "created_at", "notes"]
    manifest_exists = manifest_path.exists()
    existing_urls = set()
    if manifest_exists:
        with manifest_path.open(newline="") as fp:
            reader = csv.DictReader(fp)
            existing_urls = {row["source_url"] for row in reader if "source_url" in row}

    record = {
        "dataset": "dem_100m_epsg5070",
        "source_url": output_path.as_posix(),
        "license": "Derived from USGS 3DEP 1 arc-second (Public Domain)",
        "created_at": dt.datetime.utcnow().date().isoformat(),
        "notes": "Mosaicked DEM aligned to WhereWild 100 m grid",
    }

    if record["source_url"] in existing_urls:
        return

    with manifest_path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if not manifest_exists:
            writer.writeheader()
        writer.writerow(record)


def process_elevation(
    grid_path: Path,
    raw_dir: Path,
    output_path: Path,
    manifest_path: Optional[Path] = None,
) -> Path:
    grid = load_grid(grid_path)
    tiles = iter_dem_tiles(raw_dir)
    print(f"Found {len(tiles)} tiles in {raw_dir}")
    result = mosaic_tiles(tiles, output_path, grid)
    print(f"DEM mosaic written to {result}")
    if manifest_path:
        append_manifest(manifest_path, result)
        print(f"Manifest updated with {result}")
    return result


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Warp raw DEM tiles to the canonical 100 m EPSG:5070 grid."
    )
    parser.add_argument("--grid", type=Path, required=True, help="Path to grid.json.")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        required=True,
        help="Directory containing raw DEM tiles (GeoTIFF).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination DEM (GeoTIFF/COG).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to manifest CSV for provenance tracking.",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    try:
        process_elevation(args.grid, args.raw_dir, args.output, args.manifest)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
