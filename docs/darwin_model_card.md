# Darwin Species Distribution Model

## 1. Goal

Predict species occurrence probability at arbitrary coordinates while:

- using one shared encoder instead of a full large model per species,
- supporting server-side inference over precomputed cells and sampled coordinates,
- scaling to large partitioned parquet training datasets,
- handling presence-only supervision with Positive-Unlabeled learning.

## 2. Model Structure

### 2.1 Shared encoder

The encoder consumes the model input vector assembled from transformed feature groups and aligned missing masks.

Input feature groups:

- `bioclimate`
- `landclass`
- `terrain`
- `temporal`
- `other`

Metadata such as `lat`, `lon`, `event_time_utc`, `cell_id`, `species_key`, and `source` are retained for joins, splits, and auditability, but are not fed directly into the model input tensor.

The encoder implementation is a tabular residual MLP defined in [scripts/machine_learning/train/model.py](../scripts/machine_learning/train/model.py):

- input projection: linear -> LayerNorm -> GELU
- two residual blocks
- output projection to a fixed embedding

Default dimensions in the training CLI:

- embedding dimension: `128`
- hidden dimension: `256`

### 2.2 Species heads

Per-species binary heads are trained on top of the frozen encoder embedding.

- species head: linear logistic classifier over the embedding
- optional combined head: multiclass linear head over eligible species for comparable ranking across species

This keeps species-specific parameters small and allows encoder training to be amortized across the full dataset.

## 3. Feature Pipeline

### 3.1 Raw feature typing

Raw feature datatype is defined by GIS catalog metadata in [config/gis/catalog.json](../config/gis/catalog.json), not inferred from observed values.

- `numeric` features are normalized with train-split mean and standard deviation
- `categorical` features are one-hot encoded with an explicit unknown bucket
- `circular` features are expanded to sin/cos pairs

The fitted transform metadata is written to `_meta/feature_transforms.json` during preprocessing and reused during export and inference.

### 3.2 Preprocessed dataset layout

The training dataset stores transformed vectors and aligned missing masks for each feature group:

- `bioclimate_features` and `bioclimate_missing_mask`
- `landclass_features` and `landclass_missing_mask`
- `terrain_features` and `terrain_missing_mask`
- `temporal_features` and `temporal_missing_mask`
- `other_features` and `other_missing_mask`

The preprocessing flow:

1. Standardize raw observations and required metadata.
2. Snap observations to `cell_id` and derive split metadata.
3. Join static GIS context.
4. Join temporal context by `(cell_id, year_month)`.
5. Fit train-split feature transforms.
6. Write transformed vectors, masks, and metadata to split-partitioned parquet.
7. Generate pooled unlabeled/background rows for PU training when enabled.

Missingness is represented explicitly through masks rather than by training on sentinel-filled feature values.

### 3.3 Temporal features

Temporal model inputs are not raw timestamps. They are transformed float vectors with aligned masks.

- `event_time_utc` is used to derive `year_month`
- `year_month` is used for temporal joins and split assignment
- the model receives temporal feature values and temporal missing masks, not raw datetime fields

For the current canary dataset, temporal inputs are mostly numeric weather-history aggregates over fixed windows, plus categorical `weather_code_simple`.

## 4. Positive-Unlabeled Training

Species heads are trained with non-negative PU risk rather than standard positive-vs-negative binary labels.

For species `s`:

- positives are observed occurrences for `s`
- unlabeled rows are sampled from other-species positive rows within the same split
- candidate unlabeled rows are excluded when their `(cell_id, year_month)` collides with a positive row for `s`

The per-species prior is estimated with empirical-Bayes smoothing:

`raw_s = n_pos_s / n_rows_s`

`π_s = (n_pos_s + α * p_global) / (n_rows_s + α)`

with `α = 50` and `p_global` equal to the train-split global positive rate.

The PU objective is:

$$
R(f) = \pi_s \mathbb{E}_{x \sim P_s}[\ell(f(x))] + \max\Bigl(0,\ \mathbb{E}_{x \sim U_s}[\ell(-f(x))] - \pi_s \mathbb{E}_{x \sim P_s}[\ell(-f(x))]\Bigr)
$$

