import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

import numpy as np
import pyarrow.parquet as pq
import pytest
import fsspec
from omfiles import OmFileReader

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from util.config import load_config  # noqa: E402

PARQUET_PATH = Path(
    "/workspace/data/species/taxonomy/Animalia_1/Chordata_44/"
    "Amphibia_131/Anura_952/Scaphiopodidae_3098/Spea_2429782/"
    "Spea_intermontana_2429791/occurrence.parquet"
)
LAT_COL = "decimalLatitude"
LON_COL = "decimalLongitude"
TIME_COL = "eventTimestamp"
CATALOG_COL = "catalogNumber"
CONFIG = load_config("global")
MODEL_PREFERENCE = CONFIG.temporal_model_preference
MODELS_BY_VAR = CONFIG.temporal_models_by_variable
WINDOWS_BY_VAR = CONFIG.temporal_window_hours_by_variable
DEFAULT_WINDOWS = CONFIG.temporal_window_hours_default
AGG_BY_VAR = CONFIG.temporal_agg_by_variable
SKIP_VARIABLES = {"weather_code_simple"}

VARIABLES = [v for v in MODELS_BY_VAR.keys() if v not in SKIP_VARIABLES]
ROW_INDICES = [0, 1, 2]

API_MODELS = {
    "copernicus_era5": "era5",
    "copernicus_era5_land": "era5_land",
    "copernicus_era5_ensemble": "era5_ensemble",
}

OBSERVATION_ID = "10672205"
OBS_LAT = 39.8400741581
OBS_LON = -109.9141091108
# Observed: Jul 31, 2005 8:25 PM MDT => 2005-08-01T02:25:00Z
OBS_DT = datetime(2005, 8, 1, 2, 25, tzinfo=timezone.utc)
MIN_YEAR = 2010


def _to_datetime_utc(ts_value: float) -> datetime:
    # Heuristic: if value looks like ns, scale to seconds
    ts = float(ts_value)
    if ts > 1e12:
        ts /= 1e9
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _fetch_openmeteo_window(
    lat: float,
    lon: float,
    dt: datetime,
    *,
    variable: str,
    hours: int,
    agg_mode: str,
    model: str,
) -> tuple[float, str]:
    end_dt = dt.replace(minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(hours=hours - 1)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat:.6f}"
        f"&longitude={lon:.6f}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&hourly={variable}"
        f"&models={API_MODELS.get(model, model)}"
        "&elevation=nan"
        "&timezone=UTC"
    )
    try:
        with urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError) as exc:
        pytest.skip(f"Open-Meteo API unavailable: {exc}")

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    vals = hourly.get(variable) or []
    if not times or not vals:
        pytest.skip(f"Open-Meteo API returned no hourly {variable}")

    target = end_dt
    target_str = target.strftime("%Y-%m-%dT%H:%M")
    try:
        idx_end = times.index(target_str)
    except ValueError:
        pytest.skip("Target timestamp not present in Open-Meteo hourly data")

    idx_start = idx_end - (hours - 1)
    if idx_start < 0:
        pytest.skip("Not enough hourly data to compute window")

    window = vals[idx_start:idx_end + 1]
    if len(window) != hours:
        pytest.skip("Unexpected hourly window size for window")
    numeric = [float(v) for v in window]
    if agg_mode == "sum":
        return float(sum(numeric)), url
    return float(sum(numeric) / len(numeric)), url


def _open_om_reader(model: str, variable: str, year: int) -> OmFileReader:
    local_path = Path(
        f"/workspace/data/gis/temporal/{model}/{variable}/year_{year}.om"
    )
    if local_path.exists():
        return OmFileReader(fsspec.open(local_path.as_posix(), mode="rb"))
    uri = f"s3://openmeteo/data/{model}/{variable}/year_{year}.om"
    return OmFileReader(
        fsspec.open(
            f"blockcache::{uri}",
            mode="rb",
            s3={"anon": True, "default_block_size": 65536},
            blockcache={"cache_storage": "cache"},
        )
    )


