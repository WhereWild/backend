from __future__ import annotations

import math
import os
import json
import threading
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from util.config import load_config
from util import descriptions, gis_lookup, indexing, summary_stats, taxa_navigation, units, inference
from util.storage import get_parquet_storage

CONFIG = load_config("global")

api_title = "WhereWild API"

api_version = "0.2.0"

category_sample_limit = 500

cors_allow_headers = ("*",)

cors_allow_methods = ("GET", "POST", "DELETE", "OPTIONS")

cors_allow_origins = ("*",)

density_points = 128

forced_categorical_variables = frozenset({"landcover"})

default_species_limit = 12

max_species_limit = 100


app = FastAPI(title=api_title, version=api_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(cors_allow_origins),
    allow_methods=list(cors_allow_methods),
    allow_headers=list(cors_allow_headers),
)


INFERENCE_BUNDLE_PATH = Path(os.environ.get("WHEREWILD_INFERENCE_BUNDLE", "checkpoints/inference_bundle.pt"))


@app.on_event("startup")
def _preload_gis_legends() -> None:
    """Warm GIS legend caches at startup when metadata is available."""
    try:
        gis_lookup.preload_layer_legends()
    except FileNotFoundError:
        # Allow API to start even if GIS catalog/legends are not present yet.
        pass
    except OSError:
        # Remote/object storage might be unavailable at startup; defer to first request.
        pass


@app.on_event("startup")
def _load_inference_bundle() -> None:
    """Load the configured inference bundle during API startup."""
    bundle_path = INFERENCE_BUNDLE_PATH
    if not bundle_path.is_absolute():
        bundle_path = CONFIG.project_root / bundle_path
    if bundle_path.exists():
        try:
            inference.load_bundle(bundle_path)
            print(
                f"Inference bundle loaded: {bundle_path} "
                f"({len(inference.known_species()):,} species, "
                f"{inference.cell_count():,} cells)"
            )
        except Exception:
            import traceback as _tb

            print(f"Warning: failed to load inference bundle {bundle_path}")
            _tb.print_exc()
    else:
        print(f"Inference bundle not found at {bundle_path} — /api/predict disabled")


def _path_exists(path: Path) -> bool:
    """Check path existence for local filesystem or configured remote storage."""
    storage = get_parquet_storage(CONFIG.data_root, CONFIG.project_root)
    if storage.is_remote:
        return storage.exists(path)
    return path.exists()


@app.get("/health", summary="Simple liveness probe")
def health_check() -> dict[str, str]:
    """Returns a simple liveness payload.

    Returns:
        A status string and UTC timestamp.
    """
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/variables")
def list_environment_variables(
    unit_system: Optional[str] = Query(None, description="Unit system for response values (metric or imperial)"),
) -> List[dict[str, Any]]:
    """Lists available environmental variables.

    Returns:
        A list of variable metadata entries.
    """
    return units.apply_unit_system_to_variables(
        gis_lookup.load_variable_metadata()[0],
        unit_system,
    )


@app.get("/api/species")
def list_species(
    q: str = Query(..., min_length=1, description="Search term (scientific name or common name)"),
    limit: int = Query(default_species_limit, ge=1, le=max_species_limit),
) -> List[dict[str, Any]]:
    """Searches taxa by name and returns serialized results.

    Args:
        q: Search term for scientific or common names.
        limit: Maximum number of matches to return.

    Returns:
        A list of serialized taxon payloads.
    """
    records = taxa_navigation.search_taxa_by_name(q, limit=limit)

    payloads: list[dict[str, Any]] = []
    for record, _score, matched_name in records:
        payload = taxa_navigation.serialize_taxon(record)
        if payload:
            common_names = payload.get("common_names") or []
            matched_common_name = taxa_navigation.resolve_matched_common_name(
                common_names,
                matched_name,
            )
            payload["matched_common_name"] = matched_common_name
            payloads.append(payload)
    return payloads


@app.get("/api/species/{taxon_id}")
def get_species_detail(
    taxon_id: int,
    location: Optional[str] = Query(None, description="Optional location GID to tailor description text."),
    unit_system: Optional[str] = Query(None, description="Unit system for description values (metric or imperial)"),
) -> dict[str, Any]:
    """Loads a single taxon record by id.

    Args:
        taxon_id: Taxon id to look up.
        location: Optional location GID filter for location text context.

    Returns:
        A serialized taxon payload.
    """
    taxon = taxa_navigation.get_taxon_by_id(str(taxon_id))
    payload = taxa_navigation.serialize_taxon(taxon) if taxon else None
    if not payload:
        raise HTTPException(
            status_code=404,
            detail=f"Species with taxon_id {taxon_id} not found",
        )
    location_gid = location.strip() if location else None
    try:
        description_profile = descriptions.build_taxon_description(
            taxon,
            location_gid=location_gid,
            unit_system=unit_system,
        )
        text = description_profile.get("text")
        if isinstance(text, str) and text.strip():
            payload["description"] = text
        payload["description_profile"] = description_profile
    except Exception as exc:
        print(f"[description] failed for taxon_id={taxon_id}: {exc}")
        traceback.print_exc()
    return payload


