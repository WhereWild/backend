"""Bundle loading and inference helpers for the Darwin SDM.

Loads an inference bundle exported by
``scripts/machine_learning/train/export.py`` and exposes runtime helpers used
by the tile-rendering backend.

By default, runtime inference prefers CUDA when available and otherwise
falls back to CPU.
"""

from __future__ import annotations

import math
import os
import logging
import time
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, NamedTuple, cast

import torch

from util.request_cancellation import CancelCheck

_feature_contract = import_module("scripts.machine_learning._compat").import_feature_contract()
_feature_transforms = import_module("scripts.machine_learning.feature_transforms")
FEATURE_GROUPS = _feature_contract.FEATURE_GROUPS
_SAMPLED_FEATURE_GROUPS = _feature_contract.SAMPLED_FEATURE_GROUPS
_UNSAMPLED_FEATURE_GROUPS = _feature_contract.UNSAMPLED_FEATURE_GROUPS
feature_template_dict = _feature_contract.feature_template_dict
normalize_feature_transform_spec = _feature_transforms.normalize_feature_transform_spec
transform_feature_matrices = _feature_transforms.transform_feature_matrices

# ---------------------------------------------------------------------------
# Lazy import of model classes — avoids hard-wiring sys.path at module level.
# The first call to ``load_bundle`` patches sys.path once.
# ---------------------------------------------------------------------------
SharedEncoder = None  # type: ignore[assignment]
SpeciesHead = None  # type: ignore[assignment]
CombinedSpeciesHead = None  # type: ignore[assignment]

# Module-level singleton state.
_bundle: dict[str, Any] | None = None
_encoder: torch.nn.Module | None = None
_heads: dict[int, torch.nn.Module] = {}
_combined_head: torch.nn.Module | None = None
_cell_table: dict[str, torch.Tensor] = {}
_cell_table_by_bin: dict[tuple[int, int], torch.Tensor] = {}
_cell_size_deg: float = 0.25
_species_meta: dict[int, dict] = {}
_combined_species_keys: list[int] = []
_combined_head_meta: dict[str, Any] | None = None
_combined_species_head_class_indices: list[int] = []
_raw_feature_names: dict[str, list[str]] | None = None
_feature_names: dict[str, list[str]] | None = None
_feature_transforms_spec: dict[str, Any] | None = None
_input_dim: int = 0
_model_uses_mask: bool = False
_device: torch.device = torch.device("cpu")
_bundle_source_path: str | None = None
_bundle_source_mtime_ns: int | None = None

_TEMPORAL_RASTER_DIR = Path(__file__).parent.parent / "data" / "gis" / "temporal" / "rasters"
_GIS_REGIONS_DIR = Path(__file__).parent.parent / "data" / "gis" / "regions"
_DARWIN_VALIDITY_MASK_FILENAME = "darwin_validity_mask.tif"
_TEMPORAL_WINDOW_LABELS: dict[int, str] = {
    1: "1h",
    8: "8h",
    24: "24h",
    72: "3d",
    168: "7d",
    720: "30d",
    2160: "90d",
}
_TEMPORAL_WINDOW_TO_FORECAST_HOURS: dict[int, int] = {
    1: 1,
    8: 8,
    24: 24,
    72: 72,
    168: 168,
    720: 168,
    2160: 168,
}

HEATMAP_DEFAULT_MAX_CELLS = 40000
HEATMAP_DEFAULT_SCORE_BATCH_SIZE = 4096
LOGGER = logging.getLogger(__name__)
_MISSING_DATASET = object()


@dataclass
class SpeciesScoreProfile:
    coord_count: int = 0
    valid_feature_count: int = 0
    unresolved_count: int = 0
    cell_table_count: int = 0
    sampled_count: int = 0
    sample_chunk_size: int = 0
    score_batch_size: int = 0
    chunk_count: int = 0
    feature_prepare_seconds: float = 0.0
    model_score_seconds: float = 0.0
    total_seconds: float = 0.0
    sample_prefilter_seconds: float = 0.0
    sample_static_sampling_seconds: float = 0.0
    sample_dem_seconds: float = 0.0
    sample_temporal_seconds: float = 0.0
    sample_matrix_fill_seconds: float = 0.0
    sample_transform_seconds: float = 0.0
    sample_prefilter_kept_count: int = 0
    sample_prefilter_dropped_count: int = 0
    sample_active_coord_count: int = 0
    sample_static_layer_count: int = 0
    sample_dem_layer_count: int = 0
    sample_temporal_layer_count: int = 0


@dataclass
class SampleFeatureProfile:
    input_coord_count: int = 0
    prefilter_kept_count: int = 0
    prefilter_dropped_count: int = 0
    active_coord_count: int = 0
    static_layer_count: int = 0
    dem_layer_count: int = 0
    temporal_layer_count: int = 0
    prefilter_seconds: float = 0.0
    static_sampling_seconds: float = 0.0
    dem_seconds: float = 0.0
    temporal_seconds: float = 0.0
    matrix_fill_seconds: float = 0.0
    transform_seconds: float = 0.0


def _raw_feature_group_names(group_name: str) -> list[str]:
    """Return ordered raw source feature names for one feature group."""
    if _raw_feature_names is None:
        return []
    return list(_raw_feature_names.get(group_name, []))


def _model_feature_group_names(group_name: str) -> list[str]:
    """Return ordered model-layout feature names for one feature group."""
    if _feature_names is None:
        return []
    return list(_feature_names.get(group_name, []))


def _sampled_static_feature_names() -> list[str]:
    """Return the concatenated GIS-sampleable feature names in model order."""
    names: list[str] = []
    for group_name in _SAMPLED_FEATURE_GROUPS:
        names.extend(_raw_feature_group_names(group_name))
    return names


def _raw_temporal_feature_names() -> list[str]:
    """Return ordered raw temporal feature names."""
    return _raw_feature_group_names("temporal")


def _temporal_feature_span() -> tuple[int, int]:
    """Return [start, end) of temporal features within the model feature vector."""
    static_width = sum(len(_model_feature_group_names(group_name)) for group_name in _SAMPLED_FEATURE_GROUPS)
    temporal_width = len(_model_feature_group_names("temporal"))
    return static_width, static_width + temporal_width


def _filtered_transform_spec_for_groups(group_names: set[str]) -> dict[str, Any] | None:
    """Return the fitted transform spec limited to the selected raw feature groups."""
    if _feature_transforms_spec is None:
        return None

    raw_template = feature_template_dict(_feature_transforms_spec.get("raw_feature_template", {}))
    transformed_template = feature_template_dict(_feature_transforms_spec.get("transformed_feature_template", {}))
    filtered_raw_template = {
        group: list(raw_template.get(group, [])) if group in group_names else [] for group in FEATURE_GROUPS
    }
    filtered_transformed_template = {
        group: list(transformed_template.get(group, [])) if group in group_names else [] for group in FEATURE_GROUPS
    }
    raw_feature_specs = _feature_transforms_spec.get("feature_specs", {})
    allowed_features = {feature_name for group in group_names for feature_name in filtered_raw_template.get(group, [])}
    filtered_feature_specs = {
        feature_name: raw_feature_specs[feature_name]
        for feature_name in allowed_features
        if feature_name in raw_feature_specs
    }
    return {
        "version": _feature_transforms_spec.get("version", "v1"),
        "raw_feature_template": filtered_raw_template,
        "transformed_feature_template": filtered_transformed_template,
        "feature_specs": filtered_feature_specs,
    }


def _raw_feature_template_for_groups(group_names: set[str]) -> dict[str, list[str]]:
    """Return the raw feature template limited to the selected groups."""
    return {
        group_name: _raw_feature_group_names(group_name) if group_name in group_names else []
        for group_name in FEATURE_GROUPS
    }


def _transform_selected_raw_feature_matrices(
    *,
    group_names: set[str],
    raw_feature_template: dict[str, list[str]],
    raw_values: Any,
    raw_masks: Any,
) -> tuple[Any, Any]:
    """Transform selected raw groups and expand them back to full model width."""
    selected_values, selected_masks, selected_template = transform_feature_matrices(
        raw_feature_template=raw_feature_template,
        raw_values=raw_values,
        raw_masks=raw_masks,
        transform_spec=_filtered_transform_spec_for_groups(group_names),
    )

    full_template = {group_name: _model_feature_group_names(group_name) for group_name in FEATURE_GROUPS}
    full_dim = sum(len(full_template[group_name]) for group_name in FEATURE_GROUPS)
    if full_dim <= 0 or selected_values.shape[1] == full_dim:
        return selected_values, selected_masks

    import numpy as np

    values_out = np.zeros((selected_values.shape[0], full_dim), dtype=np.float32)
    masks_out = np.ones((selected_masks.shape[0], full_dim), dtype=np.float32)
    selected_offset = 0
    full_offset = 0
    for group_name in FEATURE_GROUPS:
        full_width = len(full_template[group_name])
        selected_width = len(selected_template.get(group_name, []))
        if selected_width:
            if selected_width != full_width:
                raise ValueError(
                    f"selected transformed width for group {group_name!r} does not align with model template "
                    f"({selected_width} != {full_width})"
                )
            values_out[:, full_offset : full_offset + full_width] = selected_values[
                :, selected_offset : selected_offset + selected_width
            ]
            masks_out[:, full_offset : full_offset + full_width] = selected_masks[
                :, selected_offset : selected_offset + selected_width
            ]
            selected_offset += selected_width
        full_offset += full_width
    return values_out, masks_out


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


def _resolve_darwin_validity_mask_enabled() -> bool:
    """Resolve whether Darwin serving should use the validity mask prefilter."""
    raw = os.environ.get("WHEREWILD_INFERENCE_USE_DARWIN_VALIDITY_MASK", "0").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"", "0", "false", "no", "off"}:
        return False
    raise ValueError("WHEREWILD_INFERENCE_USE_DARWIN_VALIDITY_MASK must be one of: 1, 0, true, false, yes, no, on, off")


def _record_prefilter_profile(
    profile: SpeciesScoreProfile | None,
    *,
    elapsed_seconds: float,
    keep_mask: list[bool],
) -> None:
    """Accumulate one prefilter pass into the species score profile."""
    if profile is None:
        return

    kept_count = sum(keep_mask)
    profile.feature_prepare_seconds += elapsed_seconds
    profile.sample_prefilter_seconds += elapsed_seconds
    profile.sample_prefilter_kept_count += kept_count
    profile.sample_prefilter_dropped_count += len(keep_mask) - kept_count


