#!/usr/bin/env python3
"""
Download iNaturalist observations for a given species and align them with the
WhereWild 100 m EPSG:5070 grid.

Workflow:
  1. Fetch observations from the iNaturalist REST API with configurable filters.
  2. Cache the raw JSON records (newline-delimited, gzipped) under raw/observations.
  3. Project observation coordinates into the canonical grid and emit a presence
     table suitable for downstream modeling.
  4. Append provenance information to manifest.csv.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import requests
from pyproj import CRS, Transformer


INAT_OBSERVATIONS_URL = "https://api.inaturalist.org/v1/observations"
MAX_PER_PAGE = 200


def load_grid(path: Path) -> Dict[str, Any]:
    """Load the grid definition so we can project lon/lat into grid cells."""
    with path.open() as fp:
        return json.load(fp)


def compute_dimensions(bounds: Sequence[float], pixel_size: float) -> Tuple[int, int]:
    """Reuse the width/height math so the grid projector knows the valid index range."""
    xmin, ymin, xmax, ymax = bounds
    width = int(round((xmax - xmin) / pixel_size))
    height = int(round((ymax - ymin) / pixel_size))
    if width <= 0 or height <= 0:
        raise ValueError("grid bounds / pixel size yield non-positive dimensions.")
    return width, height


@dataclass(frozen=True)
class GridIndex:
    column: int
    row: int

    def cell_id(self) -> str:
        """Combine column/row into a stable string for downstream joins."""
        return f"{self.column}_{self.row}"


class GridProjector:
    """Project WGS84 coordinates into the canonical grid and compute cell indices."""

    def __init__(self, grid: Dict[str, Any]) -> None:
        bounds = grid["bounds"]
        pixel_size = float(grid["pixel_size"])
        self._xmin, self._ymin, self._xmax, self._ymax = bounds
        self._pixel_size = pixel_size
        self._width, self._height = compute_dimensions(bounds, pixel_size)
        crs = CRS.from_user_input(grid["crs"])
        self._transformer = Transformer.from_crs(4326, crs, always_xy=True)

    def project(self, longitude: float, latitude: float) -> Optional[Tuple[float, float, GridIndex]]:
        """Return projected x/y plus grid indices, or None when the point lives outside the grid."""
        x, y = self._transformer.transform(longitude, latitude)
        if not (self._xmin <= x <= self._xmax and self._ymin <= y <= self._ymax):
            return None
        column = int(math.floor((x - self._xmin) / self._pixel_size))
        row = int(math.floor((self._ymax - y) / self._pixel_size))
        if column < 0 or column >= self._width or row < 0 or row >= self._height:
            return None
        return x, y, GridIndex(column=column, row=row)


def chunked_observations(
    session: requests.Session,
    params: Dict[str, Any],
    per_page: int,
    max_records: Optional[int],
    sleep_seconds: float,
) -> Iterator[Dict[str, Any]]:
    """Paginate through the iNat API, yielding raw observation dicts."""
    total_fetched = 0
    page = 1
    while True:
        page_params = {**params, "page": page, "per_page": per_page}
        response = session.get(INAT_OBSERVATIONS_URL, params=page_params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results", [])
        if not results:
            break
        for item in results:
            yield item
            total_fetched += 1
            if max_records is not None and total_fetched >= max_records:
                return
        page += 1
        if max_records is not None and total_fetched >= max_records:
            break
        # Short pause between pages keeps us friendly with the API rate limits.
        time.sleep(sleep_seconds)


def ensure_output_paths(raw_dir: Path, processed_dir: Path) -> None:
    """Make sure the nested raw/processed folders exist before we start writing."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)


def append_manifest(manifest_path: Path, rows: Sequence[Dict[str, str]]) -> None:
    """Upsert observation metadata into the shared manifest."""
    if manifest_path is None:
        return
    fieldnames = ["dataset", "source_url", "license", "created_at", "notes"]
    manifest_exists = manifest_path.exists()
    existing_urls: set[str] = set()
    if manifest_exists:
        with manifest_path.open(newline="") as fp:
            reader = csv.DictReader(fp)
            existing_urls = {row["source_url"] for row in reader if "source_url" in row}

    with manifest_path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if not manifest_exists:
            writer.writeheader()
        for row in rows:
            if row["source_url"] in existing_urls:
                continue
            # Rows are tiny; writing one at a time keeps the code straightforward.
            writer.writerow(row)


