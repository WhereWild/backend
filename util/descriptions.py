"""Rule-based taxon description builder (no GenAI)."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

from util import indexing, summary_stats


_HABITAT_CATEGORICAL_LAYERS = ("landcover", "koppen_geiger")
_OUTLIER_VARIABLES: dict[str, dict[str, str]] = {
    "elevation": {
        "metric": "mean",
        "high": "occurs at higher elevations",
        "low": "occurs at lower elevations",
    },
    "bio_1": {
        "metric": "mean",
        "high": "tolerates warmer temperatures",
        "low": "can tolerate colder temperatures",
    },
    "bio_6": {
        "metric": "mean",
        "high": "experiences milder cold-season temperatures",
        "low": "can tolerate harsher cold-season temperatures",
    },
    "bio_12": {
        "metric": "mean",
        "high": "tolerates wetter conditions",
        "low": "tolerates drier conditions",
    },
}


def _find_ancestor_by_rank(taxon: dict[str, Any], rank: str) -> Optional[dict[str, Any]]:
    from util import taxa_navigation

    target = taxa_navigation.canonical_rank(rank)
    current = taxon
    while current is not None:
        if taxa_navigation.canonical_rank(current.get("rank")) == target:
            return current
        current = taxa_navigation.get_parent_taxon(current)
    return None


def _top_categorical_phrase(
    taxon_dir: Path,
    variable_id: str,
    label: str,
) -> Optional[str]:
    payload = summary_stats.load_categorical_distribution(taxon_dir, variable_id)
    if not payload:
        return None
    distribution = payload.get("distribution") or []
    if not distribution:
        return None

    def entry_name(entry: dict[str, Any]) -> str:
        return str(
            entry.get("short_name")
            or entry.get("class_name")
            or entry.get("value")
            or ""
        ).strip()

    grouped: dict[str, list[dict[str, Any]]] = {}
    ungrouped: list[dict[str, Any]] = []
    for entry in distribution:
        group = entry.get("group")
        if group:
            grouped.setdefault(str(group), []).append(entry)
        else:
            ungrouped.append(entry)

    aggregated: list[dict[str, Any]] = []
    for group, entries in grouped.items():
        if len(entries) >= 2:
            frac = sum(float(e.get("fraction") or 0.0) for e in entries)
            group_label = entries[0].get("group_label") or entries[0].get("group") or group
            name = str(group_label).replace("_", " ").strip()
            aggregated.append({"name": name, "fraction": frac})
        else:
            aggregated.append({"name": entry_name(entries[0]), "fraction": float(entries[0].get("fraction") or 0.0)})

    for entry in ungrouped:
        aggregated.append({"name": entry_name(entry), "fraction": float(entry.get("fraction") or 0.0)})

    ranked = sorted(aggregated, key=lambda entry: float(entry.get("fraction") or 0.0), reverse=True)
    top = ranked[0]
    top_name = str(top.get("name") or "").strip()
    top_frac = float(top.get("fraction") or 0.0)
    if not top_name:
        return None

    significant = [entry for entry in ranked if float(entry.get("fraction") or 0.0) >= 0.10]
    if top_frac < 0.20 and len(significant) >= 5:
        return f"across a broad range of {label}"

    if len(ranked) >= 2:
        second = ranked[1]
        second_name = str(second.get("name") or "").strip()
        second_frac = float(second.get("fraction") or 0.0)
        if top_frac >= 0.20 and second_frac >= 0.15 and (top_frac + second_frac) >= 0.50:
            if second_name:
                return f"often in {top_name} and {second_name}"

    if top_frac >= 0.30:
        return f"primarily in {top_name}"
    if top_frac >= 0.20:
        return f"often in {top_name}"
    return None


def _best_outlier_phrase(
    taxon: dict[str, Any],
    taxon_dir: Path,
) -> Optional[str]:
    from util import taxa_navigation

    family = _find_ancestor_by_rank(taxon, "FAMILY")
    family_id = family.get("taxon_key") if family else None
    family_common = None
    family_name = None
    if family:
        family_name = family.get("scientific_name")
        common_names = taxa_navigation.extract_common_names_for_language(
            family, language=taxa_navigation.CONFIG.common_name_language
        )
        if common_names:
            family_common = common_names[0]

    best: Tuple[float, str] | None = None
    for variable_id, rules in _OUTLIER_VARIABLES.items():
        metric = rules["metric"]
        ranks = indexing.load_relative_ranks(taxon_dir, variable_id)
        if not ranks:
            continue
        if family_id:
            ranks = [entry for entry in ranks if str(entry.get("ancestorTaxonId")) == str(family_id)]
        if not ranks:
            continue
        metric_entries = [entry for entry in ranks if entry.get("metric") == metric]
        if not metric_entries:
            continue
        entry = metric_entries[0]
        percentile = entry.get("percentile")
        if percentile is None:
            continue
        try:
            pct = float(percentile)
        except (TypeError, ValueError):
            continue
        if pct >= 0.90:
            phrase = rules["high"]
        elif pct <= 0.10:
            phrase = rules["low"]
        else:
            continue
        distance = abs(pct - 0.5)
        label = family_common or family_name or entry.get("context") or "related taxa"
        outlier_text = f"Compared to other {label}, it {phrase}."
        if best is None or distance > best[0]:
            best = (distance, outlier_text)
    return best[1] if best else None


def _strip_phrase(phrase: str) -> str:
    for prefix in ("often in ", "primarily in ", "across a broad range of "):
        if phrase.startswith(prefix):
            return phrase[len(prefix) :].strip()
    return phrase.strip()


def _ensure_climate_suffix(text: str) -> str:
    lowered = text.lower()
    if "climate" in lowered:
        return text
    return f"{text} climates"


def _top_level_locations(
    taxon_id: int,
    limit: int = 3,
    min_fraction: float = 0.02,
) -> tuple[list[str], int]:
    from util import gis_lookup
    from util.config import load_config

    config = load_config("global")
    scope = config.location_scope_by_level.get(0, "gadm_level0")
    counts = gis_lookup.location_taxa_counts()
    if not counts:
        return [], 0
    _, mapping = gis_lookup.load_location_catalog()
    entries: list[tuple[str, int]] = []
    for (scope_key, gid), taxa in counts.items():
        if scope_key != scope:
            continue
        taxon_count = taxa.get(taxon_id)
        if not taxon_count:
            continue
        record = mapping.get(gid)
        if record and record.name:
            entries.append((record.name, int(taxon_count)))
    if not entries:
        return [], 0
    total_count = sum(count for _name, count in entries)
    if total_count <= 0:
        return [], 0
    filtered = [
        (name, count)
        for name, count in entries
        if (count / total_count) >= min_fraction
    ]
    if not filtered:
        return [], 0
    filtered.sort(key=lambda item: item[1], reverse=True)
    unique = []
    seen = set()
    for name, _count in filtered:
        if name in seen:
            continue
        seen.add(name)
        unique.append(name)
    total = len(unique)
    if limit > 0:
        return unique[:limit], total
    return unique, total


def build_taxon_description(taxon: dict[str, Any]) -> str:
    from util import taxa_navigation

    timing_enabled = True
    t_start = time.perf_counter()
    step_marks: list[tuple[str, float]] = []

    scientific_name = (taxon.get("scientific_name") or "").replace("_", " ").strip()
    common_names = taxa_navigation.extract_common_names_for_language(
        taxon, language=taxa_navigation.CONFIG.common_name_language
    )
    common_name = common_names[0] if common_names else None
    taxon_dir = Path(taxon["path"])
    if not scientific_name:
        return ""

    landcover_phrase = _top_categorical_phrase(taxon_dir, "landcover", "habitats")
    if timing_enabled:
        step_marks.append(("landcover_ms", time.perf_counter()))
    koppen_phrase = _top_categorical_phrase(taxon_dir, "koppen_geiger", "climates")
    if timing_enabled:
        step_marks.append(("koppen_ms", time.perf_counter()))

    family = _find_ancestor_by_rank(taxon, "FAMILY")
    family_common = None
    family_name = None
    if family:
        family_name = (family.get("scientific_name") or "").replace("_", " ").strip()
        common_names = taxa_navigation.extract_common_names_for_language(
            family, language=taxa_navigation.CONFIG.common_name_language
        )
        if common_names:
            family_common = common_names[0]

    if common_name:
        subject = f"The {common_name} ({scientific_name})"
    else:
        subject = scientific_name

    if family_common:
        opener = f"{subject} is a species of {family_common}"
    elif family_name:
        opener = f"{subject} is a species in the family {family_name}"
    else:
        opener = f"{subject} is a species"

    sentences: list[str] = []
    if landcover_phrase or koppen_phrase:
        habitat_text = _strip_phrase(landcover_phrase) if landcover_phrase else ""
        climate_text = _strip_phrase(koppen_phrase) if koppen_phrase else ""
        if climate_text:
            climate_text = _ensure_climate_suffix(climate_text)
        if habitat_text and climate_text:
            sentences.append(f"{opener} that can be found in {habitat_text} in {climate_text}.")
        elif habitat_text:
            sentences.append(f"{opener} that can be found in {habitat_text}.")
        else:
            sentences.append(f"{opener} that can be found in {climate_text}.")
    else:
        sentences.append(f"{opener}.")

    outlier_sentence = _best_outlier_phrase(taxon, taxon_dir)
    if timing_enabled:
        step_marks.append(("outlier_ms", time.perf_counter()))
    if outlier_sentence:
        sentences.append(outlier_sentence)

    taxon_id = taxon.get("taxon_key")
    if taxon_id is not None:
        try:
            taxon_id_int = int(taxon_id)
        except (TypeError, ValueError):
            taxon_id_int = None
        if taxon_id_int is not None:
            locations, total = _top_level_locations(taxon_id_int, limit=3)
            if locations:
                if total > len(locations):
                    loc_text = ", ".join(locations[:-1]) + f", and {locations[-1]}"
                    sentences.append(f"It has been recorded in {loc_text}, among others.")
                elif len(locations) == 1:
                    sentences.append(f"It has been recorded in {locations[0]}.")
                else:
                    loc_text = ", ".join(locations[:-1]) + f", and {locations[-1]}"
                    sentences.append(f"It has been recorded in {loc_text}.")

    if timing_enabled:
        t_end = time.perf_counter()
        step_marks.append(("locations_ms", t_end))
        step_times: dict[str, float] = {}
        prev = t_start
        for label, stamp in step_marks:
            step_times[label] = (stamp - prev) * 1000.0
            prev = stamp
        total_ms = (t_end - t_start) * 1000.0
        step_str = " ".join(f"{key}={value:.2f}" for key, value in step_times.items())
        taxon_id_str = taxon.get("taxon_key") or "unknown"
        print(f"[desc-timing] taxon={taxon_id_str} total_ms={total_ms:.2f} {step_str}")

    return " ".join(sentences)
