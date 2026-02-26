# Four-Species Global Surface Model Card

## Scope

This model is a four-species prototype for global suitability surface inference:

- Escobaria vivipara
- Haliaeetus leucocephalus
- Spea intermontana
- Hypaurotis crysalus

It outputs suitability scores in `[0,1]` via a shared encoder and species embedding head.

## Data

- Positives: filtered occurrence rows from species `occurrence.parquet`
- Background: accessibility-weighted sampled rows (default 10x)
- Hard negatives: sampled from ecologically similar species rows (landcover / biome overlap)

## Model

- Encoder: tabular geospatial covariates + lat/lon harmonics
- Head: species embedding dot product with encoder state + species bias
- Objective: focal-weighted BCE for presence-vs-background
- Calibration: per-species Platt scaling (`calibration.json`)

## Generalization Controls

- Spatial split by default (`--split-method spatial`)
- Optional temporal split (`--split-method temporal`)
- Validation metrics include AUC, PR-AUC, ECE, and top-k regional precision

## Inference + Serving

- Offline builder script: `scripts/build_four_species_global_surface.py`
- Precomputed artifacts:
    - Surface cell parquet partitions
    - Per-species GeoTIFF region outputs
    - Surface manifest and latest pointer
- Serving endpoint: `/species/{taxon_id}/inference-heatmap`
    - Primary: precomputed surfaces
    - Fallback: legacy point scoring

## Model Interface (Current Contract)

### Artifact Interface (`model.npz`)

- Current model family: `embedding_head_v1`
- Required keys:
    - `model_family`
    - `encoder_weights`, `encoder_bias`
    - `species_embeddings`, `species_bias`
    - `calibration_scale`, `calibration_bias`
    - `mean`, `std`
    - `feature_columns`
    - `species_names`, `class_names`
- Backward compatibility:
    - Legacy softmax artifacts with `weights`, `bias`, and `class_names` are still supported.

### Batch Scoring Interface

- Script: `scripts/ml/score_four_species_prototype.py`
- Input:
    - `--model-path` to `model.npz`
    - `--input` as `.parquet` or `.csv`
    - optional `--max-rows`
- Output per row:
    - `scores` (species -> score in `[0,1]`)
    - `top_species`
    - `top_score`
    - optional `decimalLatitude` / `decimalLongitude` pass-through

### API Interface (`/species/{taxon_id}/inference-heatmap`)

- Query parameters:
    - `bbox` (optional)
    - `zoom` (default `5`)
    - `max_cells` (range `[100, 20000]`)
    - `time_slice` (default `latest`)
- Response fields:
    - `speciesId`, `modelSpecies`, `zoom`, `cellSizeDeg`
    - `cells` with `{lat, lon, count, score, intensity}`
    - `source` (`precomputed_surface` or `legacy_fallback`)
    - `timeSlice` when precomputed surfaces are used
- Rendering note:
    - For precomputed surfaces, `count` is often `1`; clients should style heatmaps primarily by `intensity` or `score`.

## Operational Cadence

- Weekly retrain + surface rebuild
- Daily species-head refresh (config contract; implementation path retained)

## Known Limitations

- Current implementation is CPU-first (NumPy), not the full mixed-precision GPU training target yet.
- Temporal weather covariates are not yet materialized in the global raster surface builder.
- PMTiles generation is not yet included; GeoTIFF + parquet serving path is implemented.