def _grid_index_candidates(lat: float, lon: float, ny: int, nx: int, step: float) -> list[tuple[int, int]]:
    candidates: list[tuple[int, int]] = []
    lat_desc = int(round((90.0 - lat) / step))
    lat_asc = int(round((lat + 90.0) / step))
    lon_pm = int(round((lon + 180.0) / step))
    lon_360 = int(round((lon % 360.0) / step))
    for li, lo in (
        (lat_desc, lon_pm),
        (lat_desc, lon_360),
        (lat_asc, lon_pm),
        (lat_asc, lon_360),
    ):
        li = max(0, min(li, ny - 1))
        lo = max(0, min(lo, nx - 1))
        candidates.append((li, lo))
    return candidates


def _is_nan(value: object) -> bool:
    try:
        return bool(np.isnan(value))
    except Exception:
        return False


def _window_from_omfiles(
    lat: float,
    lon: float,
    dt: datetime,
    *,
    model: str,
    variable: str,
    hours: int,
    agg_mode: str,
) -> float:
    year = dt.year
    with _open_om_reader(model, variable, year) as reader:
        ny, nx, time_len = reader.shape
        step = 0.1 if (ny in (1801, 1800) and nx in (3600, 3601)) else 0.25
        # Fixed grid mode discovered in diagnostics: lat_asc_lon_pm180
        lat_idx = int(round((lat + 90.0) / step))
        lon_idx = int(round((lon + 180.0) / step))
        lat_idx = max(0, min(lat_idx, ny - 1))
        lon_idx = max(0, min(lon_idx, nx - 1))

        resolution = 3600.0
        meta = getattr(reader, "meta", None) or getattr(reader, "metadata", None) or {}
        if isinstance(meta, dict):
            value = meta.get("temporal_resolution_seconds")
            if isinstance(value, (int, float)):
                resolution = float(value)

        start_time = datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()
        end_dt = dt.replace(minute=0, second=0, microsecond=0)
        idx_end = int(round((end_dt.timestamp() - start_time) / resolution))
        idx_end = max(0, min(idx_end, time_len - 1))
        window_len = int(round((hours * 3600) / resolution))
        idx_start = max(0, idx_end - window_len + 1)
        series = np.array(
            [reader[lat_idx, lon_idx, idx] for idx in range(idx_start, idx_end + 1)],
            dtype=float,
        )
        series = series[np.isfinite(series)]
        if series.size == 0:
            return float("nan")
        if agg_mode == "sum":
            return float(series.sum())
        return float(series.mean())


def _model_for_variable(variable: str) -> str:
    models = MODELS_BY_VAR.get(variable, ())
    if not models:
        return ""
    for preferred in MODEL_PREFERENCE:
        if preferred in models:
            return preferred
    return models[0]


def _find_catalog_row(table: object, catalog_id: str) -> int | None:
    data = table.to_pydict()
    ids = data.get(CATALOG_COL) or []
    for idx, value in enumerate(ids):
        if value is None:
            continue
        if str(value) == catalog_id:
            return idx
    return None


