from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import pytest
import torch

from scripts.machine_learning.preprocess_training import pipeline
from scripts.machine_learning.preprocess_training import resume_from_staging, transform
from scripts.machine_learning.train import cli as train_cli
from scripts.machine_learning.train import data as training_data
from scripts.machine_learning.train import export
from scripts.machine_learning.train.model import CombinedSpeciesHead, SharedEncoder, SpeciesHead
from util import inference
from util import gis_lookup


def _write_parquet(path: Path, columns: dict[str, pa.Array]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(columns), path)


def _write_split_part(
    root: Path,
    *,
    split: str,
    part_name: str,
    cell_id: str,
    feature_values: list[float],
    mask_values: list[float],
    species_key: int = 101,
    presence_label: int = 1,
    sample_weight: float = 1.0,
) -> None:
    split_dir = root / f"split={split}"
    split_dir.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            **{
                feature_col: pa.array([[feature_values[idx]]], type=pa.list_(pa.float32()))
                for idx, feature_col in enumerate(training_data.FEATURE_COLUMNS)
            },
            **{
                mask_col: pa.array([[mask_values[idx]]], type=pa.list_(pa.float32()))
                for idx, mask_col in enumerate(training_data.MASK_COLUMNS)
            },
            "species_key": pa.array([species_key], type=pa.int64()),
            "presence_label": pa.array([presence_label], type=pa.int8()),
            "sample_weight": pa.array([sample_weight], type=pa.float32()),
            "cell_id": pa.array([cell_id], type=pa.string()),
        }
    )
    pq.write_table(table, split_dir / part_name)


def _write_inference_bundle(
    path: Path,
    *,
    input_dim: int,
    cell_table: dict[str, torch.Tensor],
    feature_names: dict[str, list[str]],
    species_key: int = 101,
    species_name: str = "Test species",
    embed_dim: int = 4,
    hidden_dim: int = 8,
    combined_species_keys: list[int] | None = None,
    combined_head_state: dict[str, torch.Tensor] | None = None,
    species_meta: dict[int, dict] | None = None,
) -> Path:
    encoder = SharedEncoder(input_dim=input_dim, embed_dim=embed_dim, hidden_dim=hidden_dim)
    head = SpeciesHead(embed_dim=embed_dim)
    if species_meta is None:
        species_meta = {species_key: {"name": species_name}}

    torch.save(
        {
            "bundle_version": 2,
            "model": {
                "input_dim": input_dim,
                "embed_dim": embed_dim,
                "hidden_dim": hidden_dim,
                "encoder_state_dict": encoder.state_dict(),
                "raw_feature_names": feature_names,
            },
            "heads": {
                "head_states": {species_key: head.state_dict()},
                "species_meta": species_meta,
                "combined_head_state": combined_head_state,
                "combined_species_keys": combined_species_keys or [],
            },
            "serving": {
                "cell_table": cell_table,
                "cell_size_deg": 0.25,
            },
        },
        path,
    )
    return path


def test_classify_feature_name_uses_catalog_shape() -> None:
    assert transform.classify_feature_name("clt") == "bioclimate"
    assert transform.classify_feature_name("lithology") == "landclass"
    assert transform.classify_feature_name("landform") == "terrain"
    assert transform.classify_feature_name("temperature_2m_24h") == "temporal"
    assert transform.classify_feature_name("unknown_numeric") is None


def test_normalize_template_payload_reclassifies_legacy_groups() -> None:
    raw = {
        "env": ["bio_1", "landcover"],
        "weather": ["temperature_2m_24h"],
        "legacy": ["custom_measure"],
    }

    template = resume_from_staging._normalize_template_payload(raw)

    assert template == {
        "bioclimate": ["bio_1"],
        "landclass": ["landcover"],
        "terrain": [],
        "temporal": ["temperature_2m_24h"],
        "other": ["custom_measure"],
    }


def test_resume_output_files_reuses_staging_transform_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    staging_dir = tmp_path / "staging"
    output_root = tmp_path / "output"
    staging_meta = staging_dir / "_meta"
    staging_meta.mkdir(parents=True, exist_ok=True)

    feature_template = {
        "bioclimate": ["bio_1"],
        "landclass": [],
        "terrain": [],
        "temporal": [],
        "other": [],
    }
    feature_transforms = {
        "version": "v1",
        "raw_feature_template": feature_template,
        "transformed_feature_template": feature_template,
        "feature_specs": {
            "bio_1": {
                "group": "bioclimate",
                "value_type": "numeric",
                "mean": 0.0,
                "std": 1.0,
                "output_features": ["bio_1"],
            }
        },
    }
    uncatalogued = {"kept_occurrence": [], "skipped_context": []}

    (staging_meta / "feature_template.json").write_text(json.dumps(feature_template), encoding="utf-8")
    (staging_meta / "feature_transforms.json").write_text(json.dumps(feature_transforms), encoding="utf-8")
    (staging_meta / "uncatalogued_columns.json").write_text(json.dumps(uncatalogued), encoding="utf-8")
    (staging_dir / "base_00000.parquet").write_text("placeholder", encoding="utf-8")

    captured: dict[str, object] = {}

    def _fake_write_partitioned_dataset(
        shard_paths: list[Path],
        output_root: Path,
        max_rows_per_file: int,
        metadata_payloads: dict[str, object] | None = None,
    ) -> None:
        captured["shard_paths"] = list(shard_paths)
        captured["output_root"] = output_root
        captured["max_rows_per_file"] = max_rows_per_file
        captured["metadata_payloads"] = metadata_payloads

    monkeypatch.setattr(resume_from_staging, "write_partitioned_dataset", _fake_write_partitioned_dataset)
    monkeypatch.setattr(
        "sys.argv",
        [
            "resume-from-staging",
            "--staging-dir",
            str(staging_dir),
            "--output-root",
            str(output_root),
            "--resume-base-files",
            "--resume-output-files",
        ],
    )

    exit_code = resume_from_staging.main()

    assert exit_code == 0
    assert captured["shard_paths"] == [staging_dir / "base_00000.parquet"]
    assert captured["metadata_payloads"] == {
        "_meta/feature_template.json": feature_template,
        "_meta/feature_transforms.json": feature_transforms,
        "_meta/uncatalogued_columns.json": uncatalogued,
    }


def test_export_load_feature_names_rebuilds_legacy_template(tmp_path: Path) -> None:
    meta_dir = tmp_path / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "feature_template.json").write_text(
        json.dumps(
            {
                "env": ["bio_1", "lithology"],
                "weather": ["temperature_2m_24h"],
                "misc": ["custom_measure"],
            }
        ),
        encoding="utf-8",
    )

    feature_names = export._load_feature_names(tmp_path)

    assert feature_names == {
        "bioclimate": ["bio_1"],
        "landclass": ["lithology"],
        "terrain": [],
        "temporal": ["temperature_2m_24h"],
        "other": ["custom_measure"],
    }


def test_score_species_coords_honors_cancel_check_between_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Cancelled(RuntimeError):
        pass

    state = {"cancelled": False}
    prepare_calls = 0
    score_calls = 0

    def _cancel_check() -> None:
        if state["cancelled"]:
            raise _Cancelled()

    def _fake_prepare_feature_batch_for_coords(
        coords: list[tuple[float, float]],
        *,
        resolution_hint: float,
        include_source: bool,
        feature_mode: str,
        raster_dataset_cache=None,
        dem_dataset_cache=None,
        cancel_check=None,
        sample_profile=None,
        cell_table_features=None,
        sampled_prefilter_keep_mask=None,
    ):
        nonlocal prepare_calls
        prepare_calls += 1
        return [0 for _ in coords], torch.zeros((len(coords), 2), dtype=torch.float32), None

    def _fake_score_species_feature_tensor(
        species_key: int,
        feature_tensor: torch.Tensor,
        *,
        score_batch_size: int,
        cancel_check=None,
    ) -> list[float]:
        nonlocal score_calls
        score_calls += 1
        state["cancelled"] = True
        return [0.5 for _ in range(int(feature_tensor.shape[0]))]

    monkeypatch.setattr(inference, "_resolve_sample_chunk_size", lambda score_batch_size: 2)
    monkeypatch.setattr(
        inference,
        "_prepare_feature_batch_for_coords",
        _fake_prepare_feature_batch_for_coords,
    )
    monkeypatch.setattr(
        inference,
        "_score_species_feature_tensor",
        _fake_score_species_feature_tensor,
    )

    with pytest.raises(_Cancelled):
        inference.score_species_coords(
            101,
            [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0)],
            resolution_hint=0.25,
            cancel_check=_cancel_check,
        )

    assert prepare_calls == 1
    assert score_calls == 1


