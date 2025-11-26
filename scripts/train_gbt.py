#!/usr/bin/env python3
from __future__ import annotations

import json
from collections.abc import Iterable
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform as rio_transform

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "processed"
SPECIES_CATALOG_PATH = PROCESSED_DIR / "species" / "species_catalog.json"
SPECIES_ROOT = SPECIES_CATALOG_PATH.parent
GIS_CATALOG_PATH = REPO_ROOT / "gis_catalog.json"
MODELS_DIR = PROCESSED_DIR / "models" / "gbt"
WGS84 = CRS.from_epsg(4326)

# Tunable knobs. Leave filters as None to run on every species and GIS variable.
SPECIES_ID_FILTER: list[int] | None = [148405]
VARIABLE_ID_FILTER: list[str] | None = None
NEGATIVES_PER_POSITIVE = 3
LEARNING_RATE = 0.05
BOOSTING_ROUNDS = 1000
EARLY_STOPPING_ROUNDS = 50
NUM_LEAVES = 31
FEATURE_FRACTION = 0.8
BAGGING_FRACTION = 0.8
BAGGING_FREQ = 1
MIN_DATA_IN_LEAF = 20
FOLDS = 5
SEED = 13
MAX_BACKGROUND_ATTEMPTS = 50
LOSS_LOG_INTERVAL = 20


@dataclass(frozen=True)
class DirectionBin:
    id: str
    start_deg: float
    end_deg: float


@dataclass
class RasterVariable:
    id: str
    dataset: rasterio.io.DatasetReader
    value_type: str
    direction_bins: list[DirectionBin] | None = None

    @property
    def is_categorical(self) -> bool:
        return self.value_type in {"categorical", "circular"}


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def load_species_catalog() -> dict[int, dict]:
    with SPECIES_CATALOG_PATH.open() as fp:
        entries = json.load(fp)
    return {int(entry["taxon_id"]): entry for entry in entries}


def load_gis_catalog() -> dict[str, dict]:
    with GIS_CATALOG_PATH.open() as fp:
        entries = json.load(fp)
    return {entry["id"]: entry for entry in entries}


def load_direction_bins(definition_path: str | None) -> list[DirectionBin]:
    if not definition_path:
        return []
    path = REPO_ROOT / definition_path
    if not path.exists():
        raise SystemExit(f"Direction bin definition missing at {path}")
    with path.open() as fp:
        entries = json.load(fp)
    bins: list[DirectionBin] = []
    for entry in entries:
        bins.append(
            DirectionBin(
                id=entry.get("id", f"bin_{len(bins)}"),
                start_deg=float(entry["start_deg"]),
                end_deg=float(entry["end_deg"]),
            )
        )
    return bins


def load_presence_points(parquet_path: Path) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_parquet(parquet_path, columns=["latitude", "longitude"]).dropna()
    if df.empty:
        raise RuntimeError(f"No valid coordinates found in {parquet_path}")
    return df["latitude"].to_numpy(), df["longitude"].to_numpy()


def project_coords(
    lats: np.ndarray,
    lons: np.ndarray,
    dst_crs: CRS | None,
) -> tuple[np.ndarray, np.ndarray]:
    if dst_crs is None or dst_crs == WGS84:
        return np.asarray(lons, dtype="float64"), np.asarray(lats, dtype="float64")
    xs, ys = rio_transform(WGS84, dst_crs, lons.tolist(), lats.tolist())
    return np.asarray(xs, dtype="float64"), np.asarray(ys, dtype="float64")


def to_wgs84(
    xs: np.ndarray,
    ys: np.ndarray,
    src_crs: CRS | None,
) -> tuple[np.ndarray, np.ndarray]:
    if src_crs is None or src_crs == WGS84:
        return np.asarray(ys, dtype="float64"), np.asarray(xs, dtype="float64")
    lons, lats = rio_transform(src_crs, WGS84, xs.tolist(), ys.tolist())
    return np.asarray(lats, dtype="float64"), np.asarray(lons, dtype="float64")


