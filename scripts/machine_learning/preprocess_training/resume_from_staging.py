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


def _template_counts(template: dict[str, list[str]]) -> dict[str, int]:
    return {group: len(template.get(group, [])) for group in FEATURE_GROUPS}


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

    bioclimate: set[str] = set()
    landclass: set[str] = set()
    terrain: set[str] = set()
    edaphic: set[str] = set()
    temporal: set[str] = set()
    for category in catalog.get("categories", []):
        for layer in category.get("layers", []):
            layer_id = layer.get("id")
            if not isinstance(layer_id, str) or not layer_id:
                continue
            group = classify_feature_name(layer_id)
            if group == "bioclimate":
                bioclimate.add(layer_id)
            elif group == "landclass":
                landclass.add(layer_id)
            elif group == "terrain":
                terrain.add(layer_id)
            elif group == "edaphic":
                edaphic.add(layer_id)
            elif group == "temporal":
                temporal.add(layer_id)

    template = empty_feature_template()
    template["bioclimate"] = sorted(bioclimate)
    template["landclass"] = sorted(landclass)
    template["terrain"] = sorted(terrain)
    template["edaphic"] = sorted(edaphic)
    template["temporal"] = sorted(temporal)
    return template if any(_template_counts(template).values()) else None


def _find_matching_template_in_sibling_datasets(
    output_root: Path,
    dims: dict[str, int] | None,
) -> dict[str, list[str]] | None:
    """Look for a non-empty template in other local datasets with matching dims."""
    project_root = Path(__file__).resolve().parents[3]
    data_root = project_root / "data"
    if not data_root.exists():
        return None

    target_meta = (output_root / "_meta" / "feature_template.json").resolve()
    candidates = sorted(data_root.glob("species_observation*/_meta/feature_template.json"))
    for candidate in candidates:
        try:
            if candidate.resolve() == target_meta:
                continue
        except OSError:
            continue
        template = _read_existing_template(candidate)
        if template is None:
            continue
        if _template_matches_dims(template, dims):
            return template
    return None


def _read_existing_template(template_path: Path) -> dict[str, list[str]] | None:
    if not template_path.exists():
        return None
    try:
        with open(template_path) as handle:
            raw: dict[str, Any] = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    template = normalize_feature_template(raw)
    return template if any(_template_counts(template).values()) else None


def _write_feature_template_from_output(output_root: Path) -> Path:
    """Rebuild and save feature template metadata from a written output dataset."""
    dataset = ds.dataset(output_root, format="parquet", partitioning="hive")
    schema = dataset.schema
    feature_dims = _feature_dims_from_vectors(dataset)

    bioclimate: set[str] = set()
    landclass: set[str] = set()
    terrain: set[str] = set()
    edaphic: set[str] = set()
    temporal: set[str] = set()

    for field in schema:
        if not is_numeric_arrow_type(field.type):
            continue
        group = classify_feature_name(field.name)
        if group == "bioclimate":
            bioclimate.add(field.name)
        elif group == "landclass":
            landclass.add(field.name)
        elif group == "terrain":
            terrain.add(field.name)
        elif group == "edaphic":
            edaphic.add(field.name)
        elif group == "temporal":
            temporal.add(field.name)

    rebuilt_template = empty_feature_template()
    rebuilt_template["bioclimate"] = sorted(bioclimate)
    rebuilt_template["landclass"] = sorted(landclass)
    rebuilt_template["terrain"] = sorted(terrain)
    rebuilt_template["edaphic"] = sorted(edaphic)
    rebuilt_template["temporal"] = sorted(temporal)

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

    if not any([
        args.resume_base_files,
        args.resume_background_files,
        args.resume_output_files,
        args.resume_feature_template_file,
    ]):
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
