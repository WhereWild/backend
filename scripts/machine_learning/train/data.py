"""Data loading utilities for training from preprocessed parquet datasets."""

from __future__ import annotations

import math
import queue
import threading
from importlib import import_module
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import torch
from torch.utils.data import Dataset

_feature_contract = import_module("scripts.machine_learning._compat").import_feature_contract()
FEATURE_COLUMNS = _feature_contract.FEATURE_COLUMNS
MASK_COLUMNS = _feature_contract.MASK_COLUMNS

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
META_COLUMNS = ["species_key", "presence_label", "sample_weight", "cell_id"]

MISSING_SENTINEL = -9999.0

# Rows per PyArrow scanner record-batch read from parquet.
# Large enough to amortise per-batch overhead; small enough to keep
# memory bounded during streaming.
_SCAN_BATCH_ROWS = 65_536
_MEMINFO_PATH = "/proc/meminfo"

# Adaptive prefetch pressure thresholds.
# Higher swap usage or lower available RAM reduces queue depth.
_PREFETCH_SWAP_RATIO_CRITICAL = 0.35
_PREFETCH_SWAP_RATIO_HIGH = 0.20
_PREFETCH_SWAP_RATIO_MODERATE = 0.10
_PREFETCH_MEM_AVAILABLE_GIB_CRITICAL = 4.0
_PREFETCH_MEM_AVAILABLE_GIB_HIGH = 8.0
_PREFETCH_MEM_AVAILABLE_GIB_MODERATE = 12.0
_ADAPTIVE_PREFETCH_WAIT_SECONDS = 0.05


def load_split_table(
    data_root: str | Path,
    split: str,
) -> ds.Dataset:
    """Load a single split from the split-partitioned dataset."""
    dataset = ds.dataset(str(data_root), format="parquet", partitioning="hive")
    return dataset.filter(pc.field("split") == split)


def _probe_feature_dims(split_ds: ds.Dataset) -> tuple[int, int]:
    """Read one row to determine (feature_dim, recon_dim) without loading all data."""
    row = split_ds.head(1, columns=[*FEATURE_COLUMNS, *MASK_COLUMNS])
    if row.num_rows == 0:
        raise ValueError("Split dataset is empty; cannot determine feature dimensions.")
    recon_dim = sum(len(row.column(col)[0].as_py() or []) for col in FEATURE_COLUMNS)
    return recon_dim * 2, recon_dim  # (feature_dim = features+masks, recon_dim = features only)


def _list_column_to_2d_numpy(column: pa.Array, column_name: str | None = None) -> np.ndarray:
    """Convert Arrow list/fixed-size-list column to a dense 2D float32 array."""
    column_label = column_name or "<unknown>"

    if pa.types.is_fixed_size_list(column.type):
        list_size = column.type.list_size
        start = column.offset * list_size
        end = start + len(column) * list_size
        values = column.values.to_numpy(zero_copy_only=False)[start:end].astype(np.float32, copy=False)
        return values.reshape((len(column), list_size))

    if pa.types.is_list(column.type) or pa.types.is_large_list(column.type):
        offsets = column.offsets.to_numpy(zero_copy_only=False)
        if len(offsets) <= 1:
            return np.zeros((0, 0), dtype=np.float32)
        value_start = int(offsets[0])
        value_end = int(offsets[-1])
        values = column.values.to_numpy(zero_copy_only=False)[value_start:value_end].astype(np.float32, copy=False)
        lengths = np.diff(offsets)
        width = int(lengths[0]) if lengths.size else 0
        if lengths.size and not np.all(lengths == width):
            min_len = int(lengths.min())
            max_len = int(lengths.max())
            unique_count = int(np.unique(lengths).size)
            raise ValueError(
                "Variable-length list column encountered; expected fixed-width feature vectors "
                f"in column {column_label!r}. Observed list lengths: min={min_len}, max={max_len}, "
                f"unique_count={unique_count}."
            )
        return values.reshape((len(column), width))

    raise TypeError(f"Unsupported Arrow list column type in column {column_label!r}: {column.type}")