def sample_background_coords(
    dataset: rasterio.io.DatasetReader,
    count: int,
    rng: np.random.Generator,
    max_attempts: int = 50,
) -> tuple[np.ndarray, np.ndarray]:
    bounds = dataset.bounds
    lats: list[float] = []
    lons: list[float] = []
    attempts = 0
    batch_size = min(5000, max(count * 2, 1000))
    while len(lats) < count and attempts < max_attempts:
        attempts += 1
        size = min(batch_size, (count - len(lats)) * 2)
        xs = rng.uniform(bounds.left, bounds.right, size=size)
        ys = rng.uniform(bounds.bottom, bounds.top, size=size)
        lat_candidates, lon_candidates = to_wgs84(xs, ys, dataset.crs)
        coords = list(zip(xs.tolist(), ys.tolist()))
        values = np.fromiter(
            (val[0] for val in dataset.sample(coords)),
            dtype="float64",
            count=len(coords),
        )
        valid = np.isfinite(values)
        if dataset.nodata is not None:
            valid &= values != dataset.nodata
        for lat, lon, ok in zip(lat_candidates, lon_candidates, valid):
            if ok:
                lats.append(float(lat))
                lons.append(float(lon))
                if len(lats) >= count:
                    break
    if len(lats) < count:
        raise RuntimeError(
            f"Only gathered {len(lats)} background locations after {attempts} attempts."
        )
    return np.asarray(lats), np.asarray(lons)


def sample_dataset_values(
    dataset: rasterio.io.DatasetReader,
    lats: np.ndarray,
    lons: np.ndarray,
) -> np.ndarray:
    xs, ys = project_coords(lats, lons, dataset.crs)
    coords = list(zip(xs.tolist(), ys.tolist()))
    values = np.fromiter((val[0] for val in dataset.sample(coords)), dtype="float64", count=len(coords))
    valid = np.isfinite(values)
    if dataset.nodata is not None:
        valid &= values != dataset.nodata
    result = values.astype("float64", copy=False)
    result[~valid] = np.nan
    return result


def _direction_mask(values: np.ndarray, start_deg: float, end_deg: float) -> np.ndarray:
    start = start_deg % 360.0
    end = end_deg % 360.0
    if start <= end:
        return (values >= start) & (values < end)
    return (values >= start) | (values < end)


def bin_circular_values(values: np.ndarray, bins: list[DirectionBin]) -> np.ndarray:
    if not bins:
        raise RuntimeError("Circular variable defined without direction bins.")
    result = np.full(values.shape, np.nan, dtype="float64")
    valid_idx = np.where(np.isfinite(values))[0]
    if valid_idx.size == 0:
        return result
    normalized = np.mod(values[valid_idx], 360.0)
    for idx, bin_def in enumerate(bins):
        mask = _direction_mask(normalized, bin_def.start_deg, bin_def.end_deg)
        if np.any(mask):
            result[valid_idx[mask]] = float(idx)
    return result


def transform_feature_values(values: np.ndarray, variable: RasterVariable) -> np.ndarray:
    if variable.value_type == "circular":
        return bin_circular_values(values, variable.direction_bins or [])
    return values


def coords_to_feature_matrix(
    lats: np.ndarray,
    lons: np.ndarray,
    rasters: list[RasterVariable],
) -> np.ndarray:
    if lats.size == 0:
        raise RuntimeError("No coordinates provided for feature extraction.")
    feature_columns: list[np.ndarray] = []
    for variable in rasters:
        values = sample_dataset_values(variable.dataset, lats, lons)
        feature_columns.append(transform_feature_values(values, variable))
    matrix = np.vstack(feature_columns).T
    valid_mask = np.isfinite(matrix).all(axis=1)
    filtered = matrix[valid_mask]
    if filtered.size == 0:
        raise RuntimeError("All samples were filtered out as invalid.")
    return filtered


def build_training_arrays(
    positive_lats: np.ndarray,
    positive_lons: np.ndarray,
    negative_lats: np.ndarray,
    negative_lons: np.ndarray,
    rasters: list[RasterVariable],
) -> tuple[np.ndarray, np.ndarray]:
    pos_matrix = coords_to_feature_matrix(positive_lats, positive_lons, rasters)
    neg_matrix = coords_to_feature_matrix(negative_lats, negative_lons, rasters)
    y_pos = np.ones(len(pos_matrix), dtype="float64")
    y_neg = np.zeros(len(neg_matrix), dtype="float64")
    x = np.vstack([pos_matrix, neg_matrix])
    y = np.concatenate([y_pos, y_neg])
    return x, y


@dataclass
class Standardizer:
    mean_: np.ndarray
    scale_: np.ndarray
    categorical_mask: np.ndarray

    @classmethod
    def fit(cls, data: np.ndarray, categorical_mask: np.ndarray) -> Standardizer:
        mean = np.mean(data, axis=0)
        scale = np.std(data, axis=0)
        scale = np.where(scale < 1e-6, 1.0, scale)
        adjusted_mean = np.where(categorical_mask, 0.0, mean)
        adjusted_scale = np.where(categorical_mask, 1.0, scale)
        return cls(adjusted_mean, adjusted_scale, categorical_mask.copy())

    def transform(self, data: np.ndarray) -> np.ndarray:
        transformed = data.copy()
        if transformed.size == 0:
            return transformed
        mask = ~self.categorical_mask
        if np.any(mask):
            transformed[:, mask] = (transformed[:, mask] - self.mean_[mask]) / self.scale_[mask]
        return transformed


