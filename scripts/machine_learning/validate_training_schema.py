"""Validate a training parquet dataset against a schema contract.

Checks required columns and Arrow-compatible types against
`schemas/training_observation.schema.json`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pyarrow as pa
import pyarrow.dataset as ds


def _parse_type(type_name: str) -> pa.DataType:
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
    payload = json.loads(schema_path.read_text(encoding="utf-8"))

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
    dataset = ds.dataset(data_path, format="parquet")
    return dataset.schema


def _type_matches(actual: pa.DataType, expected: pa.DataType) -> bool:
    if actual == expected:
        return True

    if pa.types.is_timestamp(actual) and pa.types.is_timestamp(expected):
        return actual.unit == expected.unit and actual.tz == expected.tz

    if pa.types.is_list(actual) and pa.types.is_list(expected):
        return _type_matches(actual.value_type, expected.value_type)

    return False


def _validate_with_loaded(
    expected: dict[str, pa.DataType],
    required: set[str],
    actual_schema: pa.Schema,
) -> tuple[list[str], list[str], list[str], list[str]]:
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


def validate(schema_path: Path, data_path: Path) -> tuple[list[str], list[str], list[str], list[str]]:
    expected, required = _load_contract(schema_path)
    actual_schema = _read_data_schema(data_path)

    return _validate_with_loaded(expected=expected, required=required, actual_schema=actual_schema)


def main() -> int:
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

    has_error = False

    if missing_required:
        has_error = True
        print("Missing required columns:")
        for name in missing_required:
            print(f"  - {name}")

    if type_mismatches:
        has_error = True
        print("Type mismatches:")
        for mismatch in type_mismatches:
            print(f"  - {mismatch}")

    if extras and not args.allow_extra_columns:
        has_error = True
        print("Extra columns (not in schema):")
        for name in extras:
            print(f"  - {name}")

    if missing_optional:
        print("Missing optional columns:")
        for name in missing_optional:
            print(f"  - {name}")

    if extras and args.allow_extra_columns:
        print("Extra columns (allowed):")
        for name in extras:
            print(f"  - {name}")

    if has_error:
        print("Validation failed.")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
