"""Lightweight CPU inference for the Darwin SDM.

Loads an inference bundle (exported by ``scripts/machine_learning/train/export.py``)
and provides a single ``predict(lat, lon)`` function that returns ranked species
suitability scores for the given coordinate.

Typical startup flow (called once at import / FastAPI startup)::

    from util.inference import load_bundle, predict

    load_bundle("checkpoints/canary_cactus/inference_bundle.pt")
    results = predict(lat=25.0, lon=-100.0, top_k=10)

The module is deliberately free of CUDA / AMP dependencies so it runs on
CPU-only servers.
"""

from __future__ import annotations

import math
from importlib import import_module
from pathlib import Path
from typing import Any

import torch

# ---------------------------------------------------------------------------
# Lazy import of model classes — avoids hard-wiring sys.path at module level.
# The first call to ``load_bundle`` patches sys.path once.
# ---------------------------------------------------------------------------
SharedEncoder = None  # type: ignore[assignment]
SpeciesHead = None  # type: ignore[assignment]

# Module-level singleton state.
_bundle: dict[str, Any] | None = None
_encoder: torch.nn.Module | None = None
_heads: dict[int, torch.nn.Module] = {}
_cell_table: dict[str, dict[str, torch.Tensor]] = {}
_cell_size_deg: float = 0.25
_species_meta: dict[int, dict] = {}
_feature_names: dict[str, list[str]] | None = None
_input_dim: int = 0


def _lazy_import_models() -> None:
    """Import model classes from the training package on first use."""
    global SharedEncoder, SpeciesHead  # noqa: PLW0603
    if SharedEncoder is not None:
        return
    module = None
    try:
        module = import_module("scripts.machine_learning.train.model")
    except ImportError:
        import sys

        train_pkg = str(Path(__file__).resolve().parent.parent / "scripts" / "machine_learning" / "train")
        if train_pkg not in sys.path:
            sys.path.insert(0, train_pkg)
        module = import_module("model")

    SharedEncoder = getattr(module, "SharedEncoder")
    SpeciesHead = getattr(module, "SpeciesHead")


def _bin_id(lat: float, lon: float, size_deg: float) -> str:
    lat_bin = int(math.floor(lat / size_deg))
    lon_bin = int(math.floor(lon / size_deg))
    return f"cell_{lat_bin}_{lon_bin}"


# ---------------------------------------------------------------------------
# On-the-fly GIS feature sampling
# ---------------------------------------------------------------------------
_DEM_DERIVED = frozenset({"slope", "aspect", "aspect_deg"})


def _meters_per_degree(lat_deg: float) -> tuple[float, float]:
    """Metres-per-degree for latitude/longitude at *lat_deg*."""
    import numpy as np

    r = np.deg2rad(lat_deg)
    m_lat = 111132.92 - 559.82 * np.cos(2 * r) + 1.175 * np.cos(4 * r) - 0.0023 * np.cos(6 * r)
    m_lon = 111412.84 * np.cos(r) - 93.5 * np.cos(3 * r) + 0.118 * np.cos(5 * r)
    return float(m_lat), float(m_lon)


def _aspect_bin(deg: float) -> int:
    """8-bin compass classification matching ``enrich_tree``."""
    a = deg % 360.0
    if a < 22.5 or a >= 337.5:
        return 1
    if a < 67.5:
        return 2
    if a < 112.5:
        return 3
    if a < 157.5:
        return 4
    if a < 202.5:
        return 5
    if a < 247.5:
        return 6
    if a < 292.5:
        return 7
    return 8


def _sample_raster_value(layer_id: str, lat: float, lon: float) -> float | None:
    """Point-sample a GIS raster.  Returns ``None`` for nodata/missing."""
    try:
        import rasterio
    except ImportError:
        return None
    from util.gis_lookup import get_cog_path

    cog_path = get_cog_path(layer_id, lat, lon)
    if cog_path is None or not cog_path.exists():
        return None
    with rasterio.open(cog_path) as ds:
        for arr in ds.sample([(lon, lat)]):
            val = arr[0]
            if ds.nodata is not None and val == ds.nodata:
                return None
            if isinstance(val, float) and val != val:
                return None
            return float(val)
    return None


