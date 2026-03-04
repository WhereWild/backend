"""Pipeline orchestration for preprocessing training observations."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import json
from pathlib import Path
import shutil
import threading
import time

import pyarrow as pa
import pyarrow.dataset as ds

from transform import build_feature_template, transform_file


FEATURE_CELL_SIZE_DEG = 0.25
FEATURE_REGION_SIZE_DEG = 10.0
MISSING_FEATURE_SENTINEL = -9999.0
PROGRESS_INTERVAL_SECONDS = 30.0
LOG_SLOW_FILE_SECONDS = 20.0
LOG_SLOW_READ_SECONDS = 8.0
SCHEMA_LOG_INTERVAL_FILES = 500
FINAL_WRITE_USE_THREADS = False


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

    fallback_time_policy = "drop" if bool(args.drop_missing_time) else "keep"

    print(f"Discovered {len(files):,} parquet files.")
    print(f"Using {args.threads} worker threads.")
    print(f"Staging dir: {staging_dir}")
    print(f"Output dir: {output_root}")
    print(f"Fallback time policy: {fallback_time_policy}")
    print(f"Missing feature sentinel: {MISSING_FEATURE_SENTINEL:.3f}")
    print("Include missing masks: True")
    print(f"Background ratio: {args.background_ratio:.3f}")
    print(f"Warn min cells/species: {int(args.warn_min_cells_per_species)}")
    print(f"Partition mode: {args.partition_mode}")
    print(f"Final write batch size (files): {int(args.final_write_batch_files)}")
    print(f"Final write use threads: {FINAL_WRITE_USE_THREADS}")
    if args.static_context_template:
        print(f"Static context template: {args.static_context_template}")
    if args.static_context_path is not None:
        print(f"Static context path: {args.static_context_path}")
    if args.temporal_context_template:
        print(f"Temporal context template: {args.temporal_context_template}")
    if args.temporal_context_path is not None:
        print(f"Temporal context path: {args.temporal_context_path}")
    print("Auto context discovery: True")
    if float(args.background_ratio) <= 0.0:
        print("Warning: background ratio is 0.0; output will contain positives only (no unlabeled/background rows).")

    print("Starting feature-template schema scan...")
    if int(args.template_scan_max_files) > 0:
        print(f"Template schema scan cap: {int(args.template_scan_max_files):,} files")
    template_start = time.perf_counter()
    feature_template = build_feature_template(
        files,
        schema_log_interval_files=SCHEMA_LOG_INTERVAL_FILES,
        log_slow_read_seconds=LOG_SLOW_READ_SECONDS,
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

    output_root.mkdir(parents=True, exist_ok=True)
    meta_dir = output_root / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    template_json_path = meta_dir / "feature_template.json"
    with open(template_json_path, "w") as _ft_fh:
        json.dump(
            {"env": feature_template.env, "habitat": feature_template.habitat, "weather": feature_template.weather},
            _ft_fh,
            indent=2,
        )
    print(f"Saved feature template to {template_json_path}")

    staging_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    staged_paths: list[Path] = []
    failures: list[tuple[Path, str]] = []
    low_cell_warnings: list[str] = []
    static_join_rows_total = 0
    temporal_join_rows_total = 0

    run_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        future_to_path = {
            pool.submit(
                transform_file,
                path,
                staging_dir,
                feature_version=args.feature_version,
                cell_size_deg=FEATURE_CELL_SIZE_DEG,
                region_size_deg=FEATURE_REGION_SIZE_DEG,
                feature_template=feature_template,
                fallback_time_policy=fallback_time_policy,
                background_ratio=args.background_ratio,
                missing_feature_sentinel=MISSING_FEATURE_SENTINEL,
                warn_min_cells_per_species=int(args.warn_min_cells_per_species),
                static_context_template=str(args.static_context_template or ""),
                static_context_path=args.static_context_path,
                static_context_required=bool(args.static_context_required),
                temporal_context_template=str(args.temporal_context_template or ""),
                temporal_context_path=args.temporal_context_path,
                temporal_context_required=bool(args.temporal_context_required),
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
                timeout=max(1.0, PROGRESS_INTERVAL_SECONDS),
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
                oldest_text = " | ".join(f"{duration:.1f}s:{path}" for duration, path in oldest_active)
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
                    if result.read_seconds >= LOG_SLOW_READ_SECONDS:
                        print(f"Slow read ({result.read_seconds:.1f}s) | rows: {result.rows:,} | {src}")
                    if result.duration_seconds >= LOG_SLOW_FILE_SECONDS:
                        print(f"Slow file ({result.duration_seconds:.1f}s) | rows: {result.rows:,} | {src}")
                    if result.low_cell_warnings:
                        low_cell_warnings.extend(result.low_cell_warnings)
                    static_join_rows_total += int(result.static_context_rows)
                    temporal_join_rows_total += int(result.temporal_context_rows)
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
        PROGRESS_INTERVAL_SECONDS,
    )
    try:
        output_root.mkdir(parents=True, exist_ok=True)

        partition_field_map = {
            "split": ["split"],
            "split/year_month": ["split", "year_month"],
            "split/year_month/region_id": ["split", "year_month", "region_id"],
        }
        partition_fields = partition_field_map[args.partition_mode]
        partition_schema = pa.schema([pa.field(field_name, pa.string()) for field_name in partition_fields])

        batch_size = max(1, int(args.final_write_batch_files))
        total_batches = (len(staged_paths) + batch_size - 1) // batch_size
        for batch_index, start_idx in enumerate(range(0, len(staged_paths), batch_size), start=1):
            end_idx = min(start_idx + batch_size, len(staged_paths))
            batch_paths = staged_paths[start_idx:end_idx]
            staged_dataset = ds.dataset(batch_paths, format="parquet")
            print(f"Final write batch {batch_index:,}/{total_batches:,} | files: {len(batch_paths):,}")
            ds.write_dataset(
                data=staged_dataset,
                base_dir=output_root,
                format="parquet",
                partitioning=ds.partitioning(
                    partition_schema,
                    flavor="hive",
                ),
                # Use a batch-specific prefix so successive batches do
                # not overwrite the files written by earlier batches.
                basename_template=f"part-{batch_index}-{{i}}.parquet",
                max_rows_per_file=args.max_rows_per_file,
                max_rows_per_group=args.max_rows_per_file,
                max_open_files=max(32, min(256, batch_size)),
                max_partitions=8192,
                use_threads=FINAL_WRITE_USE_THREADS,
                existing_data_behavior="overwrite_or_ignore",
            )
    finally:
        write_heartbeat_stop.set()
        write_heartbeat_thread.join(timeout=2.0)
    write_seconds = time.perf_counter() - write_start

    print(f"Final dataset written to {output_root}")
    print(f"Total rows: {written:,}")
    print(f"Static context merged rows: {static_join_rows_total:,}")
    print(f"Temporal context merged rows: {temporal_join_rows_total:,}")
    print(f"Final write duration: {write_seconds:.1f}s")

    if failures:
        print_failure_summary(failures)

    if low_cell_warnings:
        unique_warnings = sorted(set(low_cell_warnings))
        print("Low-cell species warnings:")
        for warning in unique_warnings[:100]:
            print(f"  - {warning}")
        if len(unique_warnings) > 100:
            print(f"  ... and {len(unique_warnings) - 100} more")

    if not args.keep_staging:
        cleanup_start = time.perf_counter()
        print(f"Removing staging directory: {staging_dir}")
        clear_dir(staging_dir)
        cleanup_seconds = time.perf_counter() - cleanup_start
        print(f"Staging cleanup duration: {cleanup_seconds:.1f}s")

    return 0 if not failures else 2
