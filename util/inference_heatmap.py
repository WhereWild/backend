from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import importlib
import json
import math
from pathlib import Path
from threading import RLock
from time import monotonic
from typing import Any, Callable, Optional

from fastapi import HTTPException
import numpy as np
import pandas as pd

from util import gis_lookup, taxa_navigation


BACKGROUND_CLASS = "BACKGROUND"

_DYNAMIC_CACHE_MAX_ENTRIES = 128
_DYNAMIC_CACHE_TTL_SECONDS = 45.0
_DYNAMIC_MAX_POINTS_DEFAULT = 12000
_DYNAMIC_MAX_POINTS_GLOBAL = 5000

_dynamic_cache_lock = RLock()
_dynamic_payload_cache: OrderedDict[tuple[Any, ...], tuple[float, str]] = OrderedDict()

try:
    _rasterio: Any = importlib.import_module("rasterio")
except ModuleNotFoundError:
    _rasterio = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _remap_path_to_repo(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        return (repo_root / path).resolve()
    if path.exists():
        return path.resolve()

    parts = path.parts
    if "artifacts" in parts:
        artifacts_idx = parts.index("artifacts")
        candidate = (repo_root / Path(*parts[artifacts_idx:])).resolve()
        if candidate.exists():
            return candidate
    return path.resolve()


def _heatmap_cell_size_degrees(zoom: int) -> float:
    cell_size = 360.0 / (2 ** (zoom + 3))
    return max(0.05, min(15.0, cell_size))


def _softmax(logits: np.ndarray) -> np.ndarray:
    stable = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(stable)
    return exp / exp.sum(axis=1, keepdims=True)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _normalize_species_name(value: str) -> str:
    normalized = value.replace("_", " ")
    return " ".join(normalized.lower().strip().split())


def _resolve_model_artifact_path() -> Path:
    root = _repo_root()
    candidates = (
        root / "artifacts/ml_prototype_4_species/model.npz",
        root / "artifacts/ml_prototype_4_species_smoke/model.npz",
        root / "artifacts/ml_prototype_4_species_v2/model.npz",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "No prototype model artifact found. Expected artifacts/ml_prototype_4_species/model.npz "
        "or artifacts/ml_prototype_4_species_smoke/model.npz"
    )


@lru_cache(maxsize=1)
def _load_inference_model() -> dict[str, Any]:
    model_path = _resolve_model_artifact_path()
    artifact = np.load(model_path, allow_pickle=True)
    feature_columns = [str(column) for column in artifact["feature_columns"].tolist()]
    base_payload = {
        "model_path": model_path,
        "mean": artifact["mean"].astype(np.float64),
        "std": artifact["std"].astype(np.float64),
        "feature_columns": feature_columns,
    }

    if "encoder_weights" in artifact.files and "species_embeddings" in artifact.files:
        species_names = [str(name) for name in artifact["species_names"].tolist()]
        class_names = species_names + [BACKGROUND_CLASS]
        class_to_idx = {name: idx for idx, name in enumerate(class_names)}
        return {
            **base_payload,
            "model_family": "embedding_head_v1",
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
            "class_names": class_names,
            "species_names": species_names,
            "class_to_idx": class_to_idx,
        }

    class_names = [str(name) for name in artifact["class_names"].tolist()]
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}
    return {
        **base_payload,
        "model_family": "legacy_softmax",
        "weights": artifact["weights"].astype(np.float64),
        "bias": artifact["bias"].astype(np.float64),
        "class_names": class_names,
        "class_to_idx": class_to_idx,
    }


def _score_species_with_model(x_scaled: np.ndarray, model: dict[str, Any], species_name: str) -> np.ndarray:
    if model.get("model_family") == "embedding_head_v1":
        species_names = model.get("species_names", [])
        if species_name not in species_names:
            raise ValueError(f"Species '{species_name}' not available in embedding-head model")
        species_idx = species_names.index(species_name)
        hidden = np.tanh(x_scaled @ model["encoder_weights"] + model["encoder_bias"])
        logits = np.sum(hidden * model["species_embeddings"][species_idx], axis=1) + model["species_bias"][species_idx]
        calibrated = (model["calibration_scale"][species_idx] * logits) + model["calibration_bias"][species_idx]
        return _sigmoid(calibrated)

    target_idx = model["class_to_idx"][species_name]
    probabilities = _softmax(x_scaled @ model["weights"] + model["bias"])
    return probabilities[:, target_idx]


def _resolve_target_species_name(taxon: Any, class_names: list[str]) -> str | None:
    raw_name = str(taxon.get("scientific_name") or "").strip()
    normalized_name = _normalize_species_name(raw_name)

    aliases = {
        "pelecyphora vivipara": "escobaria vivipara",
    }
    candidate_name = aliases.get(normalized_name, normalized_name)

    normalized_class_map = {
        _normalize_species_name(class_name): class_name for class_name in class_names if class_name != BACKGROUND_CLASS
    }
    if candidate_name in normalized_class_map:
        return normalized_class_map[candidate_name]

    for normalized_class, class_name in normalized_class_map.items():
        if candidate_name.startswith(normalized_class) or normalized_class.startswith(candidate_name):
            return class_name
    return None


