#!/usr/bin/env python3
"""
Export per-cell feature tables (Parquet) for configured regions.

Each output includes grid indices, projected and geographic coordinates,
and the environmental attributes currently available (terrain stack bands
and land cover class when present).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - dependency guard
    pd = None


def ensure_dependencies() -> None:
    if pd is None:
        raise SystemExit(
            "pandas is required for scripts/build_feature_table.py. "
            "Install with `pip install -r requirements.txt` (needs pandas + pyarrow)."
        )
import rasterio
from pyproj import Transformer
from rasterio.transform import xy

SOIL_PROPERTY_MAP = {
    "soil_cfvo": ("cfvo", "soil_cfvo_pct", np.float32),
    "soil_phh2o": ("phh2o", "soil_phh2o", np.float32),
    "soil_nitrogen": ("nitrogen", "soil_nitrogen_pct", np.float32),
    "soil_soc": ("soc", "soil_soc_pct", np.float32),
}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Parquet feature tables for configured regions."
    )
    parser.add_argument(
        "--processed-root",
        type=Path,
        default=Path("processed"),
        help="Root processed data directory (default: processed).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("regions.json"),
        help="Region configuration JSON (default: regions.json).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("processed/features"),
        help="Directory to store Parquet outputs (default: processed/features).",
    )
    parser.add_argument(
        "--include-conus",
        action="store_true",
        help="Include the full CONUS raster (warning: extremely large table).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Manifest CSV for provenance logging.",
    )
    parser.add_argument(
        "--regions",
        nargs="+",
        help="Subset of region slugs (as defined in regions.json) to export.",
    )
    return parser.parse_args(argv)


def load_regions(config_path: Path) -> Dict[str, Dict[str, str]]:
    if not config_path.exists():
        raise FileNotFoundError(f"Region configuration not found: {config_path}")
    with config_path.open() as fp:
        config = json.load(fp)

    regions: Dict[str, Dict[str, str]] = {}
    cutouts = config.get("cutouts", []) if isinstance(config, dict) else []
    for entry in cutouts:
        name = entry.get("name")
        if not name:
            continue
        slug = slugify(name, name)
        regions[slug] = {
            "label": name,
            "slug": slug,
        }
    return regions


def slugify(value: str, fallback: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    cleaned = "_".join(filter(None, cleaned.split("_")))
    return cleaned or fallback


def append_manifest(manifest_path: Optional[Path], output_path: Path, region_label: str) -> None:
    if manifest_path is None:
        return

    fieldnames = ["dataset", "source_url", "license", "created_at", "notes"]
    manifest_exists = manifest_path.exists()
    seen = set()
    if manifest_exists:
        with manifest_path.open(newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                if "source_url" in row:
                    seen.add(row["source_url"])

    record = {
        "dataset": "feature_table",
        "source_url": output_path.as_posix(),
        "license": "Derived from WhereWild processed rasters (see manifest for sources)",
        "created_at": dt.datetime.utcnow().date().isoformat(),
        "notes": f"Tidy feature table for region '{region_label}'",
    }

    if record["source_url"] in seen:
        return

    with manifest_path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if not manifest_exists:
            writer.writeheader()
        writer.writerow(record)


def build_feature_table(
    region_slug: str,
    region_label: str,
    terrain_path: Path,
    landcover_path: Optional[Path],
    soil_texture_path: Optional[Path],
    soil_property_paths: Dict[str, Optional[Path]],
    output_path: Path,
) -> None:
    if not terrain_path.exists():
        print(f"[skip] terrain stack missing for {region_slug}: {terrain_path}")
        return

    print(f"[{region_slug}] Loading terrain stack: {terrain_path}")
    with rasterio.open(terrain_path) as terrain_ds:
        terrain = terrain_ds.read(masked=True)
        elevation = terrain[0]
        slope = terrain[1]
        aspect = terrain[2]
        roughness = terrain[3]
        transform = terrain_ds.transform
        crs = terrain_ds.crs
        rows, cols = terrain_ds.height, terrain_ds.width

    landcover = None
    if landcover_path and landcover_path.exists():
        print(f"[{region_slug}] Loading land cover: {landcover_path}")
        with rasterio.open(landcover_path) as landcover_ds:
            lc_data = landcover_ds.read(1)
            lc_nodata = landcover_ds.nodata
            if lc_nodata is not None:
                landcover = np.ma.masked_equal(lc_data, lc_nodata)
            else:
                landcover = np.ma.masked_array(lc_data, mask=(lc_data == 0))
    else:
        print(f"[{region_slug}] Land cover not found; column will be filled with NaN.")

    sand = silt = clay = None
    if soil_texture_path and soil_texture_path.exists():
        print(f"[{region_slug}] Loading soil texture: {soil_texture_path}")
        with rasterio.open(soil_texture_path) as soil_ds:
            soil = soil_ds.read(masked=True)
            if soil.shape[0] < 3:
                raise ValueError(
                    f"Soil texture raster must have at least three bands (sand/silt/clay); found {soil.shape[0]}"
                )
            sand = soil[0]
            silt = soil[1]
            clay = soil[2]
    else:
        print(f"[{region_slug}] Soil texture not found; columns will be filled with NaN.")

    soil_property_arrays: Dict[str, Optional[np.ma.MaskedArray]] = {}
    for dataset_key, (_, column_name, _) in SOIL_PROPERTY_MAP.items():
        prop_path = None
        if soil_property_paths:
            prop_path = soil_property_paths.get(dataset_key)
        if prop_path and prop_path.exists():
            print(f"[{region_slug}] Loading {column_name}: {prop_path}")
            with rasterio.open(prop_path) as prop_ds:
                soil_property_arrays[column_name] = prop_ds.read(1, masked=True)
        else:
            soil_property_arrays[column_name] = None
            if prop_path:
                print(f"[{region_slug}] {column_name} raster missing ({prop_path}); filling with NaN.")

    # Build coordinate grids
    grid_y, grid_x = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")

    valid_mask = (
        ~elevation.mask
        & ~slope.mask
        & ~aspect.mask
        & ~roughness.mask
    )
    if landcover is not None:
        valid_mask &= ~landcover.mask
    if sand is not None and silt is not None and clay is not None:
        valid_mask &= ~sand.mask & ~silt.mask & ~clay.mask
    for arr in soil_property_arrays.values():
        if arr is not None:
            valid_mask &= ~arr.mask

    if not valid_mask.any():
        print(f"[{region_slug}] No valid pixels after masking; skipping.")
        return

    flat_rows = grid_y[valid_mask]
    flat_cols = grid_x[valid_mask]

    xs, ys = xy(transform, flat_rows, flat_cols, offset="center")
    xs = np.asarray(xs)
    ys = np.asarray(ys)

    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(xs, ys)

    cell_id = np.array([f"{c}_{r}" for c, r in zip(flat_cols, flat_rows)], dtype=object)

    data = {
        "region": np.full(flat_rows.shape, region_slug, dtype=object),
        "region_label": np.full(flat_rows.shape, region_label, dtype=object),
        "grid_y": flat_rows.astype(np.int32),
        "grid_x": flat_cols.astype(np.int32),
        "cell_id": cell_id,
        "projected_x": xs.astype(np.float32),
        "projected_y": ys.astype(np.float32),
        "longitude": lons.astype(np.float64),
        "latitude": lats.astype(np.float64),
        "elevation_m": elevation.data[valid_mask].astype(np.float32),
        "slope_deg": slope.data[valid_mask].astype(np.float32),
        "aspect_deg": aspect.data[valid_mask].astype(np.float32),
        "roughness": roughness.data[valid_mask].astype(np.float32),
    }
    if landcover is not None:
        data["landcover_class"] = landcover.data[valid_mask].astype(np.uint8)
    else:
        data["landcover_class"] = np.full(flat_rows.shape, np.nan, dtype=np.float32)

    if sand is not None and silt is not None and clay is not None:
        data["soil_sand_pct"] = (sand.data[valid_mask] * 0.1).astype(np.float32)
        data["soil_silt_pct"] = (silt.data[valid_mask] * 0.1).astype(np.float32)
        data["soil_clay_pct"] = (clay.data[valid_mask] * 0.1).astype(np.float32)
    else:
        data["soil_sand_pct"] = np.full(flat_rows.shape, np.nan, dtype=np.float32)
        data["soil_silt_pct"] = np.full(flat_rows.shape, np.nan, dtype=np.float32)
        data["soil_clay_pct"] = np.full(flat_rows.shape, np.nan, dtype=np.float32)

    for column_name, arr in soil_property_arrays.items():
        if arr is not None:
            data[column_name] = arr.data[valid_mask].astype(np.float32)
        else:
            data[column_name] = np.full(flat_rows.shape, np.nan, dtype=np.float32)

    df = pd.DataFrame(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[{region_slug}] Writing {len(df):,} rows -> {output_path}")
    df.to_parquet(output_path, index=False, engine="pyarrow")


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    ensure_dependencies()
    processed_root = args.processed_root
    terrain_base = processed_root / "terrain" / "terrain_stack.tif"
    landcover_base = processed_root / "landcover" / "landcover_100m_cog.tif"
    soil_base = processed_root / "soil_texture" / "soil_texture_100m_cog.tif"

    regions = load_regions(args.config)
    if args.regions:
        missing = [slug for slug in args.regions if slug not in regions]
        if missing:
            raise ValueError(f"Unknown region slugs requested: {missing}")
        regions = {slug: regions[slug] for slug in args.regions}

    targets: List[Dict[str, Path]] = []
    for slug, meta in regions.items():
        terrain_path = processed_root / "cutouts" / slug / "terrain_stack.tif"
        landcover_path = processed_root / "cutouts" / slug / "landcover.tif"
        soil_path = processed_root / "cutouts" / slug / "soil_texture.tif"
        soil_props: Dict[str, Optional[Path]] = {}
        for dataset_key, (stem, _, _) in SOIL_PROPERTY_MAP.items():
            soil_props[dataset_key] = processed_root / "cutouts" / slug / f"{dataset_key}.tif"
        targets.append(
            {
                "slug": slug,
                "label": meta["label"],
                "terrain": terrain_path,
                "landcover": landcover_path,
                "soil": soil_path,
                "soil_properties": soil_props,
            }
        )

    if args.include_conus:
        base_props: Dict[str, Optional[Path]] = {}
        for dataset_key, (stem, _, _) in SOIL_PROPERTY_MAP.items():
            base_props[dataset_key] = processed_root / "soil" / f"{stem}_100m.tif"
        targets.insert(
            0,
            {
                "slug": "conus",
                "label": "CONUS",
                "terrain": terrain_base,
                "landcover": landcover_base,
                "soil": soil_base,
                "soil_properties": base_props,
            },
        )

    if not targets:
        print("No regions discovered; nothing to do.")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for target in targets:
        output_path = args.output_dir / f"{target['slug']}.parquet"
        build_feature_table(
            target["slug"],
            target["label"],
            target["terrain"],
            target["landcover"],
            target["soil"],
            target["soil_properties"],
            output_path,
        )
        append_manifest(args.manifest, output_path, target["label"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
