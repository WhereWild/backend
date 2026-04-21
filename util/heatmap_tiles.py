from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import logging
import math
from pathlib import Path
import time

import numpy as np
from PIL import Image

from util.config import load_config
from util import inference
from util.request_cancellation import CancelCheck
from util.tile_disk_cache import DiskTileCache, make_cache_key


CONFIG = load_config("global")
_HEATMAP_CACHE_NAMESPACE = hashlib.md5(str(CONFIG.data_root).encode()).hexdigest()[:12]
_HEATMAP_TILE_DISK_CACHE = DiskTileCache(
    cache_dir=Path("/workspace/cache/darwin-heatmap-tiles"),
    max_bytes=256 * 1024 * 1024,
)
LOGGER = logging.getLogger("uvicorn.error")

WEB_MERCATOR = 6378137.0 * math.pi

HEATMAP_COLOR_STOPS = np.asarray(
    [
        [28, 38, 102],
        [34, 94, 168],
        [59, 170, 165],
        [246, 190, 0],
        [230, 57, 70],
    ],
    dtype=np.float32,
)


@dataclass(frozen=True)
class TileSpec:
    z: int
    x: int
    y: int
    tile_size: int


@dataclass
class DarwinHeatmapTileProfile:
    species_key: int
    request_z: int
    request_x: int
    request_y: int
    render_z: int
    render_x: int
    render_y: int
    tile_size: int
    render_tile_size: int
    feature_mode: str
    bypass_cache: bool
    cache_hit: bool = False
    coord_count: int = 0
    valid_feature_count: int = 0
    unresolved_count: int = 0
    cell_table_count: int = 0
    sampled_count: int = 0
    sample_chunk_size: int = 0
    score_batch_size: int = 0
    chunk_count: int = 0
    rss_start_mb: float | None = None
    rss_after_score_mb: float | None = None
    rss_after_render_mb: float | None = None
    cache_lookup_seconds: float = 0.0
    coord_generation_seconds: float = 0.0
    resolution_hint_seconds: float = 0.0
    feature_prepare_seconds: float = 0.0
    model_score_seconds: float = 0.0
    sample_prefilter_seconds: float = 0.0
    sample_static_sampling_seconds: float = 0.0
    sample_dem_seconds: float = 0.0
    sample_temporal_seconds: float = 0.0
    sample_matrix_fill_seconds: float = 0.0
    sample_transform_seconds: float = 0.0
    scoring_seconds: float = 0.0
    colorize_seconds: float = 0.0
    png_encode_seconds: float = 0.0
    cache_write_seconds: float = 0.0
    total_seconds: float = 0.0
    max_native_zoom: int | None = None
    zoom_diff: int | None = None
    crop_seconds: float = 0.0
    sample_prefilter_kept_count: int = 0
    sample_prefilter_dropped_count: int = 0
    sample_active_coord_count: int = 0
    sample_static_layer_count: int = 0
    sample_dem_layer_count: int = 0
    sample_temporal_layer_count: int = 0


def _read_rss_mb() -> float | None:
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    rss_kb = float(line.split()[1])
                    return rss_kb / 1024.0
    except OSError:
        return None
    return None


def log_heatmap_tile_profile(profile: DarwinHeatmapTileProfile) -> None:
    LOGGER.info(
        "[darwin-tile-profile] taxon_id=%s request_z=%s request_x=%s request_y=%s render_z=%s render_x=%s render_y=%s tile_size=%s render_tile_size=%s feature_mode=%s bypass_cache=%s cache_hit=%s coords=%s valid=%s unresolved=%s cell_table=%s sampled=%s sample_chunk_size=%s score_batch_size=%s chunks=%s sample_prefilter_kept=%s sample_prefilter_dropped=%s sample_active_coords=%s sample_static_layers=%s sample_dem_layers=%s sample_temporal_layers=%s rss_start_mb=%s rss_after_score_mb=%s rss_after_render_mb=%s cache_lookup_ms=%.2f coord_gen_ms=%.2f resolution_hint_ms=%.2f feature_prepare_ms=%.2f sample_prefilter_ms=%.2f sample_static_ms=%.2f sample_dem_ms=%.2f sample_temporal_ms=%.2f sample_matrix_fill_ms=%.2f sample_transform_ms=%.2f model_score_ms=%.2f scoring_total_ms=%.2f colorize_ms=%.2f png_encode_ms=%.2f cache_write_ms=%.2f crop_ms=%.2f total_ms=%.2f max_native_zoom=%s zoom_diff=%s",
        profile.species_key,
        profile.request_z,
        profile.request_x,
        profile.request_y,
        profile.render_z,
        profile.render_x,
        profile.render_y,
        profile.tile_size,
        profile.render_tile_size,
        profile.feature_mode,
        profile.bypass_cache,
        profile.cache_hit,
        profile.coord_count,
        profile.valid_feature_count,
        profile.unresolved_count,
        profile.cell_table_count,
        profile.sampled_count,
        profile.sample_chunk_size,
        profile.score_batch_size,
        profile.chunk_count,
        profile.sample_prefilter_kept_count,
        profile.sample_prefilter_dropped_count,
        profile.sample_active_coord_count,
        profile.sample_static_layer_count,
        profile.sample_dem_layer_count,
        profile.sample_temporal_layer_count,
        f"{profile.rss_start_mb:.1f}" if profile.rss_start_mb is not None else "na",
        f"{profile.rss_after_score_mb:.1f}" if profile.rss_after_score_mb is not None else "na",
        f"{profile.rss_after_render_mb:.1f}" if profile.rss_after_render_mb is not None else "na",
        profile.cache_lookup_seconds * 1000.0,
        profile.coord_generation_seconds * 1000.0,
        profile.resolution_hint_seconds * 1000.0,
        profile.feature_prepare_seconds * 1000.0,
        profile.sample_prefilter_seconds * 1000.0,
        profile.sample_static_sampling_seconds * 1000.0,
        profile.sample_dem_seconds * 1000.0,
        profile.sample_temporal_seconds * 1000.0,
        profile.sample_matrix_fill_seconds * 1000.0,
        profile.sample_transform_seconds * 1000.0,
        profile.model_score_seconds * 1000.0,
        profile.scoring_seconds * 1000.0,
        profile.colorize_seconds * 1000.0,
        profile.png_encode_seconds * 1000.0,
        profile.cache_write_seconds * 1000.0,
        profile.crop_seconds * 1000.0,
        profile.total_seconds * 1000.0,
        profile.max_native_zoom,
        profile.zoom_diff,
    )