def _compute_dem_derived_single(lat: float, lon: float) -> dict[str, float]:
    """Slope / aspect / aspect_deg from a 3x3 DEM window (single point)."""
    import numpy as np

    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError:
        return {}
    from util.gis_lookup import get_cog_path

    dem_path = get_cog_path("elevation", lat, lon)
    if dem_path is None or not dem_path.exists():
        return {}

    with rasterio.open(dem_path) as ds:
        row, col = ds.index(lon, lat)
        if row - 1 < 0 or col - 1 < 0 or row + 1 >= ds.height or col + 1 >= ds.width:
            return {}
        win = ds.read(1, window=Window(col - 1, row - 1, 3, 3), boundless=False)
        if win.shape != (3, 3):
            return {}
        nodata = ds.nodata
        if nodata is not None and np.any(win == nodata):
            return {}
        if np.any(np.isnan(win)):
            return {}
        pw = abs(float(ds.transform.a))
        ph = abs(float(ds.transform.e))

    m_lat, m_lon = _meters_per_degree(lat)
    dx = pw * m_lon
    dy = ph * m_lat
    if dx == 0 or dy == 0:
        return {}

    z1, z2, z3 = win[0, 0], win[0, 1], win[0, 2]
    z4, _, z6 = win[1, 0], win[1, 1], win[1, 2]
    z7, z8, z9 = win[2, 0], win[2, 1], win[2, 2]

    dzdx = ((z3 + 2 * z6 + z9) - (z1 + 2 * z4 + z7)) / (8.0 * dx)
    dzdy = ((z7 + 2 * z8 + z9) - (z1 + 2 * z2 + z3)) / (8.0 * dy)

    slope_deg = float(np.degrees(np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2))))
    if dzdx == 0 and dzdy == 0:
        asp_deg = 0.0
    else:
        asp_deg = float(90.0 - np.degrees(np.arctan2(dzdy, -dzdx)))
        if asp_deg < 0:
            asp_deg += 360.0

    return {"slope": slope_deg, "aspect": float(_aspect_bin(asp_deg)), "aspect_deg": asp_deg}


def _sample_point_features(lat: float, lon: float) -> dict[str, torch.Tensor] | None:
    """Build a feature + mask vector for an arbitrary point from GIS rasters.

    Static (env + habitat) features are sampled from local COG tiles.
    Weather features are filled with zeros and marked entirely missing so
    the model relies only on environmental context.
    Returns ``None`` when feature names are unavailable or rasterio is
    not installed.
    """
    if _feature_names is None:
        return None
    try:
        import rasterio  # noqa: F401
    except ImportError:
        return None

    env_names: list[str] = _feature_names["env"]
    habitat_names: list[str] = _feature_names["habitat"]
    weather_dim: int = _input_dim - len(env_names) - len(habitat_names)

    needs_dem = _DEM_DERIVED & set(env_names)
    dem_vals = _compute_dem_derived_single(lat, lon) if needs_dem else {}

    env_v: list[float] = []
    env_m: list[float] = []
    for name in env_names:
        val = dem_vals.get(name) if name in _DEM_DERIVED else _sample_raster_value(name, lat, lon)
        if val is None:
            env_v.append(0.0)
            env_m.append(1.0)
        else:
            env_v.append(val)
            env_m.append(0.0)

    hab_v: list[float] = []
    hab_m: list[float] = []
    for name in habitat_names:
        val = _sample_raster_value(name, lat, lon)
        if val is None:
            hab_v.append(0.0)
            hab_m.append(1.0)
        else:
            hab_v.append(val)
            hab_m.append(0.0)

    features = env_v + hab_v + [0.0] * weather_dim
    mask = env_m + hab_m + [1.0] * weather_dim

    feat_t = torch.tensor(features, dtype=torch.float32)
    mask_t = torch.tensor(mask, dtype=torch.float32)
    feat_t[mask_t > 0.5] = 0.0
    return {"features": feat_t, "mask": mask_t}


