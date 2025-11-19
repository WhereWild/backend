#!/usr/bin/env python3
"""
Catalog-driven bootstrap: download datasets and reproject rasters into the canonical grid.

Config: scripts/data_catalog.json
Env overrides:
  RAW_ROOT [raw]
  PROCESSED_ROOT [processed]
  CATALOG [scripts/data_catalog.json]
  MAX_CONCURRENT_FETCHES [4]
  MAX_CONCURRENT_WARPS [1]
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import zipfile
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

# Tweakable knobs (override via env as noted above)
MAX_CONCURRENT_FETCHES = int(os.getenv("MAX_CONCURRENT_FETCHES", "4"))
MAX_CONCURRENT_WARPS = int(os.getenv("MAX_CONCURRENT_WARPS", "1"))
def run(cmd: List[str]) -> None:
    msg = "> " + " ".join(cmd)
    print(msg)
    subprocess.run(cmd, check=True)


def to_workspace_path(path: Path, repo_root: Path) -> str:
    """Map a host path under the repo to the /workspace mount used by docker compose."""
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return path.as_posix()
    return f"/workspace/{rel.as_posix()}"


def load_catalog(path: Path) -> Dict[str, Any]:
    with path.open() as fp:
        return json.load(fp)


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".part")
    try:
        with urlopen(url) as resp, temp.open("wb") as out:
            chunk = resp.read(1024 * 1024)
            while chunk:
                out.write(chunk)
                chunk = resp.read(1024 * 1024)
    except HTTPError as exc:
        raise RuntimeError(f"HTTP error {exc.code} for {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error for {url}: {exc.reason}") from exc
    else:
        temp.replace(destination)


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)


def fetch_direct_zip(entry: Dict[str, Any], raw_root: Path) -> Path:
    url = entry["fetch"]["url"]
    subdir = entry["fetch"].get("raw_subdir", entry["name"])
    dest_dir = raw_root / subdir
    zip_path = dest_dir / Path(url).name
    if not zip_path.exists():
        print(f"Downloading {entry['name']} from {url}")
        download_file(url, zip_path)
    else:
        print(f"{zip_path} already exists; skipping download")
    if entry["fetch"].get("extract", True):
        print(f"Extracting {zip_path} -> {dest_dir}")
        extract_zip(zip_path, dest_dir)
    return dest_dir


def fetch_grid_tiles(entry: Dict[str, Any], raw_root: Path, repo_root: Path) -> Path:
    grid = entry["fetch"].get("grid", "grid.json")
    workers = str(entry["fetch"].get("workers", 4))
    raw_dir = to_workspace_path(raw_root, repo_root)
    grid_path = to_workspace_path(repo_root / grid, repo_root)
    print(f"Downloading tiles for {entry['name']} with {workers} workers")
    run(
        [
            "docker",
            "compose",
            "run",
            "-T",
            "--rm",
            "gdal",
            "python",
            "download_dem.py",
            "--grid",
            grid_path,
            "--raw-dir",
            raw_dir,
            "--workers",
            workers,
        ]
    )
    return raw_root / entry["fetch"].get("raw_subdir", "dem")


def clean_partials(raw_dir: Path) -> None:
    for part in raw_dir.glob("*.part"):
        part.unlink(missing_ok=True)


def process_raster(entry: Dict[str, Any], raw_dir: Path, processed_root: Path, grid: str, repo_root: Path) -> None:
    resampling = entry["process"].get("resampling", "bilinear")
    overview_levels = [str(level) for level in entry["process"].get("overview_levels", [2, 4, 8, 16, 32])]
    pixel_size = entry["process"].get("pixel_size")
    rename_map = entry["process"].get("rename_map", {})

    processed_root.mkdir(parents=True, exist_ok=True)
    grid_path = to_workspace_path(repo_root / grid, repo_root) if grid else to_workspace_path(repo_root / "grid.json", repo_root)
    tmp_grid: Path | None = None
    if pixel_size is not None:
        base_grid_path = Path(grid) if grid else Path("grid.json")
        with base_grid_path.open() as fp:
            grid_spec = json.load(fp)
        grid_spec["pixel_size"] = pixel_size
        if "dtype" in entry["process"]:
            grid_spec["dtype"] = entry["process"]["dtype"]
        if "nodata" in entry["process"]:
            grid_spec["nodata"] = entry["process"]["nodata"]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", dir=repo_root)
        tmp_grid = Path(tmp.name)
        json.dump(grid_spec, tmp)
        tmp.close()
        grid_path = to_workspace_path(tmp_grid, repo_root)

    try:
        if entry["fetch"]["type"] == "grid_tiles":
            dst = processed_root / f"{entry['name']}_cog.tif"
            if dst.exists():
                print(f"Destination exists ({dst}); skipping.")
                return
            print(f"Reprojecting {entry['name']} -> {dst}")
            run(
                [
                    "docker",
                    "compose",
                    "run",
                    "-T",
                    "--rm",
                    "gdal",
                    "python",
                    "reproject_gis.py",
                    "--src-dir",
                    to_workspace_path(raw_dir / entry["fetch"].get("raw_subdir", ""), repo_root),
                    "--dst",
                    to_workspace_path(dst, repo_root),
                    "--grid",
                    grid_path,
                    "--resampling",
                    resampling,
                    "--overview-levels",
                    *overview_levels,
                ]
            )
        else:
            tifs = sorted(raw_dir.rglob("*.tif"))
            if not tifs:
                print(f"No TIFFs found under {raw_dir} for {entry['name']}", file=sys.stderr)
                return
            for tif in tifs:
                stem = tif.stem
                idx = ""
                for part in stem.split("_"):
                    if part.isdigit():
                        idx = part
                friendly = rename_map.get(idx, stem)
                dst = processed_root / f"{entry['name']}_{friendly}_cog.tif"
                if dst.exists():
                    print(f"{dst.name} exists; skipping.")
                    continue
                print(f"Reprojecting {tif.name} -> {dst.name}")
                run(
                    [
                        "docker",
                        "compose",
                        "run",
                        "-T",
                        "--rm",
                        "gdal",
                        "python",
                        "reproject_gis.py",
                        "--src-files",
                        to_workspace_path(tif, repo_root),
                        "--dst",
                        to_workspace_path(dst, repo_root),
                        "--grid",
                        grid_path,
                        "--resampling",
                        resampling,
                        "--overview-levels",
                        *overview_levels,
                    ]
                )
    finally:
        if tmp_grid is not None:
            tmp_grid.unlink(missing_ok=True)


def main(argv: List[str]) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    raw_root = repo_root / os.getenv("RAW_ROOT", "raw")
    processed_root = repo_root / os.getenv("PROCESSED_ROOT", "processed")
    catalog_path = Path(os.getenv("CATALOG", "scripts/data_catalog.json"))

    catalog = load_catalog(catalog_path)

    def fetch(entry: Dict[str, Any]) -> Tuple[Dict[str, Any], Path]:
        print(f"==> {entry['name']}")
        fetch_type = entry["fetch"]["type"]
        if fetch_type == "direct_zip":
            raw_dest = fetch_direct_zip(entry, raw_root)
        elif fetch_type == "grid_tiles":
            raw_dest = fetch_grid_tiles(entry, raw_root, repo_root)
        else:
            raise ValueError(f"Unknown fetch type '{fetch_type}' for {entry['name']}")
        clean_partials(raw_dest)
        return entry, raw_dest

    def project(entry: Dict[str, Any], raw_dest: Path) -> None:
        if entry.get("kind") == "raster":
            process_raster(
                entry,
                raw_dest,
                processed_root,
                entry["process"].get("grid", entry["fetch"].get("grid", "grid.json")),
                repo_root,
            )
        else:
            print(f"Skipping processing for non-raster dataset {entry['name']}")
        print()

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WARPS) as warp_pool:
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_FETCHES) as fetch_pool:
            futures = {fetch_pool.submit(fetch, entry): entry for entry in catalog.get("datasets", [])}
            for fut in as_completed(futures):
                try:
                    entry, raw_dest = fut.result()
                except Exception as exc:
                    print(f"Fetch failed: {exc}", file=sys.stderr)
                    continue
                warp_pool.submit(project, entry, raw_dest)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
