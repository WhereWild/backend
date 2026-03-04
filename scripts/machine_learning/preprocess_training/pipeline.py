"""Pipeline orchestration for preprocessing training observations."""

from __future__ import annotations

import json
import shutil
import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from transform import build_feature_template, transform_file

if TYPE_CHECKING:
    from pathlib import Path

FEATURE_CELL_SIZE_DEG = 0.25
FEATURE_REGION_SIZE_DEG = 10.0
MISSING_FEATURE_SENTINEL = -9999.0
PROGRESS_INTERVAL_SECONDS = 30.0
LOG_SLOW_FILE_SECONDS = 20.0
LOG_SLOW_READ_SECONDS = 8.0
SCHEMA_LOG_INTERVAL_FILES = 500
FINAL_WRITE_USE_THREADS = False


def _build_background_table_for_split(
    split_table: pa.Table,
    *,
    split_name: str,
    background_ratio: float,
    rng: np.random.Generator,
) -> pa.Table | None:
    """Generate pooled other-species unlabeled rows for one split."""
    if split_table.num_rows == 0 or background_ratio <= 0:
        return None

    species = split_table.column("species_key").to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
    cell_ids = split_table.column("cell_id").to_numpy(zero_copy_only=False)
    year_month = split_table.column("year_month").to_numpy(zero_copy_only=False)

    if len(species) == 0:
        return None

    key_frame = pd.DataFrame({"cell_id": cell_ids, "year_month": year_month})
    key_ids = pd.util.hash_pandas_object(key_frame, index=False).to_numpy(dtype=np.uint64, copy=False)

    unique_species, positive_counts = np.unique(species, return_counts=True)
    per_species_positive_keys: dict[int, np.ndarray] = {}
    for sp_key in unique_species.tolist():
        per_species_positive_keys[int(sp_key)] = np.unique(key_ids[species == sp_key])

    sampled_donor_indices: list[np.ndarray] = []
    sampled_target_species: list[np.ndarray] = []

    for sp_key, n_pos in zip(unique_species.tolist(), positive_counts.tolist(), strict=True):
        target_bg = round(float(n_pos) * background_ratio)
        if target_bg <= 0:
            continue

        forbidden_key_ids = per_species_positive_keys[int(sp_key)]
        selected: list[np.ndarray] = []
        selected_count = 0

        attempts = 0
        while selected_count < target_bg and attempts < 8:
            attempts += 1
            remaining = target_bg - selected_count
            draw_size = max(128, int(remaining * 2.0))
            draw_idx = rng.integers(0, len(species), size=draw_size, endpoint=False)

            valid_species = species[draw_idx] != int(sp_key)
            if not valid_species.any():
                continue

            candidate_idx = draw_idx[valid_species]
            if forbidden_key_ids.size > 0:
                candidate_keys = key_ids[candidate_idx]
                non_conflict = ~np.isin(candidate_keys, forbidden_key_ids)
                candidate_idx = candidate_idx[non_conflict]

            if candidate_idx.size == 0:
                continue

            take_n = min(remaining, int(candidate_idx.size))
            selected.append(candidate_idx[:take_n].astype(np.int64, copy=False))
            selected_count += take_n

        if not selected:
            continue

        donor_idx = np.concatenate(selected)
        sampled_donor_indices.append(donor_idx)
        sampled_target_species.append(np.full(donor_idx.shape[0], int(sp_key), dtype=np.int64))

    if not sampled_donor_indices:
        print(f"Background generation | split={split_name} | no valid donor rows")
        return None

    donor_indices_all = np.concatenate(sampled_donor_indices)
    target_species_all = np.concatenate(sampled_target_species)
    take_indices = pa.array(donor_indices_all, type=pa.int64())
    sampled = split_table.take(take_indices)

    n_rows = sampled.num_rows
    arrays: list[pa.Array] = []
    names = sampled.schema.names
    for name in names:
        if name == "sample_id":
            arrays.append(pa.array([str(uuid.uuid4()) for _ in range(n_rows)], type=pa.string()))
        elif name == "observation_id":
            arrays.append(pa.array([None] * n_rows, type=pa.string()))
        elif name == "species_key":
            arrays.append(pa.array(target_species_all, type=pa.int64()))
        elif name == "presence_label":
            arrays.append(pa.array(np.zeros(n_rows, dtype=np.int8), type=pa.int8()))
        elif name == "sample_weight":
            arrays.append(pa.array(np.ones(n_rows, dtype=np.float32), type=pa.float32()))
        elif name == "source":
            arrays.append(pa.array(["generated_background"] * n_rows, type=pa.string()))
        else:
            arrays.append(sampled.column(name))

    return pa.Table.from_arrays(arrays, names=names)


def generate_pooled_background_shards(
    staged_paths: list[Path],
    *,
    staging_dir: Path,
    background_ratio: float,
) -> tuple[list[Path], int]:
    """Generate unlabeled rows from pooled other-species positives per split."""
    if background_ratio <= 0.0:
        return [], 0

    dataset = ds.dataset(staged_paths, format="parquet")
    generated_paths: list[Path] = []
    generated_rows = 0
    rng = np.random.default_rng(0)

    for split_name in ("train", "val", "test"):
        split_table = dataset.to_table(filter=pc.field("split") == split_name, use_threads=True)
        background_table = _build_background_table_for_split(
            split_table,
            split_name=split_name,
            background_ratio=background_ratio,
            rng=rng,
        )
        if background_table is None or background_table.num_rows == 0:
            continue

        out_path = staging_dir / f"background_pooled_{split_name}.parquet"
        pq.write_table(background_table, out_path, compression="zstd")
        generated_paths.append(out_path)
        generated_rows += int(background_table.num_rows)
        print(
            f"Background generation | split={split_name} | rows={background_table.num_rows:,} | path={out_path.name}"
        )

    return generated_paths, generated_rows


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
                except (OSError, ValueError, RuntimeError) as exc:  # pragma: no cover
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

    positive_rows = written
    if float(args.background_ratio) > 0.0:
        print("Generating pooled unlabeled/background rows from other-species observations...")
        bg_start = time.perf_counter()
        background_paths, background_rows = generate_pooled_background_shards(
            staged_paths,
            staging_dir=staging_dir,
            background_ratio=float(args.background_ratio),
        )
        staged_paths.extend(background_paths)
        written += int(background_rows)
        bg_seconds = time.perf_counter() - bg_start
        print(
            f"Background generation complete | rows: {background_rows:,} | "
            f"shards: {len(background_paths):,} | duration: {bg_seconds:.1f}s"
        )

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
    print(f"Positive rows: {positive_rows:,}")
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
