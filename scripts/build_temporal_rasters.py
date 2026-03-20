"""
Build and incrementally update aggregate rasters for all temporal variables.

On first run: full rebuild from ERA5 + GFS013 chunks.
On subsequent runs: incremental sliding-window update —
  1. Drop the oldest hours that have fallen off the window
  2. Add the newest hours since last run
  3. Recompute final output and save

Sidecar files per raster:
  {var}_{window}.npy       — final output (avg or sum); read by the API
  {var}_{window}.meta.json — bookkeeping timestamps and counts
  {var}_{window}.sums.npz  — raw component sums (for incremental updates)

Sources:
  - ERA5-land (copernicus_era5_land, 0.1°): temp, soil, dew_point
  - ERA5      (copernicus_era5,     0.25°): cloud, precip, swe
  - GFS013    (ncep_gfs013,         0.125°): ~6-day ERA5 gap fill

All data reprojected to ERA5 0.25° output grid [721 × 1440].

Usage: pd scripts/build_temporal_rasters.py [--vars v1,v2] [--windows 24h,30d] [--force]
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fsspec
import numpy as np
from omfiles import OmFileReader
from rasterio.crs import CRS
from rasterio.transform import from_bounds as rasterio_from_bounds
from rasterio.warp import reproject, Resampling

# ── Config ────────────────────────────────────────────────────────────────────

ERA5_NY, ERA5_NX           = 721, 1440
ERA5_LAT_MIN, ERA5_LAT_MAX = -90.0,  90.0
ERA5_LON_MIN, ERA5_LON_MAX = -180.0, 180.0

MODELS: dict[str, dict] = {
    "copernicus_era5": {
        "s3":      "s3://openmeteo/data/copernicus_era5",
        "lat_min": -90.0, "lat_max": 90.0,
        "lon_min": -180.0, "lon_max": 180.0,
        "flipud":  False,
    },
    "copernicus_era5_land": {
        "s3":      "s3://openmeteo/data/copernicus_era5_land",
        "lat_min": -90.0, "lat_max": 90.0,
        "lon_min": -180.0, "lon_max": 180.0,
        "flipud":  True,
    },
    "ncep_gfs013": {
        "s3":      "s3://openmeteo/data/ncep_gfs013",
        "lat_min": -89.912125, "lat_max": 89.912125,
        "lon_min": -180.0,     "lon_max": 179.88281,
        "flipud":  True,
    },
}

WGS84   = CRS.from_epsg(4326)
OUT_DIR = Path(__file__).parent.parent / "data" / "gis" / "temporal" / "rasters"

WINDOW_HOURS  = [1, 8, 24, 72, 168, 720, 2160]
WINDOW_LABELS = {1: "1h", 8: "8h", 24: "24h", 72: "3d", 168: "7d", 720: "30d", 2160: "90d"}
FORECAST_HOURS = [1, 8, 24, 72, 168]

VAR_CONFIGS: dict[str, dict] = {
    "temperature_2m": {
        "era5_model": "copernicus_era5_land",
        "era5_var":   "temperature_2m",
        "gfs_var":    "temperature_2m",
        "agg": "avg",
    },
    "soil_moisture_0_to_7cm": {
        "era5_model": "copernicus_era5_land",
        "era5_var":   "soil_moisture_0_to_7cm",
        "gfs_var":    "soil_moisture_0_to_10cm",
        "agg": "avg",
    },
    "soil_temperature_0_to_7cm": {
        "era5_model": "copernicus_era5_land",
        "era5_var":   "soil_temperature_0_to_7cm",
        "gfs_var":    "soil_temperature_0_to_10cm",
        "agg": "avg",
    },
    "dew_point_2m": {
        "era5_model":        "copernicus_era5_land",
        "era5_var":          "dew_point_2m",
        "gfs_derived_needs": ["temperature_2m", "relative_humidity_2m"],
        "agg": "avg",
    },
    "vapor_pressure_deficit": {
        "era5_model":         "copernicus_era5_land",
        "era5_derived_needs": ["temperature_2m", "dew_point_2m"],
        "gfs_derived_needs":  ["temperature_2m", "relative_humidity_2m"],
        "agg": "avg",
    },
    "cloud_cover": {
        "era5_model": "copernicus_era5",
        "era5_var":   "cloud_cover",
        "gfs_var":    "cloud_cover",
        "agg": "avg",
    },
    "precipitation": {
        "era5_model": "copernicus_era5",
        "era5_var":   "precipitation",
        "gfs_var":    "precipitation",
        "agg": "sum",
    },
    "snowfall_water_equivalent": {
        "era5_model": "copernicus_era5",
        "era5_var":   "snowfall_water_equivalent",
        "gfs_var":    "snowfall_water_equivalent",
        "agg": "sum",
    },
}

# ── S3 / download helpers ─────────────────────────────────────────────────────

fs = fsspec.filesystem("s3", anon=True)


def _download_chunk(chunk_name: str, model: str, var: str) -> str:
    short = model.replace("copernicus_", "")
    local = f"/tmp/{short}_{var}_{chunk_name}"
    if not os.path.exists(local):
        s3 = f"{MODELS[model]['s3']}/{var}/{chunk_name}"
        print(f"    dl {model}/{var}/{chunk_name} ...", end=" ", flush=True)
        fs.get(s3, local)
        print("done", flush=True)
    return local


def _reproject_to_output(arr: np.ndarray, model: str) -> np.ndarray:
    m = MODELS[model]
    src = np.flipud(arr) if m["flipud"] else arr
    ny, nx = src.shape
    dest = np.zeros((ERA5_NY, ERA5_NX), dtype=np.float32)
    reproject(
        source=src, destination=dest,
        src_transform=rasterio_from_bounds(m["lon_min"], m["lat_min"], m["lon_max"], m["lat_max"], nx, ny),
        src_crs=WGS84, src_nodata=np.nan,
        dst_transform=rasterio_from_bounds(ERA5_LON_MIN, ERA5_LAT_MIN, ERA5_LON_MAX, ERA5_LAT_MAX, ERA5_NX, ERA5_NY),
        dst_crs=WGS84, dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    return dest


def _derive_vpd(T: np.ndarray, Td_or_RH: np.ndarray, mode: str) -> np.ndarray:
    es = 0.6108 * np.exp(17.27 * T / (T + 237.3))
    ea = (0.6108 * np.exp(17.27 * Td_or_RH / (Td_or_RH + 237.3))
          if mode == "td" else es * np.clip(Td_or_RH, 0, 100) / 100.0)
    return np.maximum(es - ea, 0.0).astype(np.float32)


def _derive_dew_point(T: np.ndarray, RH: np.ndarray) -> np.ndarray:
    RH_c  = np.clip(RH, 1.0, 100.0)
    gamma = np.log(RH_c / 100.0) + 17.625 * T / (243.04 + T)
    return (243.04 * gamma / (17.625 - gamma)).astype(np.float32)


# ── Chunk index ───────────────────────────────────────────────────────────────

def _build_chunk_index(model: str, var: str, resolution_s: float, data_end_ts: float,
                       window_start_ts: float, chunk_time_length: int
                       ) -> list[tuple[str, float, float, int]]:
    """List (chunk_name, start_ts, end_ts, time_len) newest→oldest.
    Uses chunk_time_length to compute timestamps without downloading files.
    Stops once it passes window_start_ts.
    """
    listing = fs.ls(f"{MODELS[model]['s3']}/{var}")
    names   = [item if isinstance(item, str) else item["name"] for item in listing]
    chunks  = sorted(
        [n.split("/")[-1] for n in names if n.split("/")[-1].startswith("chunk_") and n.endswith(".om")],
        key=lambda n: int(n.replace("chunk_", "").replace(".om", ""))
    )
    result = []
    running_end = data_end_ts
    for i, name in enumerate(reversed(chunks)):
        if i == 0:
            # Newest chunk may be partial — download it to get actual time_len
            local = _download_chunk(name, model, var)
            _, _, actual_tlen = OmFileReader(local).shape
            tlen = actual_tlen
        else:
            tlen = chunk_time_length
        start = running_end - (tlen - 1) * resolution_s
        result.append((name, start, running_end, tlen))
        running_end = start - resolution_s
        if start <= window_start_ts:
            break
    return result


# ── Slice accumulation ────────────────────────────────────────────────────────

def _accumulate(model: str, var: str, start_ts: float, end_ts: float,
                resolution_s: float, chunk_index: list) -> tuple[np.ndarray, int]:
    """Sum hourly slices in [start_ts, end_ts]. Downloads chunks lazily.
    Returns (sum_at_output_grid, n_hours).
    """
    native_acc: np.ndarray | None = None
    n_hours = 0
    for chunk_name, chunk_start_ts, chunk_end_ts, time_len in chunk_index:
        if chunk_end_ts < start_ts:
            break
        if chunk_start_ts > end_ts:
            continue
        t0 = max(0,        int(round((max(chunk_start_ts, start_ts) - chunk_start_ts) / resolution_s)))
        t1 = min(time_len, int(round((min(chunk_end_ts,   end_ts)   - chunk_start_ts) / resolution_s)) + 1)
        if t1 <= t0:
            continue
        local = _download_chunk(chunk_name, model, var)
        root  = OmFileReader(local)
        ny, nx, _ = root.shape
        if native_acc is None:
            native_acc = np.zeros((ny, nx), dtype=np.float64)
        native_acc += np.nansum(root.read_array((slice(0, ny), slice(0, nx), slice(t0, t1))), axis=2)
        n_hours += (t1 - t0)

    if native_acc is None:
        return np.zeros((ERA5_NY, ERA5_NX), dtype=np.float32), 0
    result = native_acc.astype(np.float32)
    if model != "copernicus_era5":
        result = _reproject_to_output(result, model)
    return result, n_hours


# ── Sums: keys are "era5_{raw_var}" and "gfs_{raw_var}" ──────────────────────

def _compute_final(var_id: str, cfg: dict, sums: dict[str, np.ndarray],
                   n_era5: int, n_gfs: int) -> np.ndarray:
    agg     = cfg["agg"]
    n_total = max(n_era5 + n_gfs, 1)
    zero    = np.zeros((ERA5_NY, ERA5_NX), dtype=np.float32)

    if var_id == "vapor_pressure_deficit":
        T_e  = sums.get("era5_temperature_2m", zero) / max(n_era5, 1)
        Td_e = sums.get("era5_dew_point_2m",   zero) / max(n_era5, 1)
        val  = _derive_vpd(T_e, Td_e, mode="td") * n_era5
        if n_gfs > 0 and "gfs_temperature_2m" in sums:
            T_g  = sums["gfs_temperature_2m"]    / n_gfs
            RH_g = sums["gfs_relative_humidity_2m"] / n_gfs
            val += _derive_vpd(T_g, RH_g, mode="rh") * n_gfs
        return (val / n_total).astype(np.float32)

    if var_id == "dew_point_2m":
        era5_val = sums.get("era5_dew_point_2m", zero) / max(n_era5, 1)
        if n_gfs > 0 and "gfs_temperature_2m" in sums:
            T_g  = sums["gfs_temperature_2m"]       / n_gfs
            RH_g = sums["gfs_relative_humidity_2m"] / n_gfs
            gfs_val = _derive_dew_point(T_g, RH_g)
            return ((era5_val * n_era5 + gfs_val * n_gfs) / n_total).astype(np.float32)
        return era5_val.astype(np.float32)

    era5_var = cfg.get("era5_var", "")
    gfs_var  = cfg.get("gfs_var", "")
    combined = (sums.get(f"era5_{era5_var}", zero) +
                sums.get(f"gfs_{gfs_var}",  zero))
    return (combined / n_total if agg == "avg" else combined).astype(np.float32)


def _state_paths(var_id: str, window_label: str, suffix: str = ""):
    base = OUT_DIR / f"{var_id}_{window_label}{suffix}"
    return (
        base.with_suffix(".npy"),
        Path(str(base) + ".meta.json"),
        Path(str(base) + ".sums.npz"),
    )


def _load_state(var_id: str, window_label: str, suffix: str = "") -> tuple[dict | None, dict | None]:
    _, meta_p, sums_p = _state_paths(var_id, window_label, suffix)
    if not meta_p.exists() or not sums_p.exists():
        return None, None
    with open(meta_p) as f:
        meta = json.load(f)
    sums = {k: v for k, v in np.load(sums_p).items()}
    return sums, meta


def _save_state(var_id: str, window_label: str, cfg: dict,
                sums: dict[str, np.ndarray], meta: dict, suffix: str = "") -> None:
    npy_p, meta_p, sums_p = _state_paths(var_id, window_label, suffix)
    result = _compute_final(var_id, cfg, sums, meta["n_era5"], meta["n_gfs"])
    np.save(npy_p, result)
    with open(meta_p, "w") as f:
        json.dump(meta, f, indent=2)
    np.savez(sums_p, **sums)
    print(f"  [{window_label:4s}] {meta['n_era5']}h ERA5 + {meta['n_gfs']}h GFS  "
          f"range=[{result.min():.3f}, {result.max():.3f}]  → {npy_p.name}")


# ── ERA5 raw var lists ────────────────────────────────────────────────────────

def _era5_raw_vars(cfg: dict) -> list[str]:
    ev = cfg.get("era5_var")
    return ([ev] if ev else []) + cfg.get("era5_derived_needs", [])


def _gfs_raw_vars(cfg: dict) -> list[str]:
    gv = cfg.get("gfs_var")
    return ([gv] if gv else []) + cfg.get("gfs_derived_needs", [])


# ── Full build for one var + window ──────────────────────────────────────────

def _full_build(var_id: str, cfg: dict, window_h: int, window_label: str,
                now_ts: float, era5_end_ts: float, gfs_end_ts: float,
                resolution_s: float,
                era5_cidx: dict[str, list], gfs_cidx: dict[str, list],
                suffix: str = "") -> None:
    era5_model = cfg["era5_model"]
    w_start    = now_ts - window_h * 3600

    sums: dict[str, np.ndarray] = {}
    n_era5_total = 0

    for rv in _era5_raw_vars(cfg):
        if rv not in era5_cidx:
            continue
        acc, n = _accumulate(era5_model, rv, w_start, era5_end_ts, resolution_s, era5_cidx[rv])
        sums[f"era5_{rv}"] = acc
        n_era5_total = max(n_era5_total, n)

    if not sums:
        print(f"  [{window_label}] no ERA5 data, skipping")
        return

    n_gfs_total = 0
    for gv in _gfs_raw_vars(cfg):
        if gv not in gfs_cidx:
            continue
        # GFS covers era5_end → gfs_end
        gfs_start = max(era5_end_ts, w_start)
        acc, n = _accumulate("ncep_gfs013", gv, gfs_start, gfs_end_ts, resolution_s, gfs_cidx[gv])
        sums[f"gfs_{gv}"] = acc
        n_gfs_total = max(n_gfs_total, n)

    meta = {
        "var_id": var_id, "window_h": window_h, "window_label": window_label,
        "era5_window_start_ts": w_start, "era5_end_ts": era5_end_ts,
        "gfs_start_ts": max(era5_end_ts, w_start),
        "gfs_end_ts": gfs_end_ts,
        "n_era5": n_era5_total, "n_gfs": n_gfs_total,
        "built_at": datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat(),
    }
    _save_state(var_id, window_label, cfg, sums, meta, suffix=suffix)


# ── Incremental update for one var + window ───────────────────────────────────

def _incremental_update(var_id: str, cfg: dict, window_h: int, window_label: str,
                        sums: dict[str, np.ndarray], old_meta: dict,
                        now_ts: float, era5_end_ts: float, gfs_end_ts: float,
                        resolution_s: float,
                        era5_cidx: dict[str, list], gfs_cidx: dict[str, list]) -> None:
    era5_model = cfg["era5_model"]
    new_w_start = now_ts - window_h * 3600
    old_w_start = old_meta["era5_window_start_ts"]
    old_gfs_end = old_meta["gfs_end_ts"]

    # If ERA5 has advanced since last build, trigger a full rebuild for accuracy
    old_era5_end = old_meta["era5_end_ts"]
    if era5_end_ts > old_era5_end + 3600:
        print(f"  [{window_label}] ERA5 advanced by {(era5_end_ts-old_era5_end)/3600:.0f}h → full rebuild")
        _full_build(var_id, cfg, window_h, window_label, now_ts, era5_end_ts, gfs_end_ts,
                    resolution_s, era5_cidx, gfs_cidx)
        return

    n_era5 = old_meta["n_era5"]
    n_gfs  = old_meta["n_gfs"]

    # ── 1. Drop oldest hours that fell off the window ──────────────────────
    if new_w_start > old_w_start:
        drop_end = min(new_w_start, era5_end_ts)  # how far into ERA5?
        if drop_end > old_w_start:
            for rv in _era5_raw_vars(cfg):
                key = f"era5_{rv}"
                if key not in sums or rv not in era5_cidx:
                    continue
                dropped, n_drop = _accumulate(era5_model, rv, old_w_start, drop_end,
                                              resolution_s, era5_cidx[rv])
                sums[key] = (sums[key] - dropped).astype(np.float32)
            n_era5 -= int(round((drop_end - old_w_start) / resolution_s))

        # Drop from GFS if window start is now in the GFS region
        gfs_drop_start = max(old_w_start, old_meta["gfs_start_ts"])
        gfs_drop_end   = min(new_w_start, old_gfs_end)
        if gfs_drop_end > gfs_drop_start:
            for gv in _gfs_raw_vars(cfg):
                key = f"gfs_{gv}"
                if key not in sums or gv not in gfs_cidx:
                    continue
                dropped, n_drop = _accumulate("ncep_gfs013", gv, gfs_drop_start, gfs_drop_end,
                                              resolution_s, gfs_cidx[gv])
                sums[key] = (sums[key] - dropped).astype(np.float32)
            n_gfs -= int(round((gfs_drop_end - gfs_drop_start) / resolution_s))

    # ── 2. Add newest GFS hours ────────────────────────────────────────────
    add_start = old_gfs_end
    add_end   = gfs_end_ts
    if add_end > add_start:
        for gv in _gfs_raw_vars(cfg):
            key = f"gfs_{gv}"
            if gv not in gfs_cidx:
                continue
            added, n_add = _accumulate("ncep_gfs013", gv, add_start, add_end,
                                       resolution_s, gfs_cidx[gv])
            sums[key] = (sums.get(key, np.zeros((ERA5_NY, ERA5_NX), dtype=np.float32)) + added).astype(np.float32)
        n_gfs += int(round((add_end - add_start) / resolution_s))

    n_era5 = max(n_era5, 0)
    n_gfs  = max(n_gfs,  0)

    meta = {
        **old_meta,
        "era5_window_start_ts": new_w_start,
        "gfs_start_ts": max(era5_end_ts, new_w_start),
        "gfs_end_ts": gfs_end_ts,
        "n_era5": n_era5, "n_gfs": n_gfs,
        "built_at": datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat(),
    }
    _save_state(var_id, window_label, cfg, sums, meta)


# ── Stale chunk cleanup ───────────────────────────────────────────────────────

def _cleanup_stale_chunks(needed_chunks: set[str], indexed_prefixes: set[str]) -> None:
    """Delete locally cached .om chunks that are no longer within any aggregation window.

    Only removes files whose model+var prefix was indexed this run (so we don't
    accidentally delete chunks for vars we didn't process).
    """
    removed = 0
    for path in Path("/tmp").glob("*_chunk_*.om"):
        name = path.name
        idx = name.find("_chunk_")
        if idx == -1:
            continue
        prefix     = name[:idx]           # e.g. "era5_land_temperature_2m"
        chunk_name = name[idx + 1:]       # e.g. "chunk_42.om"
        if prefix in indexed_prefixes and chunk_name not in needed_chunks:
            path.unlink(missing_ok=True)
            removed += 1
    if removed:
        print(f"  cleaned {removed} stale .om chunk(s) from /tmp/")


# ── Forecast aggregate builds ─────────────────────────────────────────────────

def build_forecast_aggregates(
    forecast_hours_list: list[int],
    var_configs: dict,
    windows: list[tuple[int, str]],
    now_ts: float,
    era5_end_ts: float,
    gfs_data_end_ts: float,
    resolution_s: float,
    era5_cidx_by_var: dict[str, dict[str, list]],
    gfs_cidx: dict[str, list],
) -> None:
    """Build aggregate rasters for each forecast offset.

    Each file is saved as {var}_{window}__f{hours:03d}h.npy (e.g. temperature_2m_30d__f072h.npy).

    Uses the "now" sums as a starting point and applies a small incremental delta:
      - drop the oldest forecast_h hours from the ERA5/GFS tail
      - add the GFS forecast hours at the leading edge
    This makes each forecast offset O(forecast_hours) rather than O(window_size).
    Falls back to a full build if the "now" state is missing.
    """
    print("\n=== forecast aggregate builds ===")
    for forecast_h in forecast_hours_list:
        future_ts      = now_ts + forecast_h * 3600
        gfs_end_for_fc = min(gfs_data_end_ts, future_ts)
        suffix         = f"__f{forecast_h:03d}h"
        future_dt      = datetime.fromtimestamp(future_ts, tz=timezone.utc)
        print(f"\n--- +{forecast_h}h forecast | anchor={future_dt.strftime('%Y-%m-%dT%HZ')} ---")

        for var_id, cfg in var_configs.items():
            era5_cidx  = era5_cidx_by_var.get(var_id, {})
            era5_model = cfg["era5_model"]

            for window_h, window_label in windows:
                print(f"  [{window_label:4s}] {var_id} +{forecast_h}h ...", flush=True)

                # Load the "now" state built in the main loop
                now_sums, now_meta = _load_state(var_id, window_label)
                if now_sums is None:
                    # State missing — fall back to full build
                    _full_build(var_id, cfg, window_h, window_label,
                                future_ts, era5_end_ts, gfs_end_for_fc,
                                resolution_s, era5_cidx, gfs_cidx, suffix=suffix)
                    continue

                sums   = {k: v.copy() for k, v in now_sums.items()}
                n_era5 = now_meta["n_era5"]
                n_gfs  = now_meta["n_gfs"]
                old_w_start  = now_meta["era5_window_start_ts"]
                old_gfs_end  = now_meta["gfs_end_ts"]
                old_gfs_start = now_meta["gfs_start_ts"]
                new_w_start  = old_w_start + forecast_h * 3600

                # 1. Drop oldest forecast_h hours from the ERA5 tail
                drop_end = min(new_w_start, era5_end_ts)
                if drop_end > old_w_start:
                    for rv in _era5_raw_vars(cfg):
                        key = f"era5_{rv}"
                        if key not in sums or rv not in era5_cidx:
                            continue
                        dropped, _ = _accumulate(era5_model, rv, old_w_start, drop_end,
                                                 resolution_s, era5_cidx[rv])
                        sums[key] = (sums[key] - dropped).astype(np.float32)
                    n_era5 -= int(round((drop_end - old_w_start) / resolution_s))

                # Drop from GFS if the old window start was already in the GFS region
                gfs_drop_end = min(new_w_start, old_gfs_end)
                if gfs_drop_end > old_gfs_start:
                    for gv in _gfs_raw_vars(cfg):
                        key = f"gfs_{gv}"
                        if key not in sums or gv not in gfs_cidx:
                            continue
                        dropped, _ = _accumulate("ncep_gfs013", gv, old_gfs_start, gfs_drop_end,
                                                 resolution_s, gfs_cidx[gv])
                        sums[key] = (sums[key] - dropped).astype(np.float32)
                    n_gfs -= int(round((gfs_drop_end - old_gfs_start) / resolution_s))

                # 2. Add new GFS forecast hours [old_gfs_end → future_ts]
                if gfs_end_for_fc > old_gfs_end:
                    for gv in _gfs_raw_vars(cfg):
                        key = f"gfs_{gv}"
                        if gv not in gfs_cidx:
                            continue
                        added, n_add = _accumulate("ncep_gfs013", gv, old_gfs_end, gfs_end_for_fc,
                                                   resolution_s, gfs_cidx[gv])
                        sums[key] = (sums.get(key, np.zeros((ERA5_NY, ERA5_NX), dtype=np.float32))
                                     + added).astype(np.float32)
                    n_gfs += int(round((gfs_end_for_fc - old_gfs_end) / resolution_s))

                n_era5 = max(n_era5, 0)
                n_gfs  = max(n_gfs,  0)
                meta = {
                    **now_meta,
                    "era5_window_start_ts": new_w_start,
                    "gfs_start_ts": max(era5_end_ts, new_w_start),
                    "gfs_end_ts": gfs_end_for_fc,
                    "n_era5": n_era5, "n_gfs": n_gfs,
                    "built_at": datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat(),
                }
                _save_state(var_id, window_label, cfg, sums, meta, suffix=suffix)


# ── Main ──────────────────────────────────────────────────────────────────────

def main(only_vars: list[str] | None, only_windows: list[str] | None,
         force: bool = False) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    var_configs = {k: v for k, v in VAR_CONFIGS.items()
                   if only_vars is None or k in only_vars}
    windows = [(h, WINDOW_LABELS[h]) for h in WINDOW_HOURS
               if only_windows is None or WINDOW_LABELS[h] in only_windows]
    max_window_h = max(h for h, _ in windows)

    # Read model metadata
    with fs.open(f"{MODELS['copernicus_era5']['s3']}/static/meta.json") as f:
        era5_meta = json.load(f)
    era5_end_ts       = float(era5_meta["data_end_time"])
    resolution_s      = float(era5_meta.get("temporal_resolution_seconds", 3600))
    era5_chunk_length = int(era5_meta.get("chunk_time_length", 1464))

    with fs.open(f"{MODELS['ncep_gfs013']['s3']}/static/meta.json") as f:
        gfs_meta = json.load(f)
    gfs_chunk_length = int(gfs_meta.get("chunk_time_length", 481))
    now_ts         = datetime.now(timezone.utc).timestamp()
    gfs_data_end_ts = float(gfs_meta["data_end_time"])   # actual chunk anchor (may be future forecast)
    gfs_end_ts      = min(gfs_data_end_ts, now_ts)        # capped to now for accumulation bounds

    era5_end_dt = datetime.fromtimestamp(era5_end_ts, tz=timezone.utc)
    gfs_end_dt  = datetime.fromtimestamp(gfs_end_ts,  tz=timezone.utc)
    now         = datetime.fromtimestamp(now_ts, tz=timezone.utc)

    print(f"ERA5 ends : {era5_end_dt.strftime('%Y-%m-%dT%HZ')}")
    print(f"GFS  ends : {gfs_end_dt.strftime('%Y-%m-%dT%HZ')}")
    print(f"Now       : {now.strftime('%Y-%m-%dT%HZ')}")
    print(f"ERA5 gap  : {(now - era5_end_dt).total_seconds()/3600:.1f}h (filled by GFS)")
    print(f"Max window: {max_window_h}h  Force rebuild: {force}\n")

    window_start_ts = now_ts - max_window_h * 3600

    # ── Collect GFS raw vars needed ───────────────────────────────────────
    gfs_raw_needed: set[str] = set()
    for cfg in var_configs.values():
        gfs_raw_needed.update(_gfs_raw_vars(cfg))

    # ── Build chunk indices (no downloads) ────────────────────────────────
    print("=== chunk indices ===")
    gfs_cidx: dict[str, list] = {}
    for gv in sorted(gfs_raw_needed):
        try:
            gfs_cidx[gv] = _build_chunk_index(
                "ncep_gfs013", gv, resolution_s, gfs_data_end_ts,  # uncapped: correct chunk anchor
                window_start_ts=era5_end_ts, chunk_time_length=gfs_chunk_length,
            )
            print(f"  GFS {gv}: {len(gfs_cidx[gv])} chunk(s)")
        except Exception as e:
            print(f"  GFS {gv}: ERROR {e}")

    # ── Process each variable ─────────────────────────────────────────────
    era5_cidx_by_var: dict[str, dict[str, list]] = {}

    for var_id, cfg in var_configs.items():
        print(f"\n=== {var_id} ===")
        era5_model = cfg["era5_model"]

        # Build ERA5 chunk indices for this var
        era5_cidx: dict[str, list] = {}
        for rv in _era5_raw_vars(cfg):
            try:
                era5_cidx[rv] = _build_chunk_index(
                    era5_model, rv, resolution_s, era5_end_ts,
                    window_start_ts=window_start_ts, chunk_time_length=era5_chunk_length,
                )
                print(f"  ERA5 {rv}: {len(era5_cidx[rv])} chunk(s)")
            except Exception as e:
                print(f"  ERA5 {rv}: ERROR {e}")
        era5_cidx_by_var[var_id] = era5_cidx

        for window_h, window_label in windows:
            sums, old_meta = _load_state(var_id, window_label)

            if force or sums is None:
                print(f"  [{window_label}] full build ...", flush=True)
                _full_build(var_id, cfg, window_h, window_label,
                            now_ts, era5_end_ts, gfs_end_ts, resolution_s,
                            era5_cidx, gfs_cidx)
            else:
                hours_stale = (now_ts - old_meta["gfs_end_ts"]) / 3600
                print(f"  [{window_label}] incremental update ({hours_stale:.1f}h stale) ...", flush=True)
                _incremental_update(var_id, cfg, window_h, window_label,
                                    sums, old_meta,
                                    now_ts, era5_end_ts, gfs_end_ts, resolution_s,
                                    era5_cidx, gfs_cidx)

    # ── Build forecast aggregate rasters ──────────────────────────────────
    build_forecast_aggregates(
        FORECAST_HOURS, var_configs, windows,
        now_ts, era5_end_ts, gfs_data_end_ts,
        resolution_s, era5_cidx_by_var, gfs_cidx,
    )

    # ── Clean up stale downloaded chunks ──────────────────────────────────
    needed_chunks: set[str] = set()
    indexed_prefixes: set[str] = set()
    for gv, idx_list in gfs_cidx.items():
        indexed_prefixes.add(f"gfs013_{gv}")
        for chunk_name, *_ in idx_list:
            needed_chunks.add(chunk_name)
    for var_id, era5_cidx in era5_cidx_by_var.items():
        short = VAR_CONFIGS[var_id]["era5_model"].replace("copernicus_", "")
        for rv, idx_list in era5_cidx.items():
            indexed_prefixes.add(f"{short}_{rv}")
            for chunk_name, *_ in idx_list:
                needed_chunks.add(chunk_name)
    _cleanup_stale_chunks(needed_chunks, indexed_prefixes)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from util.config import GlobalConfig

    cfg = GlobalConfig()

    only_vars    = list(cfg.temporal_raster_vars)    or None
    only_windows = list(cfg.temporal_raster_windows) or None

    main(only_vars=only_vars, only_windows=only_windows, force=cfg.temporal_raster_force_rebuild)

    if cfg.temporal_raster_upload_enabled:
        import subprocess
        print("\n=== uploading to B2 ===")
        result = subprocess.run(
            ["rclone", "sync", str(OUT_DIR), cfg.temporal_raster_b2_dest,
             "--include", "*.npy",
             "--include", "*.meta.json",
             "--include", "*.sums.npz",
             "--stats-one-line"],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"  rclone exited with code {result.returncode}")
        else:
            print("  upload complete")

    print("\n=== preloading forecast tiles ===")
    from util import weather_tiles
    weather_tiles.preload_all_forecasts()
    weather_tiles.cleanup_weather_disk_cache(now_ts)
