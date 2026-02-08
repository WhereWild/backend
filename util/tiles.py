from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from collections import OrderedDict
import math
import threading
from typing import Iterable, Sequence

import numpy as np
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import reproject
import rasterio

from util.config import load_config
from util import gis_lookup, models


CONFIG = load_config("global")

WEB_MERCATOR = "EPSG:3857"
DEFAULT_TILE_SIZE = CONFIG.sdm_tile_size
DEFAULT_MAX_OPEN_DATASETS = 16

FORCED_CATEGORICAL_LAYERS = frozenset({"landcover"})


@dataclass(frozen=True)
class TileSpec:
    z: int
    x: int
    y: int
    tile_size: int = DEFAULT_TILE_SIZE


class DatasetCache:
    def __init__(self, max_open: int = DEFAULT_MAX_OPEN_DATASETS) -> None:
        self._max_open = max_open
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, rasterio.DatasetReader] = OrderedDict()

    def open(self, path: str) -> rasterio.DatasetReader:
        with self._lock:
            existing = self._cache.get(path)
            if existing is not None:
                self._cache.move_to_end(path)
                return existing
            ds = rasterio.open(path)
            self._cache[path] = ds
            if len(self._cache) > self._max_open:
                old_path, old_ds = self._cache.popitem(last=False)
                old_ds.close()
            return ds

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


def _render_layer(
    layer_id: str,
    spec: TileSpec,
    layer_meta: dict[str, object] | None,
    *,
    reproject_to_mercator: bool,
) -> np.ndarray:
    bounds_wgs84 = tile_bounds_wgs84(spec)
    region_size = float(layer_meta.get("region_size") or 10.0) if layer_meta else 10.0
    if reproject_to_mercator:
        transform = tile_transform(spec)
        dst_crs = WEB_MERCATOR
    else:
        min_lon, min_lat, max_lon, max_lat = bounds_wgs84
        transform = from_bounds(min_lon, min_lat, max_lon, max_lat, spec.tile_size, spec.tile_size)
        dst_crs = "EPSG:4326"
    resampling = Resampling.nearest if _is_layer_categorical(layer_id, layer_meta) else Resampling.bilinear
    dest = np.full((spec.tile_size, spec.tile_size), np.nan, dtype=np.float32)
    logged_overview = False
    for lat0, lon0 in _iter_region_origins(bounds_wgs84, region_size):
        region_id = _region_id_from_origin(lat0, lon0)
        cog_path = gis_lookup.get_cog_path_for_region(layer_id, region_id)
        if cog_path is None or not cog_path.exists():
            continue
        ds = _DATASET_CACHE.open(cog_path.as_posix())
        if not logged_overview:
            overviews, src_res_x, src_res_y, desired, dst_res = _estimate_overview_factor(
                ds, bounds_wgs84, spec.tile_size
            )
            if overviews:
                chosen = min(overviews, key=lambda factor: abs(factor - desired))
                print(
                    f"[sdm_tile] layer={layer_id} src_res=({src_res_x:.6f},{src_res_y:.6f})deg "
                    f"dst_res≈{dst_res:.6f}deg overviews={overviews} desired≈{desired:.2f} "
                    f"chosen≈{chosen}",
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
        temp = np.full_like(dest, np.nan)
        reproject(
            source=rasterio.band(ds, 1),
            destination=temp,
            src_transform=ds.transform,
            src_crs=ds.crs,
            src_nodata=ds.nodata,
            dst_transform=transform,
            dst_crs=dst_crs,
            dst_nodata=np.nan,
            resampling=resampling,
        )
        mask = np.isfinite(temp)
        dest[mask] = temp[mask]
    return dest


def _colorize(values: np.ndarray, *, alpha_scale: float = 0.85) -> np.ndarray:
    v = np.clip(values, 0.0, 1.0)
    stops = np.array(
        [
            [28, 38, 102],
            [34, 94, 168],
            [59, 170, 165],
            [246, 190, 0],
            [230, 57, 70],
        ],
        dtype=np.float32,
    )
    idx = (v * (len(stops) - 1)).astype(np.int32)
    frac = (v * (len(stops) - 1)) - idx
    idx = np.clip(idx, 0, len(stops) - 2)
    frac = frac[..., None]
    rgb = stops[idx] * (1.0 - frac) + stops[idx + 1] * frac
    alpha = (v * 255.0 * alpha_scale).astype(np.uint8)
    rgba = np.zeros((*v.shape, 4), dtype=np.uint8)
    rgba[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba[..., 3] = alpha
    return rgba


@lru_cache(maxsize=256)
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
    spec = TileSpec(z=z, x=x, y=y, tile_size=tile_size)
    layer_lookup = gis_lookup.load_layer_metadata()
    stack = np.empty((tile_size, tile_size, len(layers_key)), dtype=np.float32)
    for idx, layer_id in enumerate(layers_key):
        if idx == 0 or idx == len(layers_key) - 1 or idx % 5 == 0:
            print(
                f"[sdm_tile] rendering layer {idx + 1}/{len(layers_key)} {layer_id}",
                flush=True,
            )
        stack[:, :, idx] = _render_layer(
            layer_id,
            spec,
            layer_lookup.get(layer_id),
            reproject_to_mercator=reproject_to_mercator,
        )
    preds = models.predict(model_id, stack)
    rgba = _colorize(preds)
    from PIL import Image
    import io

    image = Image.fromarray(rgba, mode="RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


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
        unknown = [layer for layer in layer_list if layer not in meta]
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
