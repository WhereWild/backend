# WhereWild

## Overview
WhereWild is a geospatial data platform that fuses biodiversity observations (e.g., iNaturalist) with large-scale environmental layers—elevation, climate, land cover, soil, and more—to model and visualize species presence and habitat characteristics. The system supports both a React Native front end for exploration and a Python/FastAPI back end for analytics and machine-learning experiments.

## Architecture Snapshot
- **Frontend:** React Native web/mobile for map visualization and user interaction.
- **Backend:** FastAPI with Python analytics stack (NumPy, Pandas, PyTorch).
- **Object Storage:** Rasterized environmental layers aligned to a canonical grid.
- **Database:** Lightweight metadata and user preferences; bulk spatial data lives in object storage.

## Data Strategy
- Normalize all Tier 1 environmental datasets (elevation, slope, aspect, roughness, land cover, NDVI, precipitation, temperature, distance-to-water, human footprint) onto a shared 100 m grid.
- Target region: continental United States.
- Canonical projection: EPSG:5070 (US Albers Equal Area).
- Storage format: Cloud-Optimized GeoTIFF (COG) or GeoParquet for efficient spatial querying.
- Quantization guidance: elevation as float32/uint16; slope/aspect/roughness as uint8; categorical layers as uint8.

## Current Focus
Establish the master 100 m DEM that defines pixel alignment, grid origin, and CRS for every other dataset.
1. Download USGS 3DEP 1″ (~30 m) elevation tiles covering CONUS.
2. Reproject/mosaic the tiles to the canonical grid defined in `grid.json`.
3. Produce a compressed COG and record provenance in `manifest.csv`.
4. Use this aligned DEM as the baseline for derived products (slope, aspect, roughness) and future Tier 1 layers.

## Repository Layout
```
WhereWild/
├── grid.json                # Canonical grid specification (CRS, bounds, pixel size)
├── Makefile                 # Automation entry points (download, warp, validate)
├── manifest.csv             # Provenance log (populated as datasets are ingested)
├── requirements.txt         # Python dependencies for data processing
├── scripts/
│   ├── download_dem.py      # Fetch USGS 3DEP tiles (parallel-aware)
│   └── process_elevation.py # Mosaic + warp DEM tiles into the 100 m grid
├── raw/                     # Cached source data (ignored by git)
└── processed/               # Aligned outputs (ignored by git)
```

## Setup
1. Prefer Linux or WSL
2. Ensure GNU Make and Python 3.10+ are available.
3. Install Python dependencies (virtual environment recommended):
   ```bash
   pip install -r requirements.txt
   ```
   On Ubuntu/WSL you can alternatively install system packages:
   ```bash
   sudo apt-get install make python3-pyproj python3-rasterio
   pip install rio-cogeo  # optional, for COG output
   ```
4. Confirm GDAL/Rasterio can open GeoTIFFs (`rio --version` or `python -c "import rasterio"`).

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

### 3. Validate (Placeholder)
```
make validate-dem
```
Hook for grid-alignment, statistics, and QA visualizations (to be implemented).

## Future Work
- Derive slope, aspect, and roughness from the aligned DEM.
- Warp additional Tier 1 layers (precipitation, temperature, NDVI, land cover, distance-to-water, human footprint) to the canonical grid.
- Store curated outputs in object storage and maintain a comprehensive dataset manifest.
- Build automated validation checks (affine alignment, histograms, hillshades) for every dataset.

## Licensing & Attribution
- USGS 3DEP tiles are public domain; retain attribution when publishing derivatives.
- iNaturalist and other community datasets may carry Creative Commons licenses (often non-commercial). Track license terms in `manifest.csv`, surface attributions in the UI, and ensure compliance before open-sourcing or distributing data.

## Additional Resources
- Automation/AI agent instructions are maintained in `docs/agent_context.md`.