@app.get("/locations/search")
def search_locations_endpoint(
    q: str = Query(..., min_length=1, description="Location name or partial match"),
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Searches locations by name substring.

    Args:
        q: Search term for location names.
        limit: Maximum number of matches to return.

    Returns:
        A dict containing location match results.
    """
    matches = gis_lookup.search_locations(q, limit)
    return {"results": matches}


@app.get("/species/{taxon_id}/occurrences")
def species_occurrences(
    taxon_id: int,
    location: Optional[str] = Query(None, description="Filter observations by location gid"),
) -> dict[str, Any]:
    """Returns occurrence points for a taxon, optionally filtered by location.

    Args:
        taxon_id: Taxon id to query.
        location: Optional location GID to filter observations.

    Returns:
        A dict with occurrence count and point records.
    """
    taxon = taxa_navigation.get_taxon_by_id(str(taxon_id))
    if taxon is None:
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    if not _path_exists(Path(taxon["path"])):
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    normalized_location = location.strip() if location else None
    if normalized_location and not gis_lookup.is_valid_location_gid(normalized_location):
        return {
            "speciesId": taxon_id,
            "count": 0,
            "occurrences": [],
        }
    rows = taxa_navigation.load_occurrence_points(
        taxon_id,
        normalized_location,
    )
    return {
        "speciesId": taxon_id,
        "count": len(rows),
        "occurrences": rows,
    }


@app.get("/species/{taxon_id}/locations")
def species_locations(
    taxon_id: int,
    level: Optional[str] = Query(None, description="continent|country|state|county"),
    parent: Optional[str] = Query(None, description="Parent location GID (optional)"),
    limit: int = Query(500, ge=1, le=5000),
) -> List[dict[str, Any]]:
    """Returns locations where the species is present using precomputed membership."""
    taxon = taxa_navigation.get_taxon_by_id(str(taxon_id))
    if taxon is None:
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    if not _path_exists(Path(taxon["path"])):
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    target_taxon_id = taxa_navigation.taxon_id_as_int(str(taxon["taxon_key"]))
    if target_taxon_id is None:
        return []

    level_map = {"continent": -1, "country": 0, "state": 1, "county": 2}
    expected_level: int | None = None
    if level is not None:
        try:
            expected_level = int(level)
        except (TypeError, ValueError):
            expected_level = level_map.get(str(level).lower())

    entries, by_gid = gis_lookup.load_location_catalog()
    if not entries:
        return []

    level_by_scope = {str(scope): int(level_idx) for level_idx, scope in CONFIG.location_scope_by_level.items()}
    level_by_scope["gbif_region"] = -1

    parent_tokens = [token.strip() for token in (parent or "").split("|") if token.strip()]
    records_by_lower_name: dict[str, list[gis_lookup.LocationRecord]] = {}
    for record in entries:
        records_by_lower_name.setdefault(record.name.lower(), []).append(record)

    parent_matchers: list[tuple[set[str], set[str]]] = []
    for token in parent_tokens:
        name_options = {token.lower()}
        gid_options = {token.lower()}
        by_gid_record = by_gid.get(token) or by_gid.get(token.upper())
        if by_gid_record is not None:
            name_options.add(by_gid_record.name.lower())
            gid_options.add(by_gid_record.gid.lower())
        for named_record in records_by_lower_name.get(token.lower(), []):
            name_options.add(named_record.name.lower())
            gid_options.add(named_record.gid.lower())
        parent_matchers.append((name_options, gid_options))

    ancestor_gid_cache: dict[str, set[str]] = {}

    def ancestor_gids_for(record: gis_lookup.LocationRecord) -> set[str]:
        """Collect ancestor GIDs for parent-filter matching with cache reuse."""
        cached = ancestor_gid_cache.get(record.gid)
        if cached is not None:
            return cached
        chain: set[str] = set()
        seen: set[str] = set()
        current = record.parent_gid
        while current:
            current_key = str(current)
            if current_key in seen:
                break
            seen.add(current_key)
            chain.add(current_key.lower())
            parent_record = by_gid.get(current_key)
            if parent_record is None:
                break
            current = parent_record.parent_gid
        ancestor_gid_cache[record.gid] = chain
        return chain

    def matches_parent(
        gid: str,
        name: str,
        hierarchy_names: list[str],
        hierarchy_gids: set[str],
    ) -> bool:
        """Return True when a location satisfies all provided parent constraints."""
        if not parent_matchers:
            return True
        cand_gid = gid.lower()
        cand_name = name.lower()
        hierarchy_name_set = {item.lower() for item in hierarchy_names}
        for name_options, gid_options in parent_matchers:
            name_match = bool(name_options & hierarchy_name_set) or cand_name in name_options
            gid_match = cand_gid in gid_options or bool(gid_options & hierarchy_gids)
            if not (name_match or gid_match):
                return False
        return True

    location_counts = gis_lookup.location_counts_for_taxon(target_taxon_id)
    if not location_counts:
        return []

    results: list[dict[str, Any]] = []
    seen_gids: set[str] = set()
    for (scope, gid), count in location_counts.items():
        location_level = level_by_scope.get(str(scope))
        if location_level is None:
            continue
        if expected_level is not None and location_level != expected_level:
            continue
        gid_key = str(gid)
        if not gis_lookup.is_valid_location_gid(gid_key):
            continue
        if gid_key in seen_gids:
            continue
        seen_gids.add(gid_key)

        record = by_gid.get(gid_key)
        if record is not None:
            location_name = record.name
            hierarchy = gis_lookup.resolve_location_context(record, by_gid)
            hierarchy_gids = ancestor_gids_for(record)
        else:
            location_name = gid_key
            hierarchy = []
            hierarchy_gids = set()

        if not matches_parent(gid_key, location_name, hierarchy, hierarchy_gids):
            continue

        results.append({
            "gid": gid_key,
            "name": location_name,
            "level": location_level,
            "hierarchy": hierarchy,
            "count": int(count),
        })

    results.sort(
        key=lambda item: (
            -int(item.get("count", 0)),
            str(item.get("name", "")).lower(),
            str(item.get("gid", "")),
        )
    )
    if limit and len(results) > limit:
        return results[:limit]
    return results


@app.get("/locations/search_hierarchy")
def search_locations_by_hierarchy(
    q: str = Query("", description="Location name or partial match (optional if parent provided)"),
    level: Optional[str] = Query(None, description="continent|country|state|county or numeric level code"),
    parent: Optional[str] = Query(
        None, description="Parent name or gid. For counties pass 'United States|Utah' or a gid."
    ),
    limit: int = Query(50, ge=1, le=1000),
) -> dict[str, Any]:
    """Search locations with optional level and parent hierarchy constraints."""

    q = (q or "").strip()

    level_map = {"continent": -1, "country": 0, "state": 1, "county": 2}

    expected_level = None
    if level is not None:
        try:
            expected_level = int(level)
        except Exception:
            expected_level = level_map.get(level.lower())

    parents_raw = (parent or "").strip()
    parent_tokens = [p.strip() for p in parents_raw.split("|") if p.strip()]

    resolved_parent_names: list[str] = []
    resolved_parent_gids: list[str] = []
    for tok in parent_tokens:
        resolved_name = tok
        resolved_gid = tok
        try:
            if hasattr(gis_lookup, "get_location_by_gid"):
                maybe = gis_lookup.get_location_by_gid(tok)
                if maybe:
                    resolved_name = maybe.get("name", tok)
                    resolved_gid = maybe.get("gid", tok)
        except Exception:
            pass
        resolved_parent_names.append(str(resolved_name).lower())
        resolved_parent_gids.append(str(resolved_gid).lower())

    if not q and not parent_tokens and expected_level is None:
        return {"results": []}

    candidates: list[dict[str, Any]] = []
    seen_gids = set()

    def matches_parent(cand: dict[str, Any]) -> bool:
        """Check whether a candidate location belongs to the requested parent chain."""
        # if no parent requested, everything matches
        if not resolved_parent_names:
            return True
        cand_hierarchy = [str(x).lower() for x in (cand.get("hierarchy") or []) if x is not None]
        cand_name = str(cand.get("name") or "").lower()
        cand_gid = str(cand.get("gid") or "").lower()
        for pname, pgid in zip(resolved_parent_names, resolved_parent_gids):
            if pname in cand_hierarchy or pname == cand_name or pgid == cand_gid or pgid in cand_hierarchy:
                continue
            return False
        return True

    def push_candidate_if_valid(cand: dict[str, Any]):
        """Deduplicate and append a candidate when it passes parent filtering."""
        gid = str(cand.get("gid") or "")
        if not gid or gid in seen_gids:
            return
        # enforce parent matching here (critical fix)
        if not matches_parent(cand):
            return
        seen_gids.add(gid)
        candidates.append(cand)

    try:
        if q:
            raw = gis_lookup.search_locations(q, limit)
            for cand in raw:
                push_candidate_if_valid(cand)

        else:
            # 1) catalog-based enumeration (fast)
            if expected_level is not None and hasattr(gis_lookup, "load_location_catalog"):
                try:
                    entries, mapping = gis_lookup.load_location_catalog()
                    for rec in entries:
                        if getattr(rec, "level", None) != expected_level:
                            continue

                        # build hierarchy names
                        hierarchy = []
                        parent_gid = getattr(rec, "parent_gid", None)
                        while parent_gid:
                            parent_rec = mapping.get(parent_gid)
                            if not parent_rec:
                                break
                            hierarchy.append(parent_rec.name)
                            parent_gid = parent_rec.parent_gid

                        cand = {
                            "gid": rec.gid,
                            "name": rec.name,
                            "level": rec.level,
                            "hierarchy": list(reversed(hierarchy)),
                        }
                        push_candidate_if_valid(cand)
                        if len(candidates) >= limit:
                            break
                except Exception:
                    pass

            # 2) list_children if available
            if not candidates and hasattr(gis_lookup, "list_children"):
                for parent_tok in parent_tokens or []:
                    try:
                        parent_gid = None
                        if hasattr(gis_lookup, "get_location_by_gid"):
                            maybe = gis_lookup.get_location_by_gid(parent_tok)
                            if maybe:
                                parent_gid = maybe.get("gid")
                        raw = gis_lookup.list_children(parent_gid or parent_tok, level=expected_level, limit=limit * 3)
                        for cand in raw:
                            push_candidate_if_valid(cand)
                        if len(candidates) >= limit:
                            break
                    except Exception:
                        continue

            # 3) letter-scan fallback — keep scanning letters until we have enough valid matches
            if not candidates:
                letters = "abcdefghijklmnopqrstuvwxyz"
                per_letter_limit = max(50, min(200, limit))
                for ch in letters:
                    if len(candidates) >= limit:
                        break
                    try:
                        partial = gis_lookup.search_locations(ch, per_letter_limit)
                    except Exception:
                        continue
                    for cand in partial:
                        push_candidate_if_valid(cand)
                        if len(candidates) >= limit:
                            break

    except Exception:
        return {"results": []}

    # final strict filter by level (redundant but safe)
    results: list[dict[str, Any]] = []
    for cand in candidates:
        if expected_level is not None and cand.get("level") != expected_level:
            continue
        results.append({
            "gid": str(cand.get("gid") or ""),
            "name": cand.get("name") or "",
            "level": cand.get("level", -999),
            "hierarchy": cand.get("hierarchy") or [],
        })
        if len(results) >= limit:
            break

    return {"results": results}


@app.get("/species/{taxon_id}/environment/{variable_id}")
def species_environment_stats(
    taxon_id: int,
    variable_id: str,
    location: Optional[str] = Query(
        None, description="Optional location gid (GADM or GBIF region) to filter observations."
    ),
    unit_system: Optional[str] = Query(None, description="Unit system for response values (metric or imperial)"),
) -> dict[str, Any]:
    """Returns environment stats for a taxon and variable.

    Args:
        taxon_id: Taxon id to query.
        variable_id: Environmental variable id.
        location: Optional location GID to filter observations.

    Returns:
        A dict containing summary stats, distributions, and rankings.
    """
    variable_id = variable_id.strip()
    variable_entry = gis_lookup.load_variable_metadata()[1].get(variable_id)
    if not variable_entry:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{variable_id}' is not available.",
        )
    raw_units = variable_entry.get("units")
    taxon = taxa_navigation.get_taxon_by_id(str(taxon_id))
    if taxon is None:
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    taxon_dir = Path(taxon["path"])
    if not _path_exists(taxon_dir):
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    location_gid = location.strip() if location else None
    value_type = str(variable_entry.get("value_type") or "").lower() or "numeric"
    forced_categorical = variable_id.lower() in forced_categorical_variables
    categorical_payload = None
    if forced_categorical or value_type == "categorical":
        if location_gid:
            categorical_payload = summary_stats.build_categorical_stats_for_location(
                taxon_id,
                variable_id,
                location_gid,
                sample_limit=category_sample_limit,
            )
            if categorical_payload is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"No samples available for taxon {taxon_id}, "
                        f"variable '{variable_id}' and location '{location_gid}'."
                    ),
                )
            value_type = "categorical"
        else:
            categorical_payload = summary_stats.load_categorical_distribution(taxon_dir, variable_id)
            if categorical_payload is None and forced_categorical:
                value_type = "categorical"
            elif categorical_payload is not None:
                value_type = "categorical"
    generated_at = datetime.now(timezone.utc).isoformat()

    baseline_numeric_summary = None
    baseline_categorical_distribution: list[dict[str, Any]] = []
    baseline_categorical_totals: dict[str, Any] = {}

    if categorical_payload:
        if location_gid:
            baseline_stats = summary_stats.load_categorical_distribution(taxon_dir, variable_id)
            if baseline_stats:
                baseline_categorical_distribution = baseline_stats.get("distribution", [])
                baseline_categorical_totals = baseline_stats.get("totals", {})
        totals = categorical_payload.get("totals", {})
        total_samples = totals.get("total_samples") or 0
        summary = {
            "count": int(total_samples),
            "min": None,
            "mean": None,
            "max": None,
            "stddev": None,
            "q01": None,
            "q10": None,
            "q90": None,
            "q99": None,
        }
        if location_gid:
            ranks = []
            print(
                f"[timing][env] taxon_id={taxon_id} variable={variable_id} "
                f"location={location_gid} step=relative_ranks skipped=1 reason=location_filter"
            )
        else:
            ranks = indexing.load_relative_ranks(taxon_dir, variable_id)
        response = {
            "speciesId": taxon_id,
            "species_id": taxon_id,
            "variable": variable_id,
            "variableName": variable_entry.get("name"),
            "variable_metadata": {
                "name": variable_entry.get("name"),
                "units": raw_units,
                "value_type": "categorical",
            },
            "units": raw_units,
            "variableType": "categorical",
            "generatedAt": generated_at,
            "generated_at": generated_at,
            "summary": summary,
            "histogram": None,
            "densityCurve": None,
            "binSamples": [],
            "bin_samples": [],
            "density_curve": None,
            "categoricalDistribution": categorical_payload.get("distribution", []),
            "categorical_distribution": categorical_payload.get("distribution", []),
            "dominantCategories": categorical_payload.get("dominant", []),
            "dominant_categories": categorical_payload.get("dominant", []),
            "baselineCategoricalDistribution": baseline_categorical_distribution,
            "baseline_categorical_distribution": baseline_categorical_distribution,
            "baselineCategoricalTotals": baseline_categorical_totals,
            "baseline_categorical_totals": baseline_categorical_totals,
            "baselineSummary": baseline_numeric_summary,
            "baseline_summary": baseline_numeric_summary,
            "relativeRanks": ranks,
            "relative_ranks": ranks,
        }
        return units.apply_unit_system_to_env_response(response, unit_system, raw_units)

    if not location_gid:
        summary = summary_stats.load_numeric_summary(str(taxon_dir), variable_id)
        density_curve = summary_stats.load_density_graph(str(taxon_dir), variable_id)
        if not summary or not density_curve:
            raise HTTPException(
                status_code=503,
                # We COULD compute on-demand here but I think it's better to fail loudly as the data *should* be here for performance reasons.
                detail=(
                    f"Precomputed summary stats or KDE missing (summary={bool(summary)} "
                    f"density={bool(density_curve)}). "
                    "Rebuild summary_stats.parquet and density_graph.parquet."
                ),
            )
        ranks = indexing.load_relative_ranks(taxon_dir, variable_id)
        response = {
            "speciesId": taxon_id,
            "species_id": taxon_id,
            "variable": variable_id,
            "variableName": variable_entry.get("name"),
            "variable_metadata": {
                "name": variable_entry.get("name"),
                "units": variable_entry.get("units"),
                "value_type": value_type or "numeric",
            },
            "units": variable_entry.get("units"),
            "variableType": value_type or "numeric",
            "generatedAt": generated_at,
            "generated_at": generated_at,
            "summary": summary,
            "histogram": None,
            "densityCurve": density_curve,
            "binSamples": [],
            "bin_samples": [],
            "density_curve": density_curve,
            "baselineSummary": baseline_numeric_summary,
            "baseline_summary": baseline_numeric_summary,
            "baselineCategoricalDistribution": [],
            "baseline_categorical_distribution": [],
            "baselineCategoricalTotals": {},
            "baseline_categorical_totals": {},
            "categoricalDistribution": [],
            "categorical_distribution": [],
            "dominantCategories": [],
            "dominant_categories": [],
            "relativeRanks": ranks,
            "relative_ranks": ranks,
        }
        return units.apply_unit_system_to_env_response(response, unit_system, raw_units)

    samples = summary_stats.gather_numeric_records(
        taxon_id,
        taxon_dir,
        variable_id,
        location_gid=location_gid,
    )
    values = [sample["value"] for sample in samples]
    if not values:
        raise HTTPException(
            status_code=404,
            detail=f"No samples available for taxon {taxon_id} and variable '{variable_id}'.",
        )
    if location_gid:
        baseline_samples = summary_stats.gather_numeric_records(
            taxon_id,
            taxon_dir,
            variable_id,
            location_gid=None,
        )
        baseline_values = [sample["value"] for sample in baseline_samples]
        if baseline_values:
            baseline_numeric_summary = summary_stats.summarize_values(baseline_values)
    summary = summary_stats.summarize_values(values)
    density_curve = indexing.build_density_curve(values, point_count=density_points)
    ranks = []
    print(
        f"[timing][env] taxon_id={taxon_id} variable={variable_id} "
        f"location={location_gid} step=relative_ranks skipped=1 reason=location_filter"
    )
    response = {
        "speciesId": taxon_id,
        "species_id": taxon_id,
        "variable": variable_id,
        "variableName": variable_entry.get("name"),
        "variable_metadata": {
            "name": variable_entry.get("name"),
            "units": raw_units,
            "value_type": value_type or "numeric",
        },
        "units": raw_units,
        "variableType": value_type or "numeric",
        "generatedAt": generated_at,
        "generated_at": generated_at,
        "summary": summary,
        "histogram": None,
        "densityCurve": density_curve,
        "binSamples": [],
        "bin_samples": [],
        "density_curve": density_curve,
        "baselineSummary": baseline_numeric_summary,
        "baseline_summary": baseline_numeric_summary,
        "baselineCategoricalDistribution": [],
        "baseline_categorical_distribution": [],
        "baselineCategoricalTotals": {},
        "baseline_categorical_totals": {},
        "categoricalDistribution": [],
        "categorical_distribution": [],
        "dominantCategories": [],
        "dominant_categories": [],
        "relativeRanks": ranks,
        "relative_ranks": ranks,
    }
    return units.apply_unit_system_to_env_response(response, unit_system, raw_units)


@app.get("/species/{taxon_id}/environment/{variable_id}/class/{class_value}/samples")
def species_environment_class_samples(
    taxon_id: int,
    variable_id: str,
    class_value: str,
    limit: int | None = Query(None, ge=1, le=10000),
    location: Optional[str] = Query(
        None, description="Optional location gid (GADM or GBIF region) to filter observations."
    ),
) -> dict[str, Any]:
    """Returns categorical class samples for a taxon and variable.

    Args:
        taxon_id: Taxon id to query.
        variable_id: Categorical variable id.
        class_value: Class value to match.
        limit: Maximum number of samples to return.
        location: Optional location GID to filter observations.

    Returns:
        A dict containing matching observation samples.
    """
    taxon = taxa_navigation.get_taxon_by_id(str(taxon_id))
    if taxon is None:
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    taxon_dir = Path(taxon["path"])
    if not _path_exists(taxon_dir):
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    try:
        parsed_value: float | int | str
        parsed_value = float(class_value)
        if parsed_value.is_integer():
            parsed_value = int(parsed_value)
    except ValueError:
        parsed_value = class_value
    location_gid = location.strip() if location else None
    observations: list[dict[str, Any]] = []
    if location_gid:
        observations = summary_stats.categorical_class_samples_for_location(
            taxon_id,
            variable_id,
            parsed_value,
            location_gid=location_gid,
            limit=limit,
        )
    else:
        index_path = taxon_dir / "occurrence_index.parquet"
        if not _path_exists(index_path):
            raise HTTPException(
                status_code=503,
                detail="GIS lookup utilities are unavailable on this server.",
            )
        try:
            rows = summary_stats.get_layer_records_for_class(index_path, variable_id, parsed_value)
        except Exception as exc:  # pragma: no cover - passthrough
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if limit is not None and limit > 0:
            rows = rows[:limit]
        observations = [
            {
                "catalogNumber": row[0],
                "latitude": row[1],
                "longitude": row[2],
                "value": row[3],
            }
            for row in rows
        ]
    return {
        "speciesId": taxon_id,
        "variable": variable_id,
        "classValue": parsed_value,
        "observations": observations,
        "count": len(observations),
    }


@app.get("/species/{taxon_id}/environment/{variable_id}/slice")
def species_environment_slice(
    taxon_id: int,
    variable_id: str,
    min_value: float = Query(..., alias="min"),
    max_value: float = Query(..., alias="max"),
    limit: int | None = Query(None, ge=1, le=10000),
    location: Optional[str] = Query(
        None, description="Optional location gid (GADM or GBIF region) to filter observations."
    ),
    unit_system: Optional[str] = Query(None, description="Unit system for response values (metric or imperial)"),
) -> dict[str, Any]:
    """Returns numeric samples within a value range for a taxon/variable.

    Args:
        taxon_id: Taxon id to query.
        variable_id: Numeric variable id.
        min_value: Minimum value to include.
        max_value: Maximum value to include.
        limit: Maximum number of samples to return.
        location: Optional location GID to filter observations.

    Returns:
        A dict containing range parameters and matching observations.
    """
    if not math.isfinite(min_value) or not math.isfinite(max_value):
        raise HTTPException(status_code=400, detail="min and max must be finite numbers")
    if max_value < min_value:
        min_value, max_value = max_value, min_value
    variable_entry = gis_lookup.load_variable_metadata()[1].get(variable_id)
    if not variable_entry:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{variable_id}' is not available.",
        )
    value_type = str(variable_entry.get("value_type") or "").lower() or "numeric"
    raw_units = variable_entry.get("units")
    resolved_unit_system = units.normalize_unit_system(unit_system)
    if resolved_unit_system and raw_units:
        min_value = units.convert_value_from_system(min_value, raw_units, resolved_unit_system)
        max_value = units.convert_value_from_system(max_value, raw_units, resolved_unit_system)
    if value_type == "categorical" or variable_id.lower() in forced_categorical_variables:
        raise HTTPException(
            status_code=400,
            detail="Categorical layers must be queried via the class samples endpoint.",
        )
    taxon = taxa_navigation.get_taxon_by_id(str(taxon_id))
    if taxon is None:
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    taxon_dir = Path(taxon["path"])
    if not _path_exists(taxon_dir):
        raise HTTPException(status_code=404, detail=f"Unknown taxon {taxon_id}")
    index_path = taxon_dir / "occurrence_index.parquet"
    if not _path_exists(index_path):
        raise HTTPException(
            status_code=404,
            detail=f"Index parquet missing for taxon {taxon_id}",
        )
    location_gid = location.strip() if location else None
    rows: list[tuple[str, float | None, float | None, float | None]] = []
    if location_gid:
        rows = summary_stats.numeric_range_samples_for_location(
            taxon_id,
            variable_id,
            min_value,
            max_value,
            location_gid=location_gid,
            limit=limit,
        )
    else:
        try:
            rows = summary_stats.get_sorted_layer_records_in_value_range(
                index_path,
                variable_id,
                value_min=min_value,
                value_max=max_value,
                limit=limit,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    observations: list[dict[str, Any]] = []
    for catalog, lat, lon, value in rows:
        observations.append({
            "catalogNumber": catalog,
            "value": float(value) if isinstance(value, (int, float)) else value,
            "latitude": lat,
            "longitude": lon,
        })
    response = {
        "speciesId": taxon_id,
        "variable": variable_id,
        "range": {"min": min_value, "max": max_value},
        "units": raw_units,
        "limit": limit,
        "count": len(observations),
        "observations": observations,
    }
    return units.apply_unit_system_to_slice_response(response, unit_system, raw_units)


@app.get("/relative-rankings/{taxon_id}")
def get_relative_rankings(
    taxon_id: int,
    rank: str = Query(..., description="Descendant rank to include (e.g., SPECIES)"),
    variable: str = Query(..., description="Environmental variable / layer id"),
    metric: str = Query(..., description="Metric to rank by (min, mean, max, std, 1-99 range)"),
    limit: int = Query(50, ge=1, le=200),
    order: str = Query("asc", description="Sort order: asc or desc"),
    min_samples: int = Query(0, ge=0, description="Minimum samples required to appear"),
    include_species_like: bool = Query(False, description="When rank=SPECIES, include subspecies/varieties/forms"),
    include_distribution: bool = Query(
        False,
        description=(
            "Include the kernel density distribution for all eligible descendants. "
            "This can be expensive for large taxa."
        ),
    ),
    location: Optional[str] = Query(
        None,
        description="Optional location GID (GADM) or GBIF region to filter descendants by",
    ),
    unit_system: Optional[str] = Query(None, description="Unit system for response values (metric or imperial)"),
) -> dict[str, Any]:
    """Returns descendant rankings for a taxon by variable/metric.

    Args:
        taxon_id: Ancestor taxon id to rank descendants under.
        rank: Descendant rank to include.
        variable: Environmental variable id to rank by.
        metric: Metric name to rank by.
        limit: Maximum number of results to return.
        order: Sort order ("asc" or "desc").
        min_samples: Minimum sample count required to appear.
        include_species_like: Whether to include subspecies-like ranks for species.
        include_distribution: Whether to return raw values for density curves.
        location: Optional location GID to filter descendants by occurrence membership.

    Returns:
        A dict containing ranking entries and optional distribution data.
    """
    location_gid = location.strip() if location else None
    try:
        entries, distribution_values = indexing.child_relative_rankings(
            str(taxon_id),
            rank,
            variable,
            metric,
            limit=limit,
            order=order,
            min_samples=min_samples,
            include_species_like=include_species_like,
            return_distribution=include_distribution,
            location_gid=location_gid,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    total = entries[0]["count"] if entries else 0
    distribution_curve = None
    if include_distribution and distribution_values:
        distribution_curve = indexing.build_density_curve(
            distribution_values,
            point_count=density_points,
        )
    raw_units = None
    variable_entry = gis_lookup.load_variable_metadata()[1].get(variable)
    if variable_entry:
        raw_units = variable_entry.get("units")
    response = {
        "ancestor_taxon_id": taxon_id,
        "rank": rank.upper(),
        "variable": variable,
        "metric": metric,
        "units": raw_units,
        "total": total,
        "limit": limit,
        "order": order.lower(),
        "min_samples": min_samples,
        "include_species_like": include_species_like,
        "entries": entries,
        "distribution": distribution_curve,
    }
    return units.apply_unit_system_to_rankings_response(response, unit_system, raw_units)


@app.get("/relative-rankings/{taxon_id}/options")
def list_relative_ranking_options(
    taxon_id: int,
    rank: str = Query(..., description="Descendant rank to inspect (e.g., SPECIES)"),
) -> dict[str, Any]:
    """Lists available ranking metrics for an ancestor/rank.

    Args:
        taxon_id: Ancestor taxon id to inspect.
        rank: Descendant rank to inspect.

    Returns:
        A dict containing available variable/metric options.
    """
    try:
        options = indexing.list_rank_metric_options(str(taxon_id), rank)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ancestor_taxon_id": taxon_id,
        "rank": rank.upper(),
        "options": options,
    }


# ---------------------------------------------------------------------------
# SDM prediction response models
# ---------------------------------------------------------------------------


class SpeciesPrediction(BaseModel):
    species_key: int
    score: float
    prior: float


class PredictResponse(BaseModel):
    lat: float
    lon: float
    top_k: int
    threshold: float
    n_results: int
    predictions: list[SpeciesPrediction]


class CoordinatePredictions(BaseModel):
    lat: float
    lon: float
    n_results: int
    predictions: list[SpeciesPrediction]


class PredictBatchResponse(BaseModel):
    n_coordinates: int
    top_k: int
    threshold: float
    results: list[CoordinatePredictions]


class HeatmapCell(BaseModel):
    lat: float
    lon: float
    score: float
    n_native: int
    source: str | None = None


class PredictHeatmapResponse(BaseModel):
    species_key: int
    bbox: list[float]
    resolution: float
    native_resolution: float
    n_cells: int
    cells: list[HeatmapCell]


class PredictInfoResponse(BaseModel):
    loaded: bool
    n_species: int
    n_cells: int
    species_keys: list[int]


class HeatmapJobCreateRequest(BaseModel):
    species_key: int
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    resolution: float | None = None
    include_source: bool = False
    feature_mode: str = "auto"
    max_cells: int = 20000


class HeatmapJobResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    stream_url: str
    cancel_url: str


class HeatmapJobDeleteResponse(BaseModel):
    job_id: str
    status: str


_heatmap_jobs_lock = threading.Lock()
_heatmap_jobs: dict[str, dict[str, Any]] = {}
_HEATMAP_JOB_TTL_SECONDS = 6 * 60 * 60
_HEATMAP_JOB_MAX_ENTRIES = 2000


def _parse_iso8601(ts: Any) -> datetime | None:
    """Parse an ISO8601 timestamp value into an aware datetime when possible."""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _prune_heatmap_jobs() -> None:
    """Prune stale/finished jobs and cap in-memory job count."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=_HEATMAP_JOB_TTL_SECONDS)
    finished_statuses = {"cancelled", "completed", "failed"}

    with _heatmap_jobs_lock:
        stale_ids: list[str] = []
        for job_id, job in _heatmap_jobs.items():
            status = str(job.get("status") or "")
            finished_at = _parse_iso8601(job.get("finished_at"))
            if status in finished_statuses and finished_at is not None and finished_at <= cutoff:
                stale_ids.append(job_id)

        for job_id in stale_ids:
            _heatmap_jobs.pop(job_id, None)

        overflow = len(_heatmap_jobs) - _HEATMAP_JOB_MAX_ENTRIES
        if overflow <= 0:
            return

        def _eviction_key(item: tuple[str, dict[str, Any]]) -> tuple[int, datetime]:
            _id, job = item
            status = str(job.get("status") or "")
            is_finished = status in finished_statuses
            finished_at = _parse_iso8601(job.get("finished_at"))
            created_at = _parse_iso8601(job.get("created_at"))
            ref_time = finished_at or created_at or now
            return (0 if is_finished else 1, ref_time)

        for job_id, _job in sorted(_heatmap_jobs.items(), key=_eviction_key)[:overflow]:
            _heatmap_jobs.pop(job_id, None)


def _validate_heatmap_bbox(min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> None:
    """Validate heatmap bbox ordering and raise HTTP 400 on invalid bounds."""
    if min_lat >= max_lat:
        raise HTTPException(status_code=400, detail="min_lat must be less than max_lat.")
    if min_lon >= max_lon:
        raise HTTPException(status_code=400, detail="min_lon must be less than max_lon.")


def _get_heatmap_job(job_id: str) -> dict[str, Any]:
    """Fetch a heatmap job by id or raise HTTP 404 when absent."""
    _prune_heatmap_jobs()
    with _heatmap_jobs_lock:
        job = _heatmap_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown heatmap job {job_id}.")
    return job


def _build_heatmap_stream_response(
    stream_result: dict[str, Any],
    *,
    job_id: str | None = None,
    cancel_check: Callable[[], bool] | None = None,
    on_cancel: Callable[[int], None] | None = None,
    on_done: Callable[[int], None] | None = None,
) -> StreamingResponse:
    """Build a reusable NDJSON stream response for heatmap cell iterators."""
    cells_iter = stream_result["cells"]
    meta_payload: dict[str, Any] = {
        "type": "meta",
        "species_key": stream_result["species_key"],
        "bbox": stream_result["bbox"],
        "resolution": stream_result["resolution"],
        "native_resolution": stream_result["native_resolution"],
        "requested_cells": stream_result["requested_cells"],
    }
    if job_id is not None:
        meta_payload["job_id"] = job_id

    def _terminal_payload(event_type: str, yielded: int) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": event_type, "n_cells": yielded}
        if job_id is not None:
            payload["job_id"] = job_id
        return payload

    def _ndjson_events():
        yielded = 0
        yield json.dumps(meta_payload) + "\n"
        for cell in cells_iter:
            if cancel_check is not None and cancel_check():
                if on_cancel is not None:
                    on_cancel(yielded)
                yield json.dumps(_terminal_payload("cancelled", yielded)) + "\n"
                return
            yielded += 1
            yield json.dumps({"type": "cell", **cell}) + "\n"

        was_cancelled = cancel_check is not None and cancel_check()
        if was_cancelled:
            if on_cancel is not None:
                on_cancel(yielded)
            yield json.dumps(_terminal_payload("cancelled", yielded)) + "\n"
            return

        if on_done is not None:
            on_done(yielded)
        yield json.dumps(_terminal_payload("done", yielded)) + "\n"

    return StreamingResponse(_ndjson_events(), media_type="application/x-ndjson")


# ---------------------------------------------------------------------------
# SDM prediction endpoints
# ---------------------------------------------------------------------------


@app.get("/api/predict", response_model=PredictResponse)
def predict_species(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in degrees."),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in degrees."),
    top_k: int = Query(20, ge=1, le=500, description="Maximum species to return."),
    threshold: float = Query(0.0, ge=0.0, le=1.0, description="Minimum score threshold."),
) -> PredictResponse:
    """Predict species suitability for a geographic coordinate.

    Returns ranked species scores from the Darwin SDM.  Requires an
    inference bundle to be loaded at startup (set WHEREWILD_INFERENCE_BUNDLE
    env var or place at checkpoints/inference_bundle.pt).

    Args:
        lat: Latitude of the query point.
        lon: Longitude of the query point.
        top_k: Number of top-scoring species to return.
        threshold: Minimum sigmoid score to include.

    Returns:
        A dict with coordinate echo, cell info, and ranked predictions.
    """
    if not inference.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="Inference model not loaded. Set WHEREWILD_INFERENCE_BUNDLE or place bundle at checkpoints/inference_bundle.pt.",
        )

    predictions = inference.predict(
        lat,
        lon,
        top_k=top_k,
        score_threshold=threshold,
    )
    return PredictResponse(
        lat=lat,
        lon=lon,
        top_k=top_k,
        threshold=threshold,
        n_results=len(predictions),
        predictions=predictions,
    )


