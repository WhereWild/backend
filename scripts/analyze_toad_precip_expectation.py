import math
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


SPEA_PARQUET_PATH = Path(
    "/workspace/data/species/taxonomy/Animalia_1/Chordata_44/"
    "Amphibia_131/Anura_952/Scaphiopodidae_3098/Spea_2429782/"
    "Spea_intermontana_2429791/occurrence.parquet"
)
PEDIOCACTUS_PARQUET_PATH = Path(
    "/workspace/data/species/taxonomy/Plantae_6/Tracheophyta_7707728/"
    "Magnoliopsida_220/Caryophyllales_422/Cactaceae_2519/"
    "Pediocactus_3084062/Pediocactus_simpsonii_3084072/occurrence.parquet"
)

PRECIP_WINDOWS = (1, 8, 24, 72)
ANNUAL_PRECIP_COL = "bio_12"  # annual precipitation (mm)


def _expected_precip(annual_mm: np.ndarray, hours: int) -> np.ndarray:
    # Expected precipitation for a window based on annual total (uniform rate).
    return (annual_mm / 365.0) * (hours / 24.0)


def _analyze_path(parquet_path: Path) -> None:
    if not parquet_path.exists():
        raise SystemExit(f"Parquet not found: {parquet_path}")

    needed_cols = [ANNUAL_PRECIP_COL] + [f"precipitation_sum_{h}h" for h in PRECIP_WINDOWS]
    schema_cols = pq.read_schema(parquet_path).names
    missing = [c for c in needed_cols if c not in schema_cols]
    if missing:
        raise SystemExit(f"Parquet missing columns in {parquet_path}: {missing}")

    table = pq.read_table(parquet_path, columns=needed_cols).combine_chunks()
    data = table.to_pydict()
    annual = np.array(data[ANNUAL_PRECIP_COL], dtype=float)

    print(f"path={parquet_path}")
    print(f"rows={table.num_rows}")
    for hours in PRECIP_WINDOWS:
        col = f"precipitation_sum_{hours}h"
        observed = np.array(data[col], dtype=float)

        mask = np.isfinite(annual) & np.isfinite(observed)
        if not mask.any():
            print(f"[{hours}h] no valid rows")
            continue

        annual_valid = annual[mask]
        obs_valid = observed[mask]
        exp_valid = _expected_precip(annual_valid, hours)
        diff = obs_valid - exp_valid

        mean_obs = float(np.mean(obs_valid))
        mean_exp = float(np.mean(exp_valid))
        mean_diff = float(np.mean(diff))
        median_diff = float(np.median(diff))
        pct_over = float(np.mean(diff > 0.0) * 100.0)

        ratio = np.where(exp_valid > 0, obs_valid / exp_valid, np.nan)
        mean_ratio = float(np.nanmean(ratio))

        print(
            f"[{hours}h] n={mask.sum()} mean_obs={mean_obs:.4f} "
            f"mean_exp={mean_exp:.4f} mean_diff={mean_diff:.4f} "
            f"median_diff={median_diff:.4f} pct_over={pct_over:.1f}% "
            f"mean_ratio={mean_ratio:.3f}"
        )


def main() -> None:
    _analyze_path(SPEA_PARQUET_PATH)
    _analyze_path(PEDIOCACTUS_PARQUET_PATH)


if __name__ == "__main__":
    main()
