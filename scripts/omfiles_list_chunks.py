from __future__ import annotations

import json
from datetime import datetime, timezone

import fsspec
from omfiles import OmFileReader
import numpy as np


MODEL = "copernicus_era5"
VARIABLE = "temperature_2m"


def _open_s3_json(uri: str) -> dict | None:
    try:
        with fsspec.open(uri, mode="rb", s3={"anon": True}) as handle:
            return json.loads(handle.read())
    except Exception:
        return None


def _iso(ts: int | float | None) -> str:
    if ts is None:
        return "unknown"
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except Exception:
        return "unknown"

def _parse_meta_time(meta: dict, key: str) -> float | None:
    value = meta.get(key)
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


def _open_s3_json(uri: str) -> dict | None:
    try:
        with fsspec.open(uri, mode="rb", s3={"anon": True}) as handle:
            return json.loads(handle.read())
    except Exception:
        return None


def main() -> None:
    base = f"s3://openmeteo/data/{MODEL}/{VARIABLE}"
    static_meta = _open_s3_json(f"s3://openmeteo/data/{MODEL}/static/meta.json") or {}
    end_time = _parse_meta_time(static_meta, "data_end_time")
    resolution = _parse_meta_time(static_meta, "temporal_resolution_seconds") or 3600.0
    chunk_len = static_meta.get("chunk_time_length")
    if not isinstance(chunk_len, (int, float)):
        chunk_len = None
    fs = fsspec.filesystem("s3", anon=True)
    try:
        listing = fs.ls(base)
    except Exception as exc:
        raise SystemExit(f"Failed to list {base}: {exc}") from exc

    year_files = sorted(name for name in listing if name.split("/")[-1].startswith("year_"))
    chunk_files = sorted(name for name in listing if name.split("/")[-1].startswith("chunk_"))

    print(f"model: {MODEL}")
    print(f"variable: {VARIABLE}")
    print(f"years: {[name.split('/')[-1] for name in year_files]}")
    print(f"chunk_count: {len(chunk_files)}")

    if not chunk_files:
        print("chunk_time_ranges: none")
        return

    print("chunk_time_ranges:")
    if end_time is None or chunk_len is None:
        print("  unknown (missing data_end_time/chunk_time_length in static meta)")
        return
    stitched_start = None
    stitched_end = None
    coverage_gaps = 0
    expected_step = resolution
    last_start = None
    for chunk_path in chunk_files:
        start_time = end_time - (float(chunk_len) - 1) * resolution
        print(f"  {chunk_path.split('/')[-1]}: {_iso(start_time)} -> {_iso(end_time)}")
        if stitched_end is None:
            stitched_end = end_time
            stitched_start = start_time
        else:
            stitched_start = start_time
            if last_start is not None:
                gap = last_start - end_time - expected_step
                if gap > 0:
                    coverage_gaps += 1
        end_time = start_time - resolution
        last_start = start_time
    if stitched_start is not None and stitched_end is not None:
        print("chunk_coverage:")
        print(f"  start: {_iso(stitched_start)}")
        print(f"  end: {_iso(stitched_end)}")
        print(f"  gaps_detected: {coverage_gaps}")
        if year_files:
            last_year = sorted(year_files)[-1].split("/")[-1]
            try:
                last_year_num = int(last_year.replace("year_", "").replace(".om", ""))
            except ValueError:
                last_year_num = None
            if last_year_num is not None:
                year_start = datetime(last_year_num, 1, 1, tzinfo=timezone.utc).timestamp()
                year_end = datetime(last_year_num, 12, 31, 23, tzinfo=timezone.utc).timestamp()
                combined_start = datetime(1940, 1, 1, tzinfo=timezone.utc).timestamp()
                combined_end = stitched_end
                overlap = year_end >= stitched_start
                print("combined_coverage:")
                print(f"  start: {_iso(combined_start)}")
                print(f"  end: {_iso(combined_end)}")
                print(f"  last_year_file: {last_year}")
                print(f"  last_year_range: {_iso(year_start)} -> {_iso(year_end)}")
                print(f"  chunk_start: {_iso(stitched_start)}")
                print(f"  overlap_with_last_year: {overlap}")


if __name__ == "__main__":
    main()