def test_score_species_coords_prefilters_once_across_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefilter_calls = 0
    received_masks: list[list[bool] | None] = []

    def _fake_prepare_feature_batch_for_coords(
        coords: list[tuple[float, float]],
        *,
        resolution_hint: float,
        include_source: bool,
        feature_mode: str,
        raster_dataset_cache=None,
        dem_dataset_cache=None,
        cancel_check=None,
        sample_profile=None,
        cell_table_features=None,
        sampled_prefilter_keep_mask=None,
    ):
        received_masks.append(
            list(sampled_prefilter_keep_mask) if sampled_prefilter_keep_mask is not None else None,
        )
        return list(range(len(coords))), torch.zeros((len(coords), 1), dtype=torch.float32), None

    def _fake_sample_darwin_prefilter_keep_mask(coords, dataset_cache=None):
        nonlocal prefilter_calls
        prefilter_calls += 1
        return [True for _ in coords], 1

    monkeypatch.setattr(inference, "_resolve_sample_chunk_size", lambda score_batch_size: 2)
    monkeypatch.setattr(
        inference,
        "_resolve_heatmap_feature_mode",
        lambda feature_mode, resolution_hint, native_resolution: inference._HeatmapFeatureConfig("sampled", False),
    )
    monkeypatch.setattr(
        inference,
        "_prepare_feature_batch_for_coords",
        _fake_prepare_feature_batch_for_coords,
    )
    monkeypatch.setattr(
        inference,
        "_sample_darwin_prefilter_keep_mask",
        _fake_sample_darwin_prefilter_keep_mask,
    )
    monkeypatch.setattr(
        inference,
        "_score_species_feature_tensor",
        lambda species_key, feature_tensor, *, score_batch_size, cancel_check=None: [
            0.5 for _ in range(int(feature_tensor.shape[0]))
        ],
    )

    scores, _ = inference.score_species_coords(
        101,
        [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0)],
        resolution_hint=0.01,
        feature_mode="prefer_cell_table",
    )

    assert scores == [0.5, 0.5, 0.5, 0.5]
    assert prefilter_calls == 1
    assert received_masks == [[True, True], [True, True]]


def test_train_cli_heads_parse_combined_head_batch_size(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "train-cli",
            "heads",
            "--data-root",
            str(tmp_path / "data"),
            "--output-dir",
            str(tmp_path / "out"),
            "--encoder-checkpoint",
            str(tmp_path / "encoder_best.pt"),
            "--train-combined-head",
            "--combined-head-only",
            "--batch-size",
            "16384",
            "--combined-head-batch-size",
            "512",
        ],
    )

    args = train_cli.parse_args()

    assert args.stage == "heads"
    assert args.batch_size == 16384
    assert args.combined_head_batch_size == 512
    assert args.train_combined_head is True
    assert args.combined_head_only is True


def test_train_cli_heads_parse_fixed_prior(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "train-cli",
            "heads",
            "--data-root",
            str(tmp_path / "data"),
            "--output-dir",
            str(tmp_path / "out"),
            "--encoder-checkpoint",
            str(tmp_path / "encoder_best.pt"),
            "--fixed-prior",
            "0.02",
        ],
    )

    args = train_cli.parse_args()

    assert args.stage == "heads"
    assert args.fixed_prior == pytest.approx(0.02)


def test_train_cli_main_forwards_distinct_stage_c_batch_sizes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    forwarded: dict[str, object] = {}

    def _fake_train_species_heads(**kwargs: object) -> Path:
        forwarded.update(kwargs)
        return tmp_path / "species_heads.pt"

    def _fake_import_local_symbol(module_name: str, symbol_name: str) -> object:
        if (module_name, symbol_name) == ("train_heads", "train_species_heads"):
            return _fake_train_species_heads
        raise AssertionError(f"unexpected import request: {(module_name, symbol_name)}")

    monkeypatch.setattr(train_cli, "import_local_symbol", _fake_import_local_symbol)
    monkeypatch.setattr(
        "sys.argv",
        [
            "train-cli",
            "heads",
            "--data-root",
            str(tmp_path / "data"),
            "--output-dir",
            str(tmp_path / "out"),
            "--encoder-checkpoint",
            str(tmp_path / "encoder_best.pt"),
            "--train-combined-head",
            "--combined-head-only",
            "--batch-size",
            "8192",
            "--combined-head-batch-size",
            "256",
            "--fixed-prior",
            "0.02",
        ],
    )

    assert train_cli.main() == 0
    assert forwarded["batch_size"] == 8192
    assert forwarded["combined_head_batch_size"] == 256
    assert forwarded["fixed_prior"] == pytest.approx(0.02)
    assert forwarded["train_combined_head"] is True
    assert forwarded["combined_head_only"] is True


def test_train_cli_main_rejects_combined_head_only_with_all(tmp_path: Path) -> None:
    import sys

    argv = sys.argv
    sys.argv = [
        "train-cli",
        "all",
        "--data-root",
        str(tmp_path / "data"),
        "--output-dir",
        str(tmp_path / "out"),
        "--combined-head-only",
    ]
    try:
        with pytest.raises(SystemExit, match="only supported with the 'heads' stage"):
            train_cli.main()
    finally:
        sys.argv = argv


def test_train_species_heads_combined_head_only_requires_existing_checkpoint(tmp_path: Path) -> None:
    from scripts.machine_learning.train import train_heads

    data_root = tmp_path / "training_data"
    output_dir = tmp_path / "outputs"
    encoder_checkpoint = tmp_path / "encoder_best.pt"

    n_groups = len(training_data.FEATURE_COLUMNS)
    zero_mask = [0.0] * n_groups
    _write_split_part(
        data_root,
        split="train",
        part_name="train.parquet",
        cell_id="train_cell",
        feature_values=[0.0] * n_groups,
        mask_values=zero_mask,
        species_key=101,
        presence_label=1,
    )
    _write_split_part(
        data_root,
        split="val",
        part_name="val.parquet",
        cell_id="val_cell",
        feature_values=[0.0] * n_groups,
        mask_values=zero_mask,
        species_key=101,
        presence_label=1,
    )

    input_dim = n_groups * 2
    encoder = SharedEncoder(input_dim=input_dim, embed_dim=4, hidden_dim=8)
    torch.save(
        {
            "input_dim": input_dim,
            "embed_dim": 4,
            "hidden_dim": 8,
            "encoder_state_dict": encoder.state_dict(),
        },
        encoder_checkpoint,
    )

    with pytest.raises(FileNotFoundError):
        train_heads.train_species_heads(
            data_root=data_root,
            encoder_checkpoint=encoder_checkpoint,
            output_dir=output_dir,
            device="cpu",
            train_combined_head=True,
            combined_head_only=True,
        )


def test_train_species_heads_rejects_non_positive_fixed_prior(tmp_path: Path) -> None:
    from scripts.machine_learning.train import train_heads

    data_root = tmp_path / "training_data"
    output_dir = tmp_path / "outputs"
    encoder_checkpoint = tmp_path / "encoder_best.pt"

    n_groups = len(training_data.FEATURE_COLUMNS)
    zero_mask = [0.0] * n_groups
    _write_split_part(
        data_root,
        split="train",
        part_name="train.parquet",
        cell_id="train_cell",
        feature_values=[0.0] * n_groups,
        mask_values=zero_mask,
        species_key=101,
        presence_label=1,
    )
    _write_split_part(
        data_root,
        split="val",
        part_name="val.parquet",
        cell_id="val_cell",
        feature_values=[0.0] * n_groups,
        mask_values=zero_mask,
        species_key=101,
        presence_label=1,
    )

    input_dim = n_groups * 2
    encoder = SharedEncoder(input_dim=input_dim, embed_dim=4, hidden_dim=8)
    torch.save(
        {
            "input_dim": input_dim,
            "embed_dim": 4,
            "hidden_dim": 8,
            "encoder_state_dict": encoder.state_dict(),
        },
        encoder_checkpoint,
    )

    with pytest.raises(ValueError, match="fixed_prior must be > 0"):
        train_heads.train_species_heads(
            data_root=data_root,
            encoder_checkpoint=encoder_checkpoint,
            output_dir=output_dir,
            fixed_prior=0.0,
            device="cpu",
        )


def test_train_species_heads_combined_head_only_rejects_legacy_checkpoint_without_encoder_metadata(
    tmp_path: Path,
) -> None:
    from scripts.machine_learning.train import train_heads

    data_root = tmp_path / "training_data"
    output_dir = tmp_path / "outputs"
    encoder_checkpoint = tmp_path / "encoder_best.pt"

    n_groups = len(training_data.FEATURE_COLUMNS)
    zero_mask = [0.0] * n_groups
    _write_split_part(
        data_root,
        split="train",
        part_name="train.parquet",
        cell_id="train_cell",
        feature_values=[0.0] * n_groups,
        mask_values=zero_mask,
        species_key=101,
        presence_label=1,
    )
    _write_split_part(
        data_root,
        split="val",
        part_name="val.parquet",
        cell_id="val_cell",
        feature_values=[0.0] * n_groups,
        mask_values=zero_mask,
        species_key=101,
        presence_label=1,
    )

    input_dim = n_groups * 2
    encoder = SharedEncoder(input_dim=input_dim, embed_dim=4, hidden_dim=8)
    torch.save(
        {
            "input_dim": input_dim,
            "embed_dim": 4,
            "hidden_dim": 8,
            "encoder_state_dict": encoder.state_dict(),
        },
        encoder_checkpoint,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "embed_dim": 4,
            "head_states": {},
            "species_meta": {},
            "combined_head_state": None,
            "combined_species_keys": [],
            "combined_head_meta": None,
        },
        output_dir / "species_heads.pt",
    )

    with pytest.raises(ValueError, match="written with encoder checkpoint metadata"):
        train_heads.train_species_heads(
            data_root=data_root,
            encoder_checkpoint=encoder_checkpoint,
            output_dir=output_dir,
            device="cpu",
            train_combined_head=True,
            combined_head_only=True,
        )


