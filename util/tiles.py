from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from collections import OrderedDict
from contextlib import nullcontext
import logging
import math
import os
import threading
import time
from typing import Iterable, Sequence

import numpy as np
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import reproject
from rasterio.windows import Window, from_bounds as window_from_bounds, transform as window_transform
import rasterio

from util.config import load_config
from util import gis_lookup, models


CONFIG = load_config("global")

# --- Debug logging setup ---
_TILE_DEBUG_LOG_PATH = os.environ.get("TILE_DEBUG_LOG", "/workspace/logs/tile_debug.log")
os.makedirs(os.path.dirname(_TILE_DEBUG_LOG_PATH), exist_ok=True)
_tile_logger = logging.getLogger("tile_debug")
_tile_logger.setLevel(logging.DEBUG)
_tile_logger.propagate = False
if not _tile_logger.handlers:
    _fh = logging.FileHandler(_TILE_DEBUG_LOG_PATH, mode="a")
    _fh.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    _tile_logger.addHandler(_fh)
    # Also print to stdout
    _sh = logging.StreamHandler()
    _sh.setFormatter(logging.Formatter("%(message)s"))
    _tile_logger.addHandler(_sh)


def _debug(msg: str) -> None:
    """Log debug message to file and stdout."""
    _tile_logger.debug(msg)


# Set to a layer name to only log that layer's details (reduces noise)
# Set to None or "" to log all layers
_DEBUG_LAYER_FILTER = os.environ.get("TILE_DEBUG_LAYER", "elevation")

# Set to "verbose" for full detail, "summary" for just per-tile summaries, "off" to disable
_DEBUG_VERBOSITY = os.environ.get("TILE_DEBUG_VERBOSITY", "summary")


