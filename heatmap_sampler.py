"""Reusable helper for sampling heatmap payloads from a raster."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from osgeo import gdal, osr


@dataclass(frozen=True)
class BoundingBox:
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float


def _invert_transform(gt: Sequence[float]) -> tuple[float, ...]:
    result = gdal.InvGeoTransform(gt)
    if result is None:
        raise RuntimeError("Unable to invert geotransform.")
    if isinstance(result, tuple):
        if len(result) == 2 and isinstance(result[0], (int, bool)):
            success, inv_gt = result
            if success != 1 or inv_gt is None:
                raise RuntimeError("Unable to invert geotransform.")
            return tuple(inv_gt)
        if len(result) == 6:
            return tuple(result)
    raise RuntimeError(f"Unexpected InvGeoTransform result: {result}")


def _overview_geotransform(base_gt: Sequence[float], decimation: float) -> tuple[float, ...]:
    return (
        base_gt[0],
        base_gt[1] * decimation,
        base_gt[2] * decimation,
        base_gt[3],
        base_gt[4] * decimation,
        base_gt[5] * decimation,
    )


def _project_bbox_to_pixels(
    transformer: osr.CoordinateTransformation,
    inv_gt: tuple[float, ...],
    base_width: int,
    base_height: int,
    bbox: BoundingBox,
) -> tuple[int, int, int, int] | None:
    corners = [
        (bbox.lon_min, bbox.lat_min),
        (bbox.lon_min, bbox.lat_max),
        (bbox.lon_max, bbox.lat_min),
        (bbox.lon_max, bbox.lat_max),
    ]
    cols: list[float] = []
    rows: list[float] = []
    for lon, lat in corners:
        x, y, _ = transformer.TransformPoint(lon, lat)
        col, row = gdal.ApplyGeoTransform(inv_gt, x, y)
        cols.append(col)
        rows.append(row)
    col_min = max(0, int(np.floor(min(cols))))
    row_min = max(0, int(np.floor(min(rows))))
    col_max = min(base_width, int(np.ceil(max(cols))))
    row_max = min(base_height, int(np.ceil(max(rows))))
    width = col_max - col_min
    height = row_max - row_min
    if width <= 0 or height <= 0:
        return None
    return col_min, row_min, width, height


def _window_for_overview(
    base_window: tuple[int, int, int, int],
    decimation: float,
    band_width: int,
    band_height: int,
) -> tuple[int, int, int, int] | None:
    base_col, base_row, base_width, base_height = base_window
    col_min = max(0, int(np.floor(base_col / decimation)))
    row_min = max(0, int(np.floor(base_row / decimation)))
    col_max = min(band_width, int(np.ceil((base_col + base_width) / decimation)))
    row_max = min(band_height, int(np.ceil((base_row + base_height) / decimation)))
    width = col_max - col_min
    height = row_max - row_min
    if width <= 0 or height <= 0:
        return None
    return col_min, row_min, width, height


def _overview_decimations(band: gdal.Band, include_base: bool) -> list[tuple[str, float, gdal.Band]]:
    decimations: list[tuple[str, float, gdal.Band]] = []
    for idx in range(band.GetOverviewCount()):
        ov = band.GetOverview(idx)
        if ov is None:
            continue
        decimation = band.XSize / ov.XSize
        decimations.append((str(idx), decimation, ov))
    if include_base:
        decimations.append(("base", 1.0, band))
    decimations.sort(key=lambda x: x[1], reverse=True)  # finest first
    return decimations


def _estimate_payload(width: int, height: int, bytes_per_value: int) -> int:
    return width * height * bytes_per_value


class HeatmapSampler:
    """Utility for sampling a raster into Google Maps heatmap payloads."""

    def __init__(self, raster_path: Path | str, include_base: bool = True) -> None:
        ds = gdal.Open(str(raster_path))
        if ds is None:
            raise ValueError(f"Unable to open raster {raster_path}")
        band = ds.GetRasterBand(1)
        if band is None:
            raise ValueError("Expected at least one raster band.")
        self.ds = ds
        self.band = band
        self.bytes_per_value = gdal.GetDataTypeSize(band.DataType) // 8 or 4
        self.base_gt = ds.GetGeoTransform()
        self.base_inv_gt = _invert_transform(self.base_gt)
        self.base_width = ds.RasterXSize
        self.base_height = ds.RasterYSize
        self.src_srs, self.dst_srs = self._build_spatial_refs()
        self.to_raster = osr.CoordinateTransformation(self.dst_srs, self.src_srs)
        self.to_wgs = osr.CoordinateTransformation(self.src_srs, self.dst_srs)
        self.decimations = _overview_decimations(band, include_base=include_base)

    def _build_spatial_refs(self) -> tuple[osr.SpatialReference, osr.SpatialReference]:
        src_srs = osr.SpatialReference()
        src_srs.ImportFromWkt(self.ds.GetProjection())
        dst_srs = osr.SpatialReference()
        dst_srs.ImportFromEPSG(4326)
        src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        dst_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        return src_srs, dst_srs

    def sample(
        self,
        bbox: BoundingBox,
        payload_cap_mb: float = 5.0,
        include_base_after: int | None = None,
    ) -> dict[str, object]:
        base_window = _project_bbox_to_pixels(
            self.to_raster,
            self.base_inv_gt,
            self.base_width,
            self.base_height,
            bbox,
        )
        if base_window is None:
            raise ValueError("Viewport lies outside the raster extent.")
        allowed_decimations = (
            [d for d in self.decimations if d[0] != "base"]
            if include_base_after is not None and include_base_after < 0
            else self.decimations
        )
        payload_cap = int(payload_cap_mb * 1024 * 1024)
        choice = self._choose_overview(allowed_decimations, base_window, payload_cap)
        if choice is None:
            raise RuntimeError("No overview produced payload under the cap.")
        return choice

    def _choose_overview(
        self,
        decimations: list[tuple[str, float, gdal.Band]],
        base_window: tuple[int, int, int, int],
        payload_cap: int,
    ) -> dict[str, object] | None:
        best: dict[str, object] | None = None
        for label, decimation, ov_band in decimations:
            window = _window_for_overview(base_window, decimation, ov_band.XSize, ov_band.YSize)
            if window is None:
                continue
            col_min, row_min, width, height = window
            estimated_payload = _estimate_payload(width, height, self.bytes_per_value)
            if estimated_payload > payload_cap:
                continue
            arr = ov_band.ReadAsArray(col_min, row_min, width, height)
            if arr is None:
                continue
            data = self._to_points(arr, decimation, col_min, row_min)
            best = {
                "overview": label,
                "decimation": decimation,
                "window": {"col": col_min, "row": row_min, "width": width, "height": height},
                "estimated_payload": estimated_payload,
                "payload_bytes": arr.size * arr.itemsize,
                "points": data,
            }
            break
        return best

    def _to_points(
        self,
        arr: np.ndarray,
        decimation: float,
        col_min: int,
        row_min: int,
    ) -> list[dict[str, float]]:
        gt = _overview_geotransform(self.base_gt, decimation)
        nodata = self.band.GetNoDataValue()
        nrows, ncols = arr.shape
        points: list[dict[str, float]] = []
        for r in range(nrows):
            for c in range(ncols):
                value = float(arr[r, c])
                if nodata is not None and value == nodata:
                    continue
                x = gt[0] + (col_min + c + 0.5) * gt[1] + (row_min + r + 0.5) * gt[2]
                y = gt[3] + (col_min + c + 0.5) * gt[4] + (row_min + r + 0.5) * gt[5]
                lon, lat, _ = self.to_wgs.TransformPoint(x, y)
                points.append({"lat": lat, "lng": lon, "weight": value})
        return points

    def _build_src_srs(self) -> osr.SpatialReference:
        src_srs = osr.SpatialReference()
        src_srs.ImportFromWkt(self.ds.GetProjection())
        src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        return src_srs

    def _build_dst_srs(self) -> osr.SpatialReference:
        dst_srs = osr.SpatialReference()
        dst_srs.ImportFromEPSG(4326)
        dst_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        return dst_srs
