from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from wherewild.model_repository import (
    FeatureImportancesUnavailableError,
    ModelArtifactNotFoundError,
    SpeciesMetadataNotFoundError,
    get_feature_importances,
)
from wherewild.prediction_repository import (
    PredictionMapNotFoundError,
    SpeciesNotFoundError,
    get_prediction_map,
)
from wherewild.stats_repository import (
    SpeciesStatsNotFoundError,
    VariableNotFoundError,
    get_species_stats,
    get_variable_leaderboard,
)

app = FastAPI(title="WhereWild API", version="0.1.0")


@app.get("/health", summary="Simple liveness probe")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/species/{species_id}/environment/{variable}",
    summary="Retrieve precomputed environmental stats for a species/variable pair",
)
def species_environment_stats(species_id: int, variable: str) -> dict:
    variable_id = variable.strip()
    try:
        return get_species_stats(species_id=species_id, variable_id=variable_id)
    except VariableNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{variable_id}' is not available.",
        ) from None
    except SpeciesStatsNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No stats found for species {species_id} and variable '{variable_id}'.",
        ) from None


@app.get(
    "/variables/{variable}/leaderboard",
    summary="Retrieve the leaderboard for a GIS variable",
)
def variable_leaderboard(variable: str) -> dict:
    variable_id = variable.strip()
    try:
        return get_variable_leaderboard(variable_id=variable_id)
    except VariableNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{variable_id}' is not available.",
        ) from None
    except SpeciesStatsNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No leaderboard found for variable '{variable_id}'.",
        ) from None


@app.get(
    "/species/{species_id}/prediction-map",
    summary="Retrieve a pre-rendered prediction map for a species",
)
def species_prediction_map(species_id: int, format: str = "png") -> StreamingResponse:
    fmt = format.lower()
    if fmt not in {"png", "tif"}:
        raise HTTPException(
            status_code=400, detail="Format must be either 'png' or 'tif'."
        )
    try:
        map_path = get_prediction_map(species_id=species_id, fmt=fmt)
    except SpeciesNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Species '{species_id}' is not available.",
        ) from None
    except PredictionMapNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No prediction map found for species '{species_id}' in format '{fmt}'.",
        ) from None
    media_type = "image/png" if fmt == "png" else "image/tiff"
    file_handle = map_path.open("rb")
    return StreamingResponse(
        file_handle,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename=\"{map_path.name}\"'},
    )


@app.get(
    "/species/{species_id}/feature-importances",
    summary="Retrieve the ranked feature importances for a species model",
)
def species_feature_importances(
    species_id: int, limit: int | None = Query(default=None, ge=1, le=50)
) -> dict:
    try:
        return get_feature_importances(species_id=species_id, limit=limit)
    except SpeciesMetadataNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Species '{species_id}' is not available.",
        ) from None
    except ModelArtifactNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No trained model found for species '{species_id}'.",
        ) from None
    except FeatureImportancesUnavailableError:
        raise HTTPException(
            status_code=404,
            detail=f"Feature importances are unavailable for species '{species_id}'.",
        ) from None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