def test_train_species_heads_combined_head_only_preserves_existing_species_heads(tmp_path: Path) -> None:
    from scripts.machine_learning.train import train_heads

    data_root = tmp_path / "training_data"
    output_dir = tmp_path / "outputs"
    encoder_checkpoint = tmp_path / "encoder_best.pt"

    n_groups = len(training_data.FEATURE_COLUMNS)
    zero_mask = [0.0] * n_groups

    def _group_values(first: float, second: float) -> list[float]:
        values = [0.0] * n_groups
        if n_groups > 0:
            values[0] = first
        if n_groups > 1:
            values[1] = second
        return values

    row_specs = [
        ("train", "train_sp101_pos_a.parquet", 101, 1, _group_values(1.0, 0.0)),
        ("train", "train_sp101_pos_b.parquet", 101, 1, _group_values(0.9, 0.0)),
        ("train", "train_sp101_unl.parquet", 101, 0, _group_values(0.2, 0.1)),
        ("train", "train_sp202_pos_a.parquet", 202, 1, _group_values(0.0, 1.0)),
        ("train", "train_sp202_pos_b.parquet", 202, 1, _group_values(0.0, 0.9)),
        ("train", "train_sp202_unl.parquet", 202, 0, _group_values(0.1, 0.2)),
        ("val", "val_sp101_pos.parquet", 101, 1, _group_values(1.0, 0.0)),
        ("val", "val_sp101_unl.parquet", 101, 0, _group_values(0.2, 0.1)),
        ("val", "val_sp202_pos.parquet", 202, 1, _group_values(0.0, 1.0)),
        ("val", "val_sp202_unl.parquet", 202, 0, _group_values(0.1, 0.2)),
    ]

    for split, part_name, species_key, presence_label, feature_values in row_specs:
        _write_split_part(
            data_root,
            split=split,
            part_name=part_name,
            cell_id=f"{split}_{species_key}_{presence_label}_{part_name}",
            feature_values=feature_values,
            mask_values=zero_mask,
            species_key=species_key,
            presence_label=presence_label,
        )

    input_dim = n_groups * 2
    encoder = SharedEncoder(input_dim=input_dim, embed_dim=4, hidden_dim=8)
    torch.save(
        {
            "input_dim": input_dim,
            "embed_dim": 4,
            "hidden_dim": 8,
            "encoder_state_dict": encoder.state_dict(),
        },
        encoder_checkpoint,
    )

    existing_head_101 = SpeciesHead(embed_dim=4)
    existing_head_202 = SpeciesHead(embed_dim=4)
    with torch.no_grad():
        existing_head_101.linear.bias.fill_(1.5)
        existing_head_202.linear.bias.fill_(-2.5)
    existing_species_meta = {
        101: {"name": "species-101", "val_loss": 0.3},
        202: {"name": "species-202", "val_loss": 0.4},
    }
    existing_checkpoint_path = output_dir / "species_heads.pt"
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "embed_dim": 4,
            "encoder_checkpoint": {
                "path": str(encoder_checkpoint.resolve()),
                "sha256": train_heads._sha256_file(encoder_checkpoint),
                "input_dim": input_dim,
                "embed_dim": 4,
                "hidden_dim": 8,
            },
            "head_states": {
                101: existing_head_101.state_dict(),
                202: existing_head_202.state_dict(),
            },
            "species_meta": existing_species_meta,
            "combined_head_state": None,
            "combined_species_keys": [],
            "combined_head_meta": None,
        },
        existing_checkpoint_path,
    )

    heads_path = train_heads.train_species_heads(
        data_root=data_root,
        encoder_checkpoint=encoder_checkpoint,
        output_dir=output_dir,
        min_positives=2,
        fixed_prior=0.02,
        head_epochs=1,
        head_lr=1e-2,
        head_weight_decay=1e-3,
        batch_size=4,
        device="cpu",
        train_combined_head=True,
        combined_head_only=True,
        combined_head_min_positives=2,
        combined_head_epochs=1,
        combined_head_lr=1e-2,
        combined_head_batch_size=2,
        combined_head_weight_decay=1e-4,
    )

    checkpoint = torch.load(heads_path, map_location="cpu", weights_only=True)

    assert heads_path == existing_checkpoint_path
    assert checkpoint["combined_head_state"] is not None
    assert checkpoint["combined_species_keys"] == [101, 202]
    assert checkpoint["combined_head_meta"]["n_species"] == 2
    assert checkpoint["head_states"].keys() == {101, 202}
    assert checkpoint["species_meta"] == existing_species_meta
    assert torch.equal(
        checkpoint["head_states"][101]["linear.bias"],
        existing_head_101.state_dict()["linear.bias"],
    )
    assert torch.equal(
        checkpoint["head_states"][202]["linear.bias"],
        existing_head_202.state_dict()["linear.bias"],
    )


def test_train_species_heads_combined_head_only_clears_stale_combined_head_when_no_species_are_eligible(
    tmp_path: Path,
) -> None:
    from scripts.machine_learning.train import train_heads

    data_root = tmp_path / "training_data"
    output_dir = tmp_path / "outputs"
    encoder_checkpoint = tmp_path / "encoder_best.pt"

    n_groups = len(training_data.FEATURE_COLUMNS)
    zero_mask = [0.0] * n_groups

    def _group_values(first: float, second: float) -> list[float]:
        values = [0.0] * n_groups
        if n_groups > 0:
            values[0] = first
        if n_groups > 1:
            values[1] = second
        return values

    row_specs = [
        ("train", "train_sp101_pos.parquet", 101, 1, _group_values(1.0, 0.0)),
        ("train", "train_sp101_unl.parquet", 101, 0, _group_values(0.2, 0.1)),
        ("train", "train_sp202_pos.parquet", 202, 1, _group_values(0.0, 1.0)),
        ("train", "train_sp202_unl.parquet", 202, 0, _group_values(0.1, 0.2)),
        ("val", "val_sp101_pos.parquet", 101, 1, _group_values(1.0, 0.0)),
        ("val", "val_sp101_unl.parquet", 101, 0, _group_values(0.2, 0.1)),
        ("val", "val_sp202_pos.parquet", 202, 1, _group_values(0.0, 1.0)),
        ("val", "val_sp202_unl.parquet", 202, 0, _group_values(0.1, 0.2)),
    ]

    for split, part_name, species_key, presence_label, feature_values in row_specs:
        _write_split_part(
            data_root,
            split=split,
            part_name=part_name,
            cell_id=f"{split}_{species_key}_{presence_label}_{part_name}",
            feature_values=feature_values,
            mask_values=zero_mask,
            species_key=species_key,
            presence_label=presence_label,
        )

    input_dim = n_groups * 2
    encoder = SharedEncoder(input_dim=input_dim, embed_dim=4, hidden_dim=8)
    torch.save(
        {
            "input_dim": input_dim,
            "embed_dim": 4,
            "hidden_dim": 8,
            "encoder_state_dict": encoder.state_dict(),
        },
        encoder_checkpoint,
    )

    existing_head_101 = SpeciesHead(embed_dim=4)
    existing_head_202 = SpeciesHead(embed_dim=4)
    stale_combined_head = CombinedSpeciesHead(embed_dim=4, species_count=2)
    output_dir.mkdir(parents=True, exist_ok=True)
    existing_checkpoint_path = output_dir / "species_heads.pt"
    torch.save(
        {
            "embed_dim": 4,
            "encoder_checkpoint": {
                "path": str(encoder_checkpoint.resolve()),
                "sha256": train_heads._sha256_file(encoder_checkpoint),
                "input_dim": input_dim,
                "embed_dim": 4,
                "hidden_dim": 8,
            },
            "head_states": {
                101: existing_head_101.state_dict(),
                202: existing_head_202.state_dict(),
            },
            "species_meta": {
                101: {"name": "species-101"},
                202: {"name": "species-202"},
            },
            "combined_head_state": stale_combined_head.state_dict(),
            "combined_species_keys": [101, 202],
            "combined_head_meta": {"n_species": 2, "min_positives": 1},
        },
        existing_checkpoint_path,
    )

    heads_path = train_heads.train_species_heads(
        data_root=data_root,
        encoder_checkpoint=encoder_checkpoint,
        output_dir=output_dir,
        min_positives=1,
        head_epochs=1,
        head_lr=1e-2,
        head_weight_decay=1e-3,
        batch_size=4,
        device="cpu",
        train_combined_head=True,
        combined_head_only=True,
        combined_head_min_positives=3,
        combined_head_epochs=1,
        combined_head_lr=1e-2,
        combined_head_batch_size=2,
        combined_head_weight_decay=1e-4,
    )

    checkpoint = torch.load(heads_path, map_location="cpu", weights_only=True)

    assert heads_path == existing_checkpoint_path
    assert checkpoint["head_states"].keys() == {101, 202}
    assert checkpoint["combined_head_state"] is None
    assert checkpoint["combined_species_keys"] == []
    assert checkpoint["combined_head_meta"] is None


