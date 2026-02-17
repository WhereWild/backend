# Training Observation Schema

_This file is generated. Do not edit manually._

Canonical contract: [schemas/training_observation.schema.json](../schemas/training_observation.schema.json)

## Storage

- Format: `parquet`
- Partition keys: `split`, `year_month`, `region_id`
- Compression: `zstd`

## Partitioning Guidance

- Primary partitions are split/year_month/region_id for efficient spatiotemporal slicing and leakage-safe evaluation. Species partitioning is optional for derived head-training datasets (e.g., species_bucket) but not recommended as the base layout due to high cardinality and small-file risk.

## Feature Roles

- `input`: can be fed into model tensors.
- `metadata`: retained for joins, splits, QA, and bias auditing; excluded from model input.

## Columns

| Column | Type | Required | Feature Role | Description |
| --- | --- | --- | --- | --- |
| `sample_id` | `string` | yes | `metadata` | Globally unique row id (observation or background sample). |
| `observation_id` | `string` | no | `metadata` | Original occurrence id; null for generated background rows. |
| `species_key` | `int64` | yes | `metadata` | Species identifier used by per-species heads. |
| `presence_label` | `int8` | yes | `metadata` | 1 for positive, 0 for unlabeled/background sample. |
| `sample_weight` | `float32` | yes | `metadata` | Row weight for PU learning / sampling correction. |
| `cell_id` | `string` | yes | `metadata` | Spatial index cell id used to join environmental context. |
| `region_id` | `string` | yes | `metadata` | Region/biome partition id for stratified splits and sampling. |
| `lat` | `float64` | yes | `metadata` | Latitude in WGS84 decimal degrees. |
| `lon` | `float64` | yes | `metadata` | Longitude in WGS84 decimal degrees. |
| `event_time_utc` | `timestamp_ms_utc` | yes | `metadata` | Observation/background timestamp in UTC used for weather alignment. |
| `year_month` | `string` | yes | `metadata` | YYYY-MM partition key derived from event_time_utc. |
| `split` | `string` | yes | `metadata` | Dataset split label (train/val/test) from spatiotemporal splitter. |
| `source` | `string` | yes | `metadata` | Data source tag (e.g., gbif, inat, generated_background). |
| `feature_version` | `string` | yes | `metadata` | Version of feature engineering order and normalization. |
| `env_features` | `list<float32>` | yes | `input` | Dense static environmental feature vector (BIO, elevation, etc.). |
| `habitat_features` | `list<float32>` | no | `input` | Dense habitat/landcover neighborhood feature vector. |
| `weather_features` | `list<float32>` | no | `input` | Dense recent weather feature vector aligned to event_time_utc. |

## Validation

Run the validator against a parquet file or dataset root:

```bash
uv run python scripts/machine_learning/validate_training_schema.py \
  --schema schemas/training_observation.schema.json \
  --data /path/to/training_observation
```
