from __future__ import annotations

from typing import Any, Callable, Sequence

import numpy as np

from util import gis_lookup, models


def is_temporal_feature_layer(layer_id: str) -> bool:
    return gis_lookup.is_temporal_layer_id(layer_id)


def load_model_feature_layers(
    taxon_id: int,
    model_id: str | None,
    layers: Sequence[str] | None,
) -> list[str]:
    if layers:
        layer_list = [str(layer).strip() for layer in layers if str(layer).strip()]
    else:
        layer_list = models.model_feature_columns(model_id, taxon_id=taxon_id)

    if not layer_list:
        requested = (model_id or "").strip() or models.DEFAULT_MODEL_ID
        raise ValueError(f"No feature columns available for taxon {taxon_id} and model '{requested}'.")

    layer_meta = gis_lookup.load_layer_metadata()
    unknown_gis = [layer for layer in layer_list if not is_temporal_feature_layer(layer) and layer not in layer_meta]
    if unknown_gis:
        raise ValueError(
            "Model feature columns are not available in the GIS catalog: " + ", ".join(sorted(unknown_gis))
        )
    return layer_list


def render_feature_stack(
    layer_list: list[str],
    spec: Any,
    reproject: bool,
    forecast_hours: int,
    *,
    static_layer_renderer: Callable[[str, Any, bool], np.ndarray],
    layer_cache: dict[str, np.ndarray] | None = None,
) -> np.ndarray:
    """Render a tile-sized feature tensor for the given model feature list."""
    from util import weather_tiles as _wt

    tile_size = spec.tile_size
    stack = np.empty((tile_size, tile_size, len(layer_list)), dtype=np.float32)
    for idx, layer_id in enumerate(layer_list):
        if layer_cache is not None and layer_id in layer_cache:
            stack[:, :, idx] = layer_cache[layer_id]
            continue

        parsed_temporal = gis_lookup.parse_temporal_layer_id(layer_id)
        if parsed_temporal is not None:
            variable_id, _agg, window_hours = parsed_temporal
            try:
                arr = _wt.sample_grid_for_tile(variable_id, window_hours, forecast_hours, spec)
            except Exception as exc:
                arr = np.full((tile_size, tile_size), np.nan, dtype=np.float32)
                print(f"[model-tile] WARNING: temporal layer {layer_id} failed: {exc}")
        else:
            try:
                arr = static_layer_renderer(layer_id, spec, reproject)
            except Exception as exc:
                arr = np.full((tile_size, tile_size), np.nan, dtype=np.float32)
                print(
                    f"[model-tile] WARNING: layer {layer_id} read failed for tile "
                    f"z={spec.z} x={spec.x} y={spec.y} — filling NaN. Error: {exc}"
                )

        stack[:, :, idx] = arr
        if layer_cache is not None:
            layer_cache[layer_id] = arr
        if idx == 0 or idx == len(layer_list) - 1 or (idx + 1) % 10 == 0:
            print(f"[model-tile] rendered layers {idx + 1}/{len(layer_list)} current_layer={layer_id}")

    return stack