def extract_presence_row(
    obs: Dict[str, Any],
    projector: GridProjector,
) -> Optional[Dict[str, Any]]:
    """Convert an iNaturalist observation into one grid-aligned presence row."""
    geojson = obs.get("geojson") or {}
    coords = geojson.get("coordinates")
    if not coords or len(coords) != 2:
        return None
    longitude, latitude = coords
    projected = projector.project(longitude, latitude)
    if projected is None:
        return None

    x, y, grid_index = projected
    observed_details = obs.get("observed_on_details") or {}
    observed_at = (
        observed_details.get("datetime")
        or obs.get("time_observed_at")
        or obs.get("observed_on")
    )

    return {
        "observation_id": obs["id"],
        "species_id": obs.get("taxon_id"),
        "observed_at": observed_at,
        "latitude": latitude,
        "longitude": longitude,
        "positional_accuracy_m": obs.get("positional_accuracy"),
        "quality_grade": obs.get("quality_grade"),
        "individual_count": obs.get("individual_count"),
        "is_captive": obs.get("captive"),
        "grid_x": grid_index.column,
        "grid_y": grid_index.row,
        "cell_id": grid_index.cell_id(),
        "projected_x": x,
        "projected_y": y,
        "presence": 1,
    }


def build_query_params(args: argparse.Namespace) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "taxon_id": args.species_id,
        "order": "desc",
        "order_by": "created_at",
    }
    if args.quality_grade:
        params["quality_grade"] = args.quality_grade
    params["geo"] = args.geo
    if args.media:
        params["photos"] = args.media == "photos"
        params["sounds"] = args.media == "sounds"
    if args.place_id:
        params["place_id"] = args.place_id
    if args.project_id:
        params["project_id"] = args.project_id
    if args.start_date:
        params["d1"] = args.start_date
    if args.end_date:
        params["d2"] = args.end_date
    if args.bbox:
        params["nelat"], params["nelng"], params["swlat"], params["swlng"] = args.bbox
    if args.user_id:
        params["user_id"] = args.user_id
    return params


