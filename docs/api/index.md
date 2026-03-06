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

Runtime device env vars:

- `WHEREWILD_INFERENCE_DEVICE`: `auto` (default), `cpu`, `cuda`.
  `auto` uses CUDA when available, else CPU.
- `WHEREWILD_INFERENCE_CELL_TABLE_DEVICE`: `auto` (default), `cpu`, `cuda`.
  `auto` keeps `cell_table` on CPU.
  `cuda` is allowed only when `WHEREWILD_INFERENCE_DEVICE=cuda`.

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
| `include_source` | bool | false | Include per-cell feature source (`sampled` or `cell_table`) for debugging. |
| `feature_mode` | string | `auto` | Feature source strategy: `auto`, `prefer_cell_table`, `cell_table_only`, `sampled_only`. |
| `max_cells` | int | 20000 | Hard cap on output cells; oversized requests return 400. |

All requested cells in the bbox are scored in vectorized batches.
`feature_mode=prefer_cell_table` is the default stability mode and avoids
over-aggressive sampled fallback by using precomputed native-cell features when
available. When `include_source=true`, each returned cell may include `source`
as `sampled` or `cell_table`.

### `GET /api/predict/heatmap/stream`

Stream the same heatmap as NDJSON (`application/x-ndjson`) so clients can
render progressively without waiting for the full grid.

Uses the same query parameters as `GET /api/predict/heatmap`.

Event lines:

- `{"type":"meta", ...}` once at start (includes `requested_cells`)
- `{"type":"cell", "lat":..., "lon":..., "score":..., "n_native":...}` per cell
- `{"type":"done", "n_cells":...}` once at end

This endpoint is preferred for large bboxes because the server does not need to
build a giant in-memory `cells` list before sending data.

### Job resource model for stale-call cancellation

For robust client workflows, use cancellable heatmap jobs:

### `POST /api/predict/heatmap-jobs`

Create a job resource and receive stable URLs to stream and cancel it.

Request body uses the same fields as heatmap requests:
`species_key`, `min_lat`, `min_lon`, `max_lat`, `max_lon`, optional
`resolution`, `include_source`, `feature_mode`, `max_cells`.

Response includes:

- `job_id`
- `status` (`created`)
- `stream_url`
- `cancel_url`

### `GET /api/predict/heatmap-jobs/{job_id}/stream`

Stream job output as NDJSON. Event lines:

- `{"type":"meta", "job_id":..., ...}`
- many `{"type":"cell", ...}`
- terminal `{"type":"done", "job_id":..., "n_cells":...}`
- or `{"type":"cancelled", "job_id":..., "n_cells":...}`

Only one active stream is allowed per job.

### `DELETE /api/predict/heatmap-jobs/{job_id}`

Cancel stale jobs. Running streams will stop quickly and emit a
`cancelled` terminal event.

### `GET /api/predict/info`

Return metadata about the loaded inference model (species count, cell count,
list of species keys).
