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
    - Also embeds raw feature names, transformed model feature names, and transform metadata so the inference engine can sample raw GIS rasters on the fly and reconstruct model-aligned inputs.
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
    --overwrite-output \
    --drop-missing-time
```

### Large run (OOM-safer schema scan)

This example sets `--template-scan-max-files 50000` as an explicit override for large runs. It is not the default.

```bash
uv run python -m scripts.machine_learning.preprocess_training.cli \
    --input-root ./data/species/taxonomy/Plantae_6 \
    --output-root ./data_ml/species_observation_canary_plants \
    --max-files 10000 \
    --overwrite-output \
    --template-scan-max-files 50000 \
    --keep-staging
```

### Full-data run in WSL (OOM-aware)

This example also overrides `--template-scan-max-files` to `50000`; the CLI default remains `0`.

```bash
uv run python -m scripts.machine_learning.preprocess_training.cli \
    --input-root ./data/species/taxonomy/Plantae_6 \
    --output-root ./data_ml/species_observation_canary_plants \
    --max-files 0 \
    --template-scan-max-files 50000 \
    --overwrite-output \
    --keep-staging
```

If you still see OOM kills (`exit code 137`), reduce `--background-split-chunk-rows`,
reduce `--max-rows-per-file`, or lower `--template-scan-max-files`.

Background generation now writes bounded background staging shards internally
instead of materializing one large generated table per split chunk. This lowers
peak RAM during pooled background generation, especially when `--background-ratio`
is greater than `1.0`.

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
- `--background-split-chunk-rows`
    - Default is `50000`.
    - Lower values reduce peak RAM during pooled background generation.
    - Higher values can improve throughput but increase the size of in-memory split chunks.
- `--max-rows-per-file`
    - Default is `150000`.
    - Lower values reduce per-file write pressure during final parquet output.
    - Higher values reduce file counts but increase memory pressure during final write.
- `--overwrite-output`
    - Clears the staging directory before a fresh run.
    - Keeps the previous published dataset in place until the replacement dataset has been written and verified.
- `--template-scan-max-files`
    - Default is `0`.
    - Caps how many files are scanned for feature-template schema inference (`0` scans all discovered files).
    - Large-run examples in this doc use `50000` as a manual override, not as the default.
- `--warn-min-cells-per-species`
    - Logs warning lines when a species has too few unique cells in a shard (helps detect split brittleness).
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
    - Catalog-backed columns are grouped into `bioclimate_features`, `landclass_features`, `terrain_features`, and `temporal_features`.
    - Stored vectors are model-ready transformed features, not raw source layer values.
    - Raw source ordering comes from `_meta/feature_template.json`; transformed model ordering comes from `_meta/feature_transforms.json`.
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
    --resume-feature-template-file
```

Notes:

- `--resume-output-files` writes a verified replacement dataset to a temporary directory and only publishes it after parquet verification passes.
- Resume preserves metadata from the published dataset when present, and otherwise falls back to `staging/_meta`, including `_meta/feature_transforms.json`.
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
    --regenerate-background
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
- `_meta/feature_transforms.json` looks consistent with the intended model layout and transform policy.
- `other_features` width looks reasonable for the occurrence schema you expect.

## 4. Train the model

Install training dependencies with: `uv sync --extra ml`.

### Stage B: Train shared encoder (self-supervised)

Current Stage B objective is masked reconstruction of observed feature values.

```bash
uv run python -m scripts.machine_learning.train.cli encoder \
    --data-root ./data_ml/species_observation_canary_plants \
    --output-dir ./checkpoints/canary_plants/encoder
```

On CPU (slower, no AMP):

```bash
uv run python -m scripts.machine_learning.train.cli encoder \
    --data-root ./data_ml/species_observation_canary_plants \
    --output-dir ./checkpoints/canary_plants/encoder \
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

Train Stage C with the shared combined species-ranking head enabled:

```bash
uv run python -m scripts.machine_learning.train.cli heads \
    --data-root ./data_ml/species_observation_canary_plants \
    --encoder-checkpoint ./checkpoints/canary_plants/encoder/encoder_best.pt \
    --output-dir ./checkpoints/canary_plants/heads \
    --train-combined-head
```

### Both stages sequentially

```bash
uv run python -m scripts.machine_learning.train.cli all \
    --data-root ./data_ml/species_observation_canary_plants \
    --output-dir ./checkpoints/canary_plants
