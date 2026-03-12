# ML Scripts Guide

This page explains the end-to-end machine learning workflow: preprocessing,
training, export, and inference.

Optional shell shortcuts:

```bash
alias ww-preprocess='uv run python -m scripts.machine_learning.preprocess_training.cli'
alias ww-train='uv run python -m scripts.machine_learning.train.cli'
```

## Scripts

- `scripts/machine_learning/preprocess_training/cli.py`
    - Builds a split-partitioned training parquet dataset from occurrence parquet files.
    - Entry script for the split implementation in `pipeline.py` and `transform.py`.
- `scripts/machine_learning/train/cli.py`
    - Trains the shared encoder (Stage B) and per-species PU heads (Stage C).
    - Entry script for `train_encoder.py`, `train_heads.py`, `model.py`, `losses.py`, `data.py`.
- `scripts/machine_learning/train/export.py`
    - Packages the encoder, species heads, and a pre-computed geocell feature table into a single `.pt` inference bundle.
    - Also embeds feature names so the inference engine can sample GIS rasters on the fly for catalog-backed groups and preserve the unsampleable `temporal` and `other` group widths.
- `scripts/machine_learning/validate_training_schema.py`
    - Validates dataset schema compatibility against `schemas/training_observation.schema.json`.
- `scripts/machine_learning/generate_training_schema_docs.py`
    - Regenerates `docs/training_observation_schema.md` from the schema contract.

## 1. Preprocess data

### Basic smoke run

```bash
uv run python -m scripts.machine_learning.preprocess_training.cli \
    --input-root ./data/species/taxonomy/Plantae_6 \
    --output-root ./data_ml/species_observation_canary_plants \
    --max-files 100 \
    --threads 8 \
    --overwrite-output
```

### PU-ready run (with unlabeled/background rows)

This uses pooled same-split background generation: for each target species,
donor rows are sampled from other-species positives in the same split,
with `(cell_id, year_month)` conflicts excluded.

```bash
uv run python -m scripts.machine_learning.preprocess_training.cli \
    --input-root ./data/species/taxonomy/Plantae_6 \
    --output-root ./data_ml/species_observation_canary_plants \
    --max-files 1000 \
    --threads 16 \
    --overwrite-output \
    --drop-missing-time \
    --background-ratio 1.0
```

### Large run (OOM-safer schema scan)

```bash
uv run python -m scripts.machine_learning.preprocess_training.cli \
    --input-root ./data/species/taxonomy/Plantae_6 \
    --output-root ./data_ml/species_observation_canary_plants \
    --max-files 10000 \
    --threads 8 \
    --overwrite-output \
    --background-ratio 1.0 \
    --template-scan-max-files 50000 \
    --max-rows-per-file 500000 \
    --keep-staging
```

### Full-data run in WSL (OOM-aware)

```bash
uv run python -m scripts.machine_learning.preprocess_training.cli \
    --input-root ./data/species/taxonomy/Plantae_6 \
    --output-root ./data_ml/species_observation_canary_plants \
    --max-files 0 \
    --template-scan-max-files 50000 \
    --threads 8 \
    --overwrite-output \
    --background-ratio 1.0 \
    --max-rows-per-file 500000 \
    --keep-staging
```

If you still see OOM kills (`exit code 137`), reduce `--template-scan-max-files` (for example to `20000`).

### Important flags

- `--glob` defaults to `**/occurrence.parquet`.
- `--drop-missing-time`
    - If set, drops rows with missing/unparseable event timestamps.
    - If omitted, keeps rows and applies fallback timestamps.
- `--background-ratio`
    - Default is `1.0` (one generated unlabeled row per positive row for each target species).
    - Donors come from other-species positives in the same split (`train`, `val`, `test` kept separate).
    - Rows that conflict with target-species positives on `(cell_id, year_month)` are excluded.
    - Set `0.0` for positives-only debug runs.
- `--template-scan-max-files`
    - Caps how many files are scanned for feature-template schema inference (`0` scans all discovered files).
