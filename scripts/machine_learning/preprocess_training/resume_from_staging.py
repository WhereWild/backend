"""Resume preprocessing from existing staging shards.

This utility is intended for runs where per-file transforms completed but the
pipeline stopped during pooled background generation or final dataset write.
"""

from __future__ import annotations

import argparse
import json
from importlib import import_module
from pathlib import Path
from typing import Any

import pyarrow.dataset as ds

_feature_contract = import_module("scripts.machine_learning._compat").import_feature_contract()
FEATURE_COLUMNS = _feature_contract.FEATURE_COLUMNS
FEATURE_COLUMN_TO_GROUP = _feature_contract.FEATURE_COLUMN_TO_GROUP
FEATURE_GROUPS = _feature_contract.FEATURE_GROUPS
empty_feature_template = _feature_contract.empty_feature_template
format_feature_group_counts = _feature_contract.format_feature_group_counts
normalize_feature_template = _feature_contract.normalize_feature_template

try:
    from .pipeline import (
        generate_pooled_background_shards,
        write_partitioned_dataset,
    )
except ImportError:
    from pipeline import (  # type: ignore[no-redef]
        generate_pooled_background_shards,
        write_partitioned_dataset,
    )

try:
    from .transform import classify_feature_name, is_numeric_arrow_type
except ImportError:
    from transform import classify_feature_name, is_numeric_arrow_type  # type: ignore[no-redef]


DEFAULT_MAX_ROWS_PER_FILE = 150_000
DEFAULT_BACKGROUND_SPLIT_CHUNK_ROWS = 250_000


def _template_counts(template: dict[str, list[str]]) -> dict[str, int]:
    return {group: len(template.get(group, [])) for group in FEATURE_GROUPS}


def _normalize_template_payload(raw: dict[str, Any]) -> dict[str, list[str]]:
    """Normalize modern or legacy feature-template payloads to current groups."""
    template = normalize_feature_template(raw)
    if any(_template_counts(template).values()):
        return template

    legacy = empty_feature_template()
    for group_name, values in raw.items():
        if group_name in FEATURE_GROUPS or not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, str) or not value:
                continue
            group = classify_feature_name(value)
            if group is None:
                group = "other"
            legacy[group].append(value)

    for group in FEATURE_GROUPS:
        legacy[group] = sorted(set(legacy[group]))
    return legacy


def _format_feature_dims(dims: dict[str, int] | None) -> str:
    if dims is None:
        return "unknown"
    return format_feature_group_counts(dims)


def _feature_dims_from_vectors(dataset: ds.Dataset) -> dict[str, int] | None:
    """Read one row to infer vector widths for feature-vector columns."""
    vector_columns = list(FEATURE_COLUMNS)
    present_columns = [name for name in vector_columns if name in dataset.schema.names]
    if not present_columns:
        return None

    row = dataset.head(1, columns=present_columns)
    if row.num_rows == 0:
        return None

    dims = {group: 0 for group in FEATURE_GROUPS}
    for column_name in present_columns:
        values = row.column(column_name)[0].as_py() or []
        dims[FEATURE_COLUMN_TO_GROUP[column_name]] = len(values)
    return dims


def _template_matches_dims(template: dict[str, list[str]], dims: dict[str, int] | None) -> bool:
    if dims is None:
        return True
    counts = _template_counts(template)
    for key, expected in dims.items():
        if expected > 0 and counts.get(key, 0) != expected:
            return False
    return True