def test_train_species_heads_end_to_end_writes_combined_head_payload(tmp_path: Path) -> None:
    from scripts.machine_learning.train import train_heads

    data_root = tmp_path / "training_data"
    output_dir = tmp_path / "outputs"
    encoder_checkpoint = tmp_path / "encoder_best.pt"

    n_groups = len(training_data.FEATURE_COLUMNS)
    zero_mask = [0.0] * n_groups

    def _group_values(first: float, second: float) -> list[float]:
        values = [0.0] * n_groups
        if n_groups > 0:
            values[0] = first
        if n_groups > 1:
            values[1] = second
        return values

    row_specs = [
        ("train", "train_sp101_pos_a.parquet", 101, 1, _group_values(1.0, 0.0)),
        ("train", "train_sp101_pos_b.parquet", 101, 1, _group_values(0.9, 0.0)),
        ("train", "train_sp101_unl.parquet", 101, 0, _group_values(0.2, 0.1)),
        ("train", "train_sp202_pos_a.parquet", 202, 1, _group_values(0.0, 1.0)),
        ("train", "train_sp202_pos_b.parquet", 202, 1, _group_values(0.0, 0.9)),
        ("train", "train_sp202_unl.parquet", 202, 0, _group_values(0.1, 0.2)),
        ("val", "val_sp101_pos.parquet", 101, 1, _group_values(1.0, 0.0)),
        ("val", "val_sp101_unl.parquet", 101, 0, _group_values(0.2, 0.1)),
        ("val", "val_sp202_pos.parquet", 202, 1, _group_values(0.0, 1.0)),
        ("val", "val_sp202_unl.parquet", 202, 0, _group_values(0.1, 0.2)),
    ]

    for split, part_name, species_key, presence_label, feature_values in row_specs:
        _write_split_part(
            data_root,
            split=split,
            part_name=part_name,
            cell_id=f"{split}_{species_key}_{presence_label}_{part_name}",
            feature_values=feature_values,
            mask_values=zero_mask,
            species_key=species_key,
            presence_label=presence_label,
        )

    input_dim = n_groups * 2
    encoder = SharedEncoder(input_dim=input_dim, embed_dim=4, hidden_dim=8)
    torch.save(
        {
            "input_dim": input_dim,
            "embed_dim": 4,
            "hidden_dim": 8,
            "encoder_state_dict": encoder.state_dict(),
        },
        encoder_checkpoint,
    )

    heads_path = train_heads.train_species_heads(
        data_root=data_root,
        encoder_checkpoint=encoder_checkpoint,
        output_dir=output_dir,
        min_positives=2,
        fixed_prior=0.02,
        head_epochs=1,
        head_lr=1e-2,
        head_weight_decay=1e-3,
        batch_size=4,
        device="cpu",
        train_combined_head=True,
        combined_head_min_positives=2,
        combined_head_epochs=1,
        combined_head_lr=1e-2,
        combined_head_batch_size=2,
        combined_head_weight_decay=1e-4,
    )

    checkpoint = torch.load(heads_path, map_location="cpu", weights_only=True)

    assert heads_path == output_dir / "species_heads.pt"
    assert checkpoint["combined_head_state"] is not None
    assert checkpoint["combined_species_keys"] == [101, 202]
    assert checkpoint["combined_head_meta"]["n_species"] == 2
    assert checkpoint["combined_head_meta"]["n_positive_rows_train"] == 4
    assert checkpoint["combined_head_meta"]["min_positives"] == 2
    assert checkpoint["combined_head_meta"]["val_loss"] is not None
    assert set(checkpoint["head_states"]) == {101, 202}
    assert set(checkpoint["species_meta"]) == {101, 202}
    assert checkpoint["species_meta"][101]["prior_pi"] == pytest.approx(0.02)
    assert checkpoint["species_meta"][101]["prior_mode"] == "fixed"


def test_iter_combined_positive_batches_skips_positive_species_outside_eligible_set() -> None:
    from scripts.machine_learning.train import train_heads

    embeddings = np.asarray(
        [
            [1.0, 0.0],
            [2.0, 0.0],
            [3.0, 0.0],
            [4.0, 0.0],
        ],
        dtype=np.float32,
    )
    species = np.asarray([101, 202, 999, 202], dtype=np.int64)
    labels = np.asarray([1, 1, 1, 0], dtype=np.int8)
    eligible_species = np.asarray([101, 202], dtype=np.int64)

    batches = list(
        train_heads._iter_combined_positive_batches(
            embeddings,
            species,
            labels,
            eligible_species=eligible_species,
            batch_size=8,
            shuffle=False,
        )
    )

    assert len(batches) == 1
    batch_embeddings, batch_targets = batches[0]
    assert batch_embeddings.shape == (2, 2)
    assert batch_targets.tolist() == [0, 1]


def test_build_feature_template_uses_catalog_groups_and_occurrence_other(tmp_path: Path) -> None:
    transform.reset_uncatalogued_summary()

    occurrence_path = tmp_path / "occurrence.parquet"
    static_context_path = tmp_path / "static_context.parquet"
    temporal_context_path = tmp_path / "temporal_context.parquet"

    _write_parquet(
        occurrence_path,
        {
            "lat": pa.array([10.0], type=pa.float64()),
            "lon": pa.array([20.0], type=pa.float64()),
            "species_key": pa.array([101], type=pa.int64()),
            "bio_1": pa.array([1.0], type=pa.float32()),
            "landcover": pa.array([2], type=pa.int32()),
            "landform": pa.array([3], type=pa.int32()),
            "temperature_2m_24h": pa.array([4.0], type=pa.float32()),
            "custom_measure": pa.array([5.0], type=pa.float32()),
        },
    )
    _write_parquet(
        static_context_path,
        {
            "cell_id": pa.array(["cell_1_2"]),
            "lithology": pa.array([7], type=pa.int32()),
            "ignored_context": pa.array([9.0], type=pa.float32()),
        },
    )
    _write_parquet(
        temporal_context_path,
        {
            "cell_id": pa.array(["cell_1_2"]),
            "year_month": pa.array(["2024-01"]),
            "precipitation_24h": pa.array([8.0], type=pa.float32()),
        },
    )

    template = transform.build_feature_template(
        [occurrence_path],
        schema_log_interval_files=0,
        log_slow_read_seconds=999.0,
        template_scan_max_files=0,
        static_context_template="{src_dir}/static_context.parquet",
        static_context_path=None,
        temporal_context_template="{src_dir}/temporal_context.parquet",
        temporal_context_path=None,
    )

    assert template.bioclimate == ["bio_1"]
    assert template.landclass == ["landcover", "lithology"]
    assert template.terrain == ["landform"]
    assert template.temporal == ["precipitation_24h", "temperature_2m_24h"]
    assert template.other == ["custom_measure"]


def test_load_occurrence_frame_projects_case_insensitive_columns(tmp_path: Path) -> None:
    source_path = tmp_path / "occurrence.parquet"
    _write_parquet(
        source_path,
        {
            "Latitude": pa.array([10.0], type=pa.float64()),
            "Longitude": pa.array([20.0], type=pa.float64()),
            "Species_Key": pa.array([101], type=pa.int64()),
            "EventDate": pa.array(["2024-01-15T00:00:00Z"], type=pa.string()),
            "BIO_1": pa.array([1.0], type=pa.float32()),
            "LANDCOVER": pa.array([2], type=pa.int32()),
        },
    )

    frame = transform.load_occurrence_frame(
        source_path,
        feature_template=transform.FeatureGroups(
            bioclimate=["bio_1"],
            landclass=["landcover"],
            terrain=[],
            temporal=[],
            other=[],
        ),
    )

    assert {"Latitude", "Longitude", "Species_Key", "EventDate", "BIO_1", "LANDCOVER"}.issubset(frame.columns)
    assert transform.choose_column(frame, ("lat", "latitude")) == "Latitude"
    assert transform.choose_column(frame, ("lon", "longitude")) == "Longitude"
    assert transform.choose_column(frame, ("species_key",)) == "Species_Key"
    assert frame["BIO_1"].iloc[0] == pytest.approx(1.0)


def test_load_occurrence_frame_caches_explicit_schema_reads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_path = tmp_path / "occurrence.parquet"
    _write_parquet(
        source_path,
        {
            "lat": pa.array([10.0], type=pa.float64()),
            "lon": pa.array([20.0], type=pa.float64()),
            "species_key": pa.array([101], type=pa.int64()),
            "eventDate": pa.array(["2024-01-15T00:00:00Z"], type=pa.string()),
            "bio_1": pa.array([1.0], type=pa.float32()),
        },
    )

    transform._occurrence_schema_columns_cached.cache_clear()
    original_read_schema = transform.pq.read_schema
    call_counter = {"count": 0}

    def _counting_read_schema(*args: object, **kwargs: object):
        call_counter["count"] += 1
        return original_read_schema(*args, **kwargs)

    monkeypatch.setattr(transform.pq, "read_schema", _counting_read_schema)

    template = transform.FeatureGroups(
        bioclimate=["bio_1"],
        landclass=[],
        terrain=[],
        temporal=[],
        other=[],
    )
    transform.load_occurrence_frame(source_path, feature_template=template)
    transform.load_occurrence_frame(source_path, feature_template=template)

    assert call_counter["count"] == 1


