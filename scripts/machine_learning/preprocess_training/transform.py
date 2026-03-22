"""Feature construction and per-file transformation utilities."""

from __future__ import annotations

import json
import hashlib
import re
import threading
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

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
_CONTEXT_LOAD_LOCKS: dict[str, threading.Lock] = {}
_CONTEXT_LOAD_LOCKS_GUARD = threading.Lock()
_WARNING_KEYS: set[str] = set()
_WARNING_KEYS_GUARD = threading.Lock()
_UNCATALOGUED_SUMMARY = {
    "kept_occurrence": {},
    "skipped_context": {},
}
_UNCATALOGUED_SUMMARY_GUARD = threading.Lock()


@dataclass(frozen=True)
class FeatureGroups:
    bioclimate: list[str]
    landclass: list[str]
    terrain: list[str]
    edaphic: list[str]
    temporal: list[str]
    other: list[str]


@dataclass(frozen=True)
class TransformResult:
    out_path: Path
    rows: int
    duration_seconds: float
    read_seconds: float
    low_cell_warnings: list[str]
    static_context_rows: int
    temporal_context_rows: int


@dataclass(frozen=True)
class CatalogFeatureRules:
    bioclimate_exact: frozenset[str]
    landclass_exact: frozenset[str]
    terrain_exact: frozenset[str]
    edaphic_exact: frozenset[str]
    temporal_exact: frozenset[str]
    temporal_prefixes: tuple[str, ...]


def warn_once(key: str, message: str) -> None:
    """Print a warning message once per process for a stable warning key."""
    with _WARNING_KEYS_GUARD:
        if key in _WARNING_KEYS:
            return
        _WARNING_KEYS.add(key)
    print(f"Warning: {message}")


def reset_uncatalogued_summary() -> None:
    """Clear process-local uncatalogued column warnings and summary state."""
    with _WARNING_KEYS_GUARD:
        _WARNING_KEYS.clear()
    with _UNCATALOGUED_SUMMARY_GUARD:
        _UNCATALOGUED_SUMMARY["kept_occurrence"].clear()
        _UNCATALOGUED_SUMMARY["skipped_context"].clear()


def record_uncatalogued_column(
    *,
    group: Literal["kept_occurrence", "skipped_context"],
    column: str,
    example_path: Path,
) -> None:
    """Store one uncatalogued column example for later metadata export."""
    column_key = column.lower()
    with _UNCATALOGUED_SUMMARY_GUARD:
        entries: dict[str, dict[str, str]] = _UNCATALOGUED_SUMMARY[group]
        if column_key in entries:
            return
        entries[column_key] = {
            "column": column,
            "example_path": str(example_path),
        }


