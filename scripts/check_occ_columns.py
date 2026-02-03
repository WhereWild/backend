from __future__ import annotations

"""
Scan all occurrence.parquet files under the taxonomy root and report how many
are missing required columns.

Usage:
  python3 scripts/check_occ_columns.py
  python3 scripts/check_occ_columns.py --cols cloud_cover_sum_1h,precipitation_sum_1h
"""

import argparse
from pathlib import Path

import pyarrow.parquet as pq

from util.config import load_config
from util import taxa_navigation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check required columns in occurrence parquets.")
    parser.add_argument(
        "--cols",
        default="cloud_cover_sum_1h,precipitation_sum_1h,snowfall_water_equivalent_sum_1h,weather_code_simple_sum_1h",
        help="Comma-separated list of required columns.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="Max number of example files to list for each missing column set.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    required = tuple(col.strip() for col in args.cols.split(",") if col.strip())
    sample_limit = max(0, args.sample)

    config = load_config("global")
    root = config.root_taxon_id
    root_record = taxa_navigation.get_taxon_by_id(root)
    if root_record is None:
        raise SystemExit(f"Unknown root taxon {root}")

    total = 0
    missing = 0
    samples: list[tuple[Path, tuple[str, ...]]] = []

    for node in taxa_navigation.iter_descendants(root_record, include_self=True):
        path = Path(node["path"]) / config.occurrence_parquet_filename
        if not path.exists():
            continue
        total += 1
        try:
            schema = pq.read_schema(path)
        except Exception:
            missing += 1
            if len(samples) < sample_limit:
                samples.append((path, ("<schema read error>",)))
            continue
        cols = set(schema.names)
        missing_cols = tuple(col for col in required if col not in cols)
        if missing_cols:
            missing += 1
            if len(samples) < sample_limit:
                samples.append((path, missing_cols))

    print(f"total occurrence files: {total}")
    print(f"missing required cols: {missing}")
    if samples:
        print("examples:")
        for path, cols in samples:
            print(f"  {path}: missing {', '.join(cols)}")


if __name__ == "__main__":
    main()
