"""Build precomputed global suitability surfaces for the four-species prototype.

Outputs:
- Partitioned parquet cells for serving `/species/{taxon_id}/inference-heatmap`
- Per-species GeoTIFF (COG when supported) per region tile
- Surface manifest with metadata and API-facing contract fields

This script is intentionally pragmatic for current 4-species scope and uses
available static GIS rasters (bio_*, dem/elevation, landcover, koppen_geiger)
plus geospatial harmonics.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    rasterio: Any = importlib.import_module("rasterio")
    Affine: Any = rasterio.Affine
except ModuleNotFoundError:
    rasterio = None
    Affine = None


BACKGROUND_CLASS = "BACKGROUND"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _softmax(logits: np.ndarray) -> np.ndarray:
    stable = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(stable)
    return exp / exp.sum(axis=1, keepdims=True)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _load_model(model_path: Path) -> dict[str, Any]:
    artifact = np.load(model_path, allow_pickle=True)
    feature_columns = [str(column) for column in artifact["feature_columns"].tolist()]
    mean = artifact["mean"].astype(np.float64)
    std = artifact["std"].astype(np.float64)

    if "encoder_weights" in artifact.files and "species_embeddings" in artifact.files:
        species_names = [str(name) for name in artifact["species_names"].tolist()]
        return {
            "family": "embedding_head_v1",
            "feature_columns": feature_columns,
            "mean": mean,
            "std": std,
            "encoder_weights": artifact["encoder_weights"].astype(np.float64),
            "encoder_bias": artifact["encoder_bias"].astype(np.float64),
            "species_embeddings": artifact["species_embeddings"].astype(np.float64),
            "species_bias": artifact["species_bias"].astype(np.float64),
            "calibration_scale": artifact["calibration_scale"].astype(np.float64)
            if "calibration_scale" in artifact.files
            else np.ones(len(species_names), dtype=np.float64),
            "calibration_bias": artifact["calibration_bias"].astype(np.float64)
            if "calibration_bias" in artifact.files
            else np.zeros(len(species_names), dtype=np.float64),
            "species_names": species_names,
        }

    class_names = [str(name) for name in artifact["class_names"].tolist()]
    species_names = [name for name in class_names if name != BACKGROUND_CLASS]
    return {
        "family": "legacy_softmax",
        "feature_columns": feature_columns,
        "mean": mean,
        "std": std,
        "weights": artifact["weights"].astype(np.float64),
        "bias": artifact["bias"].astype(np.float64),
        "class_names": class_names,
        "species_names": species_names,
    }


def _slugify(value: str) -> str:
    return value.lower().replace(" ", "_")


def _find_reference_raster(region_dir: Path) -> Path | None:
    for name in ("bio_1.tif", "dem.tif", "landcover.tif", "koppen_geiger.tif"):
        candidate = region_dir / name
        if candidate.exists():
            return candidate
    return None


def _read_raster(path: Path) -> np.ndarray:
    with rasterio.open(path) as dataset:
        arr = dataset.read(1, masked=True).astype(np.float64)
    return np.ma.filled(arr, np.nan)


def _sample_raster_at_coords(path: Path, lon_arr: np.ndarray, lat_arr: np.ndarray) -> np.ndarray:
    coords = list(zip(lon_arr.tolist(), lat_arr.tolist(), strict=False))
    with rasterio.open(path) as dataset:
        values = np.fromiter((float(value[0]) for value in dataset.sample(coords)), dtype=np.float64, count=len(coords))
        nodata = dataset.nodata
    if nodata is not None:
        values = np.where(np.isclose(values, nodata), np.nan, values)
    return values


def _slope_aspect_from_dem(dem: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dem_fill = float(np.nanmedian(dem[np.isfinite(dem)]) if np.isfinite(dem).any() else 0.0)
    dem_safe = np.nan_to_num(dem, nan=dem_fill)
    grad_y, grad_x = np.gradient(dem_safe)
    slope = np.sqrt((grad_x**2) + (grad_y**2))
    aspect_rad = np.arctan2(-grad_x, grad_y)
    aspect_deg = (np.degrees(aspect_rad) + 360.0) % 360.0
    return slope, aspect_rad, aspect_deg


def _score_species_map(model: dict[str, Any], x_scaled: np.ndarray) -> dict[str, np.ndarray]:
    if model["family"] == "embedding_head_v1":
        hidden = np.tanh(x_scaled @ model["encoder_weights"] + model["encoder_bias"])
        out: dict[str, np.ndarray] = {}
        for idx, species in enumerate(model["species_names"]):
            logits = np.sum(hidden * model["species_embeddings"][idx], axis=1) + model["species_bias"][idx]
            calibrated = (model["calibration_scale"][idx] * logits) + model["calibration_bias"][idx]
            out[species] = _sigmoid(calibrated)
        return out

    class_to_idx = {name: idx for idx, name in enumerate(model["class_names"])}
    probabilities = _softmax(x_scaled @ model["weights"] + model["bias"])
    return {species: probabilities[:, class_to_idx[species]] for species in model["species_names"]}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build global four-species suitability surfaces")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path("artifacts/ml_prototype_4_species/model.npz"),
        help="Path to trained model artifact",
    )
    parser.add_argument(
        "--regions-root",
        type=Path,
        default=Path("data/gis/regions"),
        help="Root containing region raster folders",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/ml_global_surface_4_species"),
        help="Output directory for surface artifacts",
    )
    parser.add_argument("--stride", type=int, default=6, help="Raster stride for sampling global grid")
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(8, os.cpu_count() or 1)),
        help="Number of worker threads for processing regions",
    )
    parser.add_argument("--max-regions", type=int, default=0, help="Optional cap for quick smoke runs (0=all)")
    parser.add_argument(
        "--time-slice",
        type=str,
        default="static",
        help="Time slice label for manifest and serving",
    )
    return parser


def _process_region(
    region_dir: Path,
    model: dict[str, Any],
    species_cols: dict[str, str],
    stride: int,
    time_slice: str,
    cells_dir: Path,
    geotiff_dir: Path,
) -> tuple[str, int, dict[str, dict[str, float | int]]] | None:
    reference_path = _find_reference_raster(region_dir)
    if reference_path is None:
        return None

    with rasterio.open(reference_path) as ref_ds:
        transform = ref_ds.transform
        height = ref_ds.height
        width = ref_ds.width
        crs = ref_ds.crs

    row_idx = np.arange(0, height, stride)
    col_idx = np.arange(0, width, stride)
    grid_rows, grid_cols = np.meshgrid(row_idx, col_idx, indexing="ij")
    rr = grid_rows.ravel()
    cc = grid_cols.ravel()

    lon, lat = rasterio.transform.xy(transform, rr, cc, offset="center")
    lat_arr = np.asarray(lat, dtype=np.float64)
    lon_arr = np.asarray(lon, dtype=np.float64)

    reference_values = _sample_raster_at_coords(reference_path, lon_arr, lat_arr)
    valid = np.isfinite(reference_values)
    if not np.any(valid):
        return None
    rr = rr[valid]
    cc = cc[valid]
    lat_arr = lat_arr[valid]
    lon_arr = lon_arr[valid]

    feature_raster_paths: dict[str, Path] = {}
    dem_path = region_dir / "dem.tif"
    for feature in model["feature_columns"]:
        if feature.startswith("bio_"):
            candidate = region_dir / f"{feature}.tif"
            if candidate.exists():
                feature_raster_paths[feature] = candidate
        elif feature in {"landcover", "koppen_geiger"}:
            candidate = region_dir / f"{feature}.tif"
            if candidate.exists():
                feature_raster_paths[feature] = candidate
        elif feature in {"elevation", "dem"} and dem_path.exists():
            feature_raster_paths[feature] = dem_path

    x = np.zeros((len(rr), len(model["feature_columns"])), dtype=np.float64)
    for col_idx_feature, feature in enumerate(model["feature_columns"]):
        if feature == "lat_sin":
            x[:, col_idx_feature] = np.sin(np.deg2rad(lat_arr))
        elif feature == "lat_cos":
            x[:, col_idx_feature] = np.cos(np.deg2rad(lat_arr))
        elif feature == "lon_sin":
            x[:, col_idx_feature] = np.sin(np.deg2rad(lon_arr))
        elif feature == "lon_cos":
            x[:, col_idx_feature] = np.cos(np.deg2rad(lon_arr))
        elif feature in feature_raster_paths:
            x[:, col_idx_feature] = _sample_raster_at_coords(feature_raster_paths[feature], lon_arr, lat_arr)
        else:
            x[:, col_idx_feature] = 0.0

    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    x_scaled = (x - model["mean"]) / np.where(model["std"] < 1e-8, 1.0, model["std"])
    x_scaled = np.nan_to_num(x_scaled, nan=0.0, posinf=0.0, neginf=0.0)

    score_map = _score_species_map(model, x_scaled)

    frame_dict: dict[str, Any] = {
        "lat": lat_arr.astype(np.float32),
        "lon": lon_arr.astype(np.float32),
        "row": rr.astype(np.int32),
        "col": cc.astype(np.int32),
        "region": np.full(len(rr), region_dir.name, dtype=object),
        "time_slice": np.full(len(rr), time_slice, dtype=object),
    }
    region_species_summary: dict[str, dict[str, float | int]] = {}
    for species, col_name in species_cols.items():
        values = np.asarray(score_map[species], dtype=np.float32)
        frame_dict[col_name] = values
        region_species_summary[species] = {
            "points": int(len(values)),
            "min": float(values.min()),
            "max": float(values.max()),
            "mean_sum": float(values.mean()) * len(values),
        }

    region_frame = pd.DataFrame(frame_dict)
    region_out = cells_dir / f"{region_dir.name}.parquet"
    region_frame.to_parquet(region_out, index=False)

    sampled_transform = transform * Affine.scale(stride, stride)
    sampled_h = len(row_idx)
    sampled_w = len(col_idx)

    for species, col_name in species_cols.items():
        raster_values = np.full((sampled_h, sampled_w), np.nan, dtype=np.float32)
        sr = (rr // stride).astype(np.int64)
        sc = (cc // stride).astype(np.int64)
        raster_values[sr, sc] = region_frame[col_name].to_numpy(dtype=np.float32)

        species_dir = geotiff_dir / _slugify(species)
        species_dir.mkdir(parents=True, exist_ok=True)
        tif_path = species_dir / f"{region_dir.name}.tif"

        driver = "COG"
        profile = {
            "driver": driver,
            "height": sampled_h,
            "width": sampled_w,
            "count": 1,
            "dtype": "float32",
            "crs": crs,
            "transform": sampled_transform,
            "nodata": np.nan,
            "compress": "deflate",
        }
        try:
            with rasterio.open(tif_path, "w", **profile) as dst:
                dst.write(raster_values, 1)
        except Exception:
            fallback_profile = dict(profile)
            fallback_profile["driver"] = "GTiff"
            with rasterio.open(tif_path, "w", **fallback_profile) as dst:
                dst.write(raster_values, 1)

    return region_dir.name, len(region_frame), region_species_summary


def main() -> None:
    args = _build_arg_parser().parse_args()
    root = _repo_root()

    if rasterio is None or Affine is None:
        raise ModuleNotFoundError(
            "rasterio is required for global surface builds. Run this script in the GDAL container or install rasterio."
        )

    model_path = (root / args.model_path).resolve()
    regions_root = (root / args.regions_root).resolve()
    output_dir = (root / args.output_dir).resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")
    if not regions_root.exists():
        raise FileNotFoundError(f"Regions root not found: {regions_root}")
    if args.stride < 1:
        raise ValueError("--stride must be >= 1")
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")

    model = _load_model(model_path)

    run_dir = output_dir / args.time_slice
    cells_dir = run_dir / "cells"
    geotiff_dir = run_dir / "geotiff"
    cells_dir.mkdir(parents=True, exist_ok=True)
    geotiff_dir.mkdir(parents=True, exist_ok=True)

    regions = sorted([path for path in regions_root.iterdir() if path.is_dir()])
    if args.max_regions > 0:
        regions = regions[: args.max_regions]

    species_cols = {species: f"score_{_slugify(species)}" for species in model["species_names"]}
    species_summary = {
        species: {"points": 0, "min": 1.0, "max": 0.0, "mean_sum": 0.0} for species in model["species_names"]
    }

    processed_regions = 0
    sampled_points_total = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                _process_region,
                region_dir,
                model,
                species_cols,
                args.stride,
                args.time_slice,
                cells_dir,
                geotiff_dir,
            )
            for region_dir in regions
        ]
        for future in as_completed(futures):
            result = future.result()
            if result is None:
                continue
            region_name, sampled_points, region_species_summary = result

            sampled_points_total += sampled_points
            processed_regions += 1
            for species, summary in region_species_summary.items():
                species_summary[species]["points"] += int(summary["points"])
                species_summary[species]["min"] = float(min(species_summary[species]["min"], float(summary["min"])))
                species_summary[species]["max"] = float(max(species_summary[species]["max"], float(summary["max"])))
                species_summary[species]["mean_sum"] += float(summary["mean_sum"])

            print(f"Processed region {region_name}: sampled_points={sampled_points}")

    species_manifest = {}
    for species in model["species_names"]:
        summary = species_summary[species]
        points = max(1, int(summary["points"]))
        species_manifest[species] = {
            "score_column": species_cols[species],
            "points": int(summary["points"]),
            "min": float(summary["min"]),
            "max": float(summary["max"]),
            "mean": float(summary["mean_sum"] / points),
        }

    manifest = {
        "version": "v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_path": str(model_path),
        "model_family": model["family"],
        "time_slice": args.time_slice,
        "species": species_manifest,
        "cells_dir": str(cells_dir),
        "geotiff_dir": str(geotiff_dir),
        "regions_processed": processed_regions,
        "sampled_points_total": sampled_points_total,
        "stride": args.stride,
        "serving": {
            "endpoint": "/species/{taxon_id}/inference-heatmap",
            "mode": "precomputed_surface_cells",
            "fallback": "legacy_point_scoring_for_unseen_time_slice",
        },
    }

    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    latest_pointer_path = output_dir / "latest.json"
    latest_pointer_path.write_text(
        json.dumps(
            {
                "time_slice": args.time_slice,
                "manifest": str(manifest_path),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Saved manifest:", manifest_path)
    print("Updated latest pointer:", latest_pointer_path)


if __name__ == "__main__":
    main()
