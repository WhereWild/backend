#!/usr/bin/env python3
"""
Download USGS 3DEP 1 arc-second DEM tiles that intersect a grid.json bbox.

Usage:
  python download_dem.py --grid grid.json --raw-dir raw --workers 6
  python download_dem.py --grid grid.json --raw-dir raw --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

try:
    from pyproj import Transformer
except ModuleNotFoundError as exc:
    raise SystemExit("pyproj required. `pip install pyproj`") from exc

TNM_S3_BASE = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF/current"


def load_grid(grid_path: Path) -> Dict[str, float]:
    with grid_path.open() as fp:
        grid = json.load(fp)
    for key in ("bounds", "crs"):
        if key not in grid:
            raise KeyError(f"grid specification missing '{key}'")
    return grid


def bounds_to_latlon(bounds: List[float], crs: str) -> Tuple[float, float, float, float]:
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    xmin, ymin, xmax, ymax = bounds
    lon_min, lat_min = transformer.transform(xmin, ymin)
    lon_max, lat_max = transformer.transform(xmax, ymax)
    lon_left, lon_right = sorted([lon_min, lon_max])
    lat_bottom, lat_top = sorted([lat_min, lat_max])
    return lon_left, lat_bottom, lon_right, lat_top


def degree_tile_names(
    lon_left: float, lat_bottom: float, lon_right: float, lat_top: float
) -> Iterable[str]:
    lon_start = math.floor(lon_left)
    lon_stop = math.ceil(lon_right)
    lat_start = math.floor(lat_bottom)
    lat_stop = math.ceil(lat_top)
    for lat in range(lat_start, lat_stop):
        lat_prefix = "n" if lat >= 0 else "s"
        lat_digits = f"{abs(lat):02d}"
        for lon in range(lon_start, lon_stop):
            lon_prefix = "e" if lon >= 0 else "w"
            lon_digits = f"{abs(lon):03d}"
            yield f"{lat_prefix}{lat_digits}{lon_prefix}{lon_digits}"


def tile_url(tile_name: str) -> str:
    return f"{TNM_S3_BASE}/{tile_name}/USGS_1_{tile_name}.tif"


def download_file(url: str, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return False
    temp_path = destination.with_suffix(destination.suffix + ".part")
    try:
        with urlopen(url) as response, temp_path.open("wb") as out_fp:
            chunk = response.read(1024 * 1024)
            while chunk:
                out_fp.write(chunk)
                chunk = response.read(1024 * 1024)
    except HTTPError as err:
        if err.code == 404:
            print(f"Warning: missing tile (404) for {url}", file=sys.stderr)
            return False
        raise RuntimeError(f"HTTP error {err.code} for {url}") from err
    except URLError as err:
        raise RuntimeError(f"Failed to reach {url}: {err.reason}") from err
    else:
        temp_path.replace(destination)
    return True


def run(grid_path: Path, raw_dir: Path, dry_run: bool, workers: int) -> None:
    grid = load_grid(grid_path)
    lon_left, lat_bottom, lon_right, lat_top = bounds_to_latlon(grid["bounds"], grid["crs"])
    tiles = sorted(degree_tile_names(lon_left, lat_bottom, lon_right, lat_top))

    print("Grid bounds (lat/lon):")
    print("  Lon:", lon_left, "→", lon_right)
    print("  Lat:", lat_bottom, "→", lat_top)
    print("Tiles to fetch:", len(tiles))
    print()

    if dry_run:
        for tile in tiles:
            dest = raw_dir / "dem" / f"{tile}.tif"
            status = "exists" if dest.exists() else "pending"
            print(f"[dry-run] {tile} -> {dest} ({status})")
        return

    to_fetch: List[Tuple[str, str, Path]] = []
    for tile in tiles:
        url = tile_url(tile)
        dest = raw_dir / "dem" / f"{tile}.tif"
        if dest.exists():
            continue
        to_fetch.append((tile, url, dest))

    total = len(to_fetch)
    workers = max(1, workers)
    if total == 0:
        print("All tiles already downloaded.")
        return

    print(f"Downloading {total} remaining tiles ...")
    for idx, (tile, _, dest) in enumerate(to_fetch, start=1):
        print(f"[queue {idx}/{total}] {tile} -> {dest}")

    def worker(task: Tuple[str, str, Path]) -> None:
        tile, url, dest = task
        print(f"Downloading {tile} ...")
        download_file(url, dest)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for future in as_completed(executor.submit(worker, t) for t in to_fetch):
            try:
                future.result()
            except Exception as exc:
                print(f"Error downloading tile: {exc}", file=sys.stderr)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download USGS 3DEP 1 arc-second DEM tiles intersecting grid.json.")
    parser.add_argument("--grid", type=Path, required=True, help="Path to grid.json")
    parser.add_argument("--raw-dir", type=Path, required=True, help="Root raw data directory")
    parser.add_argument("--dry-run", action="store_true", help="List tiles without downloading.")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent download workers (default: 1).")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        run(args.grid, args.raw_dir, args.dry_run, args.workers)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