def _batch_sample_raster(layer_id: str, coords: list[tuple[float, float]]) -> list[float | None]:
    """Sample one raster layer at many points, opening each region tile once."""
    import rasterio
    from util.gis_lookup import get_cog_path, get_region_name

    results: list[float | None] = [None] * len(coords)
    groups: dict[str, list[tuple[int, float, float]]] = {}
    for i, (lat, lon) in enumerate(coords):
        groups.setdefault(get_region_name(lat, lon), []).append((i, lat, lon))

    for _region, members in groups.items():
        _, ref_lat, ref_lon = members[0]
        cog_path = get_cog_path(layer_id, ref_lat, ref_lon)
        if cog_path is None or not cog_path.exists():
            continue
        xy = [(lon, lat) for _, lat, lon in members]
        idx_list = [i for i, _, _ in members]
        with rasterio.open(cog_path) as ds:
            nodata = ds.nodata
            for arr, idx in zip(ds.sample(xy), idx_list):
                val = arr[0]
                if nodata is not None and val == nodata:
                    continue
                if isinstance(val, float) and val != val:
                    continue
                results[idx] = float(val)
    return results


def _batch_compute_dem_derived(coords: list[tuple[float, float]]) -> list[dict[str, float]]:
    """Batch DEM-derived features, opening each region COG once."""
    import numpy as np
    import rasterio
    from rasterio.windows import Window
    from util.gis_lookup import get_cog_path, get_region_name

    results: list[dict[str, float]] = [{} for _ in coords]
    groups: dict[str, list[tuple[int, float, float]]] = {}
    for i, (lat, lon) in enumerate(coords):
        groups.setdefault(get_region_name(lat, lon), []).append((i, lat, lon))

    for _region, members in groups.items():
        _, ref_lat, ref_lon = members[0]
        dem_path = get_cog_path("elevation", ref_lat, ref_lon)
        if dem_path is None or not dem_path.exists():
            continue
        with rasterio.open(dem_path) as ds:
            nodata = ds.nodata
            pw = abs(float(ds.transform.a))
            ph = abs(float(ds.transform.e))
            for idx, lat, lon in members:
                row, col = ds.index(lon, lat)
                if row - 1 < 0 or col - 1 < 0 or row + 1 >= ds.height or col + 1 >= ds.width:
                    continue
                win = ds.read(1, window=Window(col - 1, row - 1, 3, 3), boundless=False)
                if win.shape != (3, 3):
                    continue
                if nodata is not None and np.any(win == nodata):
                    continue
                if np.any(np.isnan(win)):
                    continue
                m_lat, m_lon = _meters_per_degree(lat)
                dx = pw * m_lon
                dy = ph * m_lat
                if dx == 0 or dy == 0:
                    continue
                z1, z2, z3 = win[0, 0], win[0, 1], win[0, 2]
                z4, _, z6 = win[1, 0], win[1, 1], win[1, 2]
                z7, z8, z9 = win[2, 0], win[2, 1], win[2, 2]
                dzdx = ((z3 + 2 * z6 + z9) - (z1 + 2 * z4 + z7)) / (8.0 * dx)
                dzdy = ((z7 + 2 * z8 + z9) - (z1 + 2 * z2 + z3)) / (8.0 * dy)
                slope_deg = float(np.degrees(np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2))))
                if dzdx == 0 and dzdy == 0:
                    asp_deg = 0.0
                else:
                    asp_deg = float(90.0 - np.degrees(np.arctan2(dzdy, -dzdx)))
                    if asp_deg < 0:
                        asp_deg += 360.0
                results[idx] = {"slope": slope_deg, "aspect": float(_aspect_bin(asp_deg)), "aspect_deg": asp_deg}
    return results


