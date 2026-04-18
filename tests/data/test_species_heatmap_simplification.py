from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from util import heatmap_tiles
from util import inference
from util import gis_lookup
from util import species_heatmap_feature_sources as sources
from util import species_heatmap_scorers as scorers
from util.tile_disk_cache import DiskTileCache
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
        bypass_cache=False,
        profile=None,
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


def test_darwin_scorer_forwards_bypass_cache(monkeypatch):
    observed: list[bool] = []

    def _fake_render_heatmap_tile_bytes(
        taxon_id,
        z,
        x,
        y,
        *,
        tile_size,
        feature_mode,
        cancel_check=None,
        bypass_cache=False,
        profile=None,
    ):
        observed.append(bypass_cache)
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
    scorer.render_runtime_tile_bytes(321, 3, 4, 5, tile_size=2, max_native_zoom=3, bypass_cache=True)

    assert observed == [True]


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
        profile=None,
    ) -> tuple[list[float | None], None]:
        nonlocal call_count
        call_count += 1
        return [0.5 for _ in coords], None

    monkeypatch.setattr(
        heatmap_tiles,
        "_HEATMAP_TILE_DISK_CACHE",
        DiskTileCache(cache_dir=tmp_path, max_bytes=256 * 1024 * 1024),
    )
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

    monkeypatch.setattr(
        heatmap_tiles,
        "_HEATMAP_TILE_DISK_CACHE",
        DiskTileCache(cache_dir=tmp_path, max_bytes=256 * 1024 * 1024),
    )
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


def test_render_heatmap_tile_bytes_can_bypass_cache(
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
        profile=None,
    ) -> tuple[list[float | None], None]:
        nonlocal call_count
        call_count += 1
        return [0.5 for _ in coords], None

    monkeypatch.setattr(
        heatmap_tiles,
        "_HEATMAP_TILE_DISK_CACHE",
        DiskTileCache(cache_dir=tmp_path, max_bytes=256 * 1024 * 1024),
    )
    monkeypatch.setattr(heatmap_tiles.inference, "bundle_cache_token", lambda: "bundle-a")
    monkeypatch.setattr(heatmap_tiles.inference, "score_species_coords", _fake_score_species_coords)

    heatmap_tiles.render_heatmap_tile_bytes(101, 3, 4, 5, tile_size=4, bypass_cache=True)
    heatmap_tiles.render_heatmap_tile_bytes(101, 3, 4, 5, tile_size=4, bypass_cache=True)

    assert call_count == 2


def test_batch_sample_features_records_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    coords = [(10.0, 20.0), (11.0, 21.0), (12.0, 22.0)]
    sampled_layers: list[str] = []

    monkeypatch.setattr(inference, "_raw_feature_names", {"other": []})
    monkeypatch.setattr(
        inference, "_sampled_static_feature_names", lambda: ["elevation", "landcover", "bio_1", "slope"]
    )
    monkeypatch.setattr(inference, "_raw_temporal_feature_names", lambda: [])
    monkeypatch.setattr(inference, "_resolve_sampling_workers", lambda: 1)
    monkeypatch.setattr(inference, "_DEM_DERIVED", {"slope"})
    monkeypatch.setattr(inference, "_sample_darwin_prefilter_keep_mask", lambda coords: ([True, False, True], 1))

    def _fake_batch_sample_raster(name, target_coords, dataset_cache=None):
        sampled_layers.append(name)
        values_by_coord = {
            "elevation": {(10.0, 20.0): 1.0, (11.0, 21.0): None, (12.0, 22.0): 3.0},
            "landcover": {(10.0, 20.0): 1.0, (11.0, 21.0): None, (12.0, 22.0): 3.0},
            "bio_1": {(10.0, 20.0): 1.0, (11.0, 21.0): None, (12.0, 22.0): 3.0},
        }
        return [values_by_coord[name][coord] for coord in target_coords]

    monkeypatch.setattr(inference, "_batch_sample_raster", _fake_batch_sample_raster)
    monkeypatch.setattr(
        inference,
        "_batch_compute_dem_derived",
        lambda target_coords, dem_dataset_cache=None: [{"slope": 4.0} for _ in target_coords],
    )
    monkeypatch.setattr(
        inference,
        "transform_feature_matrices",
        lambda raw_feature_template, raw_values, raw_masks, transform_spec: (raw_values, raw_masks, None),
    )
    monkeypatch.setattr(inference, "_coerce_model_input_batch", lambda feature_tensor, mask_tensor: feature_tensor)

    profile = inference.SampleFeatureProfile()
    payloads = inference._batch_sample_features(coords, profile=profile)

    assert len(payloads) == 3
    assert payloads[0] is not None
    assert payloads[1] is None
    assert payloads[2] is not None
    assert sampled_layers == ["elevation", "landcover", "bio_1"]
    assert profile.input_coord_count == 3
    assert profile.prefilter_kept_count == 2
    assert profile.prefilter_dropped_count == 1
    assert profile.active_coord_count == 2
    assert profile.static_layer_count == 4
    assert profile.dem_layer_count == 1
    assert profile.temporal_layer_count == 0
    assert profile.prefilter_seconds >= 0.0
    assert profile.dem_seconds >= 0.0
    assert profile.matrix_fill_seconds >= 0.0
    assert profile.transform_seconds >= 0.0


