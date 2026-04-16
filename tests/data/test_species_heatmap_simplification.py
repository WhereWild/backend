from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from util import heatmap_tiles
from util import species_heatmap_feature_sources as sources
from util import species_heatmap_scorers as scorers
from util import tiles


@dataclass(frozen=True)
class _StubTileSpec:
    z: int
    x: int
    y: int
    tile_size: int


def _png_bytes(size: int, quadrant_colors: tuple[tuple[int, int, int, int], ...]) -> bytes:
    image = Image.new("RGBA", (size, size))
    half = size // 2
    coords = [
        (0, 0, half, half),
        (half, 0, size, half),
        (0, half, half, size),
        (half, half, size, size),
    ]
    for box, color in zip(coords, quadrant_colors, strict=True):
        block = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), color)
        image.paste(block, box)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_render_feature_stack_uses_static_temporal_and_cache(monkeypatch):
    calls: list[tuple[str, int]] = []

    def _fake_sample_grid(variable_id, window_hours, forecast_hours, spec):
        calls.append((variable_id, forecast_hours))
        return np.full((spec.tile_size, spec.tile_size), window_hours + forecast_hours, dtype=np.float32)

    monkeypatch.setattr("util.weather_tiles.sample_grid_for_tile", _fake_sample_grid)

    static_calls: list[str] = []

    def _static_layer_renderer(layer_id, spec, reproject):
        static_calls.append(f"{layer_id}:{reproject}")
        return np.full((spec.tile_size, spec.tile_size), 5.0, dtype=np.float32)

    spec = _StubTileSpec(z=3, x=4, y=5, tile_size=2)
    cache: dict[str, np.ndarray] = {}
    stack = sources.render_feature_stack(
        ["bio_1", "temperature_2m_avg_24h", "bio_1"],
        spec,
        True,
        8,
        static_layer_renderer=_static_layer_renderer,
        layer_cache=cache,
    )

    assert stack.shape == (2, 2, 3)
    assert np.all(stack[:, :, 0] == 5.0)
    assert np.all(stack[:, :, 1] == 32.0)
    assert np.all(stack[:, :, 2] == 5.0)
    assert static_calls == ["bio_1:True"]
    assert calls == [("temperature_2m", 8)]
    assert sorted(cache) == ["bio_1", "temperature_2m_avg_24h"]


def test_legacy_scorer_crops_from_fixed_parent_zoom(monkeypatch):
    rendered: list[tuple[int, int, int, int]] = []

    def _fake_render_model_tile_bytes(*, taxon_id, z, x, y, model_id, tile_size, **_kwargs):
        rendered.append((z, x, y, tile_size))
        return _png_bytes(
            tile_size,
            (
                (255, 0, 0, 255),
                (0, 255, 0, 255),
                (0, 0, 255, 255),
                (255, 255, 0, 255),
            ),
        )

    monkeypatch.setattr("util.tiles.render_model_tile_bytes", _fake_render_model_tile_bytes)

    scorer = scorers.LegacySpeciesHeatmapScorer(
        model_id="model",
        reproject=True,
        forecast_hours=0,
        apply_phenology=True,
        phenology_only=False,
        max_tile_size=8,
    )
    payload = scorer.render_runtime_tile_bytes(123, 3, 5, 7, tile_size=2, max_native_zoom=2)
    image = Image.open(BytesIO(payload))

    assert rendered == [(2, 2, 3, 4)]
    assert image.size == (2, 2)
    assert image.getpixel((0, 0)) == (255, 255, 0, 255)


def test_darwin_scorer_uses_closest_reusable_parent(monkeypatch):
    rendered: list[tuple[int, int, int, int, str]] = []

    def _fake_render_heatmap_tile_bytes(
        taxon_id,
        z,
        x,
        y,
        *,
        tile_size,
        feature_mode,
        cancel_check=None,
    ):
        rendered.append((z, x, y, tile_size, feature_mode))
        return _png_bytes(
            tile_size,
            (
                (255, 0, 0, 255),
                (0, 255, 0, 255),
                (0, 0, 255, 255),
                (255, 255, 0, 255),
            ),
        )

    monkeypatch.setattr("util.heatmap_tiles.render_heatmap_tile_bytes", _fake_render_heatmap_tile_bytes)

    scorer = scorers.DarwinSpeciesHeatmapScorer(feature_mode="prefer_cell_table", max_tile_size=8)
    payload = scorer.render_runtime_tile_bytes(321, 6, 40, 50, tile_size=2, max_native_zoom=2)
    image = Image.open(BytesIO(payload))

    assert rendered == [(4, 10, 12, 8, "prefer_cell_table")]
    assert image.size == (2, 2)


def test_render_heatmap_tile_bytes_uses_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    call_count = 0

    def _fake_score_species_coords(
        species_key: int,
        coords: list[tuple[float, float]],
        *,
        resolution_hint: float,
        feature_mode: str,
        score_batch_size: int,
        include_source: bool,
        cancel_check=None,
    ) -> tuple[list[float | None], None]:
        nonlocal call_count
        call_count += 1
        return [0.5 for _ in coords], None

    monkeypatch.setattr(heatmap_tiles, "_HEATMAP_TILE_CACHE_DIR", tmp_path)
    monkeypatch.setattr(heatmap_tiles.inference, "bundle_cache_token", lambda: "bundle-a")
    monkeypatch.setattr(heatmap_tiles.inference, "score_species_coords", _fake_score_species_coords)

    first = heatmap_tiles.render_heatmap_tile_bytes(101, 3, 4, 5, tile_size=4)
    second = heatmap_tiles.render_heatmap_tile_bytes(101, 3, 4, 5, tile_size=4)

    assert call_count == 1
    assert first == second


def test_render_heatmap_tile_bytes_honors_cancel_check(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fail_score_species_coords(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("score_species_coords should not run after cancellation")

    def _cancel_check() -> None:
        raise tiles.TileRenderCancelled()

    monkeypatch.setattr(heatmap_tiles, "_HEATMAP_TILE_CACHE_DIR", tmp_path)
    monkeypatch.setattr(heatmap_tiles.inference, "bundle_cache_token", lambda: "bundle-a")
    monkeypatch.setattr(heatmap_tiles.inference, "score_species_coords", _fail_score_species_coords)

    with pytest.raises(tiles.TileRenderCancelled):
        heatmap_tiles.render_heatmap_tile_bytes(
            101,
            3,
            4,
            5,
            tile_size=4,
            cancel_check=_cancel_check,
        )
