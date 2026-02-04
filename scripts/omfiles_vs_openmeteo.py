from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from typing import Any

import numpy as np
import pyarrow.parquet as pq

import fsspec
from omfiles import OmFileReader

from util.config import load_config
PARQUET_PATH = Path(
    "/workspace/data/species/taxonomy/Animalia_1/Chordata_44/"
    "Amphibia_131/Anura_952/Scaphiopodidae_3098/Spea_2429782/"
    "Spea_intermontana_2429791/occurrence.parquet"
)
LAT_COL = "decimalLatitude"
LON_COL = "decimalLongitude"
TIME_COL = "eventTimestamp"

CONFIG = load_config("global")
ROW_INDICES: list[int] | None = None
SAMPLE_COUNT = 3
SAMPLE_SEED = 7
US_LAT_RANGE = (40.0, 50.0)
US_LON_RANGE = (-125.0, -100.0)
TIME_START = datetime(2017, 1, 1, tzinfo=timezone.utc)
TIME_END = datetime(2019, 1, 1, tzinfo=timezone.utc)
API_NONZERO_MIN = 1
WINTER_MONTHS = {11, 12, 1, 2, 3}
SKIP_VARIABLES = {"weather_code_simple"}
# Set to a non-empty list (e.g., ["precipitation"]) to focus diagnostics.
ONLY_VARIABLES: list[str] = []
VARIABLES = [
    v for v in CONFIG.temporal_models_by_variable.keys() if v not in SKIP_VARIABLES
]
if ONLY_VARIABLES:
    VARIABLES = [v for v in VARIABLES if v in ONLY_VARIABLES]
SHIFT_RANGE_HOURS = range(-2, 3)
GRID_MODES = (
    "lat_desc_lon_pm180",
    "lat_desc_lon_360",
    "lat_asc_lon_pm180",
    "lat_asc_lon_360",
)
API_MODELS = {
    "copernicus_era5": "era5",
    "copernicus_era5_land": "era5_land",
    "copernicus_era5_ensemble": "era5_ensemble",
}


def _api_model_name(model: str) -> str:
    return API_MODELS.get(model, model)


def _model_for_variable(variable: str) -> str:
    models = CONFIG.temporal_models_by_variable.get(variable, ())
    if not models:
        return ""
    for preferred in CONFIG.temporal_model_preference:
        if preferred in models:
            return preferred
    return models[0]


def _agg_mode_for_variable(variable: str) -> str:
    return CONFIG.temporal_agg_by_variable.get(variable, "avg")


@dataclass(frozen=True)
class AxisInfo:
    lat_start: float
    lat_step: float
    lon_start: float
    lon_step: float
    ny: int
    nx: int

    @property
    def lon_360(self) -> bool:
        lon_end = self.lon_start + self.lon_step * (self.nx - 1)
        return self.lon_start >= -1.0 and lon_end > 180.0


def _to_datetime_utc(ts_value: float) -> datetime:
    ts = float(ts_value)
    if ts > 1e12:
        ts /= 1e9
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _sample_rows(
    table: pq.Table,
    *,
    count: int,
    seed: int,
) -> list[int]:
    data = table.to_pydict()
    lats = np.array(data[LAT_COL], dtype=float)
    lons = np.array(data[LON_COL], dtype=float)
    times = np.array(data[TIME_COL], dtype=float)
    # Heuristic: if value looks like ns, scale to seconds
    times = np.where(times > 1e12, times / 1e9, times)

    lat_ok = (lats >= US_LAT_RANGE[0]) & (lats <= US_LAT_RANGE[1])
    lon_ok = (lons >= US_LON_RANGE[0]) & (lons <= US_LON_RANGE[1])
    time_ok = (times >= TIME_START.timestamp()) & (times < TIME_END.timestamp())
    candidates = np.flatnonzero(lat_ok & lon_ok & time_ok)
    if candidates.size:
        winter_candidates = []
        for idx in candidates:
            dt = datetime.fromtimestamp(float(times[idx]), tz=timezone.utc)
            if dt.month in WINTER_MONTHS:
                winter_candidates.append(int(idx))
        if winter_candidates:
            candidates = np.array(winter_candidates, dtype=int)
    if candidates.size == 0:
        return list(range(min(count, table.num_rows)))
    rng = np.random.default_rng(seed)
    pick = rng.choice(candidates, size=min(count, candidates.size), replace=False)
    return [int(i) for i in pick]


