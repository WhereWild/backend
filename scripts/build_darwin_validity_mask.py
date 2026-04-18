"""Build Darwin serving-validity masks from regional landcover rasters.

The first version is intentionally narrow: a pixel is marked valid when the
regional ``landcover.tif`` has a real value there. This mirrors the current
Darwin runtime prefilter, which uses landcover as the single serving gate.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio

from util.config import load_config


CONFIG = load_config("global")
LANDCOVER_FILENAME = "landcover.tif"
MASK_FILENAME = "darwin_validity_mask.tif"


@dataclass(frozen=True)
class MaskAuditSummary:
    coord_count: int
    mask_keep_count: int
    landcover_keep_count: int
    matched_count: int
    false_negative_count: int
    false_positive_count: int


def _iter_region_dirs(regions_root: Path) -> list[Path]:
    return sorted(path for path in regions_root.iterdir() if path.is_dir())


def _validity_mask_from_band(band: np.ma.MaskedArray) -> np.ndarray:
    """Return a uint8 validity mask where 1 means the source pixel is usable."""
    mask = np.ma.getmaskarray(band)
    valid = ~mask
    return valid.astype(np.uint8, copy=False)


def _sample_region_raster_values(
    coords: list[tuple[float, float]],
    *,
    regions_root: Path,
    filename: str,
) -> list[float | None]:
    """Sample one region-local raster filename at the provided coordinates."""
    import math

    results: list[float | None] = [None] * len(coords)
    by_region: dict[str, list[tuple[int, float, float]]] = {}
    for idx, (lat, lon) in enumerate(coords):
        region_name = f"lat{int(math.floor(lat / 10.0) * 10)}_lon{int(math.floor(lon / 10.0) * 10)}"
        by_region.setdefault(region_name, []).append((idx, lat, lon))

    for region_name, members in by_region.items():
        raster_path = regions_root / region_name / filename
        if not raster_path.exists():
            continue
        with rasterio.open(raster_path) as ds:
            nodata = ds.nodata
            xy = [(lon, lat) for _, lat, lon in members]
            indices = [idx for idx, _, _ in members]
            for arr, idx in zip(ds.sample(xy), indices, strict=True):
                value = arr[0]
                if nodata is not None and value == nodata:
                    continue
                if isinstance(value, float) and value != value:
                    continue
                if np.isnan(value):
                    continue
                results[idx] = float(value)
    return results


def audit_mask_against_landcover(
    coords: list[tuple[float, float]],
    *,
    regions_root: Path,
) -> MaskAuditSummary:
    """Compare mask keep/drop decisions against the landcover gate."""
    mask_values = _sample_region_raster_values(coords, regions_root=regions_root, filename=MASK_FILENAME)
    landcover_values = _sample_region_raster_values(coords, regions_root=regions_root, filename=LANDCOVER_FILENAME)

    mask_keep = [value is not None and float(value) > 0.0 for value in mask_values]
    landcover_keep = [value is not None for value in landcover_values]
    matched_count = sum(left == right for left, right in zip(mask_keep, landcover_keep, strict=True))
    false_negative_count = sum((not left) and right for left, right in zip(mask_keep, landcover_keep, strict=True))
    false_positive_count = sum(left and (not right) for left, right in zip(mask_keep, landcover_keep, strict=True))
    return MaskAuditSummary(
        coord_count=len(coords),
        mask_keep_count=sum(mask_keep),
        landcover_keep_count=sum(landcover_keep),
        matched_count=matched_count,
        false_negative_count=false_negative_count,
        false_positive_count=false_positive_count,
    )


def _mask_profile_from_source(profile: dict) -> dict:
    """Build an output profile for the validity mask raster."""
    out_profile = profile.copy()
    out_profile.update(
        count=1,
        dtype="uint8",
        nodata=0,
        compress="deflate",
    )
    return out_profile


def write_region_validity_mask(
    landcover_path: Path,
    output_path: Path,
    *,
    overwrite: bool = False,
) -> bool:
    """Write one region validity mask aligned to a regional landcover raster.

    Returns True when a file was written and False when the output already
    exists and overwrite is disabled.
    """
    if output_path.exists() and not overwrite:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(landcover_path) as src:
        band = src.read(1, masked=True)
        mask = _validity_mask_from_band(band)
        profile = _mask_profile_from_source(src.profile)

    with tempfile.NamedTemporaryFile(
        dir=output_path.parent,
        prefix=f"{output_path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)

    try:
        with rasterio.open(tmp_path, "w", **profile) as dst:
            dst.write(mask, 1)
        os.replace(tmp_path, output_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
    return True


def build_all_region_validity_masks(
    *,
    regions_root: Path,
    overwrite: bool = False,
) -> tuple[int, int, int]:
    """Build masks for every regional landcover tile.

    Returns ``(written, skipped, missing_landcover)``.
    """
    written = 0
    skipped = 0
    missing_landcover = 0

    for region_dir in _iter_region_dirs(regions_root):
        landcover_path = region_dir / LANDCOVER_FILENAME
        output_path = region_dir / MASK_FILENAME
        if not landcover_path.exists():
            missing_landcover += 1
            print(f"[darwin-mask] missing landcover: {landcover_path}")
            continue
        if write_region_validity_mask(landcover_path, output_path, overwrite=overwrite):
            written += 1
            print(f"[darwin-mask] wrote {output_path}")
        else:
            skipped += 1
            print(f"[darwin-mask] skipped existing {output_path}")

    return written, skipped, missing_landcover


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--regions-root",
        type=Path,
        default=CONFIG.gis_regions_root,
        help="Root directory containing regional GIS tiles.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rewrite existing darwin_validity_mask.tif outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    regions_root = args.regions_root.expanduser().resolve()
    if not regions_root.exists():
        raise FileNotFoundError(f"Regions root not found: {regions_root}")

    written, skipped, missing_landcover = build_all_region_validity_masks(
        regions_root=regions_root,
        overwrite=bool(args.overwrite),
    )
    print(f"[darwin-mask] done written={written} skipped={skipped} missing_landcover={missing_landcover}")


if __name__ == "__main__":
    main()
