# Darwin Heatmap Improvement Plan

This note records the concrete optimization port plan for the Darwin inference
heatmap route and the reasoning behind the implementation order.

## Current Path

The Darwin species heatmap route renders tiles through:

1. `main.py` route handler for `/api/species/{taxon_id}/heatmap/tiles/{z}/{x}/{y}.png`
2. `DarwinSpeciesHeatmapScorer.render_runtime_tile_bytes(...)`
3. `util.heatmap_tiles.render_heatmap_tile_bytes(...)`
4. `util.inference.score_species_coords(...)`

This path now includes:

- disk-backed Darwin tile caching with bundle-aware cache invalidation;
- request cancellation support through the Darwin tile render path;
- parent-tile reuse for deep zoom;
- request-scoped profiling and cache bypass controls for targeted testing.

The main remaining work is no longer basic parity with the legacy tile stack.
It is reducing raster-read cost, deciding how to handle live temporal inputs on
the tile route, and adding backpressure for bursty deep-zoom parent renders.

## Port Status And Remaining Work

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

## Inference Profiling And Bottleneck Attribution

We should be able to determine whether Darwin inference is primarily limited by:

- SSD or other disk I/O;
- RAM pressure or paging;
- single-core CPU saturation;
- multi-core CPU saturation.

The current code now exposes both runtime controls and request-level timing,
which is enough to attribute the dominant Darwin tile bottleneck with much more
confidence than before.

### Implemented instrumentation

Today we can tune:

- `WHEREWILD_INFERENCE_DEVICE`;
- `WHEREWILD_INFERENCE_CELL_TABLE_DEVICE`;
- `WHEREWILD_INFERENCE_SAMPLE_WORKERS`;
- `WHEREWILD_INFERENCE_SAMPLE_CHUNK_SIZE`.

And we now have request-scoped Darwin profiling via the tile route:

- `profile=true` to emit structured per-request timing and counters;
- `bypass_cache=true` to force uncached measurement of one tile request.

The current profiling output includes:

- cache lookup, coordinate generation, resolution-hint, scoring total,
  colorization, PNG encode, cache write, crop, and total request time;
- sampled-feature phase splits for prefilter, static sampling, DEM-derived
  work, temporal sampling, matrix fill, and feature transform;
- coordinate and feature-source counters such as cell-table hits, sampled
  fallbacks, chunk count, sample chunk size, and score batch size;
- RSS snapshots before score, after score, and after render.

### Profiling result so far

Profiling on the current hot Darwin tile class shows:

- model scoring is small relative to feature preparation;
- the dominant remaining cost is raster work, especially static sampling and
  the runtime prefilter;
- increasing sample chunk size to a single giant chunk raised RSS and did not
  improve total request time materially;
- bounded-window raster reads for compact point clouds produced a meaningful
  win;
- simplifying the runtime prefilter to a single `landcover` gate produced
  another meaningful win.

In other words, the current Darwin tile bottleneck is no longer speculative.
It is primarily raster sampling work rather than the model forward path.

### Why this matters

This shifts the priority order of Darwin optimization work.

The next likely wins are things like:

- cheaper serving-time validity masks;
- fewer static raster reads per uncached tile;
- better temporal-raster reuse if live temporal tile inference is enabled.

The next likely wins are not larger sampling chunks or broad changes to model
batching.

### Optional follow-up measurements

When running a representative hot tile and cold tile, collect Linux process and
system metrics in parallel.

Recommended tools:

- `pidstat -dru -t 1` for per-process CPU, memory, and disk activity;
- `iostat -xz 1` for device saturation and read latency;
- `vmstat 1` for paging or memory pressure;
- `py-spy top` or `py-spy record` for Python wall-time hotspots;
- `perf stat` when we need stronger evidence about CPU utilization,
  instructions, cache misses, and scaling behavior.

## Next Raster-Work Reduction Candidate

Recent Darwin tile profiling points to raster work, not model scoring, as the
main remaining latency source. After the compact-window sampling change and the
landcover-only runtime prefilter, the next candidate optimization is a derived
serving-validity mask.

### Proposal

Build one shared Darwin validity mask raster per GIS region tile and use it as
the first prefilter before full static feature sampling.

This mask should answer only:

- can the backend build a usable Darwin static feature vector here?

It should not encode per-species suitability or range assumptions.

### Recommended first version

- Build the mask from `landcover` only.
- Store it with the GIS data under `data/gis/regions/...`, not under
  `checkpoints`.
- Use it to replace the current runtime landcover prefilter read, not sit
  alongside it.

Why start there:

- the current fastest prefilter already reduced runtime to a single landcover
  gate;
- the earlier shadow audit found no rescued points on the profiled tile from
  the old `elevation|bio_1` fallback path;
- landcover-only keeps the artifact cheap to build and easy to audit.

### Why not build it from all three gate layers first

Do not start by baking `landcover`, `elevation`, and `bio_1` into the mask.

Reasons:

- `dem.tif` dominates the static raster corpus and would make mask generation a
  much heavier job;
- adding `bio_1` couples the artifact to broader climate coverage rather than
  the narrow serving-validity question;
- a stricter multi-layer rule is harder to reason about if it drops valid
  cells.

If later audits show real false negatives, add `elevation` before considering
`bio_1`.

