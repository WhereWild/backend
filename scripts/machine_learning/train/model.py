"""Model definitions for the Darwin Species Distribution Model."""

from __future__ import annotations

import torch
import torch.nn as nn


class ResidualBlock(nn.Module):
    """Single residual MLP block: Linear → LayerNorm → GELU with skip connection."""

    def __init__(self, dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x) + x


class SharedEncoder(nn.Module):
    """Shared global encoder (model card Section 2.1).

    3-layer MLP with residual connections, GELU, LayerNorm.
    Projects concatenated feature vector to a fixed-size embedding.
    """

    def __init__(
        self,
        input_dim: int,
        embed_dim: int = 128,
        hidden_dim: int = 256,
    ) -> None:
        super().__init__()
        self.project_in = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )
        self.residual_blocks = nn.Sequential(
            ResidualBlock(hidden_dim),
            ResidualBlock(hidden_dim),
        )
        self.project_out = nn.Sequential(
            nn.Linear(hidden_dim, embed_dim),
            nn.LayerNorm(embed_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.project_in(x)
        h = self.residual_blocks(h)
        return self.project_out(h)


class SpeciesHead(nn.Module):
    """Per-species binary classifier on frozen encoder embeddings (model card Section 2.2).

    Default: logistic regression (w^T z + b).
    """

    def __init__(self, embed_dim: int = 128) -> None:
        super().__init__()
        self.linear = nn.Linear(embed_dim, 1)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        return self.linear(z).squeeze(-1)


class AuxDecoder(nn.Module):
    """Auxiliary reconstruction head for self-supervised encoder pretraining.

    Reconstructs original input features from the encoder embedding.
    Used with MSE loss to encourage informative representations.
    """

    def __init__(self, embed_dim: int, output_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 2),
            nn.GELU(),
            nn.Linear(embed_dim * 2, output_dim),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        return self.net(z)
