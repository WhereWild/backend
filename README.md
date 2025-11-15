# Local Setup

## 1. Base Python Tooling (uv)

Install **uv** once.

### Windows (PowerShell)
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

### macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Python dependencies and run the app
```bash
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Visit `http://127.0.0.1:8000/health` to confirm the API is up. `uv run python start.py` is a shortcut that runs the same command.

*Tip: Install the **Ruff** VS Code extension for inline linting feedback.*

---

## Leaflet + heatmap.js scratchpad (optional)

Need a free map preview without wiring a full frontend? A static page lives at `frontend-demo/index.html` that fetches `/heatmap/image` and overlays the server-rendered PNG on Leaflet (no Google Maps dependency).

1. Start the FastAPI server (e.g. `uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000`).
2. In another terminal, serve the static page:
   ```bash
   cd frontend-demo
   python -m http.server 4173
   ```
3. Open `http://127.0.0.1:4173` in a browser. Pan/zoom the map and the overlay will re-fetch automatically for the current viewport.

The demo hits `http://127.0.0.1:8000/heatmap/image` directly, so update the URL in the script if the backend runs elsewhere. Since it is a throwaway scratchpad, feel free to delete the `frontend-demo` directory once you've evaluated other mapping stacks.

---

## 2. GDAL / Raster Workflow (Optional — GIS Tasks Only)

### Build the GDAL toolchain via Docker
1. Install and start **Docker Desktop**.
2. From the repo root:
```bash
docker compose build gdal
```
This downloads the GDAL image and bakes in **rasterio**, **geopandas**, **pyproj**, and more. It's a heavy build.

### Verify the container toolchain
```bash
python gdal_test.py
```
You should see the versions of GDAL/rasterio/geopandas/pyproj printed.

---

## Simple Raster Workflows

### Overview benchmarking (default scaffolding)

1. Drop a raster (e.g., `data/dem_100m_cog.tif`) somewhere inside the repo.
2. Update the constants at the top of `start_workflow.py` (`RASTER_RELATIVE_PATH`, the base CONUS bbox, either a fixed shrink percent or a `SHRINK_SCHEDULE` such as `0.1:5,0.03:10,0.01:*`, number of steps, `MIN_OVERVIEW_INDEX`, optionally `DROP_MIN_OVERVIEW_EVERY` to start including finer pyramid levels as the viewport shrinks, and `INCLUDE_BASE_AFTER` if you want to begin sampling the raw band once the step index is high enough).
3. Kick off the benchmark:
   ```bash
   python start_workflow.py
   ```
   This shells into Docker, runs `benchmark_overviews.py`, and emits one section per viewport step (CONUS, then progressively smaller bboxes). Each overview line reports the raster window size, number of COG blocks touched, approximate cell size, estimated IO (blocks × bytes per block), actual payload bytes (window size), and elapsed time. A JSON dump of all measurements is written to `/workspace/benchmark_results.json`, and PNG previews land in `/workspace/benchmark_plots/` so you can quickly visualize what each overview looks like. Use the info to decide where to switch overview levels or tile more aggressively.

### Single-point sample (direct)

For faster iteration, keep the GDAL container running and call the sampler inside it:
```bash
docker compose run --rm gdal bash
# inside the container prompt:
python read_raster.py /workspace/data/dem_100m_cog.tif -120.5 38.2
```

If you already have a container session running you can also call the sampler directly from your host shell:
```bash
docker compose run --rm gdal python read_raster.py /workspace/data/dem_100m_cog.tif -120.5 38.2
```

### Heatmap-style output (resampled grid)

`read_raster.py` also exposes `sample_heatmap_grid`, which converts a bounding box into a list of `{lat, lng, weight}` dicts that can be fed straight into Google Maps' `HeatmapLayer`:

```python
from pathlib import Path
from read_raster import sample_heatmap_grid

points = sample_heatmap_grid(
    Path("data/dem_100m_cog.tif"),
    lon_min=-123,
    lat_min=36,
    lon_max=-121,
    lat_max=38,
    step_degrees=0.05,
)
print(points[:5])
```

If you want to benchmark an ad-hoc bbox without the shrink loop, invoke `benchmark_overviews.py` directly:
```bash
docker compose run --rm gdal python benchmark_overviews.py /workspace/data/dem_100m_cog.tif --lon-min -123 --lon-max -121 --lat-min 36 --lat-max 38 --steps 1 --shrink-percent 0.05 --min-overview-index 0 --output /workspace/custom_benchmark.json --plot-dir /workspace/custom_plots
# Include the base band only after step 5:
docker compose run --rm gdal python benchmark_overviews.py /workspace/data/dem_100m_cog.tif --lon-min -123 --lon-max -121 --lat-min 36 --lat-max 38 --steps 10 --include-base --include-base-after 5
# Dynamically choose the finest overview whose payload stays under 5 MB:
docker compose run --rm gdal python dynamic_res_test.py /workspace/data/dem_100m_cog.tif --payload-cap-mb 5 --steps 12 --shrink-percent 0.1 --include-base-after 8 --plot-dir dynamic_plots
# You can also pass a shrink schedule (percent:steps segments):
docker compose run --rm gdal python dynamic_res_test.py /workspace/data/dem_100m_cog.tif --payload-cap-mb 5 --steps 30 --shrink-schedule "0.1:5,0.03:10,0.01:*" --include-base-after 20 --plot-dir dynamic_plots
# Call the FastAPI endpoint directly:
curl "http://127.0.0.1:8000/heatmap?lon_min=-123&lat_min=36&lon_max=-121&lat_max=38&payload_cap_mb=5"
# Or grab the server-rendered PNG:
curl "http://127.0.0.1:8000/heatmap/image?lon_min=-123&lat_min=36&lon_max=-121&lat_max=38&payload_cap_mb=5" | jq '.image_base64' | head
```
Run `python benchmark_overviews.py --help` for all options.

---

## Why Docker?
GDAL-related libraries require native dependencies that are painful to install consistently across Windows, macOS, Linux, or alongside uv. The Docker image ships everything preconfigured so the entire team runs the exact same stack—no Conda installs, no OS‑specific troubleshooting. Build once, and scripts can call into the container as needed.
