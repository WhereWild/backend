#!/usr/bin/env python3
"""
Train a bare‑bones presence/absence model for a species using the enriched
observation features and a random background sample.

The script is intentionally lightweight: it balances presences with sampled
background cells, fits a logistic regression (interpretable, fast), emits a
few metrics, and scores the entire region grid so we can draw probability
maps. Tweak/extend as needed – this is scaffolding for future experiments.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

# Columns emitted by sample_species_features.py that we do not want to feed directly
# into the model (IDs, coordinates, timestamps, provenance).
DEFAULT_EXCLUDE = {
    "observation_id",
    "species_id",
    "observed_at",
    "observed_month",
    "latitude",
    "longitude",
    "projected_x",
    "projected_y",
    "grid_x",
    "grid_y",
    "cell_id",
    "presence",  # label column
}


@dataclass
class ModelArtifacts:
    pipeline: Pipeline
    numeric_features: List[str]
    categorical_features: List[str]
    metrics: dict


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fit a baseline presence/absence model for a species."
    )
    parser.add_argument(
        "--features",
        type=Path,
        required=True,
        help="Path to the species feature table (CSV/Parquet, optionally gzipped).",
    )
    parser.add_argument(
        "--background",
        type=Path,
        required=True,
        help="Path to the regional feature grid (Parquet).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where model artifacts will be written.",
    )
    parser.add_argument(
        "--species",
        type=str,
        help="Species slug for logging (default: inferred from features filename).",
    )
    parser.add_argument(
        "--background-sample",
        type=int,
        help="Number of background rows to sample (default: 5x presence count).",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Hold-out fraction for evaluation (default: 0.2).",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for sampling and train/test split.",
    )
    return parser.parse_args(argv)


def load_features(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".gz" or path.name.endswith(".csv.gz"):
        return pd.read_csv(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported feature file format: {path}")


def pick_feature_columns(df: pd.DataFrame) -> List[str]:
    cols = [c for c in df.columns if c not in DEFAULT_EXCLUDE]
    if not cols:
        raise ValueError("No usable feature columns discovered.")
    return cols


def build_pipeline(
    numeric_features: List[str],
    categorical_features: List[str],
) -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ],
        remainder="drop",
    )

    clf = LogisticRegression(
        class_weight="balanced",
        max_iter=500,
        solver="lbfgs",
        n_jobs=None,
    )
    pipeline = Pipeline(steps=[("prep", preprocessor), ("model", clf)])
    return pipeline


def train_model(
    presences: pd.DataFrame,
    background: pd.DataFrame,
    features: List[str],
    test_size: float,
    random_state: int,
) -> ModelArtifacts:
    pres_df = presences.copy()
    pres_df["label"] = 1

    bg_df = background.copy()
    bg_df["label"] = 0

    combined = pd.concat([pres_df, bg_df], ignore_index=True)

    numeric_features = [
        col for col in features if pd.api.types.is_numeric_dtype(combined[col])
    ]
    categorical_features = [col for col in features if col not in numeric_features]

    X = combined[features]
    y = combined["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    pipeline = build_pipeline(numeric_features, categorical_features)
    pipeline.fit(X_train, y_train)

    proba = pipeline.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "log_loss": float(log_loss(y_test, proba)),
        "accuracy": float(accuracy_score(y_test, preds)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_numeric_features": len(numeric_features),
        "n_categorical_features": len(categorical_features),
    }
    return ModelArtifacts(
        pipeline=pipeline,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        metrics=metrics,
    )


def sample_background(
    df: pd.DataFrame,
    sample_size: int,
    random_state: int,
) -> pd.DataFrame:
    if sample_size >= len(df):
        return df.copy()
    return df.sample(n=sample_size, random_state=random_state).copy()


def determine_species_name(path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    stem = path.stem
    if stem.endswith("_features"):
        stem = stem[:-len("_features")]
    return stem


def save_metrics(metrics_path: Path, metrics: dict) -> None:
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2))


def score_region(
    pipeline: Pipeline,
    region_df: pd.DataFrame,
    features: List[str],
) -> pd.DataFrame:
    usable = region_df.copy()
    missing_cols = [col for col in features if col not in usable.columns]
    for col in missing_cols:
        usable[col] = np.nan
    probs = pipeline.predict_proba(usable[features])[:, 1]
    result = pd.DataFrame(
        {
            "grid_x": usable.get("grid_x"),
            "grid_y": usable.get("grid_y"),
            "cell_id": usable.get("cell_id"),
            "prob_presence": probs,
        }
    )
    return result


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)

    pres_df = load_features(args.features)
    if "presence" not in pres_df.columns:
        raise ValueError("Species feature table must contain a 'presence' column.")
    pres_df = pres_df[pres_df["presence"] == 1]

    region_df = pd.read_parquet(args.background)

    feature_cols = pick_feature_columns(pres_df)
    available_cols = [col for col in feature_cols if col in region_df.columns]
    missing_cols = sorted(set(feature_cols) - set(available_cols))
    if missing_cols:
        print(
            f"Warning: dropping {len(missing_cols)} feature(s) missing from background grid: "
            f"{', '.join(missing_cols)}"
        )
    feature_cols = available_cols
    if not feature_cols:
        raise ValueError("No overlapping feature columns between presence table and background grid.")

    if args.background_sample:
        bg_sample = sample_background(region_df, args.background_sample, args.random_state)
    else:
        default_n = min(len(region_df), len(pres_df) * 5)
        bg_sample = sample_background(region_df, default_n, args.random_state)

    artifacts = train_model(
        presences=pres_df[feature_cols],
        background=bg_sample[feature_cols],
        features=feature_cols,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    species_name = determine_species_name(args.features, args.species)
    output_dir = args.output_dir / species_name
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = output_dir / "metrics.json"
    save_metrics(metrics_path, artifacts.metrics)

    model_path = output_dir / "model.joblib"
    joblib.dump(
        {
            "pipeline": artifacts.pipeline,
            "numeric_features": artifacts.numeric_features,
            "categorical_features": artifacts.categorical_features,
            "feature_columns": feature_cols,
        },
        model_path,
    )

    scored = score_region(artifacts.pipeline, region_df, feature_cols)
    predictions_path = output_dir / "predictions.parquet"
    scored.to_parquet(predictions_path, index=False)

    print(f"[{species_name}] Metrics -> {metrics_path}")
    print(f"[{species_name}] Model -> {model_path}")
    print(f"[{species_name}] Predictions -> {predictions_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
