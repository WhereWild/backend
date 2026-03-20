"""Live weather tile rendering from Open-Meteo ncep_gfs013 spatial data on S3."""
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

_PRECIP = np.array([
    [240, 248, 255],
    [100, 180, 255],
    [ 30, 100, 220],
    [  0,  50, 160],
    [  0,  20,  80],
], dtype=np.float32)

_SNOWFALL = np.array([
    [230, 240, 255],
    [160, 200, 255],
    [ 80, 140, 255],
    [ 20,  60, 200],
    [  0,  10, 100],
], dtype=np.float32)

_SOIL_MOIST = np.array([
    [210, 170, 100],
    [160, 130,  60],
    [ 80, 160,  80],
    [ 30, 120, 180],
    [  0,  60, 160],
], dtype=np.float32)

_VPD = np.array([
    [  0, 120, 200],  # low VPD: blue
    [ 80, 200, 120],
    [255, 240,  80],
    [255, 140,   0],
    [200,   0,   0],  # high VPD: red
], dtype=np.float32)

# Categorical color lookup for weather_code_simple (RGBA tuples)
_WEATHER_CODE_COLORS: dict[int, tuple[int, int, int]] = {
    0:  (255, 240,  80),  # clear
    1:  (220, 230, 120),  # mainly clear
    2:  (180, 190, 180),  # partly cloudy
    3:  (120, 120, 130),  # overcast
    51: (160, 210, 255),  # light drizzle
    53: (100, 170, 255),  # moderate drizzle
    55: ( 60, 130, 240),  # dense drizzle
    61: ( 30, 100, 220),  # light rain
    63: (  0,  60, 180),  # moderate rain
    65: (  0,  20, 120),  # heavy rain
    71: (220, 245, 255),  # slight snow — near white/icy
    73: (160, 220, 240),  # moderate snow — cyan
    75: ( 80, 170, 210),  # heavy snow — teal
}

# "derived": True  → computed from other vars, not fetched from S3
_EXTRA_RAW = {"relative_humidity_2m"}  # fetched but not rendered directly

LIVE_WEATHER_VARIABLES: dict[str, dict] = {
    # --- direct ---
    "temperature_2m":            {"model": "ncep_gfs013", "lo": -50.0, "hi":  50.0, "stops": _BLUE_RED},
    "cloud_cover":               {"model": "ncep_gfs013", "lo":   0.0, "hi": 100.0, "stops": _CLOUD},
    "precipitation":             {"model": "ncep_gfs013", "lo":   0.0, "hi":   5.0, "stops": _PRECIP},
    "snowfall_water_equivalent": {"model": "ncep_gfs013", "lo":   0.0, "hi":  10.0, "stops": _SNOWFALL},
    "soil_moisture_0_to_10cm":   {"model": "ncep_gfs013", "lo":   0.0, "hi":   0.5, "stops": _SOIL_MOIST},
    "soil_temperature_0_to_10cm": {"model": "ncep_gfs013", "lo": -10.0, "hi":  40.0, "stops": _BLUE_RED},
    # --- derived from temperature_2m + relative_humidity_2m ---
    "dew_point_2m":           {"model": "ncep_gfs013", "lo": -40.0, "hi":  35.0, "stops": _BLUE_RED, "derived": True},
    "vapor_pressure_deficit":  {"model": "ncep_gfs013", "lo":   0.0, "hi":   5.0, "stops": _VPD,     "derived": True},
    # --- derived from cloud_cover + precipitation + snowfall_water_equivalent ---
    "weather_code_simple":    {"model": "ncep_gfs013", "categorical": True, "derived": True},
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

    # Determine which variables this model needs to supply (direct only; derived computed below)
    raw_needs = (
        {var_id for var_id, cfg in LIVE_WEATHER_VARIABLES.items()
         if cfg["model"] == model and not cfg.get("derived")}
        | _EXTRA_RAW
    )

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
        valid = datetime.fromisoformat(meta["valid_times"][1].replace("Z", "+00:00"))
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

    # Compute derived variables
    cc   = disk_hits.get("cloud_cover")
    prec = disk_hits.get("precipitation")
    swe  = disk_hits.get("snowfall_water_equivalent")
    if cc is not None and prec is not None and swe is not None:
        snow_rate = swe / 10.0  # cm/h (T+1 step = 1h)
        rain_rate = prec         # mm/h
        code = np.full(cc.shape, 3, dtype=np.float32)  # default: overcast
        code[cc < 80] = 2
        code[cc < 50] = 1
        code[cc < 20] = 0
        code[rain_rate >= 0.01] = 51
        code[rain_rate >= 0.5]  = 53
        code[rain_rate >= 1.0]  = 55
        code[rain_rate >= 1.3]  = 61
        code[rain_rate >= 2.5]  = 63
        code[rain_rate >= 7.6]  = 65
        code[snow_rate >= 0.01] = 71
        code[snow_rate >= 0.2]  = 73
        code[snow_rate >= 0.8]  = 75
        disk_hits["weather_code_simple"] = code

    T = disk_hits.get("temperature_2m")
    RH = disk_hits.get("relative_humidity_2m")
    if T is not None and RH is not None:
        RH_c = np.clip(RH, 1.0, 100.0)
        # Magnus formula → dew point (°C)
        gamma = np.log(RH_c / 100.0) + 17.625 * T / (243.04 + T)
        disk_hits["dew_point_2m"] = (243.04 * gamma / (17.625 - gamma)).astype(np.float32)
        # Saturation vapor pressure → VPD (kPa)
        es = 0.6108 * np.exp(17.27 * T / (T + 237.3))
        disk_hits["vapor_pressure_deficit"] = (es * (1.0 - RH_c / 100.0)).astype(np.float32)

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
        resampling=RasterioResampling.nearest if cfg.get("categorical") else RasterioResampling.bilinear,
    )

    if cfg.get("categorical"):
        rgba = np.zeros((tile_size, tile_size, 4), dtype=np.uint8)
        for code, rgb in _WEATHER_CODE_COLORS.items():
            mask = (dest == code)
            rgba[mask, 0] = rgb[0]
            rgba[mask, 1] = rgb[1]
            rgba[mask, 2] = rgb[2]
            rgba[mask, 3] = 210
    else:
        rgba = _colorize(dest, cfg["stops"], cfg["lo"], cfg["hi"])
    rgba[~np.isfinite(dest), 3] = 0
    img = Image.fromarray(rgba, mode="RGBA")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
