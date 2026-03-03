# ML Scripts Guide

This page explains how to use the machine learning data scripts in this repo.

Optional shell shortcut:

```bash
alias ww-preprocess='uv run python scripts/machine_learning/preprocess_training/cli.py'
```

Then use `ww-preprocess ...` instead of typing the full command.

## Scripts

- `scripts/machine_learning/preprocess_training/cli.py`
    - Builds partitioned training parquet dataset from occurrence parquet files.
    - Entry script for the split implementation in `pipeline.py` and `transform.py`.
- `scripts/machine_learning/validate_training_schema.py`
    - Validates dataset schema compatibility against `schemas/training_observation.schema.json`.
- `scripts/machine_learning/generate_training_schema_docs.py`
    - Regenerates `docs/training_observation_schema.md` from the schema contract.

## 1) Preprocess data

### Basic smoke run

```bash
uv run python scripts/machine_learning/preprocess_training/cli.py \
  --input-root ./data \
  --output-root ./data/training_observation_smoke \
  --max-files 100 \
  --threads 8 \
  --overwrite-output
```

### PU-ready run (with unlabeled/background rows)

```bash
uv run python scripts/machine_learning/preprocess_training/cli.py \
  --input-root ./data \
  --output-root ./data/training_observation_smoke \
  --max-files 1000 \
  --threads 16 \
  --overwrite-output \
    --drop-missing-time \
  --background-ratio 1.0
```

### Large run (OOM-safer schema scan)

```bash
uv run python scripts/machine_learning/preprocess_training/cli.py \
    --input-root ./data \
    --output-root ./data/species_observation_canary \
    --max-files 10000 \
    --threads 8 \
    --overwrite-output \
    --background-ratio 1.0 \
    --template-scan-max-files 50000 \
    --partition-mode split/year_month \
    --max-rows-per-file 500000 \
    --keep-staging
```

### Full-data run in WSL (OOM-aware)

```bash
uv run python scripts/machine_learning/preprocess_training/cli.py \
    --input-root ./data \
    --output-root ./data/species_observation_canary \
    --max-files 0 \
    --template-scan-max-files 50000 \
    --threads 8 \
    --overwrite-output \
    --background-ratio 1.0 \
    --partition-mode split/year_month \
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
    - Default is `1.0` (one generated unlabeled row per positive row).
    - Set `0.0` for positives-only debug runs.
- `--template-scan-max-files`
    - Caps how many files are scanned for feature-template schema inference (`0` scans all discovered files).
- `--partition-mode`
    - `split`: fewest partitions, usually fewest output files.
    - `split/year_month`: good training default to reduce file counts while preserving time partitions.
    - `split/year_month/region_id`: most granular; usually highest file counts.
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

### Not implemented yet

- Species-bucket partitioned view for per-species head training (`species_bucket`) is a separate derived-dataset step and is not implemented by the current preprocessing CLI.
- Current tooling only builds the base dataset partitioned by `split/year_month/region_id`.

## 2) Validate output schema

```bash
uv run python scripts/machine_learning/validate_training_schema.py \
  --schema schemas/training_observation.schema.json \
  --data ./data/training_observation_smoke \
  --partitioning hive \
  --allow-extra-columns
```

Notes:

- Use `--partitioning hive` for partitioned datasets written as
    `split=...`, `split=.../year_month=...`, or `split=.../year_month=.../region_id=...`.
- `fixed_size_list<float>` vectors are accepted as compatible with schema `list<float>`.

## 3) Regenerate schema docs

```bash
uv run python scripts/machine_learning/generate_training_schema_docs.py
```

## Trainability checklist

Before starting model training, verify:

- Dataset validates successfully against schema contract.
- `presence_label` contains both `1` (positive) and `0` (unlabeled/background) for PU runs.
- `train/val/test` splits are all present.
- `year_month` coverage looks reasonable and not dominated by fallback timestamps.
- Feature vectors are non-null and consistent in dimensionality.
