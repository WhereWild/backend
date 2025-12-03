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
TEMPLATE_VARIABLE_ID = "annual_precip"
PLOT_DOWNSAMPLE = 4  # use every Nth pixel when plotting to keep memory reasonable
RECALCULATE_TIFF = False  # toggle to force raster recomputation when needed
PLOT_MAX_NORTHING = 3_200_000  # crop anything north of roughly Maine/Canada boundary
PLOT_MIN_SOUTHING = None  # set to a value (meters) to crop south as well
IGNORE_VARIABLE_IDS = {"landcover"}  # provide mean value everywhere to neutralize bias


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


def prediction_output_paths(species_id: int, slug: str) -> tuple[Path, Path]:
    base = f"{slug}_{species_id}_probability"
    probability_raster = OUTPUT_DIR / f"{base}.tif"
    plot_path = OUTPUT_DIR / f"{base}.png"
    return probability_raster, plot_path


def prediction_outputs_exist(probability_path: Path, plot_path: Path) -> bool:
    return probability_path.exists() and plot_path.exists()


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
                    ignore_variable = raster_spec.id in IGNORE_VARIABLE_IDS
                    if ignore_variable:
                        fill_value = mean[var_index[raster_spec.id]]
                        data = np.full((window.height, window.width), fill_value, dtype="float64")
                        valid = np.ones_like(data, dtype=bool)
                    else:
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
                            resampling = (
                                Resampling.nearest
                                if raster_spec.id in categorical_variables
                                else Resampling.bilinear
                            )
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
                    if not ignore_variable:
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
    _ = label  # label kept for future annotations if needed
    with rasterio.open(prob_path) as src:
        data = src.read(
            1,
            out_shape=(
                src.height // PLOT_DOWNSAMPLE,
                src.width // PLOT_DOWNSAMPLE,
            ),
            resampling=rasterio.enums.Resampling.bilinear,
        )
        data = data.astype("float32")
        data[data == src.nodata] = np.nan
        bounds = src.bounds
        pixel_height = (bounds.top - bounds.bottom) / data.shape[0]
    if PLOT_MAX_NORTHING is not None or PLOT_MIN_SOUTHING is not None:
        # Remove anything outside the configured vertical extent.
        row_centers = np.linspace(
            bounds.top - pixel_height / 2,
            bounds.bottom + pixel_height / 2,
            data.shape[0],
        )
        mask = np.ones_like(row_centers, dtype=bool)
        if PLOT_MAX_NORTHING is not None:
            mask &= row_centers <= PLOT_MAX_NORTHING
        if PLOT_MIN_SOUTHING is not None:
            mask &= row_centers >= PLOT_MIN_SOUTHING
        data[~mask, :] = np.nan
    valid_mask = np.isfinite(data)
    row_mask = np.any(valid_mask, axis=1)
    if not np.any(row_mask):
        return plot_path
    top_idx = row_mask.argmax()
    bottom_idx = len(row_mask) - row_mask[::-1].argmax() - 1
    data = data[top_idx : bottom_idx + 1, :]
    valid_mask = valid_mask[top_idx : bottom_idx + 1, :]
    alpha = np.where(valid_mask, 1.0, 0.0)
    display = np.where(valid_mask, data, 0.0)
    top_bound = bounds.top - top_idx * pixel_height
    bottom_bound = bounds.top - (bottom_idx + 1) * pixel_height
    extent = [bounds.left, bounds.right, bottom_bound, top_bound]
    width = extent[1] - extent[0]
    height = extent[3] - extent[2]
    aspect = width / height if height else 1
    fig_width = 12
    fig_height = max(4, fig_width / max(aspect, 1e-6))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_aspect("equal")
    cmap = plt.cm.viridis
    ax.imshow(
        display,
        origin="upper",
        extent=extent,
        cmap=cmap,
        vmin=0,
        vmax=1,
        alpha=alpha,
    )
    ax.set_axis_off()
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(plot_path, dpi=200, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return plot_path


def main() -> None:
    species_catalog = load_species_catalog()
    if not species_catalog:
        raise SystemExit("Species catalog is empty; nothing to predict.")
    for species_id in sorted(species_catalog.keys()):
        entry = species_catalog[species_id]
        slug = get_slug(entry, species_id)
        species_label = entry.get("scientific_name", slug)
        prediction_tiff, plot_path_file = prediction_output_paths(species_id, slug)
        raster_exists = prediction_tiff.exists()
        plot_exists = plot_path_file.exists()
        if raster_exists and plot_exists:
            print(
                f"[SKIP] Prediction artifacts already exist for {species_label} "
                f"({species_id})."
            )
            continue
        try:
            model_path = resolve_model_path(species_id, slug)
        except FileNotFoundError as exc:
            print(f"[SKIP] {exc}")
            continue
        model_payload = load_model(model_path)
        if not raster_exists or RECALCULATE_TIFF:
            prob_path = predict_surface(model_payload, prediction_tiff)
        else:
            prob_path = prediction_tiff
        plot_prediction(prob_path, plot_path_file, species_label)
        rel_prob = prob_path.relative_to(REPO_ROOT)
        rel_plot = plot_path_file.relative_to(REPO_ROOT)
        print(
            f"[DONE] {species_label} ({species_id}) -> raster: {rel_prob}, plot: {rel_plot}"
        )


if __name__ == "__main__":
    main()
