# Darwin Species Distribution Model (Modular, Server-Side)

## 1. Goal

Predict species occurrence probability at a location while:

- avoiding a separate large model per species,
- supporting server-side inference at arbitrary coordinates,
- scaling to ~891 GB / ~2.93M files,
- handling presence-only data (no true negatives).

## 2. Recommended Model Family

Use a shared global encoder + small per-species heads.

### 2.1 Shared encoder (`E`)

Input for a location/cell:

- static environmental features (BIO variables, elevation, landcover, aspect, Koppen, etc.),
- optional temporal features (month, recent weather aggregates),
- optional neighborhood context (small raster patch summary or precomputed local stats).

Implementation note: use location/time/source fields only to join and construct features; do not feed raw `lat`, `lon`, exact `event_time_utc`, or `source` directly into model input tensors.

Encoder output:

- embedding vector `z = E(x)`, e.g. 128 dims.

Practical architecture:

- tabular encoder: 4 linear layers total (`project_in` + two residual block linears + `project_out`) with residual connections, GELU, LayerNorm,
- optional raster branch: tiny CNN (MobileNet-style depthwise blocks), fused with tabular branch,
- final projection to 128-d embedding.

Counting note: this may be informally described as a 3-stage stack (input projection, residual trunk, output projection), but implementation uses 4 linear layers.

### 2.2 Species heads (`H_s`)

For each species `s`, train only a tiny classifier on `z`:

- default: logistic regression (`w_s^T z + b_s`),
- optional: 1 hidden layer (64 units) for hard species.

This keeps per-species parameters tiny and allows fast retraining/new species onboarding.

## 3. Handling Missing Negatives (Presence-Only)

Train heads with Positive-Unlabeled (PU) learning instead of standard binary labels.

### 3.1 Data for species `s`

- Positives `P_s`: known occurrences.
- Unlabeled `U_s`: background samples drawn from accessible area (M), time-aware when possible.

### 3.2 Loss

Use non-negative PU risk (`nnPU`) with prior `π_s = P(y=1|s)`.

Current implementation estimates `π_s` with empirical-Bayes smoothing:

`raw_s = n_pos_s / n_rows_s`

`π_s = (n_pos_s + α * p_global) / (n_rows_s + α)`

where `p_global` is the global positive rate in the train split and `α=50`.

Then apply non-negative PU risk:

$R(f) = \pi_s \mathbb{E}_{x \sim P_s}[\ell(f(x))] + \max\bigl(0,\ \mathbb{E}_{x \sim U_s}[\ell(-f(x))] - \pi_s \mathbb{E}_{x \sim P_s}[\ell(-f(x))]\bigr)$

where `f(x)=H_s(E(x))` and `l` is logistic loss.

Why: this directly addresses “absence of negatives” and reduces false-negative bias.

### 3.3 Unlabeled sampling policy (critical)

- pool transformed positive rows across species,
- for target species `s`, sample unlabeled rows from other-species rows in the same split only,
- exclude sampled rows whose `(cell_id, year_month)` pair is already positive for species `s`,
- set `presence_label=0` for sampled rows and treat them as unlabeled (not true negatives).

Constraints:

- Current implementation: donor rows are constrained to the same split and filtered to avoid `(cell_id, year_month)` conflicts for the target species.
- Current implementation: sample weights rebalance donor-species frequency skew within each target species.
- Not yet implemented: explicit donor-pool constraints by region/biome/month.
- Not yet implemented: explicit hotspot-cell rebalancing beyond donor-species frequency weighting.

## 4. Training Strategy for Your Hardware (RTX 5090 32 GB)

### Stage A - Build training table

- Convert source shards into a training parquet index with:
    - cell_id, lat/lon/time,
    - environmental feature vector,
    - species occurrence links.
- Keep this as a streaming dataset (do not materialize giant tensors).

### Stage B - Train global encoder once

This stage can be run without species labels (self-supervised/unsupervised pretraining on all rows).

Current objective:

- auxiliary reconstruction/regression of environmental variables.

Deferred objective terms (not active in current scripts):

- spatial contrastive term,
- taxonomy-aware metric loss for species co-occurrence neighborhoods.

Default settings:

- embedding dim: 128,
- mixed precision (bf16/fp16),
- batch size: 32768 (current training CLI default; tune per memory budget),
- encoder data mode: chunk-cached (default bounded-RAM middle ground), streaming (lowest RAM), or in-memory (fastest when RAM allows),
- chunk rows: 400000 (default),
- prefetch chunks: 3 (default max depth),
- adaptive prefetch: enabled by default (backs off queue depth under memory/swap pressure),
- encoder shuffle mode: block (default) or global,
- optimizer: AdamW, cosine decay.

### Stage C - Train per-species heads

After Stage B, use the pretrained encoder embedding as the fixed representation for species-level training.

- freeze encoder,
- train PU logistic head per species.
- Current implementation status: heads are trained sequentially in one process (not yet parallelized into CPU/GPU mini-jobs).
- Not yet implemented: optional unfreeze of top encoder block for rare species.

Expected outcome: most compute spent once in shared encoder; species updates are cheap.

## 5. Server-Side Inference Design

### 5.1 Export format

- The trained encoder + per-species heads + geocell feature table are packaged into a single `.pt` inference bundle via `scripts/machine_learning/train/export.py`.
- The bundle also stores feature names (bioclimate, landclass, terrain, edaphic, temporal, other). The catalog-backed static groups are directly sampleable from GIS rasters; temporal and other are filled as missing in sampled-only inference paths.