def _sample_rows_for_model(
    table: pq.Table,
    *,
    model: str,
    count: int,
    seed: int,
) -> list[int]:
    """Sample rows per model; apply winter filter only for snow_depth (era5_land)."""
    data = table.to_pydict()
    lats = np.array(data[LAT_COL], dtype=float)
    lons = np.array(data[LON_COL], dtype=float)
    times = np.array(data[TIME_COL], dtype=float)
    times = np.where(times > 1e12, times / 1e9, times)

    lat_ok = (lats >= US_LAT_RANGE[0]) & (lats <= US_LAT_RANGE[1])
    lon_ok = (lons >= US_LON_RANGE[0]) & (lons <= US_LON_RANGE[1])
    time_ok = (times >= TIME_START.timestamp()) & (times < TIME_END.timestamp())
    candidates = np.flatnonzero(lat_ok & lon_ok & time_ok)

    if model == "copernicus_era5_land":
        winter_candidates = []
        for idx in candidates:
            dt = datetime.fromtimestamp(float(times[idx]), tz=timezone.utc)
            if dt.month in WINTER_MONTHS:
                winter_candidates.append(int(idx))
        if winter_candidates:
            candidates = np.array(winter_candidates, dtype=int)

    if candidates.size == 0:
        return list(range(min(count, table.num_rows)))
    rng = np.random.default_rng(seed)
    pick = rng.choice(candidates, size=min(count, candidates.size), replace=False)
    return [int(i) for i in pick]


def _fetch_openmeteo_agg_24h(
    lat: float,
    lon: float,
    dt: datetime,
    *,
    variable: str,
    agg_mode: str,
    model: str,
) -> tuple[float, str]:
    end_dt = dt.replace(minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(hours=23)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat:.6f}"
        f"&longitude={lon:.6f}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&hourly={variable}"
        f"&models={_api_model_name(model)}"
        "&elevation=nan"
        "&timezone=UTC"
    )
    with urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    vals = hourly.get(variable) or []
    if not times or not vals:
        raise RuntimeError(f"Open-Meteo returned no hourly {variable}")

    target_str = end_dt.strftime("%Y-%m-%dT%H:%M")
    try:
        idx_end = times.index(target_str)
    except ValueError as exc:
        raise RuntimeError("Target timestamp missing from Open-Meteo response") from exc

    idx_start = idx_end - 23
    if idx_start < 0:
        raise RuntimeError("Not enough hourly values to compute 24h sum")

    window = vals[idx_start:idx_end + 1]
    if len(window) != 24:
        raise RuntimeError("Unexpected hourly window size for 24h window")
    numeric = [float(v) for v in window]
    if agg_mode == "sum":
        return float(sum(numeric)), url
    return float(sum(numeric) / len(numeric)), url


def _fetch_openmeteo_hourly(
    lat: float,
    lon: float,
    start_dt: datetime,
    end_dt: datetime,
    *,
    variable: str,
    model: str,
) -> tuple[list[str], list[float], str]:
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat:.6f}"
        f"&longitude={lon:.6f}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&hourly={variable}"
        f"&models={_api_model_name(model)}"
        "&elevation=nan"
        "&timezone=UTC"
    )
    with urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    vals = hourly.get(variable) or []
    if not times or not vals:
        raise RuntimeError(f"Open-Meteo returned no hourly {variable}")
    return times, [float(v) for v in vals], url


def _open_om_reader(model: str, variable: str, year: int) -> OmFileReader:
    local_path = Path(
        f"/workspace/data/gis/temporal/{model}/{variable}/year_{year}.om"
    )
    if local_path.exists():
        return OmFileReader(fsspec.open(local_path.as_posix(), mode="rb"))
    uri = f"s3://openmeteo/data/{model}/{variable}/year_{year}.om"
    return OmFileReader(
        fsspec.open(
            f"blockcache::{uri}",
            mode="rb",
            s3={"anon": True, "default_block_size": 65536},
            blockcache={"cache_storage": "cache"},
        )
    )


def _open_s3_json(uri: str) -> dict | None:
    try:
        with fsspec.open(uri, mode="rb", s3={"anon": True}) as handle:
            return json.loads(handle.read())
    except Exception:
        return None