def _record_batch_to_tensors(record_batch: pa.RecordBatch) -> dict[str, torch.Tensor]:
    """Convert one Arrow record batch into training tensors.

    Applies the same zeroing and concatenation used by TrainingDataset.
    """
    feats: list[np.ndarray] = []
    msks: list[np.ndarray] = []
    for feat_col, mask_col in zip(FEATURE_COLUMNS, MASK_COLUMNS, strict=True):
        feats.append(_list_column_to_2d_numpy(record_batch.column(feat_col), feat_col))
        msks.append(_list_column_to_2d_numpy(record_batch.column(mask_col), mask_col))
    features = np.concatenate(feats, axis=1).astype(np.float32)
    masks = np.concatenate(msks, axis=1).astype(np.float32)
    features[masks > 0.5] = 0.0
    model_features = np.concatenate([features, masks], axis=1)

    species_col = record_batch.column("species_key").to_numpy(zero_copy_only=False)
    label_col = record_batch.column("presence_label").to_numpy(zero_copy_only=False)
    weight_col = record_batch.column("sample_weight").to_numpy(zero_copy_only=False)

    # Use copy=True for metadata vectors because Arrow-backed NumPy views can
    # be non-writable; torch.from_numpy warns and has undefined behavior for
    # writes on non-writable arrays.

    return {
        "features": torch.from_numpy(model_features),
        "recon_target": torch.from_numpy(features),
        "masks": torch.from_numpy(masks),
        "species_key": torch.from_numpy(np.array(species_col, dtype=np.int64, copy=True)),
        "presence_label": torch.from_numpy(np.array(label_col, dtype=np.int8, copy=True)),
        "sample_weight": torch.from_numpy(np.array(weight_col, dtype=np.float32, copy=True)),
    }


def detect_feature_dims(data_root: str | Path) -> dict[str, int]:
    """Read one row to determine feature vector sizes."""
    dataset = ds.dataset(str(data_root), format="parquet", partitioning="hive")
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
    ) -> None:
        split_ds = load_split_table(data_root, split)
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
    ) -> None:
        self._split_ds = load_split_table(data_root, split)
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
            yield _record_batch_to_tensors(record_batch)


def _yield_batches_from_parts(
    parts: list[dict[str, torch.Tensor]],
    *,
    batch_size: int,
    shuffle: bool,
    shuffle_mode: str,
    shuffle_block_rows: int,
) -> Iterator[dict[str, torch.Tensor]]:
    """Merge tensor parts, optionally shuffle, and yield mini-batches.

    This helper clears ``parts`` in-place after concatenation so callers can
    release references to chunk tensors promptly and keep peak RAM bounded.
    """
    if not parts:
        return
    merged = {key: torch.cat([part[key] for part in parts], dim=0) for key in parts[0]}
    parts.clear()

    n_rows = merged["features"].shape[0]
    if shuffle:
        if shuffle_mode == "global":
            perm = torch.randperm(n_rows)
            merged = {key: value[perm] for key, value in merged.items()}
        elif shuffle_mode == "block":
            block_rows = max(batch_size, shuffle_block_rows)
            block_starts = torch.arange(0, n_rows, block_rows)
            block_order = block_starts[torch.randperm(len(block_starts))]
            for block_start in block_order.tolist():
                block_end = min(block_start + block_rows, n_rows)
                for start in range(block_start, block_end, batch_size):
                    yield {key: value[start : start + batch_size] for key, value in merged.items()}
            return
        else:
            raise ValueError(f"Unsupported shuffle_mode={shuffle_mode!r}. Expected 'global' or 'block'.")

    for start in range(0, n_rows, batch_size):
        yield {key: value[start : start + batch_size] for key, value in merged.items()}


def _read_chunk_parts(
    record_batches: Iterator[dict[str, torch.Tensor]],
    target_rows: int,
) -> list[dict[str, torch.Tensor]]:
    """Read up to target_rows from a record-batch iterator into chunk parts."""
    parts: list[dict[str, torch.Tensor]] = []
    rows = 0
    while rows < target_rows:
        try:
            batch = next(record_batches)
        except StopIteration:
            break
        parts.append(batch)
        rows += int(batch["features"].shape[0])
    return parts


def _read_linux_memory_pressure() -> tuple[int, float] | None:
    """Return (mem_available_bytes, swap_used_ratio) from /proc/meminfo on Linux.

    This helper parses ``/proc/meminfo`` and is intended for Linux systems.
    If ``/proc/meminfo`` does not exist or cannot be read (for example on
    non-Linux platforms or in restricted environments), this returns ``None``.
    Callers must handle the ``None`` case gracefully and fall back to a
    conservative default behaviour.
    """
    try:
        values_kib: dict[str, int] = {}
        with open(_MEMINFO_PATH, "r", encoding="utf-8") as handle:
            for line in handle:
                parts = line.split()
                if len(parts) < 2:
                    continue
                key = parts[0].rstrip(":")
                if key in {"MemAvailable", "SwapTotal", "SwapFree"}:
                    values_kib[key] = int(parts[1])
        mem_available_bytes = values_kib.get("MemAvailable", 0) * 1024
        swap_total = values_kib.get("SwapTotal", 0)
        swap_free = values_kib.get("SwapFree", 0)
        if swap_total <= 0:
            swap_used_ratio = 0.0
        else:
            swap_used_ratio = max(0.0, min(1.0, (swap_total - swap_free) / swap_total))
        return mem_available_bytes, swap_used_ratio
    except OSError:
        return None


