# WhereWild Species Occurrence Modeling Plan

## Plan

### 0. Design Goals

* No monolithic “one giant model per species”
* Modular, extensible to new species
* Runs inference fully offline on phones
* Trained on a single RTX 5090 (32 GB)
* Handles ~900 GB / ~3M-file dataset
* Correctly models presence-only data (no true negatives)

### 1. High-Level Architecture

#### 1.1 Model Structure

##### Shared trunk + factorized species head

```txt
Input features x
      ↓
Tabular Encoder (MLP) → z ∈ R^d
      ↓
Species vectors w_s ∈ R^d
      ↓
logit_s = z · w_s + b_s
```

* One shared trunk (compact MLP)
* One vector per species
* Dot-product scoring
* Fully modular
* Efficient on-device

### 1.2 Why This Works

* Add species = add a vector
* Freeze trunk to cheaply train rare species
* Trunk runs once per location
* Species scoring = matrix multiply (fast even on mobile)

### 2. Data Strategy

#### 2.1 Training Data Shape

Build a consolidated parquet training table:

Each row:

* lat, lon
* time features
* climate covariates
* landcover / soil / Köppen class
* observation effort proxy features
* species_id (positive)

Do NOT train by opening millions of TIFF files during epochs.
Pre-extract raster values into parquet.

#### 2.2 Background / Pseudo-Absence Strategy

We use **presence vs background** (MaxEnt-style).

For each presence point:

* Sample K background points from:

    * Accessible area
    * Effort-weighted surface (preferred)
    * Same temporal distribution if possible

Train logistic objective:

```python
Presence = 1
Background = 0
```

Interpretation:

* Model learns relative intensity / suitability
* Outputs must be calibrated

### 3. Model Details

#### 3.1 Trunk

Small MLP:

* Input dim: ~50–150
* Layers: 3–4
* Width: 128–256
* Activation: SiLU
* LayerNorm
* Dropout 0.1

Embedding dimension:

* d = 128 (good balance)

#### 3.2 Species Head

* Matrix W ∈ R^(num_species × d)
* Bias vector b ∈ R^(num_species)

Score:

```python
logits = z @ W^T + b
```

Training:

* Sampled negatives (species)
* Or full batch if species count manageable

#### 3.3 Loss

Option A (recommended first):

Binary logistic:

```python
L = BCE(presence_vs_background)
```

Option B (later):

nnPU objective if you want more formal PU modeling.

### 4. Training Strategy (5090-friendly)

#### 4.1 Data Loading

* Pre-shard parquet into large row groups
* Avoid tiny-file access during training
* Use PyTorch DataLoader with pinned memory
* Mixed precision (bf16/fp16)

#### 4.2 Scaling Species

If species count large:

* Sample 20–100 negative species per positive
* Or hierarchical softmax by taxonomy

#### 4.3 Curriculum

1. Train trunk + head on well-sampled species
2. Freeze trunk
3. Train head vectors for rare species
4. Optional global fine-tune

### 5. Calibration

Raw output ≠ absolute probability.

We will:

* Hold out spatial blocks
* Fit per-species calibration curve
* Normalize within region
* Present as:

    * “Likelihood relative to nearby species”
    * or “Habitat suitability index”

### 6. Mobile Deployment Plan

#### 6.1 Export

* TorchScript or ONNX
* Quantize trunk (int8 or dynamic)
* Quantize species matrix

#### 6.2 Model Packaging

App ships:

* Trunk
* Small starter species pack

User downloads:

* Regional species packs
* Taxon packs

Each pack contains:

* Subset of species vectors
* Calibration metadata

### 7. Evaluation

#### 7.1 Metrics

* AUC against background
* Spatial cross-validation
* Precision@K (top species)
* Calibration curves

#### 7.2 Real-World Evaluation

* Known hotspots
* Rare species test cases
* Out-of-region validation

### 8. Roadmap

| Phase   | Goal                        |
| ------- | --------------------------- |
| Phase 1 | Build training table        |
| Phase 2 | Trunk + background training |
| Phase 3 | Species scaling             |
| Phase 4 | Calibration                 |
| Phase 5 | Mobile quantized export     |

## Rapid Prototype Plan (2–3 Weeks)

This is the “get something real working fast” version.

### One-Hour Feasible Prototype Scope (4 Species)

Target species:

