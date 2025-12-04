import argparse
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

API_BASE = "https://api.inaturalist.org/v1/observations"
USER_AGENT = "WhereWild-quality-grade-script"
MAX_BATCH = 200  # API limit for id batching
REQUEST_DELAY = 0.5  # seconds between requests to be gentle
DEFAULT_PARQUET_DIR = (
    Path(__file__).resolve().parents[1] / "processed" / "species" / "parquet"
)


def chunked(iterable, size):
    for idx in range(0, len(iterable), size):
        yield iterable[idx : idx + size]


def fetch_quality_grades(ids):
    if not ids:
        return {}

    params = urllib.parse.urlencode([("id", str(obs_id)) for obs_id in ids])
    url = f"{API_BASE}?{params}&per_page={len(ids)}&fields=id,quality_grade"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"Failed to fetch quality grades: {err}") from err

    results = payload.get("results") or []
    grades = {}
    for entry in results:
        obs_id = entry.get("id")
        grade = entry.get("quality_grade")
        if obs_id is None:
            continue
        grades[int(obs_id)] = grade
    return grades


def annotate_parquet(source_path: Path) -> None:
    schema = pq.read_schema(source_path)
    if "quality_grade" in schema.names:
        print(f"[SKIP] {source_path.name} already has quality_grade column.")
        return

    table = pq.read_table(source_path)
    if "id" not in table.column_names:
        print(f"[WARN] {source_path.name} missing 'id' column; skipping.")
        return

    ids = table["id"].to_pylist()
    id_list = [int(obs_id) for obs_id in ids]
    quality_by_id = {}

    total_batches = max(1, math.ceil(len(id_list) / MAX_BATCH))
    for batch_index, batch in enumerate(chunked(id_list, MAX_BATCH), start=1):
        print(f"[{source_path.name}] Batch {batch_index}/{total_batches} ({len(batch)} IDs)")
        grades = fetch_quality_grades(batch)
        quality_by_id.update(grades)
        time.sleep(REQUEST_DELAY)

    quality_values = [quality_by_id.get(obs_id) for obs_id in id_list]
    new_column = pa.array(quality_values, type=pa.string())
    updated = table.append_column("quality_grade", new_column)
    pq.write_table(updated, source_path)
    print(f"[DONE] Annotated {source_path.name}")


def resolve_targets(paths):
    if paths:
        return [Path(p).resolve() for p in paths]

    if not DEFAULT_PARQUET_DIR.exists():
        raise SystemExit(f"Default parquet directory not found: {DEFAULT_PARQUET_DIR}")

    return sorted(DEFAULT_PARQUET_DIR.glob("*.parquet"))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Append iNaturalist quality grade info to species parquets."
    )
    parser.add_argument(
        "parquets",
        nargs="*",
        help="Optional parquet files to annotate. If omitted, annotates every file under processed/species/parquet.",
    )
    args = parser.parse_args(argv)

    targets = resolve_targets(args.parquets)
    if not targets:
        print("No parquet files found.")
        return

    for parquet_path in targets:
        if not parquet_path.exists():
            print(f"[WARN] File not found, skipping: {parquet_path}")
            continue
        annotate_parquet(parquet_path)


if __name__ == "__main__":
    main()