- `--warn-min-cells-per-species`
    - Logs warning lines when a species has too few unique cells in a shard (helps detect split brittleness).
- `--final-write-batch-files`
    - Batches staged shards during final write to reduce file-descriptor and memory pressure.
- `--static-context-template` / `--static-context-path`
    - Optional static context join source keyed by `cell_id`.
- `--temporal-context-template` / `--temporal-context-path`
    - Optional temporal context join source keyed by `cell_id,year_month`.
- `--static-context-required` / `--temporal-context-required`
    - Fail fast when a configured join source is missing or lacks required keys.
- Auto context discovery
    - When explicit templates/paths are not set, the preprocessor looks for nearby context files in each occurrence directory.
- Uncatalogued numeric columns
    - Numeric columns from occurrence parquet files that are not represented in the GIS catalog are retained in `other_features`.
    - Numeric columns from context parquet files that are not represented in the GIS catalog are skipped.
    - The preprocessor logs warnings when uncatalogued numeric columns are encountered.
    - The preprocessor also writes `_meta/uncatalogued_columns.json` under the dataset root with kept/skipped examples.
- Feature grouping
    - Catalog-backed numeric columns are grouped into `bioclimate_features`, `landclass_features`, `terrain_features`, `edaphic_features`, and `temporal_features`.
    - Within each group, vector order comes from the discovered feature template written to `_meta/feature_template.json`.
    - `other_features` retains uncatalogued numeric columns from occurrence parquet files only.

### Not implemented yet

- Species-bucket or species-partitioned derived views for per-species head training (`species_bucket`) are separate derived-dataset steps and are not implemented by the current preprocessing CLI.

### Resume from staging after interrupted preprocess

If a long preprocess run finished transforms but stopped during
"Generating pooled unlabeled/background rows..." or final write, you can resume
without reprocessing all occurrence files.

`resume_from_staging` is explicit-action: by default it performs no work unless
you pass one or more `--resume-*` flags.

Resume base + background shards, write output partitions, then write template:

```bash
uv run python -m scripts.machine_learning.preprocess_training.resume_from_staging \
    --staging-dir ./data_ml/.species_observation_canary_plants_staging \
    --output-root ./data_ml/species_observation_canary_plants \
    --resume-base-files \
    --resume-background-files \
    --reuse-existing-background \
    --resume-output-files \
    --resume-feature-template-file \
    --background-ratio 1.0 \
    --background-split-chunk-rows 500000
```

Notes:

- `--resume-output-files` always clears the output directory before writing (full rewrite from staging).
- Use `--regenerate-background` with `--resume-background-files` to delete and rebuild existing `background_pooled_*.parquet` shards.
- If background shards already exist in staging, the resume CLI requires either `--reuse-existing-background` or `--regenerate-background` when `--resume-background-files` is set.
- Keep `--max-rows-per-file` aligned with your normal preprocess settings for consistent output sizing.
- `--resume-output-files` requires selecting at least one staging file type via `--resume-base-files` and/or `--resume-background-files`.

If you only need to (re)create metadata after a completed write:

```bash
uv run python -m scripts.machine_learning.preprocess_training.resume_from_staging \
    --output-root ./data_ml/species_observation_canary_plants \
    --resume-feature-template-file
```

If you only want to rebuild pooled background shards in staging (no final write):

```bash
uv run python -m scripts.machine_learning.preprocess_training.resume_from_staging \
    --staging-dir ./data_ml/.species_observation_canary_plants_staging \
    --output-root ./data_ml/species_observation_canary_plants \
    --resume-base-files \
    --resume-background-files \
    --regenerate-background \
    --background-ratio 1.0 \
    --background-split-chunk-rows 500000
```

## 2. Validate output schema

```bash
uv run python -m scripts.machine_learning.validate_training_schema \
    --schema schemas/training_observation.schema.json \
    --data ./data_ml/species_observation_canary_plants \
    --allow-extra-columns
```

Notes:

- The validator reads split-partitioned datasets written under `split=...` directories.
- `fixed_size_list<float>` vectors are accepted as compatible with schema `list<float>`.

