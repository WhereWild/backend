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

The per-species prior uses a fixed positive prior:

`π_s = 0.05`

This fixed prior is applied to every per-species head during Stage C training and
is recorded in checkpoint metadata as `prior_pi` with `prior_mode = "fixed"`.

The PU objective is:

$$
R(f) = \pi_s \mathbb{E}_{x \sim P_s}[\ell(f(x))] + \max\Bigl(0,\ \mathbb{E}_{x \sim U_s}[\ell(-f(x))] - \pi_s \mathbb{E}_{x \sim P_s}[\ell(-f(x))]\Bigr)
$$

where `f(x) = H_s(E(x))`.

## 5. Training Summary

Training proceeds in two stages:

- Stage B pretrains the shared encoder with masked reconstruction of observed
  feature values.
- Stage C freezes the encoder and trains per-species PU heads on cached
  embeddings, with an optional combined head for cross-species ranking.

The cached embeddings are a training-time performance detail used to avoid
recomputing encoder outputs on every head-training pass.

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

This allows runtime inference to reconstruct model-ready inputs from sampled raw features using the same fitted transform specification used during preprocessing.

Important serving detail:

- the exported cell table is observation-derived coverage from the training
  dataset, not a dense global grid;
- coordinates outside that observed cell coverage still require runtime GIS
  sampling.

## 7. Inference

Runtime inference is implemented in [util/inference.py](../util/inference.py).

The server loads the exported bundle once and then scores requests by either:

- looking up precomputed cell-table entries for known cells, or
- sampling raw GIS and temporal features for arbitrary coordinates, transforming them with the saved transform metadata, and then scoring the resulting model input

For heatmap scoring, feature-source selection is resolution-dependent:

- at native-or-coarser resolution, inference prefers the exported cell table
  and falls back to sampled GIS features when allowed;
- at finer-than-native resolution, inference prefers sampled GIS features when
  the bundle and runtime support them, with cell-table fallback when needed.

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

Current route-level behavior is more limited than the inference layer:

- the general inference helpers support both temporal modes;
- the normal Darwin tile heatmap route still serves the static path and does
  not yet expose route-level temporal controls;
- the weather-delta ranking path already uses live temporal inference.

The weather-delta path uses a hybrid serving strategy when possible:

- reuse static features from the exported cell table;
- sample and transform only the temporal slice;
- overwrite the temporal span in the model input;
- fall back to fully sampled weather features only when the coordinate is not
  covered by the cell table.

Inference defaults to CUDA when available and otherwise falls back to CPU. Device placement can be overridden through runtime environment variables.

## 8. Data Splits and Validation

The preprocessing pipeline assigns deterministic space-time splits by hashing `(cell_id, year_month)` into `train`, `val`, and `test`.

The canonical dataset contract is defined in [schemas/training_observation.schema.json](../schemas/training_observation.schema.json), with generated documentation in [docs/training_observation_schema.md](training_observation_schema.md).

Schema validation is performed with the training-schema validation script against the written parquet dataset.

## 9. Operational Notes

- Runtime inference can score from either cell-table features or sampled GIS
  features depending on request resolution and bundle support.
- The exported bundle is self-contained for serving, but sampled fallback still
  depends on runtime access to GIS rasters and temporal rasters.
- Device placement can be controlled with runtime environment variables for the
  main inference path and cell-table placement.

Detailed preprocessing, training, export, and CLI defaults are documented in
[docs/ml_scripts.md](ml_scripts.md).

## 10. Future Work

- spatially stratified or explicitly accessible-area background sampling
- richer evaluation reporting such as PR-AUC, calibration metrics, and prevalence-bin summaries
- broader blocked validation protocols
- hierarchical or taxonomically structured heads
- smaller distilled deployment variants when needed
- route-level live temporal Darwin tiles with temporal-aware cache versioning