def test_sample_darwin_prefilter_keep_mask_falls_back_to_landcover(monkeypatch: pytest.MonkeyPatch) -> None:
    coords = [(10.0, 20.0), (11.0, 21.0), (12.0, 22.0)]

    monkeypatch.setattr(
        inference,
        "_batch_sample_region_raster_filename",
        lambda filename, target_coords, regions_root=inference._GIS_REGIONS_DIR: [1.0, None, 0.0],
    )
    monkeypatch.setattr(
        inference,
        "_batch_sample_raster",
        lambda layer_id, target_coords, dataset_cache=None: [7.0] if target_coords == [coords[1]] else [],
    )

    keep_mask, prefilter_layer_count = inference._sample_darwin_prefilter_keep_mask(coords)

    assert keep_mask == [True, True, False]
    assert prefilter_layer_count == 2


def test_batch_sample_region_raster_filename_uses_compact_window_reads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raster_path = tmp_path / "region-a" / "darwin_validity_mask.tif"
    raster_path.parent.mkdir(parents=True, exist_ok=True)
    raster_path.write_bytes(b"stub")

    observed_windows: list[tuple[int, int, int, int]] = []

    class _FakeWindow:
        def __init__(self, col_off: int, row_off: int, width: int, height: int) -> None:
            self.col_off = col_off
            self.row_off = row_off
            self.width = width
            self.height = height

    class _FakeDataset:
        nodata = None
        width = 512
        height = 512

        def index(self, lon: float, lat: float) -> tuple[int, int]:
            return int(round(lat * 10)), int(round(lon * 10))

        def read(self, indexes: int, window: _FakeWindow, boundless: bool = False):
            observed_windows.append(
                (window.row_off, window.col_off, window.height, window.width),
            )
            arr = np.empty((window.height, window.width), dtype=np.float32)
            for row in range(window.height):
                for col in range(window.width):
                    arr[row, col] = float((window.row_off + row) * 1000 + (window.col_off + col))
            return arr

        def sample(self, xy):
            raise AssertionError("compact window path should avoid ds.sample")

        def __enter__(self) -> "_FakeDataset":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    fake_rasterio = SimpleNamespace(open=lambda path: _FakeDataset())
    monkeypatch.setitem(sys.modules, "rasterio", fake_rasterio)
    monkeypatch.setitem(sys.modules, "rasterio.windows", SimpleNamespace(Window=_FakeWindow))
    monkeypatch.setattr(gis_lookup, "get_region_name", lambda lat, lon: "region-a")

    values = inference._batch_sample_region_raster_filename(
        "darwin_validity_mask.tif",
        [(1.0, 2.0), (1.1, 2.1), (1.2, 2.2)],
        regions_root=tmp_path,
    )

    assert values == [10020.0, 11021.0, 12022.0]
    assert observed_windows == [(10, 20, 3, 3)]
