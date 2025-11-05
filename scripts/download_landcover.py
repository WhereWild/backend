#!/usr/bin/env python3
"""
Grab the NLCD 2019 CONUS land cover mosaic and unpack it for reuse.

We keep the raw ZIP in raw/landcover/ alongside the extracted GeoTIFF so the
processing step can warp it into the 100 m grid without redownloading.

Data source: Multi-Resolution Land Characteristics (MRLC) Consortium.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Optional

import requests

# MRLC occasionally rehosts NLCD; try each endpoint until one responds.
ZIP_FILENAME = "NLCD_2019_Land_Cover_L48_20210604.zip"
LANDCOVER_URLS = (
    "https://prd-tnm.s3.amazonaws.com/StagedProducts/NLCD/data/land_cover/LC_2019_L48/NLCD_2019_Land_Cover_L48_20210604.zip",
    f"https://www.mrlc.gov/downloadfile/2?filenames={ZIP_FILENAME}",
    f"https://storage.googleapis.com/mrlc/{ZIP_FILENAME}",
    f"https://s3-us-west-2.amazonaws.com/mrlc/{ZIP_FILENAME}",
)
TIF_FILENAME = "nlcd_2019_land_cover_l48_20210604.tif"

CHUNK_SIZE = 1024 * 1024  # 1 MiB stream chunks keep memory usage tiny.


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download NLCD 2019 CONUS land cover (GeoTIFF) into raw/landcover/."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("raw"),
        help="Root raw data directory (default: raw).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("manifest.csv"),
        help="Manifest CSV for provenance logging (default: manifest.csv).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download the ZIP even if it already exists.",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Override download URL (useful when MRLC publishes a new endpoint).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without downloading or extracting.",
    )
    return parser.parse_args(argv)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def try_download(url: str, destination: Path, overwrite: bool) -> bool:
    """Attempt to stream the NLCD ZIP from a single endpoint."""
    if destination.exists() and not overwrite:
        print(f"ZIP already present -> {destination}")
        return False

    headers = {
        "User-Agent": "WhereWild/0.1 (+https://github.com/wherewild)",
        "Accept": "application/zip, application/octet-stream;q=0.9,*/*;q=0.8",
        "Referer": "https://www.mrlc.gov/",
    }
    try:
        with requests.get(url, stream=True, timeout=120, headers=headers, allow_redirects=True) as response:
            response.raise_for_status()
            temp_path = destination.with_suffix(destination.suffix + ".part")
            with temp_path.open("wb") as fp:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        fp.write(chunk)
            temp_path.replace(destination)
    except requests.RequestException as exc:
        print(f"  Attempt failed ({url}): {exc}")
        return False

    return True


def download_zip(destination: Path, overwrite: bool, preferred_url: Optional[str]) -> str:
    """Try each known endpoint until one succeeds; return the working URL."""
    urls = list(LANDCOVER_URLS)
    if preferred_url:
        urls.insert(0, preferred_url)

    for url in urls:
        print(f"Downloading NLCD land cover from {url}")
        if try_download(url, destination, overwrite):
            return url
    raise RuntimeError(
        "NLCD download failed for all known endpoints. "
        "Pass --url <direct_download_link> after manually verifying the path."
    )


def extract_zip(zip_path: Path, output_dir: Path) -> Path:
    """Unpack the GeoTIFF (overwrites existing files). Returns path to the .tif."""
    with zipfile.ZipFile(zip_path) as zf:
        # MRLC sometimes wraps files in a subdirectory, so we search for the .tif entry.
        tif_member: Optional[zipfile.ZipInfo] = None
        for member in zf.infolist():
            if member.filename.lower().endswith(".tif"):
                tif_member = member
                break
        if tif_member is None:
            raise FileNotFoundError(
                f"No GeoTIFF found inside {zip_path}. MRLC may have changed the archive layout."
            )

        print(f"Extracting {tif_member.filename} -> {output_dir}")
        zf.extract(member=tif_member, path=output_dir)
        extracted_path = output_dir / tif_member.filename
        if extracted_path.is_dir():
            raise IsADirectoryError(
                f"Expected a file but extracted directory {extracted_path}. Check the ZIP contents."
            )

        final_path = output_dir / TIF_FILENAME
        if extracted_path != final_path:
            extracted_path.replace(final_path)
    return output_dir / TIF_FILENAME


def append_manifest_row(manifest_path: Path, zip_path: Path, source_url: str) -> None:
    """Record the raw NLCD download in the manifest (skip when already present)."""
    if manifest_path is None:
        return

    fieldnames = ["dataset", "source_url", "license", "created_at", "notes"]
    manifest_exists = manifest_path.exists()
    existing_urls: Dict[str, bool] = {}

    if manifest_exists:
        with manifest_path.open(newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                if "source_url" in row:
                    existing_urls[row["source_url"]] = True

    record = {
        "dataset": "nlcd_2019_land_cover_raw",
        "source_url": source_url,
        "license": "Public Domain (USGS MRLC)",
        "created_at": dt.datetime.utcnow().date().isoformat(),
        "notes": f"Downloaded to {zip_path}",
    }

    if record["source_url"] in existing_urls:
        return

    with manifest_path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if not manifest_exists:
            writer.writeheader()
        writer.writerow(record)


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    landcover_dir = args.raw_dir / "landcover"
    ensure_dir(landcover_dir)
    zip_path = landcover_dir / ZIP_FILENAME

    if args.dry_run:
        status = "present" if zip_path.exists() else "missing"
        print(f"[dry-run] NLCD ZIP -> {zip_path} ({status})")
        return 0

    used_url = download_zip(zip_path, overwrite=args.overwrite, preferred_url=args.url)
    tif_path = extract_zip(zip_path, landcover_dir)
    print(f"GeoTIFF staged at {tif_path}")
    append_manifest_row(args.manifest, zip_path, used_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