def _adaptive_prefetch_target(max_prefetch_chunks: int) -> int:
    """Choose prefetch queue depth based on host memory/swap pressure."""
    pressure = _read_linux_memory_pressure()
    if pressure is None:
        return max_prefetch_chunks

    mem_available_bytes, swap_used_ratio = pressure
    mem_available_gib = mem_available_bytes / (1024**3)

    if swap_used_ratio >= _PREFETCH_SWAP_RATIO_CRITICAL or mem_available_gib < _PREFETCH_MEM_AVAILABLE_GIB_CRITICAL:
        return 1
    if swap_used_ratio >= _PREFETCH_SWAP_RATIO_HIGH or mem_available_gib < _PREFETCH_MEM_AVAILABLE_GIB_HIGH:
        return min(2, max_prefetch_chunks)
    if swap_used_ratio >= _PREFETCH_SWAP_RATIO_MODERATE or mem_available_gib < _PREFETCH_MEM_AVAILABLE_GIB_MODERATE:
        return min(3, max_prefetch_chunks)
    return max_prefetch_chunks


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
        shuffle_mode: str = "global",
        shuffle_block_rows: int = 131_072,
    ) -> None:
        if shuffle_mode not in {"global", "block"}:
            raise ValueError(f"Unsupported shuffle_mode={shuffle_mode!r}. Expected 'global' or 'block'.")
        self._dataset = dataset
        self._batch_size = batch_size
        self._shuffle = shuffle
        self._shuffle_buffer_size = max(batch_size, shuffle_buffer_size)
        self._shuffle_mode = shuffle_mode
        self._shuffle_block_rows = shuffle_block_rows

    def __len__(self) -> int:
        """Estimated batch count based on parquet footer row count."""
        return max(1, math.ceil(self._dataset.row_count / self._batch_size))

    def __iter__(self) -> Iterator[dict[str, torch.Tensor]]:
        buffer: list[dict[str, torch.Tensor]] = []
        buf_rows = 0

        for rb_tensors in self._dataset._iter_record_batches():
            buffer.append(rb_tensors)
            buf_rows += rb_tensors["features"].shape[0]
            if buf_rows >= self._shuffle_buffer_size:
                yield from _yield_batches_from_parts(
                    buffer,
                    batch_size=self._batch_size,
                    shuffle=self._shuffle,
                    shuffle_mode=self._shuffle_mode,
                    shuffle_block_rows=self._shuffle_block_rows,
                )
                buf_rows = 0

        yield from _yield_batches_from_parts(
            buffer,
            batch_size=self._batch_size,
            shuffle=self._shuffle,
            shuffle_mode=self._shuffle_mode,
            shuffle_block_rows=self._shuffle_block_rows,
        )