* Escobaria vivipara
* Haliaeetus leucocephalus
* Spea intermontana
* Hypaurotis crysalus

#### Scope Decision

For a strict one-hour training window, use a **single small tabular baseline** (presence vs background) over just these four species, with aggressive row caps and no raster reads during training.

Notes from current local data:

* Escobaria appears under `Pelecyphora_vivipara_11498251` (with Escobaria vivipara varieties)
* All four species have a shared 100-column `occurrence.parquet` schema
* Approximate positive rows available:
    * Escobaria vivipara (mapped as above): 9,193
    * Haliaeetus leucocephalus: 135,199
    * Spea intermontana: 1,239
    * Hypaurotis crysalus: 342

#### Hard Constraints (to stay ≤ 1 hour)

1. **Model type**: one-vs-background tabular classifier (single shared model with `species_id` as categorical feature, or four separate binary models)
2. **Feature scope**: numeric columns only from `occurrence.parquet`; drop IDs/text fields
3. **Row caps per species (positives)**:
    * Escobaria: up to 9k (use all)
    * Haliaeetus: cap at 20k (subsample)
    * Spea: use all (~1.2k)
    * Hypaurotis: use all (~342)
4. **Background ratio**: 5:1 background-to-positive (random within union bbox of positives)
5. **Total training rows target**: ~150k to 220k
6. **Validation split**: simple spatial hash split or 80/20 random split (spatial preferred if already implemented)
7. **Training budget**: max 10 epochs for MLP or equivalent early-stopped tabular baseline

#### Expected 1-Hour Time Budget

* Data read + sampling: 10–15 min
* Feature filtering/encoding: 10 min
* Training (CPU/GPU): 15–20 min
* Evaluation + save artifacts: 10–15 min

Total: **45–60 minutes**

#### Deliverables for This Prototype

* One trainable script/notebook producing:
    * model artifact
    * feature list used
    * per-species AUC vs background (or PR-AUC for rare taxa)
* One inference smoke test:
    * input: one `(lat, lon, time)` row with covariates
    * output: scores for the four species

#### Explicit Non-Goals (deferred)

* Full species catalog
* Mobile quantization/export optimization
* PU-specific objectives (nnPU, etc.)
* Calibration curves beyond a basic sanity check
* TIFF-on-the-fly feature extraction during epochs

#### Success Criteria

Prototype is successful if, within one hour wall-clock:

* training completes,
* all four species return finite scores,
* at least 3/4 species beat frequency-prior baseline on holdout.

### Week 1 – Minimal End-to-End Pipeline

#### Step 1: Reduce Scope

* Pick 200–500 well-sampled species
* Use only tabular covariates
* Ignore TIFF at runtime

#### Step 2: Build Training Table

For each presence:

* Extract covariates
* Sample 5–10 background points
* Store in single parquet

Target size:

* 5–20M rows max

#### Step 3: Train Simple Model

Architecture:

* 3-layer MLP (128 hidden)
* d = 128
* Dot-product head

Train:

* Presence vs background
* Mixed precision
* 3–5 epochs

Goal:

* Get non-trivial AUC
* Confirm model learns habitat patterns

### Week 2 – Mobile Simulation

#### Step 4: Export Model

* TorchScript export
* Quantize trunk
* Save species matrix

#### Step 5: Build Inference Mock

In Python:

```python
z = trunk(x)
scores = z @ W.T
top_k = torch.topk(scores, k=10)
```

Measure:

* Single inference latency
* Memory footprint

Target:

* <50ms per location on mid-tier phone equivalent

### Week 3 – Reality Check

#### Step 6: Spatial Holdout

* Split by geographic blocks
* Measure AUC and Precision@K

#### Step 7: Bias Stress Test

* Evaluate in under-sampled regions
* Compare to naive baseline:
    * Species frequency prior
    * Climate-only logistic regression

## What This Prototype Proves

* Architecture scales
* Mobile inference feasible
* Presence-only training workable
* Species modularity works
* Training fits on 5090

## After Prototype

Then you can:

* Add effort-aware background sampling
* Add raster-derived features
* Add hierarchical taxonomic modeling
* Add PU objective
* Add calibration layer

This plan keeps you:

* Modular
* Mobile-first
* Statistically defensible
* Feasible on your hardware
* Expandable to full 900GB scale

And most importantly — it avoids the “giant brittle monolith” trap.