```

### Training flags

- `--embed-dim`: encoder embedding dimension (default 128).
- `--hidden-dim`: encoder hidden layer dimension (default 256).
- `--epochs`: encoder training epochs (default 50).
- `--head-epochs`: epochs per species head (default 50).
- `--combined-head-epochs`: epochs for the shared multiclass combined head (default 10).
- `--batch-size`: shared batch-size flag.
    - Stage B (`encoder`): encoder training mini-batch size (default 32768).
    - Stage C (`heads`): embedding pass chunk size only; per-species head optimization is full-batch.
- `--lr`: encoder peak learning rate (default 1e-3).
- `--head-lr`: species head learning rate (default 1e-2).
- `--combined-head-batch-size`: optimization mini-batch size for the shared multiclass combined head over frozen embeddings (default 4096).
- `--combined-head-lr`: combined-head learning rate (default 5e-3).
- `--recon-weight`: reconstruction loss weight for encoder pretraining.
- `--min-positives`: skip species with fewer positives (default 50).
- `--train-combined-head`: enable the shared multiclass combined species head (default disabled).
- `--combined-head-min-positives`: minimum positives for a species to participate in the combined head (default 50).
- `--combined-head-weight-decay`: combined-head weight decay (default 1e-4).
- `--device`: auto (default), cuda, mps, cpu.
- `--no-amp`: disable automatic mixed precision.

### Output files

- `encoder_best.pt`: shared encoder checkpoint (Stage B).
- `species_heads.pt`: per-species head weights + metadata, and when enabled also the shared combined-head weights plus the ordered species key list used by that head (Stage C).

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
- Optional shared combined-head weights, species ordering, and metadata when trained with `--train-combined-head`.
- Pre-computed geocell feature table (mean features per 0.25 deg cell from training data).
- `raw_feature_names` for GIS/context sampling, `feature_names` for model input layout, and `feature_transforms` for reconstructing transformed runtime inputs. GIS sampling reconstructs catalog-backed static groups, while runtime paths can also fill temporal features from current rasters under `data/gis/temporal` when using the combined-head weather-delta helpers.

The preprocessing step writes both `feature_template.json` and
`feature_transforms.json` under `<output-root>/_meta/`. Export reads these files automatically.
If `feature_template.json` is missing (for example older preprocessed datasets), export falls back
to deriving catalog-backed raw feature names from the GIS catalog; uncatalogued `other` names still
require the saved template. Without `feature_transforms.json`, export can still build a bundle, but
runtime sampled inference falls back to identity feature handling rather than the fitted transform path.

## 6. Run inference / serve the API

### Load the bundle and prepare a heatmap stream in Python

```python
from util.inference import load_bundle, predict_heatmap_stream

load_bundle("checkpoints/canary_plants/inference_bundle.pt")
stream_result = predict_heatmap_stream(
    11498251,
    (24.0, -106.0, 32.0, -94.0),
)
```

### Load the bundle and rank species with the combined head

```python
from util.inference import load_bundle, rank_species_coords, rank_species_weather_delta_coords

load_bundle("checkpoints/canary_plants/inference_bundle.pt")

ranked_species, _ = rank_species_coords(
    [(31.5, -100.2)],
    resolution_hint=0.25,
    top_k=25,
)

weather_uplift, _ = rank_species_weather_delta_coords(
    [(31.5, -100.2)],
    top_k=25,
)
```

Notes:

- `rank_species_coords(...)` returns combined-head rankings only for species that also have per-species heads in the loaded bundle.
- `rank_all_species_coords(...)` returns the full combined-head ranking space, including species that may not have per-species heads.
- `rank_species_weather_delta_coords(...)` compares a masked-temporal baseline pass against a current-weather temporal pass and ranks species by `delta_logit` uplift.

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
    Controls sampling chunk size for heatmap job streams.
    Independent from model scoring batch size.
- `WHEREWILD_INFERENCE_STREAM_PREFETCH_CHUNKS`: integer `>=1` (default: `2`).
    Controls how many prepared stream chunks can queue ahead.
    Increase for more read-ahead overlap (uses more memory).

Example forcing both inference compute and cell table to CUDA:

```bash
WHEREWILD_INFERENCE_DEVICE=cuda \
WHEREWILD_INFERENCE_CELL_TABLE_DEVICE=cuda \
WHEREWILD_INFERENCE_SAMPLE_WORKERS=1 \
WHEREWILD_INFERENCE_SAMPLE_CHUNK_SIZE=8192 \
WHEREWILD_INFERENCE_STREAM_PREFETCH_CHUNKS=2 \
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

- `GET /api/species/{taxon_id}/heatmap` -- heatmap tile metadata for one species.
- `GET /api/species/{taxon_id}/heatmap/tiles/{z}/{x}/{y}.png` -- rendered PNG heatmap tiles.
- `POST /api/predict/heatmap-jobs` -- create a cancellable heatmap job.
- `GET /api/predict/heatmap-jobs/{job_id}/stream` -- stream heatmap NDJSON events.
- `DELETE /api/predict/heatmap-jobs/{job_id}` -- cancel a stale or running heatmap job.

Tile endpoint notes:

- Tile requests are synchronous request/response renders, not job resources.
- The backend currently relies on client/proxy caching headers rather than a
    built-in rendered-tile cache.
- High zoom tiles may render a reusable parent tile and crop the requested
    subtile.

### On-the-fly GIS sampling

When a query coordinate does not fall in a pre-computed cell (i.e. no training
observations existed there), the inference engine samples static environmental
features (bioclim, elevation, slope, aspect, landcover, Koppen-Geiger) directly
from local GIS COG rasters via rasterio. Temporal features are marked as
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
