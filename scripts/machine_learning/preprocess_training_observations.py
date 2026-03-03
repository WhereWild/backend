"""Preprocess occurrence parquet files into training_observation parquet dataset.

Pipeline goals:
- read scattered parquet observation files from an input root (default: /data),
- build model-ready feature vectors (`env_features`, `habitat_features`, `weather_features`),
- preserve leakage-sensitive fields as metadata only,
- write a partitioned dataset by split/year_month/region_id.

This script uses file-level multithreading for faster NVMe throughput.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import uuid

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq


_NUMERIC_SPECIES_SUFFIX = re.compile(r"(-?\d+)$")

# Metadata columns that must not leak into model input vectors.
_METADATA_COLUMNS = {
    "sample_id",
    "observation_id",
    "species_key",
    "presence_label",
    "sample_weight",
    "cell_id",
    "region_id",
    "lat",
    "lon",
    "event_time_utc",
    "year_month",
    "split",
    "source",
    "feature_version",
}

# Candidate input column aliases commonly seen in biodiversity datasets.
_LAT_COLUMNS = ("lat", "latitude", "decimalLatitude", "decimal_latitude")
_LON_COLUMNS = ("lon", "longitude", "decimalLongitude", "decimal_longitude")
_TIME_COLUMNS = (
    "event_time_utc",
    "eventTimestamp",
    "eventDate",
    "event_date",
    "timestamp",
    "datetime",
    "date",
)
_SPECIES_COLUMNS = ("species_key", "taxon_key", "species_id", "taxonKey")
_OBSERVATION_COLUMNS = ("observation_id", "occurrence_id", "gbifID", "id")
_SOURCE_COLUMNS = ("source", "dataset", "publisher", "provider")

_EXCLUDED_FEATURE_COLUMNS = {
    *_LAT_COLUMNS,
    *_LON_COLUMNS,
    *_TIME_COLUMNS,
    *_SPECIES_COLUMNS,
    *_OBSERVATION_COLUMNS,
    *_SOURCE_COLUMNS,
}
_EXCLUDED_FEATURE_COLUMNS_LOWER = {name.lower() for name in _EXCLUDED_FEATURE_COLUMNS}


@dataclass(frozen=True)
class FeatureGroups:
    env: list[str]
    habitat: list[str]
    weather: list[str]


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for preprocessing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path("/data"),
        help="Root directory containing scattered occurrence parquet files.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/data/training_observation"),
        help="Partitioned output dataset root.",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=None,
        help=(
            "Temporary directory for transformed intermediate parquet shards. "
            "Defaults to a sibling of output-root."
        ),
    )
    parser.add_argument(
        "--glob",
        type=str,
        default="**/occurrence.parquet",
        help="Glob to discover input observation parquet files under input-root.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Optional cap for number of input files to process (0 = no cap).",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=max(2, (os.cpu_count() or 8) // 2),
        help="File-level worker threads.",
    )
    parser.add_argument(
        "--feature-version",
        type=str,
        default="v1",
        help="Feature version string written to output rows.",
    )
    parser.add_argument(
        "--cell-size-deg",
        type=float,
        default=0.25,
        help="Spatial bin size in degrees for derived cell_id.",
    )
    parser.add_argument(
        "--region-size-deg",
        type=float,
        default=10.0,
        help="Coarser spatial bin size in degrees for region_id.",
    )
    parser.add_argument(
        "--max-rows-per-file",
        type=int,
        default=250_000,
        help="Max rows per output parquet file in final partitioned dataset.",
    )
    parser.add_argument(
        "--fallback-time-policy",
        type=str,
        default="keep",
        choices=["keep", "drop"],
        help="How to handle rows with missing/unparseable event time that fall back to 1970-01.",
    )
    parser.add_argument(
        "--background-ratio",
        type=float,
        default=0.0,
        help="Optional unlabeled/background rows to generate per positive row (e.g., 1.0 = 1:1).",
    )
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Delete output and staging directories before writing.",
    )
    parser.add_argument(
        "--keep-staging",
        action="store_true",
        help="Keep staging parquet files after final dataset write.",
    )
    return parser.parse_args()


def _choose_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    """Return the first matching DataFrame column for a list of aliases."""
    lower_map = {column.lower(): column for column in df.columns}
    for candidate in candidates:
        selected = lower_map.get(candidate.lower())
        if selected is not None:
            return selected
    return None


def _to_int64_species(value: object) -> int:
    """Convert species identifiers to a stable int64 key."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 0

    if isinstance(value, (int, np.integer)):
        return int(value)

    text = str(value).strip()
    if not text:
        return 0

    match = _NUMERIC_SPECIES_SUFFIX.search(text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False) & ((1 << 63) - 1)