def _batch_sample_features(
    coords: list[tuple[float, float]],
) -> list[dict[str, torch.Tensor] | None]:
    """Batch-sample static features for many coordinates.

    Opens each GIS raster once per 10-degree region rather than once per
    coordinate, so this is efficient enough for heatmap-sized batches.
    """
    if _feature_names is None:
        return [None] * len(coords)
    try:
        import rasterio  # noqa: F401
    except ImportError:
        return [None] * len(coords)

    env_names: list[str] = _feature_names["env"]
    habitat_names: list[str] = _feature_names["habitat"]
    weather_dim: int = _input_dim - len(env_names) - len(habitat_names)

    needs_dem = _DEM_DERIVED & set(env_names)
    dem_results = _batch_compute_dem_derived(coords) if needs_dem else [{} for _ in coords]

    layer_vals: dict[str, list[float | None]] = {}
    for name in env_names:
        if name not in _DEM_DERIVED:
            layer_vals[name] = _batch_sample_raster(name, coords)
    for name in habitat_names:
        layer_vals[name] = _batch_sample_raster(name, coords)

    out: list[dict[str, torch.Tensor] | None] = []
    for i in range(len(coords)):
        ev: list[float] = []
        em: list[float] = []
        for name in env_names:
            val = dem_results[i].get(name) if name in _DEM_DERIVED else layer_vals[name][i]
            if val is None:
                ev.append(0.0)
                em.append(1.0)
            else:
                ev.append(val)
                em.append(0.0)
        hv: list[float] = []
        hm: list[float] = []
        for name in habitat_names:
            val = layer_vals[name][i]
            if val is None:
                hv.append(0.0)
                hm.append(1.0)
            else:
                hv.append(val)
                hm.append(0.0)

        features = ev + hv + [0.0] * weather_dim
        mask = em + hm + [1.0] * weather_dim
        ft = torch.tensor(features, dtype=torch.float32)
        mt = torch.tensor(mask, dtype=torch.float32)
        ft[mt > 0.5] = 0.0

        # Skip if every static feature is missing (e.g. ocean).
        static_missing = sum(mask[: len(env_names) + len(habitat_names)])
        if static_missing == len(env_names) + len(habitat_names):
            out.append(None)
        else:
            out.append({"features": ft, "mask": mt})
    return out


def load_bundle(path: str | Path) -> None:
    """Load an inference bundle into module-level singletons.

    Safe to call multiple times (reloads the bundle).  Should be called
    once during application startup.
    """
    global _bundle, _encoder, _heads, _cell_table, _cell_size_deg, _species_meta  # noqa: PLW0603
    global _feature_names, _input_dim  # noqa: PLW0603

    _lazy_import_models()

    loaded = torch.load(str(path), map_location="cpu", weights_only=False)
    if not isinstance(loaded, dict):
        raise ValueError("Invalid inference bundle: expected dict payload.")
    _bundle = loaded

    input_dim: int = loaded["input_dim"]
    embed_dim: int = loaded["embed_dim"]
    hidden_dim: int = loaded["hidden_dim"]
    _input_dim = input_dim

    if SharedEncoder is None or SpeciesHead is None:
        raise RuntimeError("Training model classes are unavailable.")

    encoder = SharedEncoder(input_dim, embed_dim=embed_dim, hidden_dim=hidden_dim)
    encoder.load_state_dict(loaded["encoder_state_dict"])
    encoder.eval()
    for p in encoder.parameters():
        p.requires_grad = False
    _encoder = encoder

    _heads = {}
    for sp_key, state in loaded["head_states"].items():
        head = SpeciesHead(embed_dim=embed_dim)
        head.load_state_dict(state)
        head.eval()
        for p in head.parameters():
            p.requires_grad = False
        _heads[int(sp_key)] = head

    _cell_table = loaded.get("cell_table", {})
    _cell_size_deg = loaded.get("cell_size_deg", 0.25)
    _species_meta = loaded.get("species_meta", {})
    _feature_names = loaded.get("feature_names")


def is_loaded() -> bool:
    """True when a bundle has been successfully loaded."""
    return _encoder is not None


def known_species() -> list[int]:
    """Return the list of species keys that have trained heads."""
    return sorted(_heads.keys())


def species_meta() -> dict[int, dict]:
    """Return per-species training metadata (prior, counts, val_loss)."""
    return dict(_species_meta)


def cell_count() -> int:
    """Return the number of cells in the loaded lookup table."""
    return len(_cell_table)


def _sigmoid(logit: float) -> float:
    """Numerically stable scalar sigmoid."""
    if logit >= 0:
        z = math.exp(-logit)
        return 1.0 / (1.0 + z)
    z = math.exp(logit)
    return z / (1.0 + z)


