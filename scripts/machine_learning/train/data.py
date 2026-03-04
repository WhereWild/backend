"""Data loading utilities for training from preprocessed parquet datasets."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pyarrow.compute as pc
import pyarrow.dataset as ds
import torch
from torch.utils.data import Dataset

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

FEATURE_COLUMNS = ["env_features", "habitat_features", "weather_features"]
MASK_COLUMNS = ["env_missing_mask", "habitat_missing_mask", "weather_missing_mask"]
META_COLUMNS = ["species_key", "presence_label", "sample_weight", "cell_id"]

MISSING_SENTINEL = -9999.0

# Rows per PyArrow scanner record-batch read from parquet.
# Large enough to amortise per-batch overhead; small enough to keep
# memory bounded during streaming.
_SCAN_BATCH_ROWS = 65_536


def load_split_table(
    data_root: str | Path,
    split: str,
    partitioning: str = "hive",
) -> ds.Dataset:
    """Load a single split from the partitioned dataset."""
    dataset = ds.dataset(str(data_root), format="parquet", partitioning=partitioning)
    return dataset.filter(pc.field("split") == split)


def _probe_feature_dims(split_ds: ds.Dataset) -> tuple[int, int]:
    """Read one row to determine (feature_dim, recon_dim) without loading all data."""
    row = split_ds.head(1, columns=[*FEATURE_COLUMNS, *MASK_COLUMNS])
    if row.num_rows == 0:
        raise ValueError("Split dataset is empty; cannot determine feature dimensions.")
    recon_dim = sum(len(row.column(col)[0].as_py() or []) for col in FEATURE_COLUMNS)
    return recon_dim * 2, recon_dim  # (feature_dim = features+masks, recon_dim = features only)


def _record_batch_to_tensors(df) -> dict[str, torch.Tensor]:
    """Convert one pandas record batch into training tensors.

    Applies the same zeroing and concatenation used by TrainingDataset.
    """
    feats: list[np.ndarray] = []
    msks: list[np.ndarray] = []
    for feat_col, mask_col in zip(FEATURE_COLUMNS, MASK_COLUMNS, strict=True):
        feats.append(np.stack(df[feat_col].to_numpy()))
        msks.append(np.stack(df[mask_col].to_numpy()))
    features = np.concatenate(feats, axis=1).astype(np.float32)
    masks = np.concatenate(msks, axis=1).astype(np.float32)
    features[masks > 0.5] = 0.0
    model_features = np.concatenate([features, masks], axis=1)
    return {
        "features": torch.from_numpy(model_features),
        "recon_target": torch.from_numpy(features),
        "masks": torch.from_numpy(masks),
        "species_key": torch.from_numpy(df["species_key"].to_numpy().astype(np.int64)),
        "presence_label": torch.from_numpy(df["presence_label"].to_numpy().astype(np.int8)),
        "sample_weight": torch.from_numpy(df["sample_weight"].to_numpy().astype(np.float32)),
    }


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

        model_features = np.concatenate([features, masks], axis=1).astype(np.float32)

        self.features = torch.from_numpy(model_features)
        self.recon_target = torch.from_numpy(features)
        self.masks = torch.from_numpy(masks)
        self.species_key = torch.from_numpy(df["species_key"].to_numpy().astype(np.int64))
        self.presence_label = torch.from_numpy(df["presence_label"].to_numpy().astype(np.int8))
        self.sample_weight = torch.from_numpy(df["sample_weight"].to_numpy().astype(np.float32))
        self.cell_ids = df["cell_id"].to_numpy()

        self.feature_dim = self.features.shape[1]
        self.recon_dim = self.recon_target.shape[1]
        self.num_rows = self.features.shape[0]

    def pin(self) -> TrainingDataset:
        """Pin all tensors to page-locked memory for fast GPU transfers."""
        self.features = self.features.pin_memory()
        self.recon_target = self.recon_target.pin_memory()
        self.masks = self.masks.pin_memory()
        self.species_key = self.species_key.pin_memory()
        self.presence_label = self.presence_label.pin_memory()
        self.sample_weight = self.sample_weight.pin_memory()
        return self

    def __len__(self) -> int:
        return self.num_rows

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "features": self.features[idx],
            "recon_target": self.recon_target[idx],
            "masks": self.masks[idx],
            "species_key": self.species_key[idx],
            "presence_label": self.presence_label[idx],
            "sample_weight": self.sample_weight[idx],
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
        perm = torch.randperm(self._n) if self.shuffle else torch.arange(self._n)

        ds = self.dataset
        for start in range(0, self._n, self.batch_size):
            idx = perm[start : start + self.batch_size]
            yield {
                "features": ds.features[idx],
                "recon_target": ds.recon_target[idx],
                "masks": ds.masks[idx],
                "species_key": ds.species_key[idx],
                "presence_label": ds.presence_label[idx],
                "sample_weight": ds.sample_weight[idx],
            }


def make_batches(
    dataset: TrainingDataset,
    batch_size: int = 4096,
    shuffle: bool = True,
) -> BatchIterator:
    """Create a fast batch iterator for a TrainingDataset."""
    return BatchIterator(dataset, batch_size=batch_size, shuffle=shuffle)


class StreamingTrainingDataset:
    """Streaming dataset that reads preprocessed parquet splits lazily.

    Unlike TrainingDataset, no data is materialized into RAM at construction.
    The PyArrow scanner reads record-batches from disk on each iteration,
    so peak working memory is determined by the shuffle buffer rather than
    the full split size.

    Suitable for encoder pretraining on large datasets that do not fit in RAM.
    For per-species head training (TrainingDataset) the in-memory approach is
    still preferred because the per-species slice is small.
    """

    def __init__(
        self,
        data_root: str | Path,
        split: str = "train",
        partitioning: str = "hive",
    ) -> None:
        self._split_ds = load_split_table(data_root, split, partitioning)
        self.feature_dim, self.recon_dim = _probe_feature_dims(self._split_ds)
        # count_rows() reads only parquet footers -- no column data is loaded.
        self.row_count: int = self._split_ds.count_rows()

    def _iter_record_batches(self) -> Iterator[dict[str, torch.Tensor]]:
        """Yield one tensor dict per parquet record batch (lazy, re-entrant)."""
        columns = [*FEATURE_COLUMNS, *MASK_COLUMNS, *META_COLUMNS]
        scanner = self._split_ds.scanner(columns=columns, batch_size=_SCAN_BATCH_ROWS)
        for record_batch in scanner.to_batches():
            if record_batch.num_rows == 0:
                continue
            yield _record_batch_to_tensors(record_batch.to_pandas())


class StreamingBatchIterator:
    """Batch iterator over a StreamingTrainingDataset.

    Streams parquet record batches into a bounded shuffle buffer and
    yields mini-batches without fully materialising the split.

    Each call to __iter__ creates a fresh scanner, so iterating multiple
    epochs simply re-iterates the same StreamingBatchIterator instance.
    """

    def __init__(
        self,
        dataset: StreamingTrainingDataset,
        batch_size: int = 4096,
        shuffle: bool = True,
        shuffle_buffer_size: int = 100_000,
    ) -> None:
        self._dataset = dataset
        self._batch_size = batch_size
        self._shuffle = shuffle
        self._shuffle_buffer_size = max(batch_size, shuffle_buffer_size)

    def __len__(self) -> int:
        """Estimated batch count based on parquet footer row count."""
        return max(1, math.ceil(self._dataset.row_count / self._batch_size))

    def __iter__(self) -> Iterator[dict[str, torch.Tensor]]:
        buffer: list[dict[str, torch.Tensor]] = []
        buf_rows = 0

        def _drain() -> Iterator[dict[str, torch.Tensor]]:
            """Merge, optionally shuffle, and yield batches from the buffer."""
            if not buffer:
                return
            merged = {key: torch.cat([b[key] for b in buffer], dim=0) for key in buffer[0]}
            buffer.clear()
            n = merged["features"].shape[0]
            if self._shuffle:
                perm = torch.randperm(n)
                merged = {k: v[perm] for k, v in merged.items()}
            for start in range(0, n, self._batch_size):
                yield {k: v[start : start + self._batch_size] for k, v in merged.items()}

        for rb_tensors in self._dataset._iter_record_batches():
            buffer.append(rb_tensors)
            buf_rows += rb_tensors["features"].shape[0]
            if buf_rows >= self._shuffle_buffer_size:
                yield from _drain()
                buf_rows = 0

        yield from _drain()


def make_streaming_batches(
    dataset: StreamingTrainingDataset,
    batch_size: int = 4096,
    shuffle: bool = True,
    shuffle_buffer_size: int = 100_000,
) -> StreamingBatchIterator:
    """Create a streaming batch iterator for a StreamingTrainingDataset."""
    return StreamingBatchIterator(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        shuffle_buffer_size=shuffle_buffer_size,
    )