def _load_catalog_feature_template() -> dict[str, list[str]] | None:
    """Derive feature names from GIS catalog layer ids using classifier rules."""
    project_root = Path(__file__).resolve().parents[3]
    catalog_candidates = [
        project_root / "config" / "gis" / "catalog.json",
        project_root / "data" / "gis" / "catalog.json",
    ]
    catalog_path = next((path for path in catalog_candidates if path.exists()), None)
    if catalog_path is None:
        return None

    try:
        with open(catalog_path) as handle:
            catalog = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None

    grouped: dict[str, set[str]] = {group: set() for group in FEATURE_GROUPS if group != "other"}
    for category in catalog.get("categories", []):
        for layer in category.get("layers", []):
            layer_id = layer.get("id")
            if not isinstance(layer_id, str) or not layer_id:
                continue
            group = classify_feature_name(layer_id)
            if group in grouped:
                grouped[group].add(layer_id)

    template = empty_feature_template()
    for group_name, values in grouped.items():
        template[group_name] = sorted(values)
    return template if any(_template_counts(template).values()) else None


def _find_matching_template_in_sibling_datasets(
    output_root: Path,
    dims: dict[str, int] | None,
) -> dict[str, list[str]] | None:
    """Look for a non-empty template in other local datasets with matching dims."""
    project_root = Path(__file__).resolve().parents[3]
    target_meta = (output_root / "_meta" / "feature_template.json").resolve()
    search_roots: list[Path] = []
    for candidate_root in (output_root.parent, project_root / "data_ml", project_root / "data"):
        try:
            resolved = candidate_root.resolve()
        except OSError:
            continue
        if not resolved.exists() or resolved in search_roots:
            continue
        search_roots.append(resolved)

    candidates: list[Path] = []
    for search_root in search_roots:
        candidates.extend(sorted(search_root.glob("species_observation*/_meta/feature_template.json")))

    normalized_candidates: list[dict[str, list[str]]] = []
    for candidate in candidates:
        try:
            if candidate.resolve() == target_meta:
                continue
        except OSError:
            continue
        template = _read_existing_template(candidate)
        if template is None:
            continue
        normalized_candidates.append(template)
        if _template_matches_dims(template, dims):
            return template

    if dims is None:
        return None

    composed = empty_feature_template()
    for group in FEATURE_GROUPS:
        expected = int(dims.get(group, 0))
        if expected <= 0:
            continue
        for candidate in normalized_candidates:
            values = list(candidate.get(group, []))
            if len(values) == expected:
                composed[group] = values
                break
        else:
            return None

    return composed


def _read_existing_template(template_path: Path) -> dict[str, list[str]] | None:
    if not template_path.exists():
        return None
    try:
        with open(template_path) as handle:
            raw: dict[str, Any] = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    template = _normalize_template_payload(raw)
    return template if any(_template_counts(template).values()) else None


def _read_json_payload(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _write_feature_template_from_output(output_root: Path) -> Path:
    """Rebuild and save feature template metadata from a written output dataset."""
    dataset = ds.dataset(output_root, format="parquet", partitioning="hive")
    schema = dataset.schema
    feature_dims = _feature_dims_from_vectors(dataset)

    grouped: dict[str, set[str]] = {group: set() for group in FEATURE_GROUPS if group != "other"}

    for field in schema:
        if not is_numeric_arrow_type(field.type):
            continue
        group = classify_feature_name(field.name)
        if group in grouped:
            grouped[group].add(field.name)

    rebuilt_template = empty_feature_template()
    for group_name, values in grouped.items():
        rebuilt_template[group_name] = sorted(values)

    meta_dir = output_root / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    template_path = meta_dir / "feature_template.json"

    if any(_template_counts(rebuilt_template).values()) and _template_matches_dims(rebuilt_template, feature_dims):
        template_to_write = rebuilt_template
    else:
        existing_template = _read_existing_template(template_path)
        if existing_template is not None and _template_matches_dims(existing_template, feature_dims):
            template_to_write = existing_template
        else:
            sibling_template = _find_matching_template_in_sibling_datasets(output_root, feature_dims)
            if sibling_template is not None:
                template_to_write = sibling_template
            else:
                catalog_template = _load_catalog_feature_template()
                if catalog_template is not None and _template_matches_dims(catalog_template, feature_dims):
                    template_to_write = catalog_template
                else:
                    dims_text = _format_feature_dims(feature_dims)
                    raise ValueError(
                        "Unable to rebuild feature_template.json from output schema and no valid fallback was found "
                        f"for feature dims={dims_text}."
                    )

    with open(template_path, "w") as handle:
        json.dump(template_to_write, handle, indent=2)
    return template_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume preprocessing from staging shards with explicit actions.")
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
        default=DEFAULT_BACKGROUND_SPLIT_CHUNK_ROWS,
        help="Row cap per split chunk during pooled background generation.",
    )
    parser.add_argument(
        "--max-rows-per-file",
        type=int,
        default=DEFAULT_MAX_ROWS_PER_FILE,
        help="Max rows per output parquet file in final dataset.",
    )
    parser.add_argument(
        "--regenerate-background",
        action="store_true",
        help="Delete existing background_pooled_*.parquet files and regenerate them (requires --resume-background-files).",
    )
    parser.add_argument(
        "--reuse-existing-background",
        action="store_true",
        help="Acknowledge and reuse existing background_pooled_*.parquet files without regenerating them.",
    )
    return parser.parse_args()