def tile_bounds_mercator(spec: TileSpec) -> tuple[float, float, float, float]:
    resolution = (2 * WEB_MERCATOR) / (spec.tile_size * (2**spec.z))
    min_x = spec.x * spec.tile_size * resolution - WEB_MERCATOR
    max_x = (spec.x + 1) * spec.tile_size * resolution - WEB_MERCATOR
    max_y = WEB_MERCATOR - spec.y * spec.tile_size * resolution
    min_y = WEB_MERCATOR - (spec.y + 1) * spec.tile_size * resolution
    return min_x, min_y, max_x, max_y


def _mercator_to_lonlat(x: float, y: float) -> tuple[float, float]:
    lon = (x / WEB_MERCATOR) * 180.0
    lat = (y / WEB_MERCATOR) * 180.0
    lat = 180.0 / math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return lon, lat


def _tile_pixel_center_coords(spec: TileSpec) -> list[tuple[float, float]]:
    min_x, min_y, max_x, max_y = tile_bounds_mercator(spec)
    step_x = (max_x - min_x) / spec.tile_size
    step_y = (max_y - min_y) / spec.tile_size

    coords: list[tuple[float, float]] = []
    for row in range(spec.tile_size):
        y = max_y - ((row + 0.5) * step_y)
        for col in range(spec.tile_size):
            x = min_x + ((col + 0.5) * step_x)
            lon, lat = _mercator_to_lonlat(x, y)
            coords.append((lat, lon))
    return coords


def _tile_resolution_hint(spec: TileSpec) -> float:
    coords = _tile_pixel_center_coords(spec)
    lat0, lon0 = coords[0]
    lat_row, lon_row = coords[spec.tile_size]
    lat_col, lon_col = coords[1]
    return max(
        abs(lat_row - lat0),
        abs(lon_row - lon0),
        abs(lat_col - lat0),
        abs(lon_col - lon0),
        1e-9,
    )


def _colorize_heatmap(values: np.ndarray) -> np.ndarray:
    rgba = np.zeros((*values.shape, 4), dtype=np.uint8)
    finite = np.isfinite(values)
    if not np.any(finite):
        return rgba

    norm = np.clip(values, 0.0, 1.0)
    finite_norm = norm[finite]
    positions = np.linspace(0.0, 1.0, HEATMAP_COLOR_STOPS.shape[0], dtype=np.float32)
    rgba[finite, 0] = np.interp(finite_norm, positions, HEATMAP_COLOR_STOPS[:, 0]).astype(np.uint8)
    rgba[finite, 1] = np.interp(finite_norm, positions, HEATMAP_COLOR_STOPS[:, 1]).astype(np.uint8)
    rgba[finite, 2] = np.interp(finite_norm, positions, HEATMAP_COLOR_STOPS[:, 2]).astype(np.uint8)
    rgba[finite, 3] = np.clip(finite_norm * 128.0, 0.0, 128.0).astype(np.uint8)
    return rgba


