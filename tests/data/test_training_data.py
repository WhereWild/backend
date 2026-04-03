from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts.machine_learning.train import data as training_data


class _ReversePermutationGenerator:
    def permutation(self, n: int) -> np.ndarray:
        return np.arange(n - 1, -1, -1)


def _write_split_part(root: Path, *, part_name: str, presence_label: int) -> None:
    split_dir = root / "split=train"
    split_dir.mkdir(parents=True, exist_ok=True)

    scalar_feature = [float(presence_label)]
    scalar_mask = [0.0]
    table = pa.table(
        {
            **{
                feature_col: pa.array([scalar_feature], type=pa.list_(pa.float32()))
                for feature_col in training_data.FEATURE_COLUMNS
            },
            **{
                mask_col: pa.array([scalar_mask], type=pa.list_(pa.float32()))
                for mask_col in training_data.MASK_COLUMNS
            },
            "species_key": pa.array([101], type=pa.int64()),
            "presence_label": pa.array([presence_label], type=pa.int8()),
            "sample_weight": pa.array([1.0], type=pa.float32()),
            "cell_id": pa.array([presence_label + 1], type=pa.int64()),
        }
    )
    pq.write_table(table, split_dir / part_name)


def _write_empty_split_part(root: Path, *, part_name: str) -> None:
    split_dir = root / "split=train"
    split_dir.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            **{feature_col: pa.array([], type=pa.list_(pa.float32())) for feature_col in training_data.FEATURE_COLUMNS},
            **{mask_col: pa.array([], type=pa.list_(pa.float32())) for mask_col in training_data.MASK_COLUMNS},
            "species_key": pa.array([], type=pa.int64()),
            "presence_label": pa.array([], type=pa.int8()),
            "sample_weight": pa.array([], type=pa.float32()),
            "cell_id": pa.array([], type=pa.int64()),
        }
    )
    pq.write_table(table, split_dir / part_name)


def test_streaming_dataset_can_shuffle_fragment_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_split_part(tmp_path, part_name="part-0.parquet", presence_label=1)
    _write_split_part(tmp_path, part_name="part-1.parquet", presence_label=0)

    dataset = training_data.StreamingTrainingDataset(tmp_path, split="train")

    unshuffled_labels = [int(batch["presence_label"][0].item()) for batch in dataset._iter_record_batches()]
    assert unshuffled_labels == [1, 0]

    monkeypatch.setattr(training_data.np.random, "default_rng", lambda seed: _ReversePermutationGenerator())
    shuffled_labels = [
        int(batch["presence_label"][0].item()) for batch in dataset._iter_record_batches(shuffle_fragments=True)
    ]
    assert shuffled_labels == [0, 1]


def test_chunk_cached_batches_respect_fragment_shuffle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_split_part(tmp_path, part_name="part-0.parquet", presence_label=1)
    _write_split_part(tmp_path, part_name="part-1.parquet", presence_label=0)

    dataset = training_data.StreamingTrainingDataset(tmp_path, split="train")
    monkeypatch.setattr(training_data.np.random, "default_rng", lambda seed: _ReversePermutationGenerator())

    iterator = training_data.make_chunk_cached_batches(
        dataset,
        batch_size=1,
        shuffle=True,
        chunk_rows=1,
        prefetch_chunks=1,
        shuffle_mode="block",
        shuffle_block_rows=1,
        adaptive_prefetch=False,
    )

    labels = [int(batch["presence_label"][0].item()) for batch in iterator]
    assert labels == [0, 1]


def test_list_column_to_2d_numpy_rejects_variable_length_lists() -> None:
    column = pa.array([[1.0], [1.0, 2.0]], type=pa.list_(pa.float32()))

    with pytest.raises(ValueError, match="Variable-length list column encountered"):
        training_data._list_column_to_2d_numpy(column, "bioclimate_features")


def test_probe_feature_dims_raises_for_empty_split(tmp_path: Path) -> None:
    _write_empty_split_part(tmp_path, part_name="part-0.parquet")
    split_ds = training_data.load_split_table(tmp_path, "train")

    with pytest.raises(ValueError, match="Split dataset is empty"):
        training_data._probe_feature_dims(split_ds)


def test_record_batch_to_tensors_zeroes_masked_features() -> None:
    record_batch = pa.record_batch(
        [
            *[pa.array([[value]], type=pa.list_(pa.float32())) for value in [1.0, 2.0, 3.0, 4.0, 5.0]],
            *[pa.array([[value]], type=pa.list_(pa.float32())) for value in [0.0, 1.0, 0.0, 0.0, 0.0]],
            pa.array([101], type=pa.int64()),
            pa.array([1], type=pa.int8()),
            pa.array([1.0], type=pa.float32()),
            pa.array([1], type=pa.int64()),
        ],
        names=[
            *training_data.FEATURE_COLUMNS,
            *training_data.MASK_COLUMNS,
            "species_key",
            "presence_label",
            "sample_weight",
            "cell_id",
        ],
    )

    tensors = training_data._record_batch_to_tensors(record_batch)

    assert tensors["features"].tolist() == [[1.0, 0.0, 3.0, 4.0, 5.0, 0.0, 1.0, 0.0, 0.0, 0.0]]
    assert tensors["recon_target"].tolist() == [[1.0, 0.0, 3.0, 4.0, 5.0]]
    assert tensors["masks"].tolist() == [[0.0, 1.0, 0.0, 0.0, 0.0]]
