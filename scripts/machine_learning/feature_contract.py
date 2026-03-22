"""Shared feature-group contract for ML preprocessing, training, export, and inference."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

FEATURE_GROUPS = ("bioclimate", "landclass", "terrain", "edaphic", "temporal", "other")
SAMPLED_FEATURE_GROUPS = ("bioclimate", "landclass", "terrain", "edaphic")
UNSAMPLED_FEATURE_GROUPS = ("temporal", "other")

FEATURE_COLUMNS = tuple(f"{group}_features" for group in FEATURE_GROUPS)
MASK_COLUMNS = tuple(f"{group}_missing_mask" for group in FEATURE_GROUPS)
GROUP_TO_FEATURE_COLUMN = dict(zip(FEATURE_GROUPS, FEATURE_COLUMNS, strict=True))
FEATURE_COLUMN_TO_GROUP = dict(zip(FEATURE_COLUMNS, FEATURE_GROUPS, strict=True))


def empty_feature_template() -> dict[str, list[str]]:
    """Return an empty feature-template mapping with all expected groups present."""
    return {group: [] for group in FEATURE_GROUPS}


def normalize_feature_template(raw: Mapping[str, Sequence[Any]]) -> dict[str, list[str]]:
    """Coerce raw JSON-like template payloads into the canonical group mapping."""
    template = empty_feature_template()
    for group in FEATURE_GROUPS:
        values = raw.get(group, [])
        template[group] = sorted(str(value) for value in values if isinstance(value, str) and value)
    return template


def feature_template_dict(template: Mapping[str, Sequence[Any]] | object) -> dict[str, list[str]]:
    """Convert a mapping or object with group attributes into canonical template JSON."""
    if isinstance(template, Mapping):
        return normalize_feature_template(template)
    return normalize_feature_template({group: getattr(template, group, []) for group in FEATURE_GROUPS})


def feature_template_counts(template: Mapping[str, Sequence[Any]] | object) -> dict[str, int]:
    """Return per-group feature counts for a template mapping or object."""
    normalized = feature_template_dict(template)
    return {group: len(normalized[group]) for group in FEATURE_GROUPS}


def format_feature_group_counts(template: Mapping[str, Sequence[Any]] | Mapping[str, int] | object) -> str:
    """Format per-group counts for stable logging."""
    counts_map: dict[str, int] = {}
    if isinstance(template, Mapping):
        for group in FEATURE_GROUPS:
            value = template.get(group, 0)
            if isinstance(value, int):
                counts_map[group] = value
            else:
                counts_map = feature_template_counts(template)
                break
        else:
            counts = counts_map
            return ", ".join(f"{group}={counts[group]:,}" for group in FEATURE_GROUPS)
    counts = feature_template_counts(template)
    return ", ".join(f"{group}={counts[group]:,}" for group in FEATURE_GROUPS)
