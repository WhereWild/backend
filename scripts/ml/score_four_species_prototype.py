"""Score rows with the 4-species prototype model.

Supports both model artifacts:
- Legacy multiclass softmax
- Shared encoder + species embedding head (with calibration)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BACKGROUND_CLASS = "BACKGROUND"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score rows with 4-species prototype model")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path("artifacts/ml_prototype_4_species/model.npz"),
        help="Path to model.npz",
    )
    parser.add_argument("--input", type=Path, required=True, help="Input .parquet or .csv file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/ml_prototype_4_species/predictions.json"),
        help="Output JSON file path",
    )
    parser.add_argument("--max-rows", type=int, default=1000, help="Max rows to score")
    return parser


def _read_input(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported input extension: {path.suffix}. Use .parquet or .csv")


def _softmax(logits: np.ndarray) -> np.ndarray:
    stable = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(stable)
    return exp / exp.sum(axis=1, keepdims=True)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _prepare_features(df: pd.DataFrame, feature_columns: list[str]) -> np.ndarray:
    work = df.copy()
    if "decimalLatitude" in work.columns and "lat_sin" in feature_columns:
        lat_rad = np.deg2rad(
            pd.to_numeric(work["decimalLatitude"], errors="coerce").fillna(0.0).to_numpy(dtype=np.float64)
        )
        work["lat_sin"] = np.sin(lat_rad)
        work["lat_cos"] = np.cos(lat_rad)
    if "decimalLongitude" in work.columns and "lon_sin" in feature_columns:
        lon_rad = np.deg2rad(
            pd.to_numeric(work["decimalLongitude"], errors="coerce").fillna(0.0).to_numpy(dtype=np.float64)
        )
        work["lon_sin"] = np.sin(lon_rad)
        work["lon_cos"] = np.cos(lon_rad)

    for column in feature_columns:
        if column not in work.columns:
            work[column] = 0.0
    x = work[feature_columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    return x


def _load_model(artifact_path: Path) -> dict[str, Any]:
    artifact = np.load(artifact_path, allow_pickle=True)
    feature_columns = [str(column) for column in artifact["feature_columns"].tolist()]
    mean = artifact["mean"].astype(np.float64)
    std = artifact["std"].astype(np.float64)

    model_family = "legacy_softmax"
    if "model_family" in artifact.files:
        model_family_raw = artifact["model_family"]
        if model_family_raw.size > 0:
            model_family = str(model_family_raw.tolist()[0])

    if "encoder_weights" in artifact.files and "species_embeddings" in artifact.files:
        species_names = [str(name) for name in artifact["species_names"].tolist()]
        return {
            "model_family": model_family,
            "feature_columns": feature_columns,
            "mean": mean,
            "std": std,
            "encoder_weights": artifact["encoder_weights"].astype(np.float64),
            "encoder_bias": artifact["encoder_bias"].astype(np.float64),
            "species_embeddings": artifact["species_embeddings"].astype(np.float64),
            "species_bias": artifact["species_bias"].astype(np.float64),
            "calibration_scale": artifact["calibration_scale"].astype(np.float64)
            if "calibration_scale" in artifact.files
            else np.ones(len(species_names), dtype=np.float64),
            "calibration_bias": artifact["calibration_bias"].astype(np.float64)
            if "calibration_bias" in artifact.files
            else np.zeros(len(species_names), dtype=np.float64),
            "species_names": species_names,
        }

    class_names = [str(name) for name in artifact["class_names"].tolist()]
    return {
        "model_family": "legacy_softmax",
        "feature_columns": feature_columns,
        "mean": mean,
        "std": std,
        "weights": artifact["weights"].astype(np.float64),
        "bias": artifact["bias"].astype(np.float64),
        "class_names": class_names,
    }


def _score_embedding_head(model: dict[str, Any], x_scaled: np.ndarray) -> dict[str, np.ndarray]:
    hidden = np.tanh(x_scaled @ model["encoder_weights"] + model["encoder_bias"])
    out: dict[str, np.ndarray] = {}
    for idx, species in enumerate(model["species_names"]):
        logits = np.sum(hidden * model["species_embeddings"][idx], axis=1) + model["species_bias"][idx]
        calibrated = (model["calibration_scale"][idx] * logits) + model["calibration_bias"][idx]
        out[species] = _sigmoid(calibrated)
    return out


def _score_legacy_softmax(model: dict[str, Any], x_scaled: np.ndarray) -> dict[str, np.ndarray]:
    probabilities = _softmax(x_scaled @ model["weights"] + model["bias"])
    class_to_idx = {name: idx for idx, name in enumerate(model["class_names"])}
    species_names = [name for name in model["class_names"] if name != BACKGROUND_CLASS]
    return {species: probabilities[:, class_to_idx[species]] for species in species_names}


def main() -> None:
    args = _build_arg_parser().parse_args()
    root = _repo_root()

    model_path = (root / args.model_path).resolve()
    input_path = (root / args.input).resolve()
    output_path = (root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    model = _load_model(model_path)

    frame = _read_input(input_path)
    if args.max_rows > 0 and len(frame) > args.max_rows:
        frame = frame.head(args.max_rows).copy()

    x_raw = _prepare_features(frame, model["feature_columns"])
    x_scaled = (x_raw - model["mean"]) / np.where(model["std"] < 1e-8, 1.0, model["std"])
    x_scaled = np.nan_to_num(x_scaled, nan=0.0, posinf=0.0, neginf=0.0)

    if "species_names" in model:
        score_map = _score_embedding_head(model, x_scaled)
        species_names = list(model["species_names"])
    else:
        score_map = _score_legacy_softmax(model, x_scaled)
        species_names = list(score_map.keys())

    lat_values = (
        pd.to_numeric(frame["decimalLatitude"], errors="coerce").to_numpy(dtype=np.float64)
        if "decimalLatitude" in frame.columns
        else None
    )
    lon_values = (
        pd.to_numeric(frame["decimalLongitude"], errors="coerce").to_numpy(dtype=np.float64)
        if "decimalLongitude" in frame.columns
        else None
    )

    records: list[dict[str, Any]] = []
    for idx in range(len(frame)):
        species_scores = {species: float(score_map[species][idx]) for species in species_names}
        top_species = max(species_scores.items(), key=lambda item: item[1])[0]

        record: dict[str, Any] = {
            "row_index": int(idx),
            "scores": species_scores,
            "top_species": top_species,
            "top_score": float(species_scores[top_species]),
        }
        if lat_values is not None and np.isfinite(lat_values[idx]):
            record["decimalLatitude"] = float(lat_values[idx])
        if lon_values is not None and np.isfinite(lon_values[idx]):
            record["decimalLongitude"] = float(lon_values[idx])
        records.append(record)

    output = {
        "model_path": str(model_path),
        "model_family": model["model_family"],
        "input_path": str(input_path),
        "rows_scored": len(records),
        "species_order": species_names,
        "predictions": records,
    }
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("Saved predictions:", output_path)
    print("Rows scored:", len(records))


if __name__ == "__main__":
    main()
