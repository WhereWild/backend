# API

This section documents the backend HTTP API. The public interface is defined in
`main.py`, which exposes FastAPI routes that wrap the core `util/` libraries.

This page is a curated overview so the API documentation lives alongside the
library and script docs. The default FastAPI page (at `/docs` when running
locally) may still contain useful information not present here.

## Prediction Endpoints

These endpoints require an inference bundle to be loaded at startup. Set the
`WHEREWILD_INFERENCE_BUNDLE` env var, or place the bundle at
`checkpoints/inference_bundle.pt`.

### `GET /api/predict`

Predict species suitability for a single coordinate.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `lat` | float | required | Latitude (-90 to 90). |
| `lon` | float | required | Longitude (-180 to 180). |
| `top_k` | int | 20 | Maximum species to return. |
| `threshold` | float | 0.0 | Minimum sigmoid score to include. |

Returns ranked `{species_key, score, prior}` dicts. Works for any land
coordinate: pre-computed cells are used when available, otherwise static GIS
features (bioclim, terrain, landcover) are sampled on the fly from local COG
tiles.

### `GET /api/predict/batch`

Batch prediction for up to 100 coordinates.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `coords` | string | required | Comma-separated lat,lon pairs (e.g. `25.0,-100.0,26.5,-99.0`). |
| `top_k` | int | 20 | Maximum species per coordinate. |
| `threshold` | float | 0.0 | Minimum sigmoid score. |

Coordinates that fall in the same cell share a single encoder pass.

### `GET /api/predict/heatmap`

Compute a probability grid for one species over a bounding box.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `species_key` | int | required | GBIF species key. |
| `min_lat` | float | required | Southern edge. |
| `min_lon` | float | required | Western edge. |
| `max_lat` | float | required | Northern edge. |
| `max_lon` | float | required | Eastern edge. |
| `resolution` | float | model native (0.25) | Output cell size in degrees. |

All native-resolution (0.25 deg) cells in the bbox are scored in a single
vectorized forward pass. When `resolution` exceeds native, per-cell scores are
averaged into coarser tiles. Cells not in the pre-computed table are sampled
from GIS rasters on the fly, giving dense coverage over any land area.

### `GET /api/predict/info`

Return metadata about the loaded inference model (species count, cell count,
list of species keys).
