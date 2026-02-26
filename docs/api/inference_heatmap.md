# Inference Heatmap Contract

## Endpoint

`GET /species/{taxon_id}/inference-heatmap`

`GET /species/{taxon_id}/inference-heatmap-dynamic`

## Query Parameters

- `bbox` (optional): `minLon,minLat,maxLon,maxLat`
- `zoom` (optional): integer in `[1,12]`, default `5`
- `max_cells` (optional): integer in `[100,20000]`, default `4000`
- `time_slice` (optional): precomputed slice id, default `latest`
- `location` (optional): only used in legacy fallback mode

### Dynamic Endpoint Parameters

- `center_lat` (required): center latitude
- `center_lon` (required): center longitude
- `viewport_width_deg` (required): viewport width in degrees
- `viewport_height_deg` (required): viewport height in degrees
- `density` (optional): points-per-axis for grid sampling, default `64`
- `workers` (optional): worker threads for tile/raster sampling, default `4` (typically `2-4` is fastest)
- `apply_range_filter` (optional): default `true`; limits dynamic points to cached species occurrence envelope to reduce implausible extrapolation
- `apply_ood_penalty` (optional): default `true`; applies smooth score dampening outside the occurrence envelope
- `ood_penalty_strength` (optional): default `0.12`; larger values suppress out-of-envelope scores more aggressively
- `time_slice` (optional): label echoed in response, default `dynamic`

Notes:

- Dynamic requests now auto-cap effective density for very large viewports to keep latency bounded.
- Responses include `dynamic.requestedDensity` and `dynamic.effectiveDensity` so clients can detect applied capping.
- Responses include `dynamic.cacheHit` for short-lived in-process memoized repeats of identical requests.
- Responses include `dynamic.applyOodPenalty`, `dynamic.oodPenaltyStrength`, and `dynamic.oodPenaltyMean`.

## Serving Behavior

1. Resolve species mapping from taxon scientific name to model species.
2. Attempt precomputed surface lookup from `artifacts/ml_global_surface_4_species`.
3. If a matching precomputed surface exists, aggregate precomputed cells to requested zoom/bbox.
4. If precomputed surface is unavailable (or time slice missing), fallback to legacy point-scoring inference.

## Response Shape

```json
{
  "speciesId": 2480446,
  "modelSpecies": "Haliaeetus leucocephalus",
  "timeSlice": "static",
  "zoom": 5,
  "cellSizeDeg": 1.40625,
  "totalPoints": 12000,
  "boundedPoints": 800,
  "maxIntensity": 1.0,
  "source": "precomputed_surface",
  "cells": [
    {
      "lat": 44.296875,
      "lon": -112.734375,
      "count": 6,
      "score": 0.842,
      "intensity": 1.0
    }
  ]
}
```

## Source Field

- `precomputed_surface`: responses from precomputed global surface parquet cells.
- `legacy_fallback`: responses computed by scoring occurrence rows on demand.
- `dynamic_inference`: responses from on-demand viewport grid scoring.
