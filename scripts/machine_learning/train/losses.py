"""Loss functions for Darwin SDM training."""

from __future__ import annotations

import torch
import torch.nn.functional as F


def _weighted_mean(loss: torch.Tensor, weights: torch.Tensor | None) -> torch.Tensor:
    """Compute mean(loss) or sum(weights * loss) / sum(weights)."""
    if weights is None:
        return loss.mean()
    weighted = loss * weights
    denom = torch.clamp(weights.sum(), min=1e-12)
    return weighted.sum() / denom


def nnpu_loss(
    f_positive: torch.Tensor,
    f_unlabeled: torch.Tensor,
    prior_pi: float,
    *,
    weights_positive: torch.Tensor | None = None,
    weights_unlabeled: torch.Tensor | None = None,
) -> torch.Tensor:
    """Non-negative PU risk estimator (model card Section 3.2).

    R(f) = pi * E_P[l(f(x))] + max(0, E_U[l(-f(x))] - pi * E_P[l(-f(x))])

    where l is the logistic (softplus) loss.

    Args:
        f_positive: raw logits for known-positive samples.
        f_unlabeled: raw logits for unlabeled/background samples.
        prior_pi: class prior P(y=1|s), estimated from data.
        weights_positive: optional per-sample weights for positives.
        weights_unlabeled: optional per-sample weights for unlabeled.

    Returns:
        Scalar nnPU loss.
    """
    if f_positive.numel() == 0 or f_unlabeled.numel() == 0:
        return torch.tensor(0.0, device=f_positive.device, requires_grad=True)

    # Logistic loss: l(t) = softplus(-t) = log(1 + exp(-t))
    pos_pos_loss = F.softplus(-f_positive)  # l(f(x)) on positives
    pos_neg_loss = F.softplus(f_positive)  # l(-f(x)) on positives
    unl_neg_loss = F.softplus(f_unlabeled)  # l(-f(x)) on unlabeled

    positive_risk = prior_pi * _weighted_mean(pos_pos_loss, weights_positive)
    negative_risk = _weighted_mean(unl_neg_loss, weights_unlabeled) - prior_pi * _weighted_mean(
        pos_neg_loss,
        weights_positive,
    )

    # Non-negative correction: clamp to prevent pathological gradient
    return positive_risk + torch.clamp(negative_risk, min=0.0)


def reconstruction_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
) -> torch.Tensor:
    """Masked MSE reconstruction loss for encoder pretraining.

    Only penalizes reconstruction of observed (non-missing) features.

    Args:
        prediction: reconstructed features from AuxDecoder.
        target: original input features (with missing values zeroed).
        mask: missingness mask (1=missing, 0=observed).
    """
    observed = 1.0 - mask  # invert: 1=observed, 0=missing
    if observed.sum() == 0:
        return torch.tensor(0.0, device=prediction.device, requires_grad=True)
    diff_sq = (prediction - target) ** 2
    return (diff_sq * observed).sum() / observed.sum()