## 3. Regenerate schema docs

```bash
uv run python -m scripts.machine_learning.generate_training_schema_docs
```

## Trainability checklist

Before starting model training, verify:

- Dataset validates successfully against schema contract.
- `presence_label` contains both `1` (positive) and `0` (unlabeled/background) for PU runs.
- `train/val/test` splits are all present.
- `year_month` coverage looks reasonable and not dominated by fallback timestamps.
- Feature vectors are non-null and consistent in dimensionality.
- Catalog-group widths in `_meta/feature_template.json` look reasonable for the source schemas you expect.
- `other_features` width looks reasonable for the occurrence schema you expect.

## 4. Train the model

Install training dependencies with: `uv sync --extra ml`.

### Stage B: Train shared encoder (self-supervised)

Current Stage B objective is masked reconstruction of observed feature values.

```bash
uv run python -m scripts.machine_learning.train.cli encoder \
    --data-root ./data_ml/species_observation_canary_plants \
    --output-dir ./checkpoints/canary_plants/encoder \
    --epochs 50 \
    --batch-size 32768
```

On CPU (slower, no AMP):

```bash
uv run python -m scripts.machine_learning.train.cli encoder \
    --data-root ./data_ml/species_observation_canary_plants \
    --output-dir ./checkpoints/canary_plants/encoder \
    --epochs 50 \
    --batch-size 2048 \
    --device cpu \
    --no-amp
```

### Stage C: Train per-species PU heads

```bash
uv run python -m scripts.machine_learning.train.cli heads \
    --data-root ./data_ml/species_observation_canary_plants \
    --encoder-checkpoint ./checkpoints/canary_plants/encoder/encoder_best.pt \
    --output-dir ./checkpoints/canary_plants/heads
```

### Both stages sequentially

```bash
uv run python -m scripts.machine_learning.train.cli all \
    --data-root ./data_ml/species_observation_canary_plants \
    --output-dir ./checkpoints/canary_plants \
    --epochs 50 \
    --head-epochs 50 \
    --batch-size 32768
```

### Training flags

- `--embed-dim`: encoder embedding dimension (default 128).
- `--hidden-dim`: encoder hidden layer dimension (default 256).
- `--epochs`: encoder training epochs (default 50).
- `--head-epochs`: epochs per species head (default 50).
- `--batch-size`: shared batch-size flag.
    - Stage B (`encoder`): encoder training mini-batch size (default 32768).
    - Stage C (`heads`): embedding pass chunk size only; per-species head optimization is full-batch.
- `--lr`: encoder peak learning rate (default 1e-3).
- `--head-lr`: species head learning rate (default 1e-2).
- `--recon-weight`: reconstruction loss weight for encoder pretraining.
- `--min-positives`: skip species with fewer positives (default 5).
- `--device`: auto (default), cuda, mps, cpu.
- `--no-amp`: disable automatic mixed precision.

### Output files

- `encoder_best.pt`: shared encoder checkpoint (Stage B).
- `species_heads.pt`: all per-species head weights + metadata (Stage C).

## 5. Export inference bundle

Package the trained model into a single `.pt` file for server-side deployment:

```bash
uv run python -m scripts.machine_learning.train.export \
    --encoder-checkpoint ./checkpoints/canary_plants/encoder/encoder_best.pt \
    --heads-checkpoint ./checkpoints/canary_plants/heads/species_heads.pt \
    --data-root ./data_ml/species_observation_canary_plants \
    --output ./checkpoints/canary_plants/inference_bundle.pt
```

The bundle contains:

- Encoder architecture config and weights.
- Per-species head weights and metadata (prior, val_loss, counts).
- Pre-computed geocell feature table (mean features per 0.25 deg cell from training data).
- Feature names per group (env, habitat, weather, other). GIS sampling only reconstructs catalog-backed env/habitat features; weather and other are emitted as missing in sampled-only paths.

The preprocessing step also writes `feature_template.json` under
`<output-root>/_meta/`. Export reads this file automatically. If it is missing (e.g. older
preprocessed datasets), export falls back to deriving catalog-backed feature names from the GIS
catalog; uncatalogued `other` names require the saved template.

