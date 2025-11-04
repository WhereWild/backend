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
- Elevation is the foundation: once the DEM is aligned, we can derive slope/aspect/roughness and warp other layers (precipitation, NDVI, land cover, etc.).
- We store aligned rasters as Cloud Optimized GeoTIFFs (COGs) because they’re fast to read, even over the network.
- Each dataset carries provenance in `manifest.csv` so we know the source URL, license, and when we downloaded it.

## What’s in This Repo?
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

### 3. Validate (Placeholder)
```
make validate-dem
```
Hook for grid-alignment, statistics, and QA visualizations (to be implemented).

## Future Work
- Generate slope, aspect, and terrain roughness from the aligned DEM.
- Add more environmental layers (precipitation, temperature, NDVI, land cover, distance-to-water, human footprint) using the same download + warp workflow.
- Stand up validation scripts that check alignment, nodata coverage, and generate quick-look plots for QA.
- Store the processed rasters in shared object storage so the app/backend can stream them without redownloading.

## Licensing & Attribution
- USGS 3DEP elevation tiles are public domain; we still keep attribution info in the manifest.
- Community datasets (e.g., iNaturalist) often use Creative Commons licenses—some allow non-commercial use only. Log license terms in `manifest.csv`, display attributions to users, and confirm permissions before sharing anything publicly.
- The project will remain non-commercial unless all sources permit it.

## Additional Resources
- Automation/AI agent instructions live in `docs/agent_context.md` (optional reading).