def _score_heads(
    embedding: torch.Tensor,
    heads_to_run: dict[int, torch.nn.Module],
    score_threshold: float,
) -> list[dict[str, Any]]:
    """Score an embedding against species heads and return sorted predictions."""
    results: list[dict[str, Any]] = []
    for sp_key, head in heads_to_run.items():
        logit = float(head(embedding).item())
        score = _sigmoid(logit)
        if score >= score_threshold:
            meta = _species_meta.get(sp_key, {})
            results.append({
                "species_key": sp_key,
                "score": round(score, 6),
                "prior": meta.get("prior_pi"),
            })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def predict(
    lat: float,
    lon: float,
    *,
    top_k: int = 0,
    species_filter: list[int] | None = None,
    score_threshold: float = 0.0,
) -> list[dict[str, Any]]:
    """Run inference for a single (lat, lon) coordinate.

    Args:
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        top_k: If >0, return only the top-k species by score.
        species_filter: If provided, only score these species keys.
        score_threshold: Minimum sigmoid score to include in results.

    Returns:
        Sorted list of dicts ``{species_key, score, prior}`` with the
        highest-scoring species first.  Returns an empty list when the
        coordinate falls outside all known cells and GIS rasters are
        unavailable.
    """
    if _encoder is None:
        raise RuntimeError("Inference bundle not loaded. Call load_bundle() first.")

    cell_id = _bin_id(lat, lon, _cell_size_deg)
    cell = _cell_table.get(cell_id)
    if cell is None:
        cell = _sample_point_features(lat, lon)
    if cell is None:
        return []

    features = cell["features"].unsqueeze(0)  # (1, input_dim)

    with torch.no_grad():
        embedding = _encoder(features)  # (1, embed_dim)

        heads_to_run = _heads
        if species_filter is not None:
            filter_set = set(species_filter)
            heads_to_run = {k: v for k, v in _heads.items() if k in filter_set}

        results = _score_heads(
            embedding,
            heads_to_run,
            score_threshold,
        )

    if top_k > 0:
        results = results[:top_k]
    return results