def _species_key_from_path(src_path: Path) -> int | None:
    """Infer a fallback species key from taxonomy-like source path segments."""
    for part in reversed(src_path.parts):
        match = _NUMERIC_SPECIES_SUFFIX.search(part)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def _parse_numeric_event_time(raw_time: pd.Series) -> pd.Series:
    """Parse numeric event timestamps using automatic epoch unit inference."""
    numeric = pd.to_numeric(raw_time, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.to_datetime(numeric, errors="coerce", utc=True)

    magnitude = float(valid.abs().quantile(0.5))
    if magnitude >= 1e18:
        unit = "ns"
    elif magnitude >= 1e15:
        unit = "us"
    elif magnitude >= 1e12:
        unit = "ms"
    else:
        unit = "s"
    return pd.to_datetime(numeric, errors="coerce", utc=True, unit=unit)


def _stable_split(cell_id: str, year_month: str) -> str:
    """Map a row deterministically to train/val/test based on space-time key."""
    token = f"{cell_id}|{year_month}".encode("utf-8")
    bucket = int.from_bytes(hashlib.blake2b(token, digest_size=2).digest(), byteorder="big") % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "val"
    return "test"


def _bin_id(lat: float, lon: float, size_deg: float, prefix: str) -> str:
    """Build a coarse spatial bin id from lat/lon and bin size."""
    lat_bin = int(np.floor(lat / size_deg))
    lon_bin = int(np.floor(lon / size_deg))
    return f"{prefix}_{lat_bin}_{lon_bin}"


def _vector_from_columns(frame: pd.DataFrame, columns: list[str]) -> pa.Array:
    """Create a fixed-size float32 vector from the provided columns."""
    if not columns:
        return pa.array([None] * len(frame), type=pa.list_(pa.float32()))

    values = (
        frame.reindex(columns=columns, fill_value=0.0)
        .apply(pd.to_numeric, errors="coerce")
        .astype(np.float32)
        .fillna(0.0)
        .to_numpy(copy=False)
    )
    flat = pa.array(values.reshape(-1), type=pa.float32())
    return pa.FixedSizeListArray.from_arrays(flat, list_size=len(columns))


def _classify_feature_name(column_name: str) -> str | None:
    """Classify numeric source column into env/habitat/weather feature groups."""
    name = column_name.lower()
    if name in _EXCLUDED_FEATURE_COLUMNS_LOWER:
        return None

    if name.startswith(("bio_", "climate_")) or name in {
        "elevation",
        "slope",
        "aspect",
        "aspect_deg",
    }:
        return "env"

    if name.startswith(("habitat_", "landcover_", "ndvi", "canopy_", "terrain_")) or name in {
        "landcover",
        "koppen_geiger",
    }:
        return "habitat"

    if name.startswith(
        (
            "weather_",
            "temp_",
            "temperature_",
            "precip_",
            "precipitation_",
            "wind_",
            "humidity_",
            "pressure_",
            "cloud_cover_",
            "snowfall_",
            "snow_depth_",
            "dew_point_",
            "vapor_pressure_",
            "soil_moisture_",
            "soil_temperature_",
        )
    ) or name == "weather_code_simple":
        return "weather"

    return None


def _is_numeric_arrow_type(data_type: pa.DataType) -> bool:
    """Return True if Arrow field type is numeric and usable as model feature."""
    return (
        pa.types.is_integer(data_type)
        or pa.types.is_floating(data_type)
        or pa.types.is_decimal(data_type)
    )


def _build_feature_template(files: list[Path]) -> FeatureGroups:
    """Build one global feature layout to keep vector sizes consistent."""
    env: set[str] = set()
    habitat: set[str] = set()
    weather: set[str] = set()

    for path in files:
        schema = pq.read_schema(path)
        for field in schema:
            if not _is_numeric_arrow_type(field.type):
                continue
            feature_group = _classify_feature_name(field.name)
            if feature_group == "env":
                env.add(field.name)
            elif feature_group == "habitat":
                habitat.add(field.name)
            elif feature_group == "weather":
                weather.add(field.name)

    return FeatureGroups(
        env=sorted(env),
        habitat=sorted(habitat),
        weather=sorted(weather),
    )


def _transform_frame(
    frame: pd.DataFrame,
    *,
    feature_version: str,
    cell_size_deg: float,
    region_size_deg: float,
    fallback_species_key: int | None,
    feature_template: FeatureGroups,
    fallback_time_policy: str,
) -> pa.Table:
    """Transform one raw occurrence frame into schema-aligned training rows."""
    lat_col = _choose_column(frame, _LAT_COLUMNS)
    lon_col = _choose_column(frame, _LON_COLUMNS)
    species_col = _choose_column(frame, _SPECIES_COLUMNS)

    if lat_col is None or lon_col is None:
        raise ValueError("Missing required source columns. Need lat/lon columns in each input file.")
    if species_col is None and fallback_species_key is None:
        raise ValueError("Missing species column and could not infer species key from source path.")

    time_col = _choose_column(frame, _TIME_COLUMNS)
    observation_col = _choose_column(frame, _OBSERVATION_COLUMNS)
    source_col = _choose_column(frame, _SOURCE_COLUMNS)

    lat = pd.to_numeric(frame[lat_col], errors="coerce")
    lon = pd.to_numeric(frame[lon_col], errors="coerce")
    valid_geo = lat.notna() & lon.notna()
    lat = lat.loc[valid_geo].astype(np.float64)
    lon = lon.loc[valid_geo].astype(np.float64)

    filtered = frame.loc[valid_geo].copy()
    if filtered.empty:
        raise ValueError("No valid rows with numeric lat/lon after filtering.")

    if species_col is not None:
        species_key = filtered[species_col].map(_to_int64_species).astype(np.int64)
    else:
        if fallback_species_key is None:
            raise ValueError("Missing species column and could not infer species key from source path.")
        species_key = pd.Series([fallback_species_key] * len(filtered), index=filtered.index, dtype=np.int64)

    if time_col is not None:
        raw_time = filtered[time_col]
        if pd.api.types.is_numeric_dtype(raw_time):
            event_time = _parse_numeric_event_time(raw_time)
        else:
            event_time = pd.to_datetime(raw_time, errors="coerce", utc=True)
    else:
        event_time = pd.Series(pd.Timestamp("1970-01-01", tz="UTC"), index=filtered.index)

    fallback_time_mask = event_time.isna()
    if fallback_time_policy == "drop" and bool(fallback_time_mask.any()):
        keep_mask = ~fallback_time_mask
        filtered = filtered.loc[keep_mask].copy()
        lat = lat.loc[keep_mask]
        lon = lon.loc[keep_mask]
        species_key = species_key.loc[keep_mask]
        event_time = event_time.loc[keep_mask]

    if filtered.empty:
        raise ValueError("No valid rows remain after fallback-time filtering.")

    event_time = event_time.fillna(pd.Timestamp("1970-01-01", tz="UTC"))

    year_month = event_time.dt.strftime("%Y-%m")

    cell_ids = [
        _bin_id(float(la), float(lo), size_deg=cell_size_deg, prefix="cell")
        for la, lo in zip(lat.to_numpy(), lon.to_numpy(), strict=False)
    ]
    region_ids = [
        _bin_id(float(la), float(lo), size_deg=region_size_deg, prefix="region")
        for la, lo in zip(lat.to_numpy(), lon.to_numpy(), strict=False)
    ]
    splits = [_stable_split(cell_id, ym) for cell_id, ym in zip(cell_ids, year_month, strict=False)]

    if observation_col is not None:
        raw_observation = filtered[observation_col]
        observation_id = pd.Series(
            [str(value) if pd.notna(value) else None for value in raw_observation],
            index=filtered.index,
            dtype="object",
        )
    else:
        observation_id = pd.Series([None] * len(filtered), index=filtered.index, dtype="object")

    if source_col is not None:
        source = filtered[source_col].astype(str).where(filtered[source_col].notna(), "unknown")
    else:
        source = pd.Series(["unknown"] * len(filtered), index=filtered.index)

    sample_id = pd.Series(
        [str(uuid.uuid4()) for _ in range(len(filtered))],
        index=filtered.index,
        dtype="object",
    )

    table = pa.Table.from_arrays(
        [
            pa.array(sample_id.tolist(), type=pa.string()),
            pa.array(observation_id.tolist(), type=pa.string()),
            pa.array(species_key.tolist(), type=pa.int64()),
            pa.array([1] * len(filtered), type=pa.int8()),
            pa.array([1.0] * len(filtered), type=pa.float32()),
            pa.array(cell_ids, type=pa.string()),
            pa.array(region_ids, type=pa.string()),
            pa.array(lat.to_numpy(), type=pa.float64()),
            pa.array(lon.to_numpy(), type=pa.float64()),
            pa.Array.from_pandas(event_time, type=pa.timestamp("ms", tz="UTC")),
            pa.array(year_month.tolist(), type=pa.string()),
            pa.array(splits, type=pa.string()),
            pa.array(source.tolist(), type=pa.string()),
            pa.array([feature_version] * len(filtered), type=pa.string()),
            _vector_from_columns(filtered, feature_template.env),
            _vector_from_columns(filtered, feature_template.habitat),
            _vector_from_columns(filtered, feature_template.weather),
        ],
        names=[
            "sample_id",
            "observation_id",
            "species_key",
            "presence_label",
            "sample_weight",
            "cell_id",
            "region_id",
            "lat",
            "lon",
            "event_time_utc",
            "year_month",
            "split",
            "source",
            "feature_version",
            "env_features",
            "habitat_features",
            "weather_features",
        ],
    )
    return table


def _transform_file(
    src_path: Path,
    staging_dir: Path,
    *,
    feature_version: str,
    cell_size_deg: float,
    region_size_deg: float,
    feature_template: FeatureGroups,
    fallback_time_policy: str,
    background_ratio: float,
) -> tuple[Path, int]:
    """Transform one source parquet file into one staged training parquet shard."""
    table = pq.read_table(src_path, use_threads=True)
    frame = table.to_pandas(types_mapper=None)
    fallback_species_key = _species_key_from_path(src_path)
    transformed = _transform_frame(
        frame,
        feature_version=feature_version,
        cell_size_deg=cell_size_deg,
        region_size_deg=region_size_deg,
        fallback_species_key=fallback_species_key,
        feature_template=feature_template,
        fallback_time_policy=fallback_time_policy,
    )

    if background_ratio > 0:
        transformed = _append_background_rows(transformed, background_ratio, src_path)

    staging_dir.mkdir(parents=True, exist_ok=True)
    out_path = staging_dir / f"{src_path.stem}_{hashlib.blake2b(str(src_path).encode('utf-8'), digest_size=6).hexdigest()}.parquet"
    pq.write_table(transformed, out_path, compression="zstd")
    return out_path, transformed.num_rows


def _discover_files(input_root: Path, glob_pattern: str, max_files: int) -> list[Path]:
    """Discover input parquet files under root using glob and optional file cap."""
    files = [path for path in input_root.glob(glob_pattern) if path.is_file()]
    files = [path for path in files if path.suffix.lower() == ".parquet"]
    files.sort()
    if max_files > 0:
        return files[:max_files]
    return files


def _append_background_rows(table: pa.Table, ratio: float, src_path: Path) -> pa.Table:
    """Append unlabeled/background rows by deterministic resampling for PU setups."""
    if ratio <= 0 or table.num_rows == 0:
        return table

    background_count = int(round(table.num_rows * ratio))
    if background_count <= 0:
        return table

    seed = int.from_bytes(hashlib.blake2b(str(src_path).encode("utf-8"), digest_size=8).digest(), byteorder="big")
    rng = np.random.default_rng(seed)
    # Use replacement only when requested background rows exceed available source rows.
    take_idx = rng.choice(table.num_rows, size=background_count, replace=background_count > table.num_rows)
    background = table.take(pa.array(take_idx, type=pa.int64()))

    sample_ids = pa.array([str(uuid.uuid4()) for _ in range(background_count)], type=pa.string())
    observation_ids = pa.array([None] * background_count, type=pa.string())
    labels = pa.array([0] * background_count, type=pa.int8())
    weights = pa.array([1.0] * background_count, type=pa.float32())
    sources = pa.array(["generated_background"] * background_count, type=pa.string())

    background = background.set_column(background.schema.get_field_index("sample_id"), "sample_id", sample_ids)
    background = background.set_column(
        background.schema.get_field_index("observation_id"),
        "observation_id",
        observation_ids,
    )
    background = background.set_column(
        background.schema.get_field_index("presence_label"),
        "presence_label",
        labels,
    )
    background = background.set_column(
        background.schema.get_field_index("sample_weight"),
        "sample_weight",
        weights,
    )
    background = background.set_column(
        background.schema.get_field_index("source"),
        "source",
        sources,
    )

    return pa.concat_tables([table, background], promote_options="none")


def _clear_dir(path: Path) -> None:
    """Delete a directory tree if present."""
    if path.exists():
        shutil.rmtree(path)


def _print_failure_summary(failures: list[tuple[Path, str]], *, limit: int = 20) -> None:
    """Print a bounded summary of file-level failures."""
    if not failures:
        return
    print("Some files failed:")
    for src, err in failures[:limit]:
        print(f"  - {src}: {err}")
    if len(failures) > limit:
        print(f"  ... and {len(failures) - limit} more")


def main() -> int:
    """CLI entrypoint for generating training observations dataset."""
    args = _parse_args()
    input_root = args.input_root.resolve()
    output_root = args.output_root.resolve()
    if args.staging_dir is not None:
        staging_dir = args.staging_dir.resolve()
    else:
        staging_dir = output_root.parent / f".{output_root.name}_staging"

    if args.overwrite_output:
        _clear_dir(output_root)
        _clear_dir(staging_dir)

    if not input_root.exists():
        raise SystemExit(f"Input root does not exist: {input_root}")

    files = _discover_files(input_root, args.glob, args.max_files)
    if not files:
        raise SystemExit(f"No parquet files found in {input_root} with glob '{args.glob}'.")

    print(f"Discovered {len(files):,} parquet files.")
    print(f"Using {args.threads} worker threads.")
    print(f"Staging dir: {staging_dir}")
    print(f"Output dir: {output_root}")
    print(f"Fallback time policy: {args.fallback_time_policy}")
    print(f"Background ratio: {args.background_ratio:.3f}")

    feature_template = _build_feature_template(files)
    print(
        "Feature template sizes | "
        f"env={len(feature_template.env):,}, "
        f"habitat={len(feature_template.habitat):,}, "
        f"weather={len(feature_template.weather):,}"
    )

    staging_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    staged_paths: list[Path] = []
    failures: list[tuple[Path, str]] = []

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {
            pool.submit(
                _transform_file,
                path,
                staging_dir,
                feature_version=args.feature_version,
                cell_size_deg=args.cell_size_deg,
                region_size_deg=args.region_size_deg,
                feature_template=feature_template,
                fallback_time_policy=args.fallback_time_policy,
                background_ratio=args.background_ratio,
            ): path
            for path in files
        }

        for idx, future in enumerate(as_completed(futures), start=1):
            src = futures[future]
            try:
                out_path, rows = future.result()
                staged_paths.append(out_path)
                written += rows
            except (OSError, IOError, ValueError, RuntimeError) as exc:  # pragma: no cover - defensive error reporting path
                failures.append((src, str(exc)))

            if idx % 50 == 0 or idx == len(futures):
                print(
                    f"Processed {idx:,}/{len(futures):,} files | "
                    f"rows written: {written:,} | failures: {len(failures):,}"
                )

    if not staged_paths:
        if failures:
            print("No transformed shards were produced. Sample failure reasons:")
            for src, err in failures[:20]:
                print(f"  - {src}: {err}")
            if len(failures) > 20:
                print(f"  ... and {len(failures) - 20} more")
        raise SystemExit("No transformed shards were produced; aborting final write.")

    staged_dataset = ds.dataset(staging_dir, format="parquet")
    output_root.mkdir(parents=True, exist_ok=True)

    ds.write_dataset(
        data=staged_dataset,
        base_dir=output_root,
        format="parquet",
        partitioning=ds.partitioning(
            pa.schema(
                [
                    pa.field("split", pa.string()),
                    pa.field("year_month", pa.string()),
                    pa.field("region_id", pa.string()),
                ]
            ),
            flavor="hive",
        ),
        max_rows_per_file=args.max_rows_per_file,
        max_rows_per_group=args.max_rows_per_file,
        max_partitions=8192,
        existing_data_behavior="overwrite_or_ignore",
    )

    print(f"Final dataset written to {output_root}")
    print(f"Total rows: {written:,}")

    if failures:
        _print_failure_summary(failures)

    if not args.keep_staging:
        _clear_dir(staging_dir)

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
