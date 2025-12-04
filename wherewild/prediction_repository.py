from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "processed"
SPECIES_CATALOG_PATH = PROCESSED_DIR / "species" / "species_catalog.json"
PREDICTIONS_DIR = PROCESSED_DIR / "predictions"


class SpeciesNotFoundError(KeyError):
    """Raised when a requested species taxon_id cannot be found."""


class PredictionMapNotFoundError(FileNotFoundError):
    """Raised when a requested prediction map is missing."""


@lru_cache()
def _load_species_catalog() -> Dict[int, dict]:
    if not SPECIES_CATALOG_PATH.exists():
        msg = f"Species catalog not found at {SPECIES_CATALOG_PATH}"
        raise FileNotFoundError(msg)
    with SPECIES_CATALOG_PATH.open() as fp:
        data = json.load(fp)
    return {entry["taxon_id"]: entry for entry in data}


def _get_species_entry(species_id: int) -> dict:
    catalog = _load_species_catalog()
    try:
        return catalog[species_id]
    except KeyError as exc:
        raise SpeciesNotFoundError(species_id) from exc


def get_prediction_map(species_id: int, fmt: str = "png") -> Path:
    """Return the absolute path to a pre-rendered prediction map image."""
    species = _get_species_entry(species_id)
    slug = species["slug"]
    fmt_normalized = fmt.lower()
    if fmt_normalized not in {"png", "tif"}:
        raise ValueError("Prediction map format must be 'png' or 'tif'.")

    filename = f"{slug}_{species_id}_probability.{fmt_normalized}"
    map_path = PREDICTIONS_DIR / filename
    if not map_path.exists():
        raise PredictionMapNotFoundError(
            f"Prediction map not found for species {species_id} ({fmt_normalized})."
        )
    return map_path