def _surface_root() -> Path:
    return _repo_root() / "artifacts/ml_global_surface_4_species"


def _load_surface_manifest(time_slice: str | None) -> tuple[dict[str, Any], str]:
    root = _surface_root()
    repo_root = _repo_root()
    requested = (time_slice or "latest").strip()

    if requested in {"", "latest"}:
        latest_path = root / "latest.json"
        if not latest_path.exists():
            raise FileNotFoundError("No precomputed global surface latest pointer found")
        latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
        manifest_path = _remap_path_to_repo(str(latest_payload.get("manifest") or ""), repo_root)
        if not manifest_path.exists():
            raise FileNotFoundError(f"Surface manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return manifest, str(latest_payload.get("time_slice") or manifest.get("time_slice") or "latest")

    manifest_path = (root / requested / "manifest.json").resolve()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Precomputed surface time_slice '{requested}' not found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest, requested


@lru_cache(maxsize=16)
def _surface_region_file_names(cells_dir_str: str) -> tuple[str, ...]:
    cells_dir = Path(cells_dir_str)
    return tuple(sorted(path.name for path in cells_dir.glob("*.parquet")))


def _tile_starts_for_range(min_value: float, max_value: float, step: int = 10) -> list[int]:
    start = int(math.floor(min_value / float(step)) * step)
    end = int(math.floor(max_value / float(step)) * step)
    if end < start:
        return []
    return list(range(start, end + 1, step))


def _surface_region_files_for_bbox(
    cells_dir: Path,
    bbox_tuple: tuple[float, float, float, float],
) -> list[Path]:
    min_lon, min_lat, max_lon, max_lat = bbox_tuple
    lon_starts = _tile_starts_for_range(min_lon, max_lon)
    lat_starts = _tile_starts_for_range(min_lat, max_lat)
    if not lon_starts or not lat_starts:
        return []

    available = set(_surface_region_file_names(str(cells_dir.resolve())))
    candidates: list[Path] = []
    for lat_start in lat_starts:
        for lon_start in lon_starts:
            name = f"lat{lat_start}_lon{lon_start}.parquet"
            if name in available:
                candidates.append(cells_dir / name)
    return sorted(candidates)


def _legacy_inference_heatmap(
    taxon_id: int,
    taxon: Any,
    location: Optional[str],
    bbox_tuple: tuple[float, float, float, float] | None,
    zoom: int,
    max_cells: int,
) -> dict[str, Any]:
    normalized_location = location.strip() if location else None
    if normalized_location and not gis_lookup.is_valid_location_gid(normalized_location):
        return {
            "speciesId": taxon_id,
            "zoom": zoom,
            "cellSizeDeg": _heatmap_cell_size_degrees(zoom),
            "totalPoints": 0,
            "boundedPoints": 0,
            "maxIntensity": 0.0,
            "cells": [],
        }

    model = _load_inference_model()
    target_species_name = _resolve_target_species_name(taxon, model["class_names"])
    if not target_species_name:
        available = [name for name in model["class_names"] if name != BACKGROUND_CLASS]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Taxon scientific name does not map to a prototype model species.",
                "taxonScientificName": taxon.get("scientific_name"),
                "availableSpecies": available,
            },
        )

    feature_columns: list[str] = list(model["feature_columns"])
    mean = model["mean"]
    std = model["std"]
    std_safe = np.where(std < 1e-8, 1.0, std)

    cell_size = _heatmap_cell_size_degrees(zoom)
    cell_scores: dict[tuple[int, int], float] = {}
    cell_counts: dict[tuple[int, int], int] = {}
    total_points = 0
    bounded_points = 0

    for table in taxa_navigation.iter_filtered_occurrence_tables(
        taxon_id,
        extra_columns=feature_columns,
        location_gid=normalized_location,
    ):
        frame = table.to_pandas()
        if frame.empty:
            continue

        lat_series = pd.to_numeric(frame.get("decimalLatitude"), errors="coerce")
        lon_series = pd.to_numeric(frame.get("decimalLongitude"), errors="coerce")

        work = frame.copy()
        if "decimalLatitude" in work.columns and "lat_sin" in feature_columns:
            lat_rad = np.deg2rad(pd.to_numeric(work["decimalLatitude"], errors="coerce").fillna(0.0).to_numpy())
            work["lat_sin"] = np.sin(lat_rad)
            work["lat_cos"] = np.cos(lat_rad)
        if "decimalLongitude" in work.columns and "lon_sin" in feature_columns:
            lon_rad = np.deg2rad(pd.to_numeric(work["decimalLongitude"], errors="coerce").fillna(0.0).to_numpy())
            work["lon_sin"] = np.sin(lon_rad)
            work["lon_cos"] = np.cos(lon_rad)

        for column in feature_columns:
            if column not in work.columns:
                work[column] = 0.0
        x_raw = work[feature_columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
        x_raw = np.nan_to_num(x_raw, nan=0.0, posinf=0.0, neginf=0.0)
        x_scaled = np.nan_to_num((x_raw - mean) / std_safe, nan=0.0, posinf=0.0, neginf=0.0)
        species_scores = _score_species_with_model(x_scaled, model, target_species_name)

        for lat_value, lon_value, score in zip(lat_series.to_numpy(), lon_series.to_numpy(), species_scores):
            if not np.isfinite(lat_value) or not np.isfinite(lon_value):
                continue
            total_points += 1

            lat_float = float(lat_value)
            lon_float = float(lon_value)

            if bbox_tuple is not None:
                min_lon, min_lat, max_lon, max_lat = bbox_tuple
                if lon_float < min_lon or lon_float > max_lon or lat_float < min_lat or lat_float > max_lat:
                    continue

            bounded_points += 1
            x_index = int(math.floor((lon_float + 180.0) / cell_size))
            y_index = int(math.floor((lat_float + 90.0) / cell_size))
            key = (x_index, y_index)
            cell_scores[key] = cell_scores.get(key, 0.0) + float(score)
            cell_counts[key] = cell_counts.get(key, 0) + 1

    if not cell_scores:
        payload: dict[str, Any] = {
            "speciesId": taxon_id,
            "modelSpecies": target_species_name,
            "zoom": zoom,
            "cellSizeDeg": cell_size,
            "totalPoints": total_points,
            "boundedPoints": bounded_points,
            "maxIntensity": 0.0,
            "cells": [],
            "source": "legacy_fallback",
        }
        if bbox_tuple is not None:
            payload["bbox"] = {
                "minLon": bbox_tuple[0],
                "minLat": bbox_tuple[1],
                "maxLon": bbox_tuple[2],
                "maxLat": bbox_tuple[3],
            }
        return payload

    sorted_cells = sorted(
        cell_scores.items(),
        key=lambda item: (-item[1], item[0][1], item[0][0]),
    )
    if len(sorted_cells) > max_cells:
        sorted_cells = sorted_cells[:max_cells]

    max_score = max(score for _, score in sorted_cells)
    cells: list[dict[str, float | int]] = []
    for (x_index, y_index), score in sorted_cells:
        center_lon = (x_index * cell_size) - 180.0 + (cell_size / 2.0)
        center_lat = (y_index * cell_size) - 90.0 + (cell_size / 2.0)
        count = cell_counts.get((x_index, y_index), 0)
        intensity = float(score) / float(max_score) if max_score > 0 else 0.0
        cells.append({
            "lat": center_lat,
            "lon": center_lon,
            "count": int(count),
            "score": float(score),
            "intensity": intensity,
        })

    payload = {
        "speciesId": taxon_id,
        "modelSpecies": target_species_name,
        "zoom": zoom,
        "cellSizeDeg": cell_size,
        "totalPoints": total_points,
        "boundedPoints": bounded_points,
        "maxIntensity": 1.0 if max_score > 0 else 0.0,
        "cells": cells,
        "source": "legacy_fallback",
    }
    if bbox_tuple is not None:
        payload["bbox"] = {
            "minLon": bbox_tuple[0],
            "minLat": bbox_tuple[1],
            "maxLon": bbox_tuple[2],
            "maxLat": bbox_tuple[3],
        }
    return payload


def _regions_root() -> Path:
    return _repo_root() / "data/gis/regions"


@lru_cache(maxsize=1)
def _available_region_names() -> frozenset[str]:
    root = _regions_root()
    if not root.exists():
        return frozenset()
    return frozenset(path.name for path in root.iterdir() if path.is_dir())


@lru_cache(maxsize=4096)
def _region_raster_catalog(region_dir_str: str) -> dict[str, str]:
    region_dir = Path(region_dir_str)
    if not region_dir.exists():
        return {}
    catalog: dict[str, str] = {}
    for path in region_dir.glob("*.tif"):
        catalog[path.stem] = str(path)
    return catalog


def _find_reference_raster(region_dir: Path) -> Path | None:
    for name in ("bio_1.tif", "dem.tif", "landcover.tif", "koppen_geiger.tif"):
        candidate = region_dir / name
        if candidate.exists():
            return candidate
    return None


def _tile_key_for_point(lat: float, lon: float) -> tuple[int, int]:
    tile_lat = int(math.floor(lat / 10.0) * 10)
    tile_lon = int(math.floor(lon / 10.0) * 10)
    return tile_lat, tile_lon


def _dynamic_bbox_from_center(
    center_lat: float,
    center_lon: float,
    viewport_width_deg: float,
    viewport_height_deg: float,
) -> tuple[float, float, float, float]:
    half_w = viewport_width_deg / 2.0
    half_h = viewport_height_deg / 2.0
    min_lon = max(-180.0, center_lon - half_w)
    max_lon = min(180.0, center_lon + half_w)
    min_lat = max(-90.0, center_lat - half_h)
    max_lat = min(90.0, center_lat + half_h)
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=422, detail="center/viewport produced an empty bbox")
    return min_lon, min_lat, max_lon, max_lat