def predict_heatmap(
    species_key: int,
    bbox: tuple[float, float, float, float],
    *,
    resolution: float | None = None,
) -> dict[str, Any]:
    """Compute a probability grid for a single species over a bounding box.

    All native-resolution cells within the bounding box are scored in a
    single vectorized forward pass.  When *resolution* is larger than the
    model's native cell size the per-cell scores are averaged into coarser
    tiles, giving a zoom-dependent level of detail suitable for heat maps.

    Args:
        species_key: GBIF species key (must be in the loaded bundle).
        bbox: ``(min_lat, min_lon, max_lat, max_lon)`` in degrees.
        resolution: Output grid cell size in degrees.  Defaults to the
            model's native cell size (0.25 deg).  Values smaller than the
            native size are clamped up to native.

    Returns:
        A dict with:
        - ``species_key``: echoed input.
        - ``bbox``: echoed ``(min_lat, min_lon, max_lat, max_lon)``.
        - ``resolution``: output cell size actually used.
        - ``native_resolution``: the model's intrinsic cell size.
        - ``n_cells``: number of output cells with data.
        - ``cells``: list of ``{lat, lon, score, n_native}`` dicts.
          ``lat``/``lon`` are output-cell centers, ``score`` is the mean
          probability across contributing native cells, and ``n_native``
          is how many native cells were averaged.
    """
    if _encoder is None:
        raise RuntimeError("Inference bundle not loaded. Call load_bundle() first.")
    if species_key not in _heads:
        raise KeyError(f"Species {species_key} not in loaded bundle.")

    native = _cell_size_deg
    res = max(resolution if resolution is not None else native, native)
    min_lat, min_lon, max_lat, max_lon = bbox

    # Always iterate at native resolution so we hit the stored cell keys.
    nat_lat_lo = int(math.floor(min_lat / native))
    nat_lat_hi = int(math.floor(max_lat / native))
    nat_lon_lo = int(math.floor(min_lon / native))
    nat_lon_hi = int(math.floor(max_lon / native))

    feature_rows: list[torch.Tensor] = []
    # Map each native cell to its coarser output-tile key.
    tile_keys: list[tuple[int, int]] = []
    # Coordinates that missed the cell table and need GIS sampling.
    missing_coords: list[tuple[float, float]] = []
    missing_tile_keys: list[tuple[int, int]] = []

    for lat_bin in range(nat_lat_lo, nat_lat_hi + 1):
        for lon_bin in range(nat_lon_lo, nat_lon_hi + 1):
            center_lat = (lat_bin + 0.5) * native
            center_lon = (lon_bin + 0.5) * native
            tk = (
                int(math.floor(center_lat / res)),
                int(math.floor(center_lon / res)),
            )
            cid = f"cell_{lat_bin}_{lon_bin}"
            cell = _cell_table.get(cid)
            if cell is not None:
                feature_rows.append(cell["features"])
                tile_keys.append(tk)
            else:
                missing_coords.append((center_lat, center_lon))
                missing_tile_keys.append(tk)

    # Batch-sample static features for cells not in the cell table.
    if missing_coords:
        sampled = _batch_sample_features(missing_coords)
        for cell, tk in zip(sampled, missing_tile_keys):
            if cell is not None:
                feature_rows.append(cell["features"])
                tile_keys.append(tk)

    empty_result: dict[str, Any] = {
        "species_key": species_key,
        "bbox": list(bbox),
        "resolution": res,
        "native_resolution": native,
        "n_cells": 0,
        "cells": [],
    }

    if not feature_rows:
        return empty_result

    features = torch.stack(feature_rows)  # (N, input_dim)
    head = _heads[species_key]

    with torch.no_grad():
        embeddings = _encoder(features)   # (N, embed_dim)
        logits = head(embeddings)          # (N,) — head already squeezes
        scores = torch.sigmoid(logits)

    # Aggregate into output tiles (trivial 1-to-1 when res == native).
    tile_accum: dict[tuple[int, int], list[float]] = {}
    for key, s in zip(tile_keys, scores.tolist()):
        tile_accum.setdefault(key, []).append(s)

    cells_out: list[dict[str, Any]] = []
    for (t_lat, t_lon), tile_scores in sorted(tile_accum.items()):
        mean_score = sum(tile_scores) / len(tile_scores)
        cells_out.append({
            "lat": round((t_lat + 0.5) * res, 4),
            "lon": round((t_lon + 0.5) * res, 4),
            "score": round(mean_score, 6),
            "n_native": len(tile_scores),
        })

    return {
        "species_key": species_key,
        "bbox": list(bbox),
        "resolution": res,
        "native_resolution": native,
        "n_cells": len(cells_out),
        "cells": cells_out,
    }


def predict_batch(
    coordinates: list[tuple[float, float]],
    *,
    top_k: int = 0,
    species_filter: list[int] | None = None,
    score_threshold: float = 0.0,
) -> list[list[dict[str, Any]]]:
    """Run inference for multiple coordinates.

    Batches coordinates that fall in the same cell for efficiency.
    Returns one result list per input coordinate (same ordering).
    """
    if _encoder is None:
        raise RuntimeError("Inference bundle not loaded. Call load_bundle() first.")

    # Group by cell to avoid redundant encoder passes.
    cell_to_indices: dict[str, list[int]] = {}
    for idx, (lat, lon) in enumerate(coordinates):
        cid = _bin_id(lat, lon, _cell_size_deg)
        cell_to_indices.setdefault(cid, []).append(idx)

    output: list[list[dict[str, Any]]] = [[] for _ in coordinates]

    heads_to_run = _heads
    if species_filter is not None:
        filter_set = set(species_filter)
        heads_to_run = {k: v for k, v in _heads.items() if k in filter_set}

    with torch.no_grad():
        for cid, indices in cell_to_indices.items():
            cell = _cell_table.get(cid)
            if cell is None:
                # Try on-the-fly sampling from the first coordinate in this cell.
                ref_lat, ref_lon = coordinates[indices[0]]
                cell = _sample_point_features(ref_lat, ref_lon)
            if cell is None:
                continue

            features = cell["features"].unsqueeze(0)
            embedding = _encoder(features)

            results = _score_heads(
                embedding,
                heads_to_run,
                score_threshold,
            )
            if top_k > 0:
                results = results[:top_k]

            for idx in indices:
                output[idx] = results

    return output
