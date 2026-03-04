# Darwin Species Distribution Model (Modular, Server-Side)

## 1) Goal

Predict species occurrence probability at a location while:

- avoiding a separate large model per species,
- supporting server-side inference at arbitrary coordinates,
- scaling to ~891 GB / ~2.93M files,
- handling presence-only data (no true negatives).

## 2) Recommended Model Family

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

- tabular encoder: 3-layer MLP with residual connections, GELU, LayerNorm,
- optional raster branch: tiny CNN (MobileNet-style depthwise blocks), fused with tabular branch,
- final projection to 128-d embedding.

### 2.2 Species heads (`H_s`)

For each species `s`, train only a tiny classifier on `z`:

- default: logistic regression (`w_s^T z + b_s`),
- optional: 1 hidden layer (64 units) for hard species.

This keeps per-species parameters tiny and allows fast retraining/new species onboarding.

## 3) Handling Missing Negatives (Presence-Only)

Train heads with Positive-Unlabeled (PU) learning instead of standard binary labels.

### 3.1 Data for species `s`

- Positives `P_s`: known occurrences.
- Unlabeled `U_s`: background samples drawn from accessible area (M), time-aware when possible.

### 3.2 Loss

Use non-negative PU risk (`nnPU`) with prior `π_s = P(y=1|s)`:

$R(f) = \pi_s \mathbb{E}_{x \sim P_s}[\ell(f(x))] + \max\bigl(0,\ \mathbb{E}_{x \sim U_s}[\ell(-f(x))] - \pi_s \mathbb{E}_{x \sim P_s}[\ell(-f(x))]\bigr)$

where `f(x)=H_s(E(x))` and `l` is logistic loss.

Why: this directly addresses “absence of negatives” and reduces false-negative bias.

### 3.3 Unlabeled sampling policy (critical)

- spatially stratified by biome/ecoregion,
- bias-corrected by observer effort proxy (if available),
- hard-negative mining: periodically add top false positives from previous epoch.

## 4) Training Strategy for Your Hardware (RTX 5090 32 GB)

### Stage A - Build training table

- Convert source shards into a training parquet index with:
    - cell_id, lat/lon/time,
    - environmental feature vector,
    - species occurrence links.
- Keep this as a streaming dataset (do not materialize giant tensors).

### Stage B - Train global encoder once

This stage can be run without species labels (self-supervised/unsupervised pretraining on all rows).

Multi-task objective (recommended):

- self-supervised contrastive term on nearby vs far cells,
- auxiliary reconstruction/regression of environmental variables,
- optional taxonomy-aware metric loss for species co-occurrence neighborhoods.

Default settings:

- embedding dim: 128,
- mixed precision (bf16/fp16),
- effective batch size: 4k to 16k (gradient accumulation),
- optimizer: AdamW, cosine decay.

### Stage C - Train per-species heads

After Stage B, use the pretrained encoder embedding as the fixed representation for species-level training.

- freeze encoder,
- train PU logistic head per species (parallelized CPU/GPU mini-jobs),
- unfreeze top encoder block for rare species only if needed.

Expected outcome: most compute spent once in shared encoder; species updates are cheap.

## 5) Server-Side Inference Design

### 5.1 Export format

- The trained encoder + per-species heads + geocell feature table are packaged into a single `.pt` inference bundle via `scripts/machine_learning/train/export.py`.
- The bundle also stores feature names (env, habitat, weather) so the server can sample GIS rasters on the fly.

### 5.2 Runtime

- The inference engine (`util/inference.py`) loads the bundle at startup and runs on CPU.
- No CUDA, AMP, or heavy ML dependencies are needed on the server.
- Four FastAPI endpoints expose predictions: single-point, batch, heatmap, and model info.

### 5.3 On-the-fly GIS sampling

For coordinates without pre-computed features (not in the training cell table):

- Static features (bioclim, elevation, slope, aspect, landcover, Koppen-Geiger) are sampled from local COG rasters via rasterio.
- DEM-derived features (slope, aspect, aspect_deg) are computed from a 3x3 window around the query point.
- Weather features are marked all-missing (the model handles masked inputs).
- Batch sampling opens each raster once per 10-degree region tile for efficiency.

