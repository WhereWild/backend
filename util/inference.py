"""Streaming heatmap inference for the Darwin SDM.

Loads an inference bundle (exported by ``scripts/machine_learning/train/export.py``)
and provides ``predict_heatmap_stream(...)`` for per-species NDJSON heatmap APIs.

Typical startup flow (called once at import / FastAPI startup)::

    from util.inference import load_bundle, predict_heatmap_stream

    load_bundle("checkpoints/canary_cactus/inference_bundle.pt")
    stream = predict_heatmap_stream(
        11498251,
        (24.0, -106.0, 32.0, -94.0),
    )

By default, runtime inference prefers CUDA when available and otherwise
falls back to CPU.
"""

from __future__ import annotations

import math
import os
import logging
import queue
from importlib import import_module
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable, Iterator, NamedTuple, cast

import torch

_feature_contract = import_module("scripts.machine_learning._compat").import_feature_contract()
_SAMPLED_FEATURE_GROUPS = _feature_contract.SAMPLED_FEATURE_GROUPS
_UNSAMPLED_FEATURE_GROUPS = _feature_contract.UNSAMPLED_FEATURE_GROUPS

# ---------------------------------------------------------------------------
# Lazy import of model classes — avoids hard-wiring sys.path at module level.
# The first call to ``load_bundle`` patches sys.path once.
# ---------------------------------------------------------------------------
SharedEncoder = None  # type: ignore[assignment]
SpeciesHead = None  # type: ignore[assignment]

# Module-level singleton state.
_bundle: dict[str, Any] | None = None
_encoder: torch.nn.Module | None = None
_heads: dict[int, torch.nn.Module] = {}
_cell_table: dict[str, dict[str, torch.Tensor]] = {}
_cell_table_by_bin: dict[tuple[int, int], dict[str, torch.Tensor]] = {}
_cell_size_deg: float = 0.25
_species_meta: dict[int, dict] = {}
_feature_names: dict[str, list[str]] | None = None
_input_dim: int = 0
_model_uses_mask: bool = False
_device: torch.device = torch.device("cpu")

HEATMAP_DEFAULT_MAX_CELLS = 40000
HEATMAP_DEFAULT_SCORE_BATCH_SIZE = 4096
_QUEUE_PUT_POLL_SECONDS = 0.1
LOGGER = logging.getLogger(__name__)
_MISSING_DATASET = object()


def _feature_group_names(group_name: str) -> list[str]:
    """Return ordered feature names for one stored feature group."""
    if _feature_names is None:
        return []
    return list(_feature_names.get(group_name, []))


def _sampled_static_feature_names() -> list[str]:
    """Return the concatenated GIS-sampleable feature names in model order."""
    names: list[str] = []
    for group_name in _SAMPLED_FEATURE_GROUPS:
        names.extend(_feature_group_names(group_name))
    return names


def _resolve_inference_device() -> torch.device:
    """Resolve runtime device from env config with safe CPU fallback."""
    requested = os.environ.get("WHEREWILD_INFERENCE_DEVICE", "auto").strip().lower()
    if requested == "cpu":
        return torch.device("cpu")
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("WHEREWILD_INFERENCE_DEVICE=cuda set, but CUDA is unavailable")
        return torch.device("cuda")
    if requested != "auto":
        raise ValueError("WHEREWILD_INFERENCE_DEVICE must be one of: auto, cpu, cuda")
    if torch.cuda.is_available():
        return torch.device("cuda")
    LOGGER.info("CUDA unavailable; using CPU for inference (WHEREWILD_INFERENCE_DEVICE=auto)")
    return torch.device("cpu")


def _resolve_cell_table_device(inference_device: torch.device) -> torch.device:
    """Resolve cell_table placement device.

    Defaults to CPU. CUDA placement is opt-in and only allowed when
    WHEREWILD_INFERENCE_DEVICE is explicitly set to ``cuda``.
    """
    requested = os.environ.get("WHEREWILD_INFERENCE_CELL_TABLE_DEVICE", "auto").strip().lower()
    if requested in {"", "auto", "cpu"}:
        return torch.device("cpu")
    if requested != "cuda":
        raise ValueError("WHEREWILD_INFERENCE_CELL_TABLE_DEVICE must be one of: auto, cpu, cuda")

    inference_requested = os.environ.get("WHEREWILD_INFERENCE_DEVICE", "auto").strip().lower()
    if inference_requested != "cuda":
        raise ValueError("WHEREWILD_INFERENCE_CELL_TABLE_DEVICE=cuda requires WHEREWILD_INFERENCE_DEVICE=cuda")
    if inference_device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("WHEREWILD_INFERENCE_CELL_TABLE_DEVICE=cuda set, but CUDA is unavailable")
    return torch.device("cuda")


def _resolve_sampling_workers() -> int:
    """Resolve optional raster sampling worker count from env config."""
    raw = os.environ.get("WHEREWILD_INFERENCE_SAMPLE_WORKERS", "1").strip()
    try:
        workers = int(raw)
    except ValueError as exc:
        raise ValueError("WHEREWILD_INFERENCE_SAMPLE_WORKERS must be an integer >= 1") from exc
    if workers < 1:
        raise ValueError("WHEREWILD_INFERENCE_SAMPLE_WORKERS must be >= 1")
    return workers