def test_build_feature_transforms_from_frames_fits_numeric_and_categorical() -> None:
    feature_template = transform.FeatureGroups(
        bioclimate=["bio_1"],
        landclass=["landcover"],
        terrain=["aspect_deg"],
        temporal=[],
        other=["custom_measure"],
    )
    train_frame = pd.DataFrame(
        {
            "bio_1": [10.0, 14.0],
            "landcover": [52.0, 71.0],
            "aspect_deg": [0.0, 90.0],
            "custom_measure": [1.0, 3.0],
            "split": ["train", "train"],
        }
    )

    fitted = transform.build_feature_transforms_from_frames([train_frame], feature_template=feature_template)

    assert fitted.raw_feature_template == {
        "bioclimate": ["bio_1"],
        "landclass": ["landcover"],
        "terrain": ["aspect_deg"],
        "temporal": [],
        "other": ["custom_measure"],
    }
    assert fitted.transformed_feature_template == {
        "bioclimate": ["bio_1"],
        "landclass": ["landcover__cat_52", "landcover__cat_71", "landcover__cat_unknown"],
        "terrain": ["aspect_deg__sin", "aspect_deg__cos"],
        "temporal": [],
        "other": ["custom_measure"],
    }
    assert fitted.feature_specs["bio_1"]["value_type"] == "numeric"
    assert fitted.feature_specs["bio_1"]["mean"] == pytest.approx(12.0)
    assert fitted.feature_specs["landcover"]["value_type"] == "categorical"
    assert fitted.feature_specs["landcover"]["categories"] == [52, 71]
    assert fitted.feature_specs["aspect_deg"]["value_type"] == "circular"


def test_transform_frame_merges_context_and_builds_group_vectors() -> None:
    feature_template = transform.FeatureGroups(
        bioclimate=["bio_1"],
        landclass=["landcover", "lithology"],
        terrain=["elevation", "landform"],
        temporal=["temperature_2m_24h"],
        other=["custom_measure"],
    )
    frame = pd.DataFrame(
        {
            "lat": [10.1],
            "lon": [20.1],
            "species_key": [101],
            "eventDate": ["2024-01-15T00:00:00Z"],
            "observation_id": ["obs-1"],
            "source": ["gbif"],
            "bio_1": [1.5],
            "landcover": [2.0],
            "custom_measure": [9.0],
        }
    )
    static_context = pd.DataFrame(
        {
            "cell_id": ["cell_40_80"],
            "lithology": [7.0],
            "landform": [3.0],
        }
    )
    temporal_context = pd.DataFrame(
        {
            "cell_id": ["cell_40_80"],
            "year_month": ["2024-01"],
            "temperature_2m_24h": [4.5],
        }
    )

    table, warnings, static_rows, temporal_rows = transform.transform_frame(
        frame,
        feature_version="test-v1",
        cell_size_deg=0.25,
        region_size_deg=10.0,
        fallback_species_key=None,
        feature_template=feature_template,
        fallback_time_policy="keep",
        warn_min_cells_per_species=2,
        static_context=static_context,
        temporal_context=temporal_context,
    )

    row = table.slice(0, 1)
    assert row.column("cell_id")[0].as_py() == "cell_40_80"
    assert row.column("year_month")[0].as_py() == "2024-01"
    assert row.column("source")[0].as_py() == "gbif"
    assert row.column("bioclimate_features")[0].as_py() == [1.5]
    assert row.column("bioclimate_missing_mask")[0].as_py() == [0]
    assert row.column("landclass_features")[0].as_py() == [2.0, 7.0]
    assert row.column("landclass_missing_mask")[0].as_py() == [0, 0]
    assert row.column("terrain_features")[0].as_py() == [0.0, 3.0]
    assert row.column("terrain_missing_mask")[0].as_py() == [1, 0]
    assert row.column("temporal_features")[0].as_py() == [4.5]
    assert row.column("other_features")[0].as_py() == [9.0]
    assert static_rows == 1
    assert temporal_rows == 1
    assert warnings == ["Low-cell species warning | species_key=101 | unique_cells=1"]


def test_load_context_features_requires_join_key(tmp_path: Path) -> None:
    context_path = tmp_path / "bad_context.parquet"
    _write_parquet(
        context_path,
        {
            "wrong_key": pa.array(["cell_1_2"]),
            "bio_1": pa.array([1.0], type=pa.float32()),
        },
    )

    with pytest.raises(ValueError, match="Missing join key 'cell_id'"):
        transform.load_context_features(context_path, join_keys=("cell_id",))


def test_transform_frame_raises_when_missing_times_are_dropped() -> None:
    feature_template = transform.FeatureGroups(
        bioclimate=["bio_1"],
        landclass=[],
        terrain=[],
        temporal=[],
        other=[],
    )
    frame = pd.DataFrame(
        {
            "lat": [10.1],
            "lon": [20.1],
            "species_key": [101],
            "eventDate": ["not-a-date"],
            "bio_1": [1.5],
        }
    )

    with pytest.raises(ValueError, match="No valid rows remain after fallback-time filtering"):
        transform.transform_frame(
            frame,
            feature_version="test-v1",
            cell_size_deg=0.25,
            region_size_deg=10.0,
            fallback_species_key=None,
            feature_template=feature_template,
            fallback_time_policy="drop",
            warn_min_cells_per_species=0,
            static_context=None,
            temporal_context=None,
        )


def test_fit_feature_transforms_skips_files_with_no_rows_after_drop_missing_time(tmp_path: Path) -> None:
    source_path = tmp_path / "species_101" / "occurrence.parquet"
    _write_parquet(
        source_path,
        {
            "lat": pa.array([10.1], type=pa.float64()),
            "lon": pa.array([20.1], type=pa.float64()),
            "species_key": pa.array([101], type=pa.int64()),
            "eventDate": pa.array(["not-a-date"], type=pa.string()),
            "bio_1": pa.array([1.5], type=pa.float32()),
        },
    )

    fitted = transform.fit_feature_transforms(
        [source_path],
        cell_size_deg=0.25,
        region_size_deg=10.0,
        feature_template=transform.FeatureGroups(
            bioclimate=["bio_1"],
            landclass=[],
            terrain=[],
            temporal=[],
            other=[],
        ),
        fallback_time_policy="drop",
        warn_min_cells_per_species=0,
        static_context_template="",
        static_context_path=None,
        static_context_required=False,
        temporal_context_template="",
        temporal_context_path=None,
        temporal_context_required=False,
    )

    assert fitted.transformed_feature_template == {
        "bioclimate": ["bio_1"],
        "landclass": [],
        "terrain": [],
        "temporal": [],
        "other": [],
    }
    assert fitted.feature_specs["bio_1"]["value_type"] == "numeric"
    assert fitted.feature_specs["bio_1"]["mean"] == 0.0
    assert fitted.feature_specs["bio_1"]["std"] == 1.0


def test_transform_file_skips_files_with_no_rows_after_drop_missing_time(tmp_path: Path) -> None:
    source_path = tmp_path / "species_101" / "occurrence.parquet"
    _write_parquet(
        source_path,
        {
            "lat": pa.array([10.1], type=pa.float64()),
            "lon": pa.array([20.1], type=pa.float64()),
            "species_key": pa.array([101], type=pa.int64()),
            "eventDate": pa.array(["not-a-date"], type=pa.string()),
            "bio_1": pa.array([1.5], type=pa.float32()),
        },
    )

    result = transform.transform_file(
        source_path,
        tmp_path / "staging",
        feature_version="test-v1",
        cell_size_deg=0.25,
        region_size_deg=10.0,
        feature_template=transform.FeatureGroups(
            bioclimate=["bio_1"],
            landclass=[],
            terrain=[],
            temporal=[],
            other=[],
        ),
        feature_transforms=None,
        fallback_time_policy="drop",
        warn_min_cells_per_species=0,
        static_context_template="",
        static_context_path=None,
        static_context_required=False,
        temporal_context_template="",
        temporal_context_path=None,
        temporal_context_required=False,
    )

    assert result.out_path is None
    assert result.rows == 0
    assert result.skipped_reason == "No valid rows remain after fallback-time filtering."


