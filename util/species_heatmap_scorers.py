from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math

from PIL import Image

from util import heatmap_tiles, tiles


def _crop_tile_bytes(
    parent_payload: bytes,
    *,
    scale: int,
    subtile_x: int,
    subtile_y: int,
    parent_tile_size: int,
    tile_size: int,
) -> bytes:
    parent_img = Image.open(BytesIO(parent_payload))
    subtile_size = parent_tile_size // scale
    left = subtile_x * subtile_size
    top = subtile_y * subtile_size
    tile_img = parent_img.crop((left, top, left + subtile_size, top + subtile_size))
    if subtile_size != tile_size:
        tile_img = tile_img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    tile_img.save(buffer, format="PNG")
    return buffer.getvalue()


@dataclass(frozen=True)
class LegacySpeciesHeatmapScorer:
    model_id: str
    reproject: bool
    forecast_hours: int
    apply_phenology: bool
    phenology_only: bool
    max_tile_size: int

    def render_tile_bytes(self, taxon_id: int, z: int, x: int, y: int, *, tile_size: int) -> bytes:
        return tiles.render_model_tile_bytes(
            taxon_id=taxon_id,
            z=z,
            x=x,
            y=y,
            model_id=self.model_id,
            tile_size=tile_size,
            reproject=self.reproject,
            forecast_hours=self.forecast_hours,
            apply_phenology=self.apply_phenology,
            phenology_only=self.phenology_only,
        )

    def render_runtime_tile_bytes(
        self,
        taxon_id: int,
        z: int,
        x: int,
        y: int,
        *,
        tile_size: int,
        max_native_zoom: int,
    ) -> bytes:
        if z <= max_native_zoom:
            return self.render_tile_bytes(taxon_id, z, x, y, tile_size=tile_size)

        zoom_diff = z - max_native_zoom
        scale = 2**zoom_diff
        parent_x = x // scale
        parent_y = y // scale
        subtile_x = x % scale
        subtile_y = y % scale
        parent_tile_size = min(tile_size * scale, self.max_tile_size)
        parent_payload = self.render_tile_bytes(
            taxon_id,
            max_native_zoom,
            parent_x,
            parent_y,
            tile_size=parent_tile_size,
        )
        return _crop_tile_bytes(
            parent_payload,
            scale=scale,
            subtile_x=subtile_x,
            subtile_y=subtile_y,
            parent_tile_size=parent_tile_size,
            tile_size=tile_size,
        )


@dataclass(frozen=True)
class DarwinSpeciesHeatmapScorer:
    feature_mode: str
    max_tile_size: int

    def render_tile_bytes(self, taxon_id: int, z: int, x: int, y: int, *, tile_size: int) -> bytes:
        return heatmap_tiles.render_heatmap_tile_bytes(
            taxon_id,
            z,
            x,
            y,
            tile_size=tile_size,
            feature_mode=self.feature_mode,
        )

    def render_runtime_tile_bytes(
        self,
        taxon_id: int,
        z: int,
        x: int,
        y: int,
        *,
        tile_size: int,
        max_native_zoom: int,
    ) -> bytes:
        if z <= max_native_zoom:
            return self.render_tile_bytes(taxon_id, z, x, y, tile_size=tile_size)

        max_parent_scale = max(1, self.max_tile_size // tile_size)
        max_parent_zoom_diff = int(math.floor(math.log2(max_parent_scale))) if max_parent_scale > 1 else 0
        parent_zoom = max(max_native_zoom, z - max_parent_zoom_diff)
        zoom_diff = z - parent_zoom
        scale = 2**zoom_diff
        parent_x = x // scale
        parent_y = y // scale
        subtile_x = x % scale
        subtile_y = y % scale
        parent_tile_size = tile_size * scale
        parent_payload = self.render_tile_bytes(
            taxon_id,
            parent_zoom,
            parent_x,
            parent_y,
            tile_size=parent_tile_size,
        )
        return _crop_tile_bytes(
            parent_payload,
            scale=scale,
            subtile_x=subtile_x,
            subtile_y=subtile_y,
            parent_tile_size=parent_tile_size,
            tile_size=tile_size,
        )
