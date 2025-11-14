"""Dynamically choose the finest overview based on payload estimates."""

from __future__ import annotations

import argparse
import math
import os
import time
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from osgeo import gdal, osr


@dataclass(frozen=True)
class Viewport:
    name: str
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float

    @property
    def lon_span(self) -> float:
        return self.lon_max - self.lon_min

    @property
    def lat_span(self) -> float:
        return self.lat_max - self.lat_min


def _format_bytes(num_bytes: float) -> str:
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes:.0f} B"


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


def _build_transformer(ds: gdal.Dataset) -> osr.CoordinateTransformation:
    src_srs = osr.SpatialReference()
    src_wkt = ds.GetProjection()
    if not src_wkt:
        raise ValueError("Raster projection is missing.")
    src_srs.ImportFromWkt(src_wkt)
    dst_srs = osr.SpatialReference()
    dst_srs.ImportFromEPSG(4326)
    src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    dst_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return osr.CoordinateTransformation(dst_srs, src_srs)


def _project_bbox_to_pixels(
    transformer: osr.CoordinateTransformation,
    inv_gt: tuple[float, ...],
    base_width: int,
    base_height: int,
    viewport: Viewport,
) -> tuple[int, int, int, int] | None:
    corners = [
        (viewport.lon_min, viewport.lat_min),
        (viewport.lon_min, viewport.lat_max),
        (viewport.lon_max, viewport.lat_min),
        (viewport.lon_max, viewport.lat_max),
    ]
    cols: list[float] = []
    rows: list[float] = []
    for lon, lat in corners:
        x, y, _ = transformer.TransformPoint(lon, lat)
        col, row = gdal.ApplyGeoTransform(inv_gt, x, y)
        cols.append(col)
        rows.append(row)
    col_min = max(0, math.floor(min(cols)))
    row_min = max(0, math.floor(min(rows)))
    col_max = min(base_width, math.ceil(max(cols)))
    row_max = min(base_height, math.ceil(max(rows)))
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
    col_min = max(0, math.floor(base_col / decimation))
    row_min = max(0, math.floor(base_row / decimation))
    col_max = min(band_width, math.ceil((base_col + base_width) / decimation))
    row_max = min(band_height, math.ceil((base_row + base_height) / decimation))
    width = col_max - col_min
    height = row_max - row_min
    if width <= 0 or height <= 0:
        return None
    return col_min, row_min, width, height


def _build_percent_sequence(steps: int, shrink_percent: float, schedule: list[tuple[float, int | None]]) -> list[float]:
    steps = max(1, steps)
    percent_sequence: list[float] = []
    remaining = steps
    for percent, count in schedule:
        percent = max(0.0, min(percent, 0.99))
        qty = remaining if count is None or count <= 0 else min(count, remaining)
        percent_sequence.extend([percent] * qty)
        remaining -= qty
        if remaining <= 0:
            break
    if remaining > 0:
        percent_sequence.extend([shrink_percent] * remaining)
    return percent_sequence


def _generate_viewports(base: Viewport, percent_sequence: list[float]) -> list[Viewport]:
    lon_center = (base.lon_min + base.lon_max) / 2
    lat_center = (base.lat_min + base.lat_max) / 2
    lon_span = base.lon_span
    lat_span = base.lat_span
    viewports: list[Viewport] = []
    span_lon = lon_span
    span_lat = lat_span
    for idx, percent in enumerate(percent_sequence):
        percent = max(0.0, min(percent, 0.99))
        span_lon = max(1e-6, span_lon * (1 - percent))
        span_lat = max(1e-6, span_lat * (1 - percent))
        lon_min = lon_center - span_lon / 2
        lon_max = lon_center + span_lon / 2
        lat_min = lat_center - span_lat / 2
        lat_max = lat_center + span_lat / 2
        name = f"Step {idx + 1} – {span_lon:.2f}°x{span_lat:.2f}°"
        viewports.append(Viewport(name, lon_min, lat_min, lon_max, lat_max))
    return viewports


def _overview_decimations(band: gdal.Band, include_base: bool) -> list[tuple[str, float, gdal.Band]]:
    decimations = []
    count = band.GetOverviewCount()
    for idx in range(count):
        ov = band.GetOverview(idx)
        if ov is None:
            continue
        decimation = band.XSize / ov.XSize
        decimations.append((str(idx), decimation, ov))
    if include_base:
        decimations.append(("base", 1.0, band))
    decimations.sort(key=lambda x: x[1], reverse=True)  # finest (small decimation) first
    return decimations


def _estimate_payload(width: int, height: int, bytes_per_value: int) -> int:
    return width * height * bytes_per_value


def _save_plot(
    plot_dir: Path | None,
    arr: np.ndarray,
    viewport: Viewport,
    label: str,
    step_index: int,
    nodata: float | None,
) -> None:
    if plot_dir is None:
        return
    plot_dir.mkdir(parents=True, exist_ok=True)
    data = np.array(arr, copy=False).astype(float)
    if nodata is not None:
        data[data == nodata] = np.nan
    data = np.flipud(data)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(
        data,
        cmap="viridis",
        origin="lower",
        extent=(viewport.lon_min, viewport.lon_max, viewport.lat_min, viewport.lat_max),
    )
    ax.set_title(f"Step {step_index + 1} – Overview {label}")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    fig.colorbar(im, ax=ax, label="Value")
    fig.tight_layout()
    filename = plot_dir / f"dynamic_step{step_index + 1:02d}_overview{label}.png"
    fig.savefig(filename, dpi=200)
    plt.close(fig)