### 5.2 Runtime

- The inference engine (`util/inference.py`) loads the bundle at startup and
    runs on CPU by default, with optional CUDA inference enabled via runtime env
    configuration.
- No training-time CUDA/AMP stack is required to serve the model, but PyTorch
    and optional CUDA runtime support are still used for inference.
- FastAPI prediction endpoints currently exposed:
    - `/api/species/{taxon_id}/heatmap` (tile metadata)
    - `/api/species/{taxon_id}/heatmap/tiles/{z}/{x}/{y}.png` (species heatmap PNG tiles)
    - `/api/predict/heatmap-jobs` (create async heatmap job)
    - `/api/predict/heatmap-jobs/{job_id}/stream` (stream async heatmap job progress/results)
    - `/api/predict/heatmap-jobs/{job_id}` (delete/cancel heatmap job)

### 5.3 On-the-fly GIS sampling

For coordinates without pre-computed features (not in the training cell table):

- Static features (bioclim, elevation, slope, aspect, landcover, Koppen-Geiger) are sampled from local COG rasters via rasterio.
- DEM-derived features (slope, aspect, aspect_deg) are computed from a 3x3 window around the query point.
- Weather features are marked all-missing (the model handles masked inputs).
- Batch sampling opens each raster once per 10-degree region tile for efficiency.

This enables predictions at any land coordinate on Earth.

### 5.4 Latency strategy

- Pre-computed cell table gives instant lookup for training-covered areas.
- On-the-fly GIS sampling is substantially more expensive than cell-table
    lookup, especially for tile requests that evaluate many output pixels.
- Heatmap job streaming scores chunked coordinate batches rather than one giant
    all-cells tensor.
- Tile rendering currently computes PNG tiles on demand and does not persist a
    server-side rendered-tile cache.
- High zoom tile requests may be served by rendering a nearby parent tile under
    the configured size cap and cropping the requested subtile.

## 6. Data Splits and Validation (avoid leakage)

- split by space and time, not random rows,
- Current implementation: deterministic space-time split by hashed `(cell_id, year_month)` into train/val/test partitions.
- Not yet implemented: blocked CV by geohash/S2 and explicit recent-month holdout protocol.
- Not yet implemented in training scripts: PR-AUC, Recall@fixed precision, calibrated Brier score reporting.
- Not yet implemented in training scripts: prevalence-bin reporting (common vs rare species).

## 7. Recommended MVP (first production cut)

1. Build 128-d tabular encoder only (no raster branch yet).
2. Train encoder on all taxa with self-supervised + aux env prediction.
3. Train PU logistic heads for top N species with enough positives.
4. Export `.pt` inference bundle containing encoder + heads + geocell feature table + feature names.
5. Serve predictions via FastAPI with on-the-fly GIS raster sampling for arbitrary coordinates.

Current implementation covers modular per-species updates, server-side inference,
single-GPU feasibility, and nnPU treatment of missing negatives.

Remaining gaps to close full policy alignment are documented in Sections 3.3 and 6.

## 8. Data Preprocessing Pipeline (ETL)

1. Ingest raw observations and standardize core fields (taxonomy, UTC timestamp, WGS84 coords).
2. Snap each record to `cell_id` and derive `region_id`.
3. Join static context (climate normals, elevation, landcover, biome/ecoregion).
4. Join temporal context (recent weather aggregates aligned to observation time).
5. Build PU rows:
    - positives from observations,
    - unlabeled/background rows sampled from other-species positives in the same split, filtered to avoid `(cell_id, year_month)` conflicts for the target species.
6. Build vectors:
    - `bioclimate_features`, `landclass_features`, `terrain_features`, `edaphic_features`, `temporal_features`, `other_features` with fixed order by `feature_version`.
7. Keep leakage-prone fields (`lat`, `lon`, `event_time_utc`, `source`) as metadata only; exclude from model input tensors.
8. Write split-partitioned Parquet by `split`.

Notes:

- The script performs file-level multithreading for faster NVMe throughput.
- It keeps `lat/lon/time/source` as metadata fields and excludes them from model input vectors.
- Static and temporal context can be joined during this preprocessing step via configured context inputs, or pre-joined upstream into occurrence files; whichever path is used should be kept consistent per `feature_version`.
- Known issue: current background sampling is not yet spatially stratified over an explicit accessible-area `M` definition; treat this as a temporary approximation until stratified/background-area sampling is implemented.

## 9. Partition Strategy: Time vs Species

- Base dataset should keep a split-only partition layout.
- Why this base partitioning:
    - simple, stable layout for training/validation,
    - avoids over-partitioning and small-file proliferation,
    - keeps time and region available as metadata without making them directory keys.
- Can it be partitioned by species? Yes, but usually only as a derived dataset or view for head training jobs.
- Why not species as primary partition:
    - very high species cardinality creates many tiny partitions,
    - severe skew (common species huge, rare species tiny),
    - expensive global scans for encoder training.
- Practical compromise:
    - keep the base table split-partitioned,
    - optionally materialize species-bucket shards (e.g., hash buckets) for per-species training throughput.

## 10. Future Upgrades

- Hierarchical heads (kingdom→phylum→...→species) for better rare-species transfer.
- Distill encoder to an even smaller student for low-end phones.
- Add uncertainty estimate (MC dropout / deep ensemble heads) for abstention.
