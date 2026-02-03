from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Iterable, Tuple

import numpy as np

try:
    import fsspec
    from omfiles import OmFileReader
except ImportError as exc:
    raise SystemExit(
        "Missing dependencies. Install with:\n"
        "  pip install omfiles fsspec s3fs numpy"
    ) from exc


DEFAULT_MODEL = "copernicus_era5_land"
DEFAULT_VARIABLE = "snow_depth"
DEFAULT_YEAR = 2021
DEFAULT_TIME_INDEX = 0
# Hardcoded test point (Salt Lake City area)
DEFAULT_LAT = 37.360344
DEFAULT_LON = -118.326919
# Hardcoded reference time (UTC) for aggregates
DEFAULT_END_ISO = "2021-07-20T03:49:00Z"


def _open_s3_json(uri: str) -> dict[str, Any] | None:
    try:
        with fsspec.open(
            uri,
            mode="rb",
            s3={"anon": True},
        ) as handle:
            return json.loads(handle.read())
    except Exception:
        return None


def _maybe_axis_from_meta(meta: dict[str, Any], names: Iterable[str]) -> Any | None:
    for name in names:
        if name in meta:
            return meta[name]
    dims = meta.get("dims") or meta.get("dimensions") or {}
    if isinstance(dims, dict):
        for name in names:
            if name in dims:
                return dims[name]
    grid = meta.get("grid")
    if isinstance(grid, dict):
        for name in names:
            if name in grid:
                return grid[name]
    return None


def _find_axis_payload(meta: Any, axis_keys: Tuple[str, ...]) -> Any | None:
    if isinstance(meta, dict):
        for key in axis_keys:
            if key in meta:
                return meta[key]
        for value in meta.values():
            match = _find_axis_payload(value, axis_keys)
            if match is not None:
                return match
    elif isinstance(meta, list):
        for value in meta:
            match = _find_axis_payload(value, axis_keys)
            if match is not None:
                return match
    return None


def _axis_from_meta(meta: dict[str, Any], axis: str) -> np.ndarray | None:
    axis_names = {
        "lat": ("lat", "latitude", "y"),
        "lon": ("lon", "longitude", "x"),
    }
    names = axis_names.get(axis, (axis,))
    payload = _maybe_axis_from_meta(meta, names)
    if payload is None:
        payload = _find_axis_payload(meta, names)
    if payload is None:
        return None
    if isinstance(payload, list):
        return np.array(payload, dtype=float)
    if isinstance(payload, dict):
        start = payload.get("start")
        step = payload.get("step")
        count = payload.get("count")
        if all(isinstance(value, (int, float)) for value in (start, step, count)):
            return np.array([start + step * idx for idx in range(int(count))], dtype=float)
        values = payload.get("values")
        if isinstance(values, list):
            return np.array(values, dtype=float)
        if "data" in payload and isinstance(payload["data"], list):
            return np.array(payload["data"], dtype=float)
    return None


def _nearest_index(axis: np.ndarray, value: float) -> int:
    idx = int(np.abs(axis - value).argmin())
    return max(0, min(idx, len(axis) - 1))


def _index_from_step(axis: np.ndarray, value: float) -> int:
    if axis.size < 2:
        return 0
    step = axis[1] - axis[0]
    if step == 0:
        return 0
    idx = int(round((value - axis[0]) / step))
    return max(0, min(idx, len(axis) - 1))


def _parse_time_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            pass
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            return datetime.fromisoformat(text).timestamp()
        except ValueError:
            return None
    return None


def _iso_to_unix(value: str) -> float:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text).timestamp()


