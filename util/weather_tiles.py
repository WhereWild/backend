"""Live weather tile rendering from Open-Meteo spatial data on S3 (multi-model)."""
from __future__ import annotations

import io
import json
import logging
import threading
from datetime import datetime
from pathlib import Path

import fsspec
import numpy as np
from omfiles import OmFileReader
from PIL import Image

import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds as rasterio_from_bounds
from rasterio.warp import reproject, Resampling as RasterioResampling

from util.tiles import TileSpec, tile_bounds_mercator, WEB_MERCATOR

log = logging.getLogger(__name__)

S3_SPATIAL = "s3://openmeteo/data_spatial"

# Per-model grid configuration
MODEL_CONFIGS: dict[str, dict] = {
    "ncep_gfs013": {
        "lat_min": -89.912125, "lat_max":  89.912125,
        "lon_min": -180.0,     "lon_max":  179.88281,
        "flipud": True,   # stored south-up
    },
    "dwd_icon": {
        "lat_min": -90.0,  "lat_max":  90.0,
        "lon_min": -180.0, "lon_max":  179.875,
        "flipud": False,  # stored north-down
    },
}

# --- Color stops ---
_BLUE_RED = np.array([
    [  0,   0, 200],
    [  0, 150, 255],
    [255, 255, 100],
    [255, 120,   0],
    [200,   0,   0],
], dtype=np.float32)

_CLOUD = np.array([
    [ 30,  30,  60],
    [100, 120, 160],
    [180, 190, 210],
    [230, 235, 245],
    [255, 255, 255],
], dtype=np.float32)

_HUMID = np.array([
    [230, 100,  20],  # very dry: orange
    [250, 200,  50],
    [200, 230, 100],
    [ 50, 180, 100],
    [  0, 100, 200],  # very humid: blue
], dtype=np.float32)

LIVE_WEATHER_VARIABLES: dict[str, dict] = {
    "temperature_2m":       {"model": "ncep_gfs013", "lo": -50.0, "hi":  50.0, "stops": _BLUE_RED},
    "relative_humidity_2m": {"model": "ncep_gfs013", "lo":   0.0, "hi": 100.0, "stops": _HUMID},
    "cloud_cover":          {"model": "dwd_icon",    "lo":   0.0, "hi": 100.0, "stops": _CLOUD},
}

# --- Disk cache ---
_DISK_CACHE_DIR = Path("/tmp/wherewild_weather_cache")


def _disk_path(model: str, ref_time: str, var_id: str) -> Path:
    safe = ref_time.replace(":", "-").replace(" ", "_")
    return _DISK_CACHE_DIR / f"{model}__{safe}__{var_id}.npy"


def _save_to_disk(model: str, ref_time: str, var_id: str, arr: np.ndarray) -> None:
    _DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(_disk_path(model, ref_time, var_id), arr)


def _load_from_disk(model: str, ref_time: str, var_id: str) -> np.ndarray | None:
    path = _disk_path(model, ref_time, var_id)
    if path.exists():
        return np.load(path)
    return None


# --- Memory cache ---
_cache: dict[str, np.ndarray] = {}       # variable_id → [ny, nx] float32
_cache_ref_times: dict[str, str] = {}    # model → ref_time
_cache_lock = threading.Lock()


def _s3_path(model: str, ref: datetime, valid: datetime) -> str:
    run_dir = f"{ref.year:04d}/{ref.month:02d}/{ref.day:02d}/{ref.hour:02d}{ref.minute:02d}Z"
    fname = valid.strftime("%Y-%m-%dT%H%M") + ".om"
    return f"{S3_SPATIAL}/{model}/{run_dir}/{fname}"


