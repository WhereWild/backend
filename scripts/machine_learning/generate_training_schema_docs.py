"""Generate Markdown docs from the training schema JSON contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _render_markdown(schema: dict) -> str:
    """Render the schema contract payload as project Markdown documentation."""
    storage = schema.get("storage", {})
    notes = schema.get("notes", {})
    columns = schema.get("columns", [])
    schema_path_display = "schemas/training_observation.schema.json"

    lines: list[str] = []
    lines.append("# Training Observation Schema")
    lines.append("")
    lines.append("_This file is generated. Do not edit manually._")
    lines.append("")
    lines.append(f"Canonical contract: [{schema_path_display}](../{schema_path_display})")
    lines.append("")
    lines.append("## Storage")
    lines.append("")
    lines.append(f"- Format: `{storage.get('format', 'parquet')}`")

    partitions = storage.get("partition_by", [])
    if partitions:
        part_text = ", ".join(f"`{partition}`" for partition in partitions)
        lines.append(f"- Partition keys: {part_text}")

    compression = storage.get("compression")
    if compression:
        lines.append(f"- Compression: `{compression}`")

    partitioning_note = str(notes.get("partitioning", "")).strip()
    if partitioning_note:
        lines.append("")
        lines.append("## Partitioning Guidance")
        lines.append("")
        lines.append(f"- {partitioning_note}")

    sampling_note = str(notes.get("sampling_semantics", "")).strip()
    if sampling_note:
        lines.append("")
        lines.append("## Sampling Semantics")
        lines.append("")
        lines.append(f"- {sampling_note}")

    lines.append("")
    lines.append("## Feature Roles")
    lines.append("")
    lines.append("- `input`: can be fed into model tensors.")
    lines.append("- `metadata`: retained for joins, splits, QA, and bias auditing; excluded from model input.")

    lines.append("")
    lines.append("## Columns")
    lines.append("")
    lines.append("| Column | Type | Required | Feature Role | Description |")
    lines.append("| --- | --- | --- | --- | --- |")

    for column in columns:
        name = str(column.get("name", ""))
        parquet_type = str(column.get("parquet_type", ""))
        required = "yes" if bool(column.get("required", False)) else "no"
        feature_role = str(column.get("feature_role", "metadata"))
        description = str(column.get("description", "")).replace("\n", " ").strip()
        lines.append(f"| `{name}` | `{parquet_type}` | {required} | `{feature_role}` | {description} |")

    lines.append("")
    lines.append("## Validation")
    lines.append("")
    lines.append("Run the validator against a parquet file or dataset root:")
    lines.append("")
    lines.append("```bash")
    lines.append("uv run python scripts/machine_learning/validate_training_schema.py \\")
    lines.append("  --schema schemas/training_observation.schema.json \\")
    lines.append("  --data /path/to/training_observation")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    """CLI entrypoint for generating schema documentation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/training_observation.schema.json"),
        help="Path to the canonical schema JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/training_observation_schema.md"),
        help="Output markdown file path.",
    )
    args = parser.parse_args()

    schema_payload = json.loads(args.schema.read_text(encoding="utf-8"))
    markdown = _render_markdown(schema_payload)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
