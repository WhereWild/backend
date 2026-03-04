"""Export a trained model into a single inference bundle.

Packages the encoder, species heads, and a precomputed geocell feature
table into one .pt file that can be loaded on a CPU-only server without
access to the original training parquet or GIS tiles.

Usage:

  uv run python scripts/machine_learning/train/export.py \
      --data-root ./data/species_observation_canary_cactus \
      --encoder-checkpoint ./checkpoints/canary_cactus/encoder/encoder_best.pt \
      --heads-checkpoint ./checkpoints/canary_cactus/heads/species_heads.pt \
      --output ./checkpoints/canary_cactus/inference_bundle.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

try:
    from ._compat import import_local_symbol
except ImportError:
    from _compat import import_local_symbol

TrainingDataset = import_local_symbol("data", "TrainingDataset")


def build_cell_table(
    data_root: Path,
) -> dict[str, dict[str, torch.Tensor]]:
    """Build a cell_id -> mean-feature / mean-mask lookup from all splits.

    Uses the actual training data so the lookup covers every cell the
    model was trained on.  For cells with multiple observations the
    feature values are averaged, giving a representative "cell profile".
    """
    # Accumulate per-cell sums across all splits.
    cell_feat_sum: dict[str, np.ndarray] = defaultdict(lambda: np.zeros(0))
    cell_mask_sum: dict[str, np.ndarray] = defaultdict(lambda: np.zeros(0))
    cell_count: dict[str, int] = defaultdict(int)

    for split in ("train", "val", "test"):
        try:
            ds = TrainingDataset(data_root, split=split)
        except (FileNotFoundError, OSError, ValueError, RuntimeError):
            continue

        features = ds.features.numpy().astype(np.float64, copy=False)
        masks = ds.masks.numpy().astype(np.float64, copy=False)
        cell_ids = np.asarray(ds.cell_ids, dtype=str)

        if len(cell_ids) == 0:
            continue

        unique_ids, inverse = np.unique(cell_ids, return_inverse=True)
        split_feat_sum = np.zeros((len(unique_ids), features.shape[1]), dtype=np.float64)
        split_mask_sum = np.zeros((len(unique_ids), masks.shape[1]), dtype=np.float64)
        split_count = np.bincount(inverse, minlength=len(unique_ids)).astype(np.int64)

        np.add.at(split_feat_sum, inverse, features)
        np.add.at(split_mask_sum, inverse, masks)

        for idx, cid in enumerate(unique_ids):
            if cell_feat_sum[cid].shape[0] == 0:
                cell_feat_sum[cid] = np.zeros(features.shape[1], dtype=np.float64)
                cell_mask_sum[cid] = np.zeros(masks.shape[1], dtype=np.float64)
            cell_feat_sum[cid] += split_feat_sum[idx]
            cell_mask_sum[cid] += split_mask_sum[idx]
            cell_count[cid] += int(split_count[idx])

    result: dict[str, dict[str, torch.Tensor]] = {}
    for cid in cell_feat_sum:
        n = cell_count[cid]
        avg_feat = (cell_feat_sum[cid] / n).astype(np.float32)
        # For the mask, if *any* observation had the feature present (mask 0)
        # treat it as present.  Threshold at 0.5: majority-missing → missing.
        avg_mask = (cell_mask_sum[cid] / n >= 0.5).astype(np.float32)
        # Zero out features where the mask says missing.
        avg_feat[avg_mask > 0.5] = 0.0
        result[cid] = {
            "features": torch.from_numpy(avg_feat),
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
            return {"env": raw["env"], "habitat": raw["habitat"], "weather": raw.get("weather", [])}

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

        env: set[str] = set()
        habitat: set[str] = set()
        for category in catalog.get("categories", []):
            if category.get("name") == "temporal":
                continue
            for layer in category.get("layers", []):
                lid = layer.get("id", "")
                name = lid.lower()
                if name.startswith(("bio_", "climate_")) or name in {
                    "elevation", "slope", "aspect", "aspect_deg",
                }:
                    env.add(lid)
                elif name.startswith(("habitat_", "landcover_", "ndvi", "canopy_", "terrain_")) or name in {
                    "landcover", "koppen_geiger",
                }:
                    habitat.add(lid)
        return {"env": sorted(env), "habitat": sorted(habitat), "weather": []}
    except Exception:
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
        print(
            f"Feature names: env={len(feature_names['env'])}, "
            f"habitat={len(feature_names['habitat'])}, "
            f"weather={len(feature_names.get('weather', []))}"
        )
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