def _effective_dynamic_density(
    requested_density: int,
    viewport_width_deg: float,
    viewport_height_deg: float,
) -> int:
    world_area = 360.0 * 180.0
    viewport_area = max(0.01, viewport_width_deg * viewport_height_deg)
    area_ratio = max(0.0, min(1.0, viewport_area / world_area))
    max_points = int(
        round(_DYNAMIC_MAX_POINTS_DEFAULT - ((_DYNAMIC_MAX_POINTS_DEFAULT - _DYNAMIC_MAX_POINTS_GLOBAL) * area_ratio))
    )
    max_points = max(_DYNAMIC_MAX_POINTS_GLOBAL, min(_DYNAMIC_MAX_POINTS_DEFAULT, max_points))
    capped_density = max(4, int(math.sqrt(max_points)))
    return min(requested_density, capped_density)


def _dynamic_cache_key(
    taxon_id: int,
    species_name: str,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    density: int,
    apply_range_filter: bool,
    apply_ood_penalty: bool,
    ood_penalty_strength: float,
    time_slice: Optional[str],
) -> tuple[Any, ...]:
    return (
        taxon_id,
        species_name,
        round(min_lon, 5),
        round(min_lat, 5),
        round(max_lon, 5),
        round(max_lat, 5),
        density,
        bool(apply_range_filter),
        bool(apply_ood_penalty),
        round(float(ood_penalty_strength), 4),
        (time_slice or "dynamic"),
    )