def render_heatmap_tile_bytes(
    species_key: int,
    z: int,
    x: int,
    y: int,
    *,
    tile_size: int = 256,
    feature_mode: str = "prefer_cell_table",
    forecast_hours: int = 0,
    score_batch_size: int = inference.HEATMAP_DEFAULT_SCORE_BATCH_SIZE,
    cancel_check: CancelCheck | None = None,
    bypass_cache: bool = False,
    profile: DarwinHeatmapTileProfile | None = None,
) -> bytes:
    total_start = time.perf_counter()
    if cancel_check is not None:
        cancel_check()
    if profile is not None:
        profile.rss_start_mb = _read_rss_mb()

    spec = TileSpec(z=z, x=x, y=y, tile_size=tile_size)
    cache_key = make_cache_key(
        namespace=_HEATMAP_CACHE_NAMESPACE,
        species_key=species_key,
        z=z,
        x=x,
        y=y,
        tile_size=tile_size,
        feature_mode=feature_mode,
        forecast_hours=forecast_hours,
        score_batch_size=score_batch_size,
        bundle_token=inference.bundle_cache_token(),
    )
    cache_lookup_start = time.perf_counter()
    cached = None if bypass_cache else _HEATMAP_TILE_DISK_CACHE.read(cache_key)
    if profile is not None:
        profile.cache_lookup_seconds = time.perf_counter() - cache_lookup_start
        profile.cache_hit = cached is not None
    if cached is not None:
        if cancel_check is not None:
            cancel_check()
        if profile is not None:
            profile.total_seconds = time.perf_counter() - total_start
            profile.rss_after_render_mb = _read_rss_mb()
        return cached

    coord_start = time.perf_counter()
    coords = _tile_pixel_center_coords(spec)
    if profile is not None:
        profile.coord_generation_seconds = time.perf_counter() - coord_start
        profile.coord_count = len(coords)
    if cancel_check is not None:
        cancel_check()
    resolution_start = time.perf_counter()
    resolution_hint = _tile_resolution_hint(spec)
    if profile is not None:
        profile.resolution_hint_seconds = time.perf_counter() - resolution_start
    score_profile = inference.SpeciesScoreProfile() if profile is not None else None
    scoring_start = time.perf_counter()
    scores_list, _ = inference.score_species_coords(
        species_key,
        coords,
        resolution_hint=resolution_hint,
        feature_mode=feature_mode,
        temporal_mode="current",
        temporal_forecast_hours=forecast_hours,
        score_batch_size=score_batch_size,
        include_source=False,
        cancel_check=cancel_check,
        profile=score_profile,
    )
    if profile is not None:
        profile.scoring_seconds = time.perf_counter() - scoring_start
        profile.rss_after_score_mb = _read_rss_mb()
        if score_profile is not None:
            profile.valid_feature_count = score_profile.valid_feature_count
            profile.unresolved_count = score_profile.unresolved_count
            profile.cell_table_count = score_profile.cell_table_count
            profile.sampled_count = score_profile.sampled_count
            profile.sample_chunk_size = score_profile.sample_chunk_size
            profile.score_batch_size = score_profile.score_batch_size
            profile.chunk_count = score_profile.chunk_count
            profile.feature_prepare_seconds = score_profile.feature_prepare_seconds
            profile.model_score_seconds = score_profile.model_score_seconds
            profile.sample_prefilter_seconds = score_profile.sample_prefilter_seconds
            profile.sample_static_sampling_seconds = score_profile.sample_static_sampling_seconds
            profile.sample_dem_seconds = score_profile.sample_dem_seconds
            profile.sample_temporal_seconds = score_profile.sample_temporal_seconds
            profile.sample_matrix_fill_seconds = score_profile.sample_matrix_fill_seconds
            profile.sample_transform_seconds = score_profile.sample_transform_seconds
            profile.sample_prefilter_kept_count = score_profile.sample_prefilter_kept_count
            profile.sample_prefilter_dropped_count = score_profile.sample_prefilter_dropped_count
            profile.sample_active_coord_count = score_profile.sample_active_coord_count
            profile.sample_static_layer_count = score_profile.sample_static_layer_count
            profile.sample_dem_layer_count = score_profile.sample_dem_layer_count
            profile.sample_temporal_layer_count = score_profile.sample_temporal_layer_count
    scores = np.asarray(
        [np.nan if score is None else score for score in scores_list],
        dtype=np.float32,
    )

    colorize_start = time.perf_counter()
    rgba = _colorize_heatmap(scores.reshape((tile_size, tile_size)))
    if profile is not None:
        profile.colorize_seconds = time.perf_counter() - colorize_start
    if cancel_check is not None:
        cancel_check()
    png_start = time.perf_counter()
    image = Image.fromarray(rgba, mode="RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()
    if profile is not None:
        profile.png_encode_seconds = time.perf_counter() - png_start
    if cancel_check is not None:
        cancel_check()
    if not bypass_cache:
        write_start = time.perf_counter()
        _HEATMAP_TILE_DISK_CACHE.write(cache_key, payload)
        if profile is not None:
            profile.cache_write_seconds = time.perf_counter() - write_start
    if profile is not None:
        profile.total_seconds = time.perf_counter() - total_start
        profile.rss_after_render_mb = _read_rss_mb()
    return payload
