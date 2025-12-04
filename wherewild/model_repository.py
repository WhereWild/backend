from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "processed"
SPECIES_CATALOG_PATH = PROCESSED_DIR / "species" / "species_catalog.json"
MODELS_DIR = PROCESSED_DIR / "models" / "gbt"


class SpeciesMetadataNotFoundError(KeyError):
    """Raised when a requested species taxon_id cannot be found in the catalog."""


class ModelArtifactNotFoundError(FileNotFoundError):
    """Raised when the trained model artifact for a species cannot be located."""


class FeatureImportancesUnavailableError(KeyError):
    """Raised when a model artifact does not contain feature importances."""


@lru_cache()
def _load_species_catalog() -> Dict[int, dict]:
    if not SPECIES_CATALOG_PATH.exists():
        msg = f"Species catalog not found at {SPECIES_CATALOG_PATH}"
        raise FileNotFoundError(msg)
    with SPECIES_CATALOG_PATH.open() as fp:
        entries = json.load(fp)
    return {int(entry["taxon_id"]): entry for entry in entries}


def _get_species_entry(species_id: int) -> dict:
    catalog = _load_species_catalog()
    try:
        return catalog[species_id]
    except KeyError as exc:
        raise SpeciesMetadataNotFoundError(species_id) from exc


def _resolve_model_path(species_id: int, slug: str) -> Path:
    preferred = MODELS_DIR / f"{slug}_{species_id}.json"
    if preferred.exists():
        return preferred
    legacy = MODELS_DIR / f"{species_id}.json"
    if legacy.exists():
        return legacy
    matches = sorted(MODELS_DIR.glob(f"*_{species_id}.json"))
    if matches:
        return matches[0]
    raise ModelArtifactNotFoundError(f"Model artifact missing for species {species_id}")


def _read_json(path: Path) -> dict:
    with path.open() as fp:
        return json.load(fp)


def get_feature_importances(species_id: int, limit: int | None = None) -> dict[str, Any]:
    species = _get_species_entry(species_id)
    slug = species.get("slug") or species.get("scientific_name") or str(species_id)
    model_path = _resolve_model_path(species_id, slug)
    payload = _read_json(model_path)
    model_info = payload.get("model") or {}
    pairs: List[List[Any]] | None = model_info.get("feature_importance_pairs")
    if not pairs:
        raise FeatureImportancesUnavailableError(
            f"Feature importances missing in model for species {species_id}"
        )
    items = [
        {"variable": str(variable), "importance": float(importance)}
        for variable, importance in pairs
    ]
    items.sort(key=lambda item: item["importance"], reverse=True)
    total_importance = sum(item["importance"] for item in items) or 1.0
    for idx, item in enumerate(items, start=1):
        item["rank"] = idx
        item["relative_importance"] = item["importance"] / total_importance
    if limit is not None:
        items = items[:limit]
    return {
        "species_id": species_id,
        "species_name": species.get("scientific_name"),
        "slug": slug,
        "total_importance": total_importance,
        "count": len(items),
        "feature_importances": items,
    }