def _load_model(model: str) -> None:
    """Fetch all variables for one model, using disk cache where possible."""
    fs = fsspec.filesystem("s3", anon=True)
    with fs.open(f"{S3_SPATIAL}/{model}/latest.json") as f:
        meta = json.load(f)
    ref_time = meta["reference_time"]

    # Determine which variables this model needs to supply
    raw_needs = {var_id for var_id, cfg in LIVE_WEATHER_VARIABLES.items() if cfg["model"] == model}

    with _cache_lock:
        current_ref = _cache_ref_times.get(model)
        vars_for_model = {vid for vid, cfg in LIVE_WEATHER_VARIABLES.items() if cfg["model"] == model}
        already_done = current_ref == ref_time and all(v in _cache for v in vars_for_model)
    if already_done:
        print(f"[weather_tiles] {model} already current ({ref_time})", flush=True)
        return

    # Try disk for each raw variable
    disk_hits: dict[str, np.ndarray] = {}
    for var_id in raw_needs:
        arr = _load_from_disk(model, ref_time, var_id)
        if arr is not None:
            disk_hits[var_id] = arr
            print(f"[weather_tiles] {model}/{var_id} from disk", flush=True)

    # Fetch missing from S3
    need = [v for v in raw_needs if v not in disk_hits]
    if need:
        ref = datetime.fromisoformat(ref_time.replace("Z", "+00:00"))
        valid = datetime.fromisoformat(meta["valid_times"][0].replace("Z", "+00:00"))
        path = _s3_path(model, ref, valid)
        print(f"[weather_tiles] S3 fetch: {need} from {model} ({ref_time})", flush=True)
        backend = fsspec.open(path, mode="rb", s3={"anon": True})
        root = OmFileReader(backend)
        available = {root.get_child_by_index(i).name for i in range(root.num_children)}
        for var_id in need:
            if var_id not in available:
                print(f"[weather_tiles] {var_id} not in {model}, skipping", flush=True)
                continue
            node = root.get_child_by_name(var_id)
            ny, nx = node.shape
            arr = node.read_array((slice(0, ny), slice(0, nx)))
            _save_to_disk(model, ref_time, var_id, arr)
            disk_hits[var_id] = arr
            print(f"[weather_tiles] {model}/{var_id}  shape={arr.shape}  "
                  f"range=[{float(arr.min()):.1f}, {float(arr.max()):.1f}]", flush=True)

    # Populate memory cache
    with _cache_lock:
        for var_id, cfg in LIVE_WEATHER_VARIABLES.items():
            if cfg["model"] != model:
                continue
            arr = disk_hits.get(var_id)
            if arr is not None:
                _cache[var_id] = arr
        _cache_ref_times[model] = ref_time


def load_cache() -> None:
    """Populate memory cache for all models."""
    models = {cfg["model"] for cfg in LIVE_WEATHER_VARIABLES.values()}
    for model in sorted(models):
        try:
            _load_model(model)
        except Exception as exc:
            print(f"[weather_tiles] ERROR loading {model}: {exc}", flush=True)
            import traceback; traceback.print_exc()
    print(f"[weather_tiles] cache ready. vars={list(_cache.keys())}", flush=True)


def _colorize(arr: np.ndarray, stops: np.ndarray, lo: float, hi: float) -> np.ndarray:
    norm = np.clip((arr - lo) / max(1e-9, hi - lo), 0.0, 1.0)
    positions = np.linspace(0.0, 1.0, stops.shape[0], dtype=np.float32)
    rgba = np.zeros((*arr.shape, 4), dtype=np.uint8)
    rgba[..., 0] = np.interp(norm, positions, stops[:, 0]).astype(np.uint8)
    rgba[..., 1] = np.interp(norm, positions, stops[:, 1]).astype(np.uint8)
    rgba[..., 2] = np.interp(norm, positions, stops[:, 2]).astype(np.uint8)
    rgba[..., 3] = 210
    return rgba


def render_weather_tile_bytes(variable_id: str, z: int, x: int, y: int,
                               tile_size: int = 256) -> bytes | None:
    """Render a tile PNG from the in-memory cache. Returns None if not ready."""
    with _cache_lock:
        arr = _cache.get(variable_id)
    if arr is None:
        return None

    cfg = LIVE_WEATHER_VARIABLES[variable_id]
    model_cfg = MODEL_CONFIGS[cfg["model"]]
    ny, nx = arr.shape

    spec = TileSpec(z=z, x=x, y=y, tile_size=tile_size)
    src = np.flipud(arr) if model_cfg["flipud"] else arr
    src_transform = rasterio_from_bounds(
        model_cfg["lon_min"], model_cfg["lat_min"],
        model_cfg["lon_max"], model_cfg["lat_max"],
        nx, ny,
    )
    src_crs = CRS.from_epsg(4326)

    minx, miny, maxx, maxy = tile_bounds_mercator(spec)
    dst_transform = rasterio_from_bounds(minx, miny, maxx, maxy, tile_size, tile_size)
    dst_crs = CRS.from_string(WEB_MERCATOR)

    dest = np.full((tile_size, tile_size), np.nan, dtype=np.float32)
    reproject(
        source=src,
        destination=dest,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=np.nan,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        dst_nodata=np.nan,
        resampling=RasterioResampling.bilinear,
    )

    rgba = _colorize(dest, cfg["stops"], cfg["lo"], cfg["hi"])
    rgba[~np.isfinite(dest), 3] = 0
    img = Image.fromarray(rgba, mode="RGBA")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