def get_uncatalogued_summary() -> dict[str, list[dict[str, str]]]:
    """Return a JSON-serializable summary of uncatalogued column handling."""
    with _UNCATALOGUED_SUMMARY_GUARD:
        kept = sorted(_UNCATALOGUED_SUMMARY["kept_occurrence"].values(), key=lambda item: item["column"].lower())
        skipped = sorted(_UNCATALOGUED_SUMMARY["skipped_context"].values(), key=lambda item: item["column"].lower())
    return {
        "kept_occurrence": kept,
        "skipped_context": skipped,
    }


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
    """Infer fallback species key from explicit species directory or path suffix search."""
    species_dir = src_path.parent.name
    match = _NUMERIC_SPECIES_SUFFIX.search(species_dir)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    for part in reversed(src_path.parts):
        match = _NUMERIC_SPECIES_SUFFIX.search(part)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def resolve_context_path(
    src_path: Path,
    *,
    template: str,
    fixed_path: Path | None,
    context_kind: str,
) -> Path | None:
    """Resolve context parquet path for a source file from template or fixed path."""
    if template:
        resolved = template.format(
            src_dir=str(src_path.parent),
            src_parent=src_path.parent.name,
            src_stem=src_path.stem,
            src_name=src_path.name,
        )
        if resolved:
            return Path(resolved)
    if fixed_path is not None:
        return fixed_path

    if context_kind == "static":
        candidates = [
            src_path.parent / "static_context.parquet",
            src_path.parent / "occurrence_static.parquet",
            src_path.parent / f"{src_path.stem}_static.parquet",
        ]
    else:
        candidates = [
            src_path.parent / "temporal_context.parquet",
            src_path.parent / "occurrence_temporal.parquet",
            src_path.parent / f"{src_path.stem}_temporal.parquet",
        ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def _find_join_column(columns: list[str], desired_name: str) -> str | None:
    """Find join column by case-insensitive exact match."""
    lookup = {column.lower(): column for column in columns}
    return lookup.get(desired_name.lower())


@lru_cache(maxsize=512)
def _load_context_table_cached(path_text: str) -> pd.DataFrame:
    """Load parquet context table once per path for process lifetime."""
    table = pq.read_table(Path(path_text), use_threads=True)
    return table.to_pandas(types_mapper=None)


def _context_lock_for_path(path_text: str) -> threading.Lock:
    """Return a stable per-path lock for context table single-flight loads."""
    with _CONTEXT_LOAD_LOCKS_GUARD:
        lock = _CONTEXT_LOAD_LOCKS.get(path_text)
        if lock is None:
            lock = threading.Lock()
            _CONTEXT_LOAD_LOCKS[path_text] = lock
        return lock


@lru_cache(maxsize=1)
def _load_catalog_feature_rules() -> CatalogFeatureRules:
    """Load GIS catalog-derived feature classification rules.

    Catalog rules are the only source of truth for feature grouping.
    """
    project_root = Path(__file__).resolve().parents[3]
    catalog_candidates = [
        project_root / "config" / "gis" / "catalog.json",
        project_root / "data" / "gis" / "catalog.json",
    ]
    catalog_path = next((path for path in catalog_candidates if path.exists()), None)
    if catalog_path is None:
        raise FileNotFoundError(
            "Missing GIS catalog.json. Expected one of: " + ", ".join(str(path) for path in catalog_candidates)
        )

    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Failed reading GIS catalog: {catalog_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in GIS catalog: {catalog_path}") from exc

    bioclimate_exact: set[str] = set()
    landclass_exact: set[str] = set()
    terrain_exact: set[str] = set()
    edaphic_exact: set[str] = set()
    temporal_exact: set[str] = set()
    temporal_prefixes: set[str] = set()

    for category in payload.get("categories", []):
        if not isinstance(category, dict):
            continue
        category_name = str(category.get("name", "")).strip().lower()
        layers = category.get("layers", [])
        if not isinstance(layers, list):
            continue

        for layer in layers:
            if not isinstance(layer, dict):
                continue
            layer_id = str(layer.get("id", "")).strip().lower()
            if not layer_id:
                continue

            if category_name == "bioclimate":
                bioclimate_exact.add(layer_id)
            elif category_name == "landclass":
                landclass_exact.add(layer_id)
            elif category_name == "terrain":
                terrain_exact.add(layer_id)
            elif category_name == "temporal":
                temporal_exact.add(layer_id)
                temporal_prefixes.add(f"{layer_id}_")
            elif category_name == "edaphic":
                edaphic_exact.add(layer_id)

    rules = CatalogFeatureRules(
        bioclimate_exact=frozenset(bioclimate_exact),
        landclass_exact=frozenset(landclass_exact),
        terrain_exact=frozenset(terrain_exact),
        edaphic_exact=frozenset(edaphic_exact),
        temporal_exact=frozenset(temporal_exact),
        temporal_prefixes=tuple(sorted(temporal_prefixes)),
    )

    if not (
        rules.bioclimate_exact
        or rules.landclass_exact
        or rules.terrain_exact
        or rules.edaphic_exact
        or rules.temporal_exact
    ):
        raise ValueError(f"GIS catalog produced no feature rules: {catalog_path}")

    return rules


def load_context_features(
    context_path: Path,
    *,
    join_keys: tuple[str, ...],
) -> pd.DataFrame:
    """Load context table and keep join keys plus recognized numeric feature columns."""
    path_text = str(context_path.resolve())
    path_lock = _context_lock_for_path(path_text)
    # Single-flight guard around cached reads prevents duplicate expensive file loads
    # when multiple worker threads miss the same cache key at the same time.
    with path_lock:
        frame = _load_context_table_cached(path_text)
    if frame.empty:
        return frame

    key_map: dict[str, str] = {}
    for key in join_keys:
        actual = _find_join_column(list(frame.columns), key)
        if actual is None:
            raise ValueError(f"Missing join key '{key}' in context table: {context_path}")
        key_map[key] = actual

    selected: list[str] = []
    selected.extend(key_map.values())
    for column in frame.columns:
        if column in selected:
            continue
        if not pd.api.types.is_numeric_dtype(frame[column]):
            continue
        if classify_feature_name(column) is None:
            column_name = column.lower()
            if column_name not in _EXCLUDED_FEATURE_COLUMNS_LOWER:
                record_uncatalogued_column(
                    group="skipped_context",
                    column=column,
                    example_path=context_path,
                )
                warn_once(
                    key=f"uncatalogued-context:{column_name}",
                    message=(f"uncatalogued numeric context column skipped | column={column} | example={context_path}"),
                )
            continue
        selected.append(column)

    subset = frame.loc[:, selected].copy()
    rename_map = {actual: key for key, actual in key_map.items() if actual != key}
    if rename_map:
        subset = subset.rename(columns=rename_map)
    return subset


def merge_context_columns(
    base: pd.DataFrame,
    context: pd.DataFrame,
    *,
    join_keys: list[str],
) -> tuple[pd.DataFrame, int]:
    """Merge context features into base frame while preserving existing observed values.

    Duplicate context keys are resolved deterministically:
    1) keep the row with the largest number of non-null feature values,
    2) if tied, keep the lexicographically greatest serialized feature tuple.
    """
    if context.empty:
        return base, 0

    valid = context.dropna(subset=join_keys).copy()
    if valid.empty:
        return base, 0

    feature_columns = [column for column in valid.columns if column not in join_keys]
    if not feature_columns:
        return base, 0

    feature_numeric = valid[feature_columns].apply(pd.to_numeric, errors="coerce")
    valid["__feature_non_null_count"] = feature_numeric.notna().sum(axis=1).astype(np.int32)

    tie_parts = valid[feature_columns].astype("string").fillna("")
    valid["__feature_tie_key"] = tie_parts.agg("|".join, axis=1)

    valid = valid.sort_values(
        by=[*join_keys, "__feature_non_null_count", "__feature_tie_key"],
        ascending=[True] * len(join_keys) + [True, True],
        kind="stable",
    )
    deduped = valid.drop_duplicates(subset=join_keys, keep="last").drop(
        columns=["__feature_non_null_count", "__feature_tie_key"]
    )

    merged = base.merge(
        deduped,
        how="left",
        on=join_keys,
        suffixes=("", "__context"),
    )

    matched_any = pd.Series(False, index=merged.index)
    for feature in feature_columns:
        context_column = f"{feature}__context" if feature in base.columns else feature
        if context_column not in merged.columns:
            continue
        context_values = pd.to_numeric(merged[context_column], errors="coerce")
        matched_any = matched_any | context_values.notna()

        if feature in base.columns:
            base_values = pd.to_numeric(merged[feature], errors="coerce")
            merged[feature] = base_values.combine_first(context_values)
            merged = merged.drop(columns=[context_column])
        else:
            merged[feature] = context_values

    merged_rows = int(matched_any.sum())
    return merged, merged_rows


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
    token = f"{cell_id}|{year_month}".encode()
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


def _build_constant_fixed_list_array(rows: int, list_size: int, value: float) -> pa.Array:
    """Build constant fixed-size list<float32> array."""
    if list_size <= 0:
        return pa.array([None] * rows, type=pa.list_(pa.float32()))
    values = np.full((rows, list_size), value, dtype=np.float32)
    flat = pa.array(values.reshape(-1), type=pa.float32())
    return pa.FixedSizeListArray.from_arrays(flat, list_size=list_size)


def _build_constant_mask_array(rows: int, list_size: int, value: int) -> pa.Array:
    """Build constant fixed-size list<int8> array used for feature missingness masks."""
    if list_size <= 0:
        return pa.array([None] * rows, type=pa.list_(pa.int8()))
    values = np.full((rows, list_size), value, dtype=np.int8)
    flat = pa.array(values.reshape(-1), type=pa.int8())
    return pa.FixedSizeListArray.from_arrays(flat, list_size=list_size)


def vector_from_columns(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    missing_sentinel: float,
) -> tuple[pa.Array, pa.Array]:
    """Create value and missing-mask vectors from provided columns.

    Missing mask convention: 1 = missing/unavailable, 0 = observed.
    """
    if not columns:
        return (
            pa.array([None] * len(frame), type=pa.list_(pa.float32())),
            pa.array([None] * len(frame), type=pa.list_(pa.int8())),
        )

    numeric = frame.reindex(columns=columns)
    numeric = numeric.apply(pd.to_numeric, errors="coerce")
    missing_mask = numeric.isna().to_numpy(dtype=np.int8, copy=False)
    values = numeric.fillna(float(missing_sentinel)).astype(np.float32).to_numpy(copy=False)

    flat = pa.array(values.reshape(-1), type=pa.float32())
    values_array = pa.FixedSizeListArray.from_arrays(flat, list_size=len(columns))

    mask_flat = pa.array(missing_mask.reshape(-1), type=pa.int8())
    mask_array = pa.FixedSizeListArray.from_arrays(mask_flat, list_size=len(columns))
    return values_array, mask_array


def classify_feature_name(column_name: str) -> str | None:
    """Classify numeric source column into catalog-native feature groups."""
    name = column_name.lower()
    if name in _EXCLUDED_FEATURE_COLUMNS_LOWER:
        return None

    catalog_rules = _load_catalog_feature_rules()
    if name in catalog_rules.bioclimate_exact:
        return "bioclimate"
    if name in catalog_rules.landclass_exact:
        return "landclass"
    if name in catalog_rules.terrain_exact:
        return "terrain"
    if name in catalog_rules.edaphic_exact:
        return "edaphic"
    if name in catalog_rules.temporal_exact or any(name.startswith(prefix) for prefix in catalog_rules.temporal_prefixes):
        return "temporal"

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
    static_context_template: str,
    static_context_path: Path | None,
    temporal_context_template: str,
    temporal_context_path: Path | None,
) -> FeatureGroups:
    """Build one global feature layout to keep vector sizes consistent."""
    bioclimate: set[str] = set()
    landclass: set[str] = set()
    terrain: set[str] = set()
    edaphic: set[str] = set()
    temporal: set[str] = set()
    other: set[str] = set()

    scan_files = files
    if template_scan_max_files > 0:
        scan_files = files[:template_scan_max_files]
        print(f"Schema scan selection | using {len(scan_files):,}/{len(files):,} files for feature template")

    schema_paths: list[tuple[Path, str]] = []
    seen_schema_paths: set[tuple[Path, str]] = set()

    def add_schema_path(path: Path | None, source_kind: str) -> None:
        if path is None or not path.exists():
            return
        resolved = path.resolve()
        key = (resolved, source_kind)
        if key in seen_schema_paths:
            return
        seen_schema_paths.add(key)
        schema_paths.append((resolved, source_kind))

    for path in scan_files:
        add_schema_path(path, "occurrence")
        add_schema_path(
            resolve_context_path(
                path,
                template=static_context_template,
                fixed_path=static_context_path,
                context_kind="static",
            ),
            "static_context",
        )
        add_schema_path(
            resolve_context_path(
                path,
                template=temporal_context_template,
                fixed_path=temporal_context_path,
                context_kind="temporal",
            ),
            "temporal_context",
        )

    scan_start = time.perf_counter()
    for index, (path, source_kind) in enumerate(schema_paths, start=1):
        schema_start = time.perf_counter()
        schema = pq.read_schema(path)
        schema_seconds = time.perf_counter() - schema_start

        if schema_seconds >= log_slow_read_seconds:
            print(f"Slow schema read ({schema_seconds:.1f}s) | {path}")

        for field in schema:
            if not is_numeric_arrow_type(field.type):
                continue
            feature_group = classify_feature_name(field.name)
            if feature_group == "bioclimate":
                bioclimate.add(field.name)
            elif feature_group == "landclass":
                landclass.add(field.name)
            elif feature_group == "terrain":
                terrain.add(field.name)
            elif feature_group == "edaphic":
                edaphic.add(field.name)
            elif feature_group == "temporal":
                temporal.add(field.name)
            elif field.name.lower() not in _EXCLUDED_FEATURE_COLUMNS_LOWER:
                if source_kind == "occurrence":
                    other.add(field.name)
                    record_uncatalogued_column(
                        group="kept_occurrence",
                        column=field.name,
                        example_path=path,
                    )
                    warn_once(
                        key=f"uncatalogued-occurrence:{field.name.lower()}",
                        message=(
                            "uncatalogued numeric observation column kept in other_features "
                            f"| column={field.name} | example={path}"
                        ),
                    )
                else:
                    record_uncatalogued_column(
                        group="skipped_context",
                        column=field.name,
                        example_path=path,
                    )
                    warn_once(
                        key=f"uncatalogued-context-schema:{field.name.lower()}",
                        message=(f"uncatalogued numeric context column skipped | column={field.name} | example={path}"),
                    )

        if schema_log_interval_files > 0 and index % schema_log_interval_files == 0:
            elapsed = time.perf_counter() - scan_start
            print(f"Schema scan progress | files: {index:,}/{len(schema_paths):,} | elapsed: {elapsed:.1f}s")

    return FeatureGroups(
        bioclimate=sorted(bioclimate),
        landclass=sorted(landclass),
        terrain=sorted(terrain),
        edaphic=sorted(edaphic),
        temporal=sorted(temporal),
        other=sorted(other),
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
    missing_feature_sentinel: float,
    warn_min_cells_per_species: int,
    static_context: pd.DataFrame | None,
    temporal_context: pd.DataFrame | None,
) -> tuple[pa.Table, list[str], int, int]:
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

    static_context_rows = 0
    temporal_context_rows = 0
    filtered["cell_id"] = np.asarray(cell_ids, dtype=object)
    filtered["year_month"] = year_month.to_numpy(dtype=object)

    if static_context is not None:
        filtered, static_context_rows = merge_context_columns(
            filtered,
            static_context,
            join_keys=["cell_id"],
        )

    if temporal_context is not None:
        filtered, temporal_context_rows = merge_context_columns(
            filtered,
            temporal_context,
            join_keys=["cell_id", "year_month"],
        )

    low_cell_warnings: list[str] = []
    if warn_min_cells_per_species > 0:
        species_cells = pd.DataFrame({
            "species_key": species_key.to_numpy(),
            "cell_id": np.asarray(cell_ids, dtype=object),
        })
        min_cells = species_cells.groupby("species_key", sort=False)["cell_id"].nunique(dropna=True).astype(int)
        flagged = min_cells[min_cells < int(warn_min_cells_per_species)]
        for sp_key, cell_count in flagged.items():
            low_cell_warnings.append(
                f"Low-cell species warning | species_key={sp_key} | unique_cells={int(cell_count)}"
            )

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

    bioclimate_values, bioclimate_missing_mask = vector_from_columns(
        filtered,
        feature_template.bioclimate,
        missing_sentinel=missing_feature_sentinel,
    )
    landclass_values, landclass_missing_mask = vector_from_columns(
        filtered,
        feature_template.landclass,
        missing_sentinel=missing_feature_sentinel,
    )
    terrain_values, terrain_missing_mask = vector_from_columns(
        filtered,
        feature_template.terrain,
        missing_sentinel=missing_feature_sentinel,
    )
    edaphic_values, edaphic_missing_mask = vector_from_columns(
        filtered,
        feature_template.edaphic,
        missing_sentinel=missing_feature_sentinel,
    )
    temporal_values, temporal_missing_mask = vector_from_columns(
        filtered,
        feature_template.temporal,
        missing_sentinel=missing_feature_sentinel,
    )
    other_values, other_missing_mask = vector_from_columns(
        filtered,
        feature_template.other,
        missing_sentinel=missing_feature_sentinel,
    )

    return (
        pa.Table.from_arrays(
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
                bioclimate_values,
                bioclimate_missing_mask,
                landclass_values,
                landclass_missing_mask,
                terrain_values,
                terrain_missing_mask,
                edaphic_values,
                edaphic_missing_mask,
                temporal_values,
                temporal_missing_mask,
                other_values,
                other_missing_mask,
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
                "bioclimate_features",
                "bioclimate_missing_mask",
                "landclass_features",
                "landclass_missing_mask",
                "terrain_features",
                "terrain_missing_mask",
                "edaphic_features",
                "edaphic_missing_mask",
                "temporal_features",
                "temporal_missing_mask",
                "other_features",
                "other_missing_mask",
            ],
        ),
        low_cell_warnings,
        static_context_rows,
        temporal_context_rows,
    )


