#!/usr/bin/env python3
"""
Populate the species catalog with short descriptions pulled from iNaturalist.

Usage:
    python scripts/fetch_inat_descriptions.py [--overwrite]

The script fetches `wikipedia_summary` for each taxon via the public
iNaturalist API and stores it under the `description` field.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "processed" / "species" / "species_catalog.json"
INAT_ENDPOINT = "https://api.inaturalist.org/v1/taxa/{taxon_id}"
REQUEST_DELAY_SEC = 0.5  # stay friendly to the public API


def fetch_inat_summary(taxon_id: int) -> dict[str, str] | None:
    """Return the wikipedia summary + url for a given taxon_id."""
    url = INAT_ENDPOINT.format(taxon_id=taxon_id)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[WARN] Failed to fetch taxon {taxon_id}: {exc}", file=sys.stderr)
        return None
    payload = resp.json()
    results = payload.get("results")
    if not results:
        return None
    record = results[0]
    summary = record.get("wikipedia_summary")
    if not summary:
        return None
    return {
        "description": summary.strip(),
        "description_source": "iNaturalist (wikipedia_summary)",
        "description_url": record.get("wikipedia_url") or "",
    }


def load_catalog() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        raise SystemExit(f"Catalog not found at {CATALOG_PATH}")
    with CATALOG_PATH.open() as fh:
        return json.load(fh)


def save_catalog(data: list[dict[str, Any]]) -> None:
    with CATALOG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing descriptions instead of skipping them.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    catalog = load_catalog()
    updated = False
    for entry in catalog:
        taxon_id = entry.get("taxon_id")
        if taxon_id is None:
            continue
        if not args.overwrite and entry.get("description"):
            continue
        summary_payload = fetch_inat_summary(int(taxon_id))
        if not summary_payload:
            continue
        entry.update(summary_payload)
        updated = True
        save_catalog(catalog)
        print(f"[INFO] Updated {entry.get('scientific_name', taxon_id)}")
        time.sleep(REQUEST_DELAY_SEC)
    if updated:
        save_catalog(catalog)
        print(f"[DONE] Wrote updates to {CATALOG_PATH}")
    else:
        print("[DONE] No updates were necessary.")


if __name__ == "__main__":
    main()
