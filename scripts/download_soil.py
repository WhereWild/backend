#!/usr/bin/env python3
from pathlib import Path
from typing import Iterator, Tuple
import tempfile

from owslib.wcs import WebCoverageService
import rasterio
from rasterio.merge import merge
import numpy as np

# Install with: pip install owslib

# SoilGrids services are property-specific
PROPERTY_SERVICES = {
    "sand": ("https://maps.isric.org/mapserv?map=/map/sand.map", "sand_0-5cm_mean"),
    "silt": ("https://maps.isric.org/mapserv?map=/map/silt.map", "silt_0-5cm_mean"),
    "clay": ("https://maps.isric.org/mapserv?map=/map/clay.map", "clay_0-5cm_mean"),
    "cfvo": ("https://maps.isric.org/mapserv?map=/map/cfvo.map", "cfvo_0-5cm_mean"),
    "phh2o": ("https://maps.isric.org/mapserv?map=/map/phh2o.map", "phh2o_0-5cm_mean"),
    "nitrogen": ("https://maps.isric.org/mapserv?map=/map/nitrogen.map", "nitrogen_0-5cm_mean"),
    "soc": ("https://maps.isric.org/mapserv?map=/map/soc.map", "soc_0-5cm_mean"),
}

# Bounding box (lon_min, lat_min, lon_max, lat_max); tweak if you want AK/HI, etc.
BBOX = (-125.0, 24.0, -66.0, 50.0)
RESOLUTION_DEG = 0.002245  # ~250 m native SoilGrids resolution
MAX_TILE_DEG = 8.0  # ensure width/height stay below WCS MAXSIZE limit
FORMAT_FALLBACK = "GeoTIFF"


def iter_tiles(bbox: Tuple[float, float, float, float], max_span: float) -> Iterator[Tuple[float, float, float, float]]:
    """Yield sub-bboxes (lon_min, lat_min, lon_max, lat_max) no larger than max_span degrees."""
    lon_min, lat_min, lon_max, lat_max = bbox
    lon = lon_min
    while lon < lon_max - 1e-9:
        tile_max_lon = min(lon + max_span, lon_max)
        lat = lat_min
        while lat < lat_max - 1e-9:
            tile_max_lat = min(lat + max_span, lat_max)
            yield (lon, lat, tile_max_lon, tile_max_lat)
            lat = tile_max_lat
        lon = tile_max_lon

OUTPUT_DIR = Path("raw/soil_texture")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for name, (base_url, coverage_id) in PROPERTY_SERVICES.items():
    out_path = OUTPUT_DIR / f"{name}.tif"

    print(f"Requesting {coverage_id} from {base_url}")
    wcs = WebCoverageService(base_url, version="1.0.0")

    coverage_info = wcs.contents[coverage_id]
    fmt = next((fmt for fmt in coverage_info.supportedFormats if "tiff" in fmt.lower()), FORMAT_FALLBACK)

    temp_paths = []
    with tempfile.TemporaryDirectory(prefix=f"{name}_tiles_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        for idx, tile_bbox in enumerate(iter_tiles(BBOX, MAX_TILE_DEG), start=1):
            print(f"  tile {idx}: bbox={tile_bbox}")
            response = wcs.getCoverage(
                identifier=coverage_id,
                bbox=tile_bbox,
                crs="EPSG:4326",
                resx=RESOLUTION_DEG,
                resy=RESOLUTION_DEG,
                format=fmt,
            )
            tile_path = tmpdir_path / f"{name}_tile_{idx}.tif"
            with open(tile_path, "wb") as fp:
                fp.write(response.read())
            temp_paths.append(tile_path)

        datasets = [rasterio.open(path) for path in temp_paths]
        try:
            mosaic, transform = merge(datasets, method="first")
            profile = datasets[0].profile
            profile.update(
                {
                    "height": mosaic.shape[1],
                    "width": mosaic.shape[2],
                    "transform": transform,
                    "compress": "deflate",
                    "nodata": datasets[0].nodata if datasets[0].nodata is not None else np.nan,
                }
            )
        finally:
            for ds in datasets:
                ds.close()

        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(mosaic)
    print(f"  wrote {out_path}")
