# Preprocessing Feature Transform Plan

This note sketches the file-level changes needed to normalize continuous features and one-hot encode categorical features during ML preprocessing.

## Goal

Move feature scaling and categorical expansion into preprocessing so the training dataset stores model-ready feature vectors instead of raw raster codes and raw source magnitudes.

The current pipeline writes fixed-width raw numeric vectors plus missing masks. That is acceptable for continuous features only if the scales are compatible, and it is not appropriate for categorical features encoded as class ids.

## Why change this

Current issues in `data_ml/species_observation_all`:

- Continuous features remain on very different scales.
- Several GIS/weather features marked as categorical in `config/gis/catalog.json` are currently passed through as raw ids.
- `aspect_deg` is circular and should not be treated as a plain scalar.

Examples observed in the current dataset:

- Continuous features such as `vpd`, `bio_12`, `soc`, and `elevation` have very different magnitudes.
- Categorical features such as `landcover`, `lithology`, `wrb`, `aspect`, `landform`, and `weather_code_simple` are stored as raw values like `52`, `9`, `0`, `4`, `1`, and `61`.

## Target representation

Preprocessing should emit:

- z-scored continuous features
- one-hot encoded categorical features
- sin/cos encoded circular features
- missing masks aligned to the transformed feature space

Suggested transform policy:

- Numeric: standardize with train-split mean and std
- Categorical: one-hot with an explicit unknown bucket
- Circular: replace raw angle with sin/cos pair

## Feature classes

Treat these catalog-backed fields as categorical:

- `koppen_geiger`
- `landcover`
- `lithology`
- `wrb`
- `aspect`
- `landform`
- `weather_code_simple`

Treat `aspect_deg` as circular:

- `aspect_deg_sin`
- `aspect_deg_cos`

Keep the remaining modeled GIS/weather features numeric and normalize them.

Open decision:

- If `aspect_deg` is retained as sin/cos, drop raw `aspect_deg`.
- Prefer dropping categorical `aspect` too unless there is a strong reason to keep both binned and continuous orientation signals.

## File changes

### `scripts/machine_learning/preprocess_training/transform.py`

Add transform-aware feature assembly instead of treating all feature columns as raw numerics.

Likely changes:

- add helpers to classify feature names by transform type using catalog metadata
- add a transform-spec data model for numeric, categorical, and circular features
- add a train-split fitting pass for numeric stats and categorical vocabularies
- replace `vector_from_columns(...)` / `build_feature_group_arrays(...)` with transform-aware builders
- expand missing masks to match transformed output width
- encode unknown categorical values safely

Key constraint:

- transformed output width will no longer equal the raw feature-template width

### `scripts/machine_learning/preprocess_training/pipeline.py`

Add orchestration for fitting and writing transform metadata.

Likely changes:

- fit transform metadata from train rows only
- write transform metadata into `_meta/feature_transforms.json`
- log transformed per-group dimensions in addition to raw template counts
- pass fitted transform metadata into each file transform call

### `scripts/machine_learning/preprocess_training/cli.py`

Add flags only if needed.

Possible options:

- `--normalization` with default `zscore`
- `--categorical-encoding` with default `onehot`
- `--disable-circular-encoding` only if you want a temporary escape hatch

This can also remain config-free initially if you want one canonical path.

### `scripts/machine_learning/feature_contract.py`

Extend the contract beyond raw grouped feature names.

Likely additions:

- helpers for transformed feature metadata
- optional distinction between raw source feature template and transformed model feature template
- stable naming rules for expanded columns such as `landcover__cat_52`, `weather_code_simple__cat_61`, `aspect_deg__sin`, and `aspect_deg__cos`

Recommended direction:

- keep the existing raw grouped template for source-layer discovery
- add a separate transformed template artifact for model input layout

### `scripts/machine_learning/train/data.py`

Update loading assumptions if transformed widths differ from raw template widths.

Likely changes:

- no conceptual change to tensor loading if preprocessing already writes final vectors
- preserve the current zero-missing-and-append-mask behavior
- ensure dimension probes and dataset readers operate on transformed vectors without assuming raw source widths

### `scripts/machine_learning/train/export.py`

Bundle export must carry transform metadata.

Likely changes:

- load `_meta/feature_transforms.json`
- include both raw source feature names and transformed feature metadata in the bundle
- distinguish between raw sampled GIS feature template and transformed model-input feature layout

This is required because runtime GIS sampling currently assumes bundle feature names map directly to raw raster/sampleable variables.

### `util/inference.py`

Inference must apply the same fitted transform used by preprocessing.

Likely changes:

- add runtime transform loading from the bundle
- after sampling raw GIS/weather values, apply numeric normalization, categorical one-hot expansion, and circular sin/cos encoding
- align runtime missing masks with transformed feature width
- use transformed width when checking input compatibility

Key point:

- this cannot remain a preprocessing-only change because sampled inference and weather-delta inference currently build model inputs directly from raw source feature names

### `tests/data/test_ml_pipeline.py`

Add regression coverage for the new transform path.

Needed tests:

- preprocessing writes transform metadata
- categorical features expand to expected one-hot width
- numeric features are normalized using train-split stats
- unseen categorical values map to unknown bucket
- circular features emit sin/cos columns
- export bundle round-trip preserves transform metadata
- runtime sampled inference produces model-ready transformed inputs

### `docs/ml_scripts.md`

Update the ML preprocessing and training docs.

Document:

- that preprocessing emits model-ready transformed features
- how normalization stats are fit
- how categorical vocabularies are derived
- retraining requirement after changing preprocessing format

### `docs/training_observation_schema.md`

Clarify that the stored vectors are transformed model features, not raw source feature ids.

Document:

- transformed feature vector semantics
- missing-mask semantics after one-hot expansion
- metadata files written under `_meta/`

## Metadata to write

Add a new artifact such as `_meta/feature_transforms.json` with fields like:

- `version`
- `raw_feature_template`
- `transformed_feature_template`
- `numeric_features` containing entries with `name`, `mean`, and `std`
- `categorical_features` containing entries with `name`, `vocabulary`, and `unknown_token`
- `circular_features` containing entries with `name` and `encoding`
- `group_output_slices`

This should be treated as the source of truth for model-input reconstruction outside preprocessing.

## Rollout order

Recommended implementation sequence:

1. Add transform metadata model and fitting pass in preprocessing.
2. Update preprocessing output vectors and masks.
3. Update training loaders and export to understand transformed metadata.
4. Update inference sampling to apply the same transform.
5. Add regression tests.
6. Update docs.

## Compatibility notes

This change is not artifact-compatible with existing checkpoints and bundles.

Expected impact:

- preprocessed datasets must be rebuilt
- encoder and head checkpoints must be retrained
- inference bundles must be re-exported

If backward compatibility is needed temporarily, gate the new path behind a preprocessing feature version such as `v2` and keep `v1` behavior intact until migration is complete.

## Recommended first implementation cut

The lowest-risk first cut is:

- normalize continuous features
- one-hot encode categorical features
- leave runtime inference support disabled for sampled fallback until transform metadata is wired through export and inference

That reduces ambiguity in preprocessing and training quickly while keeping the runtime migration explicit instead of silently incorrect.
