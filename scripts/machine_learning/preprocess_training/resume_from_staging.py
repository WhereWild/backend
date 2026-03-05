"""Resume preprocessing from existing staging shards.

This utility is intended for runs where per-file transforms completed but the
pipeline stopped during pooled background generation or final dataset write.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds

try:
    from .pipeline import (
        FINAL_WRITE_USE_THREADS,
        PROGRESS_INTERVAL_SECONDS,
        clear_dir,
        generate_pooled_background_shards,
        start_phase_heartbeat,
    )
except ImportError:
    from pipeline import (  # type: ignore[no-redef]
        FINAL_WRITE_USE_THREADS,
        PROGRESS_INTERVAL_SECONDS,
        clear_dir,
        generate_pooled_background_shards,
        start_phase_heartbeat,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resume preprocessing from staging shards (background + final write only)."
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        required=True,
        help="Directory containing transformed staging parquet shards.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Final partitioned output dataset root.",
    )
    parser.add_argument(
        "--partition-mode",
        type=str,
        default="split/year_month/region_id",
        choices=["split", "split/year_month", "split/year_month/region_id"],
        help="Partition columns for final dataset write.",
    )
    parser.add_argument(
        "--background-ratio",
        type=float,
        default=1.0,
        help="Unlabeled/background rows to generate per positive row.",
    )
    parser.add_argument(
        "--background-split-chunk-rows",
        type=int,
        default=2_000_000,
        help="Row cap per split chunk during pooled background generation.",
    )
    parser.add_argument(
        "--max-rows-per-file",
        type=int,
        default=250_000,
        help="Max rows per output parquet file in final dataset.",
    )
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Delete output directory before final write.",
    )
    parser.add_argument(
        "--regenerate-background",
        action="store_true",
        help="Delete existing background_pooled_*.parquet files and regenerate them.",
    )
    return parser.parse_args()


def _list_staging_paths(staging_dir: Path) -> tuple[list[Path], list[Path]]:
    # Base shards come from per-file transforms; background shards are optional
    # synthetic PU rows generated after transforms complete.
    all_paths = sorted(path for path in staging_dir.glob("*.parquet") if path.is_file())
    base_paths = [path for path in all_paths if not path.name.startswith("background_pooled_")]
    background_paths = [path for path in all_paths if path.name.startswith("background_pooled_")]
    return base_paths, background_paths


def main() -> int:
    args = _parse_args()

    staging_dir = args.staging_dir.resolve()
    output_root = args.output_root.resolve()

    if not staging_dir.exists():
        raise SystemExit(f"Staging dir does not exist: {staging_dir}")

    base_paths, existing_background_paths = _list_staging_paths(staging_dir)
    if not base_paths:
        raise SystemExit(f"No base staging parquet shards found in: {staging_dir}")

    if args.regenerate_background and existing_background_paths:
        # Allow deterministic rebuilds when previous background generation was
        # interrupted or when PU parameters have changed.
        for path in existing_background_paths:
            path.unlink(missing_ok=True)
        existing_background_paths = []

    print(f"Staging dir: {staging_dir}")
    print(f"Output dir: {output_root}")
    print(f"Base shards: {len(base_paths):,}")
    print(f"Existing background shards: {len(existing_background_paths):,}")
    print(f"Background ratio: {args.background_ratio:.3f}")
    print(f"Background split chunk rows: {args.background_split_chunk_rows:,}")
    print(f"Partition mode: {args.partition_mode}")

    # Reuse existing background shards when present to avoid recomputing the
    # expensive pooled-sampling step on large staging directories.
    background_paths = existing_background_paths
    if args.background_ratio > 0.0 and not background_paths:
        print("Generating pooled unlabeled/background rows from staging shards...")
        background_paths, generated_background_rows = generate_pooled_background_shards(
            base_paths,
            staging_dir=staging_dir,
            background_ratio=args.background_ratio,
            split_chunk_rows=args.background_split_chunk_rows,
        )
        print(
            f"Background generation complete | rows: {generated_background_rows:,} | "
            f"shards: {len(background_paths):,}"
        )

    # Final write always includes transformed base shards plus any generated
    # background shards.
    final_paths = [*base_paths, *background_paths]
    if not final_paths:
        raise SystemExit("No staging shards available for final write.")

    if args.overwrite_output:
        clear_dir(output_root)

    output_root.mkdir(parents=True, exist_ok=True)
    partition_field_map = {
        "split": ["split"],
        "split/year_month": ["split", "year_month"],
        "split/year_month/region_id": ["split", "year_month", "region_id"],
    }
    partition_fields = partition_field_map[args.partition_mode]
    partition_schema = pa.schema([pa.field(field_name, pa.string()) for field_name in partition_fields])

    print(f"Starting final dataset write | shards: {len(final_paths):,}")
    # Heartbeat keeps long writes visible in logs when no per-batch output is emitted.
    heartbeat_stop, heartbeat_thread = start_phase_heartbeat("Final write", PROGRESS_INTERVAL_SECONDS)
    try:
        staged_dataset = ds.dataset(final_paths, format="parquet")
        ds.write_dataset(
            data=staged_dataset,
            base_dir=output_root,
            format="parquet",
            partitioning=ds.partitioning(partition_schema, flavor="hive"),
            basename_template="part-{i}.parquet",
            max_rows_per_file=args.max_rows_per_file,
            max_rows_per_group=args.max_rows_per_file,
            # Keep this high enough for throughput but below typical ulimit caps.
            max_open_files=512,
            max_partitions=8192,
            use_threads=FINAL_WRITE_USE_THREADS,
            existing_data_behavior="overwrite_or_ignore",
        )
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=2.0)

    print(f"Final dataset written to {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
