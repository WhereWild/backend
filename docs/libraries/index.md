# Libraries

This section documents the reusable modules in `util/`. Each page is generated
from module docstrings and stays in sync with the source.

Start with:

- `util.gis_lookup`: GIS layer metadata/legends, location catalog search, and location/taxa mappings.
- `util.summary_stats`: summary stats, categorical distributions, and index-backed slice queries.
- `util.indexing`: occurrence index builders plus relative ranking/KDE helpers.
- `util.taxa_navigation`: taxonomy traversal and occurrence parquet filters.
- `util.inference`: streaming heatmap inference engine for the Darwin SDM.
  Loads an inference bundle and exposes `predict_heatmap_stream()`. Supports
  on-the-fly GIS raster sampling for arbitrary heatmap coordinates not present
  in the pre-computed cell table.
- `util.tiles`: heatmap tile rendering helpers built on top of `util.inference`.
