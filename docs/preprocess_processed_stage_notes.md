# Preprocess "Processed" Stage Notes

This note records the most obvious reasons the preprocessing `Processed X/Y files`
stage can be slow, along with the lowest-risk optimization directions.

## What The "Processed" Stage Actually Includes

The progress counter in the preprocess pipeline does not advance after a simple
file read. A source file is only counted as processed after a worker finishes:

1. reading the occurrence parquet into pandas;
2. resolving and optionally loading static and temporal context parquet files;
3. parsing timestamps, deriving `cell_id` and `region_id`, and assigning splits;
4. merging context features when configured;
5. building transformed feature arrays and missing masks;
6. generating `sample_id` values;
7. writing the staged parquet shard with zstd compression.

That means the `Processed X/Y files` stage is a combined read, transform, and
write path, not just a lightweight transform counter.

## Obvious Reasons It Can Be Slow

### 1. The dataset is traversed more than once before final publish

Preprocessing does not stream directly from raw occurrence files to the final
dataset in one pass.

Before the main processed-file loop starts, the pipeline first:

- scans schemas to build the raw feature template;
- reads source files again to fit feature transforms from train-split rows.

After that, the processed-file loop reads the source files again to build the
staged shards.

This is not necessarily wrong. It is the current design tradeoff for deriving a
stable global feature layout and fitted transform metadata without trying to
hold the full dataset in memory.

### 2. Per-file context loading and merge work is non-trivial

When static or temporal context is present, each file can trigger:

- context parquet loading;
- projection down to join keys plus recognized numeric feature columns;
- numeric coercion for mergeable columns;
- tie-break key construction for duplicate context rows;
- sort, dedupe, and merge work.

The merge path is especially not free because duplicate context keys are
resolved deterministically rather than by a simple first-row or last-row rule.

### 3. There is still a lot of Python object churn in the hot path

The transform path currently does several Python-heavy operations per row or per
column group, including:

- generating one `uuid4` string per output row for `sample_id`;
- building `cell_id`, `region_id`, and split assignments via Python loops;
- materializing multiple object-backed lists before Arrow conversion;
- converting pandas columns to Arrow arrays field by field.

On large files, this can easily dominate the wall clock even if disk I/O is not
the main bottleneck.

### 4. Staged shard writes are compressed parquet writes, not cheap flushes

Each transformed file ends with a parquet write using zstd compression. That is
usually a good storage tradeoff, but it adds noticeable CPU cost to the same
stage that increments the processed counter.

### 5. Threading is file-level, so one slow file can keep the counter stuck

The processed counter advances only when a file-level future completes. If a few
large files are slow because of context joins, heavy feature transforms, or slow
zstd writes, the counter can appear stalled even though workers are still busy.

## Memory-Safe Optimization Directions

These are the lowest-risk places to improve throughput without changing the
pipeline into a high-memory design.

### 1. Reduce Python work in row identity and Arrow conversion

The safest likely win is reducing Python object creation in the final transform
assembly.

Candidate changes:

- replace per-row `uuid4()` generation with a cheaper deterministic sample id
  scheme;
- avoid unnecessary `.tolist()` materialization before Arrow conversion;
- keep values in NumPy or Arrow-friendly buffers for longer.

Why this is low risk:

- it targets CPU and Python allocation overhead;
- it should not require broader caching;
- it may reduce transient memory rather than increase it.

### 2. Vectorize derived key generation more aggressively

The `cell_id`, `region_id`, and split derivation path is currently simple and
clear, but it still relies on Python loops over coordinates.

If those become a measurable hotspot, more vectorized implementations would be a
reasonable next step.

Why this is low risk:

- the work stays row-local;
- it does not require holding more files in memory at once;
- it mostly trades Python overhead for array operations.

### 3. Cache a more useful context representation

The current code already caches context table loads for the process lifetime,
which is good. But if the same context file is reused across many occurrence
files, it may be better to cache a projected and pre-deduped join-ready version
instead of repeating expensive merge preparation work per file.

Why this is usually low risk:

- it improves reuse of data that is already being kept around;
- it is bounded by the number of reused context files rather than the number of
  occurrence files;
- it should help CPU more than it increases memory.

### 4. Measure read, merge, transform, and write separately

Before changing behavior, the most practical step is to split timings inside the
per-file transform path so the slow bucket is obvious on real data.

The most useful timing buckets are:

- occurrence read;
- static-context load and merge;
- temporal-context load and merge;
- feature matrix build and transform;
- staged parquet write.

Why this is low risk:

- it changes no data semantics;
- it avoids optimizing the wrong phase;
- it gives direct evidence about whether the true bottleneck is CPU, I/O, or
  serialization.

## Changes That Could Improve Speed But Risk Higher Memory Use

These are the fixes to treat cautiously.

### 1. Eliminating the second file pass by holding more prepared data in memory

Avoiding the fit pass plus transform pass split can sound attractive, but the
obvious implementation path is keeping much more of the dataset in memory while
global transform metadata is being derived.

That is exactly the kind of change that can turn a slow run into an unstable or
OOM-prone run.

### 2. Broad caching of full occurrence frames

Caching raw or prepared occurrence DataFrames across many source files may speed
repeated work, but it scales with dataset size much faster than the current
context caching approach.

This should be avoided unless profiling proves it is necessary and the cache is
tightly bounded.

### 3. Raising chunk sizes or write concurrency without measurement

Larger chunks and broader write concurrency can improve throughput, but they can
also raise peak memory materially, especially when multiple file workers are
already active.

This is not the first lever to pull.

## Practical Conclusion

There are clear, non-speculative reasons the processed stage can be slow:

- repeated dataset passes before final publish;
- expensive context merge preparation;
- Python-heavy row and array assembly;
- zstd parquet writes inside the same counted stage.

The safest optimization path is not to redesign the pipeline around larger
in-memory batches. It is to reduce Python object churn, improve reuse in the
context path, and add finer-grained timings so the real dominant sub-phase is
obvious on representative runs.

That should improve throughput without materially increasing peak memory, and in
some cases may reduce it.
