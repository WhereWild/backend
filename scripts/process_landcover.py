#!/usr/bin/env python3
"""
Warp the NLCD land cover mosaic into the canonical 100 m EPSG:5070 grid.

Output: processed/landcover/landcover_100m_cog.tif (COG when rio-cogeo is around).
The raster keeps the original NLCD integer classes; we resample with nearest
neighbour so categories stay intact.
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
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import numpy as np

try:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import Affine
    from rasterio.warp import reproject
except ModuleNotFoundError as exc:  # pragma: no cover - guard for missing deps
    raise SystemExit(
        "rasterio is required for scripts/process_landcover.py. "
        "Install with `pip install rasterio` or your distro package."
    ) from exc


# NLCD stores classes as uint8; 0 marks background.
LANDCOVER_NODATA = 0


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resample NLCD land cover into the 100 m EPSG:5070 grid."
    )
    parser.add_argument(
        "--grid",
        type=Path,
        required=True,
        help="Path to grid.json (defines bounds, CRS, pixel size).",
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to the raw NLCD GeoTIFF (e.g. raw/landcover/nlcd_2019_land_cover_l48_20210604.tif).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path where the aligned land cover raster will be written.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to manifest CSV for provenance logging.",
    )
    return parser.parse_args(argv)


def load_grid(path: Path) -> Dict[str, Any]:
    """Load the canonical grid JSON so we know CRS + bounds up front."""
    with path.open() as fp:
        grid: Dict[str, Any] = json.load(fp)
    required = {"crs", "pixel_size", "bounds"}
    missing = required - grid.keys()
    if missing:
        raise KeyError(f"grid specification missing keys: {sorted(missing)}")
    return grid


def compute_dimensions(bounds: Sequence[float], pixel_size: float) -> Tuple[int, int]:
    """Translate bounds + pixel size into raster width/height counts."""
    xmin, ymin, xmax, ymax = bounds
    width = int(round((xmax - xmin) / pixel_size))
    height = int(round((ymax - ymin) / pixel_size))
    if width <= 0 or height <= 0:
        raise ValueError("grid bounds / pixel size yield non-positive dimensions.")
    return width, height


def build_transform(bounds: Sequence[float], pixel_size: float) -> Affine:
    """Create the affine transform that maps pixel indices into projected coords."""
    xmin, ymin, xmax, ymax = bounds
    return Affine(pixel_size, 0.0, xmin, 0.0, -pixel_size, ymax)


def fill_with_nodata(dataset: rasterio.io.DatasetWriter, nodata: int) -> None:
    """Prime the destination raster with nodata so empty cells stay at 0."""
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


def convert_to_cog(tmp_tif: Path, output_path: Path, nodata: int) -> Path:
    """Turn the temporary GeoTIFF into a COG when rio-cogeo is installed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from rio_cogeo.cogeo import cog_translate
        try:
            from rio_cogeo.profiles import get_profile
        except ImportError:  # rio-cogeo >=5 swapped helpers
            get_profile = None
            from rio_cogeo.profiles import cog_profiles
    except ModuleNotFoundError:
        print(
            "rio-cogeo not installed; leaving land cover output as a standard GeoTIFF.",
            "Install rio-cogeo for COG-friendly tiling.",
        )
        shutil.move(tmp_tif, output_path)
        return output_path

    if get_profile is not None:
        profile = get_profile("deflate")
    else:
        profile_obj = cog_profiles.get("deflate")
        profile = dict(profile_obj) if profile_obj else {}
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


def append_manifest(manifest_path: Optional[Path], output_path: Path) -> None:
    """Record the processed NLCD raster in the manifest (skip duplicates)."""
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

    record = {
        "dataset": "nlcd_2019_land_cover_100m_epsg5070",
        "source_url": output_path.as_posix(),
        "license": "Public Domain (USGS MRLC)",
        "created_at": dt.datetime.utcnow().date().isoformat(),
        "notes": "NLCD 2019 land cover resampled to WhereWild 100 m grid (nearest).",
    }

    if record["source_url"] in seen_urls:
        return

    with manifest_path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if not manifest_exists:
            writer.writeheader()
        writer.writerow(record)


def process_landcover(grid_path: Path, source_path: Path, output_path: Path) -> Path:
    """Reproject NLCD land cover into the shared grid and emit a (C)OG."""
    grid = load_grid(grid_path)
    bounds = grid["bounds"]
    pixel_size = float(grid["pixel_size"])
    width, height = compute_dimensions(bounds, pixel_size)
    transform = build_transform(bounds, pixel_size)
    crs = grid["crs"]

    tmp_dir = Path(tempfile.mkdtemp(prefix="landcover_"))
    tmp_tif = tmp_dir / "landcover_100m.tif"

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "uint8",
        "crs": crs,
        "transform": transform,
        "nodata": LANDCOVER_NODATA,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "predictor": 2,
        "BIGTIFF": "YES",
    }

    with rasterio.Env(GDAL_NUM_THREADS="ALL_CPUS"):
        with rasterio.open(source_path) as src, rasterio.open(tmp_tif, "w", **profile) as dest:
            fill_with_nodata(dest, LANDCOVER_NODATA)
            print(f"Reprojecting {source_path} -> {tmp_tif} (nearest neighbor)")
            # Nearest neighbour keeps the NLCD class IDs intact (no averaging of categories).
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dest, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=src.nodata if src.nodata is not None else LANDCOVER_NODATA,
                dst_transform=transform,
                dst_crs=crs,
                dst_nodata=LANDCOVER_NODATA,
                resampling=Resampling.nearest,
                num_threads=8,
            )

    final_path = convert_to_cog(tmp_tif, output_path, LANDCOVER_NODATA)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return final_path


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    try:
        result = process_landcover(args.grid, args.source, args.output)
        print(f"Land cover raster written to {result}")
        append_manifest(args.manifest, result)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