def _resolve_sample_chunk_size(score_batch_size: int) -> int:
    """Resolve heatmap sampling chunk size, independent from score batch size."""
    raw = os.environ.get("WHEREWILD_INFERENCE_SAMPLE_CHUNK_SIZE", "8192").strip()
    try:
        requested = int(raw)
    except ValueError as exc:
        raise ValueError("WHEREWILD_INFERENCE_SAMPLE_CHUNK_SIZE must be an integer >= 1") from exc
    if requested < 1:
        raise ValueError("WHEREWILD_INFERENCE_SAMPLE_CHUNK_SIZE must be >= 1")
    return max(score_batch_size, requested)


def _resolve_stream_prefetch_chunks() -> int:
    """Resolve how many prepared stream chunks can queue ahead."""
    raw = os.environ.get("WHEREWILD_INFERENCE_STREAM_PREFETCH_CHUNKS", "2").strip()
    try:
        requested = int(raw)
    except ValueError as exc:
        raise ValueError("WHEREWILD_INFERENCE_STREAM_PREFETCH_CHUNKS must be an integer >= 1") from exc
    if requested < 1:
        raise ValueError("WHEREWILD_INFERENCE_STREAM_PREFETCH_CHUNKS must be >= 1")
    return requested


def _close_dataset_cache(cache: dict[tuple[str, str], Any]) -> None:
    """Close cached raster datasets created during a stream request."""
    for ds in cache.values():
        if ds is _MISSING_DATASET:
            continue
        close = getattr(ds, "close", None)
        if callable(close):
            close()


def _move_cell_table_to_device(
    cell_table: dict[str, dict[str, torch.Tensor]], target_device: torch.device
) -> dict[str, dict[str, torch.Tensor]]:
    """Move tensor payloads in cell_table to target device."""
    if target_device.type == "cpu":
        return cell_table

    moved: dict[str, dict[str, torch.Tensor]] = {}
    for cid, payload in cell_table.items():
        moved_payload: dict[str, torch.Tensor] = {}
        for key, value in payload.items():
            if isinstance(value, torch.Tensor):
                moved_payload[key] = value.to(target_device)
            else:
                moved_payload[key] = value
        moved[cid] = moved_payload
    return moved


def _raw_feature_dim_from_names() -> int | None:
    """Return raw feature dimension from feature names when available."""
    if _feature_names is None:
        return None
    groups = (*_SAMPLED_FEATURE_GROUPS, *_UNSAMPLED_FEATURE_GROUPS)
    return sum(len(_feature_names.get(group_name, [])) for group_name in groups)