### Expected impact

This is a plausible next speed win because the current prefilter still costs on
the order of `1.4-1.6s` on the profiled Darwin tile class. The expected gain is
not guaranteed, but a binary validity mask could save a substantial fraction of
that time if it materially reduces raster bytes read and replaces the runtime
landcover gate.

### Expected artifact cost

Based on the current regioned GIS layout:

- there are 648 region directories under `data/gis/regions`;
- compressed `landcover.tif` tiles total about `29.5 GB` across regions;
- compressed `dem.tif` tiles total about `555.9 GB` across regions.

That suggests a landcover-only binary validity mask should be modest relative
to the rest of the GIS stack, likely low single-digit GB total, and should be
possible to generate in tens of minutes rather than hours on local storage.

### Validation plan

Before enabling the mask by default:

1. generate the landcover-only mask;
2. compare keep/drop decisions against the current runtime gate on a sample of
   representative tiles;
3. only widen the mask rule if the audit shows meaningful false negatives.

## Live Temporal Darwin Support

Darwin already has most of the temporal feature machinery needed to consume
live weather rasters during inference. The missing piece is wiring that
support into the species heatmap route and cache model.

### Current state

- Darwin bundle schema and model docs already include temporal feature inputs
  and temporal missing masks.
- `util.inference._batch_sample_features(...)` already supports temporal
  sampling via `temporal_mode` and `temporal_forecast_hours`.
- `util.inference.rank_species_weather_delta_coords(...)` now reuses static
  cell-table inputs when available and overwrites only the temporal feature
  span with live temporal values, falling back to sampled weather only when the
  cell table cannot serve the coordinate.
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

There are two viable approaches for the tile route:

1. Force sampled features whenever live temporal data is requested.
2. Keep static features from the cell table, then overwrite only the temporal
   feature span with sampled live values.

The first approach is simpler.
The second approach is likely better for performance because it preserves the
main benefit of the cell table while still allowing fresh temporal inputs.

Recommended direction:

- Prefer the hybrid approach on the tile route as well, because it already
  works in the weather-delta path and is the best fit for Darwin's current
  serving architecture.

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
2. Reuse the existing hybrid static-reuse plus temporal-overwrite pattern from
  the weather-delta path.
3. Keep a sampled-only fallback path for coordinates not covered by the cell
  table.
4. Extend Darwin tile cache keys with temporal version inputs.
5. Validate deep-zoom behavior and cache hit rates under rapid pan and zoom.

### Practical conclusion

Feeding live temporal data into Darwin does not require a new model format or
new temporal sampling system. It mostly requires exposing the existing temporal
sampling controls on the heatmap route, deciding how they interact with
cell-table reuse on the tile path, and making the Darwin tile cache aware of
temporal raster freshness.

## Darwin Prior Calibration Fix

This work is no longer a proposal. It has been implemented in the Darwin
training path and documented here as completed calibration work.

Recent inspection of the pre-fix canary-plants inference bundle had suggested
that the old Darwin per-species heads could become badly overconfident for
broadly distributed or well-supported taxa.

For taxon `10818007`, the pre-fix bundle metadata showed:

- `n_positives == n_unlabeled`;
- `prior_pi == 0.5`;
- high runtime scores even at obvious non-habitat locations such as Great Salt
  Lake.

This is consistent with the current training setup:

- Stage C head training estimates `prior_pi` from the sampled Stage C table;
- the canary preprocessing pipeline defaults to `--background-ratio 1.0`;
- that produces a roughly 1:1 positive-to-unlabeled table for many species;
- the estimated class prior is then driven toward `0.5` and clamped there.

That makes the sampled training ratio act like species prevalence, which is not
the intended semantics of the class prior for online suitability scoring.

### Implemented change

The old sampled-ratio prior path was dropped.

Stage C head training now uses an explicit fixed prior configuration and stores
that choice in model metadata.

Implemented behavior:

- CLI support for `--fixed-prior`;
- fixed-prior Stage C head training;
- metadata persistence of `prior_pi` and `prior_mode = "fixed"`.

Current default used for the canary workflow:

- `fixed_prior = 0.05`

This is intentionally conservative and should be treated as the first
calibration pass, not the final answer for every taxon or dataset.

### Why this was the lowest-risk fix

- It changes only Stage C head training.
- It does not require rebuilding the preprocessed parquet dataset.
- It does not require retraining the shared encoder.
- It does not require changing the inference bundle format in a disruptive way.
- It makes Darwin calibration experiments cheap because only heads need to be
  retrained and re-exported.

### Current status

- Implemented in the training and export path.
- Model documentation has been updated to reflect fixed-prior behavior.
- Focused regression tests for the fixed-prior path are in place.

### Open question after this fix

If a fixed prior materially improves obviously wrong non-habitat scores, the
next likely issue is not runtime inference but training data composition.

In particular, Darwin may still need:

- more aggressive broad-background sampling;
- stronger geographic negatives;
- explicit water or non-habitat sanity evaluation.

## Validation

Implemented caching should be validated with:

1. repeated-request tests proving identical tiles reuse cached PNG bytes;
2. a bundle-aware invalidation test proving cache keys change when the bundle
   changes;
3. containerized backend tests, since this repo expects Python validation in
   the GDAL Docker runtime.
