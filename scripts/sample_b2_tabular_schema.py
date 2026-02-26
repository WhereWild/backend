"""Sample tabular files from B2 and infer compact schema/profile metadata.

Profile mode reads candidate tabular paths from ``b2_schema_summary.json``
(produced by ``scripts/export_b2_schema.py``), downloads only bounded-size
files, and writes tabular schema reports.

Markdown-only mode regenerates markdown from an existing tabular-schema JSON
output produced by this script.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import tempfile
import subprocess
import sys
from typing import IO

import pandas as pd
import pyarrow.parquet as pq


TABULAR_EXTENSIONS = {
    "parquet",
    "csv",
    "tsv",
    "jsonl",
    "json",
}


@dataclass
class FileSchemaResult:
    path: str
    extension: str
    status: str
    size_bytes: int | None = None
    rows_sampled: int | None = None
    columns: list[dict] | None = None
    notes: str | None = None
    error: str | None = None


def _run_rclone(
    args: list[str],
    config_path: Path | None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    cmd = ["rclone"]
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    cmd.extend(args)
    return subprocess.run(
        cmd,
        check=False,
        capture_output=capture_output,
        text=True,
    )


def _join_remote(remote: str, rel_path: str) -> str:
    root = remote.rstrip("/")
    rel = rel_path.lstrip("/")
    if not rel:
        return root
    return f"{root}/{rel}"


def _extension(file_path: str) -> str:
    suffixes = Path(file_path).suffixes
    if not suffixes:
        return "[no_extension]"
    if len(suffixes) >= 2 and suffixes[-1] == ".gz":
        return "".join(suffixes[-2:]).lstrip(".").lower()
    return suffixes[-1].lstrip(".").lower()


def _load_summary_paths(summary_json_path: Path) -> list[str]:
    payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return []

    paths: list[str] = []
    sample_paths = payload.get("sample_tabular_paths")
    if isinstance(sample_paths, list):
        for value in sample_paths:
            if isinstance(value, str):
                cleaned = value.strip().lstrip("/")
                if cleaned:
                    paths.append(cleaned)

    extensions = payload.get("extensions")
    if isinstance(extensions, dict):
        for ext_payload in extensions.values():
            if not isinstance(ext_payload, dict):
                continue
            examples = ext_payload.get("example_paths")
            if not isinstance(examples, list):
                continue
            for example in examples:
                if isinstance(example, str):
                    cleaned = example.strip().lstrip("/")
                    if cleaned:
                        paths.append(cleaned)

    deduped: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def _fetch_object_size(
    remote_obj: str,
    config_path: Path | None,
) -> int | None:
    result = _run_rclone(["lsjson", remote_obj], config_path=config_path)
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    if not isinstance(first, dict):
        return None
    size = first.get("Size")
    if isinstance(size, int):
        return size
    return None


def _download_object(
    remote_obj: str,
    local_path: Path,
    config_path: Path | None,
) -> tuple[bool, str | None]:
    result = _run_rclone(
        ["copyto", remote_obj, str(local_path)],
        config_path=config_path,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return False, stderr or "rclone copyto failed"
    return True, None


def _frame_columns(df: pd.DataFrame) -> list[dict]:
    columns: list[dict] = []
    for name in df.columns:
        series = df[name]
        non_null = series.dropna()
        sample = None
        if not non_null.empty:
            sample = str(non_null.iloc[0])
        columns.append({
            "name": str(name),
            "dtype": str(series.dtype),
            "null_pct": float(series.isna().mean()),
            "distinct_sample": int(series.nunique(dropna=True)),
            "sample_value": sample,
        })
    return columns


def _infer_from_parquet(local_path: Path) -> tuple[list[dict], int | None]:
    parquet = pq.ParquetFile(local_path)
    schema = parquet.schema_arrow
    columns = [
        {
            "name": field.name,
            "dtype": str(field.type),
            "null_pct": None,
            "distinct_sample": None,
            "sample_value": None,
        }
        for field in schema
    ]
    rows = parquet.metadata.num_rows if parquet.metadata is not None else None
    return columns, rows


def _infer_from_csv(
    local_path: Path,
    rows: int,
    sep: str,
) -> tuple[list[dict], int]:
    frame = pd.read_csv(local_path, nrows=rows, sep=sep)
    return _frame_columns(frame), int(len(frame))


def _infer_from_jsonl(local_path: Path, rows: int) -> tuple[list[dict], int]:
    frame = pd.read_json(local_path, lines=True, nrows=rows)
    return _frame_columns(frame), int(len(frame))


def _infer_from_json(local_path: Path, rows: int) -> tuple[list[dict], int]:
    with local_path.open("r", encoding="utf-8") as file_obj:
        raw = json.load(file_obj)

    if isinstance(raw, list):
        records = [item for item in raw if isinstance(item, dict)][:rows]
    elif isinstance(raw, dict):
        records = [raw]
    else:
        raise ValueError("JSON is neither a dict nor list[dict]")

    frame = pd.json_normalize(records)
    return _frame_columns(frame), int(len(frame))


def _infer_schema(
    local_path: Path,
    extension: str,
    sample_rows: int,
) -> tuple[list[dict], int | None]:
    if extension == "parquet":
        return _infer_from_parquet(local_path)
    if extension == "csv":
        return _infer_from_csv(local_path, rows=sample_rows, sep=",")
    if extension == "tsv":
        return _infer_from_csv(local_path, rows=sample_rows, sep="\t")
    if extension == "jsonl":
        return _infer_from_jsonl(local_path, rows=sample_rows)
    if extension == "json":
        return _infer_from_json(local_path, rows=sample_rows)
    raise ValueError(f"Unsupported tabular extension: {extension}")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_markdown(path: Path, payload: dict) -> None:
    def _wrapped_path_lines(path_text: str, width: int = 100) -> list[str]:
        parts = [part for part in path_text.split("/") if part]
        if not parts:
            return [path_text]

        wrapped: list[str] = []
        current = parts[0]
        for part in parts[1:]:
            candidate = f"{current}/{part}"
            if len(candidate) <= width:
                current = candidate
            else:
                wrapped.append(f"{current}/")
                current = part
        wrapped.append(current)
        return wrapped

    def _truncate_markdown_text(value: str, max_len: int = 30) -> str:
        if len(value) <= max_len:
            return value
        if max_len <= 1:
            return value[:max_len]
        return f"{value[: max_len - 1]}…"

    lines: list[str] = []
    source_value = payload.get("source") or payload.get("remote") or ""
    lines.append("# B2 Tabular Schema Sample")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_utc']}")
    lines.append(f"- Source: `{source_value}`")
    lines.append(f"- Candidates considered: {payload['totals']['candidates_considered']:,}")
    lines.append(f"- Profiles generated: {payload['totals']['profiles_generated']:,}")
    lines.append(f"- Skipped files: {payload['totals']['skipped']:,}")
    lines.append(f"- Failed files: {payload['totals']['failed']:,}")
    lines.append("")
    lines.append("## Profiled Files")
    lines.append("")

    for index, item in enumerate(payload["results"], start=1):
        status = item.get("status")
        p = item.get("path")
        ext = item.get("extension")
        lines.append(f"### File {index}")
        lines.append("")
        lines.append("- Path:")
        lines.append("")
        lines.append("  ```text")
        for wrapped in _wrapped_path_lines(p):
            lines.append(f"  {wrapped}")
        lines.append("  ```")
        lines.append("")
        lines.append(f"- Status: `{status}`")
        lines.append(f"- Extension: `{ext}`")
        if item.get("size_bytes") is not None:
            lines.append(f"- Size bytes: {item['size_bytes']:,}")
        if item.get("rows_sampled") is not None:
            lines.append(f"- Rows sampled: {item['rows_sampled']:,}")
        if item.get("notes"):
            lines.append(f"- Notes: {item['notes']}")
        if item.get("error"):
            lines.append(f"- Error: {item['error']}")

        columns = item.get("columns") or []
        if columns:
            lines.append("")
            lines.append("| Column | Dtype | Null% | Distinct(sample) |")
            lines.append("| --- | --- | ---: | ---: |")
            for column in columns:
                null_pct = column.get("null_pct")
                null_text = "n/a" if null_pct is None else f"{null_pct * 100:.2f}"
                distinct = column.get("distinct_sample")
                distinct_text = "n/a" if distinct is None else f"{distinct:,}"
                dtype_text = _truncate_markdown_text(str(column["dtype"]))
                lines.append(f"| `{column['name']}` | `{dtype_text}` | {null_text} | {distinct_text} |")
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Profile tabular files referenced by b2_schema_summary.json, or regenerate markdown "
            "from an existing tabular-schema JSON report."
        )
    )
    parser.add_argument(
        "--markdown-only",
        action="store_true",
        help=(
            "Regenerate markdown only and skip profiling/rclone. Uses --markdown-input if provided, "
            "otherwise defaults to --json-out"
        ),
    )
    parser.add_argument(
        "--markdown-input",
        default="",
        help=("Path to an existing tabular-schema JSON produced by this script (used in --markdown-only mode)"),
    )
    parser.add_argument(
        "--markdown-from-json",
        nargs="?",
        const="__USE_JSON_OUT__",
        default="",
        help=("Deprecated alias for --markdown-input; retained for compatibility"),
    )
    parser.add_argument(
        "--remote",
        default="",
        help=("rclone remote root for profile mode, e.g. wherewild-localdev-reader:wherewild-data"),
    )
    parser.add_argument(
        "--local-root",
        default="",
        help=("Local directory root for profile mode (mutually exclusive with --remote)"),
    )
    parser.add_argument(
        "--config",
        default="docker/rclone.conf",
        help="Path to rclone config file (used in profile mode; default: docker/rclone.conf)",
    )
    parser.add_argument(
        "--summary-json",
        default="b2_schema_summary.json",
        help=("Input summary JSON from export_b2_schema.py (used in profile mode; default: b2_schema_summary.json)"),
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=20,
        help="Maximum number of files to profile (default: 20)",
    )
    parser.add_argument(
        "--sample-strategy",
        choices=["head", "random"],
        default="head",
        help="How to choose files from candidates: head (default) or random",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed used when --sample-strategy=random (default: 42)",
    )
    parser.add_argument(
        "--max-download-bytes",
        type=int,
        default=64 * 1024 * 1024,
        help=("Skip files bigger than this many bytes to avoid heavy transfers (default: 67108864)"),
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=50000,
        help="Rows to sample for row-based formats (default: 50000)",
    )
    parser.add_argument(
        "--json-out",
        default="b2_tabular_schema.json",
        help="Output JSON report path (default: b2_tabular_schema.json)",
    )
    parser.add_argument(
        "--md-out",
        default="b2_tabular_schema.md",
        help="Output Markdown report path (default: b2_tabular_schema.md)",
    )
    return parser


def main(stdout: IO[str] | None = None) -> int:
    out = stdout or sys.stdout
    parser = _build_parser()
    args = parser.parse_args()

    if args.max_files <= 0:
        parser.error("--max-files must be >= 1")
    if args.max_download_bytes <= 0:
        parser.error("--max-download-bytes must be >= 1")
    if args.sample_rows <= 0:
        parser.error("--sample-rows must be >= 1")

    legacy_markdown_input = args.markdown_from_json
    if legacy_markdown_input == "__USE_JSON_OUT__":
        legacy_markdown_input = args.json_out

    markdown_input_value = args.markdown_input.strip() or str(legacy_markdown_input).strip()
    if args.markdown_only and not markdown_input_value:
        markdown_input_value = args.json_out

    markdown_input = Path(markdown_input_value) if markdown_input_value else None
    if markdown_input is not None:
        if not markdown_input.exists():
            parser.error(f"Markdown input JSON file not found: {markdown_input}")
        payload = json.loads(markdown_input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            parser.error("Markdown input must point to a JSON object")

        md_out = Path(args.md_out)
        _write_markdown(md_out, payload)
        print(f"Wrote {md_out} from {markdown_input}.", file=out)
        return 0

    remote = args.remote.strip()
    local_root = Path(args.local_root).expanduser() if args.local_root else None

    if not remote and local_root is None:
        parser.error("Provide either --remote or --local-root unless markdown-only mode is used")
    if remote and local_root is not None:
        parser.error("Use only one profile source: either --remote or --local-root")
    if local_root is not None:
        if not local_root.exists():
            parser.error(f"--local-root not found: {local_root}")
        if not local_root.is_dir():
            parser.error(f"--local-root must be a directory: {local_root}")

    summary_path = Path(args.summary_json)
    if not summary_path.exists():
        parser.error(f"summary file not found: {summary_path}")

    config_path = Path(args.config) if args.config else None
    if local_root is not None:
        source_value = f"local:{local_root.resolve()}"
    else:
        source_value = remote

    candidate_paths = _load_summary_paths(summary_path)
    filtered = [path for path in candidate_paths if _extension(path) in TABULAR_EXTENSIONS]
    if args.sample_strategy == "random":
        rng = random.Random(args.random_seed)
        if len(filtered) <= args.max_files:
            selected = list(filtered)
            rng.shuffle(selected)
        else:
            selected = rng.sample(filtered, args.max_files)
    else:
        selected = filtered[: args.max_files]

    results: list[FileSchemaResult] = []
    profiles_generated = 0
    skipped = 0
    failed = 0

    if local_root is not None:
        for index, rel_path in enumerate(selected, start=1):
            ext = _extension(rel_path)
            print(
                f"[{index}/{len(selected)}] Profiling {rel_path}",
                file=out,
            )

            local_path = local_root / rel_path
            if not local_path.exists() or not local_path.is_file():
                results.append(
                    FileSchemaResult(
                        path=rel_path,
                        extension=ext,
                        status="failed",
                        error=(f"Local file not found under --local-root: {local_path}"),
                    )
                )
                failed += 1
                continue

            file_size = local_path.stat().st_size
            if file_size > args.max_download_bytes:
                results.append(
                    FileSchemaResult(
                        path=rel_path,
                        extension=ext,
                        status="skipped",
                        size_bytes=file_size,
                        notes=("File exceeds --max-download-bytes; increase limit to include"),
                    )
                )
                skipped += 1
                continue

            try:
                columns, rows_sampled = _infer_schema(
                    local_path,
                    extension=ext,
                    sample_rows=args.sample_rows,
                )
                results.append(
                    FileSchemaResult(
                        path=rel_path,
                        extension=ext,
                        status="profiled",
                        size_bytes=file_size,
                        rows_sampled=rows_sampled,
                        columns=columns,
                    )
                )
                profiles_generated += 1
            except Exception as exc:  # noqa: BLE001
                results.append(
                    FileSchemaResult(
                        path=rel_path,
                        extension=ext,
                        status="failed",
                        size_bytes=file_size,
                        error=str(exc),
                    )
                )
                failed += 1
    else:
        with tempfile.TemporaryDirectory(prefix="ww-b2-schema-") as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)

            for index, rel_path in enumerate(selected, start=1):
                ext = _extension(rel_path)
                remote_obj = _join_remote(remote, rel_path)
                print(
                    f"[{index}/{len(selected)}] Profiling {rel_path}",
                    file=out,
                )

                file_size = _fetch_object_size(remote_obj, config_path)
                if file_size is not None and file_size > args.max_download_bytes:
                    results.append(
                        FileSchemaResult(
                            path=rel_path,
                            extension=ext,
                            status="skipped",
                            size_bytes=file_size,
                            notes=("File exceeds --max-download-bytes; increase limit to include"),
                        )
                    )
                    skipped += 1
                    continue

                local_path = tmp_dir / f"sample_{index}_{Path(rel_path).name}"
                ok, download_error = _download_object(
                    remote_obj,
                    local_path,
                    config_path,
                )
                if not ok:
                    results.append(
                        FileSchemaResult(
                            path=rel_path,
                            extension=ext,
                            status="failed",
                            size_bytes=file_size,
                            error=download_error,
                        )
                    )
                    failed += 1
                    continue

                try:
                    columns, rows_sampled = _infer_schema(
                        local_path,
                        extension=ext,
                        sample_rows=args.sample_rows,
                    )
                    results.append(
                        FileSchemaResult(
                            path=rel_path,
                            extension=ext,
                            status="profiled",
                            size_bytes=file_size,
                            rows_sampled=rows_sampled,
                            columns=columns,
                        )
                    )
                    profiles_generated += 1
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        FileSchemaResult(
                            path=rel_path,
                            extension=ext,
                            status="failed",
                            size_bytes=file_size,
                            error=str(exc),
                        )
                    )
                    failed += 1

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": source_value,
        "remote": remote,
        "source_summary_json": str(summary_path),
        "limits": {
            "max_files": args.max_files,
            "sample_strategy": args.sample_strategy,
            "random_seed": args.random_seed,
            "max_download_bytes": args.max_download_bytes,
            "sample_rows": args.sample_rows,
        },
        "totals": {
            "candidates_considered": len(selected),
            "profiles_generated": profiles_generated,
            "skipped": skipped,
            "failed": failed,
        },
        "results": [result.__dict__ for result in results],
    }

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    _write_json(json_out, payload)
    _write_markdown(md_out, payload)

    print(
        f"Wrote {json_out} and {md_out}. Profiled {profiles_generated}/{len(selected)} files.",
        file=out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