def lightgbm_params() -> dict:
    return {
        "objective": "binary",
        "metric": ["binary_logloss"],
        "learning_rate": LEARNING_RATE,
        "num_leaves": NUM_LEAVES,
        "feature_fraction": FEATURE_FRACTION,
        "bagging_fraction": BAGGING_FRACTION,
        "bagging_freq": BAGGING_FREQ,
        "min_data_in_leaf": MIN_DATA_IN_LEAF,
        "verbosity": -1,
    }


def train_with_validation(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    categorical_features: list[int],
    verbose: bool,
) -> tuple[lgb.Booster, int]:
    train_set = lgb.Dataset(x_train, label=y_train, categorical_feature=categorical_features)
    val_set = lgb.Dataset(x_val, label=y_val, categorical_feature=categorical_features)
    callbacks: list = [lgb.early_stopping(EARLY_STOPPING_ROUNDS)]
    if verbose:
        callbacks.append(lgb.log_evaluation(LOSS_LOG_INTERVAL))
    booster = lgb.train(
        lightgbm_params(),
        train_set,
        num_boost_round=BOOSTING_ROUNDS,
        valid_sets=[val_set],
        valid_names=["valid"],
        callbacks=callbacks,
    )
    best_iter = booster.best_iteration or BOOSTING_ROUNDS
    return booster, best_iter


def train_final_model(
    features: np.ndarray,
    labels: np.ndarray,
    num_boost_round: int,
    categorical_features: list[int],
) -> lgb.Booster:
    train_set = lgb.Dataset(features, label=labels, categorical_feature=categorical_features)
    booster = lgb.train(
        lightgbm_params(),
        train_set,
        num_boost_round=max(1, num_boost_round),
        valid_sets=[train_set],
        valid_names=["train"],
        callbacks=[lgb.log_evaluation(LOSS_LOG_INTERVAL)],
    )
    return booster


def binary_log_loss(y_true: np.ndarray, probs: np.ndarray) -> float:
    eps = 1e-9
    clipped = np.clip(probs, eps, 1 - eps)
    loss = -np.mean(y_true * np.log(clipped) + (1 - y_true) * np.log(1 - clipped))
    return float(loss)


def average_precision(y_true: np.ndarray, probs: np.ndarray) -> float:
    if probs.size == 0:
        return float("nan")
    order = np.argsort(-probs)
    y_sorted = y_true[order]
    positives = y_sorted.sum()
    if positives == 0:
        return 0.0
    cum_tp = np.cumsum(y_sorted)
    precision = cum_tp / (np.arange(len(y_sorted)) + 1)
    return float(np.sum(precision * y_sorted) / positives)