def _choose_overview(
    decimations: list[tuple[str, float, gdal.Band]],
    base_window: tuple[int, int, int, int],
    bytes_per_value: int,
    payload_cap: int,
) -> tuple[str, gdal.Band, int, int, int, float] | None:
    best: tuple[str, gdal.Band, int, int, int, float] | None = None
    for label, decimation, ov_band in decimations:
        window = _window_for_overview(base_window, decimation, ov_band.XSize, ov_band.YSize)
        if window is None:
            continue
        _, _, width, height = window
        payload = _estimate_payload(width, height, bytes_per_value)
        if payload <= payload_cap:
            best = (label, ov_band, *window, payload)
        else:
            break
    if best is not None:
        return best
    # fallback to coarsest overview (last entry after sorting finest-first)
    label, decimation, ov_band = decimations[-1]
    window = _window_for_overview(base_window, decimation, ov_band.XSize, ov_band.YSize)
    if window is None:
        return None
    return (label, ov_band, *window, _estimate_payload(window[2], window[3], bytes_per_value))


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Dynamically choose overviews based on payload thresholds.")
    parser.add_argument("raster", type=Path, help="Path to the raster inside the container.")
    parser.add_argument("--lon-min", type=float, default=-125.0, help="Base bounding box minimum longitude.")
    parser.add_argument("--lat-min", type=float, default=24.0, help="Base bounding box minimum latitude.")
    parser.add_argument("--lon-max", type=float, default=-66.0, help="Base bounding box maximum longitude.")
    parser.add_argument("--lat-max", type=float, default=49.0, help="Base bounding box maximum latitude.")
    parser.add_argument("--steps", type=int, default=12, help="Number of shrinking steps.")
    parser.add_argument("--shrink-percent", type=float, default=0.1, help="Fraction of original span removed each step (fallback).")
    parser.add_argument(
        "--shrink-schedule",
        type=str,
        default="",
        help="Comma-separated percent:count segments (e.g. '0.1:5,0.05:10,0.01:*'). '*' means remainder.",
    )
    parser.add_argument("--payload-cap-mb", type=float, default=5.0, help="Target payload cap per view (MB).")
    parser.add_argument("--include-base-after", type=int, default=None, help="Step index to allow base band (0-based).")
    parser.add_argument("--plot-dir", type=Path, default=Path("dynamic_plots"), help="Directory to save chosen plots.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    ds = gdal.Open(str(args.raster))
    if ds is None:
        raise ValueError(f"Unable to open raster {args.raster}")
    band = ds.GetRasterBand(1)
    if band is None:
        raise ValueError("Expected at least one raster band.")
    bytes_per_value = gdal.GetDataTypeSize(band.DataType) // 8
    if bytes_per_value <= 0:
        bytes_per_value = 4

    from_wgs = _build_transformer(ds)
    base_gt = ds.GetGeoTransform()
    base_inv_gt = _invert_transform(base_gt)
    base_width = ds.RasterXSize
    base_height = ds.RasterYSize

    allow_base_after = args.include_base_after if args.include_base_after is not None and args.include_base_after >= 0 else None
    decimations = _overview_decimations(band, include_base=True)

    steps = max(1, args.steps)
    schedule: list[tuple[float, int | None]] = []
    if args.shrink_schedule:
        for segment in args.shrink_schedule.split(","):
            segment = segment.strip()
            if not segment:
                continue
            try:
                percent_str, count_str = segment.split(":")
            except ValueError:
                raise ValueError(f"Invalid schedule segment '{segment}'. Expected format 'percent:count'.")
            percent = float(percent_str)
            count = None if count_str.strip() in ("*", "") else int(count_str)
            schedule.append((percent, count))
    percent_sequence = _build_percent_sequence(steps, args.shrink_percent, schedule)
    viewports = _generate_viewports(
        Viewport("Base", args.lon_min, args.lat_min, args.lon_max, args.lat_max),
        percent_sequence,
    )

    payload_cap_bytes = int(args.payload_cap_mb * 1024 * 1024)
    plot_dir = (Path("/workspace") / args.plot_dir).resolve()

    for idx, vp in enumerate(viewports):
        print(f"\n{vp.name}: lon [{vp.lon_min:.2f}, {vp.lon_max:.2f}] lat [{vp.lat_min:.2f}, {vp.lat_max:.2f}]")
        base_window = _project_bbox_to_pixels(from_wgs, base_inv_gt, base_width, base_height, vp)
        if base_window is None:
            print("  Viewport outside raster extent.")
            continue
        filtered_decimations = decimations.copy()
        if allow_base_after is not None and idx < allow_base_after:
            filtered_decimations = [d for d in decimations if d[0] != "base"]
        chosen = _choose_overview(filtered_decimations, base_window, bytes_per_value, payload_cap_bytes)
        if chosen is None:
            print("  No overview available.")
            continue
        label, band_to_read, col_min, row_min, win_width, win_height, estimated_payload = chosen
        print(f"  Selected overview {label} (estimated payload {_format_bytes(estimated_payload)})")
        start = time.perf_counter()
        arr = band_to_read.ReadAsArray(col_min, row_min, win_width, win_height)
        duration = time.perf_counter() - start
        if arr is None:
            print("  Read failed.")
            continue
        _save_plot(plot_dir, arr, vp, label, idx, band_to_read.GetNoDataValue())
        actual_payload = arr.size * arr.itemsize
        print(
            f"  window {win_height}x{win_width} px, payload {_format_bytes(actual_payload)}, "
            f"read {duration:.2f} s"
        )
    print("\nDynamic sampling run complete.")


if __name__ == "__main__":
    main()