@pytest.mark.parametrize("variable", VARIABLES)
@pytest.mark.parametrize("row_index", ROW_INDICES)
def test_temporal_parquet_matches_openmeteo(variable: str, row_index: int) -> None:
    if not PARQUET_PATH.exists():
        pytest.skip("Occurrence parquet not found")

    model = _model_for_variable(variable)
    if not model:
        pytest.skip("Variable has no configured model")
    windows = WINDOWS_BY_VAR.get(variable, DEFAULT_WINDOWS)
    if not windows:
        pytest.skip("Variable has no configured windows")

    schema_cols = pq.read_schema(PARQUET_PATH).names
    table = pq.read_table(PARQUET_PATH, columns=[LAT_COL, LON_COL, TIME_COL]).combine_chunks()
    if table.num_rows <= row_index:
        pytest.skip("Not enough rows in parquet for the test")

    row = table.slice(row_index, 1)
    lat = row[LAT_COL][0].as_py()
    lon = row[LON_COL][0].as_py()
    ts = row[TIME_COL][0].as_py()
    if lat is None or lon is None or ts is None:
        pytest.skip("Row missing lat/lon/timestamp")

    dt = _to_datetime_utc(ts)
    if dt.year < MIN_YEAR:
        pytest.skip("Pre-2010 observations are expected to be NaN")
    for hours in windows:
        col = f"{variable}_{AGG_BY_VAR.get(variable, 'avg')}_{hours}h"
        if col not in schema_cols:
            pytest.skip(f"Parquet missing column {col}")
        row_with_col = pq.read_table(
            PARQUET_PATH, columns=[LAT_COL, LON_COL, TIME_COL, col]
        ).combine_chunks().slice(row_index, 1)
        val = row_with_col[col][0].as_py()
        if val is None or (isinstance(val, float) and np.isnan(val)):
            pytest.skip(f"Row missing {col} value")

        api_val, url = _fetch_openmeteo_window(
            float(lat),
            float(lon),
            dt,
            variable=variable,
            hours=hours,
            agg_mode=AGG_BY_VAR.get(variable, "avg"),
            model=model,
        )

        om_val = _window_from_omfiles(
            float(lat),
            float(lon),
            dt,
            model=model,
            variable=variable,
            hours=hours,
            agg_mode=AGG_BY_VAR.get(variable, "avg"),
        )
        if np.isnan(om_val):
            pytest.skip("OM files returned NaN for this row")

        print(
            f"row={row_index} var={variable} h={hours} lat={lat:.6f} lon={lon:.6f} "
            f"time={dt.isoformat()} parquet={float(val)} omfiles={om_val} api={api_val} url={url}"
        )

        assert abs(om_val - api_val) <= 0.1
        assert abs(float(val) - om_val) <= 0.1


def test_specific_observation_temperature_2m() -> None:
    if not PARQUET_PATH.exists():
        pytest.skip("Occurrence parquet not found")
    variable = "temperature_2m"
    hours = 24
    agg_mode = AGG_BY_VAR.get(variable, "avg")
    model = _model_for_variable(variable)
    if not model:
        pytest.skip("Variable has no configured model")

    col = f"{variable}_{agg_mode}_{hours}h"
    schema_cols = pq.read_schema(PARQUET_PATH).names
    if col not in schema_cols or CATALOG_COL not in schema_cols:
        pytest.skip(f"Parquet missing {col} or {CATALOG_COL}")

    table = pq.read_table(
        PARQUET_PATH, columns=[CATALOG_COL, LAT_COL, LON_COL, TIME_COL, col]
    ).combine_chunks()
    row_idx = _find_catalog_row(table, OBSERVATION_ID)
    if row_idx is None:
        pytest.skip("Observation id not found in parquet")

    row = table.slice(row_idx, 1)
    lat = row[LAT_COL][0].as_py()
    lon = row[LON_COL][0].as_py()
    ts = row[TIME_COL][0].as_py()
    parquet_val = row[col][0].as_py()
    if lat is None or lon is None or ts is None:
        pytest.skip("Row missing lat/lon/timestamp")
    if parquet_val is None or (isinstance(parquet_val, float) and np.isnan(parquet_val)):
        pytest.skip("Row missing parquet value")

    dt = _to_datetime_utc(ts)
    if dt.year < MIN_YEAR:
        pytest.skip("Pre-2010 observations are expected to be NaN")
    api_val, url = _fetch_openmeteo_window(
        float(lat),
        float(lon),
        dt,
        variable=variable,
        hours=hours,
        agg_mode=agg_mode,
        model=model,
    )
    om_val = _window_from_omfiles(
        float(lat),
        float(lon),
        dt,
        model=model,
        variable=variable,
        hours=hours,
        agg_mode=agg_mode,
    )
    if np.isnan(om_val):
        pytest.skip("OM files returned NaN for this row")

    print(
        f"obs={OBSERVATION_ID} lat={lat:.6f} lon={lon:.6f} time={dt.isoformat()} "
        f"parquet={float(parquet_val)} omfiles={om_val} api={api_val} url={url}"
    )

    assert abs(om_val - api_val) <= 0.1
    assert abs(float(parquet_val) - om_val) <= 0.1
