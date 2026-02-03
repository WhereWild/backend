from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Tuple

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import fsspec
from omfiles import OmFileReader


MODEL = "copernicus_era5"
INPUT_PARQUET = "/workspace/occurrence.parquet"
OUTPUT_PARQUET = "/workspace/occurrence.parquet.om_sample.parquet"
CACHE_DIR = "/tmp/om_cache"

VARIABLES = [
    "cloud_cover",
    "dew_point_2m",
    "precipitation",
    "snowfall_water_equivalent",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_temperature_0_to_7cm",
    "soil_temperature_7_to_28cm",
    "temperature_2m",
]

TIME_COL = "eventTimestamp"
LAT_COL = "decimalLatitude"
LON_COL = "decimalLongitude"
CATALOG_COL = "catalogNumber"

ACCUM_VARS = {"precipitation", "snowfall_water_equivalent"}
WINDOW_CONFIG: dict[str, dict[str, list[int]]] = {
    "precipitation": {"sum": [24, 72]},
    "snowfall_water_equivalent": {"sum": [24, 72]},
    "soil_moisture_0_to_7cm": {"avg": [24]},
    "soil_moisture_7_to_28cm": {"avg": [24]},
    "soil_temperature_0_to_7cm": {"avg": [24]},
    "soil_temperature_7_to_28cm": {"avg": [24]},
    "cloud_cover": {"avg": [24]},
    "temperature_2m": {"avg": [24, 72]},
}


@dataclass
class ChunkIndex:
    latest_end_time: float
    resolution: float
    max_chunk: int
    min_chunk: int
    available_chunks: frozenset[int]
    ranges: list[tuple[int, float, float]]


def _open_s3_json(uri: str) -> dict[str, Any] | None:
    try:
        with fsspec.open(uri, mode="rb", s3={"anon": True}) as handle:
            return json.loads(handle.read())
    except Exception:
        return None


def _parse_time(value: Any) -> float | None:
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


def _open_reader(uri: str) -> OmFileReader:
    backend = fsspec.open(
        f"blockcache::{uri}",
        mode="rb",
        s3={"anon": True, "default_block_size": 65536},
        blockcache={"cache_storage": CACHE_DIR},
    )
    return OmFileReader(backend)


def _year_start(year: int) -> float:
    return datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()


def _year_end(year: int) -> float:
    return datetime(year, 12, 31, 23, tzinfo=timezone.utc).timestamp()


def _grid_indices(lat: float, lon: float, ny: int, nx: int, mode: str) -> Tuple[int, int]:
    if mode == "lat_asc_lon_360":
        lat_idx = int(round((lat + 90.0) / 0.25))
        lon_idx = int(round((lon % 360.0) / 0.25))
    elif mode == "lat_asc_lon_pm180":
        lat_idx = int(round((lat + 90.0) / 0.25))
        lon_idx = int(round((lon + 180.0) / 0.25))
    elif mode == "lat_desc_lon_360":
        lat_idx = int(round((90.0 - lat) / 0.25))
        lon_idx = int(round((lon % 360.0) / 0.25))
    else:
        lat_idx = int(round((90.0 - lat) / 0.25))
        lon_idx = int(round((lon + 180.0) / 0.25))
    lat_idx = max(0, min(lat_idx, ny - 1))
    lon_idx = max(0, min(lon_idx, nx - 1))
    return lat_idx, lon_idx


def _resolve_grid_mode(reader: OmFileReader) -> str:
    ny, nx, _ = reader.shape
    if ny == 721 and nx == 1440:
        # Try all 4 modes on a stable land point and choose non-NaN
        test_lat = 40.8
        test_lon = -111.9
        modes = (
            "lat_asc_lon_pm180",
            "lat_asc_lon_360",
            "lat_desc_lon_pm180",
            "lat_desc_lon_360",
        )
        for mode in modes:
            li, lo = _grid_indices(test_lat, test_lon, ny, nx, mode)
            try:
                value = reader[li, lo, 0]
            except Exception:
                continue
            try:
                if not np.isnan(value):
                    return mode
            except Exception:
                return mode
        return "lat_asc_lon_pm180"
    return "lat_asc_lon_pm180"