def _lat_lon_indices(
    meta: dict[str, Any],
    lat: float,
    lon: float,
    shape: Tuple[int, int, int] | None = None,
) -> Tuple[int, int]:
    lat_axis = _axis_from_meta(meta, "lat")
    lon_axis = _axis_from_meta(meta, "lon")
    if lat_axis is None or lon_axis is None:
        if shape is not None:
            ny, nx = shape[0], shape[1]
            # Heuristic fallback for common regular grids
            if ny in (1800, 1801) and nx in (3600, 3601):
                # 0.1° grid, lat descending 90 -> -90, lon -180 -> 180
                lat_idx = int(round((90.0 - lat) / 0.1))
                lon_idx = int(round((lon + 180.0) / 0.1))
                lat_idx = max(0, min(lat_idx, ny - 1))
                lon_idx = max(0, min(lon_idx, nx - 1))
                return lat_idx, lon_idx
            if ny in (721, 720) and nx in (1440, 1441):
                # 0.25° grid, lat descending 90 -> -90, lon -180 -> 180
                lat_idx = int(round((90.0 - lat) / 0.25))
                lon_idx = int(round((lon + 180.0) / 0.25))
                lat_idx = max(0, min(lat_idx, ny - 1))
                lon_idx = max(0, min(lon_idx, nx - 1))
                return lat_idx, lon_idx
        top_keys = ", ".join(sorted(meta.keys()))
        raise ValueError(
            "Unable to resolve latitude/longitude axes from metadata. "
            f"Top-level keys: {top_keys}"
        )
    lat_idx = _nearest_index(lat_axis, lat)
    lon_idx = _nearest_index(lon_axis, lon)
    if lat_axis.size > 1:
        lat_idx = _index_from_step(lat_axis, lat)
    if lon_axis.size > 1:
        lon_idx = _index_from_step(lon_axis, lon)
    return lat_idx, lon_idx


def _aggregate_variable(variable: str) -> dict[int, float]:
    data_uri = (
        f"s3://openmeteo/data/{DEFAULT_MODEL}/{variable}/year_{DEFAULT_YEAR}.om"
    )
    backend = fsspec.open(
        f"blockcache::{data_uri}",
        mode="rb",
        s3={"anon": True, "default_block_size": 65536},
        blockcache={"cache_storage": "cache"},
    )

    with OmFileReader(backend) as reader:
        meta = (
            getattr(reader, "meta", None)
            or getattr(reader, "metadata", None)
            or getattr(reader, "attrs", None)
            or {}
        )
        if not isinstance(meta, dict):
            meta = {}
        if not meta:
            variable_meta_uri = (
                f"s3://openmeteo/data/{DEFAULT_MODEL}/{variable}/meta.json"
            )
            static_meta_uri = f"s3://openmeteo/data/{DEFAULT_MODEL}/static/meta.json"
            meta = _open_s3_json(variable_meta_uri) or _open_s3_json(static_meta_uri) or {}

        lat_idx, lon_idx = _lat_lon_indices(
            meta,
            DEFAULT_LAT,
            DEFAULT_LON,
            shape=tuple(reader.shape),
        )
        lat_idx, lon_idx = _resolve_indices_from_candidates(
            reader,
            DEFAULT_LAT,
            DEFAULT_LON,
            default_lat=lat_idx,
            default_lon=lon_idx,
        )
        if not reader.is_array:
            raise SystemExit("Expected a root array in the .om file.")
        if len(reader.shape) != 3:
            raise SystemExit(f"Expected 3D array, got shape {reader.shape}")
        time_len = reader.shape[2]
        resolution = _parse_time_value(meta.get("temporal_resolution_seconds")) or 3600.0
        # For year_YYYY.om files, assume data starts at Jan 1 00:00 UTC.
        start_time = datetime(DEFAULT_YEAR, 1, 1, tzinfo=timezone.utc).timestamp()
        end_target = _iso_to_unix(DEFAULT_END_ISO)
        idx_end = int(round((end_target - start_time) / resolution))
        idx_end = max(0, min(idx_end, time_len - 1))
        windows = [1, 8, 24, 72, 168]
        aggregates = {}
        is_accum = variable in {
            "precipitation",
            "snowfall_water_equivalent",
        }
        max_window = max(windows)
        max_len = int(round((max_window * 3600) / resolution))
        idx_start = max(0, idx_end - max_len + 1)
        series = np.array(
            [reader[lat_idx, lon_idx, idx] for idx in range(idx_start, idx_end + 1)],
            dtype=float,
        )
        if variable == "snow_depth":
            finite = series[np.isfinite(series)]
            if finite.size:
                print("snow_depth_debug:")
                print(f"  samples: {finite.size}/{series.size}")
                print(f"  min: {float(finite.min()):.3f} m")
                print(f"  mean: {float(finite.mean()):.3f} m")
                print(f"  max: {float(finite.max()):.3f} m")
                print(f"  std: {float(finite.std()):.3f} m")
            else:
                print("snow_depth_debug: all NaN in window")
        for hours in windows:
            window_len = int(round((hours * 3600) / resolution))
            window = series[-window_len:]
            window = window[~np.isnan(window)]
            if window.size == 0:
                aggregates[hours] = float("nan")
            elif is_accum:
                aggregates[hours] = float(window.sum())
            else:
                aggregates[hours] = float(window.mean())
    return aggregates


