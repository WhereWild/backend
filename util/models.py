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
    """Stub model that sums features and normalizes to [0, 1]."""
    if features.size == 0:
        return np.zeros(features.shape[:-1], dtype=np.float32)
    scores = np.nansum(features, axis=-1)
    return _normalize_scores(scores)


def _normalize_scores(scores: np.ndarray) -> np.ndarray:
    finite = scores[np.isfinite(scores)]
    if finite.size == 0:
        return np.zeros_like(scores, dtype=np.float32)
    lo = float(np.percentile(finite, 2))
    hi = float(np.percentile(finite, 98))
    if hi <= lo:
        hi = lo + 1.0
    normalized = (scores - lo) / (hi - lo)
    return np.clip(normalized, 0.0, 1.0).astype(np.float32)
