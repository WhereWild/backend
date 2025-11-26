#!/usr/bin/env python3
from __future__ import annotations

import json
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "processed"
SPECIES_CATALOG_PATH = PROCESSED_DIR / "species" / "species_catalog.json"
MODELS_DIR = PROCESSED_DIR / "models" / "gbt"
GIS_CATALOG_PATH = REPO_ROOT / "gis_catalog.json"
OUTPUT_DIR = PROCESSED_DIR / "predictions"

# Tunable knobs
TARGET_SPECIES_IDS = [148405]
TEMPLATE_VARIABLE_ID = "annual_precip"
PLOT_DOWNSAMPLE = 4  # use every Nth pixel when plotting to keep memory reasonable


@dataclass(frozen=True)
class DirectionBin:
    id: str
    start_deg: float
    end_deg: float


@dataclass
class RasterVariable:
    id: str
    dataset: rasterio.io.DatasetReader
    value_type: str
    direction_bins: list[DirectionBin] | None = None

    @property
    def is_categorical(self) -> bool:
        return self.value_type in {"categorical", "circular"}


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_model(model_path: Path) -> dict:
    if not model_path.exists():
        raise FileNotFoundError(f"Model file missing at {model_path}")
    with model_path.open() as fp:
        return json.load(fp)


def load_gis_catalog() -> dict[str, dict]:
    with GIS_CATALOG_PATH.open() as fp:
        entries = json.load(fp)
    return {entry["id"]: entry for entry in entries}


def load_species_catalog() -> dict[int, dict]:
    with SPECIES_CATALOG_PATH.open() as fp:
        entries = json.load(fp)
    return {int(entry["taxon_id"]): entry for entry in entries}


def get_slug(entry: dict, fallback_id: int) -> str:
    slug = entry.get("slug")
    if slug:
        return slug
    scientific = entry.get("scientific_name")
    if scientific:
        return scientific.lower().replace(" ", "_")
    return f"species_{fallback_id}"


def load_direction_bins(definition_path: str | None) -> list[DirectionBin]:
    if not definition_path:
        return []
    path = REPO_ROOT / definition_path
    if not path.exists():
        raise RuntimeError(f"Direction bin definition missing at {path}")
    with path.open() as fp:
        entries = json.load(fp)
    bins: list[DirectionBin] = []
    for entry in entries:
        bins.append(
            DirectionBin(
                id=entry.get("id", f"bin_{len(bins)}"),
                start_deg=float(entry["start_deg"]),
                end_deg=float(entry["end_deg"]),
            )
        )
    return bins


def _direction_mask(values: np.ndarray, start_deg: float, end_deg: float) -> np.ndarray:
    start = start_deg % 360.0
    end = end_deg % 360.0
    if start <= end:
        return (values >= start) & (values < end)
    return (values >= start) | (values < end)


def bin_circular_array(values: np.ndarray, bins: list[DirectionBin]) -> np.ndarray:
    if not bins:
        raise RuntimeError("Circular variable defined without direction bins.")
    flat = values.reshape(-1)
    result = np.full(flat.shape, np.nan, dtype="float64")
    valid_idx = np.where(np.isfinite(flat))[0]
    if valid_idx.size == 0:
        return result.reshape(values.shape)
    normalized = np.mod(flat[valid_idx], 360.0)
    for idx, bin_def in enumerate(bins):
        mask = _direction_mask(normalized, bin_def.start_deg, bin_def.end_deg)
        if np.any(mask):
            result[valid_idx[mask]] = float(idx)
    return result.reshape(values.shape)


def transform_raster_values(
    data: np.ndarray,
    valid_mask: np.ndarray,
    raster: RasterVariable,
) -> tuple[np.ndarray, np.ndarray]:
    if raster.value_type == "circular":
        transformed = bin_circular_array(data, raster.direction_bins or [])
        new_valid = valid_mask & np.isfinite(transformed)
        return transformed, new_valid
    return data, valid_mask


