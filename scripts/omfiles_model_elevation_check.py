from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import json
import math
import os
import urllib.request

import fsspec
import numpy as np
from omfiles import OmFileReader

from util.config import load_config


CONFIG = load_config("global")

# Hardcoded test points (lat, lon, label)
POINTS = [
    (40.182837, -119.757990, "NV"),
    (39.840074, -109.914109, "UT"),
    (37.360344, -118.326919, "CA"),
    # From recent enrich_temporal debug min/max
    (-2.34132, -79.38357, "era5_min_dbg"),
    (-22.53647, -67.64918, "era5_max_dbg"),
    (18.37123, -71.44735, "era5_land_min_dbg"),
    (-15.78595, -71.85686, "era5_land_max_dbg"),
]

# Pick model here
MODEL = "copernicus_era5_land"

# Date window for API call (archive API needs a date range)
API_DATE = date(2020, 1, 1)


@dataclass
class AxisInfo:
    ny: int
    nx: int
    step: float
    mode: str


def _open_reader(uri: str, *, block_size: int = 64 * 1024 * 1024) -> OmFileReader:
    local_path = Path(uri)
    if local_path.exists():
        backend = fsspec.open(local_path.as_posix(), mode="rb")
        return OmFileReader(backend)

    return OmFileReader(
        fsspec.open(
            uri,
            mode="rb",
            s3={"anon": True, "default_block_size": block_size},
        )
    )


def _axis_info(reader: OmFileReader, model: str) -> AxisInfo:
    shape = reader.shape
    if len(shape) == 2:
        ny, nx = shape
    else:
        ny, nx = shape[0], shape[1]
    step = 0.1 if (ny in (1801, 1800) and nx in (3600, 3601)) else 0.25
    mode = CONFIG.temporal_grid_mode_by_model.get(model)
    if mode not in {
        "lat_asc_lon_pm180",
        "lat_asc_lon_360",
        "lat_desc_lon_pm180",
        "lat_desc_lon_360",
    }:
        raise RuntimeError(f"Missing/invalid grid mode for model={model}: {mode}")
    return AxisInfo(ny=ny, nx=nx, step=step, mode=mode)


def _grid_indices(lat: float, lon: float, axis: AxisInfo) -> tuple[int, int]:
    step = axis.step
    if axis.mode == "lat_asc_lon_360":
        lat_idx = int(round((lat + 90.0) / step))
        lon_idx = int(round((lon % 360.0) / step))
    elif axis.mode == "lat_asc_lon_pm180":
        lat_idx = int(round((lat + 90.0) / step))
        lon_idx = int(round((lon + 180.0) / step))
    elif axis.mode == "lat_desc_lon_360":
        lat_idx = int(round((90.0 - lat) / step))
        lon_idx = int(round((lon % 360.0) / step))
    else:
        lat_idx = int(round((90.0 - lat) / step))
        lon_idx = int(round((lon + 180.0) / step))
    lat_idx = max(0, min(lat_idx, axis.ny - 1))
    lon_idx = max(0, min(lon_idx, axis.nx - 1))
    return lat_idx, lon_idx


def _api_model_name(model: str) -> str:
    if model == "copernicus_era5_land":
        return "era5_land"
    return "era5"


def _fetch_api_elevation(lat: float, lon: float) -> float | None:
    api_model = _api_model_name(MODEL)
    start = API_DATE.isoformat()
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat:.6f}&longitude={lon:.6f}"
        f"&start_date={start}&end_date={start}"
        "&hourly=temperature_2m"
        f"&models={api_model}"
        "&elevation=nan&timezone=UTC"
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return float(payload.get("elevation"))
    except Exception:
        return None


def main() -> None:
    uri = f"s3://openmeteo/data/{MODEL}/static/HSURF.om"
    reader = _open_reader(uri)
    axis = _axis_info(reader, MODEL)
    # Preload full HSURF grid into memory to validate this path.
    try:
        grid = np.asarray(reader[:, :], dtype=float)
    except Exception:
        grid = None

    print(f"model={MODEL} step={axis.step} mode={axis.mode} ny={axis.ny} nx={axis.nx}")
    for lat, lon, label in POINTS:
        li, lo = _grid_indices(lat, lon, axis)
        if grid is not None:
            model_elev = grid[li, lo]
        else:
            try:
                model_elev = reader[li, lo, 0]
            except Exception:
                model_elev = reader[li, lo]
        api_elev = _fetch_api_elevation(lat, lon)
        diff = None
        if api_elev is not None and math.isfinite(api_elev):
            diff = float(model_elev) - api_elev
        print(
            f"{label} lat={lat:.6f} lon={lon:.6f} "
            f"model_elev={float(model_elev):.2f} api_elev={api_elev} diff={diff}"
        )

    reader.close()


if __name__ == "__main__":
    main()
