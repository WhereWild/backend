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
- `WHEREWILD_INFERENCE_SAMPLE_WORKERS`: integer `>=1` (default: `1`).
  Controls parallel raster-layer sampling for heatmaps.
  Keep at `1` unless benchmarked on your deployment.
- `WHEREWILD_INFERENCE_SAMPLE_CHUNK_SIZE`: integer `>=1` (default: `8192`).
  Controls sampling chunk size for heatmap job streaming.
  This is independent from model scoring batch size.
- `WHEREWILD_INFERENCE_STREAM_PREFETCH_CHUNKS`: integer `>=1` (default: `2`).
  Controls how many prepared stream chunks can queue ahead.
  Increase for more read-ahead overlap (uses more memory).

### `GET /api/species/{taxon_id}/heatmap`

Return tile-surface metadata for one species.

Response fields:

| Field | Type | Description |
| --- | --- | --- |
| `available` | bool | Whether the loaded bundle includes that species key. |
| `species_key` | int | Echoed species key. |
| `native_resolution` | float | Native model resolution in degrees. |
| `tile_url` | string\|null | URL template for PNG tiles when available. |

### `GET /api/species/{taxon_id}/heatmap/tiles/{z}/{x}/{y}.png`

Render a Web Mercator PNG tile for one species.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `z` | int | required | Slippy-map zoom level. |
| `x` | int | required | Tile x coordinate. |
| `y` | int | required | Tile y coordinate. |
| `tile_size` | int | `256` | Output PNG size in pixels. |
| `feature_mode` | string | `prefer_cell_table` | Feature source strategy: `prefer_cell_table` or `cell_table_only`. |
| `max_native_zoom` | int | `8` | Render parent tiles above this zoom, then crop subtiles. |

Tiles are rendered from the current bundle-backed per-species heatmap scorer and
returned as `image/png`.

Notes:

- Tile requests are request-scoped, not background jobs.
- The response advertises `Cache-Control`, but the backend does not currently
  persist a rendered-tile cache. Repeated requests may be recomputed unless a
  browser, proxy, or CDN serves them from cache.
- Tile renders are not currently mid-flight cancellable once scoring starts.
- High zoom requests may render the closest reusable parent tile that still
  fits under the configured tile-size cap, then crop the requested subtile.

### Job resource model for stale-call cancellation

For robust client workflows, use cancellable heatmap jobs:

### `POST /api/predict/heatmap-jobs`

Create a job resource and receive stable URLs to stream and cancel it.

Request body fields:

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `species_key` | int | required | GBIF species key. |
| `min_lat` | float | required | Southern edge. |
| `min_lon` | float | required | Western edge. |
| `max_lat` | float | required | Northern edge. |
| `max_lon` | float | required | Eastern edge. |
| `resolution` | float | model native (0.25) | Output cell size in degrees. |
| `include_source` | bool | false | Include per-cell feature source (`sampled` or `cell_table`) for debugging. |
| `feature_mode` | string | `prefer_cell_table` | Feature source strategy: `prefer_cell_table` or `cell_table_only`. |
| `max_cells` | int | 20000 | Hard cap on output cells; oversized requests return 400. |

In `prefer_cell_table`, native/coarser requests use precomputed cell-table
features first; finer-than-native requests prefer sampled GIS features when
available, with cell-table fallback for missing samples.

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