This enables predictions at any land coordinate on Earth.

### 5.4 Latency strategy

- Pre-computed cell table gives instant lookup for training-covered areas.
- On-the-fly GIS sampling adds sub-millisecond overhead per query for uncovered areas (rasterio COG reads are fast with local files).
- Heatmap endpoint scores all cells in a single vectorized forward pass.
- Variable resolution aggregation allows zoom-dependent level of detail.

## 6) Data Splits and Validation (avoid leakage)

- split by space and time, not random rows,
- e.g. blocked CV by geohash/S2 + holdout recent months,
- evaluate with PR-AUC, Recall@fixed precision, calibrated Brier score,
- report by prevalence bins (common vs rare species).

## 7) Calibration and Thresholding

- fit per-species temperature scaling or isotonic calibration on holdout,
- keep two thresholds per species:
    - high-precision threshold (user-facing confident mode),
    - high-recall threshold (exploration mode).

## 8) Recommended MVP (first production cut)

1. Build 128-d tabular encoder only (no raster branch yet).
2. Train encoder on all taxa with self-supervised + aux env prediction.
3. Train PU logistic heads for top N species with enough positives.
4. Export `.pt` inference bundle containing encoder + heads + geocell feature table + feature names.
5. Serve predictions via FastAPI with on-the-fly GIS raster sampling for arbitrary coordinates.

This matches all requirements: modular per-species updates, server-side inference,
single-GPU feasibility, and proper treatment of missing negatives.

## 9) Data Preprocessing Pipeline (ETL)

1. Ingest raw observations and standardize core fields (taxonomy, UTC timestamp, WGS84 coords).
2. Snap each record to `cell_id` and derive `region_id`.
3. Join static context (climate normals, elevation, landcover, biome/ecoregion).
4. Join temporal context (recent weather aggregates aligned to observation time).
5. Build PU rows:
    - positives from observations,
    - unlabeled/background samples stratified by region and time.
6. Build vectors:
    - `env_features`, `habitat_features`, `weather_features` with fixed order by `feature_version`.
7. Keep leakage-prone fields (`lat`, `lon`, `event_time_utc`, `source`) as metadata only; exclude from model input tensors.
8. Write partitioned Parquet by `split/year_month/region_id`.

Reference implementation script:

```bash
uv run python scripts/machine_learning/preprocess_training/cli.py \
    --input-root /data \
    --output-root /data/training_observation \
    --threads 16 \
    --background-ratio 1.0 \
    --overwrite-output
```

Notes:

- The script performs file-level multithreading for faster NVMe throughput.
- It keeps `lat/lon/time/source` as metadata fields and excludes them from model input vectors.
- Static and temporal context can be joined during this preprocessing step via configured context inputs, or pre-joined upstream into occurrence files; whichever path is used should be kept consistent per `feature_version`.
- Known issue: current background sampling is not yet spatially stratified over an explicit accessible-area `M` definition; treat this as a temporary approximation until stratified/background-area sampling is implemented.

## 10) Partition Strategy: Time vs Species

- Base dataset should stay partitioned by `split/year_month/region_id`.
- Why this base partitioning:
    - efficient spatiotemporal slices for training/validation,
    - clean support for blocked time/space evaluation,
    - avoids extreme small-file proliferation.
- Can it be partitioned by species? Yes, but usually as a derived dataset/view for head training jobs.
- Why not species as primary partition:
    - very high species cardinality creates many tiny partitions,
    - severe skew (common species huge, rare species tiny),
    - expensive global scans for encoder training.
- Practical compromise:
    - keep base table time/region partitioned,
    - optionally materialize species-bucket shards (e.g., hash buckets) for per-species training throughput.

## 11) Future Upgrades

- Hierarchical heads (kingdom→phylum→...→species) for better rare-species transfer.
- Distill encoder to an even smaller student for low-end phones.
- Add uncertainty estimate (MC dropout / deep ensemble heads) for abstention.