def _load_meta(reader: OmFileReader, model: str, variable: str) -> dict:
    meta = (
        getattr(reader, "meta", None)
        or getattr(reader, "metadata", None)
        or getattr(reader, "attrs", None)
        or {}
    )
    if isinstance(meta, dict) and meta:
        return meta
    variable_meta_uri = f"s3://openmeteo/data/{model}/{variable}/meta.json"
    static_meta_uri = f"s3://openmeteo/data/{model}/static/meta.json"
    return _open_s3_json(variable_meta_uri) or _open_s3_json(static_meta_uri) or {}


def _axis_from_meta(meta: dict, axis_keys: tuple[str, ...]) -> tuple[float, float, int] | None:
    def _extract(payload: object) -> tuple[float, float, int] | None:
        if isinstance(payload, dict):
            start = payload.get("start")
            step = payload.get("step")
            count = payload.get("count")
            if all(isinstance(v, (int, float)) for v in (start, step, count)):
                return float(start), float(step), int(count)
            values = payload.get("values")
            if isinstance(values, list) and len(values) >= 2:
                return float(values[0]), float(values[1] - values[0]), len(values)
        if isinstance(payload, list) and len(payload) >= 2:
            return float(payload[0]), float(payload[1] - payload[0]), len(payload)
        return None

    for key in axis_keys:
        if key in meta:
            res = _extract(meta[key])
            if res:
                return res
    for value in meta.values():
        if isinstance(value, dict):
            res = _axis_from_meta(value, axis_keys)
            if res:
                return res
    return None


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


def _axis_info(meta: dict, ny: int, nx: int) -> AxisInfo:
    grid = meta.get("grid") or meta.get("dims") or {}
    lat_meta = _axis_from_meta(grid if isinstance(grid, dict) else meta, ("lat", "latitude", "y"))
    lon_meta = _axis_from_meta(grid if isinstance(grid, dict) else meta, ("lon", "longitude", "x"))
    if lat_meta and lon_meta:
        lat_start, lat_step, _ = lat_meta
        lon_start, lon_step, _ = lon_meta
        return AxisInfo(lat_start, lat_step, lon_start, lon_step, ny, nx)
    if ny in (1801, 1800) and nx in (3600, 3601):
        return AxisInfo(90.0, -0.1, 0.0, 0.1, ny, nx)
    return AxisInfo(90.0, -0.25, -180.0, 0.25, ny, nx)


def _indices_from_axis(lat: float, lon: float, axis: AxisInfo) -> tuple[int, int]:
    lon_val = lon + 360.0 if axis.lon_360 and lon < 0 else lon
    lat_idx = int(round((lat - axis.lat_start) / axis.lat_step))
    lon_idx = int(round((lon_val - axis.lon_start) / axis.lon_step))
    lat_idx = max(0, min(lat_idx, axis.ny - 1))
    lon_idx = max(0, min(lon_idx, axis.nx - 1))
    return lat_idx, lon_idx


def _grid_indices_mode(
    lat: float, lon: float, ny: int, nx: int, mode: str, step: float
) -> tuple[int, int]:
    if mode == "lat_asc_lon_360":
        lat_idx = int(round((lat + 90.0) / step))
        lon_idx = int(round((lon % 360.0) / step))
    elif mode == "lat_asc_lon_pm180":
        lat_idx = int(round((lat + 90.0) / step))
        lon_idx = int(round((lon + 180.0) / step))
    elif mode == "lat_desc_lon_360":
        lat_idx = int(round((90.0 - lat) / step))
        lon_idx = int(round((lon % 360.0) / step))
    else:
        lat_idx = int(round((90.0 - lat) / step))
        lon_idx = int(round((lon + 180.0) / step))
    lat_idx = max(0, min(lat_idx, ny - 1))
    lon_idx = max(0, min(lon_idx, nx - 1))
    return lat_idx, lon_idx


def _grid_index_candidates(lat: float, lon: float, ny: int, nx: int, step: float) -> list[tuple[int, int]]:
    candidates: list[tuple[int, int]] = []
    lat_desc = int(round((90.0 - lat) / step))
    lat_asc = int(round((lat + 90.0) / step))
    lon_pm = int(round((lon + 180.0) / step))
    lon_360 = int(round((lon % 360.0) / step))
    for li, lo in (
        (lat_desc, lon_pm),
        (lat_desc, lon_360),
        (lat_asc, lon_pm),
        (lat_asc, lon_360),
    ):
        li = max(0, min(li, ny - 1))
        lo = max(0, min(lo, nx - 1))
        candidates.append((li, lo))
    return candidates


