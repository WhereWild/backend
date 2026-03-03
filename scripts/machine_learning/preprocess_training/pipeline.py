"""Pipeline orchestration for preprocessing training observations."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
import shutil
import threading
import time

import pyarrow as pa
import pyarrow.dataset as ds

from transform import build_feature_template, transform_file


def discover_files(input_root: Path, glob_pattern: str, max_files: int) -> list[Path]:
    """Discover input parquet files under root using glob and optional file cap."""
    files = [path for path in input_root.glob(glob_pattern) if path.is_file()]
    files = [path for path in files if path.suffix.lower() == ".parquet"]
    files.sort()
    if max_files > 0:
        return files[:max_files]
    return files


def clear_dir(path: Path) -> None:
    """Delete a directory tree if present."""
    if path.exists():
        shutil.rmtree(path)


def print_failure_summary(failures: list[tuple[Path, str]], *, limit: int = 20) -> None:
    """Print a bounded summary of file-level failures."""
    if not failures:
        return
    print("Some files failed:")
    for src, err in failures[:limit]:
        print(f"  - {src}: {err}")
    if len(failures) > limit:
        print(f"  ... and {len(failures) - limit} more")


def start_phase_heartbeat(label: str, interval_seconds: float) -> tuple[threading.Event, threading.Thread]:
    """Start a daemon heartbeat thread for long single-phase operations."""
    stop_event = threading.Event()
    start = time.perf_counter()

    def _emit() -> None:
        while not stop_event.wait(timeout=max(1.0, interval_seconds)):
            elapsed = time.perf_counter() - start
            print(f"{label} heartbeat | elapsed: {elapsed:.1f}s")

    thread = threading.Thread(target=_emit, daemon=True)
    thread.start()
    return stop_event, thread


def run_preprocess(args) -> int:
    """Run full preprocessing pipeline from discovery through final write."""
    input_root = args.input_root.resolve()
    output_root = args.output_root.resolve()
    if args.staging_dir is not None:
        staging_dir = args.staging_dir.resolve()
    else:
        staging_dir = output_root.parent / f".{output_root.name}_staging"

    if args.overwrite_output:
        clear_dir(output_root)
        clear_dir(staging_dir)

    if not input_root.exists():
        raise SystemExit(f"Input root does not exist: {input_root}")

    files = discover_files(input_root, args.glob, args.max_files)
    if not files:
        raise SystemExit(f"No parquet files found in {input_root} with glob '{args.glob}'.")

    print(f"Discovered {len(files):,} parquet files.")
    print(f"Using {args.threads} worker threads.")
    print(f"Staging dir: {staging_dir}")
    print(f"Output dir: {output_root}")
    print(f"Fallback time policy: {args.fallback_time_policy}")
    print(f"Background ratio: {args.background_ratio:.3f}")
    print(f"Partition mode: {args.partition_mode}")
    if float(args.background_ratio) <= 0.0:
        print("Warning: background ratio is 0.0; output will contain positives only (no unlabeled/background rows).")

    print("Starting feature-template schema scan...")
    if int(args.template_scan_max_files) > 0:
        print(f"Template schema scan cap: {int(args.template_scan_max_files):,} files")
    template_start = time.perf_counter()
    feature_template = build_feature_template(
        files,
        schema_log_interval_files=args.schema_log_interval_files,
        log_slow_read_seconds=float(args.log_slow_read_seconds),
        template_scan_max_files=int(args.template_scan_max_files),
    )
    template_seconds = time.perf_counter() - template_start
    print(
        "Feature template sizes | "
        f"env={len(feature_template.env):,}, "
        f"habitat={len(feature_template.habitat):,}, "
        f"weather={len(feature_template.weather):,}"
    )
    print(f"Feature-template schema scan duration: {template_seconds:.1f}s")

    staging_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    staged_paths: list[Path] = []
    failures: list[tuple[Path, str]] = []

    run_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        future_to_path = {
            pool.submit(
                transform_file,
                path,
                staging_dir,
                feature_version=args.feature_version,
                cell_size_deg=args.cell_size_deg,
                region_size_deg=args.region_size_deg,
                feature_template=feature_template,
                fallback_time_policy=args.fallback_time_policy,
                background_ratio=args.background_ratio,
            ): path
            for path in files
        }
        future_start = {future: time.perf_counter() for future in future_to_path}

        pending = set(future_to_path.keys())
        processed = 0
        total = len(future_to_path)
        while pending:
            done, pending = wait(
                pending,
                timeout=max(1.0, float(args.progress_interval_seconds)),
                return_when=FIRST_COMPLETED,
            )

            if not done:
                elapsed = time.perf_counter() - run_start
                now = time.perf_counter()
                oldest_active = sorted(
                    ((now - future_start[future], future_to_path[future]) for future in pending),
                    key=lambda item: item[0],
                    reverse=True,
                )[:3]
                oldest_text = " | ".join(
                    f"{duration:.1f}s:{path}" for duration, path in oldest_active
                )
                print(
                    f"Heartbeat | processed: {processed:,}/{total:,} | "
                    f"rows written: {written:,} | failures: {len(failures):,} | "
                    f"in-flight: {len(pending):,} | elapsed: {elapsed:.1f}s"
                )
                if oldest_text:
                    print(f"In-flight oldest | {oldest_text}")
                continue

            for future in done:
                src = future_to_path[future]
                future_start.pop(future, None)
                processed += 1
                try:
                    result = future.result()
                    staged_paths.append(result.out_path)
                    written += result.rows
                    if result.read_seconds >= float(args.log_slow_read_seconds):
                        print(
                            f"Slow read ({result.read_seconds:.1f}s) | "
                            f"rows: {result.rows:,} | {src}"
                        )
                    if result.duration_seconds >= float(args.log_slow_file_seconds):
                        print(
                            f"Slow file ({result.duration_seconds:.1f}s) | "
                            f"rows: {result.rows:,} | {src}"
                        )
                except (OSError, IOError, ValueError, RuntimeError) as exc:  # pragma: no cover
                    failures.append((src, str(exc)))
                    print(f"Failed file | {src} | {exc}")

                if processed % 50 == 0 or processed == total:
                    print(
                        f"Processed {processed:,}/{total:,} files | "
                        f"rows written: {written:,} | failures: {len(failures):,}"
                    )

    if not staged_paths:
        if failures:
            print("No transformed shards were produced. Sample failure reasons:")
            for src, err in failures[:20]:
                print(f"  - {src}: {err}")
            if len(failures) > 20:
                print(f"  ... and {len(failures) - 20} more")
        raise SystemExit("No transformed shards were produced; aborting final write.")

    print(f"Starting final dataset write from staging: {staging_dir}")
    write_start = time.perf_counter()
    write_heartbeat_stop, write_heartbeat_thread = start_phase_heartbeat(
        "Final write",
        float(args.progress_interval_seconds),
    )
    try:
        staged_dataset = ds.dataset(staging_dir, format="parquet")
        output_root.mkdir(parents=True, exist_ok=True)

        partition_field_map = {
            "split": ["split"],
            "split/year_month": ["split", "year_month"],
            "split/year_month/region_id": ["split", "year_month", "region_id"],
        }
        partition_fields = partition_field_map[args.partition_mode]
        partition_schema = pa.schema([pa.field(field_name, pa.string()) for field_name in partition_fields])

        ds.write_dataset(
            data=staged_dataset,
            base_dir=output_root,
            format="parquet",
            partitioning=ds.partitioning(
                partition_schema,
                flavor="hive",
            ),
            max_rows_per_file=args.max_rows_per_file,
            max_rows_per_group=args.max_rows_per_file,
            max_partitions=8192,
            existing_data_behavior="overwrite_or_ignore",
        )
    finally:
        write_heartbeat_stop.set()
        write_heartbeat_thread.join(timeout=2.0)
    write_seconds = time.perf_counter() - write_start

    print(f"Final dataset written to {output_root}")
    print(f"Total rows: {written:,}")
    print(f"Final write duration: {write_seconds:.1f}s")

    if failures:
        print_failure_summary(failures)

    if not args.keep_staging:
        cleanup_start = time.perf_counter()
        print(f"Removing staging directory: {staging_dir}")
        clear_dir(staging_dir)
        cleanup_seconds = time.perf_counter() - cleanup_start
        print(f"Staging cleanup duration: {cleanup_seconds:.1f}s")

    return 0 if not failures else 2