def transform_file(
    src_path: Path,
    staging_dir: Path,
    *,
    feature_version: str,
    cell_size_deg: float,
    region_size_deg: float,
    feature_template: FeatureGroups,
    fallback_time_policy: str,
    missing_feature_sentinel: float,
    warn_min_cells_per_species: int,
    static_context_template: str,
    static_context_path: Path | None,
    static_context_required: bool,
    temporal_context_template: str,
    temporal_context_path: Path | None,
    temporal_context_required: bool,
) -> TransformResult:
    """Transform one source parquet file into one staged training parquet shard."""
    start = time.perf_counter()
    read_start = time.perf_counter()
    table = pq.read_table(src_path, use_threads=True)
    read_seconds = time.perf_counter() - read_start
    frame = table.to_pandas(types_mapper=None)

    static_context: pd.DataFrame | None = None
    static_path = resolve_context_path(
        src_path,
        template=static_context_template,
        fixed_path=static_context_path,
        context_kind="static",
    )
    if static_path is not None:
        if not static_path.exists():
            if static_context_required:
                raise ValueError(f"Static context parquet missing: {static_path}")
        else:
            try:
                static_context = load_context_features(static_path, join_keys=("cell_id",))
            except ValueError:
                if static_context_required:
                    raise
                static_context = None

    temporal_context: pd.DataFrame | None = None
    temporal_path = resolve_context_path(
        src_path,
        template=temporal_context_template,
        fixed_path=temporal_context_path,
        context_kind="temporal",
    )
    if temporal_path is not None:
        if not temporal_path.exists():
            if temporal_context_required:
                raise ValueError(f"Temporal context parquet missing: {temporal_path}")
        else:
            try:
                temporal_context = load_context_features(
                    temporal_path,
                    join_keys=("cell_id", "year_month"),
                )
            except ValueError:
                if temporal_context_required:
                    raise
                temporal_context = None

    fallback_species_key = species_key_from_path(src_path)
    transformed, low_cell_warnings, static_context_rows, temporal_context_rows = transform_frame(
        frame,
        feature_version=feature_version,
        cell_size_deg=cell_size_deg,
        region_size_deg=region_size_deg,
        fallback_species_key=fallback_species_key,
        feature_template=feature_template,
        fallback_time_policy=fallback_time_policy,
        missing_feature_sentinel=missing_feature_sentinel,
        warn_min_cells_per_species=warn_min_cells_per_species,
        static_context=static_context,
        temporal_context=temporal_context,
    )

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
        low_cell_warnings=low_cell_warnings,
        static_context_rows=static_context_rows,
        temporal_context_rows=temporal_context_rows,
    )