## 6. Run inference / serve the API

### Load the bundle and predict in Python

```python
from util.inference import load_bundle, predict

load_bundle("checkpoints/canary_plants/inference_bundle.pt")
results = predict(lat=25.0, lon=-100.0, top_k=10)
```

### Start the FastAPI server

```bash
WHEREWILD_INFERENCE_BUNDLE=checkpoints/canary_plants/inference_bundle.pt \
    uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

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
    Controls sampling chunk size for `GET /api/predict/heatmap/stream`.
    Independent from model scoring batch size.
- `WHEREWILD_INFERENCE_STREAM_PREFETCH_CHUNKS`: integer `>=1` (default: `2`).
    Controls how many prepared stream chunks can queue ahead.
    Increase for more read-ahead overlap (uses more memory).
- `WHEREWILD_INFERENCE_PROFILE`: `0` (default) or `1`.
    When set, `GET /api/predict/heatmap` includes a `profile` object with
    stage timings.

Example forcing both inference compute and cell table to CUDA:

```bash
WHEREWILD_INFERENCE_DEVICE=cuda \
WHEREWILD_INFERENCE_CELL_TABLE_DEVICE=cuda \
WHEREWILD_INFERENCE_SAMPLE_WORKERS=1 \
WHEREWILD_INFERENCE_SAMPLE_CHUNK_SIZE=8192 \
WHEREWILD_INFERENCE_STREAM_PREFETCH_CHUNKS=2 \
WHEREWILD_INFERENCE_PROFILE=0 \
WHEREWILD_INFERENCE_BUNDLE=checkpoints/canary_plants/inference_bundle.pt \
    uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

If serving from the GDAL Docker container, rebuild after dependency changes in
`requirements.txt` (for example `torch` updates):

```bash
docker compose build gdal
docker compose up -d gdal
```

### Prediction endpoints

- `GET /api/predict?lat=&lon=&top_k=&threshold=` -- single-point prediction.
- `GET /api/predict/batch?coords=lat1,lon1,lat2,lon2&top_k=&threshold=` -- batch (max 100 coordinates).
- `GET /api/predict/heatmap?species_key=&min_lat=&min_lon=&max_lat=&max_lon=&resolution=` -- per-species probability grid with variable resolution.
- `GET /api/predict/info` -- model metadata (species count, cell count).

### On-the-fly GIS sampling

When a query coordinate does not fall in a pre-computed cell (i.e. no training
observations existed there), the inference engine samples static environmental
features (bioclim, elevation, slope, aspect, landcover, Koppen-Geiger) directly
from local GIS COG rasters via rasterio. Weather features are marked as
all-missing since they are time-dependent and not available without a timestamp.
The model was trained with masked inputs and tolerates this gracefully.

This means predictions work for any land coordinate on Earth, not just locations
where training data exists. Ocean points return empty results (no raster
coverage).

For the heatmap endpoint, missing cells are batch-sampled efficiently by opening
each raster once per 10-degree region tile rather than once per coordinate.

## Head hyperparameter tuning

### Sweep Stage C head hyperparameters (training-level)

Run a grid over `head_lr`, `head_weight_decay`, and `head_epochs`, training heads
for each trial and ranking by median species validation loss:

```bash
uv run python -m scripts.machine_learning.sweep_head_training \
    --data-root ./data_ml/species_observation_canary_plants \
    --encoder-checkpoint ./checkpoints/canary_plants/encoder/encoder_best.pt \
    --output-root ./tmp/head_sweep \
    --head-lr-grid 0.01,0.005,0.001 \
    --head-weight-decay-grid 0.001,0.0003,0.0001 \
    --head-epochs-grid 80,120
```

The summary file is written to `./tmp/head_sweep/sweep_results.json`, including
ranked trials and `best_trial`.

Current best (canary_plants, latest recorded `pass_f`):

- `head_lr=0.0088`
- `head_weight_decay=0.00055`
- `head_epochs=140`
