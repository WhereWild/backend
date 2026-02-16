from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ModelSpec:
    id: str
    description: str


DEFAULT_MODEL_ID = "stub_sum"


def list_models() -> list[ModelSpec]:
    """Return available model ids and descriptions."""
    return [
        ModelSpec(
            id=DEFAULT_MODEL_ID,
            description="Stub model: sum of features normalized to 0–1.",
        )
    ]


def predict(model_id: str, features: np.ndarray) -> np.ndarray:
    """Run a forward pass for a given model id.

    Args:
        model_id: Identifier for the model.
        features: Feature tensor with shape (..., num_features).

    Returns:
        Predictions with shape features.shape[:-1], normalized to [0, 1].
    """
    model_id = (model_id or "").strip()
    if model_id in ("", DEFAULT_MODEL_ID):
        return _predict_stub_sum(features)
    raise ValueError(f"Unknown model_id '{model_id}'")


def _predict_stub_sum(features: np.ndarray) -> np.ndarray:
    """Stub model that sums features and normalizes to [0, 1].

    For multi-layer input, normalizes each layer to [0,1] using fixed global
    bounds so tiles have consistent coloring across boundaries.
    """
    if features.size == 0:
        return np.zeros(features.shape[:-1], dtype=np.float32)

    n_features = features.shape[-1] if features.ndim > 2 else 1

    if n_features == 1:
        # Single layer (likely elevation): use global elevation bounds
        valid_mask = np.any(np.isfinite(features), axis=-1)
        scores = np.nansum(features, axis=-1)
        scores = np.where(valid_mask, scores, np.nan)
        return _normalize_scores(scores, global_min=-500.0, global_max=5000.0)

    # Multi-layer: normalize each layer to [0,1] using fixed bounds, then average
    # Use a generic 0-255 range as fallback (works for most categorical/scaled data)
    # For a real model, this wouldn't matter since it outputs proper probabilities
    normalized_layers = np.empty_like(features)
    for i in range(n_features):
        layer = features[..., i]
        # Use fixed bounds - assume most layers are either:
        # - Elevation-like: -500 to 5000
        # - Categorical/index: 0 to 255
        # We'll use a wide range that captures both reasonably
        lo, hi = -500.0, 5000.0
        normalized_layers[..., i] = (layer - lo) / (hi - lo)

    # Track which pixels have ANY valid data
    valid_mask = np.any(np.isfinite(features), axis=-1)

    # Average the normalized layers (mean instead of sum for consistent 0-1 range)
    scores = np.nanmean(normalized_layers, axis=-1)
    scores = np.where(valid_mask, scores, np.nan)

    # Clip to [0,1]
    return np.clip(scores, 0.0, 1.0).astype(np.float32)


def _normalize_scores(
    scores: np.ndarray,
    *,
    global_min: float | None = None,
    global_max: float | None = None,
) -> np.ndarray:
    """Normalize scores to [0, 1].

    If global_min/global_max are provided, use those for consistent cross-tile normalization.
    Otherwise falls back to per-tile percentiles (which causes visible tile boundaries!).
    """
    finite = scores[np.isfinite(scores)]
    if finite.size == 0:
        return np.zeros_like(scores, dtype=np.float32)

    if global_min is not None and global_max is not None:
        lo, hi = global_min, global_max
    else:
        # WARNING: Per-tile normalization causes inconsistent coloring across tiles!
        lo = float(np.percentile(finite, 2))
        hi = float(np.percentile(finite, 98))

    if hi <= lo:
        hi = lo + 1.0
    normalized = (scores - lo) / (hi - lo)
    return np.clip(normalized, 0.0, 1.0).astype(np.float32)
