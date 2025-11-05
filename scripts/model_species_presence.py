#!/usr/bin/env python3
"""
Train a simple presence/absence classifier for a species using sampled features.

Given a feature table (from sample_species_features.py) and a background table,
this script fits a baseline scikit-learn model (logistic regression by default),
prints evaluation metrics, and writes predictions + metadata to disk.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import pandas as pd
except ModuleNotFoundError:
    raise SystemExit(
        "pandas is required for scripts/model_species_presence.py. "
        "Install with `pip install -r requirements.txt`."
    )

try:
    from sklearn.compose import ColumnTransformer
    from sklearn.metrics import classification_report, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
except ModuleNotFoundError:
    raise SystemExit(
        "scikit-learn is required for scripts/model_species_presence.py. "
        "Install with `pip install -r requirements.txt`."
    )


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a baseline classifier to predict species presence."
    )
    parser.add_argument(
        "--features",
        type=Path,
        required=True,
        help="Path to species feature table (CSV/Parquet) with presence column.",
    )
    parser.add_argument(
        "--background",
        type=Path,
        required=True,
        help="Path to background feature table (CSV/Parquet) for absence sampling.",
    )
    parser.add_argument(
        "--background-sample",
        type=int,
        help="Number of background rows to sample (default: match presence count).",
    )
    parser.add_argument(
        "--model",
        choices=["logistic", "random-forest"],
        default="logistic",
        help="Classifier to train (default: logistic).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models"),
        help="Directory for reports/predictions (default: models).",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="species_model",
        help="Filename prefix for outputs (default: species_model).",
    )
    parser.add_argument(
        "--no-predictions",
        action="store_true",
        help="Skip writing per-row prediction CSV.",
    )
    return parser.parse_args(argv)


def load_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix in {".gz", ".csv"} or path.suffixes[-1] == ".gz":
        return pd.read_csv(path)
    if path.suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file format for {path}")


def select_background(df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    if len(df) <= sample_size:
        return df.copy()
    return df.sample(sample_size, random_state=42).copy()


def build_model(model_name: str, numeric_cols: List[str], categorical_cols: List[str]) -> Pipeline:
    transformers = []
    if numeric_cols:
        transformers.append(("num", StandardScaler(), numeric_cols))
    if categorical_cols:
        transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols))

    preprocessor = ColumnTransformer(transformers=transformers)

    if model_name == "random-forest":
        estimator = RandomForestClassifier(n_estimators=300, random_state=42)
    else:
        estimator = LogisticRegression(max_iter=1000, solver="lbfgs")

    return Pipeline(steps=[("preprocess", preprocessor), ("model", estimator)])


def ensure_presence_column(df: pd.DataFrame, value: int) -> pd.DataFrame:
    if "presence" not in df.columns:
        df = df.copy()
        df["presence"] = value
    else:
        df["presence"] = df["presence"].astype(int)
    return df


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    presence_df = ensure_presence_column(load_table(args.features), 1)
    background_df = ensure_presence_column(load_table(args.background), 0)

    sample_size = args.background_sample or len(presence_df)
    background_df = select_background(background_df, sample_size)

    combined = pd.concat([presence_df, background_df], ignore_index=True)

    feature_cols = [col for col in ["elevation_m", "slope_deg", "aspect_deg", "roughness", "landcover_class"] if col in combined.columns]
    if not feature_cols:
        raise ValueError("No feature columns found. Expected at least one of elevation_m, slope_deg, aspect_deg, roughness, landcover_class.")

    numeric_cols = [col for col in feature_cols if col != "landcover_class"]
    categorical_cols = ["landcover_class"] if "landcover_class" in feature_cols else []

    combined = combined.dropna(subset=feature_cols + ["presence"])

    X = combined[feature_cols]
    y = combined["presence"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    pipeline = build_model(args.model, numeric_cols, categorical_cols)
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    report = classification_report(y_test, y_pred, output_dict=True)
    roc_auc = roc_auc_score(y_test, y_proba)

    summary = {
        "model": args.model,
        "presence_count": int(presence_df.shape[0]),
        "background_count": int(background_df.shape[0]),
        "metrics": {
            "roc_auc": roc_auc,
            "classification_report": report,
        },
        "feature_columns": feature_cols,
    }

    summary_path = output_dir / f"{args.prefix}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"Saved model summary -> {summary_path}")

    if not args.no_predictions:
        combined["predicted_proba"] = pipeline.predict_proba(X)[:, 1]
        predictions_path = output_dir / f"{args.prefix}_predictions.csv"
        combined.to_csv(predictions_path, index=False)
        print(f"Saved predictions -> {predictions_path}")

    model_path = output_dir / f"{args.prefix}_model.pkl"
    try:
        import joblib
    except ModuleNotFoundError:
        joblib = None

    if joblib:
        joblib.dump(pipeline, model_path)
        print(f"Serialized model -> {model_path}")
    else:
        print("joblib not installed; skipping model serialization.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

