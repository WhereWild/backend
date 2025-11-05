# WhereWild

## What Is WhereWild?
WhereWild is a capstone project that combines wildlife sightings (for example, iNaturalist observations) with environmental context (elevation, climate, vegetation, human presence, etc.). Our goal is to give researchers and nature lovers a single place to explore why species show up where they do and how habitats change over time.

## How the System Fits Together
- **React Native app** (web/mobile) lets people browse the map, filter by species, and explore different layers.
- **FastAPI backend** handles requests, runs analyses, and talks to the Python data science stack (NumPy, Pandas, PyTorch).
- **Object storage** (cloud buckets or local storage) keeps the heavy-duty raster layers. Everything follows one shared grid so the datasets line up perfectly.
- **Lightweight database** stores references, metadata, and user settings. The big geospatial files stay out of SQL.

## Why the Grid Matters
- We picked a 100 m x 100 m grid that covers the continental U.S. (defined in `grid.json`). Every dataset we add later snaps to that grid so layers overlay cleanly.
- Elevation is the foundation: once the DEM is aligned, we derive slope/aspect/roughness (stacked into a single terrain raster) and warp other layers (precipitation, NDVI, land cover, etc.).
- We store aligned rasters as Cloud Optimized GeoTIFFs (COGs) because they’re fast to read, even over the network.
- Each dataset carries provenance in `manifest.csv` so we know the source URL, license, and when we downloaded it.

## What’s in This Repo?
```
WhereWild/
├── grid.json                # Canonical grid specification (CRS, bounds, pixel size)
├── regions.json             # Predefined cutouts (Salt Lake, Hounds Tooth, etc.)
├── Makefile                 # Automation entry points (download, warp, validate)
├── manifest.csv             # Provenance log (populated as datasets are ingested)
├── requirements.txt         # Python dependencies for data processing
├── scripts/
│   ├── download_dem.py      # Fetch USGS 3DEP tiles (parallel-aware)
│   ├── download_landcover.py# Fetch NLCD 2019 land cover mosaic (streamed ZIP)
│   ├── process_elevation.py # Mosaic + warp DEM tiles into the 100 m grid
│   ├── process_landcover.py # Warp NLCD land cover into the 100 m grid (COG)
│   ├── derive_terrain.py    # Build slope/aspect/roughness stack from the DEM
│   ├── extract_cutout.py    # Helper to clip rasters around a lat/lon center
│   ├── plot_quicklooks.py   # Render PNG previews for rasters (per band)
│   ├── build_feature_table.py # Export tidy Parquet feature tables per region
│   └── build_regions.py     # Generate configured cutouts (Salt Lake, etc.)
├── raw/                     # Cached source data (ignored by git)
└── processed/               # Aligned outputs (ignored by git)
```

## Setup
1. **Use a Linux-style shell.** Native Linux/macOS works out of the box. On Windows, install **WSL2** and run everything inside the WSL terminal.
2. **Install Make and Python 3.10+.** Most distros already have Python; add GNU Make if needed (`sudo apt-get install make` on Ubuntu/WSL).
3. **Install Python packages** (ideally in a virtualenv):
   ```bash
   pip install -r requirements.txt
   ```
   On Ubuntu/WSL you can alternatively install system packages:
   ```bash
   sudo apt-get install make python3-pyproj python3-rasterio
   pip install rio-cogeo  # optional, for COG output
   ```
4. **Verify Rasterio works** (`rio --version` or `python -c "import rasterio"`). If this fails, double-check GDAL is installed and visible in your PATH.

## Usage
### 1. Download Raw Elevation Tiles
```
make download-dem           # serial download
WORKERS=6 make download-dem # parallel downloads (recommended)
DRY_RUN=1 make download-dem # list tiles without downloading
```
- Tiles are cached under `raw/dem/` (one file per 1°×1° tile).
- Partial downloads are written to `.tif.part` and atomically renamed on completion.
- Each successful download appends a row to `manifest.csv` with source URL, license, and timestamp.

