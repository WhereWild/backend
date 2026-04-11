# Inference Optimization Opportunities

This note evaluates practical optimization options for the Darwin inference path,
with emphasis on whether they require retraining, new exported artifacts, or only
runtime code changes.

## Current State

Current inference has two broad modes:

- cell-table lookup from the exported inference bundle;
- sampled feature assembly from GIS and temporal rasters.

The cheapest path today is still exact cell-table lookup. Sampled inference is
more flexible, but it is naturally more expensive because it has to touch many
source rasters and assemble feature tensors at request time.

Recent inference-only optimization already completed:

- sampled feature assembly now fills dense batch arrays before converting to
  Torch tensors, instead of building per-coordinate Python feature lists.

This improved the runtime hot path without changing model weights or bundle
format.

## Summary Table

| Opportunity | Expected gain | Practicality | Retraining required | New artifacts required |
| --- | --- | --- | --- | --- |
| Dense sampled batch assembly | Medium | Already implemented | No | No |
| Hybrid sampled-default path | High | Good next step | No | No |
| Process-wide temporal raster cache | Medium to high | Straightforward | No | No |
| Columnar exported cell table | High for cell-table inference | Worth doing if cell-table remains central | No | Yes |
| Integer cell index instead of string-key dict lookup | Medium | Pairs well with columnar cell table | No | Yes |
| Arrow or memmap serving artifact for inference | Medium to high | Viable, but more invasive | No | Yes |
| Direct parquet access during request-time inference | Low to negative for hot path | Not recommended as the primary serving path | No | Maybe |

## Detailed Evaluation

### 1. Dense sampled batch assembly

Practicality:

- High.
- This was an inference-only refactor.
- It reduces Python object churn during sampled inference by assembling dense
  `float32` arrays and coercing them to model input in batch.

Artifact impact:

- No retraining.
- No bundle regeneration.

Assessment:

- This is the right kind of optimization for the existing sampled path.
- It improves efficiency but does not change the fundamental fact that sampled
  inference still has to read many rasters.

### 2. Hybrid sampled-default path

Idea:

- Keep sampling as the logical default behavior, but still use the exported
  cell table first when there is an exact bin match.
- Only sample missing or unresolved pieces at request time.

Practicality:

- High.
- This is likely the best next runtime optimization if the goal is to make
  sampled inference feel like the default without always paying full sampling
  cost.

Artifact impact:

- No retraining.
- No new artifacts.

Assessment:

- This gives most of the product benefit of sampled-default behavior while
  preserving the speed of the precomputed bundle when it is available.
- It is a better near-term target than replacing the cell-table path entirely.

### 3. Process-wide temporal raster cache

Idea:

- Keep current temporal rasters loaded across requests instead of using only
  request-local caches.

Practicality:

- High.
- The code change is modest.
- The main design question is cache invalidation when weather rasters refresh.

Artifact impact:

- No retraining.
- No bundle regeneration.

Assessment:

- This is especially useful now that weather-delta inference and current
  temporal sampling exist.
- Without a shared cache, repeated requests keep paying disk-read cost for the
  same `.npy` temporal arrays.

### 4. Columnar exported cell table

Idea:

- Replace the nested exported structure
  `dict[cell_id] -> {features, mask}`
  with columnar arrays or tensors such as:
    - `lat_bin`
    - `lon_bin`
    - `features[n_cells, input_dim]`
    - optional raw mask arrays

Practicality:

- Medium.
- This is a good optimization if cell-table inference remains important.
- It is more invasive because export and load paths both need to change.

Artifact impact:

- No retraining.
- Yes, new exported inference bundles would be required.

Assessment:

- This is likely the largest pure serving-side structural improvement.
- It reduces Python dict overhead and makes the lookup payload much more
  ML-native.
- It is best treated as a bundle format migration.

### 5. Integer cell index instead of string-key dict lookup

Idea:

- Replace string `cell_<lat>_<lon>` lookup with packed integer keys or sorted
  `(lat_bin, lon_bin)` arrays plus binary search.

Practicality:

- Medium.
- This fits naturally with a columnar cell-table bundle.

Artifact impact:

- No retraining.
- Yes, new exported artifacts if the bundle format changes.

Assessment:

- This is useful, but mostly as part of the same bundle redesign as the
  columnar cell table.
- On its own, it is less important than removing nested payload dicts.

### 6. Arrow or memmap serving artifact

Idea:

- Store inference-serving data in a memory-mappable format such as Arrow IPC,
  NumPy memmap, or another columnar binary layout instead of a large Python
  object graph inside the Torch bundle.

Practicality:

- Medium.
- Feasible, but it changes deployment assumptions and startup behavior.

Artifact impact:

- No retraining.
- Yes, a new export artifact or sidecar artifact would be required.

Assessment:

- This can make large serving data more efficient and more friendly to process
  startup and memory sharing.
- It is more work than the hybrid and caching optimizations, so it is better as
  a second-stage serving redesign.

### 7. Direct parquet access during online inference

Idea:

- Read parquet or Arrow datasets directly during request handling instead of
  relying on the exported bundle.

Practicality:

- Low for the hot path.
- Parquet is excellent for offline scans and preprocessing, but it is usually
  not the best representation for latency-sensitive online inference.

Artifact impact:

- No retraining.
- It may not require a new artifact, but it also does not solve the serving
  latency problem very well.

Assessment:

- This is not the right default direction for online serving.
- Parquet-friendly and ML-native are not the same thing. For request-time
  inference, dense arrays and memory-mappable serving artifacts are usually the
  better target.

## Recommended Order

If the goal is better practical inference performance without retraining, the
recommended order is:

1. Hybrid sampled-default path.
2. Process-wide temporal raster cache.
3. Columnar bundle redesign for the exported cell table.
4. Optional serving artifact redesign if startup and memory become material
   bottlenecks.

## Bottom Line

The most practical next optimizations do not require retraining.

- Runtime-only optimizations:
    - hybrid sampled-default path;
    - process-wide temporal raster cache;
    - further cleanup of sampled batch assembly.

- Export-format optimizations that still do not require retraining:
    - columnar cell-table bundles;
    - integer-key or array-index lookup structures;
    - Arrow or memmap sidecar serving artifacts.

If the immediate goal is faster inference with the current model, the best
return is still to improve runtime data access and reuse before considering any
new training work.
