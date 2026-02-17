"""Export a compact, ChatGPT-ready schema/structure summary from Backblaze B2.

This script streams object metadata from ``rclone lsf`` and aggregates dataset
structure without materializing a huge full manifest in memory.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import IO, Iterable


TABULAR_EXTENSIONS = {
    "parquet",
    "csv",
    "tsv",
    "jsonl",
    "json",
    "feather",
    "avro",
}


@dataclass
class BucketStats:
    files: int = 0
    bytes: int = 0
    examples: list[str] = field(default_factory=list)

    def add(self, file_path: str, file_bytes: int, max_examples: int) -> None:
        self.files += 1
        self.bytes += file_bytes
        if len(self.examples) < max_examples:
            self.examples.append(file_path)


def _format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def _top_n(
    stats: dict[str, BucketStats],
    n: int = 20,
) -> list[tuple[str, BucketStats]]:
    ranked = sorted(
        stats.items(),
        key=lambda item: (item[1].files, item[1].bytes),
        reverse=True,
    )
    return ranked[:n]


def _normalize_path(p: str) -> str:
    return p.strip().lstrip("/")


def _extension(file_path: str) -> str:
    name = Path(file_path).name
    suffixes = Path(name).suffixes
    if not suffixes:
        return "[no_extension]"
    if len(suffixes) >= 2 and suffixes[-1] == ".gz":
        return "".join(suffixes[-2:]).lstrip(".").lower()
    return suffixes[-1].lstrip(".").lower()


def _prefix_at_depth(file_path: str, depth: int) -> str:
    parts = [part for part in file_path.split("/") if part]
    if not parts:
        return "/"
    return "/".join(parts[:depth])


def _to_iso_utc(mod_time: str) -> str:
    raw = mod_time.strip()
    if not raw:
        return ""
    value = raw.replace(" ", "T")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _iter_rclone_lsf_lines(
    remote: str,
    config_path: Path | None,
) -> Iterable[str]:
    cmd = ["rclone"]
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    cmd.extend([
        "lsf",
        remote,
        "--recursive",
        "--files-only",
        "--format",
        "pst",
        "--separator",
        "\t",
    ])

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    if process.stdout is None:
        raise RuntimeError("Failed to read rclone stdout stream")

    try:
        for line in process.stdout:
            yield line.rstrip("\n")
    finally:
        process.stdout.close()

    stderr_text = process.stderr.read() if process.stderr is not None else ""
    if process.stderr is not None:
        process.stderr.close()

    return_code = process.wait()
    if return_code != 0:
        message = stderr_text.strip() or f"rclone exited with code {return_code}"
        raise RuntimeError(message)


def _iter_local_lsf_lines(local_root: Path) -> Iterable[str]:
    if not local_root.exists():
        raise RuntimeError(f"Local path not found: {local_root}")
    if not local_root.is_dir():
        raise RuntimeError(f"Local path must be a directory: {local_root}")

    resolved_root = local_root.resolve()
    for item in resolved_root.rglob("*"):
        if not item.is_file():
            continue
        try:
            stat = item.stat()
        except OSError:
            continue

        rel_path = item.relative_to(resolved_root).as_posix()
        modified_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        yield f"{rel_path}\t{stat.st_size}\t{modified_utc}"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_markdown(
    path: Path,
    payload: dict,
    top_n: int,
) -> None:
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

    lines: list[str] = []
    source_value = payload.get("source") or payload.get("remote") or ""
    lines.append("# B2 Dataset Structure Summary")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_utc']}")
    lines.append(f"- Source: `{source_value}`")
    lines.append(f"- Matched files: {payload['totals']['files']:,}")
    lines.append(f"- Total size: {payload['totals']['bytes']:,} bytes ({_format_bytes(payload['totals']['bytes'])})")
    lines.append(f"- Distinct extensions: {payload['totals']['distinct_extensions']:,}")
    lines.append(f"- Distinct prefixes (depth={payload['prefix_depth']}): {payload['totals']['distinct_prefixes']:,}")
    if payload.get("filters"):
        lines.append(f"- Path filters: `{', '.join(payload['filters'])}`")

    lines.append("")
    lines.append("## Time Coverage")
    lines.append("")
    lines.append(f"- Earliest modified UTC: {payload['modification_time_utc']['earliest']}")
    lines.append(f"- Latest modified UTC: {payload['modification_time_utc']['latest']}")

    lines.append("")
    lines.append("## Top Extensions")
    lines.append("")
    lines.append("| Extension | Files | Bytes |")
    lines.append("| --- | ---: | ---: |")
    extensions_payload = payload.get("extensions", {})
    if isinstance(extensions_payload, dict):
        ranked_ext = sorted(
            extensions_payload.items(),
            key=(
                lambda item: (
                    int(item[1].get("files", 0)) if isinstance(item[1], dict) else 0,
                    int(item[1].get("bytes", 0)) if isinstance(item[1], dict) else 0,
                )
            ),
            reverse=True,
        )
    else:
        ranked_ext = []
    for ext, stat in ranked_ext[:top_n]:
        files = int(stat.get("files", 0)) if isinstance(stat, dict) else 0
        size_bytes = int(stat.get("bytes", 0)) if isinstance(stat, dict) else 0
        lines.append(f"| `{ext}` | {files:,} | {size_bytes:,} |")

    lines.append("")
    lines.append(f"## Top Prefixes (Depth {payload['prefix_depth']})")
    lines.append("")
    lines.append("| Prefix | Files | Bytes |")
    lines.append("| --- | ---: | ---: |")
    prefixes_payload = payload.get("prefixes", {})
    if isinstance(prefixes_payload, dict):
        ranked_prefixes = sorted(
            prefixes_payload.items(),
            key=(
                lambda item: (
                    int(item[1].get("files", 0)) if isinstance(item[1], dict) else 0,
                    int(item[1].get("bytes", 0)) if isinstance(item[1], dict) else 0,
                )
            ),
            reverse=True,
        )
    else:
        ranked_prefixes = []
    for prefix, stat in ranked_prefixes[:top_n]:
        files = int(stat.get("files", 0)) if isinstance(stat, dict) else 0
        size_bytes = int(stat.get("bytes", 0)) if isinstance(stat, dict) else 0
        lines.append(f"| `{prefix}` | {files:,} | {size_bytes:,} |")

    lines.append("")
    lines.append("## Sample Tabular Paths")
    lines.append("")
    sample_tabular_paths = payload.get("sample_tabular_paths", [])
    if sample_tabular_paths:
        for index, sample in enumerate(sample_tabular_paths, start=1):
            lines.append(f"- Path {index}:")
            lines.append("")
            lines.append("  ```text")
            for wrapped in _wrapped_path_lines(sample):
                lines.append(f"  {wrapped}")
            lines.append("  ```")
            lines.append("")
    else:
        lines.append("- No tabular-like files found in sampled listing.")

    while lines and lines[-1] == "":
        lines.pop()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export compact dataset structure stats from an rclone remote or a local directory without creating a massive manifest file."
        )
    )
    parser.add_argument(
        "--markdown-from-json",
        default="",
        help=("Generate only markdown from an existing JSON summary path and skip source scanning"),
    )
    parser.add_argument(
        "--remote",
        default="",
        help=("rclone remote root to scan, e.g. wherewild-localdev-reader:wherewild-data (mutually exclusive with --local-root)"),
    )
    parser.add_argument(
        "--local-root",
        default="",
        help=("Local directory root to scan recursively (mutually exclusive with --remote)"),
    )
    parser.add_argument(
        "--config",
        default="docker/rclone.conf",
        help="Path to rclone config file (used only with --remote; default: docker/rclone.conf)",
    )
    parser.add_argument(
        "--filter-prefix",
        action="append",
        default=[],
        help="Keep only files whose relative path starts with this prefix (repeatable)",
    )
    parser.add_argument(
        "--prefix-depth",
        type=int,
        default=2,
        help="Directory depth to aggregate prefix stats (default: 2)",
    )
    parser.add_argument(
        "--example-limit",
        type=int,
        default=5,
        help="Max sample paths per extension/prefix bucket (default: 5)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="How many top rows to include in markdown tables (default: 20)",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10000,
        help="Print progress every N matched files (default: 10000)",
    )
    parser.add_argument(
        "--progress-seconds",
        type=float,
        default=15.0,
        help="Also print progress every N seconds (default: 15)",
    )
    parser.add_argument(
        "--json-out",
        default="b2_schema_summary.json",
        help="Output JSON summary path (default: b2_schema_summary.json)",
    )
    parser.add_argument(
        "--md-out",
        default="b2_schema_summary.md",
        help="Output Markdown summary path (default: b2_schema_summary.md)",
    )
    return parser


def main(stdout: IO[str] | None = None) -> int:
    out = stdout or sys.stdout
    parser = _build_parser()
    args = parser.parse_args()

    if args.prefix_depth <= 0:
        parser.error("--prefix-depth must be >= 1")
    if args.example_limit < 0:
        parser.error("--example-limit must be >= 0")
    if args.top_n <= 0:
        parser.error("--top-n must be >= 1")
    if args.progress_every <= 0:
        parser.error("--progress-every must be >= 1")
    if args.progress_seconds <= 0:
        parser.error("--progress-seconds must be > 0")

    markdown_from_json = Path(args.markdown_from_json) if args.markdown_from_json else None
    if markdown_from_json is not None:
        if not markdown_from_json.exists():
            parser.error(f"--markdown-from-json file not found: {markdown_from_json}")
        payload = json.loads(markdown_from_json.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            parser.error("--markdown-from-json must point to a JSON object")

        md_path = Path(args.md_out)
        _write_markdown(md_path, payload, top_n=args.top_n)
        print(f"Wrote {md_path} from {markdown_from_json}.", file=out)
        return 0

    remote = args.remote.strip()
    local_root = Path(args.local_root).expanduser() if args.local_root else None

    if not remote and local_root is None:
        parser.error("Provide either --remote or --local-root unless --markdown-from-json is provided")
    if remote and local_root is not None:
        parser.error("Use only one source: either --remote or --local-root")

    config_path = Path(args.config) if args.config else None
    filters = [_normalize_path(path) for path in args.filter_prefix if _normalize_path(path)]

    ext_stats: dict[str, BucketStats] = defaultdict(BucketStats)
    prefix_stats: dict[str, BucketStats] = defaultdict(BucketStats)
    tabular_samples: list[str] = []
    seen_tabular: set[str] = set()

    total_files = 0
    total_bytes = 0
    earliest_mod: str | None = None
    latest_mod: str | None = None
    start_monotonic = time.monotonic()
    last_progress_time = start_monotonic

    if local_root is not None:
        source_value = f"local:{local_root.resolve()}"
        print(
            f"Listing local directory: {local_root.resolve()}",
            file=out,
            flush=True,
        )
        line_iter = _iter_local_lsf_lines(local_root)
    else:
        source_value = remote
        print(
            f"Listing remote: {remote}",
            file=out,
            flush=True,
        )
        line_iter = _iter_rclone_lsf_lines(remote, config_path)

    for line in line_iter:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        file_path, raw_size, raw_mod = parts[0], parts[1], parts[2]
        file_path = _normalize_path(file_path)
        if not file_path:
            continue

        if filters and not any(file_path.startswith(prefix) for prefix in filters):
            continue

        try:
            file_bytes = int(raw_size)
        except ValueError:
            continue

        mod_utc = _to_iso_utc(raw_mod)

        total_files += 1
        total_bytes += file_bytes
        if mod_utc:
            if earliest_mod is None or mod_utc < earliest_mod:
                earliest_mod = mod_utc
            if latest_mod is None or mod_utc > latest_mod:
                latest_mod = mod_utc

        ext = _extension(file_path)
        ext_stats[ext].add(file_path, file_bytes, args.example_limit)

        prefix = _prefix_at_depth(file_path, args.prefix_depth)
        prefix_stats[prefix].add(file_path, file_bytes, args.example_limit)

        if ext in TABULAR_EXTENSIONS and file_path not in seen_tabular and len(tabular_samples) < 100:
            tabular_samples.append(file_path)
            seen_tabular.add(file_path)

        now_monotonic = time.monotonic()
        by_count = (total_files % args.progress_every) == 0
        by_time = now_monotonic - last_progress_time >= args.progress_seconds
        if by_count or by_time:
            elapsed = max(now_monotonic - start_monotonic, 1e-9)
            rate = total_files / elapsed
            print(
                (f"Scanned {total_files:,} files ({_format_bytes(total_bytes)}), rate {rate:,.1f} files/s"),
                file=out,
                flush=True,
            )
            last_progress_time = now_monotonic

    generated_utc = datetime.now(timezone.utc).isoformat()
    payload = {
        "generated_utc": generated_utc,
        "source": source_value,
        "remote": remote,
        "filters": filters,
        "prefix_depth": args.prefix_depth,
        "totals": {
            "files": total_files,
            "bytes": total_bytes,
            "distinct_extensions": len(ext_stats),
            "distinct_prefixes": len(prefix_stats),
        },
        "modification_time_utc": {
            "earliest": earliest_mod,
            "latest": latest_mod,
        },
        "extensions": {
            key: {
                "files": stat.files,
                "bytes": stat.bytes,
                "example_paths": stat.examples,
            }
            for key, stat in sorted(
                ext_stats.items(),
                key=lambda item: (item[1].files, item[1].bytes),
                reverse=True,
            )
        },
        "prefixes": {
            key: {
                "files": stat.files,
                "bytes": stat.bytes,
                "example_paths": stat.examples,
            }
            for key, stat in sorted(
                prefix_stats.items(),
                key=lambda item: (item[1].files, item[1].bytes),
                reverse=True,
            )
        },
        "tabular_extensions": sorted(TABULAR_EXTENSIONS),
        "sample_tabular_paths": tabular_samples,
    }

    json_path = Path(args.json_out)
    md_path = Path(args.md_out)
    _write_json(json_path, payload)

    _write_markdown(
        md_path,
        payload,
        top_n=args.top_n,
    )

    print(
        (f"Wrote {json_path} and {md_path}. Scanned {total_files:,} files ({_format_bytes(total_bytes)})."),
        file=out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