def _coerce_model_input(features: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
    """Coerce feature payload to the encoder input width.

    Supports both bundle formats:
    - already-concatenated model inputs (features width == input_dim),
    - raw features plus a separate mask (features+mask width == input_dim).

    Raises ``ValueError`` when the payload cannot be aligned to ``_input_dim``.
    """
    if _input_dim <= 0:
        raise ValueError("_input_dim not set; call load_bundle() first")
    if not isinstance(features, torch.Tensor) or features.ndim != 1:
        raise ValueError(
            f"model features must be a 1-d torch.Tensor; got {type(features).__name__} "
            f"with ndim={getattr(features, 'ndim', '?')}"
        )

    feat = features.to(dtype=torch.float32)
    if int(feat.shape[0]) == _input_dim:
        return feat

    if isinstance(mask, torch.Tensor) and mask.ndim == 1:
        mask_t = mask.to(dtype=torch.float32)
        if int(feat.shape[0] + mask_t.shape[0]) == _input_dim:
            return torch.cat([feat, mask_t], dim=0)

    raise ValueError(
        f"cannot align features ({feat.shape[0]}) + mask ({mask.shape[0] if isinstance(mask, torch.Tensor) else 'None'}) "
        f"to input_dim={_input_dim}"
    )


def _stack_feature_batch(
    features: list[torch.Tensor],
    *,
    target_device: torch.device | None = None,
) -> torch.Tensor:
    """Materialize a contiguous batch tensor from per-cell model inputs.

    Heatmap chunks can mix precomputed cell-table tensors already resident on
    CUDA with freshly sampled feature tensors created on CPU. When that happens,
    reconcile devices only for the mixed batch instead of failing inside
    ``torch.stack``.
    """
    if not features:
        if target_device is None:
            return torch.empty((0, _input_dim), dtype=torch.float32)
        return torch.empty((0, _input_dim), dtype=torch.float32, device=target_device)

    devices = {feature.device for feature in features}
    if len(devices) > 1:
        stack_device = target_device or next(iter(devices))
        features = [feature.to(stack_device) for feature in features]
    return torch.stack(features)


def _payload_model_input(payload: dict[str, torch.Tensor]) -> torch.Tensor:
    """Return a model-ready feature tensor from a payload."""
    features = payload.get("features")
    mask = payload.get("mask")
    if isinstance(features, torch.Tensor):
        if features.ndim != 1:
            raise ValueError("payload features must be a 1-d torch.Tensor")
        if int(features.shape[0]) == _input_dim and features.dtype == torch.float32:
            return features
        return _coerce_model_input(features, mask)
    raise ValueError("payload features must be a torch.Tensor")


def _sampled_feature_support_status() -> tuple[bool, str | None]:
    """Return whether sampled GIS features can produce model-aligned inputs."""
    if _feature_names is None:
        return False, "bundle does not include feature_names required for sampled features"

    raw_dim = _raw_feature_dim_from_names()
    if raw_dim is None:
        return False, "bundle does not include feature_names required for sampled features"
    if raw_dim <= 0:
        bioclimate_dim = len(_feature_names.get("bioclimate", []))
        landclass_dim = len(_feature_names.get("landclass", []))
        terrain_dim = len(_feature_names.get("terrain", []))
        edaphic_dim = len(_feature_names.get("edaphic", []))
        temporal_dim = len(_feature_names.get("temporal", []))
        other_dim = len(_feature_names.get("other", []))
        return (
            False,
            "bundle sampled feature template is empty "
            "("
            f"bioclimate={bioclimate_dim}, landclass={landclass_dim}, terrain={terrain_dim}, "
            f"edaphic={edaphic_dim}, temporal={temporal_dim}, other={other_dim}"
            ")",
        )

    alignable = raw_dim == _input_dim or 2 * raw_dim == _input_dim
    if not alignable:
        return (
            False,
            "sampled feature template does not align with model input width "
            f"(raw_dim={raw_dim}, input_dim={_input_dim})",
        )

    try:
        import rasterio  # noqa: F401
    except ImportError:
        return False, "rasterio is not installed, so GIS sampling is unavailable"

    return True, None


class _HeatmapFeatureConfig(NamedTuple):
    primary_source: str
    allow_fallback: bool


def _resolve_heatmap_feature_mode(
    feature_mode: str, resolution: float, native_resolution: float
) -> _HeatmapFeatureConfig:
    """Resolve feature lookup behavior for heatmap scoring."""
    normalized = feature_mode.strip().lower()
    if normalized == "auto":
        normalized = "prefer_cell_table"

    valid_feature_modes = {"prefer_cell_table", "cell_table_only"}
    if normalized not in valid_feature_modes:
        raise ValueError(
            "feature_mode must be one of ['cell_table_only', 'prefer_cell_table'] "
            "('auto' is accepted as a backward-compatible alias for 'prefer_cell_table')"
        )

    if normalized == "cell_table_only":
        return _HeatmapFeatureConfig("cell_table", False)
    if resolution >= native_resolution:
        return _HeatmapFeatureConfig("cell_table", True)

    sampled_ok, _ = _sampled_feature_support_status()
    if sampled_ok:
        return _HeatmapFeatureConfig("sampled", True)
    return _HeatmapFeatureConfig("cell_table", False)


def _build_heatmap_coords(
    bbox: tuple[float, float, float, float],
    resolution: float,
    max_cells: int | None,
) -> tuple[list[tuple[float, float]], int]:
    """Build output-grid center coordinates and return requested cell count."""
    min_lat, min_lon, max_lat, max_lon = bbox
    lat_lo = int(math.floor(min_lat / resolution))
    lat_hi = int(math.floor(max_lat / resolution))
    lon_lo = int(math.floor(min_lon / resolution))
    lon_hi = int(math.floor(max_lon / resolution))

    n_rows = max(0, lat_hi - lat_lo + 1)
    n_cols = max(0, lon_hi - lon_lo + 1)
    requested_cells = n_rows * n_cols
    if max_cells is not None and requested_cells > max_cells:
        raise ValueError(
            f"Requested heatmap has {requested_cells:,} cells, exceeds max_cells={max_cells:,}. "
            "Increase resolution (coarser grid) or reduce bbox."
        )

    coords: list[tuple[float, float]] = []
    for lat_bin in range(lat_lo, lat_hi + 1):
        center_lat = (lat_bin + 0.5) * resolution
        for lon_bin in range(lon_lo, lon_hi + 1):
            center_lon = (lon_bin + 0.5) * resolution
            coords.append((center_lat, center_lon))

    return coords, requested_cells


def _lazy_import_models() -> None:
    """Import model classes from the training package on first use."""
    global SharedEncoder, SpeciesHead  # noqa: PLW0603
    if SharedEncoder is not None:
        return
    module = None
    try:
        module = import_module("scripts.machine_learning.train.model")
    except ImportError:
        import sys

        train_pkg = str(Path(__file__).resolve().parent.parent / "scripts" / "machine_learning" / "train")
        if train_pkg not in sys.path:
            sys.path.insert(0, train_pkg)
        module = import_module("model")

    SharedEncoder = getattr(module, "SharedEncoder")
    SpeciesHead = getattr(module, "SpeciesHead")


def _bin_index(lat: float, lon: float, size_deg: float) -> tuple[int, int]:
    """Map a coordinate to integer grid bins for a given cell size."""
    lat_bin = int(math.floor(lat / size_deg))
    lon_bin = int(math.floor(lon / size_deg))
    return lat_bin, lon_bin


def _bin_id(lat: float, lon: float, size_deg: float) -> str:
    """Map a coordinate to the canonical cell-id key for a grid size."""
    lat_bin, lon_bin = _bin_index(lat, lon, size_deg)
    return f"cell_{lat_bin}_{lon_bin}"


def _cell_lookup_by_bin(lat: float, lon: float, size_deg: float) -> dict[str, torch.Tensor] | None:
    """Lookup a precomputed cell payload without constructing a string key."""
    cell = _cell_table_by_bin.get(_bin_index(lat, lon, size_deg))
    if cell is not None:
        return cell
    return _cell_table.get(_bin_id(lat, lon, size_deg))


def _parse_cell_id(cell_id: str) -> tuple[int, int] | None:
    """Parse a canonical cell id like ``cell_<lat_bin>_<lon_bin>``."""
    if not cell_id.startswith("cell_"):
        return None
    try:
        lat_str, lon_str = cell_id[5:].split("_", 1)
        return int(lat_str), int(lon_str)
    except (TypeError, ValueError):
        return None


def _normalize_loaded_cell_payload(payload: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Normalize one loaded cell payload so its feature vector is model-ready."""
    normalized = dict(payload)
    normalized["features"] = _payload_model_input(payload).to(dtype=torch.float32).contiguous()
    mask = payload.get("mask")
    if isinstance(mask, torch.Tensor):
        normalized["mask"] = mask.to(dtype=torch.float32).contiguous()
    return normalized


# ---------------------------------------------------------------------------
# On-the-fly GIS feature sampling
# ---------------------------------------------------------------------------
_DEM_DERIVED = frozenset({"slope", "aspect", "aspect_deg"})


def _meters_per_degree(lat_deg: float) -> tuple[float, float]:
    """Metres-per-degree for latitude/longitude at *lat_deg*."""
    import numpy as np

    r = np.deg2rad(lat_deg)
    m_lat = 111132.92 - 559.82 * np.cos(2 * r) + 1.175 * np.cos(4 * r) - 0.0023 * np.cos(6 * r)
    m_lon = 111412.84 * np.cos(r) - 93.5 * np.cos(3 * r) + 0.118 * np.cos(5 * r)
    return float(m_lat), float(m_lon)


def _aspect_bin(deg: float) -> int:
    """8-bin compass classification matching ``enrich_tree``."""
    a = deg % 360.0
    if a < 22.5 or a >= 337.5:
        return 1
    if a < 67.5:
        return 2
    if a < 112.5:
        return 3
    if a < 157.5:
        return 4
    if a < 202.5:
        return 5
    if a < 247.5:
        return 6
    if a < 292.5:
        return 7
    return 8


def _batch_sample_raster(
    layer_id: str,
    coords: list[tuple[float, float]],
    dataset_cache: dict[tuple[str, str], Any] | None = None,
) -> list[float | None]:
    """Sample one raster layer at many points, opening each region tile once."""
    import rasterio
    from util.gis_lookup import get_cog_path, get_region_name

    results: list[float | None] = [None] * len(coords)
    groups: dict[str, list[tuple[int, float, float]]] = {}
    for i, (lat, lon) in enumerate(coords):
        groups.setdefault(get_region_name(lat, lon), []).append((i, lat, lon))

    def _write_samples_from_dataset(ds: Any, members: list[tuple[int, float, float]]) -> None:
        nodata = ds.nodata
        xy = [(lon, lat) for _, lat, lon in members]
        idx_list = [i for i, _, _ in members]
        for arr, idx in zip(ds.sample(xy), idx_list):
            val = arr[0]
            if nodata is not None and val == nodata:
                continue
            if isinstance(val, float) and val != val:
                continue
            results[idx] = float(val)

    for _region, members in groups.items():
        if dataset_cache is not None:
            cache_key = (layer_id, _region)
            cached = dataset_cache.get(cache_key)
            if cached is _MISSING_DATASET:
                continue
            if cached is None:
                _, ref_lat, ref_lon = members[0]
                cog_path = get_cog_path(layer_id, ref_lat, ref_lon)
                if cog_path is None or not cog_path.exists():
                    dataset_cache[cache_key] = _MISSING_DATASET
                    continue
                cached = rasterio.open(cog_path)
                dataset_cache[cache_key] = cached
            _write_samples_from_dataset(cached, members)
        else:
            _, ref_lat, ref_lon = members[0]
            cog_path = get_cog_path(layer_id, ref_lat, ref_lon)
            if cog_path is None or not cog_path.exists():
                continue
            with rasterio.open(cog_path) as ds:
                _write_samples_from_dataset(ds, members)
    return results


def _batch_compute_dem_derived(
    coords: list[tuple[float, float]],
    dem_dataset_cache: dict[tuple[str, str], Any] | None = None,
) -> list[dict[str, float]]:
    """Batch DEM-derived features, opening each region COG once."""
    import numpy as np
    import rasterio
    from rasterio.windows import Window
    from util.gis_lookup import get_cog_path, get_region_name

    results: list[dict[str, float]] = [{} for _ in coords]
    groups: dict[str, list[tuple[int, float, float]]] = {}
    for i, (lat, lon) in enumerate(coords):
        groups.setdefault(get_region_name(lat, lon), []).append((i, lat, lon))

    def _write_dem_derived_from_dataset(ds: Any, members: list[tuple[int, float, float]]) -> None:
        nodata = ds.nodata
        pw = abs(float(ds.transform.a))
        ph = abs(float(ds.transform.e))
        for idx, lat, lon in members:
            row, col = ds.index(lon, lat)
            if row - 1 < 0 or col - 1 < 0 or row + 1 >= ds.height or col + 1 >= ds.width:
                continue
            win = ds.read(indexes=1, window=Window(col - 1, row - 1, 3, 3), boundless=False)  # type: ignore[call-arg]
            if win.shape != (3, 3):
                continue
            if nodata is not None and np.any(win == nodata):
                continue
            if np.any(np.isnan(win)):
                continue
            m_lat, m_lon = _meters_per_degree(lat)
            dx = pw * m_lon
            dy = ph * m_lat
            if dx == 0 or dy == 0:
                continue
            z1, z2, z3 = win[0, 0], win[0, 1], win[0, 2]
            z4, _, z6 = win[1, 0], win[1, 1], win[1, 2]
            z7, z8, z9 = win[2, 0], win[2, 1], win[2, 2]
            dzdx = ((z3 + 2 * z6 + z9) - (z1 + 2 * z4 + z7)) / (8.0 * dx)
            dzdy = ((z7 + 2 * z8 + z9) - (z1 + 2 * z2 + z3)) / (8.0 * dy)
            slope_deg = float(np.degrees(np.arctan(np.sqrt(dzdx**2 + dzdy**2))))
            if dzdx == 0 and dzdy == 0:
                asp_deg = 0.0
            else:
                asp_deg = float(90.0 - np.degrees(np.arctan2(dzdy, -dzdx)))
                if asp_deg < 0:
                    asp_deg += 360.0
            results[idx] = {"slope": slope_deg, "aspect": float(_aspect_bin(asp_deg)), "aspect_deg": asp_deg}

    for _region, members in groups.items():
        if dem_dataset_cache is not None:
            cache_key = ("elevation", _region)
            cached = dem_dataset_cache.get(cache_key)
            if cached is _MISSING_DATASET:
                continue
            if cached is None:
                _, ref_lat, ref_lon = members[0]
                dem_path = get_cog_path("elevation", ref_lat, ref_lon)
                if dem_path is None or not dem_path.exists():
                    dem_dataset_cache[cache_key] = _MISSING_DATASET
                    continue
                cached = rasterio.open(dem_path)
                dem_dataset_cache[cache_key] = cached
            _write_dem_derived_from_dataset(cached, members)
        else:
            _, ref_lat, ref_lon = members[0]
            dem_path = get_cog_path("elevation", ref_lat, ref_lon)
            if dem_path is None or not dem_path.exists():
                continue
            with rasterio.open(dem_path) as ds:
                _write_dem_derived_from_dataset(ds, members)
    return results


def _batch_sample_features(
    coords: list[tuple[float, float]],
    *,
    raster_dataset_cache: dict[tuple[str, str], Any] | None = None,
    dem_dataset_cache: dict[tuple[str, str], Any] | None = None,
) -> list[dict[str, torch.Tensor] | None]:
    """Batch-sample static features for many coordinates.

    Opens each GIS raster once per 10-degree region rather than once per
    coordinate, so this is efficient enough for heatmap-sized batches.
    """
    if _feature_names is None:
        return [None] * len(coords)
    try:
        import rasterio  # noqa: F401
    except ImportError:
        return [None] * len(coords)

    sampled_group_names = {group_name: _feature_group_names(group_name) for group_name in _SAMPLED_FEATURE_GROUPS}
    temporal_dim: int = len(_feature_names.get("temporal", []))
    other_dim: int = len(_feature_names.get("other", []))
    n_coords = len(coords)

    layer_vals: dict[str, list[float | None]] = {}
    sampled_static_names = _sampled_static_feature_names()
    layer_names = [name for name in sampled_static_names if name not in _DEM_DERIVED]
    sampling_workers = _resolve_sampling_workers()

    def _sample_layers(target_coords: list[tuple[float, float]], names: list[str]) -> dict[str, list[float | None]]:
        """Sample raster layers for a coordinate subset."""
        sampled: dict[str, list[float | None]] = {}
        if not names:
            return sampled
        # For a single layer, thread-pool setup/teardown overhead tends to
        # exceed any benefit, so keep that path serial.
        if sampling_workers == 1 or len(names) <= 1:
            for name in names:
                sampled[name] = _batch_sample_raster(name, target_coords, dataset_cache=raster_dataset_cache)
            return sampled

        from concurrent.futures import ThreadPoolExecutor

        def _sample_layer(layer_name: str) -> tuple[str, list[float | None]]:
            return layer_name, _batch_sample_raster(layer_name, target_coords, dataset_cache=raster_dataset_cache)

        max_workers = min(sampling_workers, len(names))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for name, values in pool.map(_sample_layer, names):
                sampled[name] = values
        return sampled

    # Conservative prefilter to skip expensive full-layer sampling for obvious
    # no-data points. These anchors are chosen because they are broad-coverage,
    # static layers with good land/ocean discrimination, so a hit in any one of
    # them is a strong signal to keep the coordinate for full sampling.
    prefilter_names = [name for name in ("elevation", "landcover", "bio_1") if name in layer_names]
    active_indices = list(range(n_coords))
    active_coords = coords
    if prefilter_names:
        prefilter_vals = _sample_layers(coords, prefilter_names)
        layer_vals.update(prefilter_vals)
        keep_mask = [False] * n_coords
        for name in prefilter_names:
            values = prefilter_vals[name]
            for i, val in enumerate(values):
                if val is not None:
                    keep_mask[i] = True
        active_indices = [i for i, keep in enumerate(keep_mask) if keep]
        if not active_indices:
            return [None] * n_coords
        active_coords = [coords[i] for i in active_indices]

    remaining_layers = [name for name in layer_names if name not in layer_vals]
    if active_indices and remaining_layers:
        sampled_remaining = _sample_layers(active_coords, remaining_layers)
        for name, vals in sampled_remaining.items():
            full_vals: list[float | None] = [None] * n_coords
            for pos, global_idx in enumerate(active_indices):
                full_vals[global_idx] = vals[pos]
            layer_vals[name] = full_vals

    needs_dem = _DEM_DERIVED & set(sampled_static_names)
    dem_results: list[dict[str, float]] = [{} for _ in range(n_coords)]
    if needs_dem and active_indices:
        dem_active = _batch_compute_dem_derived(active_coords, dem_dataset_cache=dem_dataset_cache)
        for pos, global_idx in enumerate(active_indices):
            dem_results[global_idx] = dem_active[pos]

    out: list[dict[str, torch.Tensor] | None] = []
    for i in range(n_coords):
        features: list[float] = []
        mask: list[float] = []
        for group_name in _SAMPLED_FEATURE_GROUPS:
            for name in sampled_group_names[group_name]:
                val = dem_results[i].get(name) if name in _DEM_DERIVED else layer_vals[name][i]
                if val is None:
                    features.append(0.0)
                    mask.append(1.0)
                else:
                    features.append(val)
                    mask.append(0.0)

        features.extend([0.0] * temporal_dim)
        mask.extend([1.0] * temporal_dim)
        features.extend([0.0] * other_dim)
        mask.extend([1.0] * other_dim)
        ft = torch.tensor(features, dtype=torch.float32)
        mt = torch.tensor(mask, dtype=torch.float32)
        ft[mt > 0.5] = 0.0

        # Skip if every static feature is missing (e.g. ocean).
        static_width = len(sampled_static_names)
        static_missing = sum(mask[:static_width])
        if static_missing == static_width:
            out.append(None)
        else:
            model_input = _coerce_model_input(ft, mt)
            out.append({"features": model_input, "mask": mt})
    return out


def load_bundle(path: str | Path) -> None:
    """Load an inference bundle into module-level singletons.

    Safe to call multiple times (reloads the bundle).  Should be called
    once during application startup.
    """
    global _bundle, _encoder, _heads, _cell_table, _cell_table_by_bin, _cell_size_deg, _species_meta  # noqa: PLW0603
    global _feature_names, _input_dim, _model_uses_mask, _device  # noqa: PLW0603

    _lazy_import_models()
    _device = _resolve_inference_device()
    cell_table_device = _resolve_cell_table_device(_device)

    # Keep bundle tensors on CPU at load time. The bundle includes a large
    # cell_table; mapping the full payload directly to CUDA can exhaust GPU
    # memory. We move only encoder/heads and runtime batches to _device.
    loaded = torch.load(str(path), map_location="cpu", weights_only=False)
    if not isinstance(loaded, dict):
        raise ValueError("Invalid inference bundle: expected dict payload.")
    _bundle = loaded

    input_dim: int = loaded["input_dim"]
    embed_dim: int = loaded["embed_dim"]
    hidden_dim: int = loaded["hidden_dim"]
    _input_dim = input_dim

    if SharedEncoder is None or SpeciesHead is None:
        raise RuntimeError("Training model classes are unavailable.")

    encoder = SharedEncoder(input_dim, embed_dim=embed_dim, hidden_dim=hidden_dim).to(_device)
    encoder.load_state_dict(loaded["encoder_state_dict"])
    encoder.eval()
    for p in encoder.parameters():
        p.requires_grad = False
    _encoder = encoder

    _heads = {}
    for sp_key, state in loaded["head_states"].items():
        head = SpeciesHead(embed_dim=embed_dim).to(_device)
        head.load_state_dict(state)
        head.eval()
        for p in head.parameters():
            p.requires_grad = False
        _heads[int(sp_key)] = head

    _cell_table = loaded.get("cell_table", {})
    _cell_table = _move_cell_table_to_device(_cell_table, cell_table_device)
    _cell_size_deg = loaded.get("cell_size_deg", 0.25)
    _species_meta = loaded.get("species_meta", {})
    _feature_names = loaded.get("feature_names")

    raw_dim = _raw_feature_dim_from_names()
    _model_uses_mask = raw_dim is not None and input_dim == raw_dim * 2
    normalized_table: dict[str, dict[str, torch.Tensor]] = {}
    normalized_by_bin: dict[tuple[int, int], dict[str, torch.Tensor]] = {}
    bad_cells: list[str] = []
    for cid, payload in _cell_table.items():
        try:
            normalized_payload = _normalize_loaded_cell_payload(payload)
        except ValueError:
            bad_cells.append(cid)
            continue
        normalized_table[cid] = normalized_payload
        cell_key = _parse_cell_id(cid)
        if cell_key is not None:
            normalized_by_bin[cell_key] = normalized_payload
    if bad_cells:
        raise ValueError(
            f"{len(bad_cells):,} cell(s) in bundle have incompatible feature width "
            f"(expected {_input_dim}); first bad cell: {bad_cells[0]}"
        )
    _cell_table = normalized_table
    _cell_table_by_bin = normalized_by_bin


def is_loaded() -> bool:
    """True when a bundle has been successfully loaded."""
    return _encoder is not None


def known_species() -> list[int]:
    """Return the list of species keys that have trained heads."""
    return sorted(_heads.keys())


def species_meta() -> dict[int, dict]:
    """Return per-species training metadata (prior, counts, val_loss)."""
    return dict(_species_meta)


def cell_count() -> int:
    """Return the number of cells in the loaded lookup table."""
    return len(_cell_table)


def predict_heatmap_stream(
    species_key: int,
    bbox: tuple[float, float, float, float],
    *,
    resolution: float | None = None,
    include_source: bool = False,
    feature_mode: str = "prefer_cell_table",
    max_cells: int | None = HEATMAP_DEFAULT_MAX_CELLS,
    score_batch_size: int = HEATMAP_DEFAULT_SCORE_BATCH_SIZE,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Stream a species heatmap as an iterator of scored cells.

    This variant avoids constructing a giant ``cells`` list in memory and is
    suitable for NDJSON/SSE APIs. It yields one scored cell dict at a time.
    """
    if _encoder is None:
        raise RuntimeError("Inference bundle not loaded. Call load_bundle() first.")
    if species_key not in _heads:
        raise KeyError(f"Species {species_key} not in loaded bundle.")
    encoder = _encoder

    native = _cell_size_deg
    res = resolution if resolution is not None else native
    if res <= 0:
        raise ValueError("resolution must be > 0")
    min_lat, min_lon, max_lat, max_lon = bbox

    if min_lat >= max_lat:
        raise ValueError("min_lat must be less than max_lat")
    if min_lon >= max_lon:
        raise ValueError("min_lon must be less than max_lon")
    if score_batch_size <= 0:
        raise ValueError("score_batch_size must be > 0")

    coords, requested_cells = _build_heatmap_coords(bbox, res, max_cells)
    feature_config = _resolve_heatmap_feature_mode(
        feature_mode,
        res,
        native,
    )
    primary_source, allow_fallback = feature_config

    head = _heads[species_key]
    sample_chunk_size = _resolve_sample_chunk_size(score_batch_size)
    prefetch_chunks = _resolve_stream_prefetch_chunks()
    raster_dataset_cache: dict[tuple[str, str], Any] = {}
    dem_dataset_cache: dict[tuple[str, str], Any] = {}

    def _prepare_stream_chunk(
        chunk_coords: list[tuple[float, float]],
    ) -> tuple[list[tuple[float, float]], list[int], torch.Tensor | None, list[str | None] | None]:
        """Resolve features for one stream chunk before model scoring."""
        features_per_coord: list[torch.Tensor | None] = [None] * len(chunk_coords)
        feature_source_per_coord: list[str | None] | None = (
            cast(list[str | None], [None] * len(chunk_coords)) if include_source else None
        )
        missing_indices: list[int] = []
        missing_coords: list[tuple[float, float]] = []

        if primary_source == "cell_table":
            for i, (lat, lon) in enumerate(chunk_coords):
                cell = _cell_lookup_by_bin(lat, lon, native)
                if cell is not None:
                    features_per_coord[i] = cell["features"]
                    if feature_source_per_coord is not None:
                        feature_source_per_coord[i] = "cell_table"
                    continue
                missing_indices.append(i)
                missing_coords.append((lat, lon))

            if allow_fallback and missing_coords:
                sampled = _batch_sample_features(
                    missing_coords,
                    raster_dataset_cache=raster_dataset_cache,
                    dem_dataset_cache=dem_dataset_cache,
                )
                for i, cell in zip(missing_indices, sampled):
                    if cell is not None:
                        features_per_coord[i] = cell["features"]
                        if feature_source_per_coord is not None:
                            feature_source_per_coord[i] = "sampled"
        else:
            sampled = _batch_sample_features(
                chunk_coords,
                raster_dataset_cache=raster_dataset_cache,
                dem_dataset_cache=dem_dataset_cache,
            )
            for i, cell in enumerate(sampled):
                if cell is not None:
                    features_per_coord[i] = cell["features"]
                    if feature_source_per_coord is not None:
                        feature_source_per_coord[i] = "sampled"
                    continue
                missing_indices.append(i)
                missing_coords.append(chunk_coords[i])

            if allow_fallback and missing_coords:
                for i, (lat, lon) in zip(missing_indices, missing_coords, strict=True):
                    cell = _cell_lookup_by_bin(lat, lon, native)
                    if cell is not None:
                        features_per_coord[i] = cell["features"]
                        if feature_source_per_coord is not None:
                            feature_source_per_coord[i] = "cell_table"

        valid_indices: list[int] = []
        valid_features: list[torch.Tensor] = []
        for i, feat in enumerate(features_per_coord):
            if feat is None:
                continue
            valid_indices.append(i)
            valid_features.append(feat)
        stacked_features = _stack_feature_batch(valid_features, target_device=_device) if valid_features else None
        return chunk_coords, valid_indices, stacked_features, feature_source_per_coord

    def _iter_cells() -> Iterator[dict[str, Any]]:
        """Yield scored cells chunk-by-chunk to keep streaming memory-bounded."""
        try:
            with torch.no_grad():
                # Producer/consumer queue allows multiple prepared chunks to
                # stay ahead so raster reads overlap scoring and streaming.
                chunk_queue: queue.Queue[
                    tuple[list[tuple[float, float]], list[int], torch.Tensor | None, list[str | None] | None]
                    | Exception
                    | None
                ] = queue.Queue(maxsize=prefetch_chunks)
                stop_event = Event()

                def _put_queue_item(item: Any) -> None:
                    while True:
                        if stop_event.is_set():
                            return
                        try:
                            chunk_queue.put(item, timeout=_QUEUE_PUT_POLL_SECONDS)
                            return
                        except queue.Full:
                            continue

                def _prefetch_chunks() -> None:
                    try:
                        for chunk_start in range(0, len(coords), sample_chunk_size):
                            if stop_event.is_set():
                                return
                            if cancel_check is not None and cancel_check():
                                return
                            prepared = _prepare_stream_chunk(coords[chunk_start : chunk_start + sample_chunk_size])
                            _put_queue_item(prepared)
                    except Exception as exc:  # pragma: no cover - runtime guard
                        _put_queue_item(exc)
                    finally:
                        _put_queue_item(None)

                # Daemon so a stuck raster read can't prevent process exit
                # under SIGTERM; normal path joins explicitly in the finally block.
                prefetch_thread = Thread(target=_prefetch_chunks, name="wherewild-heatmap-prefetch", daemon=True)
                prefetch_thread.start()
                try:
                    while True:
                        if cancel_check is not None and cancel_check():
                            stop_event.set()
                            return

                        item = chunk_queue.get()
                        if item is None:
                            return
                        if isinstance(item, Exception):
                            raise item

                        chunk_coords, valid_indices, valid_feature_tensor, feature_source_per_coord = item
                        if valid_feature_tensor is None or valid_feature_tensor.numel() == 0:
                            continue

                        scores_list: list[float] = []
                        for start in range(0, int(valid_feature_tensor.shape[0]), score_batch_size):
                            batch_features = valid_feature_tensor[start : start + score_batch_size]
                            if batch_features.device != _device:
                                batch_features = batch_features.to(_device)
                            embeddings = encoder(batch_features)
                            logits = head(embeddings)
                            scores_list.extend(torch.sigmoid(logits).cpu().tolist())

                        for idx, score in zip(valid_indices, scores_list):
                            if cancel_check is not None and cancel_check():
                                stop_event.set()
                                return
                            lat, lon = chunk_coords[idx]
                            cell_entry: dict[str, Any] = {
                                "lat": round(lat, 4),
                                "lon": round(lon, 4),
                                "score": round(score, 6),
                                "n_native": 1,
                            }
                            if include_source and feature_source_per_coord is not None:
                                cell_entry["source"] = feature_source_per_coord[idx] or "unknown"
                            yield cell_entry
                finally:
                    stop_event.set()
                    prefetch_thread.join(timeout=1.0)
                    if prefetch_thread.is_alive():
                        logging.warning(
                            "wherewild-heatmap-prefetch thread did not terminate within 1s; "
                            "waiting up to 5s more before closing dataset caches."
                        )
                        prefetch_thread.join(timeout=5.0)
                        if prefetch_thread.is_alive():
                            logging.error(
                                "wherewild-heatmap-prefetch thread is still running after "
                                "extended shutdown wait; proceeding to close dataset caches "
                                "anyway."
                            )
        finally:
            _close_dataset_cache(raster_dataset_cache)
            _close_dataset_cache(dem_dataset_cache)

    return {
        "species_key": species_key,
        "bbox": list(bbox),
        "resolution": res,
        "native_resolution": native,
        "requested_cells": requested_cells,
        "cells": _iter_cells(),
    }