def _precompute_feature_batch_inputs(
    coords: list[tuple[float, float]],
    *,
    feature_config: _HeatmapFeatureConfig,
    raster_dataset_cache: dict[tuple[str, str], Any],
    profile: SpeciesScoreProfile | None,
) -> tuple[list[torch.Tensor | None] | None, list[bool] | None]:
    """Precompute reusable cell-table hits and sampled prefilter masks for a score request."""
    precomputed_cell_table_features: list[torch.Tensor | None] | None = None
    precomputed_sampled_prefilter_keep_mask: list[bool] | None = None

    if feature_config.primary_source == "sampled":
        prefilter_start = time.perf_counter()
        precomputed_sampled_prefilter_keep_mask, _ = _sample_darwin_prefilter_keep_mask(
            coords,
            dataset_cache=raster_dataset_cache,
        )
        _record_prefilter_profile(
            profile,
            elapsed_seconds=time.perf_counter() - prefilter_start,
            keep_mask=precomputed_sampled_prefilter_keep_mask,
        )
        return None, precomputed_sampled_prefilter_keep_mask

    if feature_config.primary_source != "cell_table" or not feature_config.allow_fallback:
        return None, None

    precomputed_cell_table_features = []
    missing_indices: list[int] = []
    missing_coords: list[tuple[float, float]] = []
    for index, (lat, lon) in enumerate(coords):
        cell = _cell_lookup_by_bin(lat, lon, _cell_size_deg)
        precomputed_cell_table_features.append(cell)
        if cell is None:
            missing_indices.append(index)
            missing_coords.append((lat, lon))

    if not missing_coords:
        return precomputed_cell_table_features, None

    prefilter_start = time.perf_counter()
    missing_keep_mask, _ = _sample_darwin_prefilter_keep_mask(
        missing_coords,
        dataset_cache=raster_dataset_cache,
    )
    precomputed_sampled_prefilter_keep_mask = [True] * len(coords)
    for index, keep in zip(missing_indices, missing_keep_mask, strict=True):
        precomputed_sampled_prefilter_keep_mask[index] = keep
    _record_prefilter_profile(
        profile,
        elapsed_seconds=time.perf_counter() - prefilter_start,
        keep_mask=missing_keep_mask,
    )
    return precomputed_cell_table_features, precomputed_sampled_prefilter_keep_mask


def _close_dataset_cache(cache: dict[tuple[str, str], Any]) -> None:
    """Close cached raster datasets created during a stream request."""
    for ds in cache.values():
        if ds is _MISSING_DATASET:
            continue
        close = getattr(ds, "close", None)
        if callable(close):
            close()


def _check_cancel(cancel_check: CancelCheck | None) -> None:
    if cancel_check is not None:
        cancel_check()


def _move_cell_table_to_device(
    cell_table: dict[str, torch.Tensor], target_device: torch.device
) -> dict[str, torch.Tensor]:
    """Move cell-table tensors to the target device."""
    if target_device.type == "cpu":
        return cell_table

    return {cid: payload.to(target_device) for cid, payload in cell_table.items()}


def _raw_feature_dim_from_names() -> int | None:
    """Return raw sampled feature dimension from raw feature names when available."""
    if _raw_feature_names is None:
        return None
    groups = (*_SAMPLED_FEATURE_GROUPS, *_UNSAMPLED_FEATURE_GROUPS)
    return sum(len(_raw_feature_names.get(group_name, [])) for group_name in groups)


def _model_feature_dim_from_names() -> int | None:
    """Return transformed model feature dimension from feature names when available."""
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

    if isinstance(mask, torch.Tensor):
        mask_tensor = cast(torch.Tensor, mask)
        if mask_tensor.ndim != 1:
            raise ValueError("mask must be a 1-d torch.Tensor")
        mask_t = mask_tensor.to(dtype=torch.float32)
        if int(feat.shape[0] + mask_t.shape[0]) == _input_dim:
            return torch.cat([feat, mask_t], dim=0)
        mask_width = mask_tensor.shape[0]
    else:
        mask_width = "None"
    raise ValueError(f"cannot align features ({feat.shape[0]}) + mask ({mask_width}) to input_dim={_input_dim}")