def _build_chunk_index(model: str, variable: str) -> ChunkIndex:
    static_meta_uri = f"s3://openmeteo/data/{model}/static/meta.json"
    static_meta = _open_s3_json(static_meta_uri) or {}
    end_time = _parse_time(static_meta.get("data_end_time"))
    resolution = _parse_time(static_meta.get("temporal_resolution_seconds")) or 3600.0
    if end_time is None:
        raise RuntimeError("Missing chunk metadata in static/meta.json")

    fs = fsspec.filesystem("s3", anon=True)
    base = f"s3://openmeteo/data/{model}/{variable}"
    listing = fs.ls(base)
    chunk_nums = []
    for item in listing:
        name = item.get("name") if isinstance(item, dict) else item
        if not isinstance(name, str):
            continue
        leaf = name.split("/")[-1]
        if leaf.startswith("chunk_") and leaf.endswith(".om"):
            try:
                chunk_nums.append(int(leaf.replace("chunk_", "").replace(".om", "")))
            except ValueError:
                continue
    if not chunk_nums:
        raise RuntimeError("No chunk files found for model/variable")
    chunk_nums = sorted(chunk_nums, reverse=True)
    ranges: list[tuple[int, float, float]] = []
    running_end = float(end_time)
    for chunk_num in chunk_nums:
        data_uri = f"s3://openmeteo/data/{model}/{variable}/chunk_{chunk_num}.om"
        reader = _open_reader(data_uri)
        try:
            time_len = reader.shape[2]
        finally:
            reader.close()
        start = running_end - (time_len - 1) * resolution
        ranges.append((chunk_num, start, running_end))
        running_end = start - resolution

    return ChunkIndex(
        latest_end_time=float(end_time),
        resolution=float(resolution),
        max_chunk=max(chunk_nums),
        min_chunk=min(chunk_nums),
        available_chunks=frozenset(chunk_nums),
        ranges=ranges,
    )


def _chunk_for_timestamp(ts: float, index: ChunkIndex) -> Tuple[int, float]:
    if ts > index.latest_end_time:
        return index.max_chunk, index.latest_end_time
    for chunk_num, start, end in index.ranges:
        if start <= ts <= end:
            return chunk_num, end
    # Fallback to nearest older chunk
    last = index.ranges[-1]
    return last[0], last[2]


def _sample_value(
    reader: OmFileReader,
    lat_idx: int,
    lon_idx: int,
    time_idx: int,
) -> float | None:
    try:
        value = reader[lat_idx, lon_idx, time_idx]
    except Exception:
        return None
    try:
        if np.isnan(value):
            return None
    except Exception:
        pass
    return float(value)


def _weather_code_simple(
    cloudcover: float,
    precipitation: float,
    snowfall_water_equivalent: float,
    model_dt_seconds: int,
) -> int | None:
    if not np.isfinite(cloudcover) or not np.isfinite(precipitation) or not np.isfinite(snowfall_water_equivalent):
        return None
    model_dt_hours = model_dt_seconds / 3600.0
    snowfall_cm = snowfall_water_equivalent / 10.0

    rate_snow = snowfall_cm / model_dt_hours
    if 0.01 <= rate_snow < 0.2:
        return 71
    if 0.2 <= rate_snow < 0.8:
        return 73
    if rate_snow >= 0.8:
        return 75

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

    if cloudcover < 20:
        return 0
    if cloudcover < 50:
        return 1
    if cloudcover < 80:
        return 2
    return 3


