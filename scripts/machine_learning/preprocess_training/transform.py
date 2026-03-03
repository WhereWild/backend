"""Feature construction and per-file transformation utilities."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import time
from typing import Literal
import uuid

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

_NUMERIC_SPECIES_SUFFIX = re.compile(r"(-?\d+)$")

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


@dataclass(frozen=True)
class TransformResult:
    out_path: Path
    rows: int
    duration_seconds: float
    read_seconds: float


def choose_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    """Return the first matching DataFrame column for a list of aliases."""
    lower_map = {column.lower(): column for column in df.columns}
    for candidate in candidates:
        selected = lower_map.get(candidate.lower())
        if selected is not None:
            return selected
    return None


def to_int64_species(value: object) -> int:
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


def species_key_from_path(src_path: Path) -> int | None:
    """Infer a fallback species key from taxonomy-like source path segments."""
    for part in reversed(src_path.parts):
        match = _NUMERIC_SPECIES_SUFFIX.search(part)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def parse_numeric_event_time(raw_time: pd.Series) -> pd.Series:
    """Parse numeric event timestamps using automatic epoch unit inference."""
    numeric = pd.to_numeric(raw_time, errors="coerce")
    numeric = numeric.where(np.isfinite(numeric), np.nan)
    valid = numeric.dropna()
    if valid.empty:
        return pd.to_datetime(numeric, errors="coerce", utc=True)

    magnitude = float(valid.abs().quantile(0.5))
    if magnitude >= 1e18:
        unit: Literal["s", "ms", "us", "ns"] = "ns"
    elif magnitude >= 1e15:
        unit = "us"
    elif magnitude >= 1e12:
        unit = "ms"
    else:
        unit = "s"

    candidate_units: list[Literal["s", "ms", "us", "ns"]] = [unit, "s", "ms", "us", "ns"]
    tried: set[Literal["s", "ms", "us", "ns"]] = set()
    best_parsed: pd.Series | None = None
    best_valid_count = -1

    for candidate_unit in candidate_units:
        if candidate_unit in tried:
            continue
        tried.add(candidate_unit)
        try:
            parsed = pd.to_datetime(numeric, errors="coerce", utc=True, unit=candidate_unit)
        except (FloatingPointError, OverflowError, ValueError, TypeError):
            continue

        valid_count = int(parsed.notna().sum())
        if valid_count > best_valid_count:
            best_parsed = parsed
            best_valid_count = valid_count
            if valid_count == len(valid):
                break

    if best_parsed is not None:
        return best_parsed

    return pd.to_datetime(raw_time, errors="coerce", utc=True)


def stable_split(cell_id: str, year_month: str) -> str:
    """Map a row deterministically to train/val/test based on space-time key."""
    token = f"{cell_id}|{year_month}".encode("utf-8")
    bucket = int.from_bytes(hashlib.blake2b(token, digest_size=2).digest(), byteorder="big") % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "val"
    return "test"


def bin_id(lat: float, lon: float, size_deg: float, prefix: str) -> str:
    """Build a coarse spatial bin id from lat/lon and bin size."""
    lat_bin = int(np.floor(lat / size_deg))
    lon_bin = int(np.floor(lon / size_deg))
    return f"{prefix}_{lat_bin}_{lon_bin}"


def vector_from_columns(frame: pd.DataFrame, columns: list[str]) -> pa.Array:
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


def classify_feature_name(column_name: str) -> str | None:
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

    if (
        name.startswith((
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
        ))
        or name == "weather_code_simple"
    ):
        return "weather"

    return None


def is_numeric_arrow_type(data_type: pa.DataType) -> bool:
    """Return True if Arrow field type is numeric and usable as model feature."""
    return pa.types.is_integer(data_type) or pa.types.is_floating(data_type) or pa.types.is_decimal(data_type)


def build_feature_template(
    files: list[Path],
    *,
    schema_log_interval_files: int,
    log_slow_read_seconds: float,
    template_scan_max_files: int,
) -> FeatureGroups:
    """Build one global feature layout to keep vector sizes consistent."""
    env: set[str] = set()
    habitat: set[str] = set()
    weather: set[str] = set()

    scan_files = files
    if template_scan_max_files > 0:
        scan_files = files[:template_scan_max_files]
        print(f"Schema scan selection | using {len(scan_files):,}/{len(files):,} files for feature template")

    scan_start = time.perf_counter()
    for index, path in enumerate(scan_files, start=1):
        schema_start = time.perf_counter()
        schema = pq.read_schema(path)
        schema_seconds = time.perf_counter() - schema_start

        if schema_seconds >= log_slow_read_seconds:
            print(f"Slow schema read ({schema_seconds:.1f}s) | {path}")

        for field in schema:
            if not is_numeric_arrow_type(field.type):
                continue
            feature_group = classify_feature_name(field.name)
            if feature_group == "env":
                env.add(field.name)
            elif feature_group == "habitat":
                habitat.add(field.name)
            elif feature_group == "weather":
                weather.add(field.name)

        if schema_log_interval_files > 0 and index % schema_log_interval_files == 0:
            elapsed = time.perf_counter() - scan_start
            print(f"Schema scan progress | files: {index:,}/{len(scan_files):,} | elapsed: {elapsed:.1f}s")

    return FeatureGroups(
        env=sorted(env),
        habitat=sorted(habitat),
        weather=sorted(weather),
    )


def transform_frame(
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
    lat_col = choose_column(frame, _LAT_COLUMNS)
    lon_col = choose_column(frame, _LON_COLUMNS)
    species_col = choose_column(frame, _SPECIES_COLUMNS)

    if lat_col is None or lon_col is None:
        raise ValueError("Missing required source columns. Need lat/lon columns in each input file.")
    if species_col is None and fallback_species_key is None:
        raise ValueError("Missing species column and could not infer species key from source path.")

    time_col = choose_column(frame, _TIME_COLUMNS)
    observation_col = choose_column(frame, _OBSERVATION_COLUMNS)
    source_col = choose_column(frame, _SOURCE_COLUMNS)

    lat = pd.to_numeric(frame[lat_col], errors="coerce")
    lon = pd.to_numeric(frame[lon_col], errors="coerce")
    valid_geo = lat.notna() & lon.notna()
    lat = lat.loc[valid_geo].astype(np.float64)
    lon = lon.loc[valid_geo].astype(np.float64)

    filtered = frame.loc[valid_geo].copy()
    if filtered.empty:
        raise ValueError("No valid rows with numeric lat/lon after filtering.")

    if species_col is not None:
        species_key = filtered[species_col].map(to_int64_species).astype(np.int64)
    else:
        if fallback_species_key is None:
            raise ValueError("Missing species column and could not infer species key from source path.")
        species_key = pd.Series([fallback_species_key] * len(filtered), index=filtered.index, dtype=np.int64)

    if time_col is not None:
        raw_time = filtered[time_col]
        if pd.api.types.is_numeric_dtype(raw_time):
            event_time = parse_numeric_event_time(raw_time)
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
    event_time = event_time.dt.floor("ms")

    year_month = event_time.dt.strftime("%Y-%m")

    cell_ids = [
        bin_id(float(la), float(lo), size_deg=cell_size_deg, prefix="cell")
        for la, lo in zip(lat.to_numpy(), lon.to_numpy(), strict=True)
    ]
    region_ids = [
        bin_id(float(la), float(lo), size_deg=region_size_deg, prefix="region")
        for la, lo in zip(lat.to_numpy(), lon.to_numpy(), strict=True)
    ]
    splits = [stable_split(cell_id, ym) for cell_id, ym in zip(cell_ids, year_month, strict=True)]

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

    return pa.Table.from_arrays(
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
            vector_from_columns(filtered, feature_template.env),
            vector_from_columns(filtered, feature_template.habitat),
            vector_from_columns(filtered, feature_template.weather),
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


def append_background_rows(table: pa.Table, ratio: float, src_path: Path) -> pa.Table:
    """Append unlabeled/background rows by deterministic resampling for PU setups."""
    if ratio <= 0 or table.num_rows == 0:
        return table

    background_count = int(round(table.num_rows * ratio))
    if background_count <= 0:
        return table

    seed = int.from_bytes(hashlib.blake2b(str(src_path).encode("utf-8"), digest_size=8).digest(), byteorder="big")
    rng = np.random.default_rng(seed)
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


def transform_file(
    src_path: Path,
    staging_dir: Path,
    *,
    feature_version: str,
    cell_size_deg: float,
    region_size_deg: float,
    feature_template: FeatureGroups,
    fallback_time_policy: str,
    background_ratio: float,
) -> TransformResult:
    """Transform one source parquet file into one staged training parquet shard."""
    start = time.perf_counter()
    read_start = time.perf_counter()
    table = pq.read_table(src_path, use_threads=True)
    read_seconds = time.perf_counter() - read_start
    frame = table.to_pandas(types_mapper=None)
    fallback_species_key = species_key_from_path(src_path)
    transformed = transform_frame(
        frame,
        feature_version=feature_version,
        cell_size_deg=cell_size_deg,
        region_size_deg=region_size_deg,
        fallback_species_key=fallback_species_key,
        feature_template=feature_template,
        fallback_time_policy=fallback_time_policy,
    )

    if background_ratio > 0:
        transformed = append_background_rows(transformed, background_ratio, src_path)

    staging_dir.mkdir(parents=True, exist_ok=True)
    out_path = staging_dir / (
        f"{src_path.stem}_{hashlib.blake2b(str(src_path).encode('utf-8'), digest_size=6).hexdigest()}.parquet"
    )
    pq.write_table(transformed, out_path, compression="zstd")
    duration_seconds = time.perf_counter() - start
    return TransformResult(
        out_path=out_path,
        rows=transformed.num_rows,
        duration_seconds=duration_seconds,
        read_seconds=read_seconds,
    )
