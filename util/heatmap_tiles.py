from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import math
from pathlib import Path

import numpy as np
from PIL import Image

from util.config import load_config
from util import inference
from util.request_cancellation import CancelCheck


CONFIG = load_config("global")
_HEATMAP_CACHE_NAMESPACE = hashlib.md5(str(CONFIG.data_root).encode()).hexdigest()[:12]
_HEATMAP_TILE_CACHE_DIR = Path("/workspace/cache/darwin-heatmap-tiles")
_HEATMAP_TILE_CACHE_MAX_BYTES = 256 * 1024 * 1024

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


def _tile_cache_path(key: str) -> Path:
    return _HEATMAP_TILE_CACHE_DIR / f"{key}.png"


def _read_tile_cache(key: str) -> bytes | None:
    path = _tile_cache_path(key)
    try:
        data = path.read_bytes()
        path.touch()
        return data
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _write_tile_cache(key: str, data: bytes) -> None:
    try:
        _HEATMAP_TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _tile_cache_path(key).write_bytes(data)
        _evict_tile_cache_if_needed()
    except Exception:
        pass


def _evict_tile_cache_if_needed() -> None:
    try:
        entries = []
        total = 0
        for path in _HEATMAP_TILE_CACHE_DIR.glob("*.png"):
            stat = path.stat()
            entries.append((stat.st_mtime, stat.st_size, path))
            total += stat.st_size
        if total <= _HEATMAP_TILE_CACHE_MAX_BYTES:
            return
        target = int(_HEATMAP_TILE_CACHE_MAX_BYTES * 0.8)
        entries.sort()
        for _, size, path in entries:
            if total <= target:
                break
            path.unlink(missing_ok=True)
            total -= size
    except Exception:
        pass


def _make_tile_cache_key(**kwargs: object) -> str:
    raw = "&".join(f"{key}={value}" for key, value in sorted(kwargs.items()))
    return hashlib.md5(raw.encode()).hexdigest()


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
    coords = _tile_pixel_center_coords(TileSpec(spec.z, spec.x, spec.y, 2))
    lat0, lon0 = coords[0]
    lat_row, lon_row = coords[2]
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
    rgba[finite, 3] = np.clip(40.0 + (finite_norm * 215.0), 0.0, 255.0).astype(np.uint8)
    return rgba


def render_heatmap_tile_bytes(
    species_key: int,
    z: int,
    x: int,
    y: int,
    *,
    tile_size: int = 256,
    feature_mode: str = "prefer_cell_table",
    score_batch_size: int = inference.HEATMAP_DEFAULT_SCORE_BATCH_SIZE,
    cancel_check: CancelCheck | None = None,
) -> bytes:
    if cancel_check is not None:
        cancel_check()

    spec = TileSpec(z=z, x=x, y=y, tile_size=tile_size)
    cache_key = _make_tile_cache_key(
        namespace=_HEATMAP_CACHE_NAMESPACE,
        species_key=species_key,
        z=z,
        x=x,
        y=y,
        tile_size=tile_size,
        feature_mode=feature_mode,
        score_batch_size=score_batch_size,
        bundle_token=inference.bundle_cache_token(),
    )
    cached = _read_tile_cache(cache_key)
    if cached is not None:
        if cancel_check is not None:
            cancel_check()
        return cached

    coords = _tile_pixel_center_coords(spec)
    if cancel_check is not None:
        cancel_check()
    resolution_hint = _tile_resolution_hint(spec)
    scores_list, _ = inference.score_species_coords(
        species_key,
        coords,
        resolution_hint=resolution_hint,
        feature_mode=feature_mode,
        score_batch_size=score_batch_size,
        include_source=False,
        cancel_check=cancel_check,
    )
    scores = np.asarray(
        [np.nan if score is None else score for score in scores_list],
        dtype=np.float32,
    )

    rgba = _colorize_heatmap(scores.reshape((tile_size, tile_size)))
    if cancel_check is not None:
        cancel_check()
    image = Image.fromarray(rgba, mode="RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()
    if cancel_check is not None:
        cancel_check()
    _write_tile_cache(cache_key, payload)
    return payload