def main() -> None:
    chunk_index_cache: Dict[str, ChunkIndex] = {}
    reader_cache: Dict[Tuple[str, str], Tuple[OmFileReader, str]] = {}

    pf = pq.ParquetFile(INPUT_PARQUET)
    writer: pq.ParquetWriter | None = None

    for row_group in range(pf.num_row_groups):
        print(f"[row_group {row_group+1}/{pf.num_row_groups}]")
        table = pf.read_row_group(
            row_group,
            columns=[CATALOG_COL, LAT_COL, LON_COL, TIME_COL],
        ).combine_chunks()
        lats = table[LAT_COL].to_pylist()
        lons = table[LON_COL].to_pylist()
        times = table[TIME_COL].to_pylist()

        out_cols: Dict[str, list[float | None]] = {}
        for var in VARIABLES:
            out_cols[var] = [None] * len(lats)
            for agg, windows in WINDOW_CONFIG.get(var, {}).items():
                for hours in windows:
                    out_cols[f"{var}_{agg}_{hours}h"] = [None] * len(lats)
        out_cols["weather_code_simple"] = [None] * len(lats)

        # Precompute row info and group by (year/chunk)
        row_info: list[tuple[int, float, float, float, int | None]] = []
        for idx, (lat, lon, ts) in enumerate(zip(lats, lons, times)):
            if lat is None or lon is None or ts is None:
                row_info.append((idx, 0.0, 0.0, 0.0, None))
                continue
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                ts_f = float(ts)
            except (TypeError, ValueError):
                row_info.append((idx, 0.0, 0.0, 0.0, None))
                continue
            year = datetime.fromtimestamp(ts_f, tz=timezone.utc).year
            if year <= 2021:
                row_info.append((idx, lat_f, lon_f, ts_f, year))
            else:
                row_info.append((idx, lat_f, lon_f, ts_f, None))

        # For each variable, process rows in grouped order to reuse readers
        for var in VARIABLES:
            print(f"  [var] {var}")
            # Group by data file key
            if var not in chunk_index_cache:
                chunk_index_cache[var] = _build_chunk_index(MODEL, var)
            chunk_index = chunk_index_cache[var]

            groups: Dict[Tuple[str, int], list[tuple[int, float, float, float]]] = {}
            for idx, lat_f, lon_f, ts_f, year in row_info:
                if year is not None:
                    key = ("year", year)
                    groups.setdefault(key, []).append((idx, lat_f, lon_f, ts_f))
                else:
                    chunk_num, _ = _chunk_for_timestamp(ts_f, chunk_index)
                    key = ("chunk", chunk_num)
                    groups.setdefault(key, []).append((idx, lat_f, lon_f, ts_f))

            for (kind, ident), rows in groups.items():
                print(f"    [group] {kind}_{ident} rows={len(rows)}")
                if kind == "year":
                    data_uri = f"s3://openmeteo/data/{MODEL}/{var}/year_{ident}.om"
                    end_time = None
                else:
                    data_uri = f"s3://openmeteo/data/{MODEL}/{var}/chunk_{ident}.om"
                    end_time = None

                reader_key = (var, f"{kind}_{ident}")
                if reader_key not in reader_cache:
                    try:
                        reader = _open_reader(data_uri)
                    except FileNotFoundError:
                        print(f"    [warn] missing file: {data_uri}")
                        continue
                    grid_mode = _resolve_grid_mode(reader)
                    reader_cache[reader_key] = (reader, grid_mode)

                if reader_key not in reader_cache:
                    continue
                reader, grid_mode = reader_cache[reader_key]
                ny, nx, time_len = reader.shape
                if kind == "year":
                    start_time = _year_start(ident)
                else:
                    # locate range for this chunk
                    end_time = None
                    for chunk_num, start, end in chunk_index.ranges:
                        if chunk_num == ident:
                            end_time = end
                            break
                    if end_time is None:
                        continue
                    start_time = end_time - (time_len - 1) * chunk_index.resolution

                for idx, lat_f, lon_f, ts_f in rows:
                    if lat_f == 0.0 and lon_f == 0.0 and ts_f == 0.0:
                        continue
                    lat_idx, lon_idx = _grid_indices(lat_f, lon_f, ny, nx, grid_mode)
                    time_idx = int(round((ts_f - start_time) / chunk_index.resolution))
                    time_idx = max(0, min(time_idx, time_len - 1))
                    out_cols[var][idx] = _sample_value(reader, lat_idx, lon_idx, time_idx)
                    # Windowed aggregates (single slice per row)
                    agg_spec = WINDOW_CONFIG.get(var)
                    if agg_spec:
                        max_hours = max(h for hours in agg_spec.values() for h in hours)
                        max_len = int(round((max_hours * 3600) / chunk_index.resolution))
                        slice_start = max(0, time_idx - max_len + 1)
                        series = [
                            _sample_value(reader, lat_idx, lon_idx, i)
                            for i in range(slice_start, time_idx + 1)
                        ]
                        series = np.array([v for v in series if v is not None], dtype=float)
                        if series.size:
                            for agg, windows in agg_spec.items():
                                for hours in windows:
                                    win_len = int(round((hours * 3600) / chunk_index.resolution))
                                    window = series[-win_len:]
                                    if window.size == 0:
                                        out_cols[f"{var}_{agg}_{hours}h"][idx] = None
                                    elif agg == "sum":
                                        out_cols[f"{var}_{agg}_{hours}h"][idx] = float(window.sum())
                                    else:
                                        out_cols[f"{var}_{agg}_{hours}h"][idx] = float(window.mean())

        # Compute simplified weather code from 1h window values
        for i in range(len(lats)):
            cloud = out_cols["cloud_cover"][i]
            precip = out_cols["precipitation"][i]
            snow = out_cols["snowfall_water_equivalent"][i]
            if cloud is None or precip is None or snow is None:
                out_cols["weather_code_simple"][i] = None
            else:
                out_cols["weather_code_simple"][i] = _weather_code_simple(
                    float(cloud), float(precip), float(snow), 3600
                )

        out_table = table
        for var, values in out_cols.items():
            out_table = out_table.append_column(var, pa.array(values, type=pa.float32()))

        if writer is None:
            writer = pq.ParquetWriter(OUTPUT_PARQUET, out_table.schema)
        writer.write_table(out_table)

    if writer is not None:
        writer.close()


if __name__ == "__main__":
    main()
