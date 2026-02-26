"""Train a spec-aligned 4-species PU prototype with shared encoder + embedding head.

This script keeps the same default artifact path as the previous prototype while
upgrading the model to:
- Shared tabular geospatial encoder
- Species embedding head (dot product + species bias)
- Presence-vs-background objective with focal-weighted BCE
- Optional hard negatives from ecologically similar species
- Per-species Platt calibration artifacts

Run from repo root:

    python scripts/ml/train_four_species_prototype.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SPECIES_ORDER = [
    "Escobaria vivipara",
    "Haliaeetus leucocephalus",
    "Spea intermontana",
    "Hypaurotis crysalus",
]

BACKGROUND_CLASS = "BACKGROUND"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_species_paths(root: Path) -> dict[str, Path]:
    base = root / "data" / "species" / "taxonomy"
    return {
        "Escobaria vivipara": base
        / "Plantae_6/Tracheophyta_7707728/Magnoliopsida_220/Caryophyllales_422/Cactaceae_2519/Pelecyphora_3231951/Pelecyphora_vivipara_11498251/occurrence.parquet",
        "Haliaeetus leucocephalus": base
        / "Animalia_1/Chordata_44/Aves_212/Accipitriformes_7191147/Accipitridae_2877/Haliaeetus_2480444/Haliaeetus_leucocephalus_2480446/occurrence.parquet",
        "Spea intermontana": base
        / "Animalia_1/Chordata_44/Amphibia_131/Anura_952/Scaphiopodidae_3098/Spea_2429782/Spea_intermontana_2429791/occurrence.parquet",
        "Hypaurotis crysalus": base
        / "Animalia_1/Arthropoda_54/Insecta_216/Lepidoptera_797/Lycaenidae_5473/Hypaurotis_1933996/Hypaurotis_crysalus_1933998/occurrence.parquet",
    }


def _sample_frame(df: pd.DataFrame, max_rows: int | None, seed: int) -> pd.DataFrame:
    if max_rows is None or len(df) <= max_rows:
        return df
    return df.sample(n=max_rows, random_state=seed)


def _read_species_occurrences(
    species_paths: dict[str, Path],
    caps: dict[str, int | None],
    seed: int,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for species in SPECIES_ORDER:
        path = species_paths[species]
        if not path.exists():
            raise FileNotFoundError(f"Missing occurrence parquet for {species}: {path}")

        frame = pd.read_parquet(path)
        frame = _sample_frame(frame, caps.get(species), seed)
        frame = frame.copy()
        frame["species_name"] = species
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def _is_identifier_column(name: str) -> bool:
    lower = name.lower()
    if lower in {"species_name", "label", "target_species_idx", "is_positive"}:
        return True
    if "catalog" in lower or "tileid" in lower:
        return True
    if lower.endswith("gid") or "gid" in lower:
        return True
    if lower.endswith("key"):
        return True
    if lower in {"eventtimestamp", "obscured", "sex", "lifestage", "dp", "rcs", "vitality", "gall"}:
        return True
    return False


def _add_geospatial_harmonics(df: pd.DataFrame) -> pd.DataFrame:
    if "decimalLatitude" not in df.columns or "decimalLongitude" not in df.columns:
        return df
    out = df.copy()
    lat_rad = np.deg2rad(pd.to_numeric(out["decimalLatitude"], errors="coerce").fillna(0.0).to_numpy(dtype=np.float64))
    lon_rad = np.deg2rad(pd.to_numeric(out["decimalLongitude"], errors="coerce").fillna(0.0).to_numpy(dtype=np.float64))
    out["lat_sin"] = np.sin(lat_rad)
    out["lat_cos"] = np.cos(lat_rad)
    out["lon_sin"] = np.sin(lon_rad)
    out["lon_cos"] = np.cos(lon_rad)
    return out


def _select_feature_columns(df: pd.DataFrame) -> list[str]:
    numeric = df.select_dtypes(include=[np.number, bool]).columns.tolist()
    features = [name for name in numeric if not _is_identifier_column(name)]
    if not features:
        raise ValueError("No numeric feature columns found after filtering")
    return features


def _apply_geo_feature_mode(positives: pd.DataFrame, geo_feature_mode: str) -> tuple[pd.DataFrame, list[str]]:
    mode = geo_feature_mode.strip().lower()
    if mode not in {"cyclic", "both", "raw"}:
        raise ValueError("geo_feature_mode must be one of: cyclic, both, raw")

    with_harmonics = _add_geospatial_harmonics(positives)
    feature_columns = _select_feature_columns(with_harmonics)

    if mode == "cyclic":
        feature_columns = [
            column for column in feature_columns if column not in {"decimalLatitude", "decimalLongitude"}
        ]
    elif mode == "raw":
        feature_columns = [
            column for column in feature_columns if column not in {"lat_sin", "lat_cos", "lon_sin", "lon_cos"}
        ]

    if not feature_columns:
        raise ValueError("No feature columns remain after applying geo_feature_mode")
    return with_harmonics, feature_columns


def _make_background_rows(
    positives: pd.DataFrame,
    feature_columns: list[str],
    ratio: int,
    seed: int,
) -> pd.DataFrame:
    if ratio < 1:
        raise ValueError("background_ratio must be >= 1")

    target_rows = len(positives) * ratio
    rng = np.random.default_rng(seed)

    if "coordinateUncertaintyInMeters" in positives.columns:
        uncertainty = pd.to_numeric(positives["coordinateUncertaintyInMeters"], errors="coerce").to_numpy(
            dtype=np.float64
        )
        uncertainty_fill = float(
            np.nanmedian(uncertainty[np.isfinite(uncertainty)]) if np.isfinite(uncertainty).any() else 1000.0
        )
        uncertainty = np.nan_to_num(
            uncertainty,
            nan=uncertainty_fill,
        )
        weights = 1.0 / np.clip(uncertainty, 1.0, None)
        weights = weights / weights.sum() if weights.sum() > 0 else None
    else:
        weights = None

    sampled_idx = rng.choice(len(positives), size=target_rows, replace=target_rows > len(positives), p=weights)
    sampled = positives.iloc[sampled_idx].reset_index(drop=True)

    background = sampled[feature_columns].copy()
    for carry_col in (
        "decimalLatitude",
        "decimalLongitude",
        "koppen_geiger",
        "landcover",
        "level0Gid",
        "eventTimestamp",
    ):
        if carry_col in sampled.columns and carry_col not in background.columns:
            background[carry_col] = sampled[carry_col]
    background["species_name"] = BACKGROUND_CLASS
    return background


def _spatial_hash_split(df: pd.DataFrame, val_fraction: float) -> np.ndarray:
    if "decimalLatitude" not in df.columns or "decimalLongitude" not in df.columns:
        raise ValueError("spatial split requires decimalLatitude and decimalLongitude")

    lat_bucket = np.floor(
        (pd.to_numeric(df["decimalLatitude"], errors="coerce").fillna(0.0).to_numpy() + 90.0) * 10.0
    ).astype(np.int64)
    lon_bucket = np.floor(
        (pd.to_numeric(df["decimalLongitude"], errors="coerce").fillna(0.0).to_numpy() + 180.0) * 10.0
    ).astype(np.int64)
    hash_bucket = np.abs((lat_bucket * 73856093) ^ (lon_bucket * 19349663)) % 100
    threshold = int(round(val_fraction * 100))
    return hash_bucket < threshold


def _temporal_split(df: pd.DataFrame, val_fraction: float) -> np.ndarray:
    if "eventTimestamp" not in df.columns:
        raise ValueError("temporal split requires eventTimestamp")
    ts = pd.to_datetime(df["eventTimestamp"], errors="coerce", utc=True)
    valid = ts.notna()
    if valid.sum() == 0:
        raise ValueError("eventTimestamp has no parsable values for temporal split")
    threshold = ts[valid].quantile(1.0 - val_fraction)
    if pd.isna(threshold):
        return np.zeros(len(df), dtype=bool)
    threshold_ts = pd.Timestamp(threshold)
    return (ts >= threshold_ts).to_numpy(dtype=bool)


def _train_val_mask(df: pd.DataFrame, split_method: str, val_fraction: float, seed: int) -> np.ndarray:
    if split_method == "spatial":
        return _spatial_hash_split(df, val_fraction)
    if split_method == "temporal":
        return _temporal_split(df, val_fraction)

    rng = np.random.default_rng(seed)
    return rng.random(len(df)) < val_fraction


def _standardize(train_x: np.ndarray, val_x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = np.nanmean(train_x, axis=0)
    std = np.nanstd(train_x, axis=0)
    std = np.where(std < 1e-8, 1.0, std)

    train_x = np.nan_to_num((train_x - mean) / std, nan=0.0, posinf=0.0, neginf=0.0)
    val_x = np.nan_to_num((val_x - mean) / std, nan=0.0, posinf=0.0, neginf=0.0)
    return train_x, val_x, mean, std


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _binary_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = y_true.astype(np.int64)
    n_pos = int(y.sum())
    n_neg = int(len(y) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return float("nan")

    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1, dtype=np.float64)
    rank_sum_pos = ranks[y == 1].sum()
    auc = (rank_sum_pos - (n_pos * (n_pos + 1) / 2.0)) / (n_pos * n_neg)
    return float(auc)


def _average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = y_true.astype(np.int64)
    n_pos = int(y.sum())
    if n_pos == 0:
        return float("nan")

    order = np.argsort(-scores)
    y_sorted = y[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / n_pos

    ap = 0.0
    prev_recall = 0.0
    for p, r in zip(precision, recall):
        ap += p * max(0.0, r - prev_recall)
        prev_recall = r
    return float(ap)


def _expected_calibration_error(y_true: np.ndarray, probs: np.ndarray, bins: int = 10) -> float:
    y = y_true.astype(np.float64)
    if len(y) == 0:
        return float("nan")
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for idx in range(bins):
        left = edges[idx]
        right = edges[idx + 1]
        if idx == bins - 1:
            mask = (probs >= left) & (probs <= right)
        else:
            mask = (probs >= left) & (probs < right)
        if not np.any(mask):
            continue
        conf = float(probs[mask].mean())
        acc = float(y[mask].mean())
        ece += (mask.mean()) * abs(conf - acc)
    return float(ece)


def _eco_similarity_mask(frame: pd.DataFrame, target_species: str, candidate_species: str) -> np.ndarray:
    target = frame[frame["species_name"] == target_species]
    candidate = frame[frame["species_name"] == candidate_species]
    if target.empty or candidate.empty:
        return np.zeros(len(candidate), dtype=bool)

    mask = np.ones(len(candidate), dtype=bool)
    if "koppen_geiger" in frame.columns:
        target_vals = set(pd.to_numeric(target["koppen_geiger"], errors="coerce").dropna().astype(int).tolist())
        cand_vals = pd.to_numeric(candidate["koppen_geiger"], errors="coerce").fillna(-9999).astype(int).to_numpy()
        mask &= np.isin(cand_vals, list(target_vals))
    if "landcover" in frame.columns:
        target_vals = set(pd.to_numeric(target["landcover"], errors="coerce").dropna().astype(int).tolist())
        cand_vals = pd.to_numeric(candidate["landcover"], errors="coerce").fillna(-9999).astype(int).to_numpy()
        mask &= np.isin(cand_vals, list(target_vals))
    return mask


def _build_pairwise_dataset(
    positives: pd.DataFrame,
    background: pd.DataFrame,
    feature_columns: list[str],
    background_ratio: int,
    hard_negative_ratio: float,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames: list[pd.DataFrame] = []

    bg_with_meta = background.copy()
    for col in ("koppen_geiger", "landcover", "decimalLatitude", "decimalLongitude", "level0Gid"):
        if col not in bg_with_meta.columns and col in positives.columns:
            bg_with_meta[col] = 0.0

    positives_by_species = {
        species: positives[positives["species_name"] == species].copy() for species in SPECIES_ORDER
    }

    for species_idx, species in enumerate(SPECIES_ORDER):
        pos = positives_by_species[species].copy()
        pos["target_species_idx"] = species_idx
        pos["is_positive"] = 1
        frames.append(pos)

        bg_n = min(len(bg_with_meta), max(len(pos), len(pos) * max(1, background_ratio // len(SPECIES_ORDER))))
        bg_sample = bg_with_meta.sample(
            n=bg_n, replace=bg_n > len(bg_with_meta), random_state=seed + species_idx
        ).copy()
        bg_sample["target_species_idx"] = species_idx
        bg_sample["is_positive"] = 0
        frames.append(bg_sample)

        hard_n = int(round(len(pos) * max(0.0, hard_negative_ratio)))
        if hard_n <= 0:
            continue

        hard_frames: list[pd.DataFrame] = []
        for other in SPECIES_ORDER:
            if other == species:
                continue
            candidate = positives_by_species[other]
            if candidate.empty:
                continue
            eco_mask = _eco_similarity_mask(positives, species, other)
            hard_source = candidate.loc[eco_mask].copy() if eco_mask.any() else candidate.copy()
            if hard_source.empty:
                continue
            hard_frames.append(hard_source)

        if not hard_frames:
            continue
        hard_all = pd.concat(hard_frames, ignore_index=True)
        sampled_idx = rng.choice(len(hard_all), size=hard_n, replace=hard_n > len(hard_all))
        hard = hard_all.iloc[sampled_idx].reset_index(drop=True)
        hard["target_species_idx"] = species_idx
        hard["is_positive"] = 0
        frames.append(hard)

    pairwise = pd.concat(frames, ignore_index=True)
    needed = list(dict.fromkeys(feature_columns + ["target_species_idx", "is_positive", "species_name", "level0Gid"]))
    return pairwise[[column for column in needed if column in pairwise.columns]].copy()


def _forward_logits(
    x: np.ndarray,
    target_species_idx: np.ndarray,
    encoder_w: np.ndarray,
    encoder_b: np.ndarray,
    species_embeddings: np.ndarray,
    species_bias: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    hidden_pre = x @ encoder_w + encoder_b
    hidden = np.tanh(hidden_pre)
    emb = species_embeddings[target_species_idx]
    logits = np.sum(hidden * emb, axis=1) + species_bias[target_species_idx]
    return logits, hidden


def _train_embedding_head(
    train_x: np.ndarray,
    train_target_species: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_target_species: np.ndarray,
    val_y: np.ndarray,
    n_species: int,
    latent_dim: int,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    l2: float,
    focal_gamma: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, float]]]:
    rng = np.random.default_rng(seed)
    n_features = train_x.shape[1]

    encoder_w = rng.normal(0.0, 0.05, size=(n_features, latent_dim)).astype(np.float64)
    encoder_b = np.zeros(latent_dim, dtype=np.float64)
    species_embeddings = rng.normal(0.0, 0.05, size=(n_species, latent_dim)).astype(np.float64)
    species_bias = np.zeros(n_species, dtype=np.float64)

    pos_count = max(1, int(train_y.sum()))
    neg_count = max(1, int(len(train_y) - pos_count))
    pos_weight = neg_count / float(pos_count)
    neg_weight = 1.0

    history: list[dict[str, float]] = []

    for epoch in range(1, epochs + 1):
        order = rng.permutation(len(train_x))
        x_shuf = train_x[order]
        t_shuf = train_target_species[order]
        y_shuf = train_y[order]

        for start in range(0, len(x_shuf), batch_size):
            end = start + batch_size
            xb = x_shuf[start:end]
            tb = t_shuf[start:end]
            yb = y_shuf[start:end]

            logits, hidden = _forward_logits(
                xb,
                tb,
                encoder_w,
                encoder_b,
                species_embeddings,
                species_bias,
            )
            probs = _sigmoid(logits)

            pt = (yb * probs) + ((1.0 - yb) * (1.0 - probs))
            focal = np.power(np.clip(1.0 - pt, 1e-6, 1.0), focal_gamma)
            class_weights = np.where(yb > 0.5, pos_weight, neg_weight)
            grad_logits = (probs - yb) * focal * class_weights
            grad_logits /= max(1, len(yb))

            grad_species_embeddings = np.zeros_like(species_embeddings)
            np.add.at(grad_species_embeddings, tb, grad_logits[:, None] * hidden)
            grad_species_bias = np.zeros_like(species_bias)
            np.add.at(grad_species_bias, tb, grad_logits)

            grad_hidden = grad_logits[:, None] * species_embeddings[tb]
            grad_hidden_pre = grad_hidden * (1.0 - np.square(hidden))

            grad_encoder_w = xb.T @ grad_hidden_pre + (l2 * encoder_w)
            grad_encoder_b = grad_hidden_pre.sum(axis=0)

            encoder_w -= learning_rate * grad_encoder_w
            encoder_b -= learning_rate * grad_encoder_b
            species_embeddings -= learning_rate * (grad_species_embeddings + (l2 * species_embeddings))
            species_bias -= learning_rate * grad_species_bias

        train_logits, _ = _forward_logits(
            train_x,
            train_target_species,
            encoder_w,
            encoder_b,
            species_embeddings,
            species_bias,
        )
        val_logits, _ = _forward_logits(
            val_x,
            val_target_species,
            encoder_w,
            encoder_b,
            species_embeddings,
            species_bias,
        )
        train_probs = _sigmoid(train_logits)
        val_probs = _sigmoid(val_logits)

        train_bce = -np.mean(
            (train_y * np.log(np.clip(train_probs, 1e-12, 1.0)))
            + ((1.0 - train_y) * np.log(np.clip(1.0 - train_probs, 1e-12, 1.0)))
        )
        val_bce = -np.mean(
            (val_y * np.log(np.clip(val_probs, 1e-12, 1.0)))
            + ((1.0 - val_y) * np.log(np.clip(1.0 - val_probs, 1e-12, 1.0)))
        )

        history.append({
            "epoch": float(epoch),
            "train_bce": float(train_bce),
            "val_bce": float(val_bce),
            "pos_weight": float(pos_weight),
            "focal_gamma": float(focal_gamma),
        })

    return encoder_w, encoder_b, species_embeddings, species_bias, history


def _fit_platt_scaling(
    logits: np.ndarray, y_true: np.ndarray, epochs: int = 200, lr: float = 0.05
) -> tuple[float, float]:
    scale = 1.0
    bias = 0.0
    y = y_true.astype(np.float64)
    x = logits.astype(np.float64)

    for _ in range(epochs):
        probs = _sigmoid((scale * x) + bias)
        grad_logits = probs - y
        grad_scale = float(np.mean(grad_logits * x))
        grad_bias = float(np.mean(grad_logits))
        scale -= lr * grad_scale
        bias -= lr * grad_bias

    return float(scale), float(bias)


def _score_species(
    x: np.ndarray,
    species_idx: int,
    encoder_w: np.ndarray,
    encoder_b: np.ndarray,
    species_embeddings: np.ndarray,
    species_bias: np.ndarray,
    scale: float,
    bias: float,
) -> np.ndarray:
    target = np.full(len(x), species_idx, dtype=np.int64)
    logits, _ = _forward_logits(x, target, encoder_w, encoder_b, species_embeddings, species_bias)
    calibrated = (scale * logits) + bias
    return _sigmoid(calibrated)


def _regional_topk_precision(
    frame: pd.DataFrame,
    species_scores: np.ndarray,
    species_name: str,
    k: int = 10,
) -> float:
    if "level0Gid" not in frame.columns:
        return float("nan")

    work = pd.DataFrame({
        "level0Gid": frame["level0Gid"].fillna("__missing__").astype(str),
        "is_positive": (frame["species_name"] == species_name).astype(np.int64),
        "score": species_scores,
    })
    grouped = work.groupby("level0Gid", observed=True).agg(
        score=("score", "mean"),
        positives=("is_positive", "sum"),
    )
    if grouped.empty:
        return float("nan")
    top = grouped.sort_values("score", ascending=False).head(k)
    return float((top["positives"] > 0).mean())


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train spec-aligned 4-species PU prototype")
    parser.add_argument("--background-ratio", type=int, default=10)
    parser.add_argument("--hard-negative-ratio", type=float, default=0.5)
    parser.add_argument("--latent-dim", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--l2", type=float, default=1e-5)
    parser.add_argument("--focal-gamma", type=float, default=2.0)
    parser.add_argument("--split-method", choices=["spatial", "random", "temporal"], default="spatial")
    parser.add_argument(
        "--geo-feature-mode",
        choices=["cyclic", "both", "raw"],
        default="cyclic",
        help="Coordinate feature strategy: cyclic (sin/cos only), both, or raw lat/lon only",
    )
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/ml_prototype_4_species"),
        help="Directory for model + metrics + calibration outputs",
    )

    parser.add_argument("--cap-escobaria", type=int, default=9_193)
    parser.add_argument("--cap-haliaeetus", type=int, default=20_000)
    parser.add_argument("--cap-spea", type=int, default=1_239)
    parser.add_argument("--cap-hypaurotis", type=int, default=342)
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()
    root = _repo_root()
    output_dir = (root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    species_paths = _default_species_paths(root)
    caps: dict[str, int | None] = {
        "Escobaria vivipara": args.cap_escobaria,
        "Haliaeetus leucocephalus": args.cap_haliaeetus,
        "Spea intermontana": args.cap_spea,
        "Hypaurotis crysalus": args.cap_hypaurotis,
    }

    positives = _read_species_occurrences(species_paths, caps, args.seed)
    positives, feature_columns = _apply_geo_feature_mode(positives, args.geo_feature_mode)

    meta_columns = [
        column
        for column in ["species_name", "decimalLatitude", "decimalLongitude", "level0Gid", "eventTimestamp"]
        if column in positives.columns or column == "species_name"
    ]
    selected_columns = list(dict.fromkeys(feature_columns + meta_columns))
    positives_model = positives[selected_columns].copy()
    background = _make_background_rows(
        positives=positives_model,
        feature_columns=feature_columns,
        ratio=args.background_ratio,
        seed=args.seed,
    )

    pairwise = _build_pairwise_dataset(
        positives=positives_model,
        background=background,
        feature_columns=feature_columns,
        background_ratio=args.background_ratio,
        hard_negative_ratio=args.hard_negative_ratio,
        seed=args.seed,
    )

    val_mask = _train_val_mask(pairwise, args.split_method, args.val_fraction, args.seed)
    if val_mask.sum() == 0 or val_mask.sum() == len(pairwise):
        raise ValueError("Split produced empty train or validation set; adjust val_fraction")

    train_df = pairwise.loc[~val_mask].reset_index(drop=True)
    val_df = pairwise.loc[val_mask].reset_index(drop=True)

    train_x = train_df[feature_columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
    val_x = val_df[feature_columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
    train_target = train_df["target_species_idx"].to_numpy(dtype=np.int64)
    val_target = val_df["target_species_idx"].to_numpy(dtype=np.int64)
    train_y = train_df["is_positive"].to_numpy(dtype=np.float64)
    val_y = val_df["is_positive"].to_numpy(dtype=np.float64)

    train_x, val_x, mean, std = _standardize(train_x, val_x)

    encoder_w, encoder_b, species_embeddings, species_bias, history = _train_embedding_head(
        train_x=train_x,
        train_target_species=train_target,
        train_y=train_y,
        val_x=val_x,
        val_target_species=val_target,
        val_y=val_y,
        n_species=len(SPECIES_ORDER),
        latent_dim=args.latent_dim,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        l2=args.l2,
        focal_gamma=args.focal_gamma,
        seed=args.seed,
    )

    calibration_scale: list[float] = []
    calibration_bias: list[float] = []
    per_species_metrics: dict[str, dict[str, float | int]] = {}

    val_ref = val_df.copy()
    for species_idx, species in enumerate(SPECIES_ORDER):
        val_scores_raw = _score_species(
            val_x,
            species_idx,
            encoder_w,
            encoder_b,
            species_embeddings,
            species_bias,
            scale=1.0,
            bias=0.0,
        )
        y_bin = (
            (val_ref["target_species_idx"].to_numpy(dtype=np.int64) == species_idx)
            & (val_ref["is_positive"].to_numpy(dtype=np.int64) == 1)
        ).astype(np.int64)

        scale, bias = _fit_platt_scaling(
            np.log(np.clip(val_scores_raw, 1e-6, 1.0 - 1e-6) / np.clip(1.0 - val_scores_raw, 1e-6, 1.0)), y_bin
        )
        calibration_scale.append(scale)
        calibration_bias.append(bias)

        val_scores = _score_species(
            val_x,
            species_idx,
            encoder_w,
            encoder_b,
            species_embeddings,
            species_bias,
            scale=scale,
            bias=bias,
        )

        auc = _binary_auc(y_bin, val_scores)
        pr_auc = _average_precision(y_bin, val_scores)
        ece = _expected_calibration_error(y_bin, val_scores)
        topk_precision = _regional_topk_precision(val_ref, val_scores, species, k=10)

        per_species_metrics[species] = {
            "val_auc_vs_background": float(auc),
            "val_pr_auc_vs_background": float(pr_auc),
            "calibration_error_ece": float(ece),
            "top10_region_precision": float(topk_precision),
            "val_positive_rows": int(y_bin.sum()),
            "val_total_rows": int(len(y_bin)),
        }

    class_names = SPECIES_ORDER + [BACKGROUND_CLASS]
    artifact_path = output_dir / "model.npz"
    np.savez(
        artifact_path,
        model_family=np.array(["embedding_head_v1"], dtype=object),
        encoder_weights=encoder_w,
        encoder_bias=encoder_b,
        species_embeddings=species_embeddings,
        species_bias=species_bias,
        calibration_scale=np.array(calibration_scale, dtype=np.float64),
        calibration_bias=np.array(calibration_bias, dtype=np.float64),
        mean=mean,
        std=std,
        feature_columns=np.array(feature_columns, dtype=object),
        species_names=np.array(SPECIES_ORDER, dtype=object),
        class_names=np.array(class_names, dtype=object),
    )

    calibration_artifact = {
        "version": "v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "species": {
            species: {
                "scale": float(calibration_scale[idx]),
                "bias": float(calibration_bias[idx]),
            }
            for idx, species in enumerate(SPECIES_ORDER)
        },
    }

    calibration_path = output_dir / "calibration.json"
    calibration_path.write_text(json.dumps(calibration_artifact, indent=2), encoding="utf-8")

    smoke_x = val_x[0:1]
    smoke_scores = {
        species: float(
            _score_species(
                smoke_x,
                idx,
                encoder_w,
                encoder_b,
                species_embeddings,
                species_bias,
                scale=calibration_scale[idx],
                bias=calibration_bias[idx],
            )[0]
        )
        for idx, species in enumerate(SPECIES_ORDER)
    }

    metrics: dict[str, Any] = {
        "species_order": SPECIES_ORDER,
        "background_class": BACKGROUND_CLASS,
        "model_family": "shared_encoder_species_embedding_pu",
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "row_counts": {
            "positives_total": int(len(positives_model)),
            "background_total": int(len(background)),
            "pairwise_total": int(len(pairwise)),
            "train_total": int(len(train_df)),
            "val_total": int(len(val_df)),
        },
        "config": {
            "background_ratio": args.background_ratio,
            "hard_negative_ratio": args.hard_negative_ratio,
            "latent_dim": args.latent_dim,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "l2": args.l2,
            "focal_gamma": args.focal_gamma,
            "split_method": args.split_method,
            "geo_feature_mode": args.geo_feature_mode,
            "val_fraction": args.val_fraction,
            "seed": args.seed,
            "caps": caps,
        },
        "generalization_controls": {
            "spatial_block_cv": args.split_method == "spatial",
            "temporal_holdout": args.split_method == "temporal",
            "taxonomic_holdout": False,
        },
        "training_history": history,
        "per_species_metrics": per_species_metrics,
    }

    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    smoke_path = output_dir / "smoke_prediction.json"
    smoke_path.write_text(
        json.dumps(
            {
                "scores": smoke_scores,
                "top_species": max(smoke_scores.items(), key=lambda item: item[1])[0],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Saved artifact:", artifact_path)
    print("Saved calibration:", calibration_path)
    print("Saved metrics:", metrics_path)
    print("Saved smoke prediction:", smoke_path)
    print("Per-species validation metrics:")
    for species in SPECIES_ORDER:
        summary = per_species_metrics[species]
        print(
            f"- {species}: auc={summary['val_auc_vs_background']:.4f}, "
            f"pr_auc={summary['val_pr_auc_vs_background']:.4f}, "
            f"ece={summary['calibration_error_ece']:.4f}"
        )


if __name__ == "__main__":
    main()
