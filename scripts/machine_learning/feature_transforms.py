"""Shared feature transformation helpers for preprocessing and inference."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from importlib import import_module
from typing import Any

import numpy as np

_feature_contract = import_module("scripts.machine_learning._compat").import_feature_contract()
FEATURE_GROUPS = _feature_contract.FEATURE_GROUPS
feature_template_dict = _feature_contract.feature_template_dict

_SUPPORTED_VALUE_TYPES = frozenset({"numeric", "categorical", "circular"})


def categorical_output_name(feature_name: str, category_value: int | str) -> str:
    """Return a stable one-hot output name for one categorical bucket."""
    return f"{feature_name}__cat_{category_value}"


def categorical_unknown_output_name(feature_name: str) -> str:
    """Return the stable unknown-bucket output name for one categorical feature."""
    return f"{feature_name}__cat_unknown"


def circular_output_names(feature_name: str) -> list[str]:
    """Return sin/cos output names for one circular feature."""
    return [f"{feature_name}__sin", f"{feature_name}__cos"]


def normalize_feature_transform_spec(raw: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Normalize a serialized feature transform spec to a canonical mapping."""
    if raw is None:
        return None

    raw_feature_template = feature_template_dict(raw.get("raw_feature_template", {}))
    transformed_feature_template = feature_template_dict(raw.get("transformed_feature_template", {}))

    normalized_specs: dict[str, dict[str, Any]] = {}
    raw_specs = raw.get("feature_specs", {})
    if not isinstance(raw_specs, Mapping):
        raw_specs = {}

    for feature_name, payload in raw_specs.items():
        if not isinstance(feature_name, str) or not feature_name:
            continue
        if not isinstance(payload, Mapping):
            continue
        value_type = str(payload.get("value_type", "numeric")).strip().lower()
        if value_type not in _SUPPORTED_VALUE_TYPES:
            value_type = "numeric"
        output_features = [
            str(name) for name in payload.get("output_features", []) if isinstance(name, str) and str(name).strip()
        ]
        group_name = str(payload.get("group", "other")).strip().lower()
        if group_name not in FEATURE_GROUPS:
            group_name = "other"

        spec: dict[str, Any] = {
            "group": group_name,
            "value_type": value_type,
            "output_features": output_features,
        }
        if value_type == "numeric":
            spec["mean"] = float(payload.get("mean", 0.0))
            spec["std"] = max(float(payload.get("std", 1.0)), 1e-6)
        elif value_type == "categorical":
            categories = payload.get("categories", [])
            normalized_categories: list[int] = []
            for value in categories:
                try:
                    normalized_categories.append(int(value))
                except (TypeError, ValueError):
                    continue
            spec["categories"] = normalized_categories
        normalized_specs[feature_name] = spec

    return {
        "version": str(raw.get("version", "v1")),
        "raw_feature_template": raw_feature_template,
        "transformed_feature_template": transformed_feature_template,
        "feature_specs": normalized_specs,
    }


def transformed_feature_template_from_spec(spec: Mapping[str, Any] | None) -> dict[str, list[str]] | None:
    """Return the canonical transformed feature template from a spec."""
    normalized = normalize_feature_transform_spec(spec)
    if normalized is None:
        return None
    return feature_template_dict(normalized.get("transformed_feature_template", {}))