@app.get("/api/predict/batch", response_model=PredictBatchResponse)
def predict_species_batch(
    coords: str = Query(
        ...,
        description=("Comma-separated lat,lon pairs. Example: 25.0,-100.0,26.5,-99.0"),
    ),
    top_k: int = Query(20, ge=1, le=500),
    threshold: float = Query(0.0, ge=0.0, le=1.0),
) -> PredictBatchResponse:
    """Batch prediction for multiple coordinates.

    Coordinates are passed as a flat comma-separated string of
    alternating lat,lon values.

    Args:
        coords: Flat comma-separated lat,lon pairs.
        top_k: Number of top-scoring species per coordinate.
        threshold: Minimum sigmoid score.

    Returns:
        A list of per-coordinate prediction results.
    """
    if not inference.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="Inference model not loaded.",
        )

    parts = [float(v.strip()) for v in coords.split(",")]
    if len(parts) % 2 != 0:
        raise HTTPException(status_code=400, detail="coords must have an even number of values (lat,lon pairs).")

    coordinate_list = [(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    if len(coordinate_list) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 coordinate pairs per batch request.")

    batch_results = inference.predict_batch(
        coordinate_list,
        top_k=top_k,
        score_threshold=threshold,
    )
    return PredictBatchResponse(
        n_coordinates=len(coordinate_list),
        top_k=top_k,
        threshold=threshold,
        results=[
            CoordinatePredictions(
                lat=lat,
                lon=lon,
                n_results=len(preds),
                predictions=preds,
            )
            for (lat, lon), preds in zip(coordinate_list, batch_results)
        ],
    )


@app.get("/api/predict/heatmap", response_model=PredictHeatmapResponse)
def predict_species_heatmap(
    species_key: int = Query(..., description="GBIF species key."),
    min_lat: float = Query(..., ge=-90, le=90, description="Southern edge of bounding box."),
    min_lon: float = Query(..., ge=-180, le=180, description="Western edge of bounding box."),
    max_lat: float = Query(..., ge=-90, le=90, description="Northern edge of bounding box."),
    max_lon: float = Query(..., ge=-180, le=180, description="Eastern edge of bounding box."),
    resolution: float | None = Query(
        None, gt=0, le=10, description="Grid cell size in degrees. Defaults to model native (0.25)."
    ),
    include_source: bool = Query(
        False, description="Include per-cell feature source (`sampled` or `cell_table`) for debugging."
    ),
    feature_mode: str = Query(
        "auto",
        description="Feature source strategy: auto, prefer_cell_table, cell_table_only, sampled_only.",
    ),
    max_cells: int = Query(
        20000,
        ge=100,
        le=2_000_000,
        description="Hard cap on output heatmap cells to avoid OOM.",
    ),
) -> PredictHeatmapResponse:
    """Compute a probability grid for one species over a bounding box.

    Returns per-cell scores suitable for rendering a heat map.
    All cells within the bounding box are evaluated in a single vectorized
    forward pass.

    Args:
        species_key: GBIF species key (must exist in the loaded model).
        min_lat: Southern edge latitude.
        min_lon: Western edge longitude.
        max_lat: Northern edge latitude.
        max_lon: Eastern edge longitude.
        resolution: Grid cell size in degrees (default: model native).

    Returns:
        A dict containing species_key, bbox, resolution, cell count, and
        a list of ``{lat, lon, score}`` entries for every cell that has
        environmental data.
    """
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="Inference model not loaded.")
    _validate_heatmap_bbox(min_lat, min_lon, max_lat, max_lon)
    try:
        result = inference.predict_heatmap(
            species_key,
            (min_lat, min_lon, max_lat, max_lon),
            resolution=resolution,
            include_source=include_source,
            feature_mode=feature_mode,
            max_cells=max_cells,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PredictHeatmapResponse(**result)


@app.get("/api/predict/heatmap/stream")
def predict_species_heatmap_stream(
    species_key: int = Query(..., description="GBIF species key."),
    min_lat: float = Query(..., ge=-90, le=90, description="Southern edge of bounding box."),
    min_lon: float = Query(..., ge=-180, le=180, description="Western edge of bounding box."),
    max_lat: float = Query(..., ge=-90, le=90, description="Northern edge of bounding box."),
    max_lon: float = Query(..., ge=-180, le=180, description="Eastern edge of bounding box."),
    resolution: float | None = Query(
        None, gt=0, le=10, description="Grid cell size in degrees. Defaults to model native (0.25)."
    ),
    include_source: bool = Query(
        False, description="Include per-cell feature source (`sampled` or `cell_table`) for debugging."
    ),
    feature_mode: str = Query(
        "auto",
        description="Feature source strategy: auto, prefer_cell_table, cell_table_only, sampled_only.",
    ),
    max_cells: int = Query(
        20000,
        ge=100,
        le=2_000_000,
        description="Hard cap on output heatmap cells to avoid OOM.",
    ),
) -> StreamingResponse:
    """Stream heatmap cells as NDJSON.

    Emits one line of JSON per event:
    - ``{"type": "meta", ...}``
    - many ``{"type": "cell", ...}``
    - final ``{"type": "done", "n_cells": N}``
    """
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="Inference model not loaded.")
    _validate_heatmap_bbox(min_lat, min_lon, max_lat, max_lon)

    try:
        stream_result = inference.predict_heatmap_stream(
            species_key,
            (min_lat, min_lon, max_lat, max_lon),
            resolution=resolution,
            include_source=include_source,
            feature_mode=feature_mode,
            max_cells=max_cells,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _build_heatmap_stream_response(stream_result)


@app.post("/api/predict/heatmap-jobs", response_model=HeatmapJobResponse)
def create_predict_heatmap_job(payload: HeatmapJobCreateRequest) -> HeatmapJobResponse:
    """Create a cancellable heatmap job resource."""
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="Inference model not loaded.")
    _prune_heatmap_jobs()
    _validate_heatmap_bbox(payload.min_lat, payload.min_lon, payload.max_lat, payload.max_lon)

    job_id = uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    job = {
        "job_id": job_id,
        "status": "created",
        "created_at": created_at,
        "params": payload.model_dump(),
        "cancel_event": threading.Event(),
        "started_at": None,
        "finished_at": None,
    }
    with _heatmap_jobs_lock:
        _heatmap_jobs[job_id] = job

    return HeatmapJobResponse(
        job_id=job_id,
        status="created",
        created_at=created_at,
        stream_url=f"/api/predict/heatmap-jobs/{job_id}/stream",
        cancel_url=f"/api/predict/heatmap-jobs/{job_id}",
    )


@app.get("/api/predict/heatmap-jobs/{job_id}/stream")
def stream_predict_heatmap_job(job_id: str) -> StreamingResponse:
    """Stream job results as NDJSON and support cancellation via DELETE."""
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="Inference model not loaded.")

    _prune_heatmap_jobs()
    _get_heatmap_job(job_id)

    with _heatmap_jobs_lock:
        job = _heatmap_jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Unknown heatmap job {job_id}.")
        if job["status"] == "cancelled":
            raise HTTPException(status_code=409, detail=f"Heatmap job {job_id} is cancelled.")
        if job["status"] == "running":
            raise HTTPException(status_code=409, detail=f"Heatmap job {job_id} is already streaming.")
        job["status"] = "running"
        job["started_at"] = datetime.now(timezone.utc).isoformat()

    params = job["params"]
    cancel_event: threading.Event = job["cancel_event"]

    try:
        stream_result = inference.predict_heatmap_stream(
            params["species_key"],
            (params["min_lat"], params["min_lon"], params["max_lat"], params["max_lon"]),
            resolution=params.get("resolution"),
            include_source=params.get("include_source", False),
            feature_mode=params.get("feature_mode", "prefer_cell_table"),
            max_cells=params.get("max_cells", 20000),
            cancel_check=cancel_event.is_set,
        )
    except KeyError as exc:
        with _heatmap_jobs_lock:
            job["status"] = "failed"
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        with _heatmap_jobs_lock:
            job["status"] = "failed"
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def _on_cancel(_yielded: int) -> None:
        with _heatmap_jobs_lock:
            tracked = _heatmap_jobs.get(job_id)
            if tracked is None:
                return
            tracked["status"] = "cancelled"
            tracked["finished_at"] = datetime.now(timezone.utc).isoformat()

    def _on_done(_yielded: int) -> None:
        with _heatmap_jobs_lock:
            tracked = _heatmap_jobs.get(job_id)
            if tracked is None:
                return
            tracked["status"] = "cancelled" if cancel_event.is_set() else "completed"
            tracked["finished_at"] = datetime.now(timezone.utc).isoformat()

    return _build_heatmap_stream_response(
        stream_result,
        job_id=job_id,
        cancel_check=cancel_event.is_set,
        on_cancel=_on_cancel,
        on_done=_on_done,
    )


@app.delete("/api/predict/heatmap-jobs/{job_id}", response_model=HeatmapJobDeleteResponse)
def cancel_predict_heatmap_job(job_id: str) -> HeatmapJobDeleteResponse:
    """Cancel a stale heatmap job."""
    _prune_heatmap_jobs()
    _get_heatmap_job(job_id)
    with _heatmap_jobs_lock:
        job = _heatmap_jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Unknown heatmap job {job_id}.")
        cancel_event: threading.Event = job["cancel_event"]
        if not cancel_event.is_set():
            cancel_event.set()
        if job["status"] == "created":
            job["status"] = "cancelled"
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
        elif job["status"] == "running":
            job["status"] = "cancelling"

        current_status = job["status"]

    return HeatmapJobDeleteResponse(job_id=job_id, status=current_status)


@app.get("/api/predict/info", response_model=PredictInfoResponse)
def predict_model_info() -> PredictInfoResponse:
    """Return metadata about the loaded inference model.

    Returns:
        Species count, cell count, and per-species metadata.
    """
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="Inference model not loaded.")

    return PredictInfoResponse(
        loaded=True,
        n_species=len(inference.known_species()),
        n_cells=inference.cell_count(),
        species_keys=inference.known_species(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
