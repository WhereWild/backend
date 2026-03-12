"""Export a trained model into a single inference bundle.

Packages the encoder, species heads, and a precomputed geocell feature
table into one .pt file that can be loaded on a CPU-only server without
access to the original training parquet or GIS tiles.

Usage:

  uv run python scripts/machine_learning/train/export.py \
    --data-root ./data/species_observation_canary_plants \
    --encoder-checkpoint ./checkpoints/canary_plants/encoder/encoder_best.pt \
    --heads-checkpoint ./checkpoints/canary_plants/heads/species_heads.pt \
    --output ./checkpoints/canary_plants/inference_bundle.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from importlib import import_module
from pathlib import Path

import numpy as np
import pyarrow.compute as pc
import pyarrow.dataset as ds
import torch

try:
    from ._compat import import_local_symbol
except ImportError:
    from _compat import import_local_symbol

FEATURE_COLUMNS = import_local_symbol("data", "FEATURE_COLUMNS")
MASK_COLUMNS = import_local_symbol("data", "MASK_COLUMNS")
_list_column_to_2d_numpy = import_local_symbol("data", "_list_column_to_2d_numpy")
_feature_contract = import_module("scripts.machine_learning._compat").import_feature_contract()
FEATURE_GROUPS = _feature_contract.FEATURE_GROUPS
format_feature_group_counts = _feature_contract.format_feature_group_counts
normalize_feature_template = _feature_contract.normalize_feature_template

_EXPORT_SCAN_BATCH_ROWS = 65_536
_EXPORT_PROGRESS_EVERY_ROWS = 5_000_000


def build_cell_table(
    data_root: Path,
) -> dict[str, dict[str, torch.Tensor]]:
    """Build a cell_id -> mean-feature / mean-mask lookup from all splits.

    Uses the actual training data so the lookup covers every cell the
    model was trained on.  For cells with multiple observations the
    feature values are averaged, giving a representative "cell profile".
    """
    dataset = ds.dataset(str(data_root), format="parquet", partitioning="hive")

    # Accumulate per-cell sums across all splits.
    cell_feat_sum: dict[str, np.ndarray] = {}
    cell_mask_sum: dict[str, np.ndarray] = {}
    cell_count: dict[str, int] = defaultdict(int)
    total_processed_rows = 0

    columns = [*FEATURE_COLUMNS, *MASK_COLUMNS, "cell_id"]

    for split in ("train", "val", "test"):
        split_ds = dataset.filter(pc.field("split") == split)
        split_rows = split_ds.count_rows()
        if split_rows <= 0:
            continue

        print(f"  Split {split}: scanning {split_rows:,} rows...")
        scanner = split_ds.scanner(columns=columns, batch_size=_EXPORT_SCAN_BATCH_ROWS)
        split_seen_rows = 0

        for record_batch in scanner.to_batches():
            if record_batch.num_rows == 0:
                continue

            feats: list[np.ndarray] = []
            msks: list[np.ndarray] = []
            for feat_col, mask_col in zip(FEATURE_COLUMNS, MASK_COLUMNS, strict=True):
                feats.append(_list_column_to_2d_numpy(record_batch.column(feat_col), feat_col))
                msks.append(_list_column_to_2d_numpy(record_batch.column(mask_col), mask_col))
            features = np.concatenate(feats, axis=1).astype(np.float64, copy=False)
            masks = np.concatenate(msks, axis=1).astype(np.float64, copy=False)

            cell_ids = np.asarray(record_batch.column("cell_id").to_numpy(zero_copy_only=False), dtype=str)
            if cell_ids.size == 0:
                continue

            unique_ids, inverse = np.unique(cell_ids, return_inverse=True)
            batch_feat_sum = np.zeros((len(unique_ids), features.shape[1]), dtype=np.float64)
            batch_mask_sum = np.zeros((len(unique_ids), masks.shape[1]), dtype=np.float64)
            batch_count = np.bincount(inverse, minlength=len(unique_ids)).astype(np.int64)
            np.add.at(batch_feat_sum, inverse, features)
            np.add.at(batch_mask_sum, inverse, masks)

            for idx, cid in enumerate(unique_ids.tolist()):
                if cid not in cell_feat_sum:
                    cell_feat_sum[cid] = np.zeros(features.shape[1], dtype=np.float64)
                    cell_mask_sum[cid] = np.zeros(masks.shape[1], dtype=np.float64)
                cell_feat_sum[cid] += batch_feat_sum[idx]
                cell_mask_sum[cid] += batch_mask_sum[idx]
                cell_count[cid] += int(batch_count[idx])

            split_seen_rows += int(record_batch.num_rows)
            total_processed_rows += int(record_batch.num_rows)
            if total_processed_rows % _EXPORT_PROGRESS_EVERY_ROWS < int(record_batch.num_rows):
                print(f"    Processed rows so far: {total_processed_rows:,}")

        print(f"  Split {split}: processed {split_seen_rows:,} rows")

    result: dict[str, dict[str, torch.Tensor]] = {}
    for cid in cell_feat_sum:
        n = cell_count[cid]
        avg_feat = (cell_feat_sum[cid] / n).astype(np.float32)
        # For the mask, if *any* observation had the feature present (mask 0)
        # treat it as present.  Threshold at 0.5: majority-missing → missing.
        avg_mask = (cell_mask_sum[cid] / n >= 0.5).astype(np.float32)
        # Zero out features where the mask says missing.
        avg_feat[avg_mask > 0.5] = 0.0
        model_feat = np.concatenate([avg_feat, avg_mask], axis=0)
        result[cid] = {
            "features": torch.from_numpy(model_feat),
            "mask": torch.from_numpy(avg_mask),
        }

    return result


def _load_feature_names(data_root: Path) -> dict[str, list[str]] | None:
    """Load feature names saved during preprocessing, or derive from catalog."""
    candidate_paths = [
        data_root / "_meta" / "feature_template.json",
        data_root / "feature_template.json",
    ]
    for template_path in candidate_paths:
        if template_path.exists():
            with open(template_path) as f:
                raw = json.load(f)
            return normalize_feature_template(raw)

    # Fallback: derive from the GIS catalog using the same classification rules
    # the preprocessing pipeline uses.
    try:
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        catalog_candidates = [
            project_root / "config" / "gis" / "catalog.json",
            project_root / "data" / "gis" / "catalog.json",
        ]
        catalog_path = next((p for p in catalog_candidates if p.exists()), None)
        if catalog_path is None:
            return None
        with open(catalog_path) as f:
            catalog = json.load(f)

        grouped: dict[str, set[str]] = {group: set() for group in FEATURE_GROUPS if group != "other"}
        for category in catalog.get("categories", []):
            for layer in category.get("layers", []):
                lid = layer.get("id")
                if not isinstance(lid, str) or not lid:
                    continue
                category_name = str(category.get("name", "")).strip().lower()
                if category_name in grouped:
                    grouped[category_name].add(lid)
        return {
            "bioclimate": sorted(grouped["bioclimate"]),
            "landclass": sorted(grouped["landclass"]),
            "terrain": sorted(grouped["terrain"]),
            "edaphic": sorted(grouped["edaphic"]),
            "temporal": sorted(grouped["temporal"]),
            "other": [],
        }
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def export_bundle(
    data_root: Path,
    encoder_path: Path,
    heads_path: Path,
    output_path: Path,
    cell_size_deg: float = 0.25,
) -> Path:
    """Create a single inference bundle file."""
    encoder_ckpt = torch.load(encoder_path, map_location="cpu", weights_only=True)
    heads_ckpt = torch.load(heads_path, map_location="cpu", weights_only=True)

    print("Building geocell feature table from training data...")
    cell_table = build_cell_table(data_root)
    print(f"Geocell table: {len(cell_table):,} unique cells")

    feature_names = _load_feature_names(data_root)
    if feature_names is not None:
        print(f"Feature names: {format_feature_group_counts(feature_names)}")
    else:
        print("Warning: could not determine feature names; on-the-fly GIS sampling will be unavailable.")

    bundle = {
        # Encoder config + weights
        "input_dim": encoder_ckpt["input_dim"],
        "embed_dim": encoder_ckpt["embed_dim"],
        "hidden_dim": encoder_ckpt["hidden_dim"],
        "encoder_state_dict": encoder_ckpt["encoder_state_dict"],
        # Species heads
        "head_states": heads_ckpt["head_states"],
        "species_meta": heads_ckpt["species_meta"],
        # Geocell feature lookup
        "cell_table": cell_table,
        "cell_size_deg": cell_size_deg,
        # Feature names for on-the-fly GIS sampling
        "feature_names": feature_names,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(bundle, output_path)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Saved inference bundle: {output_path} ({size_mb:.1f} MB)")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export model inference bundle.")
    parser.add_argument("--data-root", type=Path, required=True, help="Preprocessed parquet dataset root.")
    parser.add_argument("--encoder-checkpoint", type=Path, required=True, help="Path to encoder_best.pt.")
    parser.add_argument("--heads-checkpoint", type=Path, required=True, help="Path to species_heads.pt.")
    parser.add_argument("--output", type=Path, required=True, help="Output path for inference bundle.")
    parser.add_argument("--cell-size-deg", type=float, default=0.25, help="Geocell bin size in degrees.")
    args = parser.parse_args()

    export_bundle(
        data_root=args.data_root,
        encoder_path=args.encoder_checkpoint,
        heads_path=args.heads_checkpoint,
        output_path=args.output,
        cell_size_deg=args.cell_size_deg,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
