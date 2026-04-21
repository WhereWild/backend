from __future__ import annotations

from scripts import warm_species_heatmap_tiles as warmer


def test_resolve_target_taxa_uses_classic_model_species_and_limit(monkeypatch):
    monkeypatch.setattr(warmer.models, "get_all_sdm_taxon_ids", lambda: [11, 7, 11, 3])

    assert warmer.resolve_target_taxa(limit=2) == [11, 7]


def test_plan_species_tiles_from_points_caps_each_zoom():
    points = [
        {"catalogNumber": "a", "latitude": -10.0, "longitude": -10.0},
        {"catalogNumber": "b", "latitude": 10.0, "longitude": 10.0},
    ]

    planned = warmer.plan_species_tiles_from_points(
        points,
        zooms=(3,),
        padding_degrees=0.0,
        max_tiles_per_zoom=2,
        focus_bbox=None,
    )

    assert len(planned) == 2
    assert all(tile.z == 3 for tile in planned)


def test_plan_species_tiles_from_points_respects_focus_bbox():
    points = [
        {"catalogNumber": "a", "latitude": 61.0, "longitude": -150.0},
        {"catalogNumber": "b", "latitude": 62.0, "longitude": -149.0},
    ]

    planned = warmer.plan_species_tiles_from_points(
        points,
        zooms=(5,),
        padding_degrees=0.0,
        max_tiles_per_zoom=4,
        focus_bbox=warmer.CONUS_FOCUS_BBOX,
    )

    assert planned == []


def test_warm_species_tiles_dispatches_classic_and_darwin(monkeypatch):
    calls: list[tuple[str, int, int, int, int]] = []
    classic_ctor: list[int] = []
    darwin_ctor: list[int] = []

    class _ClassicScorer:
        def render_runtime_tile_bytes(self, taxon_id, z, x, y, *, tile_size, max_native_zoom):
            calls.append(("classic", taxon_id, z, x, y))
            return b"classic"

    class _DarwinScorer:
        def render_runtime_tile_bytes(self, taxon_id, z, x, y, *, tile_size, max_native_zoom):
            calls.append(("darwin", taxon_id, z, x, y))
            return b"darwin"

    def _build_classic(**kwargs):
        classic_ctor.append(kwargs["forecast_hours"])
        return _ClassicScorer()

    def _build_darwin(**kwargs):
        darwin_ctor.append(kwargs["forecast_hours"])
        return _DarwinScorer()

    monkeypatch.setattr(warmer, "ClassicSpeciesHeatmapScorer", _build_classic)
    monkeypatch.setattr(warmer, "DarwinSpeciesHeatmapScorer", _build_darwin)
    monkeypatch.setattr(warmer, "ensure_darwin_bundle_loaded", lambda: True)
    monkeypatch.setattr(warmer.models, "has_sdm_model", lambda _taxon_id: True)
    monkeypatch.setattr(warmer.inference, "has_species", lambda _taxon_id: True)
    monkeypatch.setattr(warmer, "plan_species_tiles_for_taxon", lambda *_args, **_kwargs: [warmer.WarmTile(3, 1, 2)])

    stats = warmer.warm_species_tiles([11], renderers=("classic", "darwin"), zooms=(3,), forecast_hours=24)

    assert calls == [("classic", 11, 3, 1, 2), ("darwin", 11, 3, 1, 2)]
    assert classic_ctor == [24]
    assert darwin_ctor == [24]
    assert stats.planned_jobs == 2
    assert stats.attempted_jobs == 2
    assert stats.succeeded_jobs == 2


def test_warm_species_tiles_skips_taxa_without_occurrence_points(monkeypatch):
    monkeypatch.setattr(warmer, "plan_species_tiles_for_taxon", lambda *_args, **_kwargs: [])

    stats = warmer.warm_species_tiles([11], renderers=("classic",), dry_run=True)

    assert stats.skipped_no_points == 1
    assert stats.planned_jobs == 0
