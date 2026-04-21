from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import logging
import math
import time
from typing import Literal

from PIL import Image

from util import heatmap_tiles, tiles
from util.request_cancellation import CancelCheck


LOGGER = logging.getLogger("uvicorn.error")


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
class ClassicSpeciesHeatmapScorer:
    model_id: str
    reproject: bool
    forecast_hours: int
    apply_phenology: bool
    phenology_only: bool
    max_tile_size: int

    def render_tile_bytes(
        self,
        taxon_id: int,
        z: int,
        x: int,
        y: int,
        *,
        tile_size: int,
        cancel_check: CancelCheck | None = None,
    ) -> bytes:
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
            cancel_check=cancel_check,
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
        cancel_check: CancelCheck | None = None,
        bypass_cache: bool = False,
        profile: bool = False,
    ) -> bytes:
        if z <= max_native_zoom:
            return self.render_tile_bytes(
                taxon_id,
                z,
                x,
                y,
                tile_size=tile_size,
                cancel_check=cancel_check,
            )

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
            cancel_check=cancel_check,
        )
        if cancel_check is not None:
            cancel_check()
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
    head_variant: Literal["original", "reinforced"]
    client_key: str | None
    feature_mode: str
    temporal_mode: str
    forecast_hours: int
    max_tile_size: int

    def render_tile_bytes(
        self,
        taxon_id: int,
        z: int,
        x: int,
        y: int,
        *,
        tile_size: int,
        cancel_check: CancelCheck | None = None,
        bypass_cache: bool = False,
        profile: heatmap_tiles.DarwinHeatmapTileProfile | None = None,
    ) -> bytes:
        return heatmap_tiles.render_heatmap_tile_bytes(
            taxon_id,
            z,
            x,
            y,
            tile_size=tile_size,
            head_variant=self.head_variant,
            client_key=self.client_key,
            feature_mode=self.feature_mode,
            temporal_mode=self.temporal_mode,
            forecast_hours=self.forecast_hours,
            cancel_check=cancel_check,
            bypass_cache=bypass_cache,
            profile=profile,
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
        cancel_check: CancelCheck | None = None,
        bypass_cache: bool = False,
        profile: bool = False,
    ) -> bytes:
        total_start = time.perf_counter()
        tile_profile = (
            heatmap_tiles.DarwinHeatmapTileProfile(
                species_key=taxon_id,
                request_z=z,
                request_x=x,
                request_y=y,
                render_z=z,
                render_x=x,
                render_y=y,
                tile_size=tile_size,
                render_tile_size=tile_size,
                feature_mode=self.feature_mode,
                bypass_cache=bypass_cache,
                max_native_zoom=max_native_zoom,
            )
            if profile
            else None
        )
        if z <= max_native_zoom:
            payload = self.render_tile_bytes(
                taxon_id,
                z,
                x,
                y,
                tile_size=tile_size,
                cancel_check=cancel_check,
                bypass_cache=bypass_cache,
                profile=tile_profile,
            )
            if tile_profile is not None:
                tile_profile.total_seconds = time.perf_counter() - total_start
                heatmap_tiles.log_heatmap_tile_profile(tile_profile)
            return payload

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
        if tile_profile is not None:
            tile_profile.render_z = parent_zoom
            tile_profile.render_x = parent_x
            tile_profile.render_y = parent_y
            tile_profile.render_tile_size = parent_tile_size
            tile_profile.zoom_diff = zoom_diff
        parent_payload = self.render_tile_bytes(
            taxon_id,
            parent_zoom,
            parent_x,
            parent_y,
            tile_size=parent_tile_size,
            cancel_check=cancel_check,
            bypass_cache=bypass_cache,
            profile=tile_profile,
        )
        if cancel_check is not None:
            cancel_check()
        crop_start = time.perf_counter()
        payload = _crop_tile_bytes(
            parent_payload,
            scale=scale,
            subtile_x=subtile_x,
            subtile_y=subtile_y,
            parent_tile_size=parent_tile_size,
            tile_size=tile_size,
        )
        if tile_profile is not None:
            tile_profile.crop_seconds = time.perf_counter() - crop_start
            tile_profile.total_seconds = time.perf_counter() - total_start
            heatmap_tiles.log_heatmap_tile_profile(tile_profile)
        return payload
