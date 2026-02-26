# API

This section documents the backend HTTP API. The public interface is defined in
`main.py`, which exposes FastAPI routes that wrap the core `util/` libraries.

This page is a curated overview so the API documentation lives alongside the library and script docs. The default FastAPI page may still contain useful information not present here.

## Contracts

- `inference_heatmap.md`: `/species/{taxon_id}/inference-heatmap` contract for precomputed global surface serving with legacy fallback.
