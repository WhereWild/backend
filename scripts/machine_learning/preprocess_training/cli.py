"""CLI parsing for training observation preprocessing."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .pipeline import run_preprocess
except ImportError:
    from pipeline import run_preprocess  # type: ignore[no-redef]


DEFAULT_PREPROCESS_THREADS = 8
DEFAULT_MAX_ROWS_PER_FILE = 150_000
DEFAULT_BACKGROUND_SPLIT_CHUNK_ROWS = 250_000


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for preprocessing."""
    parser = argparse.ArgumentParser(
        description=("Preprocess occurrence parquet files into training_observation parquet dataset.")
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
        default=Path("/data_ml/training_observation"),
        help="Partitioned output dataset root.",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=None,
        help=("Temporary directory for transformed intermediate parquet shards. Defaults to a sibling of output-root."),
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
        default=DEFAULT_PREPROCESS_THREADS,
        help="File-level worker threads.",
    )
    parser.add_argument(
        "--feature-version",
        type=str,
        default="v1",
        help="Feature version string written to output rows.",
    )
    parser.add_argument(
        "--max-rows-per-file",
        type=int,
        default=DEFAULT_MAX_ROWS_PER_FILE,
        help="Max rows per output parquet file in final partitioned dataset.",
    )
    parser.add_argument(
        "--drop-missing-time",
        action="store_true",
        help="Drop rows with missing/unparseable event time instead of keeping fallback 1970-01 timestamps.",
    )
    parser.add_argument(
        "--background-ratio",
        type=float,
        default=1.0,
        help=(
            "Unlabeled/background rows to generate per positive row (default 1.0 = 1:1), "
            "sampled from other-species rows within the same split."
        ),
    )
    parser.add_argument(
        "--background-split-chunk-rows",
        type=int,
        default=DEFAULT_BACKGROUND_SPLIT_CHUNK_ROWS,
        help=(
            "Row cap per split chunk during pooled background generation. "
            "Lower values reduce peak memory usage on very large datasets."
        ),
    )
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Delete the staging directory before writing and replace the output dataset only after the new write succeeds.",
    )
    parser.add_argument(
        "--keep-staging",
        action="store_true",
        help="Keep staging parquet files after final dataset write.",
    )
    parser.add_argument(
        "--template-scan-max-files",
        type=int,
        default=0,
        help="Optional cap for schema files scanned to build feature template (0 = scan all discovered files).",
    )
    parser.add_argument(
        "--warn-min-cells-per-species",
        type=int,
        default=3,
        help="Warn when a species has fewer than this many unique cells in a transformed shard (0 = disabled).",
    )
    parser.add_argument(
        "--static-context-template",
        type=str,
        default="",
        help=(
            "Optional template to resolve per-source static context parquet path. "
            "Supports {src_dir}, {src_stem}, {src_name}, {src_parent}."
        ),
    )
    parser.add_argument(
        "--static-context-path",
        type=Path,
        default=None,
        help="Optional fixed static context parquet path joined by cell_id.",
    )
    parser.add_argument(
        "--static-context-required",
        action="store_true",
        help="Fail file transform when static context path is configured but missing/unusable.",
    )
    parser.add_argument(
        "--temporal-context-template",
        type=str,
        default="",
        help=(
            "Optional template to resolve per-source temporal context parquet path. "
            "Supports {src_dir}, {src_stem}, {src_name}, {src_parent}."
        ),
    )
    parser.add_argument(
        "--temporal-context-path",
        type=Path,
        default=None,
        help="Optional fixed temporal context parquet path joined by cell_id+year_month.",
    )
    parser.add_argument(
        "--temporal-context-required",
        action="store_true",
        help="Fail file transform when temporal context path is configured but missing/unusable.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint for generating training observations dataset."""
    return run_preprocess(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
