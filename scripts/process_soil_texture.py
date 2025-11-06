#!/usr/bin/env python3
"""
Resample multi-band soil texture rasters (sand / silt / clay percentages)
into the canonical 100 m EPSG:5070 grid used across the project.

Expected inputs are three GeoTIFFs representing percentage content for the
same depth interval (e.g., SoilGrids 0-5 cm sand, silt, clay rasters). Place
them under raw/soil_texture or pass explicit paths via the CLI flags.
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
from typing import Dict, Iterable, Optional, Sequence, Tuple

import numpy as np

try:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import Affine
    from rasterio.warp import reproject
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "rasterio is required for scripts/process_soil_texture.py. "
        "Install with `pip install rasterio`."
    ) from exc


DEFAULT_INPUTS = {
    "sand": Path("raw/soil_texture/sand.tif"),
    "silt": Path("raw/soil_texture/silt.tif"),
    "clay": Path("raw/soil_texture/clay.tif"),
}

BAND_DESCRIPTIONS = {
    1: "Soil Sand (%)",
    2: "Soil Silt (%)",
    3: "Soil Clay (%)",
}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Align soil texture percentages to the WhereWild 100 m grid."
    )
    parser.add_argument(
        "--grid",
        type=Path,
        required=True,
        help="Path to grid.json (defines canonical grid bounds/CRS).",
    )
    parser.add_argument(
        "--sand",
        type=Path,
        default=DEFAULT_INPUTS["sand"],
        help="Sand percentage GeoTIFF (default: raw/soil_texture/sand.tif).",
    )
    parser.add_argument(
        "--silt",
        type=Path,
        default=DEFAULT_INPUTS["silt"],
        help="Silt percentage GeoTIFF (default: raw/soil_texture/silt.tif).",
    )
    parser.add_argument(
        "--clay",
        type=Path,
        default=DEFAULT_INPUTS["clay"],
        help="Clay percentage GeoTIFF (default: raw/soil_texture/clay.tif).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for the aligned multi-band GeoTIFF.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional manifest CSV to log provenance (append-only).",
    )
    parser.add_argument(
        "--resampling",
        choices=["average", "bilinear"],
        default="average",
        help="Resampling kernel (percentages prefer average; bilinear is fallback).",
    )
    return parser.parse_args(argv)


def load_grid(path: Path) -> Dict[str, object]:
    with path.open() as fp:
        grid = json.load(fp)
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


def convert_to_cog(temp_path: Path, output_path: Path, nodata: float) -> Path:
    """Translate a temporary GeoTIFF into a COG if rio-cogeo is available."""
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
            "rio-cogeo not installed; leaving soil texture output as standard GeoTIFF.",
            "Install rio-cogeo for cloud-optimized output.",
        )
        shutil.move(temp_path, output_path)
        return output_path

    if get_profile is not None:
        profile = get_profile("deflate")
    else:
        profile_obj = cog_profiles.get("deflate")
        profile = dict(profile_obj) if profile_obj else {}
    profile.update({"nodata": nodata})

    cog_translate(
        str(temp_path),
        str(output_path),
        profile,
        in_memory=False,
        quiet=True,
    )
    temp_path.unlink(missing_ok=True)
    return output_path


def append_manifest(manifest_path: Optional[Path], output_path: Path) -> None:
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
        "dataset": "soil_texture_pct_100m_epsg5070",
        "source_url": output_path.as_posix(),
        "license": "See source soil dataset (e.g., SoilGrids / NRCS gNATSGO)",
        "created_at": dt.datetime.utcnow().date().isoformat(),
        "notes": "Sand/Silt/Clay percentage stack aligned to WhereWild 100 m grid.",
    }

    if record["source_url"] in seen_urls:
        return

    with manifest_path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if not manifest_exists:
            writer.writeheader()
        writer.writerow(record)


def ensure_inputs(paths: Iterable[Path]) -> None:
    missing = [path for path in paths if not path.exists()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            f"Missing soil texture raster(s): {joined}. "
            "Download the source GeoTIFFs and place them under raw/soil_texture/ "
            "or point to them explicitly with --sand/--silt/--clay."
        )


def process_soil_texture(
    grid_path: Path,
    sand_path: Path,
    silt_path: Path,
    clay_path: Path,
    output_path: Path,
    resampling: str,
) -> Path:
    grid = load_grid(grid_path)
    bounds = grid["bounds"]
    pixel_size = float(grid["pixel_size"])
    width, height = compute_dimensions(bounds, pixel_size)
    transform = build_transform(bounds, pixel_size)
    crs = grid["crs"]

    tmp_dir = Path(tempfile.mkdtemp(prefix="soil_texture_"))
    tmp_tif = tmp_dir / "soil_texture_100m.tif"

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 3,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": np.nan,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "BIGTIFF": "YES",
    }

    sources = [("sand", sand_path), ("silt", silt_path), ("clay", clay_path)]
    resampling_method = Resampling.average if resampling == "average" else Resampling.bilinear

    with rasterio.open(tmp_tif, "w", **profile) as dst:
        for band_index, (label, source_path) in enumerate(sources, start=1):
            print(f"Reprojecting {label} percentage: {source_path}")
            with rasterio.open(source_path) as src:
                reproject(
                    source=rasterio.band(src, 1),
                    destination=rasterio.band(dst, band_index),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    src_nodata=src.nodata,
                    dst_transform=transform,
                    dst_crs=crs,
                    dst_nodata=np.nan,
                    resampling=resampling_method,
                )
        for band_index, description in BAND_DESCRIPTIONS.items():
            dst.set_band_description(band_index, description)

    output = convert_to_cog(tmp_tif, output_path, nodata=np.nan)
    tmp_dir.rmdir()
    return output


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    ensure_inputs([args.sand, args.silt, args.clay])

    output = process_soil_texture(
        grid_path=args.grid,
        sand_path=args.sand,
        silt_path=args.silt,
        clay_path=args.clay,
        output_path=args.output,
        resampling=args.resampling,
    )

    append_manifest(args.manifest, output)
    print(f"Soil texture stack written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