def transform_feature_matrices(
    *,
    raw_feature_template: Mapping[str, Sequence[str]],
    raw_values: np.ndarray,
    raw_masks: np.ndarray,
    transform_spec: Mapping[str, Any] | None,
) -> tuple[np.ndarray, np.ndarray, dict[str, list[str]]]:
    """Apply a fitted feature transform spec to raw feature/mask matrices.

    Args:
        raw_feature_template: grouped raw feature names matching the input matrix order.
        raw_values: shape ``(n_rows, raw_dim)`` float32-compatible matrix.
        raw_masks: shape ``(n_rows, raw_dim)`` mask matrix where ``1`` means missing.
        transform_spec: fitted transform spec, or ``None`` to use identity transform.

    Returns:
        ``(values, masks, transformed_template)`` where the returned matrices are
        grouped in canonical feature-group order.
    """
    normalized_raw_template = feature_template_dict(raw_feature_template)
    if raw_values.ndim != 2 or raw_masks.ndim != 2:
        raise ValueError("raw_values and raw_masks must both be 2-d matrices")
    if raw_values.shape != raw_masks.shape:
        raise ValueError("raw_values and raw_masks must have identical shapes")

    normalized_spec = normalize_feature_transform_spec(transform_spec)
    if normalized_spec is None:
        return (
            raw_values.astype(np.float32, copy=False),
            raw_masks.astype(np.float32, copy=False),
            normalized_raw_template,
        )

    feature_specs = normalized_spec["feature_specs"]
    transformed_template = feature_template_dict(normalized_spec["transformed_feature_template"])
    transformed_dim = sum(len(transformed_template[group]) for group in FEATURE_GROUPS)

    values_out = np.zeros((raw_values.shape[0], transformed_dim), dtype=np.float32)
    masks_out = np.ones((raw_values.shape[0], transformed_dim), dtype=np.float32)

    raw_order: list[str] = []
    for group_name in FEATURE_GROUPS:
        raw_order.extend(normalized_raw_template[group_name])
    raw_index = {feature_name: idx for idx, feature_name in enumerate(raw_order)}

    out_index = 0
    for group_name in FEATURE_GROUPS:
        for raw_feature_name in normalized_raw_template[group_name]:
            if raw_feature_name not in raw_index:
                continue
            src_idx = raw_index[raw_feature_name]
            col_values = raw_values[:, src_idx].astype(np.float32, copy=False)
            observed = raw_masks[:, src_idx] <= 0.5
            spec = feature_specs.get(raw_feature_name, None)
            if spec is None:
                spec = {
                    "group": group_name,
                    "value_type": "numeric",
                    "output_features": [raw_feature_name],
                    "mean": 0.0,
                    "std": 1.0,
                }

            value_type = str(spec.get("value_type", "numeric"))
            output_features = [str(name) for name in spec.get("output_features", [])]
            if not output_features:
                if value_type == "numeric":
                    output_features = [raw_feature_name]
                elif value_type == "categorical":
                    categories = [int(value) for value in spec.get("categories", [])]
                    output_features = [
                        *[categorical_output_name(raw_feature_name, value) for value in categories],
                        categorical_unknown_output_name(raw_feature_name),
                    ]
                else:
                    output_features = circular_output_names(raw_feature_name)

            if value_type == "numeric":
                if len(output_features) != 1:
                    raise ValueError(f"numeric feature {raw_feature_name!r} must expand to exactly 1 output feature")
                mean = float(spec.get("mean", 0.0))
                std = max(float(spec.get("std", 1.0)), 1e-6)
                values_out[observed, out_index] = ((col_values[observed] - mean) / std).astype(np.float32, copy=False)
                masks_out[observed, out_index] = 0.0
                out_index += 1
                continue

            if value_type == "categorical":
                categories = [int(value) for value in spec.get("categories", [])]
                category_to_offset = {value: idx for idx, value in enumerate(categories)}
                width = len(output_features)
                if width != len(categories) + 1:
                    raise ValueError(
                        f"categorical feature {raw_feature_name!r} must expand to len(categories)+1 output features"
                    )
                observed_indices = np.flatnonzero(observed)
                if observed_indices.size > 0:
                    masks_out[observed_indices, out_index : out_index + width] = 0.0
                    encoded_values = np.rint(col_values[observed_indices]).astype(np.int64, copy=False)
                    unknown_offset = width - 1
                    bucket_offsets = np.array(
                        [category_to_offset.get(int(value), unknown_offset) for value in encoded_values],
                        dtype=np.int64,
                    )
                    values_out[observed_indices, out_index + bucket_offsets] = 1.0
                out_index += width
                continue

            if value_type == "circular":
                if len(output_features) != 2:
                    raise ValueError(f"circular feature {raw_feature_name!r} must expand to 2 output features")
                observed_indices = np.flatnonzero(observed)
                if observed_indices.size > 0:
                    radians = np.deg2rad(col_values[observed_indices].astype(np.float64, copy=False))
                    values_out[observed_indices, out_index] = np.sin(radians).astype(np.float32, copy=False)
                    values_out[observed_indices, out_index + 1] = np.cos(radians).astype(np.float32, copy=False)
                    masks_out[observed_indices, out_index : out_index + 2] = 0.0
                out_index += 2
                continue

            raise ValueError(f"Unsupported feature value_type {value_type!r} for {raw_feature_name!r}")

    if out_index != transformed_dim:
        raise ValueError(
            f"Transformed output width mismatch: populated {out_index} columns, expected {transformed_dim}"
        )
    return values_out, masks_out, transformed_template
