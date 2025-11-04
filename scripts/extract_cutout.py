#!/usr/bin/env python3
"""
Extract a raster cutout around a geographic coordinate.

Example:
    venv/bin/python scripts/extract_cutout.py \
        --center "40.603417,-111.767639" \
        --size-km 10 \
        --output processed/cutouts/custom_salt_lake.tif
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, Sequence, Tuple

import rasterio
from rasterio import windows
from pyproj import Transformer

DEFAULT_RASTER = Path("processed/terrain/terrain_stack.tif")
DEFAULT_OUTPUT_ROOT = Path("processed/cutouts")
DEFAULT_CONFIG = Path("regions.json")
DEFAULT_SIZE_KM = 10.0


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract raster cutouts from the canonical DEM or other rasters."
    )
    parser.add_argument(
        "--raster",
        type=Path,
        default=DEFAULT_RASTER,
        help=f"Source raster to clip (default: {DEFAULT_RASTER}).",
    )
    parser.add_argument(
        "--center",
        help="Center coordinate in 'lat,lon' or 'lon,lat' format (auto-detected).",
    )
    parser.add_argument(
        "--size-km",
        type=float,
        default=DEFAULT_SIZE_KM,
        help=f"Half-size of the cutout in kilometers (default: {DEFAULT_SIZE_KM} km).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for a single cutout (defaults to processed/cutouts when omitted).",
    )
    parser.add_argument(
        "--center-format",
        choices=["latlon", "lonlat"],
        help="Explicit ordering for the center coordinate (otherwise auto-detected).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Region configuration JSON for batch cutouts (default: {DEFAULT_CONFIG}).",
    )
    parser.add_argument(
        "--name",
        help="Region name from the configuration to extract (defaults to all regions).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate cutouts for every region in the configuration.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Directory for generated cutouts when using --all/--name (default: {DEFAULT_OUTPUT_ROOT}).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite cutouts when outputs already exist.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print diagnostic information (center pixel, lat/lon bounds).",
    )
    return parser.parse_args(argv)


def parse_center(raw: str, center_format: str | None) -> Tuple[float, float]:
    """Turn a CLI comma pair into (lat, lon), inferring order when needed."""
    parts = raw.split(",")
    if len(parts) != 2:
        raise ValueError("Center must be 'lat,lon' or 'lon,lat'.")
    values = tuple(float(p.strip()) for p in parts)
    if center_format == "latlon":
        lat, lon = values
    elif center_format == "lonlat":
        lon, lat = values
    else:
        lat_first = abs(values[0]) <= 90 and abs(values[1]) <= 180
        if lat_first and not (abs(values[1]) <= 90 and abs(values[0]) <= 180):
            lat, lon = values
        else:
            lon, lat = values
    return lat, lon


def load_regions_config(path: Path) -> Dict[str, Any]:
    """Load the JSON config that lists reusable cutout regions."""
    if not path.exists():
        raise FileNotFoundError(f"Region configuration not found: {path}")
    with path.open() as fp:
        return json.load(fp)


def slugify_name(value: str) -> str:
    """Lowercase and sanitize region names so we can safely use them in filenames."""
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    cleaned = "_".join(filter(None, cleaned.split("_")))
    return cleaned or "cutout"


def extract_cutout(
    raster: Path,
    center_lat: float,
    center_lon: float,
    size_km: float,
    output: Path,
) -> Dict[str, Any]:
    """Clip a square raster window around the requested center and write it to disk."""
    half_size_m = size_km * 1000
    if half_size_m <= 0:
        raise ValueError("size_km must be positive.")

    with rasterio.open(raster) as src:
        to_proj = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        to_geo = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
        x, y = to_proj.transform(center_lon, center_lat)

        row, col = src.index(x, y)
        half_pixels = int(round(half_size_m / src.res[0]))
        # Rasterio windows operate on pixel indices; we build a square around the center.
        window = windows.Window(
            col_off=col - half_pixels,
            row_off=row - half_pixels,
            width=2 * half_pixels,
            height=2 * half_pixels,
        )
        window = window.intersection(windows.Window(0, 0, src.width, src.height))

        bounds = windows.bounds(window, src.transform)
        data = src.read(window=window)
        profile = src.profile
        profile.update(
            {
                "height": int(window.height),
                "width": int(window.width),
                "transform": windows.transform(window, src.transform),
            }
        )
        descriptions = src.descriptions or ()

    output.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output, "w", **profile) as dst:
        dst.write(data)
        if descriptions:
            for band_index, desc in enumerate(descriptions, start=1):
                if desc:
                    dst.set_band_description(band_index, desc)

    x_min, y_min, x_max, y_max = bounds
    lon_min, lat_min = to_geo.transform(x_min, y_min)
    lon_max, lat_max = to_geo.transform(x_max, y_max)

    return {
        "output": output,
        "center": {"lat": center_lat, "lon": center_lon},
        "bounds": {
            "lon_min": lon_min,
            "lon_max": lon_max,
            "lat_min": lat_min,
            "lat_max": lat_max,
        },
        "window": {
            "row_off": int(window.row_off),
            "row_max": int(window.row_off + window.height),
            "col_off": int(window.col_off),
            "col_max": int(window.col_off + window.width),
        },
    }


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)

    if not argv and not args.center and not args.name:
        # Calling the script with zero arguments defaults to generating all configured cutouts.
        args.all = True

    if args.center:
        lat, lon = parse_center(args.center, args.center_format)
        output_path = args.output
        if output_path is None:
            slug = slugify_name(f"custom_{lat:.4f}_{lon:.4f}_{int(args.size_km * 2)}km")
            output_path = DEFAULT_OUTPUT_ROOT / f"{slug}.tif"
        info = extract_cutout(
            raster=args.raster,
            center_lat=lat,
            center_lon=lon,
            size_km=args.size_km,
            output=output_path,
        )
        if args.verbose:
            bounds = info["bounds"]
            window = info["window"]
            print(f"Center (lat,lon): ({lat:.6f}, {lon:.6f})")
            print("Cutout extent (lon/lat):")
            print(f"  Lon {bounds['lon_min']:.4f} → {bounds['lon_max']:.4f}")
            print(f"  Lat {bounds['lat_min']:.4f} → {bounds['lat_max']:.4f}")
            print(
                f"Pixel window: rows {window['row_off']}:{window['row_max']}, "
                f"cols {window['col_off']}:{window['col_max']}"
            )
        print(f"Cutout saved to {info['output']}")
        return 0

    # Batch mode via configuration
    config = load_regions_config(args.config)
    cutouts = config.get("cutouts", [])
    if args.name:
        cutouts = [c for c in cutouts if c.get("name") == args.name]
        if not cutouts:
            raise ValueError(f"Region '{args.name}' not found in {args.config}")
    if not cutouts:
        print("No cutouts defined; nothing to do.")
        return 0

    for region in cutouts:
        name = region["name"]
        lat = region["center"]["lat"]
        lon = region["center"]["lon"]
        width_km = region["width_km"]
        half_width = width_km / 2.0
        output_dir = args.output_root / name
        output_path = output_dir / f"{args.raster.stem}.tif"
        if output_path.exists() and not args.overwrite:
            print(f"Region '{name}': {output_path} already exists (skip)")
            continue
        info = extract_cutout(
            raster=args.raster,
            center_lat=lat,
            center_lon=lon,
            size_km=half_width,
            output=output_path,
        )
        bounds = info["bounds"]
        print(
            f"Region '{name}': saved {output_path} "
            f"(lon {bounds['lon_min']:.4f} → {bounds['lon_max']:.4f}, "
            f"lat {bounds['lat_min']:.4f} → {bounds['lat_max']:.4f})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
