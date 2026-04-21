"""Tests for app/runtime behavior and startup guards."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import runpy
import sys
import types
from pathlib import Path


import main


def _run_lifespan_once() -> None:
    async def _inner() -> None:
        async with main.lifespan(main.app):
            return

    asyncio.run(_inner())


def test_lifespan_handles_preload_exceptions(monkeypatch):
    calls = {"count": 0}

    def fake_preload():
        calls["count"] += 1
        if calls["count"] == 1:
            raise FileNotFoundError("missing catalog")
        raise OSError("storage unavailable")

    monkeypatch.setattr(main.gis_lookup, "preload_layer_legends", fake_preload)
    _run_lifespan_once()
    _run_lifespan_once()
    assert calls["count"] == 2


def test_path_exists_uses_remote_storage_exists(monkeypatch):
    class FakeStorage:
        is_remote = True

        @staticmethod
        def exists(path: Path) -> bool:
            return str(path).endswith("ok")

    monkeypatch.setattr(main, "get_parquet_storage", lambda *_args, **_kwargs: FakeStorage())
    assert main._path_exists(Path("/tmp/ok"))
    assert not main._path_exists(Path("/tmp/nope"))


def test_main_guard_runs_uvicorn(monkeypatch):
    calls = {}

    fake_uvicorn = types.SimpleNamespace(
        run=lambda app, host, port, reload: calls.update({"host": host, "port": port, "reload": reload, "app": app})
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    runpy.run_module("main", run_name="__main__")
    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 8000
    assert calls["reload"] is True


def test_get_species_detail_description_failure_is_swallowed(monkeypatch):
    taxon = {"taxon_key": "1", "path": "/tmp/ok", "scientific_name": "T", "rank": "SPECIES"}
    payload = {"taxon_id": 1, "scientific_name": "T", "rank": "SPECIES", "slug": "t"}
    monkeypatch.setattr(main.taxa_navigation, "get_taxon_by_id", lambda _tid: taxon)
    monkeypatch.setattr(main.taxa_navigation, "serialize_taxon", lambda _taxon: dict(payload))
    monkeypatch.setattr(
        main.descriptions,
        "build_taxon_description",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    captured = {"printed": False}
    monkeypatch.setattr(main.traceback, "print_exc", lambda: captured.__setitem__("printed", True))

    out = main.get_species_detail(1, location=None, unit_system=None)
    assert out["taxon_id"] == 1
    assert "description_profile" not in out
    assert captured["printed"] is True


def test_species_inference_heatmap_metadata_uses_single_native_zoom_source(monkeypatch):
    monkeypatch.setattr(main.inference, "is_loaded", lambda: False)

    payload = main._build_species_inference_heatmap_metadata(123)

    assert payload["max_native_zoom"] == main.DARWIN_HEATMAP_DEFAULT_MAX_NATIVE_ZOOM


def test_species_heatmap_overzoom_acquires_deep_zoom_slot(monkeypatch):
    class _FakeRequest:
        async def is_disconnected(self) -> bool:
            return False

    class _FakeScorer:
        def render_runtime_tile_bytes(self, **_kwargs):
            return b"png"

    observed = {"acquired": 0, "rendered": 0}

    @asynccontextmanager
    async def _fake_acquire_tile_render_slot(semaphore, request, *, route, **fields):
        observed["acquired"] += 1
        assert route == "species"
        assert fields == {"taxon_id": 123, "z": 9, "x": 120, "y": 95}
        yield

    async def _fake_run_tile_render_with_cancellation(request, render_fn, /, **kwargs):
        observed["rendered"] += 1
        return render_fn(**kwargs)

    monkeypatch.setattr(main, "acquire_tile_render_slot", _fake_acquire_tile_render_slot)
    monkeypatch.setattr(main, "run_tile_render_with_cancellation", _fake_run_tile_render_with_cancellation)

    async def _run() -> None:
        response = await main._render_species_heatmap_tile_response(
            _FakeRequest(),
            scorer=_FakeScorer(),
            taxon_id=123,
            z=9,
            x=120,
            y=95,
            tile_size=256,
            max_native_zoom=8,
            cache_seconds=60,
        )
        assert response.status_code == 200
        assert response.body == b"png"

    asyncio.run(_run())

    assert observed == {"acquired": 1, "rendered": 1}


def test_species_heatmap_native_zoom_skips_deep_zoom_slot(monkeypatch):
    class _FakeRequest:
        async def is_disconnected(self) -> bool:
            return False

    class _FakeScorer:
        def render_runtime_tile_bytes(self, **_kwargs):
            return b"png"

    observed = {"acquired": 0, "rendered": 0}

    @asynccontextmanager
    async def _fake_acquire_tile_render_slot(semaphore, request, *, route, **fields):
        observed["acquired"] += 1
        yield

    async def _fake_run_tile_render_with_cancellation(request, render_fn, /, **kwargs):
        observed["rendered"] += 1
        return render_fn(**kwargs)

    monkeypatch.setattr(main, "acquire_tile_render_slot", _fake_acquire_tile_render_slot)
    monkeypatch.setattr(main, "run_tile_render_with_cancellation", _fake_run_tile_render_with_cancellation)

    async def _run() -> None:
        response = await main._render_species_heatmap_tile_response(
            _FakeRequest(),
            scorer=_FakeScorer(),
            taxon_id=123,
            z=8,
            x=120,
            y=95,
            tile_size=256,
            max_native_zoom=8,
            cache_seconds=60,
        )
        assert response.status_code == 200
        assert response.body == b"png"

    asyncio.run(_run())

    assert observed == {"acquired": 0, "rendered": 1}


def test_species_inference_heatmap_route_forwards_forecast_hours(monkeypatch):
    class _FakeRequest:
        async def is_disconnected(self) -> bool:
            return False

    captured: dict[str, object] = {}

    monkeypatch.setattr(main.inference, "is_loaded", lambda: True)

    async def _fake_render_species_heatmap_tile_response(
        request,
        *,
        scorer,
        taxon_id,
        z,
        x,
        y,
        tile_size,
        max_native_zoom,
        cache_seconds,
        bypass_cache=False,
        profile=False,
    ):
        captured["forecast_hours"] = scorer.forecast_hours
        captured["taxon_id"] = taxon_id
        captured["xyz"] = (z, x, y)
        return main.Response(content=b"png", media_type="image/png")

    monkeypatch.setattr(main, "_render_species_heatmap_tile_response", _fake_render_species_heatmap_tile_response)

    async def _run() -> None:
        response = await main.species_inference_heatmap_tile_route(
            _FakeRequest(),
            taxon_id=123,
            z=8,
            x=120,
            y=95,
            forecast_hours=24,
        )
        assert response.status_code == 200

    asyncio.run(_run())

    assert captured == {
        "forecast_hours": 24,
        "taxon_id": 123,
        "xyz": (8, 120, 95),
    }