def _is_nan(value: object) -> bool:
    try:
        return bool(np.isnan(value))
    except Exception:
        return False


def _agg_24h_from_omfiles(
    lat: float,
    lon: float,
    dt: datetime,
    *,
    model: str,
    variable: str,
    agg_mode: str,
    grid_mode: str | None = None,
) -> float:
    year = dt.year
    with _open_om_reader(model, variable, year) as reader:
        ny, nx, time_len = reader.shape
        meta = _load_meta(reader, model, variable)
        axis = _axis_info(meta, ny, nx)
        step = 0.1 if (ny in (1801, 1800) and nx in (3600, 3601)) else 0.25
        if grid_mode:
            lat_idx, lon_idx = _grid_indices_mode(lat, lon, ny, nx, grid_mode, step)
        else:
            lat_idx, lon_idx = _indices_from_axis(lat, lon, axis)

        resolution = 3600.0
        if isinstance(meta, dict):
            value = meta.get("temporal_resolution_seconds")
            if isinstance(value, (int, float)):
                resolution = float(value)

        start_time = datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()
        meta_start = _parse_time_value(meta.get("data_start_time")) if isinstance(meta, dict) else None
        if meta_start is not None and abs(meta_start - start_time) > resolution:
            start_time = meta_start
        end_dt = dt.replace(minute=0, second=0, microsecond=0)
        idx_end = int(round((end_dt.timestamp() - start_time) / resolution))
        idx_end = max(0, min(idx_end, time_len - 1))
        window_len = int(round((24 * 3600) / resolution))
        idx_start = max(0, idx_end - window_len + 1)
        series = np.array(
            [reader[lat_idx, lon_idx, idx] for idx in range(idx_start, idx_end + 1)],
            dtype=float,
        )
        series = series[np.isfinite(series)]
        if series.size == 0:
            return float("nan")
        if agg_mode == "sum":
            return float(series.sum())
        return float(series.mean())


def _omfiles_hourly_series(
    lat: float,
    lon: float,
    start_dt: datetime,
    end_dt: datetime,
    *,
    model: str,
    variable: str,
    grid_mode: str | None = None,
) -> tuple[list[str], list[float], str]:
    year = start_dt.year
    with _open_om_reader(model, variable, year) as reader:
        ny, nx, time_len = reader.shape
        meta = _load_meta(reader, model, variable)
        axis = _axis_info(meta, ny, nx)
        step = 0.1 if (ny in (1801, 1800) and nx in (3600, 3601)) else 0.25

        resolution = 3600.0
        if isinstance(meta, dict):
            value = meta.get("temporal_resolution_seconds")
            if isinstance(value, (int, float)):
                resolution = float(value)
        meta_start = _parse_time_value(meta.get("data_start_time")) if isinstance(meta, dict) else None

        start_time = datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()
        if meta_start is not None and abs(meta_start - start_time) > resolution:
            start_time = meta_start
        start_ts = start_dt.timestamp()
        end_ts = end_dt.timestamp()
        idx_start = int(round((start_ts - start_time) / resolution))
        idx_end = int(round((end_ts - start_time) / resolution))
        idx_start = max(0, min(idx_start, time_len - 1))
        idx_end = max(0, min(idx_end, time_len - 1))
        if idx_end < idx_start:
            idx_start, idx_end = idx_end, idx_start

        if grid_mode:
            lat_idx, lon_idx = _grid_indices_mode(lat, lon, ny, nx, grid_mode, step)
            best_mode = grid_mode
        else:
            lat_idx, lon_idx = _indices_from_axis(lat, lon, axis)
            best_mode = "axis_meta"
        best_vals = np.array(
            [reader[lat_idx, lon_idx, idx] for idx in range(idx_start, idx_end + 1)],
            dtype=float,
        )

        times = []
        vals = []
        for offset, idx in enumerate(range(idx_start, idx_end + 1)):
            ts = start_time + idx * resolution
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            times.append(dt.strftime("%Y-%m-%dT%H:%M"))
            vals.append(float(best_vals[offset]))

        return times, vals, best_mode


