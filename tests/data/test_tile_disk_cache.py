from __future__ import annotations

from pathlib import Path

from util.tile_disk_cache import DiskTileCache, make_cache_key


def test_disk_tile_cache_write_is_atomic(tmp_path: Path) -> None:
    cache = DiskTileCache(cache_dir=tmp_path, max_bytes=256 * 1024 * 1024)
    cache.maybe_evict = lambda **_kwargs: None  # type: ignore[method-assign]

    cache.write("tile-a", b"payload")

    assert cache.path("tile-a").read_bytes() == b"payload"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["tile-a.png"]


def test_disk_tile_cache_eviction_checks_are_throttled(tmp_path: Path) -> None:
    cache = DiskTileCache(
        cache_dir=tmp_path,
        max_bytes=256 * 1024 * 1024,
        eviction_interval_seconds=5.0,
    )
    calls: list[float] = []
    cache.evict_if_needed = lambda: calls.append(1.0)  # type: ignore[method-assign]

    cache.maybe_evict(now_monotonic=10.0)
    cache.maybe_evict(now_monotonic=12.0)
    cache.maybe_evict(now_monotonic=15.0)

    assert len(calls) == 2


def test_make_cache_key_is_stable() -> None:
    left = make_cache_key(a=1, b="two", c=(3, 4))
    right = make_cache_key(c=(3, 4), b="two", a=1)

    assert left == right