def _envelope_ood_penalty(
    lat_values: np.ndarray,
    lon_values: np.ndarray,
    envelope: tuple[float, float, float, float],
    strength: float,
) -> np.ndarray:
    if strength <= 0.0:
        return np.ones(len(lat_values), dtype=np.float64)

    env_min_lon, env_min_lat, env_max_lon, env_max_lat = envelope
    lat_outside = np.where(
        lat_values < env_min_lat,
        env_min_lat - lat_values,
        np.where(lat_values > env_max_lat, lat_values - env_max_lat, 0.0),
    )
    lon_outside = np.where(
        lon_values < env_min_lon,
        env_min_lon - lon_values,
        np.where(lon_values > env_max_lon, lon_values - env_max_lon, 0.0),
    )
    env_mid_lat = (env_min_lat + env_max_lat) / 2.0
    lon_scale = max(0.2, abs(math.cos(math.radians(env_mid_lat))))
    distance = np.sqrt(np.square(lat_outside) + np.square(lon_outside * lon_scale))
    penalty = np.exp(-float(strength) * distance)
    return np.clip(penalty, 0.02, 1.0)


def _dynamic_cache_get(key: tuple[Any, ...]) -> dict[str, Any] | None:
    now = monotonic()
    with _dynamic_cache_lock:
        entry = _dynamic_payload_cache.get(key)
        if entry is None:
            return None
        created_at, payload_json = entry
        if (now - created_at) > _DYNAMIC_CACHE_TTL_SECONDS:
            _dynamic_payload_cache.pop(key, None)
            return None
        _dynamic_payload_cache.move_to_end(key)
    return json.loads(payload_json)


def _dynamic_cache_set(key: tuple[Any, ...], payload: dict[str, Any]) -> None:
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    now = monotonic()
    with _dynamic_cache_lock:
        _dynamic_payload_cache[key] = (now, payload_json)
        _dynamic_payload_cache.move_to_end(key)
        while len(_dynamic_payload_cache) > _DYNAMIC_CACHE_MAX_ENTRIES:
            _dynamic_payload_cache.popitem(last=False)


@lru_cache(maxsize=64)
def _species_occurrence_envelope(taxon_id: int) -> tuple[float, float, float, float] | None:
    rows = taxa_navigation.load_occurrence_points(taxon_id, None)
    if not rows:
        return None

    lat_vals: list[float] = []
    lon_vals: list[float] = []
    for row in rows:
        lat = row.get("latitude")
        lon = row.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            lat_float = float(lat)
            lon_float = float(lon)
            if np.isfinite(lat_float) and np.isfinite(lon_float):
                lat_vals.append(lat_float)
                lon_vals.append(lon_float)

    if len(lat_vals) < 20:
        return None

    lat_arr = np.asarray(lat_vals, dtype=np.float64)
    lon_arr = np.asarray(lon_vals, dtype=np.float64)
    min_lat = float(np.percentile(lat_arr, 1.0)) - 8.0
    max_lat = float(np.percentile(lat_arr, 99.0)) + 8.0
    min_lon = float(np.percentile(lon_arr, 1.0)) - 12.0
    max_lon = float(np.percentile(lon_arr, 99.0)) + 12.0
    min_lat = max(-90.0, min_lat)
    max_lat = min(90.0, max_lat)
    min_lon = max(-180.0, min_lon)
    max_lon = min(180.0, max_lon)
    if min_lat >= max_lat or min_lon >= max_lon:
        return None
    return (min_lon, min_lat, max_lon, max_lat)