def _best_grid_mode_by_api(
    lat: float,
    lon: float,
    start_dt: datetime,
    end_dt: datetime,
    api_times: list[str],
    api_vals: list[float],
    *,
    model: str,
    variable: str,
) -> tuple[str | None, int, float]:
    api_map = {t: v for t, v in zip(api_times, api_vals)}
    best_mode = None
    best_shift = 0
    best_mae = float("inf")
    best_count = -1
    for mode in GRID_MODES:
        om_times, om_vals, _ = _omfiles_hourly_series(
            lat, lon, start_dt, end_dt, model=model, variable=variable, grid_mode=mode
        )
        om_map = {t: v for t, v in zip(om_times, om_vals)}
        mode_best_mae = float("inf")
        mode_best_shift = 0
        mode_best_count = -1
        for shift in SHIFT_RANGE_HOURS:
            errors = []
            count = 0
            for t in om_times:
                dt_t = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                shifted = dt_t + timedelta(hours=shift)
                key = shifted.strftime("%Y-%m-%dT%H:%M")
                if key in api_map:
                    ov = om_map.get(t)
                    av = api_map.get(key)
                    if np.isfinite(ov) and np.isfinite(av):
                        errors.append(abs(ov - av))
                        count += 1
            if errors:
                mae = sum(errors) / len(errors)
                if mae < mode_best_mae or (mae == mode_best_mae and count > mode_best_count):
                    mode_best_mae = mae
                    mode_best_shift = shift
                    mode_best_count = count
        if mode_best_mae < best_mae or (
            mode_best_mae == best_mae and mode_best_count > best_count
        ):
            best_mae = mode_best_mae
            best_shift = mode_best_shift
            best_mode = mode
            best_count = mode_best_count
    return best_mode, best_shift, best_mae


def _debug_candidates(
    reader: OmFileReader,
    lat: float,
    lon: float,
    idx_start: int,
    idx_end: int,
    axis: AxisInfo,
) -> None:
    ny, nx, _ = reader.shape
    step = 0.1 if (ny in (1801, 1800) and nx in (3600, 3601)) else 0.25
    candidates = _grid_index_candidates(lat, lon, ny, nx, step)
    print("[debug] grid_axis:")
    print(
        f"  lat_start={axis.lat_start} lat_step={axis.lat_step} "
        f"lon_start={axis.lon_start} lon_step={axis.lon_step} lon_360={axis.lon_360}"
    )
    print("[debug] candidates_24h:")
    for name, (li, lo) in enumerate(candidates):
        series = np.array(
            [reader[li, lo, idx] for idx in range(idx_start, idx_end + 1)],
            dtype=float,
        )
        finite = series[np.isfinite(series)]
        total = float(finite.sum()) if finite.size else float("nan")
        mode_label = GRID_MODES[name] if name < len(GRID_MODES) else f"cand_{name}"
        print(f"  {mode_label} idx=({li},{lo}) sum={total}")
    lat_idx, lon_idx = _indices_from_axis(lat, lon, axis)
    print(f"[debug] axis_idx=({lat_idx},{lon_idx})")

    # small neighborhood scan to see if we are just off by a cell
    best_sum = -1.0
    best_idx = None
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            li = max(0, min(lat_idx + di, ny - 1))
            lo = max(0, min(lon_idx + dj, nx - 1))
            series = np.array(
                [reader[li, lo, idx] for idx in range(idx_start, idx_end + 1)],
                dtype=float,
            )
            finite = series[np.isfinite(series)]
            total = float(finite.sum()) if finite.size else float("nan")
            if np.isfinite(total) and total > best_sum:
                best_sum = total
                best_idx = (li, lo)
    if best_idx is not None:
        print(f"[debug] neighborhood_best idx={best_idx} sum={best_sum}")


