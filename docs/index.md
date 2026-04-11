# WhereWild Docs

Welcome to the WhereWild backend docs. These pages cover the core libraries,
data processing scripts, machine-learning pipeline, and the prediction API.

## What's Here

- Libraries: reusable helpers in `util/` (GIS lookup, taxonomy traversal,
  ranking utilities, inference engine).
- Scripts: occasional data workflows in `scripts/` (build, enrich, and
  indexing tasks).
- ML Pipeline: preprocessing, training (encoder + PU heads), export, and
  server-side inference.
- Prediction API: species-suitability predictions, batch scoring, and
  heatmap generation over the FastAPI backend.

## Quick Links

- [ML Scripts Guide](ml_scripts.md) -- end-to-end preprocessing, training, export, and serving
- [Training Observation Schema](training_observation_schema.md)
- [Darwin Model Card](darwin_model_card.md)
- [Inference Optimization Opportunities](inference_optimization_opportunities.md)

For more information, see the README on the left.