class ChunkCachedBatchIterator:
    """Batch iterator with bounded in-memory chunk caching.

    Reads one split lazily from parquet, but materializes larger row chunks
    (for example 1-2M rows) into contiguous tensors before yielding batches.
    This keeps memory bounded while reducing scanner and tensor-concatenation
    overhead relative to small-buffer streaming.

    A one-chunk background prefetch overlaps CPU/disk loading of the next
    chunk with model compute over the current chunk's yielded batches.
    """

    def __init__(
        self,
        dataset: StreamingTrainingDataset,
        batch_size: int = 4096,
        shuffle: bool = True,
        chunk_rows: int = 400_000,
        prefetch_chunks: int = 3,
        shuffle_mode: str = "global",
        shuffle_block_rows: int = 131_072,
        adaptive_prefetch: bool = True,
    ) -> None:
        if chunk_rows < batch_size:
            raise ValueError(
                f"chunk_rows must be >= batch_size (got chunk_rows={chunk_rows}, batch_size={batch_size})."
            )
        if prefetch_chunks < 1:
            raise ValueError(f"prefetch_chunks must be >= 1 (got prefetch_chunks={prefetch_chunks}).")
        if shuffle_mode not in {"global", "block"}:
            raise ValueError(f"Unsupported shuffle_mode={shuffle_mode!r}. Expected 'global' or 'block'.")
        self._dataset = dataset
        self._batch_size = batch_size
        self._shuffle = shuffle
        self._chunk_rows = chunk_rows
        self._prefetch_chunks = prefetch_chunks
        self._shuffle_mode = shuffle_mode
        self._shuffle_block_rows = shuffle_block_rows
        self._adaptive_prefetch = adaptive_prefetch

    def __len__(self) -> int:
        """Estimated batch count based on parquet footer row count."""
        return max(1, math.ceil(self._dataset.row_count / self._batch_size))

    def __iter__(self) -> Iterator[dict[str, torch.Tensor]]:
        record_batches = iter(self._dataset._iter_record_batches())
        # Queue maxsize is a hard safety ceiling. Adaptive prefetch is a
        # dynamic soft ceiling enforced by inflight_chunks + condition waits.
        # The producer may intentionally wait even when queue capacity remains
        # under maxsize when adaptive pressure asks for a lower target depth.
        prefetch_queue: queue.Queue[list[dict[str, torch.Tensor]] | None] = queue.Queue(maxsize=self._prefetch_chunks)
        producer_error: list[BaseException] = []
        inflight_chunks = 0
        inflight_cond = threading.Condition()
        stop_requested = threading.Event()

        def _put_with_stop(item: list[dict[str, torch.Tensor]] | None) -> bool:
            """Put an item to the queue unless shutdown is requested."""
            while not stop_requested.is_set():
                try:
                    prefetch_queue.put(item, timeout=0.1)
                    return True
                except queue.Full:
                    continue
            return False

        def _producer() -> None:
            nonlocal inflight_chunks
            try:
                while not stop_requested.is_set():
                    chunk_parts = _read_chunk_parts(record_batches, self._chunk_rows)
                    if not chunk_parts:
                        break
                    with inflight_cond:
                        while self._adaptive_prefetch and not stop_requested.is_set():
                            target_depth = _adaptive_prefetch_target(self._prefetch_chunks)
                            if inflight_chunks < target_depth:
                                break
                            inflight_cond.wait(timeout=_ADAPTIVE_PREFETCH_WAIT_SECONDS)
                        if stop_requested.is_set():
                            break
                        inflight_chunks += 1

                    try:
                        if not _put_with_stop(chunk_parts):
                            with inflight_cond:
                                inflight_chunks = max(0, inflight_chunks - 1)
                                inflight_cond.notify_all()
                            break
                    except BaseException:
                        with inflight_cond:
                            inflight_chunks = max(0, inflight_chunks - 1)
                            inflight_cond.notify_all()
                        raise
            except BaseException as exc:
                producer_error.append(exc)
            finally:
                _put_with_stop(None)

        producer = threading.Thread(target=_producer, daemon=True)
        producer.start()
        try:
            while True:
                chunk_parts = prefetch_queue.get()
                if chunk_parts is None:
                    break
                with inflight_cond:
                    inflight_chunks = max(0, inflight_chunks - 1)
                    inflight_cond.notify_all()
                yield from _yield_batches_from_parts(
                    chunk_parts,
                    batch_size=self._batch_size,
                    shuffle=self._shuffle,
                    shuffle_mode=self._shuffle_mode,
                    shuffle_block_rows=self._shuffle_block_rows,
                )
        finally:
            stop_requested.set()
            with inflight_cond:
                inflight_cond.notify_all()

        producer.join()
        if producer_error:
            raise producer_error[0]


def make_streaming_batches(
    dataset: StreamingTrainingDataset,
    batch_size: int = 4096,
    shuffle: bool = True,
    shuffle_buffer_size: int = 100_000,
    shuffle_mode: str = "global",
    shuffle_block_rows: int = 131_072,
) -> StreamingBatchIterator:
    """Create a streaming batch iterator for a StreamingTrainingDataset."""
    return StreamingBatchIterator(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        shuffle_buffer_size=shuffle_buffer_size,
        shuffle_mode=shuffle_mode,
        shuffle_block_rows=shuffle_block_rows,
    )


def make_chunk_cached_batches(
    dataset: StreamingTrainingDataset,
    batch_size: int = 4096,
    shuffle: bool = True,
    chunk_rows: int = 400_000,
    prefetch_chunks: int = 3,
    shuffle_mode: str = "global",
    shuffle_block_rows: int = 131_072,
    adaptive_prefetch: bool = True,
) -> ChunkCachedBatchIterator:
    """Create a chunk-cached batch iterator for a StreamingTrainingDataset."""
    return ChunkCachedBatchIterator(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        chunk_rows=chunk_rows,
        prefetch_chunks=prefetch_chunks,
        shuffle_mode=shuffle_mode,
        shuffle_block_rows=shuffle_block_rows,
        adaptive_prefetch=adaptive_prefetch,
    )
