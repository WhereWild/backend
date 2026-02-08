"""
Build internal overviews for all region GeoTIFFs.

Usage (inside container or with rasterio installed):
  python scripts/build_overviews.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import os
import subprocess

import rasterio
from rasterio.enums import Resampling

from util.config import load_config
from util import gis_lookup


CONFIG = load_config("global")

FORCE_REBUILD_CATEGORICAL = True
FORCED_CATEGORICAL = {"landcover", "koppen_geiger"}


def _iter_tifs(root: Path) -> Iterable[Path]:
    return root.rglob("*.tif")


def _resolve_layer_id(path: Path, meta: dict[str, dict]) -> str | None:
    filename = path.name
    stem = path.stem

    # Direct stem match for templates like "{id}.tif"
    if stem in meta:
        return stem

    # Match fixed filename templates like "landcover.tif" / "dem.tif"
    for layer_id, entry in meta.items():
        if entry.get("derived"):
            continue
        template = entry.get("filename_template") or ""
        if "{id}" in template:
            continue
        if template == filename:
            return layer_id
    return None


def _is_categorical(layer_id: str | None, meta: dict[str, dict]) -> bool:
    if not layer_id:
        return False
    if layer_id in FORCED_CATEGORICAL:
        return True
    value_type = str(meta.get(layer_id, {}).get("value_type") or "").lower()
    return value_type == "categorical"


def _build_cog(
    src_path: Path,
    dst_path: Path,
    *,
    categorical: bool,
) -> None:
    resampling = "NEAREST" if categorical else "AVERAGE"
    cmd = [
        "gdal_translate",
        "-of",
        "COG",
        "-co",
        "COMPRESS=DEFLATE",
        "-co",
        "BIGTIFF=IF_SAFER",
        "-co",
        "OVERVIEWS=AUTO",
        "-co",
        f"OVERVIEW_RESAMPLING={resampling}",
    ]
    cmd.extend([str(src_path), str(dst_path)])
    subprocess.run(cmd, check=True)


def main() -> None:
    regions_root = CONFIG.gis_regions_root
    if not regions_root.exists():
        raise FileNotFoundError(f"Regions root not found: {regions_root}")

    meta = gis_lookup.load_layer_metadata()

    total = 0
    updated = 0
    skipped = 0

    for path in _iter_tifs(regions_root):
        total += 1
        try:
            layer_id = _resolve_layer_id(path, meta)
            categorical = _is_categorical(layer_id, meta)
            with rasterio.open(path) as ds:
                existing = ds.overviews(1) or []
                if existing and not (categorical and FORCE_REBUILD_CATEGORICAL):
                    skipped += 1
                    if skipped % 500 == 0:
                        print(f"[overview] skipped {skipped} files (already have overviews)")
                    continue
                if existing and categorical and FORCE_REBUILD_CATEGORICAL:
                    print(f"[overview] forcing categorical rebuild for {path.name}")

            tmp_path = path.with_suffix(path.suffix + ".tmp")
            _build_cog(path, tmp_path, categorical=categorical)
            os.replace(tmp_path, path)
            updated += 1
            if updated % 100 == 0:
                print(f"[overview] rebuilt {updated} files (last: {path.name})")
        except Exception as exc:
            print(f"[overview] failed {path}: {exc}")
            tmp_path = path.with_suffix(path.suffix + ".tmp")
            if tmp_path.exists():
                tmp_path.unlink()

    print(f"[overview] done total={total} updated={updated} skipped={skipped}")


if __name__ == "__main__":
    main()
