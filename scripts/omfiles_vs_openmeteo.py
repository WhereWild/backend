from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import numpy as np
import pyarrow.parquet as pq

import fsspec
from omfiles import OmFileReader

PARQUET_PATH = Path(
    "/workspace/data/species/taxonomy/Animalia_1/Chordata_44/"
    "Amphibia_131/Anura_952/Scaphiopodidae_3098/Spea_2429782/"
    "Spea_intermontana_2429791/occurrence.parquet"
)
LAT_COL = "decimalLatitude"
LON_COL = "decimalLongitude"
TIME_COL = "eventTimestamp"

MODEL = "copernicus_era5"
VARIABLE = "precipitation"
ROW_INDICES = [2]


def _to_datetime_utc(ts_value: float) -> datetime:
    ts = float(ts_value)
    if ts > 1e12:
        ts /= 1e9
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _fetch_openmeteo_precip_24h(lat: float, lon: float, dt: datetime) -> tuple[float, str]:
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
        "&hourly=precipitation"
        "&elevation=nan"
        "&timezone=UTC"
    )
    with urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    vals = hourly.get("precipitation") or []
    if not times or not vals:
        raise RuntimeError("Open-Meteo returned no hourly precipitation")

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
        raise RuntimeError("Unexpected hourly window size for 24h sum")
    return float(sum(window)), url


def _fetch_openmeteo_hourly(
    lat: float, lon: float, start_dt: datetime, end_dt: datetime
) -> tuple[list[str], list[float], str]:
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat:.6f}"
        f"&longitude={lon:.6f}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        "&hourly=precipitation"
        "&elevation=nan"
        "&timezone=UTC"
    )
    with urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    vals = hourly.get("precipitation") or []
    if not times or not vals:
        raise RuntimeError("Open-Meteo returned no hourly precipitation")
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


def _precip_24h_from_omfiles(lat: float, lon: float, dt: datetime) -> float:
    year = dt.year
    with _open_om_reader(MODEL, VARIABLE, year) as reader:
        ny, nx, time_len = reader.shape
        step = 0.1 if (ny in (1801, 1800) and nx in (3600, 3601)) else 0.25
        lat_idx = None
        lon_idx = None
        for li, lo in _grid_index_candidates(lat, lon, ny, nx, step):
            if not _is_nan(reader[li, lo, 0]):
                lat_idx, lon_idx = li, lo
                break
        if lat_idx is None or lon_idx is None:
            lat_idx, lon_idx = _grid_index_candidates(lat, lon, ny, nx, step)[0]

        resolution = 3600.0
        meta = getattr(reader, "meta", None) or getattr(reader, "metadata", None) or {}
        if isinstance(meta, dict):
            value = meta.get("temporal_resolution_seconds")
            if isinstance(value, (int, float)):
                resolution = float(value)

        start_time = datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()
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
        return float(series.sum())


def _omfiles_hourly_series(
    lat: float, lon: float, start_dt: datetime, end_dt: datetime
) -> tuple[list[str], list[float], str]:
    year = start_dt.year
    with _open_om_reader(MODEL, VARIABLE, year) as reader:
        ny, nx, time_len = reader.shape
        step = 0.1 if (ny in (1801, 1800) and nx in (3600, 3601)) else 0.25
        candidates = _grid_index_candidates(lat, lon, ny, nx, step)

        resolution = 3600.0
        meta = getattr(reader, "meta", None) or getattr(reader, "metadata", None) or {}
        if isinstance(meta, dict):
            value = meta.get("temporal_resolution_seconds")
            if isinstance(value, (int, float)):
                resolution = float(value)

        start_time = datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()
        start_ts = start_dt.timestamp()
        end_ts = end_dt.timestamp()
        idx_start = int(round((start_ts - start_time) / resolution))
        idx_end = int(round((end_ts - start_time) / resolution))
        idx_start = max(0, min(idx_start, time_len - 1))
        idx_end = max(0, min(idx_end, time_len - 1))
        if idx_end < idx_start:
            idx_start, idx_end = idx_end, idx_start

        best_vals = None
        best_mode = "unknown"
        for mode_idx, (li, lo) in enumerate(candidates):
            series = np.array(
                [reader[li, lo, idx] for idx in range(idx_start, idx_end + 1)],
                dtype=float,
            )
            # Prefer a candidate with more finite values
            finite = np.isfinite(series)
            if best_vals is None or finite.sum() > np.isfinite(best_vals).sum():
                best_vals = series
                best_mode = str(mode_idx)

        times = []
        vals = []
        for offset, idx in enumerate(range(idx_start, idx_end + 1)):
            ts = start_time + idx * resolution
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            times.append(dt.strftime("%Y-%m-%dT%H:%M"))
            vals.append(float(best_vals[offset]))

        return times, vals, best_mode


