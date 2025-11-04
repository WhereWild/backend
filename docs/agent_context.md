# Agent Context

## Mission
You are continuing work on WhereWild, a geospatial data platform that normalizes environmental datasets onto a shared 100 m EPSG:5070 grid for machine learning and visualization. The platform combines iNaturalist species observations with large-scale GIS layers (elevation, slope, land cover, climate, soil, etc.) to power analytics, forecasting, and interactive mapping experiences.

## Immediate Task
- Finalize and validate the elevation pipeline using the canonical grid specified in `grid.json`.
- Download USGS 3DEP 1″ elevation tiles, reproject them to the 100 m grid, and produce the baseline DEM (`processed/dem_100m_cog.tif`).
- Derive slope, aspect, and roughness from the aligned DEM as follow-up work.
- Ensure every dataset added to the repository is logged in `manifest.csv` with license and provenance details.

## Repository Expectations
- `grid.json` defines CRS, bounds, pixel size, nodata value, data type, and alignment policy. All derived layers must honor this specification.
- `raw/` holds immutable source tiles. `processed/` stores aligned outputs. Both directories are ignored by git—regenerate as needed.
- `scripts/download_dem.py` handles parallel tile ingestion from USGS. Respect partial download handling (`.tif.part` files) when resuming work.
- `scripts/process_elevation.py` builds the canonical DEM. Update it before generating derivatives.
- `Makefile` exposes standard entry points (`download-dem`, `dem`, `validate-dem`, `metadata`). Extend it when introducing new datasets.

## Licensing Notes
- USGS 3DEP elevation data is public domain. Record source URLs and attribution in the manifest.
- iNaturalist observations are Creative Commons (often non-commercial). The project will remain non-monetizable unless all downstream datasets permit it. Maintain attribution metadata for every source to avoid takedown risk.

## Collaboration Guidelines
- Avoid committing large binary rasters; keep raw downloads and processed outputs in external storage or regenerate locally.
- When adding new datasets, create dataset-specific download and processing scripts (or parameterize existing ones), update the Makefile, and document the workflow in the README.
- Keep validation scripts lightweight but thorough—check affine transforms, nodata distribution, histograms, and generate quick-look imagery when feasible.
