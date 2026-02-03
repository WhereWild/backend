from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import fsspec
import pyarrow.parquet as pq


MODEL = "copernicus_era5"
VARIABLE = "temperature_2m"
TARGET_CHUNK = 939

INPUT_PARQUET = "/workspace/occurrence.parquet"
TIME_COL = "eventTimestamp"
LAT_COL = "decimalLatitude"
LON_COL = "decimalLongitude"


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


def _build_chunk_index(model: str, variable: str) -> tuple[float, float, int, int, int]:
    static_meta_uri = f"s3://openmeteo/data/{model}/static/meta.json"
    static_meta = _open_s3_json(static_meta_uri) or {}
    end_time = _parse_time(static_meta.get("data_end_time"))
    resolution = _parse_time(static_meta.get("temporal_resolution_seconds")) or 3600.0
    chunk_len = static_meta.get("chunk_time_length")
    if end_time is None or not isinstance(chunk_len, (int, float)):
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
    return float(end_time), float(resolution), int(chunk_len), max(chunk_nums), min(chunk_nums)


def _chunk_for_timestamp(
    ts: float,
    latest_end_time: float,
    resolution: float,
    chunk_len: int,
    max_chunk: int,
    min_chunk: int,
) -> int:
    chunk_span = chunk_len * resolution
    if ts > latest_end_time:
        return max_chunk
    offset = int((latest_end_time - ts) // chunk_span)
    chunk_num = max_chunk - offset
    if chunk_num < min_chunk:
        chunk_num = min_chunk
    end_time = latest_end_time - (max_chunk - chunk_num) * chunk_span
    start_time = end_time - (chunk_len - 1) * resolution
    if ts < start_time and chunk_num > min_chunk:
        chunk_num -= 1
    return chunk_num


def main() -> None:
    latest_end_time, resolution, chunk_len, max_chunk, min_chunk = _build_chunk_index(
        MODEL, VARIABLE
    )
    pf = pq.ParquetFile(INPUT_PARQUET)
    total = 0
    matched = 0

    for row_group in range(pf.num_row_groups):
        table = pf.read_row_group(row_group, columns=[LAT_COL, LON_COL, TIME_COL]).combine_chunks()
        lats = table[LAT_COL].to_pylist()
        lons = table[LON_COL].to_pylist()
        times = table[TIME_COL].to_pylist()

        for lat, lon, ts in zip(lats, lons, times):
            total += 1
            if lat is None or lon is None or ts is None:
                continue
            try:
                ts_f = float(ts)
            except (TypeError, ValueError):
                continue
            chunk_num = _chunk_for_timestamp(
                ts_f,
                latest_end_time,
                resolution,
                chunk_len,
                max_chunk,
                min_chunk,
            )
            if chunk_num == TARGET_CHUNK:
                matched += 1
                iso = datetime.fromtimestamp(ts_f, tz=timezone.utc).isoformat()
                print(f"lat={lat} lon={lon} ts={ts_f} iso={iso}")

    print(f"matched: {matched} / {total}")


if __name__ == "__main__":
    main()