def test_build_cell_table_averages_rows_and_zeroes_tied_missing_features(tmp_path: Path) -> None:
    _write_split_part(
        tmp_path,
        split="train",
        part_name="part-0.parquet",
        cell_id="cell_0_0",
        feature_values=[1.0, 2.0, 3.0, 4.0, 5.0],
        mask_values=[0.0, 0.0, 0.0, 0.0, 0.0],
    )
    _write_split_part(
        tmp_path,
        split="val",
        part_name="part-1.parquet",
        cell_id="cell_0_0",
        feature_values=[11.0, 12.0, 13.0, 14.0, 15.0],
        mask_values=[0.0, 1.0, 0.0, 0.0, 0.0],
    )

    cell_table = export.build_cell_table(tmp_path)

    payload = cell_table["cell_0_0"]
    # Missing values are excluded from the per-feature mean, so the second
    # feature keeps the observed value from the train row instead of being
    # biased by the missing val row.
    assert payload.tolist() == [6.0, 2.0, 8.0, 9.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_load_bundle_exposes_species_metadata_and_cell_table(tmp_path: Path) -> None:
    bundle_path = _write_inference_bundle(
        tmp_path / "bundle.pt",
        input_dim=4,
        cell_table={"cell_0_0": torch.tensor([1.0, 2.0, 0.0, 0.0], dtype=torch.float32)},
        feature_names={
            "bioclimate": ["bio_1"],
            "landclass": ["landcover"],
            "terrain": [],
            "temporal": [],
            "other": [],
        },
    )

    inference.load_bundle(bundle_path)

    assert inference.is_loaded() is True
    assert inference.known_species() == [101]
    assert inference.has_species(101) is True
    assert inference.cell_count() == 1
    assert inference.native_resolution() == 0.25


def test_load_bundle_rejects_incompatible_cell_payload(tmp_path: Path) -> None:
    bundle_path = _write_inference_bundle(
        tmp_path / "invalid_bundle.pt",
        input_dim=4,
        cell_table={"cell_0_0": torch.tensor([1.0], dtype=torch.float32)},
        feature_names={
            "bioclimate": ["bio_1"],
            "landclass": ["landcover"],
            "terrain": [],
            "temporal": [],
            "other": [],
        },
    )

    with pytest.raises(ValueError, match=r"cell\(s\) in bundle have incompatible feature width"):
        inference.load_bundle(bundle_path)


def test_run_preprocess_writes_partitioned_dataset_and_metadata(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    staging_dir = tmp_path / "staging"
    src_dir = input_root / "species_101"

    _write_parquet(
        src_dir / "observations.parquet",
        {
            "lat": pa.array([10.1], type=pa.float64()),
            "lon": pa.array([20.1], type=pa.float64()),
            "species_key": pa.array([101], type=pa.int64()),
            "eventDate": pa.array(["2024-01-15T00:00:00Z"], type=pa.string()),
            "observation_id": pa.array(["obs-1"], type=pa.string()),
            "source": pa.array(["gbif"], type=pa.string()),
            "bio_1": pa.array([1.5], type=pa.float32()),
            "landcover": pa.array([2], type=pa.int32()),
            "custom_measure": pa.array([9.0], type=pa.float32()),
        },
    )
    _write_parquet(
        src_dir / "static_context.parquet",
        {
            "cell_id": pa.array(["cell_40_80"]),
            "lithology": pa.array([7], type=pa.int32()),
            "landform": pa.array([3], type=pa.int32()),
        },
    )
    _write_parquet(
        src_dir / "temporal_context.parquet",
        {
            "cell_id": pa.array(["cell_40_80"]),
            "year_month": pa.array(["2024-01"]),
            "temperature_2m_24h": pa.array([4.5], type=pa.float32()),
        },
    )

    args = SimpleNamespace(
        input_root=input_root,
        output_root=output_root,
        staging_dir=staging_dir,
        overwrite_output=True,
        glob="**/observations.parquet",
        max_files=0,
        drop_missing_time=False,
        threads=1,
        background_ratio=0.0,
        background_split_chunk_rows=10,
        warn_min_cells_per_species=2,
        static_context_template="{src_dir}/static_context.parquet",
        static_context_path=None,
        static_context_required=False,
        temporal_context_template="{src_dir}/temporal_context.parquet",
        temporal_context_path=None,
        temporal_context_required=False,
        template_scan_max_files=0,
        feature_version="test-v1",
        max_rows_per_file=10,
        keep_staging=False,
    )

    exit_code = pipeline.run_preprocess(args)

    assert exit_code == 0
    feature_template = json.loads((output_root / "_meta" / "feature_template.json").read_text(encoding="utf-8"))
    feature_transforms = json.loads((output_root / "_meta" / "feature_transforms.json").read_text(encoding="utf-8"))
    assert feature_template == {
        "bioclimate": ["bio_1"],
        "landclass": ["landcover", "lithology"],
        "terrain": ["landform"],
        "temporal": ["temperature_2m_24h"],
        "other": ["custom_measure"],
    }
    assert feature_transforms["raw_feature_template"] == feature_template
    assert feature_transforms["transformed_feature_template"] == {
        "bioclimate": ["bio_1"],
        "landclass": [
            "landcover__cat_2",
            "landcover__cat_unknown",
            "lithology__cat_7",
            "lithology__cat_unknown",
        ],
        "terrain": ["landform__cat_3", "landform__cat_unknown"],
        "temporal": ["temperature_2m_24h"],
        "other": ["custom_measure"],
    }

    uncatalogued = json.loads((output_root / "_meta" / "uncatalogued_columns.json").read_text(encoding="utf-8"))
    assert uncatalogued["kept_occurrence"] == [
        {
            "column": "custom_measure",
            "example_path": str(src_dir / "observations.parquet"),
        }
    ]
    assert uncatalogued["skipped_context"] == []

    dataset = ds.dataset(str(output_root), format="parquet", partitioning="hive")
    table = dataset.to_table()
    assert table.num_rows == 1
    assert table.column("species_key")[0].as_py() == 101
    assert table.column("cell_id")[0].as_py() == "cell_40_80"
    assert table.column("bioclimate_features")[0].as_py() == [0.0]
    assert table.column("bioclimate_missing_mask")[0].as_py() == [0]
    assert table.column("landclass_features")[0].as_py() == [1.0, 0.0, 1.0, 0.0]
    assert table.column("landclass_missing_mask")[0].as_py() == [0, 0, 0, 0]
    assert table.column("terrain_features")[0].as_py() == [1.0, 0.0]
    assert table.column("terrain_missing_mask")[0].as_py() == [0, 0]
    assert table.column("temporal_features")[0].as_py() == [0.0]
    assert table.column("other_features")[0].as_py() == [0.0]
    assert not staging_dir.exists()


def test_run_preprocess_uses_all_discovered_files_for_template_scan_but_caps_processing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    staging_dir = tmp_path / "staging"
    source_a = input_root / "species_a" / "observations.parquet"
    source_b = input_root / "species_b" / "observations.parquet"

    _write_parquet(
        source_a,
        {
            "lat": pa.array([10.1], type=pa.float64()),
            "lon": pa.array([20.1], type=pa.float64()),
            "species_key": pa.array([101], type=pa.int64()),
            "eventDate": pa.array(["2024-01-15T00:00:00Z"], type=pa.string()),
            "bio_1": pa.array([1.5], type=pa.float32()),
        },
    )
    _write_parquet(
        source_b,
        {
            "lat": pa.array([11.1], type=pa.float64()),
            "lon": pa.array([21.1], type=pa.float64()),
            "species_key": pa.array([202], type=pa.int64()),
            "eventDate": pa.array(["2024-02-15T00:00:00Z"], type=pa.string()),
            "custom_measure": pa.array([9.0], type=pa.float32()),
        },
    )

    observed: dict[str, object] = {}
    feature_template = transform.FeatureGroups(
        bioclimate=["bio_1"],
        landclass=[],
        terrain=[],
        temporal=[],
        other=["custom_measure"],
    )
    fitted_transforms = transform.FittedFeatureTransforms(
        raw_feature_template={
            "bioclimate": ["bio_1"],
            "landclass": [],
            "terrain": [],
            "temporal": [],
            "other": ["custom_measure"],
        },
        transformed_feature_template={
            "bioclimate": ["bio_1"],
            "landclass": [],
            "terrain": [],
            "temporal": [],
            "other": ["custom_measure"],
        },
        feature_specs={
            "bio_1": {
                "group": "bioclimate",
                "value_type": "numeric",
                "mean": 0.0,
                "std": 1.0,
                "output_features": ["bio_1"],
            },
            "custom_measure": {
                "group": "other",
                "value_type": "numeric",
                "mean": 0.0,
                "std": 1.0,
                "output_features": ["custom_measure"],
            },
        },
    )

    def _fake_build_feature_template(files: list[Path], **_: object) -> transform.FeatureGroups:
        observed["template_files"] = list(files)
        return feature_template

    def _fake_fit_feature_transforms(files: list[Path], **_: object) -> transform.FittedFeatureTransforms:
        observed["fit_files"] = list(files)
        return fitted_transforms

    def _fake_transform_file(src_path: Path, _staging_dir: Path, **_: object) -> transform.TransformResult:
        processed = observed.setdefault("processed_files", [])
        assert isinstance(processed, list)
        processed.append(src_path)
        shard_path = _staging_dir / f"{src_path.parent.name}.parquet"
        _staging_dir.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.table({"split": pa.array(["train"], type=pa.string())}), shard_path)
        return transform.TransformResult(
            out_path=shard_path,
            rows=1,
            duration_seconds=0.0,
            read_seconds=0.0,
            low_cell_warnings=[],
            static_context_rows=0,
            temporal_context_rows=0,
            skipped_reason=None,
        )

    def _fake_write_partitioned_dataset(
        shard_paths: list[Path],
        output_root: Path,
        max_rows_per_file: int,
        metadata_payloads: dict[str, object] | None = None,
    ) -> None:
        observed["written_shards"] = list(shard_paths)
        output_root.mkdir(parents=True, exist_ok=True)
        if metadata_payloads:
            for relative_path, payload in metadata_payloads.items():
                target_path = output_root / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(pipeline, "build_feature_template", _fake_build_feature_template)
    monkeypatch.setattr(pipeline, "fit_feature_transforms", _fake_fit_feature_transforms)
    monkeypatch.setattr(pipeline, "transform_file", _fake_transform_file)
    monkeypatch.setattr(pipeline, "write_partitioned_dataset", _fake_write_partitioned_dataset)

    args = SimpleNamespace(
        input_root=input_root,
        output_root=output_root,
        staging_dir=staging_dir,
        overwrite_output=True,
        glob="**/observations.parquet",
        max_files=1,
        drop_missing_time=False,
        threads=1,
        background_ratio=0.0,
        background_split_chunk_rows=10,
        warn_min_cells_per_species=0,
        static_context_template="",
        static_context_path=None,
        static_context_required=False,
        temporal_context_template="",
        temporal_context_path=None,
        temporal_context_required=False,
        template_scan_max_files=0,
        feature_version="test-v1",
        max_rows_per_file=10,
        keep_staging=False,
    )

    exit_code = pipeline.run_preprocess(args)

    assert exit_code == 0
    assert observed["template_files"] == [source_a, source_b]
    assert observed["fit_files"] == [source_a]
    assert observed["processed_files"] == [source_a]
    assert len(observed["written_shards"]) == 1


def test_export_bundle_roundtrip_loads_and_scores(tmp_path: Path) -> None:
    data_root = tmp_path / "dataset"
    output_bundle = tmp_path / "bundle.pt"
    encoder_path = tmp_path / "encoder.pt"
    heads_path = tmp_path / "heads.pt"

    feature_names = {
        "bioclimate": ["bio_1"],
        "landclass": ["landcover"],
        "terrain": ["landform"],
        "temporal": ["temperature_2m_24h"],
        "other": ["custom_measure"],
    }
    transformed_feature_names = {
        "bioclimate": ["bio_1_scaled"],
        "landclass": ["landcover_scaled"],
        "terrain": ["landform_scaled"],
        "temporal": ["temperature_2m_24h_scaled"],
        "other": ["custom_measure_scaled"],
    }
    feature_transforms = {
        "version": "v1",
        "raw_feature_template": feature_names,
        "transformed_feature_template": transformed_feature_names,
        "feature_specs": {
            "bio_1": {
                "group": "bioclimate",
                "value_type": "numeric",
                "mean": 0.0,
                "std": 1.0,
                "output_features": ["bio_1_scaled"],
            },
            "landcover": {
                "group": "landclass",
                "value_type": "numeric",
                "mean": 0.0,
                "std": 1.0,
                "output_features": ["landcover_scaled"],
            },
            "landform": {
                "group": "terrain",
                "value_type": "numeric",
                "mean": 0.0,
                "std": 1.0,
                "output_features": ["landform_scaled"],
            },
            "temperature_2m_24h": {
                "group": "temporal",
                "value_type": "numeric",
                "mean": 0.0,
                "std": 1.0,
                "output_features": ["temperature_2m_24h_scaled"],
            },
            "custom_measure": {
                "group": "other",
                "value_type": "numeric",
                "mean": 0.0,
                "std": 1.0,
                "output_features": ["custom_measure_scaled"],
            },
        },
    }
    (data_root / "_meta").mkdir(parents=True, exist_ok=True)
    (data_root / "_meta" / "feature_template.json").write_text(json.dumps(feature_names), encoding="utf-8")
    (data_root / "_meta" / "feature_transforms.json").write_text(json.dumps(feature_transforms), encoding="utf-8")

    _write_split_part(
        data_root,
        split="train",
        part_name="part-0.parquet",
        cell_id="cell_0_0",
        feature_values=[1.0, 2.0, 3.0, 4.0, 5.0],
        mask_values=[0.0, 0.0, 0.0, 0.0, 0.0],
    )
    _write_split_part(
        data_root,
        split="val",
        part_name="part-1.parquet",
        cell_id="cell_0_0",
        feature_values=[11.0, 12.0, 13.0, 14.0, 15.0],
        mask_values=[0.0, 1.0, 0.0, 0.0, 0.0],
    )
    _write_split_part(
        data_root,
        split="test",
        part_name="part-2.parquet",
        cell_id="cell_1_1",
        feature_values=[21.0, 22.0, 23.0, 24.0, 25.0],
        mask_values=[0.0, 0.0, 0.0, 0.0, 0.0],
    )

    encoder = SharedEncoder(input_dim=10, embed_dim=4, hidden_dim=8)
    head = SpeciesHead(embed_dim=4)
    combined_head = CombinedSpeciesHead(embed_dim=4, species_count=1)
    torch.save(
        {
            "input_dim": 10,
            "embed_dim": 4,
            "hidden_dim": 8,
            "encoder_state_dict": encoder.state_dict(),
        },
        encoder_path,
    )
    torch.save(
        {
            "head_states": {101: head.state_dict()},
            "species_meta": {101: {"name": "Test species"}},
            "combined_head_state": combined_head.state_dict(),
            "combined_species_keys": [101],
            "combined_head_meta": {"n_species": 1, "val_loss": 0.0},
        },
        heads_path,
    )

    bundle_path = export.export_bundle(data_root, encoder_path, heads_path, output_bundle)
    bundle_payload = torch.load(bundle_path, map_location="cpu", weights_only=False)
    inference.load_bundle(bundle_path)

    assert bundle_path.exists()
    assert bundle_payload["bundle_version"] == 2
    assert bundle_payload["model"]["raw_feature_names"] == feature_names
    assert "feature_names" not in bundle_payload["model"]
    assert bundle_payload["model"]["feature_transforms"]["raw_feature_template"] == feature_names
    assert bundle_payload["model"]["feature_transforms"]["transformed_feature_template"] == transformed_feature_names
    exported_cell_payload = bundle_payload["serving"]["cell_table"]["cell_0_0"]
    assert isinstance(exported_cell_payload, torch.Tensor)
    assert torch.equal(
        exported_cell_payload,
        torch.tensor([6.0, 2.0, 8.0, 9.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=torch.float32),
    )
    assert inference.is_loaded() is True
    assert inference._feature_names == transformed_feature_names
    assert inference.has_species(101) is True
    assert inference.has_combined_head() is True
    assert inference.combined_species_keys() == [101]
    assert inference.cell_count() == 2
    assert inference.species_meta()[101]["name"] == "Test species"


def test_export_bundle_accepts_output_directory(tmp_path: Path) -> None:
    data_root = tmp_path / "dataset"
    output_dir = tmp_path / "bundle_dir"
    encoder_path = tmp_path / "encoder.pt"
    heads_path = tmp_path / "heads.pt"

    feature_names = {
        "bioclimate": ["bio_1"],
        "landclass": ["landcover"],
        "terrain": ["landform"],
        "temporal": ["temperature_2m_24h"],
        "other": ["custom_measure"],
    }
    (data_root / "_meta").mkdir(parents=True, exist_ok=True)
    (data_root / "_meta" / "feature_template.json").write_text(json.dumps(feature_names), encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_split_part(
        data_root,
        split="train",
        part_name="part-0.parquet",
        cell_id="cell_0_0",
        feature_values=[1.0, 2.0, 3.0, 4.0, 5.0],
        mask_values=[0.0, 0.0, 0.0, 0.0, 0.0],
    )

    encoder = SharedEncoder(input_dim=10, embed_dim=4, hidden_dim=8)
    head = SpeciesHead(embed_dim=4)
    torch.save(
        {
            "input_dim": 10,
            "embed_dim": 4,
            "hidden_dim": 8,
            "encoder_state_dict": encoder.state_dict(),
        },
        encoder_path,
    )
    torch.save(
        {
            "head_states": {101: head.state_dict()},
            "species_meta": {101: {"name": "Test species"}},
        },
        heads_path,
    )

    bundle_path = export.export_bundle(data_root, encoder_path, heads_path, output_dir)

    assert bundle_path == output_dir / "inference_bundle.pt"
    assert bundle_path.exists()


def test_rank_species_coords_uses_combined_head(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.pt"
    feature_names = {
        "bioclimate": ["bio_1"],
        "landclass": [],
        "terrain": [],
        "temporal": [],
        "other": [],
    }
    combined_head = CombinedSpeciesHead(embed_dim=4, species_count=2)
    with torch.no_grad():
        combined_head.linear.weight.zero_()
        combined_head.linear.bias.copy_(torch.tensor([2.0, -1.0], dtype=torch.float32))

    _write_inference_bundle(
        bundle_path,
        input_dim=2,
        cell_table={"cell_0_0": torch.tensor([1.0, 0.0], dtype=torch.float32)},
        feature_names=feature_names,
        species_meta={101: {"name": "Alpha"}, 202: {"name": "Beta"}},
        combined_head_state=combined_head.state_dict(),
        combined_species_keys=[101, 202],
    )

    inference.load_bundle(bundle_path)
    ranked, sources = inference.rank_all_species_coords(
        [(0.125, 0.125)],
        resolution_hint=0.25,
        top_k=2,
        feature_mode="cell_table_only",
        include_source=True,
        score_batch_size=1,
    )

    assert inference.has_combined_head() is True
    assert ranked[0] is not None
    assert [entry["species_key"] for entry in ranked[0]] == [101, 202]
    assert ranked[0][0]["name"] == "Alpha"
    assert ranked[0][0]["has_species_head"] is True
    assert ranked[0][0]["score"] > ranked[0][1]["score"]
    assert sources == ["cell_table"]


def test_rank_species_coords_filters_to_species_with_heads(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.pt"
    feature_names = {
        "bioclimate": ["bio_1"],
        "landclass": [],
        "terrain": [],
        "temporal": [],
        "other": [],
    }
    combined_head = CombinedSpeciesHead(embed_dim=4, species_count=2)
    with torch.no_grad():
        combined_head.linear.weight.zero_()
        combined_head.linear.bias.copy_(torch.tensor([1.0, 3.0], dtype=torch.float32))

    _write_inference_bundle(
        bundle_path,
        input_dim=2,
        cell_table={"cell_0_0": torch.tensor([1.0, 0.0], dtype=torch.float32)},
        feature_names=feature_names,
        species_meta={101: {"name": "Alpha"}, 202: {"name": "Beta"}},
        combined_head_state=combined_head.state_dict(),
        combined_species_keys=[101, 202],
    )

    inference.load_bundle(bundle_path)
    assert inference.combined_species_with_heads() == [101]

    ranked_backed, _ = inference.rank_species_coords(
        [(0.125, 0.125)],
        resolution_hint=0.25,
        top_k=2,
        feature_mode="cell_table_only",
        score_batch_size=1,
    )
    ranked_all, _ = inference.rank_all_species_coords(
        [(0.125, 0.125)],
        resolution_hint=0.25,
        top_k=2,
        feature_mode="cell_table_only",
        score_batch_size=1,
    )

    assert [entry["species_key"] for entry in ranked_backed[0]] == [101]
    assert [entry["species_key"] for entry in ranked_all[0]] == [202, 101]
    assert ranked_all[0][0]["has_species_head"] is False
    assert ranked_all[0][1]["has_species_head"] is True


def test_rank_species_weather_delta_coords_uses_current_temporal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_path = tmp_path / "bundle.pt"
    feature_names = {
        "bioclimate": ["bio_1"],
        "landclass": [],
        "terrain": [],
        "temporal": ["temperature_2m_avg_24h"],
        "other": [],
    }

    combined_head = CombinedSpeciesHead(embed_dim=4, species_count=2)

    _write_inference_bundle(
        bundle_path,
        input_dim=4,
        cell_table={"cell_0_0": torch.tensor([0.5, 0.0, 0.0, 1.0], dtype=torch.float32)},
        feature_names=feature_names,
        species_meta={101: {"name": "Alpha"}, 202: {"name": "Beta"}},
        combined_head_state=combined_head.state_dict(),
        combined_species_keys=[101, 202],
    )

    def _fail_batch_sample_raster(
        layer_id: str,
        coords: list[tuple[float, float]],
        dataset_cache: dict[tuple[str, str], object] | None = None,
    ) -> list[float | None]:
        raise AssertionError("static raster sampling should be skipped when cell-table features are available")

    def _fake_load_temporal_raster_array(
        variable_id: str,
        window_hours: int,
        forecast_hours: int,
        temporal_raster_cache: dict[tuple[str, int, int], object] | None = None,
    ) -> object:
        assert variable_id == "temperature_2m"
        assert window_hours == 24
        assert forecast_hours == 24
        return torch.tensor([[3.0]], dtype=torch.float32).numpy()

    def _fake_score_combined_logits_tensor(
        feature_tensor: torch.Tensor,
        *,
        score_batch_size: int,
    ) -> list[torch.Tensor]:
        temporal_values = feature_tensor[:, 1].cpu()
        return [torch.stack([temporal_values, -temporal_values], dim=1)]

    monkeypatch.setattr(inference, "_batch_sample_raster", _fail_batch_sample_raster)
    monkeypatch.setattr(inference, "_load_temporal_raster_array", _fake_load_temporal_raster_array)
    monkeypatch.setattr(inference, "_score_combined_logits_tensor", _fake_score_combined_logits_tensor)

    inference.load_bundle(bundle_path)
    ranked, sources = inference.rank_species_weather_delta_coords(
        [(0.125, 0.125)],
        top_k=2,
        min_delta=-10.0,
        score_batch_size=1,
        include_source=True,
        backed_species_only=False,
    )

    assert ranked[0] is not None
    assert [entry["species_key"] for entry in ranked[0]] == [101, 202]
    assert ranked[0][0]["delta_logit"] > 0.0
    assert ranked[0][0]["weather_logit"] > ranked[0][0]["baseline_logit"]
    assert ranked[0][1]["delta_logit"] < 0.0
    assert ranked[0][0]["has_species_head"] is True
    assert sources == ["cell_table_temporal"]


def test_rank_species_weather_delta_coords_falls_back_to_sampled_weather_without_cell_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_path = tmp_path / "bundle.pt"
    feature_names = {
        "bioclimate": ["bio_1"],
        "landclass": [],
        "terrain": [],
        "temporal": ["temperature_2m_avg_24h"],
        "other": [],
    }

    combined_head = CombinedSpeciesHead(embed_dim=4, species_count=1)

    _write_inference_bundle(
        bundle_path,
        input_dim=4,
        cell_table={},
        feature_names=feature_names,
        species_meta={101: {"name": "Alpha"}},
        combined_head_state=combined_head.state_dict(),
        combined_species_keys=[101],
    )

    def _fake_batch_sample_features(
        coords: list[tuple[float, float]],
        *,
        raster_dataset_cache=None,
        dem_dataset_cache=None,
        temporal_mode="missing",
        temporal_forecast_hours=None,
        temporal_raster_cache=None,
        profile=None,
    ):
        assert temporal_mode == "current"
        return [{"features": torch.tensor([0.5, 3.0, 0.0, 0.0], dtype=torch.float32)} for _ in coords]

    def _fake_score_combined_logits_tensor(
        feature_tensor: torch.Tensor,
        *,
        score_batch_size: int,
    ) -> list[torch.Tensor]:
        temporal_values = feature_tensor[:, 1].cpu()
        return [temporal_values.unsqueeze(1)]

    monkeypatch.setattr(inference, "_batch_sample_features", _fake_batch_sample_features)
    monkeypatch.setattr(inference, "_score_combined_logits_tensor", _fake_score_combined_logits_tensor)

    inference.load_bundle(bundle_path)
    ranked, sources = inference.rank_species_weather_delta_coords(
        [(0.125, 0.125)],
        top_k=1,
        min_delta=-10.0,
        score_batch_size=1,
        include_source=True,
        backed_species_only=False,
    )

    assert ranked[0] is not None
    assert ranked[0][0]["delta_logit"] > 0.0
    assert sources == ["sampled_weather"]


def test_score_species_coords_accepts_sampled_feature_payloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle_path = tmp_path / "bundle.pt"
    feature_names = {
        "bioclimate": ["bio_1"],
        "landclass": [],
        "terrain": [],
        "temporal": [],
        "other": [],
    }

    _write_inference_bundle(
        bundle_path,
        input_dim=1,
        cell_table={},
        feature_names=feature_names,
    )

    sampled_payload = {"features": torch.tensor([0.25], dtype=torch.float32)}

    monkeypatch.setattr(
        inference,
        "_batch_sample_features",
        lambda coords, **_kwargs: [sampled_payload for _ in coords],
    )
    monkeypatch.setattr(
        inference,
        "_score_species_feature_tensor",
        lambda species_key, feature_tensor, *, score_batch_size, cancel_check=None: feature_tensor[:, 0].cpu().tolist(),
    )

    inference.load_bundle(bundle_path)
    scores, sources = inference.score_species_coords(
        101,
        [(0.125, 0.125)],
        resolution_hint=0.01,
        feature_mode="prefer_cell_table",
        include_source=True,
    )

    assert scores == [0.25]
    assert sources == ["sampled"]


def test_batch_sample_raster_reads_compact_window_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raster_path = tmp_path / "fake.tif"
    raster_path.write_text("stub", encoding="utf-8")
    observed_windows: list[tuple[int, int, int, int]] = []

    class _FakeWindow:
        def __init__(self, col_off: int, row_off: int, width: int, height: int) -> None:
            self.col_off = col_off
            self.row_off = row_off
            self.width = width
            self.height = height

    class _FakeDataset:
        nodata = None
        width = 100
        height = 100

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def index(self, lon: float, lat: float) -> tuple[int, int]:
            return (int(round(lat * 10)), int(round(lon * 10)))

        def read(self, indexes: int, window: _FakeWindow, boundless: bool = False):
            observed_windows.append((window.row_off, window.col_off, window.height, window.width))
            arr = np.empty((window.height, window.width), dtype=np.float32)
            for row in range(window.height):
                for col in range(window.width):
                    arr[row, col] = float((window.row_off + row) * 1000 + (window.col_off + col))
            return arr

        def sample(self, xy):
            raise AssertionError("compact window path should avoid ds.sample")

        def close(self) -> None:
            return None

    fake_rasterio = SimpleNamespace(open=lambda path: _FakeDataset())
    monkeypatch.setitem(sys.modules, "rasterio", fake_rasterio)
    monkeypatch.setitem(sys.modules, "rasterio.windows", SimpleNamespace(Window=_FakeWindow))
    monkeypatch.setattr(gis_lookup, "get_region_name", lambda lat, lon: "region-a")
    monkeypatch.setattr(gis_lookup, "get_cog_path", lambda layer_id, lat, lon: raster_path)

    values = inference._batch_sample_raster(
        "bio_1",
        [(1.0, 2.0), (1.1, 2.1), (1.2, 2.2)],
        dataset_cache=None,
    )

    assert values == [10020.0, 11021.0, 12022.0]
    assert observed_windows == [(10, 20, 3, 3)]
