"""Pipeline orchestration for preprocessing training observations."""

from __future__ import annotations

import json
import shutil
import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from importlib import import_module
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

_feature_contract = import_module("scripts.machine_learning._compat").import_feature_contract()
feature_template_dict = _feature_contract.feature_template_dict
format_feature_group_counts = _feature_contract.format_feature_group_counts

try:
    from .transform import build_feature_template, get_uncatalogued_summary, reset_uncatalogued_summary, transform_file
except ImportError:
    from transform import (  # type: ignore[no-redef]
        build_feature_template,
        get_uncatalogued_summary,
        reset_uncatalogued_summary,
        transform_file,
    )

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


def _species_inverse_frequency_weights(
    donor_species: np.ndarray,
    target_species: np.ndarray,
) -> np.ndarray:
    """Compute per-row sample weights that correct for donor-species frequency skew.

    For each target species independently, rows donated by over-represented
    donor species receive a lower weight so that common species do not
    dominate the unlabeled distribution.  Weights are normalised per
    target species so the mean weight for each target remains 1.0,
    keeping the nnPU negative-risk term at a consistent scale.

    Args:
        donor_species: species_key of the donor row for each background row.
        target_species: target species_key each background row is assigned to.

    Returns:
        float32 array of per-row weights, same length as donor_species.
    """
    weights = np.ones(len(donor_species), dtype=np.float32)
    for sp_key in np.unique(target_species):
        sp_mask = target_species == sp_key
        d_sp = donor_species[sp_mask]
        if d_sp.size == 0:
            continue
        unique_donors, inverse, donor_counts = np.unique(d_sp, return_inverse=True, return_counts=True)
        # Inverse-frequency: common donors get lower weight.
        w = 1.0 / donor_counts[inverse].astype(np.float32)
        # Normalise so mean weight within this target species = 1.0.
        mean_w = w.mean()
        if mean_w > 0:
            w /= mean_w
        weights[sp_mask] = w
    return weights


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
        used_indices: set[int] = set()

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

            if candidate_idx.size > 0:
                candidate_idx = np.unique(candidate_idx.astype(np.int64, copy=False))
                if used_indices:
                    used_idx_arr = np.fromiter(used_indices, dtype=np.int64)
                    candidate_idx = candidate_idx[~np.isin(candidate_idx, used_idx_arr)]

            if candidate_idx.size == 0:
                continue

            take_n = min(remaining, int(candidate_idx.size))
            chosen = candidate_idx[:take_n].astype(np.int64, copy=False)
            selected.append(chosen)
            used_indices.update(chosen.tolist())
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
    donor_species_all = species[donor_indices_all]
    sample_weights = _species_inverse_frequency_weights(donor_species_all, target_species_all)
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
            arrays.append(pa.array(sample_weights, type=pa.float32()))
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
    split_chunk_rows: int,
) -> tuple[list[Path], int]:
    """Generate unlabeled rows from pooled other-species positives per split.

    To keep memory bounded on very large runs, each split is processed in
    row chunks. Sampling semantics remain pooled-other-species within each
    split chunk, and generated chunk outputs are concatenated.
    """
    if background_ratio <= 0.0:
        return [], 0

    dataset = ds.dataset(staged_paths, format="parquet")
    generated_paths: list[Path] = []
    generated_rows = 0
    rng = np.random.default_rng(0)

    for split_name in ("train", "val", "test"):
        scanner = dataset.scanner(
            filter=pc.field("split") == split_name,
            use_threads=True,
            batch_size=65_536,
        )
        split_generated_rows = 0
        split_generated_shards = 0
        chunk_batches: list[pa.RecordBatch] = []
        chunk_rows = 0

        def flush_chunk(
            batches: list[pa.RecordBatch],
            shard_index: int,
        ) -> tuple[int, int]:
            """Flush one split chunk and return (rows_written, next_shard_index).

            The caller explicitly accumulates row counters and tracks shard
            indices from this return value.
            """
            if not batches:
                return 0, shard_index

            chunk_table = pa.Table.from_batches(batches)
            background_table = _build_background_table_for_split(
                chunk_table,
                split_name=split_name,
                background_ratio=background_ratio,
                rng=rng,
            )
            if background_table is None or background_table.num_rows == 0:
                return 0, shard_index

            out_path = staging_dir / f"background_pooled_{split_name}_{shard_index:05d}.parquet"
            pq.write_table(background_table, out_path, compression="zstd")
            generated_paths.append(out_path)
            return int(background_table.num_rows), shard_index + 1

        for batch in scanner.to_batches():
            if batch.num_rows == 0:
                continue
            chunk_batches.append(batch)
            chunk_rows += int(batch.num_rows)
            if chunk_rows >= max(1, split_chunk_rows):
                rows_written, split_generated_shards = flush_chunk(chunk_batches, split_generated_shards)
                generated_rows += rows_written
                split_generated_rows += rows_written
                chunk_batches = []
                chunk_rows = 0

        rows_written, split_generated_shards = flush_chunk(chunk_batches, split_generated_shards)
        generated_rows += rows_written
        split_generated_rows += rows_written
        chunk_batches = []
        chunk_rows = 0

        if split_generated_shards == 0:
            continue
        print(
            f"Background generation | split={split_name} | rows={split_generated_rows:,} | "
            f"shards={split_generated_shards:,}"
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


def write_partitioned_dataset(
    shard_paths: list[Path],
    output_root: Path,
    max_rows_per_file: int,
) -> None:
    """Write staging shards into a split-partitioned hive-style parquet dataset."""
    output_root.mkdir(parents=True, exist_ok=True)

    partition_schema = pa.schema([pa.field("split", pa.string())])

    heartbeat_stop, heartbeat_thread = start_phase_heartbeat("Final write", PROGRESS_INTERVAL_SECONDS)
    try:
        staged_dataset = ds.dataset(shard_paths, format="parquet")
        ds.write_dataset(
            data=staged_dataset,
            base_dir=output_root,
            format="parquet",
            partitioning=ds.partitioning(partition_schema, flavor="hive"),
            basename_template="part-{i}.parquet",
            max_rows_per_file=max_rows_per_file,
            max_rows_per_group=max_rows_per_file,
            max_open_files=512,
            max_partitions=8192,
            use_threads=FINAL_WRITE_USE_THREADS,
            existing_data_behavior="overwrite_or_ignore",
        )
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=2.0)


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
    print(f"Background split chunk rows: {args.background_split_chunk_rows:,}")
    print(f"Warn min cells/species: {int(args.warn_min_cells_per_species)}")
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
    if args.background_ratio <= 0.0:
        print("Warning: background ratio is 0.0; output will contain positives only (no unlabeled/background rows).")

    reset_uncatalogued_summary()

    print("Starting feature-template schema scan...")
    if args.template_scan_max_files > 0:
        print(f"Template schema scan cap: {args.template_scan_max_files:,} files")
    template_start = time.perf_counter()
    feature_template = build_feature_template(
        files,
        schema_log_interval_files=SCHEMA_LOG_INTERVAL_FILES,
        log_slow_read_seconds=LOG_SLOW_READ_SECONDS,
        template_scan_max_files=args.template_scan_max_files,
        static_context_template=str(args.static_context_template or ""),
        static_context_path=args.static_context_path,
        temporal_context_template=str(args.temporal_context_template or ""),
        temporal_context_path=args.temporal_context_path,
    )
    template_seconds = time.perf_counter() - template_start
    print(f"Feature template sizes | {format_feature_group_counts(feature_template)}")
    print(f"Feature-template schema scan duration: {template_seconds:.1f}s")

    output_root.mkdir(parents=True, exist_ok=True)
    meta_dir = output_root / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    template_json_path = meta_dir / "feature_template.json"
    with open(template_json_path, "w") as _ft_fh:
        json.dump(feature_template_dict(feature_template), _ft_fh, indent=2)
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
    if args.background_ratio > 0.0:
        print("Generating pooled unlabeled/background rows from other-species observations...")
        bg_start = time.perf_counter()
        background_paths, background_rows = generate_pooled_background_shards(
            staged_paths,
            staging_dir=staging_dir,
            background_ratio=args.background_ratio,
            split_chunk_rows=args.background_split_chunk_rows,
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
    print(f"Final write | shards: {len(staged_paths):,}")
    write_partitioned_dataset(
        staged_paths,
        output_root=output_root,
        max_rows_per_file=args.max_rows_per_file,
    )
    write_seconds = time.perf_counter() - write_start

    print(f"Final dataset written to {output_root}")
    print(f"Positive rows: {positive_rows:,}")
    print(f"Total rows: {written:,}")
    print(f"Static context merged rows: {static_join_rows_total:,}")
    print(f"Temporal context merged rows: {temporal_join_rows_total:,}")
    print(f"Final write duration: {write_seconds:.1f}s")

    uncatalogued_summary = get_uncatalogued_summary()
    uncatalogued_summary_path = meta_dir / "uncatalogued_columns.json"
    with open(uncatalogued_summary_path, "w") as handle:
        json.dump(uncatalogued_summary, handle, indent=2)
    print(f"Saved uncatalogued column summary to {uncatalogued_summary_path}")

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
