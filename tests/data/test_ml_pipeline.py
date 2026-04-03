from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import pytest
import torch

from scripts.machine_learning.preprocess_training import pipeline
from scripts.machine_learning.preprocess_training import resume_from_staging, transform
from scripts.machine_learning.train import data as training_data
from scripts.machine_learning.train import export
from scripts.machine_learning.train.model import SharedEncoder, SpeciesHead
from util import inference


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
            "species_key": pa.array([101], type=pa.int64()),
            "presence_label": pa.array([1], type=pa.int8()),
            "sample_weight": pa.array([1.0], type=pa.float32()),
            "cell_id": pa.array([cell_id], type=pa.string()),
        }
    )
    pq.write_table(table, split_dir / part_name)


def _write_inference_bundle(
    path: Path,
    *,
    input_dim: int,
    cell_table: dict[str, dict[str, torch.Tensor]],
    feature_names: dict[str, list[str]],
    species_key: int = 101,
    species_name: str = "Test species",
    embed_dim: int = 4,
    hidden_dim: int = 8,
) -> Path:
    encoder = SharedEncoder(input_dim=input_dim, embed_dim=embed_dim, hidden_dim=hidden_dim)
    head = SpeciesHead(embed_dim=embed_dim)
    torch.save(
        {
            "input_dim": input_dim,
            "embed_dim": embed_dim,
            "hidden_dim": hidden_dim,
            "encoder_state_dict": encoder.state_dict(),
            "head_states": {species_key: head.state_dict()},
            "species_meta": {species_key: {"name": species_name}},
            "cell_table": cell_table,
            "cell_size_deg": 0.25,
            "feature_names": feature_names,
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
        missing_feature_sentinel=-9999.0,
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
    assert row.column("terrain_features")[0].as_py() == [-9999.0, 3.0]
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
            missing_feature_sentinel=-9999.0,
            warn_min_cells_per_species=0,
            static_context=None,
            temporal_context=None,
        )


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
    # The two rows are averaged elementwise: e.g. (1 + 11) / 2 = 6. The second
    # feature is then zeroed because its averaged missing mask is 1.0.
    assert payload["features"].tolist() == [6.0, 0.0, 8.0, 9.0, 10.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    assert payload["mask"].tolist() == [0.0, 1.0, 0.0, 0.0, 0.0]


def test_load_bundle_and_predict_heatmap_stream_uses_loaded_cell_table(tmp_path: Path) -> None:
    bundle_path = _write_inference_bundle(
        tmp_path / "bundle.pt",
        input_dim=4,
        cell_table={
            "cell_0_0": {
                "features": torch.tensor([1.0, 2.0], dtype=torch.float32),
                "mask": torch.tensor([0.0, 0.0], dtype=torch.float32),
            }
        },
        feature_names={
            "bioclimate": ["bio_1"],
            "landclass": ["landcover"],
            "terrain": [],
            "temporal": [],
            "other": [],
        },
    )

    inference.load_bundle(bundle_path)
    stream = inference.predict_heatmap_stream(
        101,
        (0.0, 0.0, 0.24, 0.24),
        resolution=0.25,
        feature_mode="cell_table_only",
        include_source=True,
        max_cells=1,
        score_batch_size=1,
    )
    cells = list(stream["cells"])

    assert inference.is_loaded() is True
    assert inference.known_species() == [101]
    assert inference.cell_count() == 1
    assert inference.native_resolution() == 0.25
    assert stream["requested_cells"] == 1
    assert len(cells) == 1
    assert cells[0]["lat"] == 0.125
    assert cells[0]["lon"] == 0.125
    assert cells[0]["n_native"] == 1
    assert cells[0]["source"] == "cell_table"
    assert isinstance(cells[0]["score"], float)


def test_load_bundle_rejects_incompatible_cell_payload(tmp_path: Path) -> None:
    bundle_path = _write_inference_bundle(
        tmp_path / "invalid_bundle.pt",
        input_dim=4,
        cell_table={
            "cell_0_0": {
                "features": torch.tensor([1.0], dtype=torch.float32),
                "mask": torch.tensor([0.0], dtype=torch.float32),
            }
        },
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


def test_predict_heatmap_stream_rejects_invalid_requests(tmp_path: Path) -> None:
    bundle_path = _write_inference_bundle(
        tmp_path / "bundle.pt",
        input_dim=4,
        cell_table={
            "cell_0_0": {
                "features": torch.tensor([1.0, 2.0], dtype=torch.float32),
                "mask": torch.tensor([0.0, 0.0], dtype=torch.float32),
            }
        },
        feature_names={
            "bioclimate": ["bio_1"],
            "landclass": ["landcover"],
            "terrain": [],
            "temporal": [],
            "other": [],
        },
    )
    inference.load_bundle(bundle_path)

    with pytest.raises(KeyError, match="Species 999"):
        inference.predict_heatmap_stream(999, (0.0, 0.0, 0.24, 0.24), feature_mode="cell_table_only")
    with pytest.raises(ValueError, match="resolution must be > 0"):
        inference.predict_heatmap_stream(101, (0.0, 0.0, 0.24, 0.24), resolution=0.0)
    with pytest.raises(ValueError, match="min_lat must be less than max_lat"):
        inference.predict_heatmap_stream(101, (1.0, 0.0, 0.0, 0.24), feature_mode="cell_table_only")
    with pytest.raises(ValueError, match="score_batch_size must be > 0"):
        inference.predict_heatmap_stream(101, (0.0, 0.0, 0.24, 0.24), score_batch_size=0)


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
    assert feature_template == {
        "bioclimate": ["bio_1"],
        "landclass": ["landcover", "lithology"],
        "terrain": ["landform"],
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
    assert table.column("bioclimate_features")[0].as_py() == [1.5]
    assert table.column("landclass_features")[0].as_py() == [2.0, 7.0]
    assert table.column("terrain_features")[0].as_py() == [3.0]
    assert table.column("temporal_features")[0].as_py() == [4.5]
    assert not staging_dir.exists()


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
    (data_root / "_meta").mkdir(parents=True, exist_ok=True)
    (data_root / "_meta" / "feature_template.json").write_text(json.dumps(feature_names), encoding="utf-8")

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

    bundle_path = export.export_bundle(data_root, encoder_path, heads_path, output_bundle)
    inference.load_bundle(bundle_path)
    stream = inference.predict_heatmap_stream(
        101,
        (0.0, 0.0, 0.24, 0.24),
        resolution=0.25,
        feature_mode="cell_table_only",
        include_source=True,
        max_cells=1,
        score_batch_size=1,
    )
    cells = list(stream["cells"])

    assert bundle_path.exists()
    assert inference.is_loaded() is True
    assert inference.has_species(101) is True
    assert inference.cell_count() == 2
    assert inference.species_meta()[101]["name"] == "Test species"
    assert len(cells) == 1
    assert cells[0]["source"] == "cell_table"
    assert cells[0]["lat"] == 0.125
    assert cells[0]["lon"] == 0.125
    assert isinstance(cells[0]["score"], float)