where `f(x) = H_s(E(x))`.

## 5. Training Stages

### 5.1 Stage B: encoder training

Encoder training uses masked reconstruction of observed features.

- encoder: [SharedEncoder in model.py](../scripts/machine_learning/train/model.py)
- auxiliary head: [AuxDecoder in model.py](../scripts/machine_learning/train/model.py)
- loss: reconstruction over observed feature values using the stored masks

Training entrypoint: [scripts/machine_learning/train/cli.py](../scripts/machine_learning/train/cli.py)

Default encoder training settings:

- epochs: `50`
- batch size: `32768`
- learning rate: `1e-3`
- weight decay: `1e-4`
- data mode: `chunk-cached`
- chunk rows: `400000`
- prefetch chunks: `3`
- adaptive prefetch: enabled
- shuffle mode: `block`

### 5.2 Stage C: species head training

Head training freezes the encoder, materializes train and validation embeddings to on-disk memmaps, and trains per-species PU heads over those cached embeddings.

- train embeddings cache: `_heads_train_cache/train_embeddings.f16.mmap`
- validation embeddings cache: `_heads_val_cache/val_embeddings.f16.mmap`
- trained species heads: `species_heads.pt`

Default head-training settings:

- minimum positives per species: `50`
- head epochs: `50`
- head learning rate: `1e-2`
- head weight decay: `1e-3`
- combined head: disabled by default

The memmap caches are performance artifacts used to avoid recomputing encoder outputs for every head-training pass.

## 6. Exported Bundle

The export step packages the trained model into a single inference bundle.

Bundle contents include:

- encoder weights
- per-species head weights
- optional combined-head weights
- species metadata
- geocell feature table built from the training dataset
- raw feature names
- transformed model feature names
- fitted feature transform metadata

Export entrypoint: [scripts/machine_learning/train/export.py](../scripts/machine_learning/train/export.py)

This allows runtime inference to reconstruct model-ready inputs from sampled raw features using the same fitted transform specification used during preprocessing.

## 7. Inference

Runtime inference is implemented in [util/inference.py](../util/inference.py).

The server loads the exported bundle once and then scores requests by either:

- looking up precomputed cell-table entries for known cells, or
- sampling raw GIS and temporal features for arbitrary coordinates, transforming them with the saved transform metadata, and then scoring the resulting model input

Static sampled feature groups:

- `bioclimate`
- `landclass`
- `terrain`

Unsampled groups that are still part of the model input:

- `temporal`
- `other`

Temporal inference supports two modes:

- `missing`: temporal channels remain masked
- `current`: temporal rasters are sampled, transformed, and inserted into the model input

Inference defaults to CUDA when available and otherwise falls back to CPU. Device placement can be overridden through runtime environment variables.

## 8. Data Splits and Validation

The preprocessing pipeline assigns deterministic space-time splits by hashing `(cell_id, year_month)` into `train`, `val`, and `test`.

The canonical dataset contract is defined in [schemas/training_observation.schema.json](../schemas/training_observation.schema.json), with generated documentation in [docs/training_observation_schema.md](training_observation_schema.md).

Schema validation is performed with the training-schema validation script against the written parquet dataset.

## 9. Operational Notes

- Preprocessing writes `_meta/feature_template.json`, `_meta/feature_transforms.json`, and `_meta/uncatalogued_columns.json`.
- Resume-from-staging preserves these metadata files so interrupted large preprocess runs can be published safely.
- Background generation uses pooled same-split donor rows and a configurable `--background-ratio`.
- The default background ratio is `1.0`, which yields one unlabeled/background row per positive row.

## 10. Future Work

- spatially stratified or explicitly accessible-area background sampling
- richer evaluation reporting such as PR-AUC, calibration metrics, and prevalence-bin summaries
- broader blocked validation protocols
- hierarchical or taxonomically structured heads
- smaller distilled deployment variants when needed
