"""CLI parsing for training observation preprocessing."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pipeline import run_preprocess


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for preprocessing."""
    parser = argparse.ArgumentParser(
        description=(
            "Preprocess occurrence parquet files into training_observation parquet dataset."
        )
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path("/data"),
        help="Root directory containing scattered occurrence parquet files.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/data/training_observation"),
        help="Partitioned output dataset root.",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=None,
        help=(
            "Temporary directory for transformed intermediate parquet shards. "
            "Defaults to a sibling of output-root."
        ),
    )
    parser.add_argument(
        "--glob",
        type=str,
        default="**/occurrence.parquet",
        help="Glob to discover input observation parquet files under input-root.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Optional cap for number of input files to process (0 = no cap).",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=max(2, (os.cpu_count() or 8) // 2),
        help="File-level worker threads.",
    )
    parser.add_argument(
        "--feature-version",
        type=str,
        default="v1",
        help="Feature version string written to output rows.",
    )
    parser.add_argument(
        "--cell-size-deg",
        type=float,
        default=0.25,
        help="Spatial bin size in degrees for derived cell_id.",
    )
    parser.add_argument(
        "--region-size-deg",
        type=float,
        default=10.0,
        help="Coarser spatial bin size in degrees for region_id.",
    )
    parser.add_argument(
        "--max-rows-per-file",
        type=int,
        default=250_000,
        help="Max rows per output parquet file in final partitioned dataset.",
    )
    parser.add_argument(
        "--partition-mode",
        type=str,
        default="split/year_month/region_id",
        choices=["split", "split/year_month", "split/year_month/region_id"],
        help=(
            "Partition columns for final dataset write. "
            "Coarser modes reduce file counts."
        ),
    )
    parser.add_argument(
        "--fallback-time-policy",
        type=str,
        default="keep",
        choices=["keep", "drop"],
        help="How to handle rows with missing/unparseable event time that fall back to 1970-01.",
    )
    parser.add_argument(
        "--background-ratio",
        type=float,
        default=0.0,
        help="Optional unlabeled/background rows to generate per positive row (e.g., 1.0 = 1:1).",
    )
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Delete output and staging directories before writing.",
    )
    parser.add_argument(
        "--keep-staging",
        action="store_true",
        help="Keep staging parquet files after final dataset write.",
    )
    parser.add_argument(
        "--progress-interval-seconds",
        type=float,
        default=30.0,
        help="Emit heartbeat logs every N seconds if no file completes.",
    )
    parser.add_argument(
        "--log-slow-file-seconds",
        type=float,
        default=20.0,
        help="Log completed files that take at least this many seconds.",
    )
    parser.add_argument(
        "--log-slow-read-seconds",
        type=float,
        default=8.0,
        help="Log files whose parquet read step takes at least this many seconds.",
    )
    parser.add_argument(
        "--schema-log-interval-files",
        type=int,
        default=500,
        help="During feature-template schema scan, log progress every N files.",
    )
    parser.add_argument(
        "--template-scan-max-files",
        type=int,
        default=0,
        help="Optional cap for schema files scanned to build feature template (0 = scan all discovered files).",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint for generating training observations dataset."""
    return run_preprocess(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
