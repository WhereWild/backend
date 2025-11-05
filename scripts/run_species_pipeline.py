#!/usr/bin/env python3
"""Drive the species pipeline (download → features → plots) from species.json."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the species processing pipeline.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("species.json"),
        help="Path to species configuration JSON (default: species.json).",
    )
    parser.add_argument(
        "--slug",
        type=str,
        help="Process a single species slug (default: run all listed species).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip the download step (use existing observation files).",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Always redownload observations even if cached files exist.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip plots (just download + feature sampling).",
    )
    parser.add_argument(
        "--no-kde",
        action="store_true",
        help="Disable KDE overlays on numeric plots.",
    )
    parser.add_argument(
        "--no-phenology",
        action="store_true",
        help="Disable phenology (bloom/fruit) charts even when species group supports them.",
    )
    return parser.parse_args(argv)


def load_config(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"Species configuration not found: {path}")
    with path.open() as fp:
        data = json.load(fp)
    species = data.get("species", [])
    if not species:
        raise ValueError("No species entries found in config.")
    return species


def run_command(cmd: List[str]) -> None:
    print("[cmd]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def process_species(entry: Dict[str, object], args: argparse.Namespace) -> None:
    slug = entry["slug"]
    inat_id = entry["inat_id"]
    max_records = entry.get("max_records")
    region = entry.get("region")
    group = (entry.get("group") or "").lower()

    print(f"=== Processing species: {slug} (iNat ID {inat_id}) ===")

    observations_dir = Path("processed/observations") / slug
    presence_path = observations_dir / f"{slug}_presence.csv.gz"

    should_download = not args.skip_download
    if presence_path.exists() and not args.force_download:
        if should_download:
            print(f"Existing presence file found for {slug}; skipping download (use --force-download to refresh).")
        should_download = False

    if should_download:
        make_cmd = ["make", "download-observations", f"OBS_SPECIES={slug}", f"OBS_SPECIES_ID={inat_id}"]
        if max_records:
            make_cmd.append(f"OBS_MAX_RECORDS={max_records}")
        run_command(make_cmd)
        presence_path = observations_dir / f"{slug}_presence.csv.gz"

    if not presence_path.exists():
        raise FileNotFoundError(f"No presence file found for {slug} in {observations_dir}")
    latest_presence = presence_path

    base_name = latest_presence.name.replace("_presence", "_features")
    if base_name.endswith(".csv.gz"):
        features_name = base_name
    elif base_name.endswith(".csv"):
        features_name = base_name + ".gz"
    else:
        features_name = base_name + ".csv.gz"
    features_path = observations_dir / features_name
    run_command(
        [
            "venv/bin/python",
            "scripts/sample_species_features.py",
            "--observations",
            str(latest_presence),
            "--output",
            str(features_path),
        ]
    )

    if not args.no_plots:
        plot_cmd = [
            "venv/bin/python",
            "scripts/plot_species_features.py",
            "--features",
            str(features_path),
            "--output-dir",
            f"figures/species_plots/{slug}",
        ]
        if not args.no_kde:
            plot_cmd.append("--kde")
        if not args.no_phenology and group == "plant":
            plot_cmd.append("--phenology")
        run_command(plot_cmd)

    if region:
        print(f"Region hint: {region} (feature table at processed/features/{region}.parquet)")


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    species_entries = load_config(args.config)

    if args.slug:
        species_entries = [entry for entry in species_entries if entry["slug"] == args.slug]
        if not species_entries:
            raise ValueError(f"Species slug '{args.slug}' not found in config.")

    for entry in species_entries:
        process_species(entry, args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
