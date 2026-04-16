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

## Inference Profiling And Bottleneck Attribution

We should be able to determine whether Darwin inference is primarily limited by:

- SSD or other disk I/O;
- RAM pressure or paging;
- single-core CPU saturation;
- multi-core CPU saturation.

The current code already exposes useful runtime controls such as inference
device selection, sampling worker count, and sampling chunk size, but it does
not yet emit enough stage-level timing to attribute slowness confidently.

### Current limitation

Today we can tune:

- `WHEREWILD_INFERENCE_DEVICE`;
- `WHEREWILD_INFERENCE_CELL_TABLE_DEVICE`;
- `WHEREWILD_INFERENCE_SAMPLE_WORKERS`;
- `WHEREWILD_INFERENCE_SAMPLE_CHUNK_SIZE`.

What we do not yet have is per-request timing for the major phases of the
Darwin path. Without that, optimization discussions stay speculative.

### Recommended profiling plan

#### 1. Add request-level timing inside the Darwin path

Instrument the main phases of a heatmap request and log elapsed wall time for
each phase, along with request shape metadata.

Recommended phases:

1. tile cache lookup;
2. coordinate generation and parent-tile reuse;
3. cell-table resolution versus sampled fallback;
4. raster sampling;
5. feature assembly and transform;
6. encoder forward pass;
7. per-species head scoring;
8. PNG encoding;
9. cache write.

Recommended counters per request:

- total coordinates;
- number of exact cell-table hits;
- number of sampled coordinates;
- score batch size;
- sample chunk size;
- sampling worker count;
- feature mode;
- whether temporal sampling was used.

Also capture process RSS before and after the expensive phases so we can spot
memory growth or paging pressure during hot requests.

#### 2. Pair application timings with system measurements

When running a representative hot tile and cold tile, collect Linux process and
system metrics in parallel.

Recommended tools:

- `pidstat -dru -t 1` for per-process CPU, memory, and disk activity;
- `iostat -xz 1` for device saturation and read latency;
- `vmstat 1` for paging or memory pressure;
- `py-spy top` or `py-spy record` for Python wall-time hotspots;
- `perf stat` when we need stronger evidence about CPU utilization,
  instructions, cache misses, and scaling behavior.

#### 3. Classify the bottleneck from the measurements

Use the combined app-level and system-level data to distinguish the dominant
limiter.

Signs of SSD or disk bottleneck:

- request time is concentrated in cell lookup or raster sampling phases;
- read I/O or device utilization is high;
- CPU utilization stays modest while requests stall.

Signs of RAM bottleneck:

- RSS grows materially during requests;
- page faults, reclaim, or swap activity appear;
- latency becomes unstable under repeated requests.

Signs of single-core CPU bottleneck:

- one core is saturated while aggregate CPU usage remains modest;
- profiling shows one dominant hot stack;
- raising worker count does not materially improve latency.

Signs of multi-core CPU bottleneck:

- many cores are busy during inference;
- throughput improves with worker count or chunk tuning until it plateaus;
- system CPU is high without corresponding disk saturation.

### Why this matters

This profiling pass is what allows targeted fixes instead of generic ones.

For example:

- if disk dominates, focus on process-wide raster caches or better serving
  artifacts;
- if memory dominates, focus on bundle layout and allocation behavior;
- if single-core CPU dominates, focus on hot-loop Python and model batching;
- if multi-core CPU dominates, focus on concurrency limits, worker tuning, and
  backpressure.

### Profiling conclusion

Yes, Darwin inference can be profiled deeply enough to answer whether the main
limit is SSD, RAM, single-core CPU, or multi-core CPU. The missing piece is a
small amount of request-level instrumentation in the inference path so that the
system metrics can be interpreted against concrete application phases.

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

## Darwin Prior Calibration Fix

Recent inspection of the live canary-plants inference bundle suggests that the
current Darwin per-species heads can become badly overconfident for broadly
distributed or well-supported taxa.

For taxon `10818007`, the loaded bundle metadata shows:

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

### Recommended change

Drop the old sampled-ratio prior path entirely.

Instead:

1. Add an explicit fixed prior configuration for Stage C head training.
2. Train per-species Darwin heads with a conservative fixed `prior_pi`.
3. Record the chosen prior directly in head metadata.

Recommended initial value:

- `fixed_prior = 0.05`

This is intentionally conservative and should be treated as the first
calibration pass, not the final answer for every taxon or dataset.

### Concrete implementation

#### 1. Replace sampled-ratio prior estimation in Stage C

Update `scripts/machine_learning/train/train_heads.py` so that Stage C no
longer computes `prior_pi` from:

- `n_species_positives`
- `n_species_total_rows`
- `global_positive_rate`

The current `estimate_prior(...)` path should be removed rather than retained
behind a flag.

#### 2. Add explicit fixed-prior arguments to the CLI

Extend `scripts/machine_learning/train/cli.py` with arguments such as:

- `--fixed-prior`

The Stage C code should require this value explicitly or use a clear default.

Recommended default for the canary workflow:

- `--fixed-prior 0.05`

#### 3. Persist the prior choice in metadata

When writing `species_meta` in `species_heads.pt`, store at least:

- `prior_pi`
- `prior_mode = "fixed"`

Do not preserve the old sampled-ratio estimate as a supported alternate mode.

### Why this is the lowest-risk fix

- It changes only Stage C head training.
- It does not require rebuilding the preprocessed parquet dataset.
- It does not require retraining the shared encoder.
- It does not require changing the inference bundle format in a disruptive way.
- It makes Darwin calibration experiments cheap because only heads need to be
  retrained and re-exported.

### Suggested workflow

1. Update Stage C training to use a fixed prior only.
2. Retrain Darwin heads for `canary_plants`.
3. Export a fresh `inference_bundle.pt`.
4. Re-run the same point probes for Great Salt Lake and known observations.
5. If scores remain implausibly broad, then investigate broader unlabeled or
   background sampling as the next training change.

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