def _list_staging_paths(staging_dir: Path) -> tuple[list[Path], list[Path]]:
    # Base shards come from per-file transforms; background shards are optional
    # synthetic PU rows generated after transforms complete.
    all_paths = sorted(path for path in staging_dir.glob("*.parquet") if path.is_file())
    base_paths = [path for path in all_paths if not path.name.startswith("background_pooled_")]
    background_paths = [path for path in all_paths if path.name.startswith("background_pooled_")]
    return base_paths, background_paths


def _ensure_background_selection_is_explicit(
    *,
    existing_background_paths: list[Path],
    resume_background_files: bool,
    regenerate_background: bool,
    reuse_existing_background: bool,
) -> None:
    """Refuse to silently reuse existing background shards during resume runs."""
    if not resume_background_files or not existing_background_paths:
        return
    if regenerate_background or reuse_existing_background:
        return
    raise SystemExit(
        "Existing background_pooled_*.parquet shards were found in staging. "
        "Refusing to silently reuse them because they may not match the requested background ratio. "
        "Pass --reuse-existing-background to keep them as-is, or --regenerate-background to rebuild them."
    )


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
    if args.reuse_existing_background and not args.resume_background_files:
        raise SystemExit("--reuse-existing-background requires --resume-background-files.")
    if args.regenerate_background and args.reuse_existing_background:
        raise SystemExit("Use only one of --regenerate-background or --reuse-existing-background.")

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

    _ensure_background_selection_is_explicit(
        existing_background_paths=existing_background_paths,
        resume_background_files=args.resume_background_files,
        regenerate_background=args.regenerate_background,
        reuse_existing_background=args.reuse_existing_background,
    )

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
            output_rows_per_shard=max(1, int(args.max_rows_per_file)),
        )
        print(
            f"Background generation complete | rows: {generated_background_rows:,} | shards: {len(background_paths):,}"
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

        print(f"Starting final dataset write | shards: {len(final_paths):,}")
        metadata_payloads: dict[str, object] = {}
        existing_feature_template = _read_json_payload(output_root / "_meta" / "feature_template.json")
        if existing_feature_template is not None:
            metadata_payloads["_meta/feature_template.json"] = existing_feature_template
        existing_uncatalogued = _read_json_payload(output_root / "_meta" / "uncatalogued_columns.json")
        if existing_uncatalogued is not None:
            metadata_payloads["_meta/uncatalogued_columns.json"] = existing_uncatalogued
        write_partitioned_dataset(
            final_paths,
            output_root=output_root,
            max_rows_per_file=args.max_rows_per_file,
            metadata_payloads=metadata_payloads or None,
        )
        print(f"Final dataset written to {output_root}")

    if args.resume_feature_template_file and output_root.exists():
        template_path = _write_feature_template_from_output(output_root)
        print(f"Saved feature template to {template_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