def _weather_code_simple(
    cloudcover: float,
    precipitation: float,
    snowfall_water_equivalent: float,
    model_dt_seconds: int,
) -> int | None:
    if not np.isfinite(cloudcover) or not np.isfinite(precipitation) or not np.isfinite(snowfall_water_equivalent):
        return None
    model_dt_hours = model_dt_seconds / 3600.0
    # Convert snowfall water equivalent (mm) -> cm
    snowfall_cm = (snowfall_water_equivalent / 10.0)

    # Snowfall categories
    rate_snow = snowfall_cm / model_dt_hours
    if 0.01 <= rate_snow < 0.2:
        return 71
    if 0.2 <= rate_snow < 0.8:
        return 73
    if rate_snow >= 0.8:
        return 75

    # Rain/drizzle categories
    rate_rain = precipitation / model_dt_hours
    if 0.01 <= rate_rain < 0.5:
        return 51
    if 0.5 <= rate_rain < 1.0:
        return 53
    if 1.0 <= rate_rain < 1.3:
        return 55
    if 1.3 <= rate_rain < 2.5:
        return 61
    if 2.5 <= rate_rain < 7.6:
        return 63
    if rate_rain >= 7.6:
        return 65

    # Cloud cover fallback
    if cloudcover < 20:
        return 0
    if cloudcover < 50:
        return 1
    if cloudcover < 80:
        return 2
    return 3


def main() -> None:
    print(f"model: {DEFAULT_MODEL}")
    print(f"lat/lon: {DEFAULT_LAT}, {DEFAULT_LON}")
    print(f"end_time_utc: {DEFAULT_END_ISO}")
    aggregates = _aggregate_variable(DEFAULT_VARIABLE)
    label = "sum" if DEFAULT_VARIABLE in {"precipitation", "snowfall_water_equivalent"} else "avg"
    print(f"{DEFAULT_VARIABLE}_{label}_past_hours:")
    for hours in (1, 8, 24, 72, 168):
        print(f"  {hours}h: {aggregates[hours]}")

    # Weather code (simplified: cloud cover + precip + snowfall)
    cloud = _aggregate_variable("cloud_cover")
    precip = _aggregate_variable("precipitation")
    snow = _aggregate_variable("snowfall_water_equivalent")
    # Use last 1h window as "current" snapshot
    cloud_now = cloud[1]
    precip_now = precip[1]
    snow_now = snow[1]
    code = _weather_code_simple(
        cloud_now,
        precip_now,
        snow_now,
        model_dt_seconds=3600,
    )
    print("weather_code_simple_now:")
    print(f"  code: {code}")


def _grid_index_candidates(lat: float, lon: float, ny: int, nx: int) -> list[tuple[str, int, int]]:
    candidates: list[tuple[str, int, int]] = []
    # Lat: descending 90 -> -90, ascending -90 -> 90
    lat_desc = int(round((90.0 - lat) / 0.1))
    lat_asc = int(round((lat + 90.0) / 0.1))
    # Lon: -180..180 and 0..360
    lon_pm = int(round((lon + 180.0) / 0.1))
    lon_360 = int(round((lon % 360.0) / 0.1))
    for name, li, lo in (
        ("lat_desc_lon_pm180", lat_desc, lon_pm),
        ("lat_desc_lon_360", lat_desc, lon_360),
        ("lat_asc_lon_pm180", lat_asc, lon_pm),
        ("lat_asc_lon_360", lat_asc, lon_360),
    ):
        li = max(0, min(li, ny - 1))
        lo = max(0, min(lo, nx - 1))
        candidates.append((name, li, lo))
    return candidates


def _is_nan(value: Any) -> bool:
    try:
        return bool(np.isnan(value))
    except Exception:
        return False


def _resolve_indices_from_candidates(
    reader: OmFileReader,
    lat: float,
    lon: float,
    *,
    default_lat: int,
    default_lon: int,
) -> Tuple[int, int]:
    ny, nx, _ = reader.shape
    candidates = _grid_index_candidates(lat, lon, ny, nx)
    for _name, li, lo in candidates:
        value = reader[li, lo, 0]
        if not _is_nan(value):
            return li, lo
    return default_lat, default_lon


if __name__ == "__main__":
    main()
