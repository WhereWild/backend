from __future__ import annotations

import fsspec


BASE_PREFIX = "s3://openmeteo/data"
MODEL_WHITELIST = {
    "copernicus_era5",
    "copernicus_era5_land",
    "copernicus_era5_ensemble",
    "cerra",
}
WHITELIST = {
    "temperature_2m",
    "apparent_temperature",
    "vapour_pressure_deficit",
    "dew_point_2m",
    "precipitation",
    "rain",
    "snowfall",
    "snowfall_water_equivalent",
    "snow_depth",
    "weather_code",
    "cloud_cover",
    "convective_precipitation",
    "cape",
    "lifted_index",
    "visibility",
    "categorical_freezing_rain",
    "wind_gusts_10m",
    "soil_temperature_0_to_7cm",
    "soil_temperature_7_to_28cm",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "is_day",
    "sunshine_duration",
    "et0_fao_evapotranspiration",
}


def _ls_dirs(fs, path: str) -> list[str]:
    entries = fs.ls(path)
    dirs = []
    for entry in entries:
        name = entry.get("name") if isinstance(entry, dict) else entry
        if not isinstance(name, str):
            continue
        if name.endswith("/"):
            name = name[:-1]
        if name:
            dirs.append(name)
    return sorted(set(dirs))


def main() -> None:
    fs = fsspec.filesystem("s3", anon=True)
    models = _ls_dirs(fs, BASE_PREFIX)
    model_vars: dict[str, list[str]] = {}
    var_models: dict[str, list[str]] = {}

    for model_path in models:
        model = model_path.split("/")[-1]
        if model not in MODEL_WHITELIST:
            continue
        vars_paths = _ls_dirs(fs, model_path)
        variables = [p.split("/")[-1] for p in vars_paths]
        variables = [v for v in variables if v != "static"]
        variables = [v for v in variables if v in WHITELIST]
        model_vars[model] = sorted(variables)
        for var in variables:
            var_models.setdefault(var, []).append(model)

    print("models:")
    for model in sorted(model_vars.keys()):
        print(f"  {model}")

    print("\nvariables_by_model:")
    for model in sorted(model_vars.keys()):
        print(f"  {model}: {', '.join(model_vars[model])}")

    print("\nmodels_by_variable:")
    for var in sorted(var_models.keys()):
        models_list = ", ".join(sorted(var_models[var]))
        print(f"  {var}: {models_list}")

    missing = sorted(WHITELIST - set(var_models.keys()))
    if missing:
        print("\nmissing_whitelist_vars:")
        for var in missing:
            print(f"  {var}")


if __name__ == "__main__":
    main()
