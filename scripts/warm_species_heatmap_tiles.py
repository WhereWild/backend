"""Warm classic and Darwin species heatmap caches for recommended taxa.

This script intentionally targets the existing classic-model species set,
which is the same source the current recommendation seed uses. It fills the
existing classic and Darwin tile disk caches by calling the live scorer entry
points directly rather than going through HTTP.

Defaults:
- Focus region: continental US (`--region conus`)
- Zooms: 5 through 10
- Weather window: current conditions (`--forecast-hours 0`)

Running:
- `pd warm_species_heatmap_tiles --verbose` runs it in the foreground.
- `pdb warm_species_heatmap_tiles --verbose` runs it in the background and logs
    to `logs/scripts/warm_species_heatmap_tiles.log`.

Logging:
- The script always emits a final summary line with taxa and tile counts.
- `--verbose` enables info-level logs for skip reasons.
- `--dry-run` implies info-level logging and emits each planned tile without
    rendering it.
- Darwin bundle load failures and tile render failures are logged with stack
    traces.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import logging
import math
import os
from pathlib import Path
from typing import Iterable, Sequence

from util.config import load_config
from util import inference, models, taxa_navigation
from util.species_heatmap_scorers import ClassicSpeciesHeatmapScorer, DarwinSpeciesHeatmapScorer


LOGGER = logging.getLogger(__name__)
CONFIG = load_config("global")
SUPPORTED_RENDERERS = ("classic", "darwin")
RegionBBox = tuple[float, float, float, float] | None
OccurrencePoint = dict[str, float | str]

_MAX_MERCATOR_LAT = 85.05112878
DEFAULT_TILE_SIZE = int(getattr(CONFIG, "sdm_tile_size", 256))
DEFAULT_CLASSIC_MAX_NATIVE_ZOOM = 10
DEFAULT_DARWIN_MAX_NATIVE_ZOOM = int(getattr(CONFIG, "sdm_tile_max_native_zoom", 8))
DEFAULT_ZOOMS = tuple(range(5, 11))
DEFAULT_PADDING_DEGREES = 0.5
DEFAULT_MAX_TILES_PER_ZOOM = 8
DEFAULT_FORECAST_HOURS = 0
CONUS_FOCUS_BBOX = (24.396308, -124.848974, 49.384358, -66.885444)
FOCUS_REGION_BBOXES: dict[str, RegionBBox] = {
    "conus": CONUS_FOCUS_BBOX,
    "global": None,
}


@dataclass(frozen=True)
class WarmTile:
    z: int
    x: int
    y: int


@dataclass
class WarmStats:
    taxa_considered: int = 0
    taxa_with_tiles: int = 0
    planned_jobs: int = 0
    attempted_jobs: int = 0
    succeeded_jobs: int = 0
    failed_jobs: int = 0
    skipped_no_points: int = 0
    skipped_classic_unavailable: int = 0
    skipped_darwin_unavailable: int = 0


def _dedupe_taxon_ids(taxon_ids: Iterable[int]) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for taxon_id in taxon_ids:
        normalized = int(taxon_id)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def resolve_target_taxa(
    taxon_ids: Sequence[int] | None = None,
    *,
    limit: int | None = None,
) -> list[int]:
    source = taxon_ids if taxon_ids else models.get_all_sdm_taxon_ids()
    resolved = _dedupe_taxon_ids(source)
    if limit is not None:
        return resolved[: max(0, int(limit))]
    return resolved


def _resolve_renderers(renderers: Sequence[str]) -> tuple[str, ...]:
    selected = tuple(dict.fromkeys(renderer.strip().lower() for renderer in renderers if renderer.strip()))
    if not selected:
        raise ValueError("At least one renderer must be provided")
    unsupported = [renderer for renderer in selected if renderer not in SUPPORTED_RENDERERS]
    if unsupported:
        raise ValueError(f"Unsupported renderer(s): {', '.join(unsupported)}")
    return selected


def _clamp_lat(lat: float) -> float:
    return max(-_MAX_MERCATOR_LAT, min(_MAX_MERCATOR_LAT, float(lat)))


def _normalize_lon(lon: float) -> float:
    wrapped = ((float(lon) + 180.0) % 360.0) - 180.0
    if wrapped == -180.0 and lon > 0:
        return 180.0
    return wrapped


def _lon_to_tile_x(lon: float, z: int) -> int:
    tiles_per_axis = 2**z
    normalized = (_normalize_lon(lon) + 180.0) / 360.0
    return min(max(int(math.floor(normalized * tiles_per_axis)), 0), tiles_per_axis - 1)


def _lat_to_tile_y(lat: float, z: int) -> int:
    tiles_per_axis = 2**z
    clamped = _clamp_lat(lat)
    lat_rad = math.radians(clamped)
    mercator = math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0))
    normalized = (1.0 - (mercator / math.pi)) / 2.0
    return min(max(int(math.floor(normalized * tiles_per_axis)), 0), tiles_per_axis - 1)


def _bbox_from_points(
    points: Sequence[OccurrencePoint],
    *,
    padding_degrees: float = DEFAULT_PADDING_DEGREES,
) -> tuple[float, float, float, float] | None:
    latitudes: list[float] = []
    longitudes: list[float] = []
    for point in points:
        lat = point.get("latitude")
        lon = point.get("longitude")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        if not math.isfinite(float(lat)) or not math.isfinite(float(lon)):
            continue
        latitudes.append(_clamp_lat(float(lat)))
        longitudes.append(_normalize_lon(float(lon)))
    if not latitudes or not longitudes:
        return None

    min_lat = _clamp_lat(min(latitudes) - padding_degrees)
    max_lat = _clamp_lat(max(latitudes) + padding_degrees)
    min_lon = max(-180.0, min(longitudes) - padding_degrees)
    max_lon = min(180.0, max(longitudes) + padding_degrees)
    return min_lat, min_lon, max_lat, max_lon


def _intersect_bboxes(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> tuple[float, float, float, float] | None:
    min_lat = max(left[0], right[0])
    min_lon = max(left[1], right[1])
    max_lat = min(left[2], right[2])
    max_lon = min(left[3], right[3])
    if min_lat > max_lat or min_lon > max_lon:
        return None
    return min_lat, min_lon, max_lat, max_lon


def plan_species_tiles_from_points(
    points: Sequence[OccurrencePoint],
    *,
    zooms: Sequence[int] = DEFAULT_ZOOMS,
    padding_degrees: float = DEFAULT_PADDING_DEGREES,
    max_tiles_per_zoom: int = DEFAULT_MAX_TILES_PER_ZOOM,
    focus_bbox: RegionBBox = CONUS_FOCUS_BBOX,
) -> list[WarmTile]:
    bbox = _bbox_from_points(points, padding_degrees=padding_degrees)
    if bbox is None:
        return []
    if focus_bbox is not None:
        bbox = _intersect_bboxes(bbox, focus_bbox)
        if bbox is None:
            return []

    min_lat, min_lon, max_lat, max_lon = bbox
    center_lat = (min_lat + max_lat) / 2.0
    center_lon = (min_lon + max_lon) / 2.0
    planned: list[WarmTile] = []
    for z in zooms:
        min_x = _lon_to_tile_x(min_lon, z)
        max_x = _lon_to_tile_x(max_lon, z)
        min_y = _lat_to_tile_y(max_lat, z)
        max_y = _lat_to_tile_y(min_lat, z)
        tiles = [WarmTile(z=z, x=x, y=y) for x in range(min_x, max_x + 1) for y in range(min_y, max_y + 1)]
        if len(tiles) > max_tiles_per_zoom:
            center_x = _lon_to_tile_x(center_lon, z)
            center_y = _lat_to_tile_y(center_lat, z)
            tiles = sorted(
                tiles,
                key=lambda tile: (abs(tile.x - center_x) + abs(tile.y - center_y), tile.y, tile.x),
            )[:max_tiles_per_zoom]
        planned.extend(sorted(tiles, key=lambda tile: (tile.z, tile.y, tile.x)))
    return planned


def plan_species_tiles_for_taxon(
    taxon_id: int,
    *,
    zooms: Sequence[int] = DEFAULT_ZOOMS,
    padding_degrees: float = DEFAULT_PADDING_DEGREES,
    max_tiles_per_zoom: int = DEFAULT_MAX_TILES_PER_ZOOM,
    focus_bbox: RegionBBox = CONUS_FOCUS_BBOX,
) -> list[WarmTile]:
    return plan_species_tiles_from_points(
        taxa_navigation.load_occurrence_points(int(taxon_id)),
        zooms=zooms,
        padding_degrees=padding_degrees,
        max_tiles_per_zoom=max_tiles_per_zoom,
        focus_bbox=focus_bbox,
    )


def _resolve_inference_bundle_path() -> Path:
    bundle_path = Path(os.environ.get("WHEREWILD_INFERENCE_BUNDLE", "checkpoints/inference_bundle.pt"))
    if bundle_path.is_absolute():
        return bundle_path
    return CONFIG.project_root / bundle_path


def ensure_darwin_bundle_loaded() -> bool:
    if inference.is_loaded():
        return True
    bundle_path = _resolve_inference_bundle_path()
    if not bundle_path.exists():
        LOGGER.warning("[warm-tiles] Darwin bundle missing at %s", bundle_path)
        return False
    try:
        inference.load_bundle(bundle_path)
    except Exception:
        LOGGER.exception("[warm-tiles] failed to load Darwin bundle from %s", bundle_path)
        return False
    return True


def warm_species_tiles(
    taxon_ids: Sequence[int],
    *,
    renderers: Sequence[str] = ("classic", "darwin"),
    zooms: Sequence[int] = DEFAULT_ZOOMS,
    padding_degrees: float = DEFAULT_PADDING_DEGREES,
    max_tiles_per_zoom: int = DEFAULT_MAX_TILES_PER_ZOOM,
    focus_bbox: RegionBBox = CONUS_FOCUS_BBOX,
    tile_size: int = DEFAULT_TILE_SIZE,
    forecast_hours: int = DEFAULT_FORECAST_HOURS,
    dry_run: bool = False,
    max_failures: int = 20,
) -> WarmStats:
    selected_renderers = _resolve_renderers(renderers)
    stats = WarmStats(taxa_considered=len(taxon_ids))
    classic_scorer = None
    if "classic" in selected_renderers:
        classic_scorer = ClassicSpeciesHeatmapScorer(
            model_id=models.DEFAULT_MODEL_ID,
            reproject=True,
            forecast_hours=forecast_hours,
            apply_phenology=True,
            phenology_only=False,
            max_tile_size=int(getattr(CONFIG, "sdm_tile_max_size", 2048)),
        )
    darwin_ready = "darwin" not in selected_renderers or ensure_darwin_bundle_loaded()
    darwin_scorer = None
    if "darwin" in selected_renderers:
        darwin_scorer = DarwinSpeciesHeatmapScorer(
            feature_mode="prefer_cell_table",
            forecast_hours=forecast_hours,
            max_tile_size=int(getattr(CONFIG, "sdm_tile_max_size", 2048)),
        )

    for taxon_id in taxon_ids:
        normalized_taxon_id = int(taxon_id)
        planned_tiles = plan_species_tiles_for_taxon(
            normalized_taxon_id,
            zooms=zooms,
            padding_degrees=padding_degrees,
            max_tiles_per_zoom=max_tiles_per_zoom,
            focus_bbox=focus_bbox,
        )
        if not planned_tiles:
            stats.skipped_no_points += 1
            LOGGER.info("[warm-tiles] skip taxon_id=%s reason=no_occurrence_points", taxon_id)
            continue

        stats.taxa_with_tiles += 1
        for renderer in selected_renderers:
            scorer: ClassicSpeciesHeatmapScorer | DarwinSpeciesHeatmapScorer
            if renderer == "classic":
                if not models.has_sdm_model(normalized_taxon_id):
                    stats.skipped_classic_unavailable += 1
                    LOGGER.info("[warm-tiles] skip taxon_id=%s renderer=classic reason=unavailable", taxon_id)
                    continue
                if classic_scorer is None:
                    raise RuntimeError("Classic renderer selected without an initialized classic scorer")
                scorer = classic_scorer
                max_native_zoom = DEFAULT_CLASSIC_MAX_NATIVE_ZOOM
            elif renderer == "darwin":
                if not darwin_ready or not inference.has_species(normalized_taxon_id):
                    stats.skipped_darwin_unavailable += 1
                    LOGGER.info("[warm-tiles] skip taxon_id=%s renderer=darwin reason=unavailable", taxon_id)
                    continue
                if darwin_scorer is None:
                    raise RuntimeError("Darwin renderer selected without an initialized Darwin scorer")
                scorer = darwin_scorer
                max_native_zoom = DEFAULT_DARWIN_MAX_NATIVE_ZOOM
            else:
                raise ValueError(f"Unsupported renderer: {renderer}")

            for tile in planned_tiles:
                stats.planned_jobs += 1
                if dry_run:
                    LOGGER.info(
                        "[warm-tiles] dry-run taxon_id=%s renderer=%s z=%s x=%s y=%s",
                        taxon_id,
                        renderer,
                        tile.z,
                        tile.x,
                        tile.y,
                    )
                    continue
                try:
                    stats.attempted_jobs += 1
                    scorer.render_runtime_tile_bytes(
                        normalized_taxon_id,
                        tile.z,
                        tile.x,
                        tile.y,
                        tile_size=tile_size,
                        max_native_zoom=max_native_zoom,
                    )
                    stats.succeeded_jobs += 1
                except Exception:
                    stats.failed_jobs += 1
                    LOGGER.exception(
                        "[warm-tiles] failed taxon_id=%s renderer=%s z=%s x=%s y=%s",
                        taxon_id,
                        renderer,
                        tile.z,
                        tile.x,
                        tile.y,
                    )
                    if stats.failed_jobs >= max_failures:
                        raise RuntimeError(
                            f"Aborting warm run after {stats.failed_jobs} failures (max_failures={max_failures})"
                        )

    return stats


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taxon-id", dest="taxon_ids", type=int, action="append", help="Specific taxon id to warm.")
    parser.add_argument("--limit", type=int, default=None, help="Limit how many recommendation taxa to warm.")
    parser.add_argument(
        "--renderer",
        choices=SUPPORTED_RENDERERS + ("both",),
        default="both",
        help="Which renderer caches to warm.",
    )
    parser.add_argument(
        "--zoom",
        dest="zooms",
        type=int,
        action="append",
        default=None,
        help="Zoom level to warm. Repeat to specify multiple zooms.",
    )
    parser.add_argument(
        "--region",
        choices=tuple(FOCUS_REGION_BBOXES.keys()),
        default="conus",
        help="Focus the warm run on a geographic region.",
    )
    parser.add_argument(
        "--forecast-hours",
        type=int,
        default=DEFAULT_FORECAST_HOURS,
        help="Weather forecast offset in hours (0 = current conditions).",
    )
    parser.add_argument("--max-tiles-per-zoom", type=int, default=DEFAULT_MAX_TILES_PER_ZOOM)
    parser.add_argument("--padding-degrees", type=float, default=DEFAULT_PADDING_DEGREES)
    parser.add_argument("--tile-size", type=int, default=DEFAULT_TILE_SIZE)
    parser.add_argument("--max-failures", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true", help="Plan work without rendering tiles.")
    parser.add_argument("--verbose", action="store_true", help="Enable info-level logging.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose or args.dry_run else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    zooms = tuple(args.zooms) if args.zooms else DEFAULT_ZOOMS
    renderers = ("classic", "darwin") if args.renderer == "both" else (args.renderer,)
    focus_bbox = FOCUS_REGION_BBOXES[args.region]
    taxon_ids = resolve_target_taxa(args.taxon_ids, limit=args.limit)
    stats = warm_species_tiles(
        taxon_ids,
        renderers=renderers,
        zooms=zooms,
        padding_degrees=args.padding_degrees,
        max_tiles_per_zoom=args.max_tiles_per_zoom,
        focus_bbox=focus_bbox,
        tile_size=args.tile_size,
        forecast_hours=args.forecast_hours,
        dry_run=args.dry_run,
        max_failures=args.max_failures,
    )
    LOGGER.warning(
        "[warm-tiles] taxa_considered=%s taxa_with_tiles=%s planned_jobs=%s attempted_jobs=%s succeeded_jobs=%s failed_jobs=%s skipped_no_points=%s skipped_classic_unavailable=%s skipped_darwin_unavailable=%s",
        stats.taxa_considered,
        stats.taxa_with_tiles,
        stats.planned_jobs,
        stats.attempted_jobs,
        stats.succeeded_jobs,
        stats.failed_jobs,
        stats.skipped_no_points,
        stats.skipped_classic_unavailable,
        stats.skipped_darwin_unavailable,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