def _sample_tile_features(
    region_dir: Path,
    idx_arr: np.ndarray,
    lat_arr: np.ndarray,
    lon_arr: np.ndarray,
    feature_columns: list[str],
    feature_defaults: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    tile_x = np.tile(feature_defaults, (len(idx_arr), 1)).astype(np.float64, copy=False)
    tile_valid = np.zeros(len(idx_arr), dtype=bool)

    catalog = _region_raster_catalog(str(region_dir.resolve()))
    reference_path: Path | None = None
    for name in ("bio_1", "dem", "landcover", "koppen_geiger"):
        path_str = catalog.get(name)
        if path_str:
            reference_path = Path(path_str)
            break
    if reference_path is None:
        return idx_arr, tile_x, tile_valid
    try:
        with _rasterio.open(reference_path) as ds:
            coords = list(zip(lon_arr.tolist(), lat_arr.tolist(), strict=False))
            ref_values = np.fromiter(
                (float(value[0]) for value in ds.sample(coords)),
                dtype=np.float64,
                count=len(coords),
            )
            nodata = ds.nodata
        if nodata is not None:
            tile_valid = np.isfinite(ref_values) & ~np.isclose(ref_values, nodata)
        else:
            tile_valid = np.isfinite(ref_values)
    except OSError:
        return idx_arr, tile_x, tile_valid

    feature_raster_paths: dict[str, Path] = {}
    dem_path_str = catalog.get("dem")
    for feature in feature_columns:
        if feature.startswith("bio_"):
            candidate = catalog.get(feature)
            if candidate:
                feature_raster_paths[feature] = Path(candidate)
        elif feature in {"landcover", "koppen_geiger"}:
            candidate = catalog.get(feature)
            if candidate:
                feature_raster_paths[feature] = Path(candidate)
        elif feature in {"elevation", "dem"} and dem_path_str:
            feature_raster_paths[feature] = Path(dem_path_str)

    for feature_idx, feature in enumerate(feature_columns):
        if feature == "lat_sin":
            tile_x[:, feature_idx] = np.sin(np.deg2rad(lat_arr))
        elif feature == "lat_cos":
            tile_x[:, feature_idx] = np.cos(np.deg2rad(lat_arr))
        elif feature == "lon_sin":
            tile_x[:, feature_idx] = np.sin(np.deg2rad(lon_arr))
        elif feature == "lon_cos":
            tile_x[:, feature_idx] = np.cos(np.deg2rad(lon_arr))
        elif feature == "decimalLatitude":
            tile_x[:, feature_idx] = lat_arr
        elif feature == "decimalLongitude":
            tile_x[:, feature_idx] = lon_arr
        elif feature in feature_raster_paths:
            try:
                with _rasterio.open(feature_raster_paths[feature]) as ds:
                    coords = list(zip(lon_arr.tolist(), lat_arr.tolist(), strict=False))
                    values = np.fromiter(
                        (float(value[0]) for value in ds.sample(coords)),
                        dtype=np.float64,
                        count=len(coords),
                    )
                    nodata = ds.nodata
                if nodata is not None:
                    values = np.where(np.isclose(values, nodata), feature_defaults[feature_idx], values)
                tile_x[:, feature_idx] = np.nan_to_num(
                    values,
                    nan=feature_defaults[feature_idx],
                    posinf=feature_defaults[feature_idx],
                    neginf=feature_defaults[feature_idx],
                )
            except OSError:
                continue
    return idx_arr, tile_x, tile_valid


def get_species_inference_heatmap_dynamic_payload(
    taxon_id: int,
    center_lat: float,
    center_lon: float,
    viewport_width_deg: float,
    viewport_height_deg: float,
    density: int,
    workers: int,
    apply_range_filter: bool,
    apply_ood_penalty: bool,
    ood_penalty_strength: float,
    path_exists: Callable[[Path], bool],
    time_slice: Optional[str] = None,
) -> dict[str, Any]:
    if center_lat < -90 or center_lat > 90 or center_lon < -180 or center_lon > 180:
        raise HTTPException(status_code=422, detail="center is out of world bounds")
    if viewport_width_deg <= 0.0 or viewport_width_deg > 360.0:
        raise HTTPException(status_code=422, detail="viewport_width_deg must be in (0, 360]")
    if viewport_height_deg <= 0.0 or viewport_height_deg > 180.0:
        raise HTTPException(status_code=422, detail="viewport_height_deg must be in (0, 180]")
    if density < 4 or density > 300:
        raise HTTPException(status_code=422, detail="density must be in [4, 300]")
    if workers < 1 or workers > 16:
        raise HTTPException(status_code=422, detail="workers must be in [1, 16]")
    if ood_penalty_strength < 0.0 or ood_penalty_strength > 2.0:
        raise HTTPException(status_code=422, detail="ood_penalty_strength must be in [0, 2]")

    taxon = taxa_navigation.get_taxon_by_id(str(taxon_id))
    if taxon is None:
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    if not path_exists(Path(taxon["path"])):
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")

    model = _load_inference_model()
    target_species_name = _resolve_target_species_name(taxon, model["class_names"])
    if not target_species_name:
        available = [name for name in model["class_names"] if name != BACKGROUND_CLASS]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Taxon scientific name does not map to a prototype model species.",
                "taxonScientificName": taxon.get("scientific_name"),
                "availableSpecies": available,
            },
        )

    min_lon, min_lat, max_lon, max_lat = _dynamic_bbox_from_center(
        center_lat=center_lat,
        center_lon=center_lon,
        viewport_width_deg=viewport_width_deg,
        viewport_height_deg=viewport_height_deg,
    )

    requested_density = density
    effective_density = _effective_dynamic_density(
        requested_density=requested_density,
        viewport_width_deg=viewport_width_deg,
        viewport_height_deg=viewport_height_deg,
    )

    cache_key = _dynamic_cache_key(
        taxon_id=taxon_id,
        species_name=target_species_name,
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        density=effective_density,
        apply_range_filter=apply_range_filter,
        apply_ood_penalty=apply_ood_penalty,
        ood_penalty_strength=ood_penalty_strength,
        time_slice=time_slice,
    )
    cached_payload = _dynamic_cache_get(cache_key)
    if cached_payload is not None:
        dynamic_meta = cached_payload.get("dynamic")
        if not isinstance(dynamic_meta, dict):
            dynamic_meta = {}
            cached_payload["dynamic"] = dynamic_meta
        dynamic_meta["workers"] = workers
        dynamic_meta["cacheHit"] = True
        dynamic_meta["cacheTtlSeconds"] = _DYNAMIC_CACHE_TTL_SECONDS
        dynamic_meta["requestedDensity"] = requested_density
        dynamic_meta["effectiveDensity"] = effective_density
        return cached_payload

    lon_values = np.linspace(min_lon, max_lon, num=effective_density, dtype=np.float64)
    lat_values = np.linspace(min_lat, max_lat, num=effective_density, dtype=np.float64)
    lon_grid, lat_grid = np.meshgrid(lon_values, lat_values)
    lon_flat = lon_grid.ravel()
    lat_flat = lat_grid.ravel()

    feature_columns: list[str] = list(model["feature_columns"])
    feature_defaults = model["mean"].astype(np.float64)
    x = np.tile(feature_defaults, (len(lat_flat), 1)).astype(np.float64, copy=False)
    valid_mask = np.zeros(len(lat_flat), dtype=bool)

    by_tile: dict[tuple[int, int], list[int]] = {}
    for idx, (lat, lon) in enumerate(zip(lat_flat, lon_flat, strict=False)):
        by_tile.setdefault(_tile_key_for_point(float(lat), float(lon)), []).append(idx)

    regions_root = _regions_root()
    if not regions_root.exists():
        raise FileNotFoundError(f"Regions root not found: {regions_root}")
    if _rasterio is None:
        raise FileNotFoundError("rasterio is required for dynamic inference sampling")

    tile_jobs: list[tuple[Path, np.ndarray, np.ndarray, np.ndarray]] = []
    available_regions = _available_region_names()
    for (tile_lat, tile_lon), indexes in by_tile.items():
        region_name = f"lat{tile_lat}_lon{tile_lon}"
        if region_name not in available_regions:
            continue
        region_dir = regions_root / region_name

        idx_arr = np.asarray(indexes, dtype=np.int64)
        lat_arr = lat_flat[idx_arr]
        lon_arr = lon_flat[idx_arr]
        tile_jobs.append((region_dir, idx_arr, lat_arr, lon_arr))

    if workers == 1 or len(tile_jobs) <= 1:
        for region_dir, idx_arr, lat_arr, lon_arr in tile_jobs:
            dst_idx, tile_x, tile_valid = _sample_tile_features(
                region_dir,
                idx_arr,
                lat_arr,
                lon_arr,
                feature_columns,
                feature_defaults,
            )
            x[dst_idx] = tile_x
            valid_mask[dst_idx] = tile_valid
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(tile_jobs))) as executor:
            futures = [
                executor.submit(
                    _sample_tile_features,
                    region_dir,
                    idx_arr,
                    lat_arr,
                    lon_arr,
                    feature_columns,
                    feature_defaults,
                )
                for region_dir, idx_arr, lat_arr, lon_arr in tile_jobs
            ]
            for future in as_completed(futures):
                dst_idx, tile_x, tile_valid = future.result()
                x[dst_idx] = tile_x
                valid_mask[dst_idx] = tile_valid

    if not np.any(valid_mask):
        return {
            "speciesId": taxon_id,
            "modelSpecies": target_species_name,
            "timeSlice": time_slice or "dynamic",
            "maxIntensity": 0.0,
            "totalPoints": 0,
            "boundedPoints": 0,
            "cells": [],
            "source": "dynamic_inference",
            "dynamic": {
                "centerLat": center_lat,
                "centerLon": center_lon,
                "viewportWidthDeg": viewport_width_deg,
                "viewportHeightDeg": viewport_height_deg,
                "density": effective_density,
                "workers": workers,
                "cacheHit": False,
                "cacheTtlSeconds": _DYNAMIC_CACHE_TTL_SECONDS,
                "requestedDensity": requested_density,
                "effectiveDensity": effective_density,
                "applyRangeFilter": apply_range_filter,
                "applyOodPenalty": apply_ood_penalty,
                "oodPenaltyStrength": ood_penalty_strength,
            },
            "bbox": {
                "minLon": min_lon,
                "minLat": min_lat,
                "maxLon": max_lon,
                "maxLat": max_lat,
            },
        }

    mean = model["mean"]
    std = model["std"]
    std_safe = np.where(std < 1e-8, 1.0, std)
    x_valid = x[valid_mask]
    lat_valid = lat_flat[valid_mask]
    lon_valid = lon_flat[valid_mask]

    envelope: tuple[float, float, float, float] | None = None
    if apply_range_filter or apply_ood_penalty:
        envelope = _species_occurrence_envelope(taxon_id)
        if apply_range_filter and envelope is not None:
            env_min_lon, env_min_lat, env_max_lon, env_max_lat = envelope
            within_envelope = (
                (lon_valid >= env_min_lon)
                & (lon_valid <= env_max_lon)
                & (lat_valid >= env_min_lat)
                & (lat_valid <= env_max_lat)
            )
            x_valid = x_valid[within_envelope]
            lat_valid = lat_valid[within_envelope]
            lon_valid = lon_valid[within_envelope]

    if len(lat_valid) == 0:
        return {
            "speciesId": taxon_id,
            "modelSpecies": target_species_name,
            "timeSlice": time_slice or "dynamic",
            "maxIntensity": 0.0,
            "totalPoints": 0,
            "boundedPoints": 0,
            "cells": [],
            "source": "dynamic_inference",
            "dynamic": {
                "centerLat": center_lat,
                "centerLon": center_lon,
                "viewportWidthDeg": viewport_width_deg,
                "viewportHeightDeg": viewport_height_deg,
                "density": effective_density,
                "workers": workers,
                "applyRangeFilter": apply_range_filter,
                "cacheHit": False,
                "cacheTtlSeconds": _DYNAMIC_CACHE_TTL_SECONDS,
                "requestedDensity": requested_density,
                "effectiveDensity": effective_density,
                "applyOodPenalty": apply_ood_penalty,
                "oodPenaltyStrength": ood_penalty_strength,
            },
            "bbox": {
                "minLon": min_lon,
                "minLat": min_lat,
                "maxLon": max_lon,
                "maxLat": max_lat,
            },
            "rangeEnvelope": {
                "minLon": envelope[0],
                "minLat": envelope[1],
                "maxLon": envelope[2],
                "maxLat": envelope[3],
            }
            if envelope is not None
            else None,
        }

    x_scaled = np.nan_to_num((x_valid - mean) / std_safe, nan=0.0, posinf=0.0, neginf=0.0)
    species_scores = _score_species_with_model(x_scaled, model, target_species_name)
    ood_penalty = np.ones(len(species_scores), dtype=np.float64)
    if apply_ood_penalty and envelope is not None and len(species_scores):
        ood_penalty = _envelope_ood_penalty(lat_valid, lon_valid, envelope, ood_penalty_strength)
        species_scores = species_scores * ood_penalty

    max_score = float(np.max(species_scores)) if len(species_scores) else 0.0
    cells: list[dict[str, float | int]] = []
    for lat, lon, score in zip(lat_valid, lon_valid, species_scores, strict=False):
        cells.append({
            "lat": float(lat),
            "lon": float(lon),
            "count": 1,
            "score": float(score),
            "intensity": (float(score) / max_score) if max_score > 0 else 0.0,
        })

    payload = {
        "speciesId": taxon_id,
        "modelSpecies": target_species_name,
        "timeSlice": time_slice or "dynamic",
        "maxIntensity": 1.0 if max_score > 0 else 0.0,
        "totalPoints": int(len(cells)),
        "boundedPoints": int(len(cells)),
        "cells": cells,
        "source": "dynamic_inference",
        "dynamic": {
            "centerLat": center_lat,
            "centerLon": center_lon,
            "viewportWidthDeg": viewport_width_deg,
            "viewportHeightDeg": viewport_height_deg,
            "density": effective_density,
            "workers": workers,
            "applyRangeFilter": apply_range_filter,
            "cacheHit": False,
            "cacheTtlSeconds": _DYNAMIC_CACHE_TTL_SECONDS,
            "requestedDensity": requested_density,
            "effectiveDensity": effective_density,
            "applyOodPenalty": apply_ood_penalty,
            "oodPenaltyStrength": ood_penalty_strength,
            "oodPenaltyApplied": bool(apply_ood_penalty and envelope is not None),
            "oodPenaltyMean": float(np.mean(ood_penalty)) if len(ood_penalty) else 1.0,
        },
        "bbox": {
            "minLon": min_lon,
            "minLat": min_lat,
            "maxLon": max_lon,
            "maxLat": max_lat,
        },
    }
    if envelope is not None:
        payload["rangeEnvelope"] = {
            "minLon": envelope[0],
            "minLat": envelope[1],
            "maxLon": envelope[2],
            "maxLat": envelope[3],
        }
    _dynamic_cache_set(cache_key, payload)
    return payload


