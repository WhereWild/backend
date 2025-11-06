#!/usr/bin/env python3
"""
Resample additional SoilGrids properties (coarse fragments, pH, nitrogen,
organic carbon, etc.) into the canonical 100 m grid.

These datasets are single-band rasters. Each property can have a scaling
factor applied so the stored values are in intuitive units (e.g., g/kg -> %,
pH*10 -> pH).
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
        "rasterio is required for scripts/process_soil_properties.py. "
        "Install with `pip install rasterio`."
    ) from exc


PROPERTIES = {
    # name: (raw raster path, scale factor applied during resample, band description)
    "cfvo": ("raw/soil_texture/cfvo.tif", 0.1, "Coarse Fragments (%)"),
    "phh2o": ("raw/soil_texture/phh2o.tif", 0.1, "pH (H2O)"),
    "nitrogen": ("raw/soil_texture/nitrogen.tif", 0.1, "Nitrogen (%)"),
    "soc": ("raw/soil_texture/soc.tif", 0.1, "Soil Organic Carbon (%)"),
}

OUTPUT_ROOT = Path("processed/soil")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resample SoilGrids property rasters into the 100 m grid."
    )
    parser.add_argument(
        "--grid",
        type=Path,
        required=True,
        help="Path to grid.json (defines canonical grid bounds/CRS).",
    )
    parser.add_argument(
        "--properties",
        nargs="*",
        choices=sorted(PROPERTIES.keys()),
        default=sorted(PROPERTIES.keys()),
        help="Subset of properties to process (default: all).",
    )
    parser.add_argument(
        "--resampling",
        choices=["average", "bilinear"],
        default="average",
        help="Resampling kernel (default: average).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional manifest CSV to log provenance.",
    )
    return parser.parse_args(argv)


def load_grid(path: Path) -> Tuple[Tuple[float, float, float, float], float, int, int, Affine, str]:
    with path.open() as fp:
        grid = json.load(fp)
    bounds = tuple(grid["bounds"])
    pixel_size = float(grid["pixel_size"])
    xmin, ymin, xmax, ymax = bounds
    width = int(round((xmax - xmin) / pixel_size))
    height = int(round((ymax - ymin) / pixel_size))
    transform = Affine(pixel_size, 0.0, xmin, 0.0, -pixel_size, ymax)
    crs = grid["crs"]
    return bounds, pixel_size, width, height, transform, crs


def ensure_inputs(properties: Iterable[str]) -> None:
    missing = [name for name in properties if not Path(PROPERTIES[name][0]).exists()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(
            f"Missing raw SoilGrids rasters for: {joined}. Run download_soil.py first."
        )


def append_manifest(manifest_path: Optional[Path], output_path: Path, label: str) -> None:
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
        "dataset": f"soil_{label}_100m_epsg5070",
        "source_url": output_path.as_posix(),
        "license": "See SoilGrids data policy (ISRIC).",
        "created_at": dt.datetime.utcnow().date().isoformat(),
        "notes": f"SoilGrids property '{label}' resampled to WhereWild 100 m grid.",
    }

    if record["source_url"] in seen_urls:
        return

    with manifest_path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if not manifest_exists:
            writer.writeheader()
        writer.writerow(record)


def reproject_property(
    name: str,
    src_path: Path,
    scale: float,
    description: str,
    transform: Affine,
    crs: str,
    width: int,
    height: int,
    resampling_method: Resampling,
) -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{name}_"))
    tmp_path = tmp_dir / f"{name}_100m.tif"

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
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

    with rasterio.open(tmp_path, "w", **profile) as dst:
        with rasterio.open(src_path) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=src.nodata,
                dst_transform=transform,
                dst_crs=crs,
                dst_nodata=np.nan,
                resampling=resampling_method,
            )
        dst.set_band_description(1, description)

    # Apply scaling in-place
    with rasterio.open(tmp_path, "r+") as dst:
        data = dst.read(1, masked=True)
        if scale != 1.0:
            data = (data * scale).astype(np.float32)
        dst.write(data.filled(np.nan), 1)

    final_path = OUTPUT_ROOT / f"{name}_100m.tif"
    shutil.move(tmp_path, final_path)
    tmp_dir.rmdir()
    return final_path


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    ensure_inputs(args.properties)

    _, _, width, height, transform, crs = load_grid(args.grid)
    resampling_method = Resampling.average if args.resampling == "average" else Resampling.bilinear

    for name in args.properties:
        src_path, scale, description = PROPERTIES[name]
        src = Path(src_path)
        print(f"Reprojecting {name} -> {OUTPUT_ROOT / f'{name}_100m.tif'}")
        output = reproject_property(
            name=name,
            src_path=src,
            scale=scale,
            description=description,
            transform=transform,
            crs=crs,
            width=width,
            height=height,
            resampling_method=resampling_method,
        )
        append_manifest(args.manifest, output, name)
        print(f"  wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
