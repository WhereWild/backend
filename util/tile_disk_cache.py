from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import time


@dataclass
class DiskTileCache:
    cache_dir: Path
    max_bytes: int
    eviction_interval_seconds: float = 5.0
    last_eviction_check_monotonic: float = 0.0

    def path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.png"

    def read(self, key: str) -> bytes | None:
        path = self.path(key)
        try:
            data = path.read_bytes()
            path.touch()
            return data
        except FileNotFoundError:
            return None
        except Exception:
            return None

    def write(self, key: str, data: bytes) -> None:
        tmp_path: Path | None = None
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            target_path = self.path(key)
            with NamedTemporaryFile(
                dir=self.cache_dir,
                prefix=f".{key}-",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                tmp_file.write(data)
                tmp_path = Path(tmp_file.name)
            os.replace(tmp_path, target_path)
            self.maybe_evict()
        except Exception:
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def maybe_evict(self, *, now_monotonic: float | None = None) -> None:
        now = time.monotonic() if now_monotonic is None else now_monotonic
        if (
            self.eviction_interval_seconds > 0
            and now - self.last_eviction_check_monotonic < self.eviction_interval_seconds
        ):
            return
        self.last_eviction_check_monotonic = now
        self.evict_if_needed()

    def evict_if_needed(self) -> None:
        try:
            entries = []
            total = 0
            for path in self.cache_dir.glob("*.png"):
                stat = path.stat()
                entries.append((stat.st_mtime, stat.st_size, path))
                total += stat.st_size
            if total <= self.max_bytes:
                return
            target = int(self.max_bytes * 0.8)
            entries.sort()
            for _, size, path in entries:
                if total <= target:
                    break
                path.unlink(missing_ok=True)
                total -= size
        except Exception:
            pass


def make_cache_key(**kwargs: object) -> str:
    raw = "&".join(f"{key}={value}" for key, value in sorted(kwargs.items()))
    return hashlib.md5(raw.encode()).hexdigest()