def get_species_inference_heatmap_payload(
    taxon_id: int,
    location: Optional[str],
    bbox_tuple: tuple[float, float, float, float] | None,
    zoom: int,
    max_cells: int,
    time_slice: Optional[str],
    path_exists: Callable[[Path], bool],
) -> dict[str, Any]:
    taxon = taxa_navigation.get_taxon_by_id(str(taxon_id))
    if taxon is None:
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    if not path_exists(Path(taxon["path"])):
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")

    try:
        repo_root = _repo_root()
        model = _load_inference_model()
        target_species_name = _resolve_target_species_name(taxon, model["class_names"])
        if not target_species_name:
            available = [name for name in model["class_names"] if name != BACKGROUND_CLASS]
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Taxon scientific name does not map to a prototype model species.",
                    "taxonScientificName": taxon.get("scientific_name"),
                    "availableSpecies": available,
                },
            )

        manifest, resolved_slice = _load_surface_manifest(time_slice)
        cells_dir = _remap_path_to_repo(str(manifest.get("cells_dir") or ""), repo_root)
        if not cells_dir.exists():
            raise FileNotFoundError(f"Surface cells directory not found: {cells_dir}")

        species_info = manifest.get("species", {}).get(target_species_name)
        if not species_info:
            raise FileNotFoundError(f"Species '{target_species_name}' not present in precomputed surface manifest")
        score_column = str(species_info.get("score_column"))

        if bbox_tuple is None:
            region_files = sorted(cells_dir.glob("*.parquet"))
        else:
            region_files = _surface_region_files_for_bbox(cells_dir, bbox_tuple)
        if not region_files:
            raise FileNotFoundError("No precomputed cell parquet files found")

        frames: list[pd.DataFrame] = []
        for path in region_files:
            frame = pd.read_parquet(path, columns=["lat", "lon", score_column])
            if frame.empty:
                continue
            if bbox_tuple is not None:
                min_lon, min_lat, max_lon, max_lat = bbox_tuple
                frame = frame[
                    (frame["lon"] >= min_lon)
                    & (frame["lon"] <= max_lon)
                    & (frame["lat"] >= min_lat)
                    & (frame["lat"] <= max_lat)
                ]
            if not frame.empty:
                frames.append(frame)

        if not frames:
            payload = {
                "speciesId": taxon_id,
                "modelSpecies": target_species_name,
                "timeSlice": resolved_slice,
                "zoom": zoom,
                "cellSizeDeg": _heatmap_cell_size_degrees(zoom),
                "totalPoints": 0,
                "boundedPoints": 0,
                "maxIntensity": 0.0,
                "cells": [],
                "source": "precomputed_surface",
            }
            if bbox_tuple is not None:
                payload["bbox"] = {
                    "minLon": bbox_tuple[0],
                    "minLat": bbox_tuple[1],
                    "maxLon": bbox_tuple[2],
                    "maxLat": bbox_tuple[3],
                }
            return payload

        merged = pd.concat(frames, ignore_index=True)
        cell_size = _heatmap_cell_size_degrees(zoom)
        merged["x_index"] = np.floor((merged["lon"].to_numpy(dtype=np.float64) + 180.0) / cell_size).astype(np.int64)
        merged["y_index"] = np.floor((merged["lat"].to_numpy(dtype=np.float64) + 90.0) / cell_size).astype(np.int64)

        grouped = merged.groupby(["x_index", "y_index"], observed=True).agg(
            score=(score_column, "mean"),
            count=(score_column, "size"),
        )
        grouped = grouped.sort_values(["score", "y_index", "x_index"], ascending=[False, True, True])
        if len(grouped) > max_cells:
            grouped = grouped.head(max_cells)

        max_score = float(grouped["score"].max()) if not grouped.empty else 0.0
        cells: list[dict[str, float | int]] = []
        for index, row in grouped.iterrows():
            if isinstance(index, tuple) and len(index) == 2:
                x_index = int(index[0])
                y_index = int(index[1])
            else:
                x_index = 0
                y_index = 0
            center_lon = (x_index * cell_size) - 180.0 + (cell_size / 2.0)
            center_lat = (y_index * cell_size) - 90.0 + (cell_size / 2.0)
            score = float(row["score"])
            cells.append({
                "lat": center_lat,
                "lon": center_lon,
                "count": int(row["count"]),
                "score": score,
                "intensity": (score / max_score) if max_score > 0 else 0.0,
            })

        payload = {
            "speciesId": taxon_id,
            "modelSpecies": target_species_name,
            "timeSlice": resolved_slice,
            "zoom": zoom,
            "cellSizeDeg": cell_size,
            "totalPoints": int(len(merged)),
            "boundedPoints": int(len(merged)),
            "maxIntensity": 1.0 if max_score > 0 else 0.0,
            "cells": cells,
            "source": "precomputed_surface",
        }
        if bbox_tuple is not None:
            payload["bbox"] = {
                "minLon": bbox_tuple[0],
                "minLat": bbox_tuple[1],
                "maxLon": bbox_tuple[2],
                "maxLat": bbox_tuple[3],
            }
        return payload
    except (FileNotFoundError, OSError):
        try:
            return _legacy_inference_heatmap(
                taxon_id=taxon_id,
                taxon=taxon,
                location=location,
                bbox_tuple=bbox_tuple,
                zoom=zoom,
                max_cells=max_cells,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