def _coerce_model_input_batch(features: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
    """Coerce batched raw features and masks to encoder input width."""
    if _input_dim <= 0:
        raise ValueError("_input_dim not set; call load_bundle() first")
    if not isinstance(features, torch.Tensor) or features.ndim != 2:
        raise ValueError(
            f"batched model features must be a 2-d torch.Tensor; got {type(features).__name__} "
            f"with ndim={getattr(features, 'ndim', '?')}"
        )

    feat = features.to(dtype=torch.float32)
    if int(feat.shape[1]) == _input_dim:
        return feat

    if isinstance(mask, torch.Tensor):
        mask_tensor = cast(torch.Tensor, mask)
        if mask_tensor.ndim != 2:
            raise ValueError("batched mask must be a 2-d torch.Tensor")
        mask_t = mask_tensor.to(dtype=torch.float32)
        if int(feat.shape[1] + mask_t.shape[1]) == _input_dim:
            return torch.cat([feat, mask_t], dim=1)
        mask_width = mask_tensor.shape[1]
    else:
        mask_width = "None"
    raise ValueError(f"cannot align batched features ({feat.shape[1]}) + mask ({mask_width}) to input_dim={_input_dim}")


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


def _payload_model_input(payload: torch.Tensor) -> torch.Tensor:
    """Return a model-ready feature tensor from a v2 cell-table payload."""
    if not isinstance(payload, torch.Tensor):
        raise ValueError("cell payload must be a torch.Tensor")
    if payload.ndim != 1:
        raise ValueError("cell payload tensor must be a 1-d torch.Tensor")
    if int(payload.shape[0]) == _input_dim and payload.dtype == torch.float32:
        return payload
    return _coerce_model_input(payload)


def _resolved_feature_model_input(payload: torch.Tensor | dict[str, torch.Tensor]) -> torch.Tensor:
    """Return the model-input tensor from either a cell-table or sampled payload."""
    if isinstance(payload, torch.Tensor):
        return payload
    if isinstance(payload, dict):
        features = payload.get("features")
        if isinstance(features, torch.Tensor):
            return features
        raise ValueError("sampled feature payload missing tensor 'features'")
    raise ValueError(f"unsupported feature payload type: {type(payload).__name__}")


def _sampled_feature_support_status() -> tuple[bool, str | None]:
    """Return whether sampled GIS features can produce model-aligned inputs."""
    if _raw_feature_names is None:
        return False, "bundle does not include raw_feature_names required for sampled features"

    raw_dim = _raw_feature_dim_from_names()
    if raw_dim is None:
        return False, "bundle does not include raw_feature_names required for sampled features"
    if raw_dim <= 0:
        bioclimate_dim = len(_raw_feature_names.get("bioclimate", []))
        landclass_dim = len(_raw_feature_names.get("landclass", []))
        terrain_dim = len(_raw_feature_names.get("terrain", []))
        temporal_dim = len(_raw_feature_names.get("temporal", []))
        other_dim = len(_raw_feature_names.get("other", []))
        return (
            False,
            "bundle sampled feature template is empty "
            "("
            f"bioclimate={bioclimate_dim}, landclass={landclass_dim}, terrain={terrain_dim}, "
            f"temporal={temporal_dim}, other={other_dim}"
            ")",
        )

    model_dim = _model_feature_dim_from_names()
    alignable = model_dim is not None and (model_dim == _input_dim or 2 * model_dim == _input_dim)
    if not alignable:
        return (
            False,
            "sampled feature template does not align with model input width "
            f"(raw_dim={raw_dim}, model_dim={model_dim}, input_dim={_input_dim})",
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


def _prepare_feature_batch_for_coords(
    coords: list[tuple[float, float]],
    *,
    resolution_hint: float,
    include_source: bool,
    feature_mode: str,
    temporal_mode: str = "missing",
    temporal_forecast_hours: int | None = None,
    temporal_raster_cache: dict[tuple[str, int, int], Any] | None = None,
    raster_dataset_cache: dict[tuple[str, str], Any] | None = None,
    dem_dataset_cache: dict[tuple[str, str], Any] | None = None,
    cancel_check: CancelCheck | None = None,
    sample_profile: SampleFeatureProfile | None = None,
    cell_table_features: list[torch.Tensor | None] | None = None,
    sampled_prefilter_keep_mask: list[bool] | None = None,
) -> tuple[list[int], torch.Tensor | None, list[str | None] | None]:
    """Resolve model-ready feature rows for arbitrary coordinates."""
    native = _cell_size_deg
    feature_config = _resolve_heatmap_feature_mode(
        feature_mode,
        resolution_hint,
        native,
    )
    primary_source, allow_fallback = feature_config

    features_per_coord: list[torch.Tensor | None] = [None] * len(coords)
    feature_source_per_coord: list[str | None] | None = (
        cast(list[str | None], [None] * len(coords)) if include_source else None
    )
    missing_indices: list[int] = []
    missing_coords: list[tuple[float, float]] = []
    temporal_names = _raw_temporal_feature_names()
    normalized_temporal_mode = temporal_mode.strip().lower()
    if normalized_temporal_mode not in {"missing", "current"}:
        raise ValueError("temporal_mode must be one of ['current', 'missing']")

    temporal_values = None
    temporal_masks = None
    needs_cell_table_temporal_merge = (
        normalized_temporal_mode == "current"
        and bool(temporal_names)
        and (primary_source == "cell_table" or allow_fallback)
    )
    if needs_cell_table_temporal_merge:
        raw_temporal_values, raw_temporal_masks = _sample_temporal_feature_matrices(
            coords,
            forecast_hours=temporal_forecast_hours,
            temporal_raster_cache=temporal_raster_cache,
        )
        temporal_values, temporal_masks = _transform_temporal_feature_matrices(
            raw_temporal_values,
            raw_temporal_masks,
        )

    if primary_source == "cell_table":
        for i, (lat, lon) in enumerate(coords):
            _check_cancel(cancel_check)
            cell = cell_table_features[i] if cell_table_features is not None else _cell_lookup_by_bin(lat, lon, native)
            if cell is not None:
                model_input = _payload_model_input(cell)
                if temporal_values is not None and temporal_masks is not None:
                    model_input = _merge_temporal_into_model_input(
                        model_input,
                        temporal_values[i],
                        temporal_masks[i],
                    )
                features_per_coord[i] = model_input
                if feature_source_per_coord is not None:
                    feature_source_per_coord[i] = "cell_table_temporal" if temporal_values is not None else "cell_table"
                continue
            missing_indices.append(i)
            missing_coords.append((lat, lon))

        if allow_fallback and missing_coords:
            _check_cancel(cancel_check)
            missing_prefilter_keep_mask = None
            if sampled_prefilter_keep_mask is not None:
                missing_prefilter_keep_mask = [sampled_prefilter_keep_mask[i] for i in missing_indices]
            sampled = _batch_sample_features(
                missing_coords,
                raster_dataset_cache=raster_dataset_cache,
                dem_dataset_cache=dem_dataset_cache,
                temporal_mode=normalized_temporal_mode,
                temporal_forecast_hours=temporal_forecast_hours,
                temporal_raster_cache=temporal_raster_cache,
                profile=sample_profile,
                prefilter_keep_mask=missing_prefilter_keep_mask,
            )
            for i, cell in zip(missing_indices, sampled):
                if cell is not None:
                    features_per_coord[i] = _resolved_feature_model_input(cell)
                    if feature_source_per_coord is not None:
                        feature_source_per_coord[i] = "sampled"
    else:
        _check_cancel(cancel_check)
        sampled = _batch_sample_features(
            coords,
            raster_dataset_cache=raster_dataset_cache,
            dem_dataset_cache=dem_dataset_cache,
            temporal_mode=normalized_temporal_mode,
            temporal_forecast_hours=temporal_forecast_hours,
            temporal_raster_cache=temporal_raster_cache,
            profile=sample_profile,
            prefilter_keep_mask=sampled_prefilter_keep_mask,
        )
        for i, cell in enumerate(sampled):
            _check_cancel(cancel_check)
            if cell is not None:
                features_per_coord[i] = _resolved_feature_model_input(cell)
                if feature_source_per_coord is not None:
                    feature_source_per_coord[i] = "sampled"
                continue
            missing_indices.append(i)
            missing_coords.append(coords[i])

        if allow_fallback and missing_coords:
            for i, (lat, lon) in zip(missing_indices, missing_coords, strict=True):
                _check_cancel(cancel_check)
                cell = _cell_lookup_by_bin(lat, lon, native)
                if cell is not None:
                    model_input = _payload_model_input(cell)
                    if temporal_values is not None and temporal_masks is not None:
                        model_input = _merge_temporal_into_model_input(
                            model_input,
                            temporal_values[i],
                            temporal_masks[i],
                        )
                    features_per_coord[i] = model_input
                    if feature_source_per_coord is not None:
                        feature_source_per_coord[i] = (
                            "cell_table_temporal" if temporal_values is not None else "cell_table"
                        )

    valid_indices: list[int] = []
    valid_features: list[torch.Tensor] = []
    for i, feat in enumerate(features_per_coord):
        _check_cancel(cancel_check)
        if feat is None:
            continue
        valid_indices.append(i)
        valid_features.append(feat)
    stacked_features = _stack_feature_batch(valid_features, target_device=_device) if valid_features else None
    return valid_indices, stacked_features, feature_source_per_coord


def _score_species_feature_tensor(
    species_key: int,
    feature_tensor: torch.Tensor,
    *,
    score_batch_size: int,
    cancel_check: CancelCheck | None = None,
) -> list[float]:
    """Score one species head for a prebuilt feature tensor batch."""
    if _encoder is None:
        raise RuntimeError("Inference bundle not loaded. Call load_bundle() first.")
    if species_key not in _heads:
        raise KeyError(f"Species {species_key} not in loaded bundle.")

    encoder = _encoder
    head = _heads[species_key]
    scores_list: list[float] = []
    with torch.no_grad():
        for start in range(0, int(feature_tensor.shape[0]), score_batch_size):
            _check_cancel(cancel_check)
            batch_features = feature_tensor[start : start + score_batch_size]
            if batch_features.device != _device:
                batch_features = batch_features.to(_device)
            embeddings = encoder(batch_features)
            logits = head(embeddings)
            scores_list.extend(torch.sigmoid(logits).cpu().tolist())
    return scores_list


def score_species_coords(
    species_key: int,
    coords: list[tuple[float, float]],
    *,
    resolution_hint: float,
    feature_mode: str = "prefer_cell_table",
    temporal_mode: str = "missing",
    temporal_forecast_hours: int | None = None,
    score_batch_size: int = HEATMAP_DEFAULT_SCORE_BATCH_SIZE,
    include_source: bool = False,
    cancel_check: CancelCheck | None = None,
    profile: SpeciesScoreProfile | None = None,
) -> tuple[list[float | None], list[str | None] | None]:
    """Score one species for arbitrary coordinates.

    Returns one score slot per input coordinate. Coordinates that cannot be
    resolved to model-ready features are returned as ``None``.
    """
    total_start = time.perf_counter()
    sample_chunk_size = _resolve_sample_chunk_size(score_batch_size)
    scores_per_coord: list[float | None] = [None] * len(coords)
    track_sources = include_source or profile is not None
    tracked_sources: list[str | None] | None = cast(list[str | None], [None] * len(coords)) if track_sources else None
    raster_dataset_cache: dict[tuple[str, str], Any] = {}
    dem_dataset_cache: dict[tuple[str, str], Any] = {}
    temporal_raster_cache: dict[tuple[str, int, int], Any] = {}
    try:
        feature_config = _resolve_heatmap_feature_mode(
            feature_mode,
            resolution_hint,
            _cell_size_deg,
        )
        precomputed_cell_table_features, precomputed_sampled_prefilter_keep_mask = _precompute_feature_batch_inputs(
            coords,
            feature_config=feature_config,
            raster_dataset_cache=raster_dataset_cache,
            profile=profile,
        )

        for chunk_start in range(0, len(coords), sample_chunk_size):
            _check_cancel(cancel_check)
            if profile is not None:
                profile.chunk_count += 1
            chunk_coords = coords[chunk_start : chunk_start + sample_chunk_size]
            chunk_end = chunk_start + len(chunk_coords)
            prepare_start = time.perf_counter()
            sample_profile = SampleFeatureProfile() if profile is not None else None
            valid_indices, feature_tensor, chunk_sources = _prepare_feature_batch_for_coords(
                chunk_coords,
                resolution_hint=resolution_hint,
                include_source=track_sources,
                feature_mode=feature_mode,
                temporal_mode=temporal_mode,
                temporal_forecast_hours=temporal_forecast_hours,
                temporal_raster_cache=temporal_raster_cache,
                raster_dataset_cache=raster_dataset_cache,
                dem_dataset_cache=dem_dataset_cache,
                cancel_check=cancel_check,
                sample_profile=sample_profile,
                cell_table_features=(
                    precomputed_cell_table_features[chunk_start:chunk_end]
                    if precomputed_cell_table_features is not None
                    else None
                ),
                sampled_prefilter_keep_mask=(
                    precomputed_sampled_prefilter_keep_mask[chunk_start:chunk_end]
                    if precomputed_sampled_prefilter_keep_mask is not None
                    else None
                ),
            )
            if profile is not None:
                profile.feature_prepare_seconds += time.perf_counter() - prepare_start
                if sample_profile is not None:
                    profile.sample_prefilter_seconds += sample_profile.prefilter_seconds
                    profile.sample_static_sampling_seconds += sample_profile.static_sampling_seconds
                    profile.sample_dem_seconds += sample_profile.dem_seconds
                    profile.sample_temporal_seconds += sample_profile.temporal_seconds
                    profile.sample_matrix_fill_seconds += sample_profile.matrix_fill_seconds
                    profile.sample_transform_seconds += sample_profile.transform_seconds
                    profile.sample_prefilter_kept_count += sample_profile.prefilter_kept_count
                    profile.sample_prefilter_dropped_count += sample_profile.prefilter_dropped_count
                    profile.sample_active_coord_count += sample_profile.active_coord_count
                    profile.sample_static_layer_count += sample_profile.static_layer_count
                    profile.sample_dem_layer_count += sample_profile.dem_layer_count
                    profile.sample_temporal_layer_count += sample_profile.temporal_layer_count
            if chunk_sources is not None and tracked_sources is not None:
                for local_index, source in enumerate(chunk_sources):
                    tracked_sources[chunk_start + local_index] = source
            if feature_tensor is None or feature_tensor.numel() == 0:
                continue

            _check_cancel(cancel_check)
            score_start = time.perf_counter()
            chunk_scores = _score_species_feature_tensor(
                species_key,
                feature_tensor,
                score_batch_size=score_batch_size,
                cancel_check=cancel_check,
            )
            if profile is not None:
                profile.model_score_seconds += time.perf_counter() - score_start
            for local_index, score in zip(valid_indices, chunk_scores):
                scores_per_coord[chunk_start + local_index] = score
    finally:
        _close_dataset_cache(raster_dataset_cache)
        _close_dataset_cache(dem_dataset_cache)

    if profile is not None:
        profile.coord_count = len(coords)
        profile.score_batch_size = score_batch_size
        profile.sample_chunk_size = sample_chunk_size
        profile.valid_feature_count = sum(score is not None for score in scores_per_coord)
        profile.unresolved_count = len(coords) - profile.valid_feature_count
        if tracked_sources is not None:
            profile.cell_table_count = sum(source == "cell_table" for source in tracked_sources)
            profile.sampled_count = sum(source == "sampled" for source in tracked_sources)
        profile.total_seconds = time.perf_counter() - total_start

    return scores_per_coord, tracked_sources if include_source else None


def _score_combined_logits_tensor(
    feature_tensor: torch.Tensor,
    *,
    score_batch_size: int,
) -> list[torch.Tensor]:
    """Score the shared combined head and return logits for a prebuilt batch."""
    if _encoder is None or _combined_head is None:
        raise RuntimeError("Combined inference head not loaded. Call load_bundle() with a compatible bundle first.")

    encoder = _encoder
    combined_head = _combined_head
    logits_batches: list[torch.Tensor] = []
    with torch.no_grad():
        for start in range(0, int(feature_tensor.shape[0]), score_batch_size):
            batch_features = feature_tensor[start : start + score_batch_size]
            if batch_features.device != _device:
                batch_features = batch_features.to(_device)
            embeddings = encoder(batch_features)
            logits = combined_head(embeddings)
            logits_batches.append(logits.cpu())
    return logits_batches


def has_combined_head() -> bool:
    """Return whether the loaded bundle includes a shared combined species head."""
    return _combined_head is not None and bool(_combined_species_keys)


def combined_species_keys() -> list[int]:
    """Return species-key order for the shared combined species head."""
    return list(_combined_species_keys)


def combined_head_meta() -> dict[str, Any] | None:
    """Return metadata for the shared combined head, if available."""
    if _combined_head_meta is None:
        return None
    return dict(_combined_head_meta)


def combined_species_with_heads() -> list[int]:
    """Return combined-head species that also have per-species heads loaded."""
    return [_combined_species_keys[class_index] for class_index in _combined_species_head_class_indices]


def _rank_combined_coords(
    coords: list[tuple[float, float]],
    *,
    resolution_hint: float,
    top_k: int,
    min_score: float,
    feature_mode: str,
    score_batch_size: int,
    include_source: bool,
    class_indices: list[int],
    include_has_species_head: bool,
) -> tuple[list[list[dict[str, Any]] | None], list[str | None] | None]:
    """Shared ranking implementation for combined-head inference helpers."""
    if not has_combined_head():
        raise RuntimeError("Combined inference head not loaded. Call load_bundle() with a compatible bundle first.")
    if top_k <= 0:
        raise ValueError("top_k must be > 0")
    if not 0.0 <= min_score <= 1.0:
        raise ValueError("min_score must be between 0 and 1")
    if not class_indices:
        empty = cast(list[list[dict[str, Any]] | None], [[] for _ in coords])
        feature_source_per_coord = cast(list[str | None], [None] * len(coords)) if include_source else None
        return empty, feature_source_per_coord

    score_class_indices = torch.tensor(class_indices, dtype=torch.int64)
    sample_chunk_size = _resolve_sample_chunk_size(score_batch_size)
    ranks_per_coord: list[list[dict[str, Any]] | None] = [None] * len(coords)
    feature_source_per_coord: list[str | None] | None = (
        cast(list[str | None], [None] * len(coords)) if include_source else None
    )
    raster_dataset_cache: dict[tuple[str, str], Any] = {}
    dem_dataset_cache: dict[tuple[str, str], Any] = {}

    try:
        for chunk_start in range(0, len(coords), sample_chunk_size):
            chunk_coords = coords[chunk_start : chunk_start + sample_chunk_size]
            valid_indices, feature_tensor, chunk_sources = _prepare_feature_batch_for_coords(
                chunk_coords,
                resolution_hint=resolution_hint,
                include_source=include_source,
                feature_mode=feature_mode,
                raster_dataset_cache=raster_dataset_cache,
                dem_dataset_cache=dem_dataset_cache,
            )
            if chunk_sources is not None and feature_source_per_coord is not None:
                for local_index, source in enumerate(chunk_sources):
                    feature_source_per_coord[chunk_start + local_index] = source
            if feature_tensor is None or feature_tensor.numel() == 0:
                continue

            logits_batches = _score_combined_logits_tensor(
                feature_tensor,
                score_batch_size=score_batch_size,
            )

            local_valid_offset = 0
            for logits_batch in logits_batches:
                score_batch = torch.softmax(logits_batch, dim=1)
                restricted_scores = score_batch.index_select(1, score_class_indices)
                candidate_count = int(restricted_scores.shape[1])
                batch_top_k = min(top_k, candidate_count)
                top_scores, top_positions = torch.topk(restricted_scores, k=batch_top_k, dim=1)

                for row_offset in range(int(logits_batch.shape[0])):
                    ranked: list[dict[str, Any]] = []
                    for score_value, position in zip(
                        top_scores[row_offset].tolist(), top_positions[row_offset].tolist()
                    ):
                        score = float(score_value)
                        if score < min_score:
                            continue
                        class_index = class_indices[int(position)]
                        species_key = _combined_species_keys[class_index]
                        entry: dict[str, Any] = {"species_key": species_key, "score": score}
                        meta = _species_meta.get(species_key)
                        if isinstance(meta, dict) and meta.get("name") is not None:
                            entry["name"] = meta["name"]
                        if include_has_species_head:
                            entry["has_species_head"] = species_key in _heads
                        ranked.append(entry)

                    coord_index = valid_indices[local_valid_offset + row_offset]
                    ranks_per_coord[chunk_start + coord_index] = ranked
                local_valid_offset += int(logits_batch.shape[0])
    finally:
        _close_dataset_cache(raster_dataset_cache)
        _close_dataset_cache(dem_dataset_cache)

    return ranks_per_coord, feature_source_per_coord


def rank_species_weather_delta_coords(
    coords: list[tuple[float, float]],
    *,
    top_k: int = 20,
    min_delta: float = 0.0,
    forecast_hours: int | None = None,
    score_batch_size: int = HEATMAP_DEFAULT_SCORE_BATCH_SIZE,
    include_source: bool = False,
    backed_species_only: bool = True,
) -> tuple[list[list[dict[str, Any]] | None], list[str | None] | None]:
    """Rank species by uplift from current temporal weather versus masked temporal features.

    By default only species with non-negative ``delta_logit`` are returned.
    Pass a lower ``min_delta`` to include weather-suppressed species as well.
    """
    if not has_combined_head():
        raise RuntimeError("Combined inference head not loaded. Call load_bundle() with a compatible bundle first.")
    if top_k <= 0:
        raise ValueError("top_k must be > 0")
    if forecast_hours is not None and forecast_hours < 0:
        raise ValueError("forecast_hours must be >= 0")

    class_indices = (
        list(_combined_species_head_class_indices) if backed_species_only else list(range(len(_combined_species_keys)))
    )
    if not class_indices:
        empty = cast(list[list[dict[str, Any]] | None], [[] for _ in coords])
        feature_source_per_coord = cast(list[str | None], [None] * len(coords)) if include_source else None
        return empty, feature_source_per_coord

    class_index_tensor = torch.tensor(class_indices, dtype=torch.int64)
    sample_chunk_size = _resolve_sample_chunk_size(score_batch_size)
    ranks_per_coord: list[list[dict[str, Any]] | None] = [None] * len(coords)
    feature_source_per_coord: list[str | None] | None = (
        cast(list[str | None], [None] * len(coords)) if include_source else None
    )
    raster_dataset_cache: dict[tuple[str, str], Any] = {}
    dem_dataset_cache: dict[tuple[str, str], Any] = {}
    temporal_raster_cache: dict[tuple[str, int, int], Any] = {}

    try:
        for chunk_start in range(0, len(coords), sample_chunk_size):
            chunk_coords = coords[chunk_start : chunk_start + sample_chunk_size]
            valid_indices: list[int] = []
            current_inputs: list[torch.Tensor] = []
            baseline_inputs: list[torch.Tensor] = []
            fallback_indices: list[int] = []
            fallback_coords: list[tuple[float, float]] = []

            temporal_raw_values, temporal_raw_masks = _sample_temporal_feature_matrices(
                chunk_coords,
                forecast_hours=forecast_hours,
                temporal_raster_cache=temporal_raster_cache,
            )
            temporal_values, temporal_masks = _transform_temporal_feature_matrices(
                temporal_raw_values,
                temporal_raw_masks,
            )

            for local_index, (lat, lon) in enumerate(chunk_coords):
                base_cell = _cell_lookup_by_bin(lat, lon, _cell_size_deg)
                if base_cell is None:
                    fallback_indices.append(local_index)
                    fallback_coords.append((lat, lon))
                    continue
                base_input = _payload_model_input(base_cell)
                current_input = _merge_temporal_into_model_input(
                    base_input,
                    temporal_values[local_index],
                    temporal_masks[local_index],
                )
                valid_indices.append(local_index)
                current_inputs.append(current_input)
                baseline_inputs.append(_mask_temporal_model_input(base_input))
                if feature_source_per_coord is not None:
                    feature_source_per_coord[chunk_start + local_index] = "cell_table_temporal"

            if fallback_coords:
                sampled_payloads = _batch_sample_features(
                    fallback_coords,
                    raster_dataset_cache=raster_dataset_cache,
                    dem_dataset_cache=dem_dataset_cache,
                    temporal_mode="current",
                    temporal_forecast_hours=forecast_hours,
                    temporal_raster_cache=temporal_raster_cache,
                )
                for fallback_offset, payload in enumerate(sampled_payloads):
                    if payload is None:
                        continue
                    local_index = fallback_indices[fallback_offset]
                    model_input = payload["features"]
                    valid_indices.append(local_index)
                    current_inputs.append(model_input)
                    baseline_inputs.append(_mask_temporal_model_input(model_input))
                    if feature_source_per_coord is not None:
                        feature_source_per_coord[chunk_start + local_index] = "sampled_weather"

            if not current_inputs:
                continue

            current_tensor = _stack_feature_batch(current_inputs, target_device=_device)
            baseline_tensor = _stack_feature_batch(baseline_inputs, target_device=_device)
            current_logits_batches = _score_combined_logits_tensor(current_tensor, score_batch_size=score_batch_size)
            baseline_logits_batches = _score_combined_logits_tensor(baseline_tensor, score_batch_size=score_batch_size)

            local_valid_offset = 0
            for baseline_logits_batch, current_logits_batch in zip(
                baseline_logits_batches,
                current_logits_batches,
                strict=True,
            ):
                delta_logits_batch = current_logits_batch - baseline_logits_batch
                restricted_delta_logits = delta_logits_batch.index_select(1, class_index_tensor)
                batch_top_k = min(top_k, int(restricted_delta_logits.shape[1]))
                top_deltas, top_positions = torch.topk(restricted_delta_logits, k=batch_top_k, dim=1)
                baseline_probs_batch = torch.softmax(baseline_logits_batch, dim=1)
                current_probs_batch = torch.softmax(current_logits_batch, dim=1)

                for row_offset in range(int(delta_logits_batch.shape[0])):
                    ranked: list[dict[str, Any]] = []
                    for delta_value, position in zip(
                        top_deltas[row_offset].tolist(), top_positions[row_offset].tolist()
                    ):
                        delta_logit = float(delta_value)
                        if delta_logit < min_delta:
                            continue
                        class_index = class_indices[int(position)]
                        species_key = _combined_species_keys[class_index]
                        entry: dict[str, Any] = {
                            "species_key": species_key,
                            "baseline_logit": float(baseline_logits_batch[row_offset, class_index].item()),
                            "weather_logit": float(current_logits_batch[row_offset, class_index].item()),
                            "delta_logit": delta_logit,
                            "baseline_score": float(baseline_probs_batch[row_offset, class_index].item()),
                            "weather_score": float(current_probs_batch[row_offset, class_index].item()),
                            "delta_score": float(
                                current_probs_batch[row_offset, class_index].item()
                                - baseline_probs_batch[row_offset, class_index].item()
                            ),
                        }
                        meta = _species_meta.get(species_key)
                        if isinstance(meta, dict) and meta.get("name") is not None:
                            entry["name"] = meta["name"]
                        if not backed_species_only:
                            entry["has_species_head"] = species_key in _heads
                        ranked.append(entry)

                    coord_index = valid_indices[local_valid_offset + row_offset]
                    ranks_per_coord[chunk_start + coord_index] = ranked
                local_valid_offset += int(delta_logits_batch.shape[0])
    finally:
        _close_dataset_cache(raster_dataset_cache)
        _close_dataset_cache(dem_dataset_cache)

    return ranks_per_coord, feature_source_per_coord


def rank_species_coords(
    coords: list[tuple[float, float]],
    *,
    resolution_hint: float,
    top_k: int = 20,
    min_score: float = 0.0,
    feature_mode: str = "prefer_cell_table",
    score_batch_size: int = HEATMAP_DEFAULT_SCORE_BATCH_SIZE,
    include_source: bool = False,
) -> tuple[list[list[dict[str, Any]] | None], list[str | None] | None]:
    """Rank combined-head species that also have per-species heads.

    Returns one list of ranked species dicts per input coordinate. Coordinates
    that cannot be resolved to model-ready features are returned as ``None``.
    """
    return _rank_combined_coords(
        coords,
        resolution_hint=resolution_hint,
        top_k=top_k,
        min_score=min_score,
        feature_mode=feature_mode,
        score_batch_size=score_batch_size,
        include_source=include_source,
        class_indices=_combined_species_head_class_indices,
        include_has_species_head=False,
    )


def rank_all_species_coords(
    coords: list[tuple[float, float]],
    *,
    resolution_hint: float,
    top_k: int = 20,
    min_score: float = 0.0,
    feature_mode: str = "prefer_cell_table",
    score_batch_size: int = HEATMAP_DEFAULT_SCORE_BATCH_SIZE,
    include_source: bool = False,
) -> tuple[list[list[dict[str, Any]] | None], list[str | None] | None]:
    """Rank all species represented by the combined shared head."""
    return _rank_combined_coords(
        coords,
        resolution_hint=resolution_hint,
        top_k=top_k,
        min_score=min_score,
        feature_mode=feature_mode,
        score_batch_size=score_batch_size,
        include_source=include_source,
        class_indices=list(range(len(_combined_species_keys))),
        include_has_species_head=True,
    )


def _lazy_import_models() -> None:
    """Import model classes from the training package on first use."""
    global SharedEncoder, SpeciesHead, CombinedSpeciesHead  # noqa: PLW0603
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
    CombinedSpeciesHead = getattr(module, "CombinedSpeciesHead")


def _bin_index(lat: float, lon: float, size_deg: float) -> tuple[int, int]:
    """Map a coordinate to integer grid bins for a given cell size."""
    lat_bin = int(math.floor(lat / size_deg))
    lon_bin = int(math.floor(lon / size_deg))
    return lat_bin, lon_bin


def _bin_id(lat: float, lon: float, size_deg: float) -> str:
    """Map a coordinate to the canonical cell-id key for a grid size."""
    lat_bin, lon_bin = _bin_index(lat, lon, size_deg)
    return f"cell_{lat_bin}_{lon_bin}"


def _cell_lookup_by_bin(lat: float, lon: float, size_deg: float) -> torch.Tensor | None:
    """Lookup a precomputed cell tensor without constructing a string key."""
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


def _normalize_loaded_cell_payload(payload: torch.Tensor) -> torch.Tensor:
    """Normalize one loaded cell payload so its feature vector is model-ready."""
    return _payload_model_input(payload).to(dtype=torch.float32).contiguous()


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
            _write_samples_from_dataset(cached, members, results)
        else:
            _, ref_lat, ref_lon = members[0]
            cog_path = get_cog_path(layer_id, ref_lat, ref_lon)
            if cog_path is None or not cog_path.exists():
                continue
            with rasterio.open(cog_path) as ds:
                _write_samples_from_dataset(ds, members, results)
    return results


def _batch_sample_region_raster_filename(
    filename: str,
    coords: list[tuple[float, float]],
    *,
    regions_root: Path = _GIS_REGIONS_DIR,
    dataset_cache: dict[tuple[str, str], Any] | None = None,
) -> list[float | None]:
    """Sample one region-local raster filename at many points.

    Unlike catalog-backed layers, these rasters are discovered by fixed
    filename within each region directory.
    """
    import rasterio

    from util import gis_lookup

    results: list[float | None] = [None] * len(coords)
    groups: dict[str, list[tuple[int, float, float]]] = {}
    for i, (lat, lon) in enumerate(coords):
        groups.setdefault(gis_lookup.get_region_name(lat, lon), []).append((i, lat, lon))

    cache_prefix = f"region-file:{filename}"
    for region_name, members in groups.items():
        raster_path = regions_root / region_name / filename
        if dataset_cache is not None:
            cache_key = (cache_prefix, region_name)
            cached = dataset_cache.get(cache_key)
            if cached is _MISSING_DATASET:
                continue
            if cached is None:
                if not raster_path.exists():
                    dataset_cache[cache_key] = _MISSING_DATASET
                    continue
                cached = rasterio.open(raster_path)
                dataset_cache[cache_key] = cached
            _write_samples_from_dataset(cached, members, results)
            continue

        if not raster_path.exists():
            continue
        with rasterio.open(raster_path) as ds:
            _write_samples_from_dataset(ds, members, results)
    return results


def _write_samples_from_dataset(
    ds: Any,
    members: list[tuple[int, float, float]],
    results: list[float | None],
) -> None:
    import numpy as np
    from rasterio.transform import rowcol
    from rasterio.windows import Window

    nodata = ds.nodata
    indexed_indices: np.ndarray
    rows: np.ndarray
    cols: np.ndarray

    if getattr(ds, "transform", None) is not None:
        xs = np.asarray([lon for _, _lat, lon in members], dtype=np.float64)
        ys = np.asarray([lat for _, lat, _lon in members], dtype=np.float64)
        row_values, col_values = rowcol(ds.transform, xs, ys)
        indexed_indices = np.asarray([idx for idx, _lat, _lon in members], dtype=np.int64)
        rows = np.asarray(row_values, dtype=np.int64)
        cols = np.asarray(col_values, dtype=np.int64)
        in_bounds = (rows >= 0) & (cols >= 0) & (rows < ds.height) & (cols < ds.width)
        indexed_indices = indexed_indices[in_bounds]
        rows = rows[in_bounds]
        cols = cols[in_bounds]
    else:
        indexed_members: list[tuple[int, int, int]] = []
        for idx, lat, lon in members:
            row, col = ds.index(lon, lat)
            if row < 0 or col < 0 or row >= ds.height or col >= ds.width:
                continue
            indexed_members.append((idx, int(row), int(col)))
        if not indexed_members:
            return
        indexed_indices = np.asarray([idx for idx, _row, _col in indexed_members], dtype=np.int64)
        rows = np.asarray([row for _idx, row, _col in indexed_members], dtype=np.int64)
        cols = np.asarray([col for _idx, _row, col in indexed_members], dtype=np.int64)

    if indexed_indices.size == 0:
        return

    row_min = int(rows.min())
    row_max = int(rows.max())
    col_min = int(cols.min())
    col_max = int(cols.max())
    window_height = row_max - row_min + 1
    window_width = col_max - col_min + 1
    window_area = window_height * window_width

    # For compact point clouds, one bounded read is substantially cheaper
    # than many point samples. Fall back when the requested points are too sparse.
    if window_area <= max(int(indexed_indices.size) * 64, 4096):
        window = Window(col_min, row_min, window_width, window_height)
        band = ds.read(indexes=1, window=window, boundless=False)  # type: ignore[call-arg]
        if band.shape != (window_height, window_width):
            return
        values = band[rows - row_min, cols - col_min]
        valid = ~np.isnan(values)
        if nodata is not None:
            valid &= values != nodata
        for idx, value in zip(indexed_indices[valid], values[valid], strict=True):
            results[int(idx)] = float(value)
        return

    block_shapes = getattr(ds, "block_shapes", None)
    if block_shapes:
        block_height, block_width = block_shapes[0]
        if block_height > 0 and block_width > 0:
            block_groups: dict[tuple[int, int], list[int]] = {}
            for pos, (row, col) in enumerate(zip(rows.tolist(), cols.tolist(), strict=True)):
                block_key = (int(row) // int(block_height), int(col) // int(block_width))
                block_groups.setdefault(block_key, []).append(pos)

            for (block_row, block_col), positions in block_groups.items():
                row_off = block_row * int(block_height)
                col_off = block_col * int(block_width)
                height = min(int(block_height), int(ds.height) - row_off)
                width = min(int(block_width), int(ds.width) - col_off)
                if height <= 0 or width <= 0:
                    continue
                window = Window(col_off, row_off, width, height)
                band = ds.read(indexes=1, window=window, boundless=False)  # type: ignore[call-arg]
                if band.shape != (height, width):
                    continue
                pos_arr = np.asarray(positions, dtype=np.int64)
                values = band[rows[pos_arr] - row_off, cols[pos_arr] - col_off]
                valid = ~np.isnan(values)
                if nodata is not None:
                    valid &= values != nodata
                for idx, value in zip(indexed_indices[pos_arr][valid], values[valid], strict=True):
                    results[int(idx)] = float(value)
            return

    xy = [(lon, lat) for _, lat, lon in members]
    idx_list = [i for i, _, _ in members]
    for arr, idx in zip(ds.sample(xy), idx_list, strict=True):
        value = arr[0]
        if nodata is not None and value == nodata:
            continue

        if np.isnan(value):
            continue
        results[idx] = float(value)


def _sample_darwin_prefilter_keep_mask(
    coords: list[tuple[float, float]],
    dataset_cache: dict[tuple[str, str], Any] | None = None,
) -> tuple[list[bool], int]:
    """Return per-coordinate Darwin prefilter decisions.

    Prefers the derived validity mask when present and falls back to the
    landcover gate otherwise. The second return value counts how many distinct
    prefilter rasters were touched.
    """
    import numpy as np

    if not _resolve_darwin_validity_mask_enabled():
        fallback_values = _batch_sample_raster(
            "landcover",
            coords,
            dataset_cache=dataset_cache,
        )
        keep_mask = [value is not None and not np.isnan(value) for value in fallback_values]
        return keep_mask, 1 if coords else 0

    mask_values = _batch_sample_region_raster_filename(
        _DARWIN_VALIDITY_MASK_FILENAME,
        coords,
        dataset_cache=dataset_cache,
    )
    keep_mask: list[bool] = [False] * len(coords)
    missing_indices: list[int] = []
    prefilter_layer_count = 0

    for idx, value in enumerate(mask_values):
        if value is None:
            missing_indices.append(idx)
            continue
        keep_mask[idx] = value > 0.0
    if any(value is not None for value in mask_values):
        prefilter_layer_count += 1

    if missing_indices:
        fallback_values = _batch_sample_raster(
            "landcover",
            [coords[idx] for idx in missing_indices],
        )
        prefilter_layer_count += 1
        for idx, value in zip(missing_indices, fallback_values, strict=True):
            keep_mask[idx] = value is not None and not np.isnan(value)

    return keep_mask, prefilter_layer_count


def _batch_compute_dem_derived(
    coords: list[tuple[float, float]],
    dem_dataset_cache: dict[tuple[str, str], Any] | None = None,
) -> list[dict[str, float]]:
    """Batch DEM-backed terrain features, opening each region COG once."""
    import numpy as np
    import rasterio
    from rasterio.transform import rowcol
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

        if getattr(ds, "transform", None) is not None:
            xs = np.asarray([lon for _idx, _lat, lon in members], dtype=np.float64)
            ys = np.asarray([lat for _idx, lat, _lon in members], dtype=np.float64)
            row_values, col_values = rowcol(ds.transform, xs, ys)
            indexed_indices = np.asarray([idx for idx, _lat, _lon in members], dtype=np.int64)
            indexed_lats = np.asarray([lat for _idx, lat, _lon in members], dtype=np.float64)
            rows = np.asarray(row_values, dtype=np.int64)
            cols = np.asarray(col_values, dtype=np.int64)
            in_bounds = (rows > 0) & (cols > 0) & (rows + 1 < ds.height) & (cols + 1 < ds.width)
            indexed_indices = indexed_indices[in_bounds]
            indexed_lats = indexed_lats[in_bounds]
            rows = rows[in_bounds]
            cols = cols[in_bounds]
        else:
            indexed_members: list[tuple[int, float, int, int]] = []
            for idx, lat, lon in members:
                row, col = ds.index(lon, lat)
                if row <= 0 or col <= 0 or row + 1 >= ds.height or col + 1 >= ds.width:
                    continue
                indexed_members.append((idx, lat, int(row), int(col)))
            if not indexed_members:
                return
            indexed_indices = np.asarray([idx for idx, _lat, _row, _col in indexed_members], dtype=np.int64)
            indexed_lats = np.asarray([lat for _idx, lat, _row, _col in indexed_members], dtype=np.float64)
            rows = np.asarray([row for _idx, _lat, row, _col in indexed_members], dtype=np.int64)
            cols = np.asarray([col for _idx, _lat, _row, col in indexed_members], dtype=np.int64)

        if indexed_indices.size == 0:
            return

        def _write_from_band(
            band: Any,
            pos_arr: np.ndarray,
            *,
            row_off: int,
            col_off: int,
        ) -> None:
            if band.shape[0] < 3 or band.shape[1] < 3:
                return

            local_rows = rows[pos_arr] - row_off
            local_cols = cols[pos_arr] - col_off
            z1 = band[local_rows - 1, local_cols - 1]
            z2 = band[local_rows - 1, local_cols]
            z3 = band[local_rows - 1, local_cols + 1]
            z4 = band[local_rows, local_cols - 1]
            z5 = band[local_rows, local_cols]
            z6 = band[local_rows, local_cols + 1]
            z7 = band[local_rows + 1, local_cols - 1]
            z8 = band[local_rows + 1, local_cols]
            z9 = band[local_rows + 1, local_cols + 1]

            valid = ~(
                np.isnan(z1)
                | np.isnan(z2)
                | np.isnan(z3)
                | np.isnan(z4)
                | np.isnan(z5)
                | np.isnan(z6)
                | np.isnan(z7)
                | np.isnan(z8)
                | np.isnan(z9)
            )
            if nodata is not None:
                valid &= ~(
                    (z1 == nodata)
                    | (z2 == nodata)
                    | (z3 == nodata)
                    | (z4 == nodata)
                    | (z5 == nodata)
                    | (z6 == nodata)
                    | (z7 == nodata)
                    | (z8 == nodata)
                    | (z9 == nodata)
                )
            if not np.any(valid):
                return

            valid_positions = pos_arr[valid]
            valid_lats = indexed_lats[valid_positions]
            meters = np.asarray([_meters_per_degree(float(lat)) for lat in valid_lats], dtype=np.float64)
            dy = ph * meters[:, 0]
            dx = pw * meters[:, 1]
            spacing_valid = (dx != 0.0) & (dy != 0.0)
            if not np.any(spacing_valid):
                return

            valid_positions = valid_positions[spacing_valid]
            dx = dx[spacing_valid]
            dy = dy[spacing_valid]
            z1 = z1[valid][spacing_valid]
            z2 = z2[valid][spacing_valid]
            z3 = z3[valid][spacing_valid]
            z4 = z4[valid][spacing_valid]
            z5 = z5[valid][spacing_valid]
            z6 = z6[valid][spacing_valid]
            z7 = z7[valid][spacing_valid]
            z8 = z8[valid][spacing_valid]
            z9 = z9[valid][spacing_valid]

            dzdx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * dx)
            dzdy = ((z7 + 2.0 * z8 + z9) - (z1 + 2.0 * z2 + z3)) / (8.0 * dy)
            slope_deg = np.degrees(np.arctan(np.sqrt(dzdx**2 + dzdy**2)))
            asp_deg = 90.0 - np.degrees(np.arctan2(dzdy, -dzdx))
            flat = (dzdx == 0.0) & (dzdy == 0.0)
            asp_deg = np.where(flat, 0.0, asp_deg)
            asp_deg = np.where(asp_deg < 0.0, asp_deg + 360.0, asp_deg)
            aspect_bins = (((asp_deg + 22.5) % 360.0) // 45.0 + 1.0).astype(np.float64)

            for pos, elevation_value, slope_value, aspect_bin, aspect_value in zip(
                valid_positions,
                z5,
                slope_deg,
                aspect_bins,
                asp_deg,
                strict=True,
            ):
                idx = int(indexed_indices[pos])
                results[idx] = {
                    "elevation": float(elevation_value),
                    "slope": float(slope_value),
                    "aspect": float(aspect_bin),
                    "aspect_deg": float(aspect_value),
                }

        row_min = int(rows.min())
        row_max = int(rows.max())
        col_min = int(cols.min())
        col_max = int(cols.max())
        window_height = row_max - row_min + 3
        window_width = col_max - col_min + 3
        window_area = window_height * window_width

        if window_area <= max(int(indexed_indices.size) * 81, 4096):
            row_off = row_min - 1
            col_off = col_min - 1
            window = Window(col_off, row_off, window_width, window_height)
            band = ds.read(indexes=1, window=window, boundless=False)  # type: ignore[call-arg]
            if band.shape == (window_height, window_width):
                _write_from_band(
                    band, np.arange(indexed_indices.size, dtype=np.int64), row_off=row_off, col_off=col_off
                )
                return

        block_shapes = getattr(ds, "block_shapes", None)
        if block_shapes:
            block_height, block_width = block_shapes[0]
            if block_height > 0 and block_width > 0:
                block_groups: dict[tuple[int, int], list[int]] = {}
                for pos, (row, col) in enumerate(zip(rows.tolist(), cols.tolist(), strict=True)):
                    block_key = (int(row) // int(block_height), int(col) // int(block_width))
                    block_groups.setdefault(block_key, []).append(pos)

                for (block_row, block_col), positions in block_groups.items():
                    row_off = max(block_row * int(block_height) - 1, 0)
                    col_off = max(block_col * int(block_width) - 1, 0)
                    row_end = min((block_row + 1) * int(block_height) + 1, int(ds.height))
                    col_end = min((block_col + 1) * int(block_width) + 1, int(ds.width))
                    height = row_end - row_off
                    width = col_end - col_off
                    if height < 3 or width < 3:
                        continue
                    window = Window(col_off, row_off, width, height)
                    band = ds.read(indexes=1, window=window, boundless=False)  # type: ignore[call-arg]
                    if band.shape != (height, width):
                        continue
                    _write_from_band(band, np.asarray(positions, dtype=np.int64), row_off=row_off, col_off=col_off)
                return

        for pos, (idx, lat, row, col) in enumerate(zip(indexed_indices, indexed_lats, rows, cols, strict=True)):
            win = ds.read(indexes=1, window=Window(int(col) - 1, int(row) - 1, 3, 3), boundless=False)  # type: ignore[call-arg]
            if win.shape != (3, 3):
                continue
            _write_from_band(win, np.asarray([pos], dtype=np.int64), row_off=int(row) - 1, col_off=int(col) - 1)

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


def _resolve_temporal_forecast_hours(window_hours: int, forecast_hours: int | None) -> int:
    """Resolve which temporal raster snapshot to use for one feature window."""
    if forecast_hours is not None:
        return int(forecast_hours)
    return int(_TEMPORAL_WINDOW_TO_FORECAST_HOURS.get(int(window_hours), 0))


def _temporal_raster_path(variable_id: str, window_hours: int, forecast_hours: int) -> Path | None:
    """Resolve the on-disk temporal raster path for one temporal layer."""
    window_label = _TEMPORAL_WINDOW_LABELS.get(int(window_hours))
    if window_label is None:
        return None
    if int(forecast_hours) == 0:
        return _TEMPORAL_RASTER_DIR / f"{variable_id}_{window_label}.npy"
    return _TEMPORAL_RASTER_DIR / f"{variable_id}_{window_label}__f{int(forecast_hours):03d}h.npy"


def _load_temporal_raster_array(
    variable_id: str,
    window_hours: int,
    forecast_hours: int,
    temporal_raster_cache: dict[tuple[str, int, int], Any] | None = None,
) -> Any | None:
    """Load one temporal raster array, optionally caching by variable/window/forecast."""
    cache_key = (variable_id, int(window_hours), int(forecast_hours))
    if temporal_raster_cache is not None and cache_key in temporal_raster_cache:
        cached = temporal_raster_cache[cache_key]
        return None if cached is _MISSING_DATASET else cached

    raster_path = _temporal_raster_path(variable_id, window_hours, forecast_hours)
    if raster_path is None or not raster_path.exists():
        if temporal_raster_cache is not None:
            temporal_raster_cache[cache_key] = _MISSING_DATASET
        return None

    import numpy as np

    arr = np.load(raster_path).astype(np.float32, copy=False)
    if temporal_raster_cache is not None:
        temporal_raster_cache[cache_key] = arr
    return arr


def _sample_temporal_layer_points(
    layer_id: str,
    coords: list[tuple[float, float]],
    *,
    forecast_hours: int | None = None,
    temporal_raster_cache: dict[tuple[str, int, int], Any] | None = None,
) -> list[float | None]:
    """Sample one temporal raster layer at point coordinates using nearest cells."""
    import numpy as np
    from util import gis_lookup

    parsed = gis_lookup.parse_temporal_layer_id(layer_id)
    if parsed is None:
        return [None] * len(coords)
    variable_id, _agg, window_hours = parsed
    resolved_forecast_hours = _resolve_temporal_forecast_hours(window_hours, forecast_hours)
    arr = _load_temporal_raster_array(
        variable_id,
        window_hours,
        resolved_forecast_hours,
        temporal_raster_cache=temporal_raster_cache,
    )
    if arr is None:
        return [None] * len(coords)

    ny, nx = arr.shape
    results: list[float | None] = [None] * len(coords)
    for idx, (lat, lon) in enumerate(coords):
        if lat < -90.0 or lat > 90.0:
            continue
        wrapped_lon = ((lon + 180.0) % 360.0) - 180.0
        row = int(math.floor(((90.0 - lat) / 180.0) * ny))
        col = int(math.floor(((wrapped_lon + 180.0) / 360.0) * nx))
        row = min(max(row, 0), ny - 1)
        col = min(max(col, 0), nx - 1)
        value = float(arr[row, col])
        if np.isnan(value):
            continue
        results[idx] = value
    return results


def _mask_temporal_model_input(model_input: torch.Tensor) -> torch.Tensor:
    """Return a copy of one model input with temporal features masked out."""
    if model_input.ndim != 1:
        raise ValueError("model_input must be a 1-d tensor")
    temporal_start, temporal_end = _temporal_feature_span()
    if temporal_start >= temporal_end:
        return model_input.clone()

    masked = model_input.clone()
    model_dim = _model_feature_dim_from_names()
    if model_dim is None or model_dim <= 0:
        return masked

    masked[temporal_start:temporal_end] = 0.0
    if _model_uses_mask:
        mask_offset = model_dim
        masked[mask_offset + temporal_start : mask_offset + temporal_end] = 1.0
    return masked


def _sample_temporal_feature_matrices(
    coords: list[tuple[float, float]],
    *,
    forecast_hours: int | None = None,
    temporal_raster_cache: dict[tuple[str, int, int], Any] | None = None,
) -> tuple[Any, Any]:
    """Sample raw temporal features and return aligned raw value and mask matrices."""
    import numpy as np

    temporal_names = _raw_temporal_feature_names()
    n_coords = len(coords)
    if not temporal_names:
        empty = np.zeros((n_coords, 0), dtype=np.float32)
        return empty, empty

    values_out = np.zeros((n_coords, len(temporal_names)), dtype=np.float32)
    masks_out = np.ones((n_coords, len(temporal_names)), dtype=np.float32)
    for offset, layer_name in enumerate(temporal_names):
        values = _sample_temporal_layer_points(
            layer_name,
            coords,
            forecast_hours=forecast_hours,
            temporal_raster_cache=temporal_raster_cache,
        )
        for idx, value in enumerate(values):
            if value is None:
                continue
            values_out[idx, offset] = float(value)
            masks_out[idx, offset] = 0.0
    return values_out, masks_out


def _transform_temporal_feature_matrices(raw_values: Any, raw_masks: Any) -> tuple[Any, Any]:
    """Transform only temporal raw features into model-space temporal slices."""
    temporal_template = {group: [] for group in FEATURE_GROUPS}
    temporal_template["temporal"] = _raw_temporal_feature_names()
    temporal_spec = _filtered_transform_spec_for_groups({"temporal"})
    values_out, masks_out, _ = transform_feature_matrices(
        raw_feature_template=temporal_template,
        raw_values=raw_values,
        raw_masks=raw_masks,
        transform_spec=temporal_spec,
    )
    return values_out, masks_out


def _merge_temporal_into_model_input(
    base_model_input: torch.Tensor,
    temporal_values: Any,
    temporal_masks: Any,
) -> torch.Tensor:
    """Reuse static features from a base model input and overwrite only temporal slices."""
    temporal_start, temporal_end = _temporal_feature_span()
    merged = _mask_temporal_model_input(base_model_input)
    if temporal_start >= temporal_end:
        return merged

    temporal_tensor = torch.as_tensor(temporal_values, dtype=torch.float32, device=merged.device)
    temporal_mask_tensor = torch.as_tensor(temporal_masks, dtype=torch.float32, device=merged.device)
    merged[temporal_start:temporal_end] = temporal_tensor
    if _model_uses_mask:
        model_dim = _model_feature_dim_from_names()
        if model_dim is None:
            raise ValueError("model feature names unavailable for temporal mask update")
        mask_offset = model_dim
        merged[mask_offset + temporal_start : mask_offset + temporal_end] = temporal_mask_tensor
    return merged


def _batch_sample_features(
    coords: list[tuple[float, float]],
    *,
    raster_dataset_cache: dict[tuple[str, str], Any] | None = None,
    dem_dataset_cache: dict[tuple[str, str], Any] | None = None,
    temporal_mode: str = "missing",
    temporal_forecast_hours: int | None = None,
    temporal_raster_cache: dict[tuple[str, int, int], Any] | None = None,
    profile: SampleFeatureProfile | None = None,
    prefilter_keep_mask: list[bool] | None = None,
) -> list[dict[str, torch.Tensor] | None]:
    """Batch-sample static features for many coordinates.

    Opens each GIS raster once per 10-degree region rather than once per
    coordinate, so this is efficient enough for heatmap-sized batches.
    """
    if _raw_feature_names is None:
        return [None] * len(coords)
    try:
        import numpy as np
        import rasterio  # noqa: F401
    except ImportError:
        return [None] * len(coords)

    temporal_names = _raw_temporal_feature_names()
    selected_group_names: set[str] = set(_SAMPLED_FEATURE_GROUPS)
    n_coords = len(coords)
    if profile is not None:
        profile.input_coord_count = n_coords

    layer_vals: dict[str, np.ndarray] = {}
    sampled_static_names = _sampled_static_feature_names()
    dem_backed_names = ({"elevation"} | set(_DEM_DERIVED)) & set(sampled_static_names)
    layer_names = [name for name in sampled_static_names if name not in dem_backed_names]
    sampling_workers = _resolve_sampling_workers()
    normalized_temporal_mode = temporal_mode.strip().lower()
    if normalized_temporal_mode not in {"missing", "current"}:
        raise ValueError("temporal_mode must be one of ['current', 'missing']")
    if normalized_temporal_mode == "current" and temporal_names:
        selected_group_names.add("temporal")

    raw_feature_template = _raw_feature_template_for_groups(selected_group_names)
    static_width = sum(len(raw_feature_template[group_name]) for group_name in _SAMPLED_FEATURE_GROUPS)
    raw_width = sum(len(raw_feature_template[group_name]) for group_name in FEATURE_GROUPS)

    feature_matrix = np.zeros((n_coords, raw_width), dtype=np.float32)
    mask_matrix = np.ones((n_coords, raw_width), dtype=np.float32)
    static_feature_index = {name: idx for idx, name in enumerate(sampled_static_names)}
    temporal_start = static_width

    def _sample_layers(target_coords: list[tuple[float, float]], names: list[str]) -> dict[str, np.ndarray]:
        """Sample raster layers for a coordinate subset."""
        sampled: dict[str, np.ndarray] = {}
        if not names:
            return sampled

        def _values_to_array(values: list[float | None]) -> np.ndarray:
            arr = np.full(len(values), np.nan, dtype=np.float32)
            for idx, value in enumerate(values):
                if value is not None:
                    arr[idx] = float(value)
            return arr

        def _sample_layer(layer_name: str) -> tuple[str, np.ndarray]:
            values = _batch_sample_raster(layer_name, target_coords, dataset_cache=raster_dataset_cache)
            return layer_name, _values_to_array(values)

        if sampling_workers == 1 or len(names) <= 1:
            for layer_name in names:
                sampled_name, sampled_values = _sample_layer(layer_name)
                sampled[sampled_name] = sampled_values
            return sampled

        from concurrent.futures import ThreadPoolExecutor

        max_workers = min(sampling_workers, len(names))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for sampled_name, sampled_values in pool.map(_sample_layer, names):
                sampled[sampled_name] = sampled_values
        return sampled

    active_indices = list(range(n_coords))
    active_coords = coords
    prefilter_layer_count = 0
    prefilter_start: float | None = None
    if layer_names:
        if prefilter_keep_mask is not None:
            if len(prefilter_keep_mask) != n_coords:
                raise ValueError("prefilter_keep_mask must align 1:1 with coords")
            keep_mask = prefilter_keep_mask
        else:
            prefilter_start = time.perf_counter()
            keep_mask, prefilter_layer_count = _sample_darwin_prefilter_keep_mask(
                coords,
                dataset_cache=raster_dataset_cache,
            )
        active_indices = [i for i, keep in enumerate(keep_mask) if keep]
        if profile is not None and prefilter_start is not None:
            profile.prefilter_seconds += time.perf_counter() - prefilter_start
            profile.prefilter_kept_count = len(active_indices)
            profile.prefilter_dropped_count = n_coords - len(active_indices)
        if not active_indices:
            return [None] * n_coords
        active_coords = [coords[i] for i in active_indices]
    elif profile is not None:
        profile.prefilter_kept_count = n_coords
        profile.prefilter_dropped_count = 0

    remaining_layers = [name for name in layer_names if name not in layer_vals]
    if active_indices and remaining_layers:
        static_start = time.perf_counter()
        sampled_remaining = _sample_layers(active_coords, remaining_layers)
        for name, vals in sampled_remaining.items():
            full_vals = np.full(n_coords, np.nan, dtype=np.float32)
            full_vals[np.asarray(active_indices, dtype=np.int64)] = vals
            layer_vals[name] = full_vals
        if profile is not None:
            profile.static_sampling_seconds += time.perf_counter() - static_start

    needs_dem_derived = _DEM_DERIVED & set(sampled_static_names)
    dem_layer_vals: dict[str, np.ndarray] = {
        name: np.full(n_coords, np.nan, dtype=np.float32) for name in dem_backed_names
    }
    if dem_backed_names and active_indices:
        dem_start = time.perf_counter()
        dem_active = _batch_compute_dem_derived(active_coords, dem_dataset_cache=dem_dataset_cache)
        for pos, global_idx in enumerate(active_indices):
            for name, value in dem_active[pos].items():
                if name in dem_layer_vals:
                    dem_layer_vals[name][global_idx] = float(value)
        if profile is not None:
            profile.dem_seconds += time.perf_counter() - dem_start

    temporal_vals: dict[str, np.ndarray] = {}
    if normalized_temporal_mode == "current" and temporal_names:
        temporal_start_time = time.perf_counter()
        for layer_name in temporal_names:
            values = _sample_temporal_layer_points(
                layer_name,
                coords,
                forecast_hours=temporal_forecast_hours,
                temporal_raster_cache=temporal_raster_cache,
            )
            arr = np.full(n_coords, np.nan, dtype=np.float32)
            for idx, value in enumerate(values):
                if value is not None:
                    arr[idx] = float(value)
            temporal_vals[layer_name] = arr
        if profile is not None:
            profile.temporal_seconds += time.perf_counter() - temporal_start_time

    matrix_fill_start = time.perf_counter()
    for name, values in layer_vals.items():
        col_idx = static_feature_index[name]
        observed = ~np.isnan(values)
        if not np.any(observed):
            continue
        feature_matrix[observed, col_idx] = values[observed]
        mask_matrix[observed, col_idx] = 0.0

    for name, values in dem_layer_vals.items():
        col_idx = static_feature_index[name]
        observed = ~np.isnan(values)
        if not np.any(observed):
            continue
        feature_matrix[observed, col_idx] = values[observed]
        mask_matrix[observed, col_idx] = 0.0

    if normalized_temporal_mode == "current":
        for offset, layer_name in enumerate(temporal_names):
            values = temporal_vals[layer_name]
            col_idx = temporal_start + offset
            observed = ~np.isnan(values)
            if not np.any(observed):
                continue
            feature_matrix[observed, col_idx] = values[observed]
            mask_matrix[observed, col_idx] = 0.0

    if profile is not None:
        profile.matrix_fill_seconds += time.perf_counter() - matrix_fill_start

    transform_start = time.perf_counter()
    transformed_values, transformed_masks = _transform_selected_raw_feature_matrices(
        group_names=selected_group_names,
        raw_feature_template=raw_feature_template,
        raw_values=feature_matrix,
        raw_masks=mask_matrix,
    )

    feature_tensor = torch.from_numpy(transformed_values)
    mask_tensor = torch.from_numpy(transformed_masks)
    feature_tensor[mask_tensor > 0.5] = 0.0
    model_input_tensor = _coerce_model_input_batch(feature_tensor, mask_tensor)

    static_observed = (
        (mask_matrix[:, :static_width] < 0.5).any(axis=1) if static_width > 0 else np.ones(n_coords, dtype=bool)
    )
    out: list[dict[str, torch.Tensor] | None] = []
    for i in range(n_coords):
        if not bool(static_observed[i]):
            out.append(None)
            continue
        out.append({"features": model_input_tensor[i], "mask": mask_tensor[i]})
    if profile is not None:
        profile.transform_seconds += time.perf_counter() - transform_start
        profile.active_coord_count = len(active_indices)
        profile.static_layer_count = (
            len(layer_names) + (1 if "elevation" in dem_backed_names else 0) + prefilter_layer_count
        )
        profile.dem_layer_count = len(needs_dem_derived)
        profile.temporal_layer_count = len(temporal_names) if normalized_temporal_mode == "current" else 0
    return out


def load_bundle(bundle_path: str | Path) -> None:
    """Load an exported inference bundle into module-level runtime state."""
    global _bundle, _encoder, _heads, _combined_head, _cell_table, _cell_table_by_bin  # noqa: PLW0603
    global _cell_size_deg, _species_meta, _combined_species_keys, _combined_head_meta  # noqa: PLW0603
    global _combined_species_head_class_indices, _raw_feature_names, _feature_names  # noqa: PLW0603
    global _feature_transforms_spec, _input_dim, _model_uses_mask  # noqa: PLW0603
    global _device, _bundle_source_path, _bundle_source_mtime_ns  # noqa: PLW0603

    _lazy_import_models()

    bundle_path = Path(bundle_path).expanduser().resolve()
    _bundle_source_path = str(bundle_path)
    _bundle_source_mtime_ns = bundle_path.stat().st_mtime_ns if bundle_path.exists() else None
    _device = _resolve_inference_device()
    cell_table_device = _resolve_cell_table_device(_device)
    # Keep bundle tensors on CPU at load time. The bundle includes a large
    # cell_table; mapping the full payload directly to CUDA can exhaust GPU
    # memory. We move only encoder/heads and runtime batches to _device.
    loaded = torch.load(str(bundle_path), map_location="cpu", weights_only=False)
    if not isinstance(loaded, dict):
        raise ValueError("Invalid inference bundle: expected dict payload.")
    if loaded.get("bundle_version") != 2:
        raise ValueError("Invalid inference bundle: expected bundle_version=2.")
    _bundle = loaded

    model_payload = loaded.get("model")
    heads_payload = loaded.get("heads")
    serving_payload = loaded.get("serving")
    if (
        not isinstance(model_payload, dict)
        or not isinstance(heads_payload, dict)
        or not isinstance(serving_payload, dict)
    ):
        raise ValueError("Invalid inference bundle: expected dict sections.")

    input_dim: int = model_payload["input_dim"]
    embed_dim: int = model_payload["embed_dim"]
    hidden_dim: int = model_payload["hidden_dim"]
    _input_dim = input_dim

    if SharedEncoder is None or SpeciesHead is None or CombinedSpeciesHead is None:
        raise RuntimeError("Training model classes are unavailable.")

    encoder = SharedEncoder(input_dim, embed_dim=embed_dim, hidden_dim=hidden_dim).to(_device)
    encoder.load_state_dict(model_payload["encoder_state_dict"])
    encoder.eval()
    for p in encoder.parameters():
        p.requires_grad = False
    _encoder = encoder

    _heads = {}
    for sp_key, state in heads_payload["head_states"].items():
        head = SpeciesHead(embed_dim=embed_dim).to(_device)
        head.load_state_dict(state)
        head.eval()
        for p in head.parameters():
            p.requires_grad = False
        _heads[int(sp_key)] = head

    loaded_combined_species_keys = [int(species_key) for species_key in heads_payload.get("combined_species_keys", [])]
    loaded_combined_state = heads_payload.get("combined_head_state")
    _combined_head = None
    if loaded_combined_state is not None and loaded_combined_species_keys:
        combined_head = CombinedSpeciesHead(
            embed_dim=embed_dim,
            species_count=len(loaded_combined_species_keys),
        ).to(_device)
        combined_head.load_state_dict(loaded_combined_state)
        combined_head.eval()
        for p in combined_head.parameters():
            p.requires_grad = False
        _combined_head = combined_head

    raw_cell_table = serving_payload.get("cell_table", {})
    if not isinstance(raw_cell_table, dict):
        raise ValueError("Invalid inference bundle: serving.cell_table must be a dict payload.")
    loaded_cell_table = cast(dict[str, torch.Tensor], raw_cell_table)
    loaded_cell_table = _move_cell_table_to_device(loaded_cell_table, cell_table_device)
    _cell_size_deg = serving_payload.get("cell_size_deg", 0.25)
    _species_meta = heads_payload.get("species_meta", {})
    _combined_species_keys = loaded_combined_species_keys
    _combined_head_meta = heads_payload.get("combined_head_meta")
    _combined_species_head_class_indices = [
        class_index for class_index, species_key in enumerate(_combined_species_keys) if int(species_key) in _heads
    ]
    _feature_transforms_spec = normalize_feature_transform_spec(model_payload.get("feature_transforms"))
    _raw_feature_names = model_payload.get("raw_feature_names")
    _feature_names = model_payload.get("feature_names")
    if _feature_names is None and _feature_transforms_spec is not None:
        _feature_names = _feature_transforms_spec.get("transformed_feature_template")
    if _feature_names is None:
        _feature_names = _raw_feature_names

    model_dim = _model_feature_dim_from_names()
    _model_uses_mask = model_dim is not None and input_dim == model_dim * 2
    normalized_table: dict[str, torch.Tensor] = {}
    normalized_by_bin: dict[tuple[int, int], torch.Tensor] = {}
    bad_cells: list[str] = []
    for cid, payload in loaded_cell_table.items():
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


def has_species(species_key: int) -> bool:
    """Return whether the loaded bundle contains the requested species head."""
    return species_key in _heads


def cell_count() -> int:
    """Return the number of cells in the loaded lookup table."""
    return len(_cell_table)


def native_resolution() -> float:
    """Return the loaded model's native cell size in degrees."""
    return _cell_size_deg


def bundle_cache_token() -> str:
    """Return a cache token that changes when the loaded inference bundle changes."""
    path_token = _bundle_source_path or "<unloaded>"
    mtime_token = "unknown" if _bundle_source_mtime_ns is None else str(_bundle_source_mtime_ns)
    return f"{path_token}:{mtime_token}"
