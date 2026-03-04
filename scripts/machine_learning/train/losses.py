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


def contrastive_loss(
    embeddings: torch.Tensor,
    cell_ids_encoded: torch.Tensor,
    temperature: float = 0.1,
) -> torch.Tensor:
    """Simple spatial contrastive loss for encoder pretraining.

    Pairs with matching cell_id are positive; others are negative.
    Uses NT-Xent style loss on cosine similarity.

    Args:
        embeddings: (B, D) encoder output.
        cell_ids_encoded: (B,) integer-encoded cell ids.
        temperature: softmax temperature.
    """
    embeddings = F.normalize(embeddings, dim=1)
    sim = embeddings @ embeddings.T / temperature  # (B, B)

    # Positive mask: same cell_id pairs (excluding self)
    pos_mask = cell_ids_encoded.unsqueeze(0) == cell_ids_encoded.unsqueeze(1)
    eye = torch.eye(sim.shape[0], device=sim.device, dtype=torch.bool)
    pos_mask = pos_mask & ~eye

    if not pos_mask.any():
        return torch.tensor(0.0, device=embeddings.device, requires_grad=True)

    # NT-Xent: for each anchor with at least one positive, compute cross-entropy
    # against all non-self entries
    log_softmax = sim - torch.logsumexp(sim.masked_fill(eye, float("-inf")), dim=1, keepdim=True)
    pos_log_prob = (log_softmax * pos_mask.float()).sum(dim=1)
    num_positives = pos_mask.float().sum(dim=1)
    has_positive = num_positives > 0
    if not has_positive.any():
        return torch.tensor(0.0, device=embeddings.device, requires_grad=True)

    loss_per_anchor = -pos_log_prob[has_positive] / num_positives[has_positive]
    return loss_per_anchor.mean()
