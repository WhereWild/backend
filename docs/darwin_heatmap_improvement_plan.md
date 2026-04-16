# Darwin Heatmap Improvement Plan

This note records the concrete optimization port plan for the Darwin inference
heatmap route and the reasoning behind the implementation order.

## Current Path

The Darwin species heatmap route renders tiles through:

1. `main.py` route handler for `/api/species/{taxon_id}/heatmap/tiles/{z}/{x}/{y}.png`
2. `DarwinSpeciesHeatmapScorer.render_runtime_tile_bytes(...)`
3. `util.heatmap_tiles.render_heatmap_tile_bytes(...)`
4. `util.inference.score_species_coords(...)`

This path already includes chunked inference batching and parent-tile reuse for
deep zoom, but it does not currently use the shared tile cache or
cancellation-aware helpers added for the legacy tile stack.

## Recommended Port Order

### 1. Add Darwin tile caching

Expected gain:

- High for repeated tile requests during pan/zoom and sibling subtile reuse.

Why first:

- It is the clearest missing optimization relative to the legacy tile path.
- It reduces repeated coordinate generation, feature resolution, model scoring,
  colorization, and PNG encoding for identical requests.
- It can be implemented without changing model outputs or bundle format.

Implementation notes:

- Cache key should include `taxon_id`, `z/x/y`, `tile_size`, `feature_mode`,
  `score_batch_size`, data-root namespace, and inference bundle identity.
- Cache invalidation must change when the loaded inference bundle file changes.

Status:

- Implemented.

### 2. Add request-cancellation support to Darwin heatmap renders

Expected gain:

- Medium to high under rapid pan/zoom or browser aborts.

Why second:

- It prevents wasted work on tiles the client has already abandoned.
- It matches the cancellation behavior already used by aggregate and homepage
  tile routes.

Implementation notes:

- Port `run_tile_render_with_cancellation(...)` usage to the Darwin route.
- Thread an optional `cancel_check` through `heatmap_tiles` and inference chunk
  loops so work can stop between sampling and scoring batches.

Status:

- Implemented.

### 3. Add backpressure for Darwin deep-zoom parent renders

Expected gain:

- Medium under bursty high-zoom browsing.

Why third:

- Darwin already reuses parent tiles, but high-zoom requests can still launch
  too many expensive parent renders at once.

Implementation notes:

- Port the semaphore-based deep-zoom slot acquisition pattern used by the
  legacy route.

Status:

- Not yet implemented.

### 4. Add richer cache-versioning inputs where needed

Expected gain:

- Low to medium, mostly correctness and cache hygiene.

Why fourth:

- Bundle-aware invalidation is enough for the current Darwin route.
- Additional version inputs only matter if Darwin starts depending on mutable
  temporal raster state or other dynamic artifacts.

Implementation notes:

- Current Darwin cache should invalidate on bundle changes.
- Extend key material only if route inputs begin to depend on extra mutable
  artifacts.

Status:

- Bundle-aware invalidation implemented.

## Deferred Items

These are useful but less directly portable from the referenced tile
performance commit:

- inner-loop cooperative cancellation inside inference scoring;
- process-wide caches for sampled temporal rasters;
- bundle-format redesign for more columnar cell-table serving.

## Live Temporal Darwin Support

Darwin already has most of the temporal feature machinery needed to consume
live weather rasters during inference. The missing piece is wiring that
support into the species heatmap route and cache model.

### Current state

- Darwin bundle schema and model docs already include temporal feature inputs
  and temporal missing masks.
- `util.inference._batch_sample_features(...)` already supports temporal
  sampling via `temporal_mode` and `temporal_forecast_hours`.
- `util.inference.rank_species_weather_delta_coords(...)` already uses the
  live-temporal path for weather-delta ranking.
- The Darwin heatmap path still calls `score_species_coords(...)` without any
  route-level temporal mode or forecast-hour input.
- The current Darwin heatmap cache key is bundle-aware, but not aware of
  mutable temporal raster inputs.

### Required changes

#### 1. Expose temporal inputs on the Darwin heatmap route

Add route parameters for at least:

- `temporal_mode`, likely `missing` or `current`;
- `forecast_hours` for forecast-backed temporal raster selection.

These inputs then need to flow from the route handler through:

1. `DarwinSpeciesHeatmapScorer.render_runtime_tile_bytes(...)`
2. `util.heatmap_tiles.render_heatmap_tile_bytes(...)`
3. `util.inference.score_species_coords(...)`
4. `util.inference._prepare_feature_batch_for_coords(...)`
5. `util.inference._batch_sample_features(...)`

#### 2. Decide how live temporal data interacts with `feature_mode`

This is the main design decision.

Today Darwin often serves features from the precomputed cell table when
`feature_mode` prefers it. Those cached rows do not automatically reflect live
weather raster updates.

There are two viable approaches:

1. Force sampled features whenever live temporal data is requested.
2. Keep static features from the cell table, then overwrite only the temporal
   feature span with sampled live values.

The first approach is simpler.
The second approach is likely better for performance because it preserves the
 main benefit of the cell table while still allowing fresh temporal inputs.

Recommended direction:

- Prefer the hybrid approach: reuse cell-table static features and replace the
  temporal slice only.

#### 3. Add temporal-aware cache versioning

Once Darwin heatmap tiles depend on live temporal rasters, the tile cache must
change whenever the underlying temporal artifacts change.

The Darwin cache key should then include:

- `temporal_mode`;
- `forecast_hours`;
- a temporal-raster version token analogous to the legacy tile stack.

Without that change, Darwin can serve stale PNGs after weather refreshes.

#### 4. Re-evaluate runtime cost after temporal sampling is enabled

Live temporal sampling makes the Darwin path more expensive than the current
static or cell-table-heavy path.

That increases the value of:

- cooperative cancellation, which is already implemented;
- deep-zoom backpressure, which is still pending;
- any future process-wide temporal raster cache improvements.

### Recommended implementation order

1. Add `temporal_mode` and `forecast_hours` plumbing to the Darwin heatmap
   route and inference entrypoints.
2. Start with a sampled-only implementation if a fast correctness path is
   needed.
3. Add the hybrid cell-table-plus-live-temporal path for performance.
4. Extend Darwin tile cache keys with temporal version inputs.
5. Validate deep-zoom behavior and cache hit rates under rapid pan and zoom.

### Practical conclusion

Feeding live temporal data into Darwin does not require a new model format or
new temporal sampling system. It mostly requires exposing the existing temporal
sampling controls on the heatmap route, deciding how they interact with
cell-table reuse, and making the Darwin tile cache aware of temporal raster
freshness.

## Validation

Implemented caching should be validated with:

1. repeated-request tests proving identical tiles reuse cached PNG bytes;
2. a bundle-aware invalidation test proving cache keys change when the bundle
   changes;
3. containerized backend tests, since this repo expects Python validation in
   the GDAL Docker runtime.