def main() -> None:
    if not PARQUET_PATH.exists():
        raise SystemExit(f"Missing parquet: {PARQUET_PATH}")

    table = pq.read_table(PARQUET_PATH, columns=[LAT_COL, LON_COL, TIME_COL]).combine_chunks()
    if table.num_rows == 0:
        raise SystemExit("Parquet has no rows")

    if ROW_INDICES:
        indices = [i for i in ROW_INDICES if 0 <= i < table.num_rows]
    else:
        indices = list(range(min(3, table.num_rows)))
    diffs: list[float] = []
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
            api_val, url = _fetch_openmeteo_precip_24h(float(lat), float(lon), dt)
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            print(f"row={idx} api_error={exc}")
            continue

        om_val = _precip_24h_from_omfiles(float(lat), float(lon), dt)
        diff = om_val - api_val
        diffs.append(diff)
        print(
            f"row={idx} lat={lat:.6f} lon={lon:.6f} time={dt.isoformat()} "
            f"omfiles={om_val} api={api_val} diff={diff:.3f} url={url}"
        )

        # Detailed hourly comparison for first row only
        if idx == (indices[0] if indices else 0):
            end_dt = dt.replace(minute=0, second=0, microsecond=0)
            start_dt = end_dt - timedelta(hours=47)
            try:
                api_times, api_vals, api_url = _fetch_openmeteo_hourly(
                    float(lat), float(lon), start_dt, end_dt
                )
            except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
                print(f"[hourly] api_error={exc}")
                continue

            om_times, om_vals, om_mode = _omfiles_hourly_series(
                float(lat), float(lon), start_dt, end_dt
            )

            # Build lookup for API values
            api_map = {t: v for t, v in zip(api_times, api_vals)}
            om_map = {t: v for t, v in zip(om_times, om_vals)}

            # Try shifts in hours to see best alignment
            shifts = range(-2, 3)
            best_shift = 0
            best_mae = float("inf")
            for shift in shifts:
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

            print(f"[hourly] best_shift={best_shift}h mae={best_mae:.3f} om_mode={om_mode}")

            # Compute aligned 24h sums using best shift
            end_key = end_dt.strftime("%Y-%m-%dT%H:%M")
            try:
                api_end_idx = api_times.index(end_key)
            except ValueError:
                api_end_idx = None
            if api_end_idx is not None and api_end_idx >= 23:
                api_24h = sum(api_vals[api_end_idx - 23 : api_end_idx + 1])
            else:
                api_24h = float("nan")

            # OM 24h sum aligned to shifted API window
            if api_end_idx is not None and api_end_idx >= 23:
                start_key = api_times[api_end_idx - 23]
                end_key = api_times[api_end_idx]
                # Map API window timestamps back to OM timestamps by inverse shift
                om_window_vals = []
                for key in api_times[api_end_idx - 23 : api_end_idx + 1]:
                    dt_k = datetime.strptime(key, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                    om_key = (dt_k - timedelta(hours=best_shift)).strftime("%Y-%m-%dT%H:%M")
                    val = om_map.get(om_key)
                    if val is not None and np.isfinite(val):
                        om_window_vals.append(val)
                om_24h = float(sum(om_window_vals)) if om_window_vals else float("nan")
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

    if diffs:
        abs_diffs = [abs(d) for d in diffs]
        mean_diff = sum(diffs) / len(diffs)
        mean_abs = sum(abs_diffs) / len(abs_diffs)
        max_abs = max(abs_diffs)
        print(
            f"summary rows={len(diffs)} mean_diff={mean_diff:.3f} "
            f"mean_abs={mean_abs:.3f} max_abs={max_abs:.3f}"
        )


if __name__ == "__main__":
    main()
