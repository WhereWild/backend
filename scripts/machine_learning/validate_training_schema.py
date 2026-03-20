"""Validate a split-partitioned training parquet dataset against a schema contract.

Checks required columns and Arrow-compatible types against
`schemas/training_observation.schema.json`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds


def _parse_type(type_name: str) -> pa.DataType:
    """Parse a contract type string into a PyArrow data type."""
    normalized = type_name.strip().lower()

    scalar_types: dict[str, pa.DataType] = {
        "bool": pa.bool_(),
        "int8": pa.int8(),
        "int16": pa.int16(),
        "int32": pa.int32(),
        "int64": pa.int64(),
        "float32": pa.float32(),
        "float64": pa.float64(),
        "string": pa.string(),
        "timestamp_ms_utc": pa.timestamp("ms", tz="UTC"),
    }
    if normalized in scalar_types:
        return scalar_types[normalized]

    if normalized.startswith("list<") and normalized.endswith(">"):
        inner = normalized[len("list<") : -1].strip()
        return pa.list_(_parse_type(inner))

    raise ValueError(f"Unsupported parquet_type in schema: {type_name}")


def _load_contract(schema_path: Path) -> tuple[dict[str, pa.DataType], set[str]]:
    """Load expected column types and required field names from schema JSON."""
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    # This contract uses a custom schema format keyed by `columns`; we intentionally
    # do not validate generic JSON Schema meta-fields (including `$schema`) here.

    expected: dict[str, pa.DataType] = {}
    required: set[str] = set()

    for column in payload.get("columns", []):
        name = str(column["name"])
        type_name = str(column["parquet_type"])
        expected[name] = _parse_type(type_name)
        if bool(column.get("required", False)):
            required.add(name)

    return expected, required


def _read_data_schema(data_path: Path) -> pa.Schema:
    """Read dataset schema from a split-partitioned parquet file or directory."""
    dataset = ds.dataset(data_path, format="parquet", partitioning="hive")
    return dataset.schema


def _type_matches(actual: pa.DataType, expected: pa.DataType) -> bool:
    """Return True when actual arrow type is compatible with expected contract type."""
    if actual == expected:
        return True

    if pa.types.is_timestamp(actual) and pa.types.is_timestamp(expected):
        return actual.unit == expected.unit and actual.tz == expected.tz

    if pa.types.is_list(actual) and pa.types.is_list(expected):
        return _type_matches(actual.value_type, expected.value_type)

    if pa.types.is_fixed_size_list(actual) and pa.types.is_list(expected):
        return _type_matches(actual.value_type, expected.value_type)

    return False


def _validate_with_loaded(
    expected: dict[str, pa.DataType],
    required: set[str],
    actual_schema: pa.Schema,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Validate loaded schema objects and return missing, mismatched, and extra columns."""
    actual_fields = {field.name: field.type for field in actual_schema}

    missing_required = sorted(name for name in required if name not in actual_fields)
    missing_optional = sorted(name for name in expected if name not in actual_fields and name not in required)

    type_mismatches: list[str] = []
    for name, expected_type in expected.items():
        actual_type = actual_fields.get(name)
        if actual_type is None:
            continue
        if not _type_matches(actual_type, expected_type):
            type_mismatches.append(f"{name}: expected {expected_type}, found {actual_type}")

    extras = sorted(name for name in actual_fields if name not in expected)

    return missing_required, missing_optional, type_mismatches, extras


def validate(
    schema_path: Path,
    data_path: Path,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Convenience wrapper that loads schema/data before validation."""
    expected, required = _load_contract(schema_path)
    actual_schema = _read_data_schema(data_path)

    return _validate_with_loaded(expected=expected, required=required, actual_schema=actual_schema)


def main() -> int:
    """CLI entrypoint for dataset/schema validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/training_observation.schema.json"),
        help="Path to schema JSON contract.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to parquet file or parquet dataset root.",
    )
    parser.add_argument(
        "--allow-extra-columns",
        action="store_true",
        help="If set, do not fail when data contains columns absent from schema.",
    )

    args = parser.parse_args()

    expected, required = _load_contract(args.schema)
    actual_schema = _read_data_schema(args.data)
    missing_required, missing_optional, type_mismatches, extras = _validate_with_loaded(
        expected=expected,
        required=required,
        actual_schema=actual_schema,
    )

    def _print_items(title: str, items: list[str]) -> None:
        if not items:
            return
        print(title)
        for item in items:
            print(f"  - {item}")

    has_error = False

    if missing_required:
        has_error = True
        _print_items("Missing required columns:", missing_required)

    if type_mismatches:
        has_error = True
        _print_items("Type mismatches:", type_mismatches)

    if extras and not args.allow_extra_columns:
        has_error = True
        _print_items("Extra columns (not in schema):", extras)

    if missing_optional:
        _print_items("Missing optional columns:", missing_optional)

    if extras and args.allow_extra_columns:
        _print_items("Extra columns (allowed):", extras)

    if has_error:
        print("Validation failed.")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