def main() -> None:
    if not PARQUET_PATH.exists():
        raise SystemExit(f"Missing parquet: {PARQUET_PATH}")

    table = pq.read_table(PARQUET_PATH, columns=[LAT_COL, LON_COL, TIME_COL]).combine_chunks()
    if table.num_rows == 0:
        raise SystemExit("Parquet has no rows")

    if ROW_INDICES:
        base_indices = [i for i in ROW_INDICES if 0 <= i < table.num_rows]
    else:
        base_indices = _sample_rows(table, count=SAMPLE_COUNT, seed=SAMPLE_SEED)
    print(f"sample_rows_default={base_indices}")
    all_diffs: list[float] = []
    all_abs: list[float] = []
    pass_count = 0
    overall_total = 0
    overall_valid = 0
    overall_nan_om = 0
    overall_nan_api = 0
    top_runs: list[tuple[float, str, int, float, float, str]] = []
    var_summaries: list[tuple[str, str, float, str, int, int]] = []

    for variable in VARIABLES:
        model = _model_for_variable(variable)
        if not model:
            print(f"\n=== variable={variable} model=none (skipped) ===")
            continue
        agg_mode = _agg_mode_for_variable(variable)
        print(f"\n=== variable={variable} model={model} agg={agg_mode} ===")
        diffs: list[float] = []
        var_total = 0
        var_valid = 0
        var_nan_om = 0
        var_nan_api = 0
        best_mode: str | None = None
        best_shift = 0
        best_mae = float("inf")
        best_mode_attempted = False
        grid_mode_set: set[str] = set()

        if ROW_INDICES:
            indices = base_indices
        else:
            indices = _sample_rows_for_model(
                table, model=model, count=SAMPLE_COUNT, seed=SAMPLE_SEED
            )
        print(f"sample_rows_model={model} -> {indices}")

        for idx in indices:
            row = table.slice(idx, 1)
            lat = row[LAT_COL][0].as_py()
            lon = row[LON_COL][0].as_py()
            ts = row[TIME_COL][0].as_py()
            if lat is None or lon is None or ts is None:
                print(f"row={idx} missing lat/lon/timestamp")
                continue

            dt = _to_datetime_utc(ts)
            try:
                api_val, url = _fetch_openmeteo_agg_24h(
                    float(lat),
                    float(lon),
                    dt,
                    variable=variable,
                    agg_mode=agg_mode,
                    model=model,
                )
            except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
                print(f"row={idx} api_error={exc}")
                continue

            var_total += 1
            overall_total += 1

            # Detailed hourly comparison for first row only
            if best_mode is None and not best_mode_attempted:
                end_dt = dt.replace(minute=0, second=0, microsecond=0)
                start_dt = end_dt - timedelta(hours=47)
                try:
                    api_times, api_vals, api_url = _fetch_openmeteo_hourly(
                        float(lat),
                        float(lon),
                        start_dt,
                        end_dt,
                        variable=variable,
                        model=model,
                    )
                except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
                    print(f"[hourly] api_error={exc}")
                    api_times = []
                    api_vals = []
                    api_url = ""

                if api_times and api_vals:
                    end_key = end_dt.strftime("%Y-%m-%dT%H:%M")
                    try:
                        api_end_idx = api_times.index(end_key)
                    except ValueError:
                        api_end_idx = None
                    if api_end_idx is None or api_end_idx < 23:
                        print(
                            "[hourly] api_window_missing: skipping grid_mode selection for this row"
                        )
                        api_end_idx = None
                    else:
                        api_window = api_vals[api_end_idx - 23 : api_end_idx + 1]
                        api_nonzero = sum(1 for v in api_window if abs(v) > 0)
                        if api_nonzero < API_NONZERO_MIN:
                            print(
                                f"[hourly] api_all_zero: skipping grid_mode selection for this row "
                                f"(nonzero={api_nonzero})"
                            )
                            api_end_idx = None

                    if api_end_idx is not None:
                        best_mode, best_shift, best_mae = _best_grid_mode_by_api(
                            float(lat),
                            float(lon),
                            start_dt,
                            end_dt,
                            api_times,
                            api_vals,
                            model=model,
                            variable=variable,
                        )
                        if best_mode is not None:
                            best_mode_attempted = True

                        om_times, om_vals, om_mode = _omfiles_hourly_series(
                            float(lat),
                            float(lon),
                            start_dt,
                            end_dt,
                            model=model,
                            variable=variable,
                            grid_mode=best_mode,
                        )

                        # Build lookup for API values
                        api_map = {t: v for t, v in zip(api_times, api_vals)}
                        om_map = {t: v for t, v in zip(om_times, om_vals)}

                        # Extra debug to validate grid/time assumptions
                        try:
                            with _open_om_reader(model, variable, end_dt.year) as reader:
                                ny, nx, _ = reader.shape
                                meta = _load_meta(reader, model, variable)
                                axis = _axis_info(meta, ny, nx)
                                resolution = float(meta.get("temporal_resolution_seconds") or 3600.0)
                                start_time = datetime(end_dt.year, 1, 1, tzinfo=timezone.utc).timestamp()
                                meta_start = _parse_time_value(meta.get("data_start_time"))
                                if meta_start is not None and abs(meta_start - start_time) > resolution:
                                    start_time = meta_start
                                idx_end = int(round((end_dt.timestamp() - start_time) / resolution))
                                idx_end = max(0, min(idx_end, reader.shape[2] - 1))
                                idx_start = max(0, idx_end - int(round((24 * 3600) / resolution)) + 1)
                                print("[debug] meta:")
                                print(f"  temporal_resolution_seconds={meta.get('temporal_resolution_seconds')}")
                                print(f"  data_start_time={meta.get('data_start_time')}")
                                print(f"  data_end_time={meta.get('data_end_time')}")
                                print(f"  scale_factor={meta.get('scale_factor')}")
                                print(f"  add_offset={meta.get('add_offset')}")
                                _debug_candidates(
                                    reader,
                                    float(lat),
                                    float(lon),
                                    idx_start,
                                    idx_end,
                                    axis,
                                )
                        except Exception as exc:
                            print(f"[debug] meta_error={exc}")

                        print(
                            f"[hourly] best_grid_mode={best_mode} best_shift={best_shift}h "
                            f"mae={best_mae:.3f} om_mode={om_mode}"
                        )

                        # Try shifts in hours to see best alignment (for chosen mode)
                        best_shift = 0
                        best_mae = float("inf")
                        for shift in SHIFT_RANGE_HOURS:
                            errors = []
                            for t in om_times:
                                dt_t = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                                shifted = dt_t + timedelta(hours=shift)
                                key = shifted.strftime("%Y-%m-%dT%H:%M")
                                if key in api_map:
                                    ov = om_map.get(t)
                                    av = api_map.get(key)
                                    if np.isfinite(ov) and np.isfinite(av):
                                        errors.append(abs(ov - av))
                            if errors:
                                mae = sum(errors) / len(errors)
                                if mae < best_mae:
                                    best_mae = mae
                                    best_shift = shift

                        # Compute aligned 24h sums/avg using best shift
                        if api_end_idx is not None and api_end_idx >= 23:
                            api_window = api_vals[api_end_idx - 23 : api_end_idx + 1]
                            if agg_mode == "sum":
                                api_24h = sum(api_window)
                            else:
                                api_24h = sum(api_window) / len(api_window)
                        else:
                            api_24h = float("nan")

                        # OM 24h aligned to shifted API window
                        if api_end_idx is not None and api_end_idx >= 23:
                            om_window_vals = []
                            for key in api_times[api_end_idx - 23 : api_end_idx + 1]:
                                dt_k = datetime.strptime(key, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                                om_key = (dt_k - timedelta(hours=best_shift)).strftime("%Y-%m-%dT%H:%M")
                                val = om_map.get(om_key)
                                if val is not None and np.isfinite(val):
                                    om_window_vals.append(val)
                            if om_window_vals:
                                if agg_mode == "sum":
                                    om_24h = float(sum(om_window_vals))
                                else:
                                    om_24h = float(sum(om_window_vals) / len(om_window_vals))
                            else:
                                om_24h = float("nan")
                        else:
                            om_24h = float("nan")

                        print(f"[hourly] api_24h={api_24h} om_24h_aligned={om_24h}")

                        # Show any non-zero API values within the 24h window
                        if api_end_idx is not None and api_end_idx >= 23:
                            window_times = api_times[api_end_idx - 23 : api_end_idx + 1]
                            window_vals = api_vals[api_end_idx - 23 : api_end_idx + 1]
                            nonzero = [
                                (t, v) for t, v in zip(window_times, window_vals) if abs(v) > 0
                            ]
                            print(f"[hourly] api_window_nonzero count={len(nonzero)}")
                            for t, v in nonzero[:10]:
                                print(f"  api {t} -> {v}")

                        # Print the aligned 24h window (API window + shifted OM window)
                        if api_end_idx is not None and api_end_idx >= 23:
                            print("[hourly] 24h window (aligned):")
                            window_keys = api_times[api_end_idx - 23 : api_end_idx + 1]
                            for key in window_keys:
                                dt_k = datetime.strptime(key, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                                om_key = (dt_k - timedelta(hours=best_shift)).strftime("%Y-%m-%dT%H:%M")
                                print(
                                    f"  api {key} -> {api_map.get(key)} | "
                                    f"om {om_key} -> {om_map.get(om_key)}"
                                )

            mode_used = best_mode or "axis_meta"
            grid_mode_set.add(mode_used)
            om_val = _agg_24h_from_omfiles(
                float(lat),
                float(lon),
                dt,
                model=model,
                variable=variable,
                agg_mode=agg_mode,
                grid_mode=best_mode,
            )
            om_val_axis = None
            if best_mode and idx == (indices[0] if indices else 0):
                om_val_axis = _agg_24h_from_omfiles(
                    float(lat),
                    float(lon),
                    dt,
                    model=model,
                    variable=variable,
                    agg_mode=agg_mode,
                )

            diff = om_val - api_val
            if not np.isfinite(om_val):
                var_nan_om += 1
                overall_nan_om += 1
            if not np.isfinite(api_val):
                var_nan_api += 1
                overall_nan_api += 1
            if not np.isfinite(diff):
                extra = ""
                if om_val_axis is not None:
                    extra = f" omfiles_axis={om_val_axis}"
                print(
                    f"row={idx} lat={lat:.6f} lon={lon:.6f} time={dt.isoformat()} "
                    f"omfiles={om_val} api={api_val} diff={diff:.3f} mode={mode_used}{extra} url={url}"
                )
                continue

            abs_diff = abs(diff)
            diffs.append(diff)
            all_diffs.append(diff)
            all_abs.append(abs_diff)
            var_valid += 1
            overall_valid += 1
            if abs_diff <= 0.02:
                pass_count += 1
            top_runs.append((abs_diff, variable, idx, om_val, api_val, mode_used))
            extra = ""
            if om_val_axis is not None:
                extra = f" omfiles_axis={om_val_axis}"
            print(
                f"row={idx} lat={lat:.6f} lon={lon:.6f} time={dt.isoformat()} "
                f"omfiles={om_val} api={api_val} diff={diff:.3f} mode={mode_used}{extra} url={url}"
            )

        if var_valid:
            abs_diffs = [abs(d) for d in diffs]
            mean_diff = sum(diffs) / len(diffs)
            mean_abs = sum(abs_diffs) / len(abs_diffs)
            max_abs = max(abs_diffs)
        else:
            mean_diff = float("nan")
            mean_abs = float("nan")
            max_abs = float("nan")
        print(
            f"summary runs={var_total} valid={var_valid} nan_om={var_nan_om} nan_api={var_nan_api} "
            f"mean_diff={mean_diff:.3f} mean_abs={mean_abs:.3f} max_abs={max_abs:.3f}"
        )
        if best_mode:
            step = 0.1 if model == "copernicus_era5_land" else 0.25
            grid_label = best_mode
        else:
            step = 0.1 if model == "copernicus_era5_land" else 0.25
            grid_label = "axis_meta"
        grid_modes = ",".join(sorted(grid_mode_set)) if grid_mode_set else "none"
        var_summaries.append((variable, model, step, grid_label, var_valid, var_total))
        if len(grid_mode_set) > 1:
            print(f"[warn] grid_mode_inconsistent={grid_modes}")

    if overall_total:
        if overall_valid:
            overall_mean_diff = sum(all_diffs) / len(all_diffs)
            overall_mean_abs = sum(all_abs) / len(all_abs)
            pass_rate = pass_count / overall_valid
        else:
            overall_mean_diff = float("nan")
            overall_mean_abs = float("nan")
            pass_rate = 0.0
        top_runs.sort(key=lambda item: item[0], reverse=True)
        print("\n=== overall_summary ===")
        print(
            "total_runs={total} valid_runs={valid} nan_om={nan_om} nan_api={nan_api} "
            "pass<=0.02={passed} pass_rate={rate:.3f}".format(
                total=overall_total,
                valid=overall_valid,
                nan_om=overall_nan_om,
                nan_api=overall_nan_api,
                passed=pass_count,
                rate=pass_rate,
            )
        )
        print(f"mean_diff={overall_mean_diff:.6f} mean_abs={overall_mean_abs:.6f}")
        print("top_off_runs:")
        for abs_diff, var, row_idx, om_val, api_val, mode_used in top_runs[:5]:
            print(
                f"  abs_diff={abs_diff:.6f} var={var} row={row_idx} "
                f"omfiles={om_val} api={api_val} mode={mode_used}"
            )

    if var_summaries:
        print("\n=== variable_grid_summary ===")
        for variable, model, step, grid_mode, valid, total in var_summaries:
            print(
                f"variable={variable} model={model} step={step} "
                f"grid_mode={grid_mode} valid={valid}/{total}"
            )


if __name__ == "__main__":
    main()
