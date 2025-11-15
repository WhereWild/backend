from __future__ import annotations

import base64
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from heatmap_sampler import BoundingBox, HeatmapSampler

app = FastAPI(title="WhereWild API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_SAMPLER_ERROR: str | None = None
try:
    HEATMAP_SAMPLER = HeatmapSampler(Path("data/dem_100m_cog.tif"))
except Exception as exc:  # pragma: no cover - init guard
    HEATMAP_SAMPLER = None
    _SAMPLER_ERROR = str(exc)


@app.get("/health", summary="Simple liveness probe")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/heatmap",
    summary="Generate a dynamic heatmap payload for the given bounding box.",
)
def get_heatmap(
    lon_min: float,
    lat_min: float,
    lon_max: float,
    lat_max: float,
    payload_cap_mb: float = Query(
        5.0,
        description="Maximum payload size (in megabytes) to return.",
        gt=0,
    ),
    include_base_after: int | None = Query(
        default=None,
        ge=0,
        description="Step index at which the raw band is allowed. Leave unset to always allow.",
    ),
) -> dict[str, object]:
    if HEATMAP_SAMPLER is None:
        raise HTTPException(status_code=500, detail=f"Heatmap sampler unavailable: {_SAMPLER_ERROR}")
    bbox = BoundingBox(
        lon_min=lon_min,
        lat_min=lat_min,
        lon_max=lon_max,
        lat_max=lat_max,
    )
    try:
        result = HEATMAP_SAMPLER.sample(
            bbox=bbox,
            payload_cap_mb=payload_cap_mb,
            include_base_after=include_base_after,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@app.get(
    "/heatmap/image",
    summary="Render the sampled raster window as a PNG overlay.",
)
def get_heatmap_image(
    lon_min: float,
    lat_min: float,
    lon_max: float,
    lat_max: float,
    payload_cap_mb: float = Query(
        5.0,
        description="Maximum payload size (in megabytes) to return.",
        gt=0,
    ),
    include_base_after: int | None = Query(
        default=None,
        ge=0,
        description="Step index at which the raw band is allowed. Leave unset to always allow.",
    ),
) -> dict[str, object]:
    if HEATMAP_SAMPLER is None:
        raise HTTPException(status_code=500, detail=f"Heatmap sampler unavailable: {_SAMPLER_ERROR}")
    bbox = BoundingBox(
        lon_min=lon_min,
        lat_min=lat_min,
        lon_max=lon_max,
        lat_max=lat_max,
    )
    try:
        metadata, png_bytes = HEATMAP_SAMPLER.sample_image(
            bbox=bbox,
            payload_cap_mb=payload_cap_mb,
            include_base_after=include_base_after,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    encoded = base64.b64encode(png_bytes).decode("ascii")
    response = dict(metadata)
    response["image_base64"] = encoded
    response["content_type"] = "image/png"
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