def clear_tile_debug_log() -> None:
    """Clear the tile debug log file. Call at the start of a session."""
    with open(_TILE_DEBUG_LOG_PATH, "w") as f:
        f.write(f"=== Tile Debug Log Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        f.write(f"Log path: {_TILE_DEBUG_LOG_PATH}\n")
        f.write(f"Layer filter: {_DEBUG_LAYER_FILTER or 'ALL LAYERS'}\n")
        f.write(f"Verbosity: {_DEBUG_VERBOSITY}\n")
        f.write("=" * 80 + "\n\n")


def _is_verbose() -> bool:
    return _DEBUG_VERBOSITY == "verbose"


# Log startup info
if _DEBUG_VERBOSITY != "off":
    _debug(f"Tile debug logging initialized. Log file: {_TILE_DEBUG_LOG_PATH}")
    _debug(f"Layer filter: {_DEBUG_LAYER_FILTER or 'ALL LAYERS'}, Verbosity: {_DEBUG_VERBOSITY}")

WEB_MERCATOR = "EPSG:3857"
DEFAULT_TILE_SIZE = CONFIG.sdm_tile_size
DEFAULT_MAX_OPEN_DATASETS = 16

FORCED_CATEGORICAL_LAYERS = frozenset({"landcover"})

# Derived layers that are computed from other layers rather than read directly
DERIVED_LAYERS = frozenset({"slope", "aspect"})


def _compute_slope(elevation: np.ndarray, meters_per_px: float, pad: int = 0) -> np.ndarray:
    """Compute slope in degrees from elevation data.

    Args:
        elevation: 2D array of elevation values in meters (may include padding)
        meters_per_px: Approximate meters per pixel at the tile center
        pad: If > 0, elevation includes this many pixels of padding that will be trimmed

    Returns:
        2D array of slope in degrees (0-90), trimmed to remove padding
    """
    if elevation.size == 0:
        return elevation.copy()

    # np.gradient computes rise per pixel
    dy, dx = np.gradient(elevation)

    # Convert from rise/pixel to rise/meter
    dy = dy / meters_per_px
    dx = dx / meters_per_px

    # Compute slope magnitude (rise/run) and convert to degrees
    slope_radians = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_degrees = np.degrees(slope_radians)

    # Trim padding if provided
    if pad > 0:
        slope_degrees = slope_degrees[pad:-pad, pad:-pad]
        elevation_trimmed = elevation[pad:-pad, pad:-pad]
    else:
        elevation_trimmed = elevation

    # Preserve NaN from elevation
    slope_degrees = np.where(np.isfinite(elevation_trimmed), slope_degrees, np.nan)

    return slope_degrees.astype(np.float32)


def _compute_aspect(elevation: np.ndarray, pad: int = 0) -> np.ndarray:
    """Compute aspect (slope direction) in degrees from elevation data.

    Args:
        elevation: 2D array of elevation values in meters (may include padding)
        pad: If > 0, elevation includes this many pixels of padding that will be trimmed

    Returns:
        2D array of aspect in degrees (0-360), where:
        - 0/360 = North (uphill is to the north)
        - 90 = East
        - 180 = South
        - 270 = West
    """
    if elevation.size == 0:
        return elevation.copy()

    # np.gradient: dy is change along rows (south to north), dx is change along columns (west to east)
    dy, dx = np.gradient(elevation)

    # Aspect is the direction the slope faces (downhill direction)
    # arctan2(-dy, -dx) gives the downhill direction
    # We negate both because gradient points uphill
    aspect_radians = np.arctan2(-dy, -dx)
    aspect_degrees = np.degrees(aspect_radians)

    # Convert from (-180, 180) to (0, 360) with 0 = North
    # arctan2 gives 0 = East, so rotate by 90 degrees
    aspect_degrees = (90.0 - aspect_degrees) % 360.0

    # Trim padding if provided
    if pad > 0:
        aspect_degrees = aspect_degrees[pad:-pad, pad:-pad]
        elevation_trimmed = elevation[pad:-pad, pad:-pad]
    else:
        elevation_trimmed = elevation

    # Preserve NaN from elevation
    aspect_degrees = np.where(np.isfinite(elevation_trimmed), aspect_degrees, np.nan)

    return aspect_degrees.astype(np.float32)


@dataclass(frozen=True)
class TileSpec:
    z: int
    x: int
    y: int
    tile_size: int = DEFAULT_TILE_SIZE


class DatasetCache:
    """Thread-safe cache for rasterio datasets.

    NOTE: Rasterio DatasetReader objects are NOT thread-safe for concurrent reads.
    This cache now opens a NEW dataset for each call to avoid corruption.
    Caching is disabled for thread safety - each thread gets its own handle.
    """
    def __init__(self, max_open: int = DEFAULT_MAX_OPEN_DATASETS) -> None:
        self._max_open = max_open
        self._lock = threading.Lock()
        # For now, disable caching to ensure thread safety
        # Each call opens a fresh dataset
        self._cache: OrderedDict[str, rasterio.DatasetReader] = OrderedDict()

    def open(self, path: str) -> rasterio.DatasetReader:
        # THREAD SAFETY: Always open a new dataset to avoid concurrent read issues
        # The caller is responsible for closing it (or use context manager)
        return rasterio.open(path)

    def close_all(self) -> None:
        with self._lock:
            for ds in self._cache.values():
                ds.close()
            self._cache.clear()


_DATASET_CACHE = DatasetCache()


def tile_bounds_mercator(spec: TileSpec) -> tuple[float, float, float, float]:
    origin_shift = 2 * math.pi * 6378137 / 2.0
    res = (2 * origin_shift) / (spec.tile_size * (2**spec.z))
    minx = spec.x * spec.tile_size * res - origin_shift
    maxx = (spec.x + 1) * spec.tile_size * res - origin_shift
    maxy = origin_shift - spec.y * spec.tile_size * res
    miny = origin_shift - (spec.y + 1) * spec.tile_size * res
    return minx, miny, maxx, maxy


def _mercator_to_lonlat(x: float, y: float) -> tuple[float, float]:
    origin_shift = 2 * math.pi * 6378137 / 2.0
    lon = (x / origin_shift) * 180.0
    lat = (y / origin_shift) * 180.0
    lat = 180.0 / math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return lon, lat


def tile_bounds_wgs84(spec: TileSpec) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = tile_bounds_mercator(spec)
    lon_w, lat_s = _mercator_to_lonlat(minx, miny)
    lon_e, lat_n = _mercator_to_lonlat(maxx, maxy)
    min_lon = min(lon_w, lon_e)
    max_lon = max(lon_w, lon_e)
    min_lat = min(lat_s, lat_n)
    max_lat = max(lat_s, lat_n)
    return min_lon, min_lat, max_lon, max_lat


def tile_transform(spec: TileSpec) -> rasterio.Affine:
    minx, miny, maxx, maxy = tile_bounds_mercator(spec)
    return from_bounds(minx, miny, maxx, maxy, spec.tile_size, spec.tile_size)


def meters_per_pixel(spec: TileSpec) -> float:
    minx, _miny, maxx, _maxy = tile_bounds_mercator(spec)
    return abs(maxx - minx) / spec.tile_size


def _extend_bounds_mercator(
    bounds: tuple[float, float, float, float],
    pad_pixels: int,
    mpp: float,
) -> tuple[float, float, float, float]:
    """Extend mercator bounds by pad_pixels in each direction."""
    minx, miny, maxx, maxy = bounds
    pad_meters = pad_pixels * mpp
    return (minx - pad_meters, miny - pad_meters, maxx + pad_meters, maxy + pad_meters)


def _extend_bounds_wgs84(
    bounds: tuple[float, float, float, float],
    pad_pixels: int,
    degrees_per_pixel: float,
) -> tuple[float, float, float, float]:
    """Extend WGS84 bounds by pad_pixels in each direction."""
    min_lon, min_lat, max_lon, max_lat = bounds
    pad_deg = pad_pixels * degrees_per_pixel
    return (min_lon - pad_deg, min_lat - pad_deg, max_lon + pad_deg, max_lat + pad_deg)


def _iter_region_origins(
    bounds_wgs84: tuple[float, float, float, float],
    region_size: float,
) -> Iterable[tuple[int, int]]:
    min_lon, min_lat, max_lon, max_lat = bounds_wgs84
    start_lat = math.floor(min_lat / region_size) * region_size
    end_lat = math.floor(max_lat / region_size) * region_size
    start_lon = math.floor(min_lon / region_size) * region_size
    end_lon = math.floor(max_lon / region_size) * region_size
    lat = start_lat
    while lat <= end_lat:
        lon = start_lon
        while lon <= end_lon:
            yield int(lat), int(lon)
            lon += region_size
        lat += region_size


def _region_id_from_origin(lat0: int, lon0: int) -> str:
    return f"lat{lat0}_lon{lon0}"


def _is_layer_categorical(layer_id: str, layer_meta: dict[str, object] | None) -> bool:
    if layer_id in FORCED_CATEGORICAL_LAYERS:
        return True
    value_type = str(layer_meta.get("value_type") or "").lower() if layer_meta else ""
    return value_type == "categorical"


def _load_layer_list(layers: Sequence[str] | None) -> list[str]:
    if layers:
        return [layer.strip() for layer in layers if layer.strip()]
    meta = gis_lookup.load_layer_metadata()
    entries, mapping = gis_lookup.load_variable_metadata()
    temporal_categories = {"temporal", "recent weather"}
    layer_ids: list[str] = []
    for layer_id, entry in meta.items():
        if entry.get("derived"):
            continue
        category = str(mapping.get(layer_id, {}).get("category") or "").strip().lower()
        if category in temporal_categories:
            continue
        layer_ids.append(layer_id)
    return layer_ids


def _estimate_overview_factor(
    ds: rasterio.DatasetReader,
    bounds_wgs84: tuple[float, float, float, float],
    tile_size: int,
) -> tuple[list[int], float, float, float, float]:
    overviews = ds.overviews(1) or []
    src_res_x = abs(ds.transform.a)
    src_res_y = abs(ds.transform.e)
    min_lon, min_lat, max_lon, max_lat = bounds_wgs84
    dst_res_x = abs(max_lon - min_lon) / tile_size
    dst_res_y = abs(max_lat - min_lat) / tile_size
    desired = max(dst_res_x / src_res_x, dst_res_y / src_res_y) if src_res_x and src_res_y else 1.0
    return overviews, src_res_x, src_res_y, desired, max(dst_res_x, dst_res_y)


def _choose_overview_level(overviews: list[int], desired: float) -> tuple[int | None, int | None]:
    """Choose a GDAL overview level index using a performance-first (ceil) strategy."""
    if not overviews:
        return None, None
    # Prefer the first overview that is at least as coarse as desired.
    for idx, factor in enumerate(overviews):
        if factor >= desired:
            return idx, factor
    # If desired is coarser than every available overview, use the coarsest one.
    return len(overviews) - 1, overviews[-1]


def _intersect_bounds(
    left: float,
    bottom: float,
    right: float,
    top: float,
    *,
    ds: rasterio.DatasetReader,
) -> tuple[float, float, float, float] | None:
    ds_left, ds_bottom, ds_right, ds_top = ds.bounds
    x0 = max(left, ds_left)
    y0 = max(bottom, ds_bottom)
    x1 = min(right, ds_right)
    y1 = min(top, ds_top)
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _clamp_window(window: Window, width: int, height: int) -> Window:
    col_off = max(0, int(math.floor(window.col_off)))
    row_off = max(0, int(math.floor(window.row_off)))
    col_end = min(width, int(math.ceil(window.col_off + window.width)))
    row_end = min(height, int(math.ceil(window.row_off + window.height)))
    return Window(
        col_off=col_off,
        row_off=row_off,
        width=max(0, col_end - col_off),
        height=max(0, row_end - row_off),
    )


def _window_shape(window: Window) -> tuple[int, int]:
    return int(window.height), int(window.width)


def _render_layer(
    layer_id: str,
    spec: TileSpec,
    layer_meta: dict[str, object] | None,
    *,
    reproject_to_mercator: bool,
    pad_pixels: int = 0,
) -> np.ndarray:
    """Render a single layer for a tile.

    Args:
        layer_id: The layer to render
        spec: Tile specification
        layer_meta: Layer metadata dict
        reproject_to_mercator: Whether to reproject to web mercator
        pad_pixels: Extra pixels to render around the tile (for derivative calculations)

    Returns:
        2D array of shape (tile_size + 2*pad_pixels, tile_size + 2*pad_pixels)
    """
    layer_start = time.perf_counter()
    bounds_wgs84 = tile_bounds_wgs84(spec)
    bounds_mercator = tile_bounds_mercator(spec)

    # Calculate output size (with padding if requested)
    output_size = spec.tile_size + 2 * pad_pixels

    # Extend bounds if padding requested
    if pad_pixels > 0:
        mpp = meters_per_pixel(spec)
        bounds_mercator = _extend_bounds_mercator(bounds_mercator, pad_pixels, mpp)
        # For WGS84, approximate degrees per pixel
        min_lon, min_lat, max_lon, max_lat = bounds_wgs84
        deg_per_px = (max_lon - min_lon) / spec.tile_size
        bounds_wgs84 = _extend_bounds_wgs84(bounds_wgs84, pad_pixels, deg_per_px)

    region_size = float(layer_meta.get("region_size") or 10.0) if layer_meta else 10.0
    if reproject_to_mercator:
        minx, miny, maxx, maxy = bounds_mercator
        transform = from_bounds(minx, miny, maxx, maxy, output_size, output_size)
        dst_crs = WEB_MERCATOR
    else:
        min_lon, min_lat, max_lon, max_lat = bounds_wgs84
        transform = from_bounds(min_lon, min_lat, max_lon, max_lat, output_size, output_size)
        dst_crs = "EPSG:4326"

    # Only log detailed info for filtered layer (or all if filter is None/empty)
    should_log = (not _DEBUG_LAYER_FILTER or layer_id == _DEBUG_LAYER_FILTER) and _DEBUG_VERBOSITY != "off"
    verbose = should_log and _is_verbose()

    if verbose:
        _debug(f"[tile_debug] layer={layer_id} z={spec.z} x={spec.x} y={spec.y} tile_size={spec.tile_size}")
        _debug(f"[tile_debug] bounds_wgs84=({bounds_wgs84[0]:.6f}, {bounds_wgs84[1]:.6f}, {bounds_wgs84[2]:.6f}, {bounds_wgs84[3]:.6f})")
        _debug(f"[tile_debug] bounds_mercator=({bounds_mercator[0]:.2f}, {bounds_mercator[1]:.2f}, {bounds_mercator[2]:.2f}, {bounds_mercator[3]:.2f})")
        _debug(f"[tile_debug] dst_transform={transform} dst_crs={dst_crs} reproject_to_mercator={reproject_to_mercator}")

    # Track overview factors used across regions for summary
    overview_factors_used: set[int] = set()
    resampling = Resampling.nearest if _is_layer_categorical(layer_id, layer_meta) else Resampling.bilinear
    dest = np.full((output_size, output_size), np.nan, dtype=np.float32)
    logged_overview = False
    total_regions = 0
    regions_with_data = 0
    regions_rendered = 0
    region_render_seconds = 0.0
    read_seconds = 0.0
    warp_seconds = 0.0
    src_pixels_read = 0
    dst_pixels_requested = 0
    pixels_written = 0
    for lat0, lon0 in _iter_region_origins(bounds_wgs84, region_size):
        total_regions += 1
        region_id = _region_id_from_origin(lat0, lon0)
        cog_path = gis_lookup.get_cog_path_for_region(layer_id, region_id)
        if cog_path is None or not cog_path.exists():
            continue
        regions_with_data += 1
        # Note: Opening fresh each time for thread safety (no caching)
        ds = rasterio.open(cog_path.as_posix())
        overviews, src_res_x, src_res_y, desired, dst_res = _estimate_overview_factor(
            ds, bounds_wgs84, output_size
        )
        chosen_level, chosen_factor = _choose_overview_level(overviews, desired)
        if not logged_overview:
            if overviews:
                print(
                    f"[sdm_tile] layer={layer_id} src_res=({src_res_x:.6f},{src_res_y:.6f})deg "
                    f"dst_res≈{dst_res:.6f}deg overviews={overviews} desired≈{desired:.2f} "
                    f"chosen≈{chosen_factor} requested_level={chosen_level} strategy=ceil",
                    flush=True,
                )
            else:
                print(
                    f"[sdm_tile] layer={layer_id} src_res=({src_res_x:.6f},{src_res_y:.6f})deg "
                    f"dst_res≈{dst_res:.6f}deg overviews=none",
                    flush=True,
                )
            if not reproject_to_mercator and ds.crs and str(ds.crs) not in ("EPSG:4326", "OGC:CRS84"):
                print(
                    f"[sdm_tile] layer={layer_id} warning: dataset CRS {ds.crs} not WGS84 "
                    "while reproject disabled",
                    flush=True,
                )
            logged_overview = True
        region_start = time.perf_counter()
        min_lon, min_lat, max_lon, max_lat = bounds_wgs84
        overlap = _intersect_bounds(min_lon, min_lat, max_lon, max_lat, ds=ds)
        if overlap is None:
            continue
        src_window = _clamp_window(
            window_from_bounds(*overlap, transform=ds.transform),
            ds.width,
            ds.height,
        )
        src_h, src_w = _window_shape(src_window)
        if src_h <= 0 or src_w <= 0:
            continue
        overview_factor = max(1, int(chosen_factor or 1))
        overview_factors_used.add(overview_factor)
        if (
            not reproject_to_mercator
            and ds.crs
            and str(ds.crs) in ("EPSG:4326", "OGC:CRS84")
        ):
            # Fast path: avoid warp when output remains WGS84.
            raw_dst_window = window_from_bounds(*overlap, transform=transform)
            dst_window = _clamp_window(raw_dst_window, output_size, output_size)
            dst_h, dst_w = _window_shape(dst_window)

            # Debug: log window geometry
            if verbose:
                _debug(f"[tile_debug] FAST_PATH region={region_id} overlap=({overlap[0]:.6f}, {overlap[1]:.6f}, {overlap[2]:.6f}, {overlap[3]:.6f})")
                _debug(f"[tile_debug] FAST_PATH src_window: col_off={src_window.col_off:.2f} row_off={src_window.row_off:.2f} width={src_window.width:.2f} height={src_window.height:.2f} -> src_w={src_w} src_h={src_h}")
                _debug(f"[tile_debug] FAST_PATH raw_dst_window: col_off={raw_dst_window.col_off:.2f} row_off={raw_dst_window.row_off:.2f} width={raw_dst_window.width:.2f} height={raw_dst_window.height:.2f}")
                _debug(f"[tile_debug] FAST_PATH clamped_dst_window: col_off={dst_window.col_off} row_off={dst_window.row_off} width={dst_window.width} height={dst_window.height} -> dst_w={dst_w} dst_h={dst_h}")

            if dst_h <= 0 or dst_w <= 0:
                if verbose:
                    _debug(f"[tile_debug] FAST_PATH SKIPPING region={region_id} - zero dst dimensions")
                continue
            read_h = max(1, int(math.ceil(src_h / overview_factor)))
            read_w = max(1, int(math.ceil(src_w / overview_factor)))
            dst_pixels_requested += dst_h * dst_w
            env_ctx = rasterio.Env(OVR_LEVEL=str(chosen_level)) if chosen_level is not None else nullcontext()
            read_start = time.perf_counter()

            # BUG: Reading twice - coarse_tile is never used except for counting!
            # The second read ignores overview_factor and reads at dst_h x dst_w directly
            if verbose:
                _debug(f"[tile_debug] FAST_PATH reading: overview_factor={overview_factor} read_h={read_h} read_w={read_w} BUT ALSO reading at dst_h={dst_h} dst_w={dst_w}")

            with env_ctx:
                coarse_tile = ds.read(
                    1,
                    window=src_window,
                    out_shape=(read_h, read_w),
                    resampling=resampling,
                ).astype(np.float32, copy=False)
                tile = ds.read(
                    1,
                    window=src_window,
                    out_shape=(dst_h, dst_w),
                    resampling=resampling,
                ).astype(np.float32, copy=False)
            read_seconds += time.perf_counter() - read_start
            src_pixels_read += coarse_tile.shape[0] * coarse_tile.shape[1]

            # Log actual data stats
            if verbose:
                _debug(f"[tile_debug] FAST_PATH tile_stats: shape={tile.shape} min={np.nanmin(tile):.2f} max={np.nanmax(tile):.2f} nan_count={np.isnan(tile).sum()} nodata={ds.nodata}")

            if ds.nodata is not None:
                tile[tile == ds.nodata] = np.nan
            row0 = int(dst_window.row_off)
            col0 = int(dst_window.col_off)
            row1 = row0 + dst_h
            col1 = col0 + dst_w

            if verbose:
                _debug(f"[tile_debug] FAST_PATH placement: row0={row0} row1={row1} col0={col0} col1={col1} dest_section_shape=({row1-row0}, {col1-col0}) tile_shape={tile.shape}")

            # Check for shape mismatch - always log this as it's an error
            if (row1 - row0) != tile.shape[0] or (col1 - col0) != tile.shape[1]:
                _debug(f"[tile_debug] FAST_PATH WARNING: SHAPE MISMATCH! layer={layer_id} dest_section=({row1-row0}, {col1-col0}) vs tile={tile.shape}")

            section = dest[row0:row1, col0:col1]
            mask = np.isfinite(tile)
            section[mask] = tile[mask]
            pixels_written += int(mask.sum())
            regions_rendered += 1
        else:
            # Warp path: reproject to mercator or handle non-WGS84 source
            if verbose:
                _debug(f"[tile_debug] WARP_PATH region={region_id} overlap=({overlap[0]:.6f}, {overlap[1]:.6f}, {overlap[2]:.6f}, {overlap[3]:.6f})")
                _debug(f"[tile_debug] WARP_PATH src_window: col_off={src_window.col_off:.2f} row_off={src_window.row_off:.2f} width={src_window.width:.2f} height={src_window.height:.2f}")
                _debug(f"[tile_debug] WARP_PATH ds.crs={ds.crs} ds.transform={ds.transform}")

            read_h = max(1, int(math.ceil(src_h / overview_factor)))
            read_w = max(1, int(math.ceil(src_w / overview_factor)))
            if verbose:
                _debug(f"[tile_debug] WARP_PATH reading: overview_factor={overview_factor} src_h={src_h} src_w={src_w} -> read_h={read_h} read_w={read_w}")

            env_ctx = rasterio.Env(OVR_LEVEL=str(chosen_level)) if chosen_level is not None else nullcontext()
            read_start = time.perf_counter()
            with env_ctx:
                source_tile = ds.read(
                    1,
                    window=src_window,
                    out_shape=(read_h, read_w),
                    resampling=resampling,
                ).astype(np.float32, copy=False)
            read_seconds += time.perf_counter() - read_start
            src_pixels_read += source_tile.shape[0] * source_tile.shape[1]

            if verbose:
                _debug(f"[tile_debug] WARP_PATH source_tile_stats: shape={source_tile.shape} min={np.nanmin(source_tile):.2f} max={np.nanmax(source_tile):.2f} nan_count={np.isnan(source_tile).sum()}")

            if ds.nodata is not None:
                source_tile[source_tile == ds.nodata] = np.nan
            src_transform = window_transform(src_window, ds.transform) * rasterio.Affine.scale(
                src_w / read_w,
                src_h / read_h,
            )
            if verbose:
                _debug(f"[tile_debug] WARP_PATH src_transform={src_transform} dst_transform={transform}")

            temp = np.full_like(dest, np.nan)
            warp_start = time.perf_counter()
            reproject(
                source=source_tile,
                destination=temp,
                src_transform=src_transform,
                src_crs=ds.crs,
                src_nodata=np.nan,
                dst_transform=transform,
                dst_crs=dst_crs,
                dst_nodata=np.nan,
                resampling=resampling,
            )
            warp_seconds += time.perf_counter() - warp_start

            if verbose:
                _debug(f"[tile_debug] WARP_PATH warped_stats: min={np.nanmin(temp):.2f} max={np.nanmax(temp):.2f} nan_count={np.isnan(temp).sum()} finite_count={np.isfinite(temp).sum()}")

            dst_pixels_requested += output_size * output_size
            mask = np.isfinite(temp)
            dest[mask] = temp[mask]
            pixels_written += int(mask.sum())
            regions_rendered += 1
        region_render_seconds += time.perf_counter() - region_start
    total_seconds = time.perf_counter() - layer_start

    # Final dest stats - always log summary line for filtered layer
    if should_log:
        finite_mask = np.isfinite(dest)
        overview_factors_str = ",".join(str(f) for f in sorted(overview_factors_used))
        finite_count = int(finite_mask.sum())

        # Compact summary line - easy to grep
        _debug(
            f"[LAYER_SUMMARY] layer={layer_id} z={spec.z} x={spec.x} y={spec.y} "
            f"regions={regions_rendered}/{total_regions} overview_factors=[{overview_factors_str}] "
            f"finite_px={finite_count}/{output_size**2} "
            f"mode={'warp' if reproject_to_mercator else 'direct'}"
        )

        # Flag potential issues
        if len(overview_factors_used) > 1:
            _debug(f"[WARNING] MIXED_OVERVIEW_FACTORS layer={layer_id} z={spec.z} x={spec.x} y={spec.y} factors={overview_factors_str}")

        if finite_count == 0:
            _debug(f"[WARNING] NO_DATA layer={layer_id} z={spec.z} x={spec.x} y={spec.y} - tile has no finite values")

        if verbose:
            if finite_mask.any():
                _debug(f"[tile_debug] FINAL dest_values: min={np.nanmin(dest):.4f} max={np.nanmax(dest):.4f} mean={np.nanmean(dest):.4f}")
            _debug(
                f"[sdm_tile] layer={layer_id} timings total={total_seconds:.2f}s render={region_render_seconds:.2f}s "
                f"read={read_seconds:.2f}s warp={warp_seconds:.2f}s "
                f"src_px_read={src_pixels_read:,} dst_px={dst_pixels_requested:,} written_px={pixels_written:,}"
            )
    return dest


def _render_derived_layer(
    layer_id: str,
    spec: TileSpec,
    *,
    reproject_to_mercator: bool,
) -> np.ndarray:
    """Render a derived layer (computed from other layers).

    Args:
        layer_id: The derived layer ID (e.g., "slope")
        spec: Tile specification
        reproject_to_mercator: Whether to reproject to web mercator

    Returns:
        2D array of computed values (spec.tile_size x spec.tile_size)
    """
    if layer_id in ("slope", "aspect"):
        # Both slope and aspect are derived from elevation
        # Fetch elevation with padding so gradient at edges uses real neighbor data
        pad = 2  # pixels of extra data on each side
        layer_lookup = gis_lookup.load_layer_metadata()
        elevation_padded = _render_layer(
            "elevation",
            spec,
            layer_lookup.get("elevation"),
            reproject_to_mercator=reproject_to_mercator,
            pad_pixels=pad,
        )
        if layer_id == "slope":
            mpp = meters_per_pixel(spec)
            return _compute_slope(elevation_padded, mpp, pad=pad)
        else:  # aspect
            return _compute_aspect(elevation_padded, pad=pad)
    else:
        raise ValueError(f"Unknown derived layer: {layer_id}")


def _colorize(
    values: np.ndarray,
    *,
    alpha_min: float = 0.7,
    alpha_max: float = 0.95,
    colormap: str = "terrain",
) -> np.ndarray:
    """Colorize normalized [0,1] values to RGBA.

    Args:
        values: Array of values in [0, 1] range
        alpha_min: Minimum alpha (for lowest values)
        alpha_max: Maximum alpha (for highest values)
        colormap: "terrain" for elevation, "slope" for slope, "heat" for predictions
    """
    v = np.clip(values, 0.0, 1.0)

    if colormap == "terrain":
        # Terrain colormap: green lowlands → yellow/tan hills → brown mountains → white peaks
        stops = np.array(
            [
                [34, 139, 34],    # Forest green (low elevation)
                [144, 238, 144],  # Light green
                [238, 214, 175],  # Tan/wheat
                [139, 90, 43],    # Brown (mountains)
                [255, 255, 255],  # White (peaks/snow)
            ],
            dtype=np.float32,
        )
    elif colormap == "slope":
        # Slope colormap: flat (green) → gentle (yellow) → moderate (orange) → steep (red)
        stops = np.array(
            [
                [144, 238, 144],  # Light green (flat, 0°)
                [255, 255, 150],  # Light yellow (gentle slopes)
                [255, 200, 100],  # Orange-yellow (moderate)
                [255, 100, 50],   # Orange-red (steep)
                [180, 0, 0],      # Dark red (very steep, ~45°+)
            ],
            dtype=np.float32,
        )
    elif colormap == "aspect":
        # Aspect colormap: circular hue for compass directions
        # 0=N (blue), 0.25=E (green), 0.5=S (yellow), 0.75=W (red), 1.0=N (blue)
        stops = np.array(
            [
                [65, 105, 225],   # Royal blue (North, 0°)
                [50, 205, 50],    # Lime green (East, 90°)
                [255, 215, 0],    # Gold (South, 180°)
                [220, 20, 60],    # Crimson (West, 270°)
                [65, 105, 225],   # Royal blue (North, 360° wraps to 0°)
            ],
            dtype=np.float32,
        )
    else:
        # Original heat colormap for predictions
        stops = np.array(
            [
                [28, 38, 102],    # Dark blue
                [34, 94, 168],    # Blue
                [59, 170, 165],   # Cyan
                [246, 190, 0],    # Yellow
                [230, 57, 70],    # Red
            ],
            dtype=np.float32,
        )

    # Track NaN pixels before clipping (they should be transparent)
    nan_mask = ~np.isfinite(values)

    idx = (v * (len(stops) - 1)).astype(np.int32)
    frac = (v * (len(stops) - 1)) - idx
    idx = np.clip(idx, 0, len(stops) - 2)
    frac = frac[..., None]
    rgb = stops[idx] * (1.0 - frac) + stops[idx + 1] * frac

    rgba = np.zeros((*v.shape, 4), dtype=np.uint8)
    rgba[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba[..., 3] = 255  # Fully opaque
    # Make NaN pixels transparent
    rgba[nan_mask, 3] = 0
    return rgba


_tile_request_counter = 0
_tile_request_lock = threading.Lock()


# TEMPORARILY DISABLED for debugging - uncomment to re-enable caching
# @lru_cache(maxsize=256)
def _render_tile_png_impl(
    taxon_id: int,
    z: int,
    x: int,
    y: int,
    model_id: str,
    layers_key: tuple[str, ...],
    tile_size: int,
    reproject_to_mercator: bool,
) -> bytes:
    global _tile_request_counter
    with _tile_request_lock:
        _tile_request_counter += 1
        request_id = _tile_request_counter

    if _DEBUG_VERBOSITY != "off":
        _debug(f"[TILE_REQUEST #{request_id}] z={z} x={x} y={y} reproject={reproject_to_mercator}")

    try:
        return _render_tile_png_impl_inner(
            taxon_id, z, x, y, model_id, layers_key, tile_size, reproject_to_mercator, request_id
        )
    except Exception as e:
        _debug(f"[ERROR] TILE_REQUEST #{request_id} z={z} x={x} y={y} FAILED: {type(e).__name__}: {e}")
        import traceback
        _debug(f"[ERROR] Traceback:\n{traceback.format_exc()}")
        raise


def _render_tile_png_impl_inner(
    taxon_id: int,
    z: int,
    x: int,
    y: int,
    model_id: str,
    layers_key: tuple[str, ...],
    tile_size: int,
    reproject_to_mercator: bool,
    request_id: int,
) -> bytes:

    # Log adjacent tile bounds for shearing diagnosis (only in verbose mode)
    spec = TileSpec(z=z, x=x, y=y, tile_size=tile_size)
    if _is_verbose():
        spec_left = TileSpec(z=z, x=x-1, y=y, tile_size=tile_size) if x > 0 else None
        spec_up = TileSpec(z=z, x=x, y=y-1, tile_size=tile_size) if y > 0 else None

        bounds = tile_bounds_wgs84(spec)
        _debug(f"[TILE_REQUEST #{request_id}] bounds: W={bounds[0]:.6f} S={bounds[1]:.6f} E={bounds[2]:.6f} N={bounds[3]:.6f}")

        if spec_left:
            left_bounds = tile_bounds_wgs84(spec_left)
            edge_match = abs(left_bounds[2] - bounds[0]) < 1e-9
            if not edge_match:
                _debug(f"[WARNING] EDGE_MISMATCH left tile x={x-1} E={left_bounds[2]:.6f} vs this W={bounds[0]:.6f}")

        if spec_up:
            up_bounds = tile_bounds_wgs84(spec_up)
            edge_match = abs(up_bounds[1] - bounds[3]) < 1e-9
            if not edge_match:
                _debug(f"[WARNING] EDGE_MISMATCH up tile y={y-1} S={up_bounds[1]:.6f} vs this N={bounds[3]:.6f}")

    layer_lookup = gis_lookup.load_layer_metadata()
    stack = np.empty((tile_size, tile_size, len(layers_key)), dtype=np.float32)
    for idx, layer_id in enumerate(layers_key):
        if _is_verbose() and (idx == 0 or idx == len(layers_key) - 1 or idx % 5 == 0):
            _debug(f"[sdm_tile] rendering layer {idx + 1}/{len(layers_key)} {layer_id}")
        # Check if this is a derived layer
        if layer_id in DERIVED_LAYERS:
            stack[:, :, idx] = _render_derived_layer(
                layer_id,
                spec,
                reproject_to_mercator=reproject_to_mercator,
            )
        else:
            stack[:, :, idx] = _render_layer(
                layer_id,
                spec,
                layer_lookup.get(layer_id),
                reproject_to_mercator=reproject_to_mercator,
            )

    # Determine colormap based on layers
    # If single layer and it's slope/aspect, use appropriate colormap
    # If single layer and it's elevation, use terrain colormap
    # Otherwise use heat (for model predictions)
    if len(layers_key) == 1 and layers_key[0] == "slope":
        # For slope: normalize 0-45° to 0-1 range
        preds = np.clip(stack[:, :, 0] / 45.0, 0.0, 1.0)
        preds = np.where(np.isfinite(stack[:, :, 0]), preds, np.nan)
        colormap = "slope"
    elif len(layers_key) == 1 and layers_key[0] == "aspect":
        # For aspect: normalize 0-360° to 0-1 range (circular)
        preds = stack[:, :, 0] / 360.0
        preds = np.where(np.isfinite(stack[:, :, 0]), preds, np.nan)
        colormap = "aspect"
    elif len(layers_key) == 1 and layers_key[0] == "elevation":
        # Single elevation layer - use terrain colormap
        preds = models.predict(model_id, stack)
        colormap = "terrain"
    else:
        # Multiple layers or other - use model prediction with heat colormap
        preds = models.predict(model_id, stack)
        colormap = "heat"

    if _is_verbose():
        _debug(f"[TILE_REQUEST #{request_id}] predictions: min={np.nanmin(preds):.4f} max={np.nanmax(preds):.4f} nan_count={np.isnan(preds).sum()} colormap={colormap}")
    rgba = _colorize(preds, colormap=colormap)
    from PIL import Image
    import io

    image = Image.fromarray(rgba, mode="RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def render_tile_png(
    taxon_id: int,
    z: int,
    x: int,
    y: int,
    model_id: str,
    layers_key: tuple[str, ...],
    tile_size: int,
    reproject_to_mercator: bool,
) -> bytes:
    """Wrapper to track cache hits/misses."""
    # Cache tracking disabled while lru_cache is commented out
    cache_info_fn = getattr(_render_tile_png_impl, "cache_info", None)
    if cache_info_fn:
        cache_info_before = cache_info_fn()
        result = _render_tile_png_impl(
            taxon_id, z, x, y, model_id, layers_key, tile_size, reproject_to_mercator
        )
        cache_info_after = cache_info_fn()
        if cache_info_after.hits > cache_info_before.hits:
            _debug(f"[CACHE_HIT] z={z} x={x} y={y} (cache size={cache_info_after.currsize})")
        else:
            _debug(f"[CACHE_MISS] z={z} x={x} y={y} - rendered fresh (cache size={cache_info_after.currsize})")
    else:
        # Cache disabled
        result = _render_tile_png_impl(
            taxon_id, z, x, y, model_id, layers_key, tile_size, reproject_to_mercator
        )
        _debug(f"[NO_CACHE] z={z} x={x} y={y} - cache disabled")

    return result


def render_tile_bytes(
    taxon_id: int,
    z: int,
    x: int,
    y: int,
    model_id: str | None = None,
    layers: Sequence[str] | None = None,
    tile_size: int = DEFAULT_TILE_SIZE,
    reproject: bool = True,
) -> bytes:
    model_id = (model_id or models.DEFAULT_MODEL_ID).strip()
    layer_list = _load_layer_list(layers)
    if layers:
        meta = gis_lookup.load_layer_metadata()
        # Accept both metadata layers AND derived layers (like "slope")
        unknown = [layer for layer in layer_list if layer not in meta and layer not in DERIVED_LAYERS]
        if unknown:
            raise ValueError(f"Unknown layer ids: {', '.join(unknown)}")
    if not layer_list:
        layer_list = _load_layer_list(None)
    return render_tile_png(
        taxon_id=taxon_id,
        z=z,
        x=x,
        y=y,
        model_id=model_id,
        layers_key=tuple(layer_list),
        tile_size=tile_size,
        reproject_to_mercator=reproject,
    )
