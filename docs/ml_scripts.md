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
  --fallback-time-policy drop \
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
    --fallback-time-policy keep \
    --background-ratio 1.0 \
    --progress-interval-seconds 15 \
    --log-slow-file-seconds 10 \
    --log-slow-read-seconds 10 \
    --schema-log-interval-files 30 \
    --template-scan-max-files 50000 \
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
    --fallback-time-policy keep \
    --background-ratio 1.0 \
    --progress-interval-seconds 15 \
    --log-slow-file-seconds 10 \
    --log-slow-read-seconds 10 \
    --schema-log-interval-files 30 \
    --max-rows-per-file 500000 \
    --keep-staging
```

If you still see OOM kills (`exit code 137`), reduce `--template-scan-max-files` (for example to `20000`).

### Important flags

- `--glob` defaults to `**/occurrence.parquet`.
- `--fallback-time-policy`
    - `keep`: keep rows with missing/unparseable event time (filled to fallback).
    - `drop`: drop those rows.
- `--background-ratio`
    - `0.0`: positives only.
    - `1.0`: one generated unlabeled row per positive row.
- `--progress-interval-seconds`
    - Heartbeat interval when no files complete.
- `--log-slow-file-seconds`
    - Logs full file transforms that take at least this many seconds.
- `--log-slow-read-seconds`
    - Logs parquet/schema read operations that take at least this many seconds.
- `--schema-log-interval-files`
    - Logs progress during global feature-template schema scan.
- `--template-scan-max-files`
    - Caps how many files are scanned for feature-template schema inference (`0` scans all discovered files).

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
  `split=.../year_month=.../region_id=...`.
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
