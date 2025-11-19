# WhereWild data pipeline

Tools for downloading raster sources and reprojecting them onto a canonical grid (EPSG:5070, 100 m pixels by default).

## Canonical grid
- Specified in `grid.json` (crs `EPSG:5070`, pixel size `100`, bounds `[-3100000, 200000, 2900000, 3700000]`, `nodata=-9999`, `dtype=float32`).
- `reproject_gis.py` defaults to this grid if `--grid` is omitted.

## Quickstart (one command)
1) Build the Docker image once:
   ```
   docker compose build gdal
   ```
2) Run the end-to-end helper (downloads DEM tiles and reprojects them):
   ```
   ./scripts/bootstrap_data.sh
   ```
   - Downloads USGS 1″ DEM tiles into `raw/dem/` (skips tiles already present, cleans up partials, renames to `dem_lat{lat}_lon{lon}.tif`).
   - Creates `data/dem_canonical.tif` as a COG on the canonical grid (skips if it already exists unless `FORCE_REPROJECT=1`).
   - Environment overrides: `GRID`, `RAW_DIR`, `DST_DEM`, `WORKERS`, `RESAMPLING`, `OVERVIEWS`, `SKIP_DOWNLOAD`, `SKIP_REPROJECT`, `FORCE_REPROJECT`.

## Manual commands
- Download DEM tiles only:
  ```
  docker compose run --rm gdal \
    python download_dem.py --grid grid.json --raw-dir raw --workers 4
  ```
- Reproject an existing set of tiles to the grid:
  ```
  docker compose run --rm gdal \
    python reproject_gis.py \
      --src-dir raw/dem \
      --dst data/dem_canonical.tif \
      --grid grid.json \
      --resampling bilinear
  ```
  - Also accepts `--src <file-or-vrt>` or `--src-files <list>` and builds overviews by default.

## Notes
- The Docker image bundles GDAL/rasterio/pyproj/geopandas (see `Dockerfile` and `requirements.txt`).
- Data produced by these scripts is not checked into git.