def parse_bbox(raw: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    """Validate bbox CLI input so we can forward four floats to the API."""
    if raw is None:
        return None
    parts = raw.split(",")
    if len(parts) != 4:
        raise ValueError("bbox must be four comma-separated floats: nelat,nelng,swlat,swlng")
    return tuple(float(part) for part in parts)


def write_jsonl_gz(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    """Dump newline-delimited JSON (gzipped) so raw API responses are easy to replay."""
    with gzip.open(path, "wt", encoding="utf-8") as fp:
        for record in records:
            fp.write(json.dumps(record))
            fp.write("\n")


def write_presence_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    """Persist the grid-aligned table as gzipped CSV with consistent headers."""
    fieldnames = [
        "observation_id",
        "species_id",
        "observed_at",
        "latitude",
        "longitude",
        "positional_accuracy_m",
        "quality_grade",
        "individual_count",
        "is_captive",
        "grid_x",
        "grid_y",
        "cell_id",
        "projected_x",
        "projected_y",
        "presence",
    ]
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def create_output_paths(
    species_slug: str,
    raw_root: Path,
    processed_root: Path,
) -> Tuple[Path, Path, str]:
    """Build timestamped file paths so multiple runs stay organized."""
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = raw_root / "observations" / species_slug / timestamp
    processed_dir = processed_root / "observations" / species_slug
    ensure_output_paths(raw_dir, processed_dir)
    raw_path = raw_dir / f"{species_slug}_observations.jsonl.gz"
    processed_path = processed_dir / f"{species_slug}_presence_{timestamp}.csv.gz"
    return raw_path, processed_path, timestamp


def download_and_process(args: argparse.Namespace) -> None:
    """Main CLI flow: fetch observations, write artifacts, update manifest."""
    grid = load_grid(args.grid)
    projector = GridProjector(grid)
    session = requests.Session()
    params = build_query_params(args)
    per_page = min(args.per_page, MAX_PER_PAGE)

    print(f"Fetching observations for species_id={args.species_id}", flush=True)
    all_records: List[Dict[str, Any]] = []
    try:
        for record in chunked_observations(
            session=session,
            params=params,
            per_page=per_page,
            max_records=args.max_records,
            sleep_seconds=args.sleep,
        ):
            all_records.append(record)
    except requests.HTTPError as exc:
        print(f"HTTP error while fetching observations: {exc}", file=sys.stderr)
        raise

    print(f"Fetched {len(all_records)} observations", flush=True)
    if args.dry_run or not all_records:
        return

    raw_path, processed_path, timestamp = create_output_paths(
        species_slug=args.species_slug,
        raw_root=args.raw_dir,
        processed_root=args.processed_dir,
    )
    write_jsonl_gz(raw_path, all_records)

    presence_rows: List[Dict[str, Any]] = []
    for record in all_records:
        row = extract_presence_row(record, projector)
        if row is not None:
            presence_rows.append(row)
    # Presence table only includes points landing inside the grid and with usable coords.

    processed_output: Optional[Path] = None
    if presence_rows:
        write_presence_csv(processed_path, presence_rows)
        processed_output = processed_path
    else:
        print("Warning: no observations with valid coordinates fell inside the grid.", flush=True)

    append_manifest_rows: List[Dict[str, str]] = []
    query_url = f"{INAT_OBSERVATIONS_URL}?taxon_id={args.species_id}"
    created_at = dt.datetime.now(dt.timezone.utc).date().isoformat()
    append_manifest_rows.append(
        {
            "dataset": f"inaturalist_raw_{args.species_slug}",
            "source_url": query_url,
            "license": "Creative Commons (observation-dependent; see iNaturalist terms)",
            "created_at": created_at,
            "notes": f"{len(all_records)} observations cached on {timestamp}",
        }
    )
    if processed_output:
        append_manifest_rows.append(
            {
                "dataset": f"inaturalist_presence_{args.species_slug}",
                "source_url": processed_output.as_posix(),
                "license": "Creative Commons (observation-dependent; see iNaturalist terms)",
                "created_at": created_at,
                "notes": "Presence table aligned to 100 m grid.",
            }
        )
    # Manifest rows document both the raw API query and the processed presence output.
    append_manifest(args.manifest, append_manifest_rows)
    print(f"Raw observations written to {raw_path}", flush=True)
    if processed_output:
        print(f"Presence table written to {processed_output}", flush=True)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download iNaturalist observations and align them to the WhereWild grid."
    )
    parser.add_argument("--species-id", type=int, required=True, help="iNaturalist taxon ID.")
    parser.add_argument(
        "--species-slug",
        type=str,
        required=True,
        help="Slug used for directory names (e.g. escobaria_vivipara).",
    )
    parser.add_argument(
        "--grid",
        type=Path,
        default=Path("grid.json"),
        help="Path to grid.json specification.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("raw"),
        help="Root directory for raw downloads.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("processed"),
        help="Root directory for processed outputs.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("manifest.csv"),
        help="Manifest CSV path for provenance logging.",
    )
    parser.add_argument(
        "--quality-grade",
        type=str,
        default="research",
        help="Filter by iNaturalist quality grade (e.g. research, needs_id, casual).",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=200,
        help="Number of observations to request per API page (max 200).",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        help="Optional cap on total observations to fetch (useful for testing).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Seconds to sleep between paginated API requests.",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="ISO8601 start date (d1 parameter) for the observation search window.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="ISO8601 end date (d2 parameter) for the observation search window.",
    )
    parser.add_argument(
        "--bbox",
        type=parse_bbox,
        help="Bounding box filter nelat,nelng,swlat,swlng.",
    )
    parser.add_argument(
        "--place-id",
        type=str,
        help="Optional iNaturalist place_id filter.",
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="Optional iNaturalist project_id filter.",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="Limit to observations from a specific user.",
    )
    parser.add_argument(
        "--media",
        choices=["photos", "sounds"],
        help="Require observations with a specific media type.",
    )
    parser.add_argument(
        "--geo",
        dest="geo",
        action="store_true",
        help="Require coordinates (default: true).",
    )
    parser.add_argument(
        "--no-geo",
        dest="geo",
        action="store_false",
        help="Allow observations without coordinates.",
    )
    parser.set_defaults(geo=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and report observation counts without writing files.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    try:
        download_and_process(args)
    except Exception as exc:  # pragma: no cover - command-line guardrail
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
