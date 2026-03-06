"""Resume preprocessing from existing staging shards.

This utility is intended for runs where per-file transforms completed but the
pipeline stopped during pooled background generation or final dataset write.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.dataset as ds

try:
    from .pipeline import (
        clear_dir,
        generate_pooled_background_shards,
        write_partitioned_dataset,
    )
except ImportError:
    from pipeline import (  # type: ignore[no-redef]
        clear_dir,
        generate_pooled_background_shards,
        write_partitioned_dataset,
    )

try:
    from .transform import classify_feature_name, is_numeric_arrow_type
except ImportError:
    from transform import classify_feature_name, is_numeric_arrow_type  # type: ignore[no-redef]


def _write_feature_template_from_output(output_root: Path) -> Path:
    """Rebuild and save feature template metadata from a written output dataset."""
    dataset = ds.dataset(output_root, format="parquet", partitioning="hive")
    schema = dataset.schema

    env: set[str] = set()
    habitat: set[str] = set()
    weather: set[str] = set()

    for field in schema:
        if not is_numeric_arrow_type(field.type):
            continue
        group = classify_feature_name(field.name)
        if group == "env":
            env.add(field.name)
        elif group == "habitat":
            habitat.add(field.name)
        elif group == "weather":
            weather.add(field.name)

    meta_dir = output_root / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    template_path = meta_dir / "feature_template.json"
    with open(template_path, "w") as handle:
        json.dump(
            {
                "env": sorted(env),
                "habitat": sorted(habitat),
                "weather": sorted(weather),
            },
            handle,
            indent=2,
        )
    return template_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resume preprocessing from staging shards with explicit actions."
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        required=False,
        help=(
            "Directory containing transformed staging parquet shards. "
            "Required when using --resume-base-files, --resume-background-files, "
            "or --resume-output-files."
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Final partitioned output dataset root.",
    )
    parser.add_argument(
        "--resume-base-files",
        action="store_true",
        help="Include transformed base staging shards (non-background parquet files).",
    )
    parser.add_argument(
        "--resume-background-files",
        action="store_true",
        help="Include background_pooled_*.parquet staging shards (generate if missing and ratio > 0).",
    )
    parser.add_argument(
        "--resume-output-files",
        action="store_true",
        help="Write output parquet partitions from selected staging file types.",
    )
    parser.add_argument(
        "--resume-feature-template-file",
        action="store_true",
        help="(Re)write <output-root>/_meta/feature_template.json from the existing output dataset.",
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
        "--regenerate-background",
        action="store_true",
        help="Delete existing background_pooled_*.parquet files and regenerate them (requires --resume-background-files).",
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

    output_root = args.output_root.resolve()

    if not any(
        [
            args.resume_base_files,
            args.resume_background_files,
            args.resume_output_files,
            args.resume_feature_template_file,
        ]
    ):
        print(
            "No resume actions requested. "
            "Use one or more of: --resume-base-files, --resume-background-files, "
            "--resume-output-files, --resume-feature-template-file."
        )
        return 0

    if args.regenerate_background and not args.resume_background_files:
        raise SystemExit("--regenerate-background requires --resume-background-files.")

    if args.resume_feature_template_file and not args.resume_output_files:
        if not output_root.exists():
            raise SystemExit(f"Output dir does not exist: {output_root}")
        template_path = _write_feature_template_from_output(output_root)
        print(f"Saved feature template to {template_path}")
        # Feature-template-only mode exits early when no output write was requested.
        if not args.resume_output_files:
            return 0

    needs_staging = args.resume_base_files or args.resume_background_files or args.resume_output_files
    if not needs_staging:
        return 0
    if args.staging_dir is None:
        raise SystemExit(
            "--staging-dir is required when using --resume-base-files, "
            "--resume-background-files, or --resume-output-files."
        )
    staging_dir = args.staging_dir.resolve()

    if not staging_dir.exists():
        raise SystemExit(f"Staging dir does not exist: {staging_dir}")

    base_paths, existing_background_paths = _list_staging_paths(staging_dir)
    if args.resume_base_files and not base_paths:
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

    # Reuse existing background shards when present to avoid recomputing the
    # expensive pooled-sampling step on large staging directories.
    background_paths: list[Path] = []
    if args.resume_background_files:
        background_paths = existing_background_paths

    if args.resume_background_files and args.background_ratio > 0.0 and not background_paths:
        if not args.resume_base_files:
            raise SystemExit(
                "Background generation requires base shards. Add --resume-base-files when using --resume-background-files."
            )
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

    if args.resume_output_files:
        final_paths: list[Path] = []
        if args.resume_base_files:
            final_paths.extend(base_paths)
        if args.resume_background_files:
            final_paths.extend(background_paths)
        if not final_paths:
            raise SystemExit(
                "--resume-output-files was requested but no staging file types were selected. "
                "Add --resume-base-files and/or --resume-background-files."
            )

        clear_dir(output_root)

        print(f"Starting final dataset write | shards: {len(final_paths):,}")
        write_partitioned_dataset(
            final_paths,
            output_root=output_root,
            max_rows_per_file=args.max_rows_per_file,
        )
        print(f"Final dataset written to {output_root}")

    if args.resume_feature_template_file and output_root.exists():
        template_path = _write_feature_template_from_output(output_root)
        print(f"Saved feature template to {template_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
