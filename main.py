from __future__ import annotations

from fastapi import FastAPI, HTTPException

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