def make_folds(
    n_samples: int,
    n_folds: int,
    rng: np.random.Generator,
) -> Iterable[tuple[np.ndarray, np.ndarray]]:
    folds = max(2, min(n_folds, n_samples))
    indices = np.arange(n_samples)
    rng.shuffle(indices)
    fold_sizes = np.full(folds, n_samples // folds, dtype=int)
    fold_sizes[: n_samples % folds] += 1
    current = 0
    for fold_size in fold_sizes:
        start, stop = current, current + fold_size
        val_idx = indices[start:stop]
        train_idx = np.concatenate([indices[:start], indices[stop:]])
        current = stop
        yield train_idx, val_idx


def cross_validate(
    features: np.ndarray,
    labels: np.ndarray,
    folds: int,
    rng: np.random.Generator,
    categorical_mask: np.ndarray,
    categorical_features: list[int],
) -> tuple[list[dict[str, float]], list[int]]:
    metrics: list[dict[str, float]] = []
    best_iterations: list[int] = []
    for fold, (train_idx, val_idx) in enumerate(make_folds(len(features), folds, rng), start=1):
        x_train = features[train_idx]
        y_train = labels[train_idx]
        x_val = features[val_idx]
        y_val = labels[val_idx]
        scaler = Standardizer.fit(x_train, categorical_mask)
        booster, best_iter = train_with_validation(
            scaler.transform(x_train),
            y_train,
            scaler.transform(x_val),
            y_val,
            categorical_features,
            verbose=False,
        )
        probs = booster.predict(scaler.transform(x_val), num_iteration=best_iter)
        metrics.append(
            {
                "fold": fold,
                "log_loss": binary_log_loss(y_val, probs),
                "avg_precision": average_precision(y_val, probs),
            }
        )
        best_iterations.append(best_iter)
    return metrics, best_iterations


def save_model_artifacts(
    species_id: int,
    species_slug: str,
    species_name: str,
    variable_ids: list[str],
    scaler: Standardizer,
    booster: lgb.Booster,
    best_iteration: int,
    metrics: dict,
    cross_val_metrics: list[dict[str, float]],
    feature_importance_pairs: list[tuple[str, float]],
    categorical_variables: list[str],
) -> None:
    ensure_directory(MODELS_DIR)
    payload = {
        "species_id": species_id,
        "species_name": species_name,
        "variables": variable_ids,
        "model": {
            "type": "lightgbm",
            "booster": booster.model_to_string(num_iteration=best_iteration),
            "best_iteration": best_iteration,
            "feature_importance": booster.feature_importance(importance_type="gain").tolist(),
            "feature_importance_pairs": feature_importance_pairs,
            "categorical_variables": categorical_variables,
        },
        "scaler": {
            "mean": scaler.mean_.tolist(),
            "scale": scaler.scale_.tolist(),
        },
        "metrics": metrics,
        "cross_validation": cross_val_metrics,
        "training_config": {
            "negatives_per_positive": NEGATIVES_PER_POSITIVE,
            "learning_rate": LEARNING_RATE,
            "boosting_rounds": BOOSTING_ROUNDS,
            "early_stopping_rounds": EARLY_STOPPING_ROUNDS,
            "num_leaves": NUM_LEAVES,
            "feature_fraction": FEATURE_FRACTION,
            "bagging_fraction": BAGGING_FRACTION,
            "bagging_freq": BAGGING_FREQ,
            "min_data_in_leaf": MIN_DATA_IN_LEAF,
            "folds": FOLDS,
            "seed": SEED,
        },
    }
    slug_prefix = species_slug or species_name.lower().replace(" ", "_")
    model_path = MODELS_DIR / f"{slug_prefix}_{species_id}.json"
    with model_path.open("w") as fp:
        json.dump(payload, fp, indent=2)
    rel_path = model_path.relative_to(REPO_ROOT)
    print(f"Saved model artifacts to {rel_path}")


def main() -> None:
    rng = np.random.default_rng(SEED)
    species_catalog = load_species_catalog()
    if SPECIES_ID_FILTER:
        missing_species = [sid for sid in SPECIES_ID_FILTER if sid not in species_catalog]
        if missing_species:
            raise SystemExit(f"Species missing from catalog: {', '.join(map(str, missing_species))}")
        target_species_ids = SPECIES_ID_FILTER
    else:
        target_species_ids = sorted(species_catalog.keys())
    if not target_species_ids:
        raise SystemExit("No species selected for training.")
    gis_catalog = load_gis_catalog()
    if VARIABLE_ID_FILTER:
        missing_vars = [var for var in VARIABLE_ID_FILTER if var not in gis_catalog]
        if missing_vars:
            raise SystemExit(f"GIS variables missing from catalog: {', '.join(missing_vars)}")
        variable_ids = VARIABLE_ID_FILTER
    else:
        variable_ids = sorted(gis_catalog.keys())
    if not variable_ids:
        raise SystemExit("No GIS variables available for feature extraction.")
    with ExitStack() as stack:
        rasters: list[RasterVariable] = []
        categorical_variables: list[str] = []
        categorical_features: list[int] = []
        for idx, variable_id in enumerate(variable_ids):
            entry = gis_catalog[variable_id]
            path = REPO_ROOT / entry["path"]
            if not path.exists():
                raise SystemExit(f"Raster for {variable_id} missing at {path}")
            value_type = (entry.get("value_type") or "continuous").lower()
            direction_bins = None
            if value_type == "circular":
                direction_bins = load_direction_bins(entry.get("direction_bins_file"))
                if not direction_bins:
                    raise SystemExit(
                        f"Circular variable '{variable_id}' missing direction bin definitions."
                    )
            raster = RasterVariable(
                id=variable_id,
                dataset=stack.enter_context(rasterio.open(path)),
                value_type=value_type,
                direction_bins=direction_bins,
            )
            rasters.append(raster)
            if raster.is_categorical:
                categorical_variables.append(variable_id)
                categorical_features.append(idx)
        if not rasters:
            raise SystemExit("Failed to open any raster datasets.")
        categorical_mask = np.array([raster.is_categorical for raster in rasters], dtype=bool)
        summary: list[dict[str, float]] = []
        for species_id in target_species_ids:
            species_entry = species_catalog[species_id]
            species_name = species_entry.get("scientific_name", str(species_id))
            species_slug = species_entry.get("slug") or species_name.lower().replace(" ", "_")
            parquet_path = SPECIES_ROOT / species_entry["parquet_file"]
            print(
                f"\n=== Training {species_name} (taxon_id={species_id}) "
                f"using {len(variable_ids)} variables ==="
            )
            try:
                pos_lats, pos_lons = load_presence_points(parquet_path)
            except RuntimeError as exc:
                print(f"[SKIP] {exc}")
                continue
            neg_target = max(1, int(len(pos_lats) * NEGATIVES_PER_POSITIVE))
            reference_dataset = rasters[0].dataset
            try:
                species_seed = int(rng.integers(0, 2**32 - 1))
                species_rng = np.random.default_rng(species_seed)
                neg_lats, neg_lons = sample_background_coords(
                    reference_dataset, neg_target, species_rng, MAX_BACKGROUND_ATTEMPTS
                )
                features, labels = build_training_arrays(
                    pos_lats, pos_lons, neg_lats, neg_lons, rasters
                )
            except RuntimeError as exc:
                print(f"[SKIP] Failed to build dataset: {exc}")
                continue
            positives = int(labels.sum())
            negatives = features.shape[0] - positives
            print(
                f"Prepared {features.shape[0]} samples "
                f"({positives} positives / {negatives} negatives) with {features.shape[1]} features."
            )
            metrics, best_iters = cross_validate(
                features,
                labels,
                folds=FOLDS,
                rng=species_rng,
                categorical_mask=categorical_mask,
                categorical_features=categorical_features,
            )
            mean_log_loss = float(np.mean([m["log_loss"] for m in metrics]))
            mean_ap = float(np.mean([m["avg_precision"] for m in metrics]))
            print("Cross-validation metrics (log loss / AP):")
            for metric in metrics:
                print(
                    f"  Fold {metric['fold']}: "
                    f"{metric['log_loss']:.4f} logloss, {metric['avg_precision']:.4f} AP"
                )
            print(
                f"Mean log loss: {mean_log_loss:.4f} | Mean average precision: {mean_ap:.4f}"
            )
            scaler = Standardizer.fit(features, categorical_mask)
            scaled_features = scaler.transform(features)
            avg_best_iter = int(np.mean(best_iters)) if best_iters else BOOSTING_ROUNDS
            avg_best_iter = max(10, avg_best_iter)
            print(f"Training final LightGBM model for {avg_best_iter} rounds...")
            final_model = train_final_model(
                scaled_features,
                labels,
                avg_best_iter,
                categorical_features,
            )
            baseline = labels.mean()
            print(f"Class prevalence (positive prior): {baseline:.4f}")
            importance = final_model.feature_importance(importance_type="gain")
            sorted_idx = np.argsort(-importance)
            importance_pairs = [
                (variable_ids[idx], float(importance[idx])) for idx in sorted_idx
            ]
            print("Top feature importances (gain):")
            for idx in sorted_idx[: min(10, len(variable_ids))]:
                print(f"  {variable_ids[idx]:>24}: {importance[idx]:.4f}")
            save_model_artifacts(
                species_id=species_id,
                species_slug=species_slug,
                species_name=species_name,
                variable_ids=variable_ids,
                scaler=scaler,
                booster=final_model,
                best_iteration=avg_best_iter,
                metrics={
                    "log_loss": mean_log_loss,
                    "avg_precision": mean_ap,
                    "baseline": baseline,
                    "positives": positives,
                    "negatives": negatives,
                    "samples": features.shape[0],
                },
                cross_val_metrics=metrics,
                feature_importance_pairs=importance_pairs,
                categorical_variables=categorical_variables,
            )
            summary.append(
                {
                    "species_id": species_id,
                    "species_name": species_name,
                    "samples": features.shape[0],
                    "positives": positives,
                    "log_loss": mean_log_loss,
                    "avg_precision": mean_ap,
                    "best_iteration": avg_best_iter,
                }
            )
    if summary:
        print("\n=== Aggregate summary ===")
        for record in summary:
            print(
                f"{record['species_name']} ({record['species_id']}): "
                f"logloss={record['log_loss']:.4f}, AP={record['avg_precision']:.4f}, "
                f"samples={record['samples']}, positives={record['positives']}, "
                f"rounds={record['best_iteration']}"
            )
    else:
        print("No species models were trained.")


if __name__ == "__main__":
    main()
