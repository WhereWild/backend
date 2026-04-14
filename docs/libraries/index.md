# Libraries

This section documents the reusable modules in `util/`. Each page is generated
from module docstrings and stays in sync with the source.

Start with:

- `util.gis_lookup`: GIS layer metadata/legends, location catalog search, and location/taxa mappings.
- `util.summary_stats`: summary stats, categorical distributions, and index-backed slice queries.
- `util.indexing`: occurrence index builders plus relative ranking/KDE helpers.
- `util.taxa_navigation`: taxonomy traversal and occurrence parquet filters.
- `util.inference`: bundle loading and runtime scoring helpers for the Darwin SDM.
  Loads an inference bundle used by the species heatmap tile endpoints and
  shared ranking utilities.
- `util.heatmap_tiles`: heatmap tile rendering helpers built on top of `util.inference`.
