from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from util import inference, reinforcement


LOGGER = logging.getLogger(__name__)
DEFAULT_RESOLUTION_HINT = 0.25
DEFAULT_MAX_POSITIVE_CORRECTIONS = 30
DEFAULT_ACTIVATION_THRESHOLD = 1
EPSILON = 1e-12


@dataclass(frozen=True)
class EvalPools:
    feedback_positives: pd.DataFrame
    feedback_background: pd.DataFrame
    held_out: pd.DataFrame


@dataclass(frozen=True)
class FeedbackEvent:
    lat: float
    lon: float
    present: bool


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True, help="Path to exported inference bundle.")
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to the canonical training-observation parquet dataset root.",
    )
    parser.add_argument(
        "--species",
        type=int,
        nargs="+",
        required=True,
        help="Species keys to evaluate. Expected count: 5 to 10.",
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("MIN_LAT", "MIN_LON", "MAX_LAT", "MAX_LON"),
        required=True,
        help="Bounding box used to filter feedback/test observations.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for per-species CSV outputs and summary CSV.",
    )
    parser.add_argument(
        "--n-min-grid",
        type=int,
        nargs="+",
        required=True,
        help="Thresholds for gated-series reporting.",
    )
    parser.add_argument(
        "--resolution-hint",
        type=float,
        default=DEFAULT_RESOLUTION_HINT,
        help="Resolution hint passed to score_species_coords. Defaults to 0.25 degrees.",
    )
    parser.add_argument(
        "--max-positive-corrections",
        type=int,
        default=DEFAULT_MAX_POSITIVE_CORRECTIONS,
        help="Maximum number of positive train observations to use as feedback.",
    )
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if not 5 <= len(args.species) <= 10:
        raise ValueError("--species must contain between 5 and 10 species keys.")
    if len(set(args.species)) != len(args.species):
        raise ValueError("--species must not contain duplicates.")
    min_lat, min_lon, max_lat, max_lon = args.bbox
    if min_lat >= max_lat or min_lon >= max_lon:
        raise ValueError("--bbox must satisfy MIN_LAT < MAX_LAT and MIN_LON < MAX_LON.")
    if args.max_positive_corrections < 1:
        raise ValueError("--max-positive-corrections must be >= 1.")
    if any(value < 1 for value in args.n_min_grid):
        raise ValueError("--n-min-grid values must be >= 1.")


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _dataset_table(dataset_root: Path, species_key: int, bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    min_lat, min_lon, max_lat, max_lon = bbox
    dataset = ds.dataset(str(dataset_root), format="parquet", partitioning="hive")
    filter_expr = (
        (pc.field("species_key") == species_key)
        & pc.is_in(pc.field("split"), value_set=pa.array(["train", "test"]))
        & (pc.field("lat") >= min_lat)
        & (pc.field("lat") <= max_lat)
        & (pc.field("lon") >= min_lon)
        & (pc.field("lon") <= max_lon)
    )
    table = dataset.to_table(
        filter=filter_expr,
        columns=["species_key", "split", "lat", "lon", "presence_label", "source", "event_time_utc"],
    )
    df = table.to_pandas(types_mapper=None)
    if df.empty:
        return df
    df["event_time_utc"] = pd.to_datetime(df["event_time_utc"], utc=True)
    return df


def _build_eval_pools(dataset_root: Path, species_key: int, bbox: tuple[float, float, float, float], max_positive_corrections: int) -> EvalPools:
    df = _dataset_table(dataset_root, species_key, bbox)
    if df.empty:
        raise ValueError("No rows matched species/bbox across train/test splits.")

    feedback_positives = (
        df[
            (df["split"] == "train")
            & (df["presence_label"] == 1)
        ]
        .sort_values("event_time_utc", kind="stable")
        .head(max_positive_corrections)
        .reset_index(drop=True)
    )
    feedback_background = (
        df[
            (df["split"] == "train")
            & (df["presence_label"] == 0)
            & (df["source"] == "generated_background")
        ]
        .sort_values("event_time_utc", kind="stable")
        .reset_index(drop=True)
    )
    held_out = (
        df[
            (df["split"] == "test")
            & (
                (df["presence_label"] == 1)
                | ((df["presence_label"] == 0) & (df["source"] == "generated_background"))
            )
        ]
        .sort_values("event_time_utc", kind="stable")
        .reset_index(drop=True)
    )

    if feedback_positives.empty:
        raise ValueError("No positive train observations available for feedback.")
    if feedback_background.empty:
        raise ValueError("No generated_background train rows available for synthetic absence feedback.")
    if held_out.empty:
        raise ValueError("No held-out test rows available after filtering.")
    if held_out["presence_label"].nunique() < 2:
        raise ValueError("Held-out pool does not contain both positive and background classes.")

    return EvalPools(
        feedback_positives=feedback_positives,
        feedback_background=feedback_background,
        held_out=held_out,
    )


def _stable_species_seed(species_key: int) -> int:
    return (species_key * 1_103_515_245 + 12_345) % (2**32)


def _synthesize_feedback_sequence(pools: EvalPools, species_key: int) -> list[FeedbackEvent]:
    """Build a deterministic alternating feedback stream.

    Positives are ordered chronologically, capped upstream, and each is followed
    by one sampled train background row when available. Background rows are
    sampled without replacement using a species-key-derived RNG seed, then
    sorted by event_time_utc before interleaving.
    """
    positive_count = len(pools.feedback_positives)
    background_count = min(positive_count, len(pools.feedback_background))
    rng = np.random.default_rng(_stable_species_seed(species_key))
    background_indices = np.sort(rng.choice(len(pools.feedback_background), size=background_count, replace=False))
    sampled_background = (
        pools.feedback_background.iloc[background_indices]
        .sort_values("event_time_utc", kind="stable")
        .reset_index(drop=True)
    )

    feedback: list[FeedbackEvent] = []
    for idx, positive_row in enumerate(pools.feedback_positives.itertuples(index=False)):
        feedback.append(FeedbackEvent(lat=float(positive_row.lat), lon=float(positive_row.lon), present=True))
        if idx < len(sampled_background):
            background_row = sampled_background.iloc[idx]
            feedback.append(
                FeedbackEvent(
                    lat=float(background_row["lat"]),
                    lon=float(background_row["lon"]),
                    present=False,
                )
            )
    return feedback


def _binary_cross_entropy(labels: np.ndarray, scores: np.ndarray) -> float:
    clipped = np.clip(scores, EPSILON, 1.0 - EPSILON)
    losses = -(labels * np.log(clipped) + (1.0 - labels) * np.log(1.0 - clipped))
    return float(np.mean(losses))


def _roc_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    positives = labels == 1.0
    negatives = labels == 0.0
    pos_count = int(np.sum(positives))
    neg_count = int(np.sum(negatives))
    if pos_count == 0 or neg_count == 0:
        return float("nan")

    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    sorted_labels = labels[order]
    ranks = np.empty(len(scores), dtype=np.float64)

    start = 0
    while start < len(sorted_scores):
        end = start + 1
        while end < len(sorted_scores) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        average_rank = (start + end - 1) / 2.0 + 1.0
        ranks[start:end] = average_rank
        start = end

    pos_rank_sum = float(np.sum(ranks[sorted_labels == 1.0]))
    auc = (pos_rank_sum - (pos_count * (pos_count + 1) / 2.0)) / (pos_count * neg_count)
    return float(auc)


def _score_rows(
    species_key: int,
    rows: pd.DataFrame,
    *,
    resolution_hint: float,
    head_variant: str,
    client_key: str | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    coords = [(float(row.lat), float(row.lon)) for row in rows.itertuples(index=False)]
    raw_scores, _ = inference.score_species_coords(
        species_key,
        coords,
        resolution_hint=resolution_hint,
        head_variant=head_variant,
        client_key=client_key,
        feature_mode="prefer_cell_table",
    )
    valid_mask = np.array([score is not None for score in raw_scores], dtype=bool)
    scores = np.array([float(score) for score in raw_scores if score is not None], dtype=np.float64)
    labels = rows.loc[valid_mask, "presence_label"].to_numpy(dtype=np.float64, copy=True)
    return labels, scores, valid_mask


def _metrics_for_scores(labels: np.ndarray, scores: np.ndarray) -> tuple[float, float]:
    if labels.size == 0:
        raise ValueError("No held-out rows remained after inference filtering.")
    if np.unique(labels).size < 2:
        raise ValueError("Held-out rows do not contain both classes after inference filtering.")
    return _binary_cross_entropy(labels, scores), _roc_auc(labels, scores)


def _write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    df = pd.DataFrame(list(rows))
    df.to_csv(path, index=False)


def _evaluate_species(
    *,
    dataset_root: Path,
    species_key: int,
    bbox: tuple[float, float, float, float],
    output_dir: Path,
    n_min_grid: list[int],
    resolution_hint: float,
    max_positive_corrections: int,
) -> list[dict[str, object]]:
    pools = _build_eval_pools(dataset_root, species_key, bbox, max_positive_corrections)
    feedback = _synthesize_feedback_sequence(pools, species_key)
    client_key = f"eval-{species_key}"

    LOGGER.info(
        "species=%s feedback_pos=%s feedback_bg=%s held_out=%s total_feedback=%s",
        species_key,
        len(pools.feedback_positives),
        min(len(pools.feedback_positives), len(pools.feedback_background)),
        len(pools.held_out),
        len(feedback),
    )

    reinforcement.clear_reinforced_head(species_key, client_key)
    try:
        baseline_labels, baseline_scores, baseline_mask = _score_rows(
            species_key,
            pools.held_out,
            resolution_hint=resolution_hint,
            head_variant="original",
            client_key=None,
        )
        bce_baseline, auc_baseline = _metrics_for_scores(baseline_labels, baseline_scores)

        held_out_kept = pools.held_out.loc[baseline_mask, ["lat", "lon", "presence_label"]].reset_index(drop=True)

        per_k_rows: list[dict[str, object]] = []
        raw_score_rows: list[dict[str, object]] = []
        reinforced_series: list[tuple[int, float, float]] = []

        for kept_index, kept_row in held_out_kept.iterrows():
            raw_score_rows.append(
                {
                    "species_key": species_key,
                    "k": 0,
                    "row_index": int(kept_index),
                    "lat": float(kept_row["lat"]),
                    "lon": float(kept_row["lon"]),
                    "presence_label": int(kept_row["presence_label"]),
                    "head_variant": "original",
                    "score": float(baseline_scores[kept_index]),
                }
            )

        for index, event in enumerate(feedback, start=1):
            reinforcement.reinforce_head(
                client_key,
                species_key,
                event.lat,
                event.lon,
                event.present,
                activation_threshold=DEFAULT_ACTIVATION_THRESHOLD,
            )
            reinforced_labels, reinforced_scores, reinforced_mask = _score_rows(
                species_key,
                pools.held_out,
                resolution_hint=resolution_hint,
                head_variant="reinforced",
                client_key=client_key,
            )
            if not np.array_equal(baseline_mask, reinforced_mask):
                raise ValueError("Held-out kept-mask changed between baseline and reinforced scoring.")
            if baseline_labels.shape != reinforced_labels.shape or not np.array_equal(baseline_labels, reinforced_labels):
                raise ValueError("Held-out label set changed between baseline and reinforced scoring.")
            bce_reinforced, auc_reinforced = _metrics_for_scores(reinforced_labels, reinforced_scores)
            reinforced_series.append((index, bce_reinforced, auc_reinforced))
            per_k_rows.append(
                {
                    "species_key": species_key,
                    "k": index,
                    "bce_reinforced": bce_reinforced,
                    "auc_reinforced": auc_reinforced,
                    "bce_baseline": bce_baseline,
                    "auc_baseline": auc_baseline,
                }
            )
            for kept_index, kept_row in held_out_kept.iterrows():
                raw_score_rows.append(
                    {
                        "species_key": species_key,
                        "k": index,
                        "row_index": int(kept_index),
                        "lat": float(kept_row["lat"]),
                        "lon": float(kept_row["lon"]),
                        "presence_label": int(kept_row["presence_label"]),
                        "head_variant": "reinforced",
                        "score": float(reinforced_scores[kept_index]),
                    }
                )
            LOGGER.info(
                "species=%s k=%s/%s present=%s bce=%.6f auc=%.6f",
                species_key,
                index,
                len(feedback),
                event.present,
                bce_reinforced,
                auc_reinforced,
            )

        per_species_dir = output_dir / "per_species"
        per_species_dir.mkdir(parents=True, exist_ok=True)
        _write_csv(per_species_dir / f"species_{species_key}.csv", per_k_rows)
        _write_csv(per_species_dir / f"species_{species_key}_raw_scores.csv", raw_score_rows)

        final_bce_reinforced = reinforced_series[-1][1]
        final_auc_reinforced = reinforced_series[-1][2]
        summary_rows: list[dict[str, object]] = []
        for n_min in sorted(set(n_min_grid)):
            gated_bce = final_bce_reinforced if len(feedback) >= n_min else bce_baseline
            gated_auc = final_auc_reinforced if len(feedback) >= n_min else auc_baseline
            summary_rows.append(
                {
                    "species_key": species_key,
                    "feedback_count": len(feedback),
                    "n_min": n_min,
                    "bce_gated": gated_bce,
                    "auc_gated": gated_auc,
                    "bce_baseline": bce_baseline,
                    "auc_baseline": auc_baseline,
                    "bce_reinforced_final": final_bce_reinforced,
                    "auc_reinforced_final": final_auc_reinforced,
                }
            )
        return summary_rows
    finally:
        reinforcement.clear_reinforced_head(species_key, client_key)


def main() -> int:
    args = _parse_args()
    _configure_logging()
    _validate_args(args)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    inference.load_bundle(args.bundle)

    bbox = tuple(float(value) for value in args.bbox)
    summary_rows: list[dict[str, object]] = []
    failed_species: list[int] = []
    for species_key in args.species:
        try:
            summary_rows.extend(
                _evaluate_species(
                    dataset_root=args.dataset,
                    species_key=species_key,
                    bbox=bbox,
                    output_dir=args.output_dir,
                    n_min_grid=args.n_min_grid,
                    resolution_hint=float(args.resolution_hint),
                    max_positive_corrections=int(args.max_positive_corrections),
                )
            )
        except Exception as exc:
            LOGGER.warning("species=%s skipped: %s", species_key, exc)
            failed_species.append(species_key)
            for n_min in sorted(set(args.n_min_grid)):
                summary_rows.append(
                    {
                        "species_key": species_key,
                        "feedback_count": 0,
                        "n_min": n_min,
                        "bce_gated": float("nan"),
                        "auc_gated": float("nan"),
                        "bce_baseline": float("nan"),
                        "auc_baseline": float("nan"),
                        "bce_reinforced_final": float("nan"),
                        "auc_reinforced_final": float("nan"),
                    }
                )

    _write_csv(args.output_dir / "summary.csv", summary_rows)
    LOGGER.info(
        "wrote summary=%s species=%s skipped=%s",
        args.output_dir / "summary.csv",
        len(args.species),
        failed_species,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())