def resolve_model_path(species_id: int, slug: str) -> Path:
    preferred = MODELS_DIR / f"{slug}_{species_id}.json"
    if preferred.exists():
        return preferred
    legacy = MODELS_DIR / f"{species_id}.json"
    if legacy.exists():
        return legacy
    matches = list(MODELS_DIR.glob(f"*_{species_id}.json"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No model artifact found for species {species_id}")


def iter_windows(dataset: rasterio.io.DatasetReader, max_pixels: int = 1024 * 1024):
    for _, window in dataset.block_windows(1):
        if window.width * window.height <= max_pixels:
            yield window
        else:
            step_w = max(1, int(np.sqrt(max_pixels * window.width / window.height)))
            step_h = max(1, int(np.sqrt(max_pixels * window.height / window.width)))
            for row in range(window.row_off, window.row_off + window.height, step_h):
                for col in range(window.col_off, window.col_off + window.width, step_w):
                    sub_window = Window(
                        col_off=col,
                        row_off=row,
                        width=min(step_w, window.col_off + window.width - col),
                        height=min(step_h, window.row_off + window.height - row),
                    )
                    yield sub_window


def predict_surface(model_payload: dict, output_path: Path) -> Path:
    ensure_directory(OUTPUT_DIR)
    variables = model_payload["variables"]
    model_info = model_payload.get("model")
    if not model_info or model_info.get("type") != "lightgbm":
        raise RuntimeError(
            "Model artifact missing LightGBM metadata. Regenerate using train_gbt.py."
        )
    booster = lgb.Booster(model_str=model_info["booster"])
    best_iteration = model_info.get("best_iteration")
    mean = np.asarray(model_payload["scaler"]["mean"], dtype="float64")
    scale = np.asarray(model_payload["scaler"]["scale"], dtype="float64")
    categorical_variables = set(model_info.get("categorical_variables") or [])
    catalog = load_gis_catalog()
    missing = [var for var in variables if var not in catalog]
    if missing:
        raise RuntimeError(f"Missing rasters for variables: {', '.join(missing)}")
    if TEMPLATE_VARIABLE_ID not in catalog:
        raise RuntimeError(f"Template variable '{TEMPLATE_VARIABLE_ID}' missing from GIS catalog.")
    template_path = REPO_ROOT / catalog[TEMPLATE_VARIABLE_ID]["path"]
    if not template_path.exists():
        raise RuntimeError(f"Template raster missing at {template_path}")
    var_index = {var: idx for idx, var in enumerate(variables)}
    with ExitStack() as stack:
        template = stack.enter_context(rasterio.open(template_path))
        rasters: list[RasterVariable] = []
        for var in variables:
            entry = catalog[var]
            if var == TEMPLATE_VARIABLE_ID:
                dataset = template
            else:
                path = REPO_ROOT / entry["path"]
                if not path.exists():
                    raise RuntimeError(f"Raster for variable '{var}' missing at {path}")
                dataset = stack.enter_context(rasterio.open(path))
            value_type = (entry.get("value_type") or "continuous").lower()
            direction_bins = None
            if value_type == "circular" and var in categorical_variables:
                direction_bins = load_direction_bins(entry.get("direction_bins_file"))
                if not direction_bins:
                    raise RuntimeError(
                        f"Circular variable '{var}' missing direction bin definitions."
                    )
            rasters.append(
                RasterVariable(
                    id=var,
                    dataset=dataset,
                    value_type=value_type,
                    direction_bins=direction_bins,
                )
            )
        categorical_mask = np.array([raster.id in categorical_variables for raster in rasters], dtype=bool)
        profile = template.profile
        profile.update(
            count=1,
            dtype="float32",
            nodata=np.nan,
            compress="lzw",
        )
        with rasterio.open(output_path, "w", **profile) as dst:
            for window in iter_windows(template):
                stacked: list[np.ndarray] = []
                template_mask = None
                window_bounds = rasterio.windows.bounds(window, template.transform)
                for raster_spec in rasters:
                    dataset = raster_spec.dataset
                    is_template = dataset is template
                    if is_template:
                        data = dataset.read(1, window=window).astype("float64")
                        valid = np.isfinite(data)
                        if dataset.nodata is not None:
                            valid &= data != dataset.nodata
                        if template_mask is None:
                            template_mask = valid.copy()
                    else:
                        dataset_window = from_bounds(
                            *window_bounds,
                            transform=dataset.transform,
                        )
                        resampling = Resampling.nearest if raster_spec.id in categorical_variables else Resampling.bilinear
                        data = dataset.read(
                            1,
                            window=dataset_window,
                            out_shape=(window.height, window.width),
                            resampling=resampling,
                            boundless=True,
                            fill_value=dataset.nodata if dataset.nodata is not None else np.nan,
                        ).astype("float64")
                        valid = np.isfinite(data)
                        if dataset.nodata is not None:
                            valid &= data != dataset.nodata
                    if raster_spec.id in categorical_variables and raster_spec.value_type == "circular":
                        data, valid = transform_raster_values(data, valid, raster_spec)
                    fill_value = mean[var_index[raster_spec.id]]
                    data = np.where(valid, data, fill_value)
                    stacked.append(data)
                if not stacked or template_mask is None:
                    continue
                features = np.stack(stacked, axis=-1)
                normalized = features.copy()
                continuous_mask = ~categorical_mask
                if np.any(continuous_mask):
                    normalized[..., continuous_mask] = (
                        normalized[..., continuous_mask] - mean[continuous_mask]
                    ) / scale[continuous_mask]
                flat = normalized.reshape(-1, normalized.shape[-1])
                preds = booster.predict(flat, num_iteration=best_iteration)
                probs = preds.reshape(normalized.shape[:2])
                probs[~template_mask] = np.nan
                dst.write(probs.astype("float32"), 1, window=window)
    return output_path


def plot_prediction(prob_path: Path, plot_path: Path, label: str) -> Path:
    with rasterio.open(prob_path) as src:
        data = src.read(
            1,
            out_shape=(
                src.height // PLOT_DOWNSAMPLE,
                src.width // PLOT_DOWNSAMPLE,
            ),
            resampling=rasterio.enums.Resampling.bilinear,
        )
        data[data == src.nodata] = np.nan
        bounds = src.bounds
    fig, ax = plt.subplots(figsize=(10, 6))
    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
    cmap = plt.cm.viridis
    img = ax.imshow(data, origin="upper", extent=extent, cmap=cmap, vmin=0, vmax=1)
    ax.set_title(f"Predicted presence probability for {label}")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    cbar = fig.colorbar(img, ax=ax, fraction=0.036, pad=0.04)
    cbar.set_label("Probability")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=200)
    plt.close(fig)
    return plot_path


def main() -> None:
    species_catalog = load_species_catalog()
    if not TARGET_SPECIES_IDS:
        raise SystemExit("No species IDs specified in TARGET_SPECIES_IDS.")
    for species_id in TARGET_SPECIES_IDS:
        entry = species_catalog.get(species_id)
        if not entry:
            print(f"[SKIP] Species {species_id} not found in catalog.")
            continue
        slug = get_slug(entry, species_id)
        species_label = entry.get("scientific_name", slug)
        try:
            model_path = resolve_model_path(species_id, slug)
        except FileNotFoundError as exc:
            print(f"[SKIP] {exc}")
            continue
        model_payload = load_model(model_path)
        prediction_tiff = OUTPUT_DIR / f"{slug}_{species_id}_probability.tif"
        plot_path_file = OUTPUT_DIR / f"{slug}_{species_id}_probability.png"
        prob_path = predict_surface(model_payload, prediction_tiff)
        plot_path = plot_prediction(prob_path, plot_path_file, species_label)
        rel_prob = prob_path.relative_to(REPO_ROOT)
        rel_plot = plot_path.relative_to(REPO_ROOT)
        print(f"[DONE] {species_label} ({species_id}) -> raster: {rel_prob}, plot: {rel_plot}")


if __name__ == "__main__":
    main()
