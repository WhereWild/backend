from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc


# Hacky test join for Micropuntia pulchella (taxon 3942895)
BASE_PARQUET = Path("/workspace/occurrence.parquet")
SAMPLE_PARQUET = Path("/workspace/occurrence.parquet.om_sample.parquet")
OUTPUT_PARQUET = Path("/workspace/occurrence.parquet.joined.parquet")

KEY_COL = "catalogNumber"


def main() -> None:
    if not BASE_PARQUET.exists():
        raise SystemExit(f"Missing base parquet: {BASE_PARQUET}")
    if not SAMPLE_PARQUET.exists():
        raise SystemExit(f"Missing sample parquet: {SAMPLE_PARQUET}")

    base = pq.read_table(BASE_PARQUET).combine_chunks()
    sample = pq.read_table(SAMPLE_PARQUET).combine_chunks()

    if KEY_COL not in base.column_names:
        raise SystemExit(f"{KEY_COL} missing in {BASE_PARQUET}")
    if KEY_COL not in sample.column_names:
        raise SystemExit(f"{KEY_COL} missing in {SAMPLE_PARQUET}")

    # Ensure key is string in both
    base = base.set_column(
        base.schema.get_field_index(KEY_COL),
        KEY_COL,
        pc.cast(base[KEY_COL], pa.string()),
    )
    sample = sample.set_column(
        sample.schema.get_field_index(KEY_COL),
        KEY_COL,
        pc.cast(sample[KEY_COL], pa.string()),
    )

    # Manual left join via hash map (avoids join_type support issues)
    sample_map: dict[str, dict[str, Any]] = {}
    # Dedup: drop columns that already exist in base
    sample_cols = [
        name for name in sample.column_names
        if name != KEY_COL and name not in base.column_names
    ]
    for row in sample.to_pylist():
        key = row.get(KEY_COL)
        if key is None:
            continue
        if key not in sample_map:
            sample_map[key] = {col: row.get(col) for col in sample_cols}

    new_columns: dict[str, list[Any]] = {col: [] for col in sample_cols}
    for row in base.to_pylist():
        key = row.get(KEY_COL)
        sample_row = sample_map.get(key)
        for col in sample_cols:
            new_columns[col].append(sample_row.get(col) if sample_row else None)

    joined = base
    for col, values in new_columns.items():
        joined = joined.append_column(col, pa.array(values))
    pq.write_table(joined, OUTPUT_PARQUET)
    print(f"Wrote joined parquet: {OUTPUT_PARQUET}")


if __name__ == "__main__":
    main()