### 2. Build the Canonical DEM
```
make dem
```
- Mosaics all cached tiles, reprojects to EPSG:5070 with 100 m pixels, and writes `processed/dem_100m_cog.tif` (COG when `rio-cogeo` is installed; otherwise a compressed GeoTIFF).
- The derived product is logged to `manifest.csv` for provenance.

### 2b. Fetch Sample Species Observations (Optional)
```
OBS_SPECIES=escobaria_vivipara OBS_SPECIES_ID=148405 make download-observations
```
- Caches the raw iNaturalist responses under `raw/observations/<species>/<run_timestamp>/`.
- Projects each observation into the canonical grid and writes a presence table to `processed/observations/<species>/`.
- Customize filters with environment variables (e.g. `OBS_MAX_RECORDS=500`, `OBS_QUALITY_GRADE=needs_id`, `OBS_BBOX=49,-66,24,-125`).

### 3. Derive Terrain Layers
```
make terrain
```
- Generates a multi-band terrain stack (`processed/terrain/terrain_stack.tif`): band 1 slope (degrees), band 2 aspect (degrees, 0° = north, clockwise), band 3 3×3 roughness.
- Outputs share the 100 m grid specification so downstream features align without resampling.

### 4. Align NLCD Land Cover
```
make download-landcover  # downloads + extracts the NLCD mosaic (one-time)
make landcover           # warps NLCD into processed/landcover/landcover_100m_cog.tif
```
- Streams the NLCD 2019 CONUS land cover ZIP from MRLC, caches it in `raw/landcover/`, and extracts the GeoTIFF.
- Reprojects the categorical land cover codes into EPSG:5070 with nearest-neighbour resampling so class IDs stay intact.
- Logs both the raw ZIP and the processed COG to `manifest.csv` for provenance.

### 5. Generate Standard Cutouts (Optional)
```
make regions
```
- Clips the multi-band terrain stack into named regions defined in `regions.json` (e.g., Salt Lake Valley, Hounds Tooth) and writes them under `processed/cutouts/<region>/`.
- Extend `regions.json` with additional snapshots as needed.

### 6. Quick Visualization (Optional)
```
venv/bin/python scripts/plot_quicklooks.py
```
- Builds PNG heatmaps for the global DEM, the terrain stack (per band), and every configured cutout (auto-downsampled for convenience).
- Outputs live under `figures/quicklooks/<region>/` with filenames derived from the dataset and band names (no more `band3`).
- Skips files that already exist; pass `--overwrite` to regenerate, or `--discover`/`--rasters` for custom inputs.
- Multi-band rasters emit one PNG per band (e.g., slope, aspect, roughness).
- Tune preview resolution with `--max-size`.

### 7. Feature Tables (Optional)
```
make features
```
- Exports tidy Parquet tables under `processed/features/<region>.parquet` for every configured cutout (coordinates + terrain + land cover columns).
- Great for modeling workflows that prefer tabular features over rasters. Enable `--include-conus` in the script if you really need the full domain (beware: huge).

### 8. Validate (Placeholder)
```
make validate-dem
```
Hook for grid-alignment, statistics, and QA visualizations (to be implemented).

## Future Work
- Add more environmental layers (precipitation, temperature, NDVI, distance-to-water, human footprint) using the same download + warp workflow.
- Stand up validation scripts that check alignment, nodata coverage, and generate quick-look plots for QA.
- Store the processed rasters in shared object storage so the app/backend can stream them without redownloading.
- Enrich iNaturalist presence tables with weather, vegetation, and human footprint features so we can prototype habitat models quickly.

## Licensing & Attribution
- USGS 3DEP elevation tiles are public domain; we still keep attribution info in the manifest.
- Community datasets (e.g., iNaturalist) often use Creative Commons licenses—some allow non-commercial use only. Log license terms in `manifest.csv`, display attributions to users, and confirm permissions before sharing anything publicly.
- The project will remain non-commercial unless all sources permit it.

## Additional Resources
- Automation/AI agent instructions live in `docs/agent_context.md` (optional reading).
