#!/usr/bin/env python3
"""
Build pre-defined regional cutouts from the canonical DEM and terrain stack.

Configuration lives in `regions.json` and defines:
  - A base region (metadata only; the full CONUS mosaic)
  - A list of named cutouts with center coordinates and widths (km)

Usage:
    venv/bin/python scripts/build_regions.py --config regions.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, Sequence

from extract_cutout import extract_cutout


DEFAULT_DATASETS = {
    "terrain_stack": Path("processed/terrain/terrain_stack.tif"),
}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate cutout rasters for named regions."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("regions.json"),
        help="Region configuration JSON (default: regions.json).",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=list(DEFAULT_DATASETS.keys()),
        help="Subset of datasets to cut out (default: all).",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("processed/cutouts"),
        help="Where to store cutout rasters (default: processed/cutouts).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing cutouts.",
    )
    return parser.parse_args(argv)


def load_config(path: Path) -> Dict:
    """Load the regions.json file that lists every named cutout."""
    if not path.exists():
        raise FileNotFoundError(f"Region configuration not found: {path}")
    with path.open() as fp:
        return json.load(fp)


def ensure_datasets(keys: Iterable[str], dataset_map: Dict[str, Path]) -> Dict[str, Path]:
    """Validate dataset choices and make sure the corresponding rasters exist."""
    paths: Dict[str, Path] = {}
    for key in keys:
        if key not in dataset_map:
            raise KeyError(f"Unknown dataset key '{key}'. Available: {sorted(dataset_map)}")
        candidate = dataset_map[key]
        if not candidate.exists():
            raise FileNotFoundError(
                f"Dataset '{key}' not found at {candidate}. Run the relevant pipeline first."
            )
        paths[key] = candidate
    return paths


def build_cutouts(
    config: Dict,
    dataset_paths: Dict[str, Path],
    output_root: Path,
    overwrite: bool,
) -> None:
    """Loop through regions and write one cutout per dataset."""
    cutouts = config.get("cutouts", [])
    if not cutouts:
        print("No cutouts defined in configuration.")
        return

    for region in cutouts:
        name = region["name"]
        lat = region["center"]["lat"]
        lon = region["center"]["lon"]
        width_km = region["width_km"]
        half_width = width_km / 2.0

        print(f"Region '{name}': center=({lat}, {lon}), width={width_km} km")
        region_dir = output_root / name
        region_dir.mkdir(parents=True, exist_ok=True)

        generated_paths = []
        for dataset_key, dataset_path in dataset_paths.items():
            output_path = region_dir / f"{dataset_key}.tif"
            if output_path.exists() and not overwrite:
                print(f"  {dataset_key}: exists -> {output_path}")
                generated_paths.append(output_path)
                continue
            info = extract_cutout(
                raster=dataset_path,
                center_lat=lat,
                center_lon=lon,
                size_km=half_width,
                output=output_path,
            )
            generated_paths.append(output_path)
            bounds = info["bounds"]
            print(
                f"  {dataset_key}: saved {output_path} "
                f"(lon {bounds['lon_min']:.4f} → {bounds['lon_max']:.4f}, "
                f"lat {bounds['lat_min']:.4f} → {bounds['lat_max']:.4f})"
            )

        # Remove legacy artifacts (e.g., DEM cutouts) no longer requested
        tracked = {path.resolve() for path in generated_paths}
        for orphan in region_dir.glob("*.tif"):
            if orphan.resolve() not in tracked:
                orphan.unlink()
                print(f"  removed leftover cutout {orphan}")


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    dataset_map = DEFAULT_DATASETS.copy()
    dataset_keys = args.datasets if args.datasets else dataset_map.keys()
    dataset_paths = ensure_datasets(dataset_keys, dataset_map)

    build_cutouts(config, dataset_paths, args.output_root, args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
