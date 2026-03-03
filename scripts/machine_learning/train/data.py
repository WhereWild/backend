"""Data loading utilities for training from preprocessed parquet datasets."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pyarrow.compute as pc
import pyarrow.dataset as ds
import torch
from torch.utils.data import Dataset

FEATURE_COLUMNS = ["env_features", "habitat_features", "weather_features"]
MASK_COLUMNS = ["env_missing_mask", "habitat_missing_mask", "weather_missing_mask"]
META_COLUMNS = ["species_key", "presence_label", "sample_weight", "cell_id"]

MISSING_SENTINEL = -9999.0


def load_split_table(
    data_root: str | Path,
    split: str,
    partitioning: str = "hive",
) -> ds.Dataset:
    """Load a single split from the partitioned dataset."""
    dataset = ds.dataset(str(data_root), format="parquet", partitioning=partitioning)
    return dataset.filter(pc.field("split") == split)


def detect_feature_dims(data_root: str | Path, partitioning: str = "hive") -> dict[str, int]:
    """Read one row to determine feature vector sizes."""
    dataset = ds.dataset(str(data_root), format="parquet", partitioning=partitioning)
    row = dataset.head(1)
    dims = {}
    for col in FEATURE_COLUMNS:
        arr = row.column(col)[0].as_py()
        dims[col] = len(arr) if arr else 0
    return dims


class TrainingDataset(Dataset):
    """In-memory dataset for encoder or head training.

    Materializes one split into tensors on construction.
    Suitable for datasets that fit in RAM (up to a few million rows).
    """

    def __init__(
        self,
        data_root: str | Path,
        split: str = "train",
        partitioning: str = "hive",
    ) -> None:
        split_ds = load_split_table(data_root, split, partitioning)
        columns = [*FEATURE_COLUMNS, *MASK_COLUMNS, *META_COLUMNS]
        table = split_ds.to_table(columns=columns)
        df = table.to_pandas()

        features_list = []
        masks_list = []
        for feat_col, mask_col in zip(FEATURE_COLUMNS, MASK_COLUMNS, strict=True):
            feat_np = np.stack(df[feat_col].to_numpy())
            mask_np = np.stack(df[mask_col].to_numpy())
            features_list.append(feat_np)
            masks_list.append(mask_np)

        features = np.concatenate(features_list, axis=1).astype(np.float32)
        masks = np.concatenate(masks_list, axis=1).astype(np.float32)

        # Zero out sentinel values where mask == 1 (missing).
        # The reconstruction target is intentionally the zeroed version: the
        # masked MSE loss only penalises observed positions, so the zero fill
        # in missing slots does not affect the gradient.
        features[masks > 0.5] = 0.0

        self.features = torch.from_numpy(features)
        self.masks = torch.from_numpy(masks)
        self.species_key = torch.from_numpy(df["species_key"].to_numpy().astype(np.int64))
        self.presence_label = torch.from_numpy(df["presence_label"].to_numpy().astype(np.int8))
        self.sample_weight = torch.from_numpy(df["sample_weight"].to_numpy().astype(np.float32))
        self.cell_ids = df["cell_id"].to_numpy()

        # Pre-hash cell_id strings to int64 so they can travel as tensors
        # (needed for contrastive pairing after shuffle).
        cell_id_hashes = np.array(
            [
                int.from_bytes(
                    hashlib.blake2b(str(cid).encode("utf-8"), digest_size=8).digest(),
                    byteorder="big",
                    signed=True,
                )
                for cid in self.cell_ids
            ],
            dtype=np.int64,
        )
        self.cell_id_hash = torch.from_numpy(cell_id_hashes)

        self.feature_dim = self.features.shape[1]
        self.num_rows = self.features.shape[0]

    def pin(self) -> "TrainingDataset":
        """Pin all tensors to page-locked memory for fast GPU transfers."""
        self.features = self.features.pin_memory()
        self.masks = self.masks.pin_memory()
        self.species_key = self.species_key.pin_memory()
        self.presence_label = self.presence_label.pin_memory()
        self.sample_weight = self.sample_weight.pin_memory()
        self.cell_id_hash = self.cell_id_hash.pin_memory()
        return self

    def __len__(self) -> int:
        return self.num_rows

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "features": self.features[idx],
            "masks": self.masks[idx],
            "species_key": self.species_key[idx],
            "presence_label": self.presence_label[idx],
            "sample_weight": self.sample_weight[idx],
            "cell_id_hash": self.cell_id_hash[idx],
        }


class BatchIterator:
    """Fast batch iterator over an in-memory TrainingDataset.

    Replaces DataLoader for tabular data already held as contiguous tensors.
    Yields dict batches via direct tensor slicing (no per-item __getitem__,
    no Python-level collation).  ~10-50x faster than DataLoader for this
    workload because the hot loop is a single torch index_select per tensor.
    """

    def __init__(
        self,
        dataset: TrainingDataset,
        batch_size: int = 4096,
        shuffle: bool = True,
    ) -> None:
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle
        self._n = len(dataset)
        self._n_batches = (self._n + batch_size - 1) // batch_size

    def __len__(self) -> int:
        return self._n_batches

    def __iter__(self):
        if self.shuffle:
            perm = torch.randperm(self._n)
        else:
            perm = torch.arange(self._n)

        ds = self.dataset
        for start in range(0, self._n, self.batch_size):
            idx = perm[start : start + self.batch_size]
            yield {
                "features": ds.features[idx],
                "masks": ds.masks[idx],
                "species_key": ds.species_key[idx],
                "presence_label": ds.presence_label[idx],
                "sample_weight": ds.sample_weight[idx],
                "cell_id_hash": ds.cell_id_hash[idx],
            }


def make_batches(
    dataset: TrainingDataset,
    batch_size: int = 4096,
    shuffle: bool = True,
) -> BatchIterator:
    """Create a fast batch iterator for a TrainingDataset."""
    return BatchIterator(dataset, batch_size=batch_size, shuffle=shuffle)
