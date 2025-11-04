#!/usr/bin/env python3
"""
Generate lightweight heatmap quicklooks for geospatial rasters.

This script downsamples large rasters (e.g., the 100 m DEM and derived terrain
layers) to a manageable preview size and renders PNG heatmaps for fast visual
QA. By default it looks for the canonical DEM plus the terrain stack
(slope/aspect/roughness) and produces per-band PNGs under `figures/`.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib

# Headless environment compatibility.
matplotlib.use("Agg")  # type: ignore[attr-defined]

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from pyproj import Transformer  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.windows import Window  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("figures/quicklooks")
DEFAULT_PROCESSED_DIR = Path("processed")
DEFAULT_CONFIG = Path("regions.json")

# Default datasets built from the canonical terrain stack (no standalone DEM quicklook).
DEFAULT_BASE_DATASETS: Tuple[Tuple[str, str, Path], ...] = (
    ("Terrain Stack", "terrain_stack", Path("terrain/terrain_stack.tif")),
)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render quicklook PNGs for rasters aligned to the WhereWild grid."
    )
    parser.add_argument(
        "--rasters",
        nargs="+",
        type=Path,
        help="Explicit raster paths. When omitted, defaults to datasets listed in regions.json.",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Automatically include all GeoTIFFs under --processed-dir.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help="Root directory to scan when --discover is enabled.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where PNG quicklooks will be written.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Region configuration JSON (default: regions.json).",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=2000,
        help="Max width/height (pixels) for the downsampled quicklook.",
    )
    parser.add_argument(
        "--percentile-clip",
        type=float,
        default=98.0,
        help="Upper percentile for contrast clipping (lower bound mirrors this value).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate PNGs even when an output file already exists.",
    )
    return parser.parse_args(argv)


def ensure_rasters(
    raster_paths: Optional[Iterable[Path]],
    discover: bool,
    processed_root: Path,
) -> List[Path]:
    discovered: List[Path] = []
    if discover:
        if not processed_root.exists():
            raise FileNotFoundError(
                f"--processed-dir {processed_root} does not exist; nothing to discover."
            )
        for pattern in ("*.tif", "*.tiff"):
            discovered.extend(sorted(processed_root.rglob(pattern)))
    provided = [Path(p) for p in raster_paths] if raster_paths else []
    if not discovered and not provided:
        raise FileNotFoundError(
            "No rasters found. Provide --rasters, enable --discover, or rely on regions.json defaults."
        )

    seen = set()
    rasters: List[Path] = []
    for path in discovered + provided:
        path = Path(path)
        if path in seen:
            continue
        seen.add(path)
        rasters.append(path)
    return rasters


def downsample_raster(
    src: rasterio.io.DatasetReader,
    max_size: int,
    band: int = 1,
) -> np.ma.MaskedArray:
    if max_size <= 0:
        data = src.read(band, masked=True)
        return data

    height, width = src.height, src.width
    scale = max(height, width) / max_size
    if scale <= 1.0:
        return src.read(band, masked=True)

    out_height = max(1, int(math.ceil(height / scale)))
    out_width = max(1, int(math.ceil(width / scale)))
    data = src.read(
        band,
        out_shape=(1, out_height, out_width),
        resampling=Resampling.average,
        masked=True,
    )
    return data


def slugify(value: str, fallback: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    cleaned = "_".join(filter(None, cleaned.split("_")))
    return cleaned or fallback


def load_config(path: Path) -> Dict[str, object]:
    if path.exists():
        with path.open() as fp:
            return json.load(fp)
    return {}


def gather_default_targets(config_path: Path, processed_root: Path) -> List[Dict[str, object]]:
    config = load_config(config_path)
    targets: List[Dict[str, object]] = []

    base_config = config.get("base", {}) if isinstance(config, dict) else {}
    base_enabled = base_config.get("quicklook", True)
    base_label = base_config.get("name", "CONUS")
    base_slug = slugify(base_label, "conus")

    if base_enabled:
        for display_name, dataset_slug, rel_path in DEFAULT_BASE_DATASETS:
            path = rel_path if rel_path.is_absolute() else processed_root / rel_path
            if path.exists():
                targets.append(
                    {
                        "region_slug": base_slug,
                        "region_label": base_label,
                        "dataset_slug": slugify(dataset_slug, dataset_slug),
                        "dataset_label": display_name,
                        "path": path,
                    }
                )

    cutouts = config.get("cutouts", []) if isinstance(config, dict) else []
    for region in cutouts:
        if not region.get("quicklook", True):
            continue
        region_label = region.get("name", "cutout")
        region_slug = slugify(region_label, region_label)
        stack_path = processed_root / "cutouts" / region_slug / "terrain_stack.tif"
        if stack_path.exists():
            targets.append(
                {
                    "region_slug": region_slug,
                    "region_label": region_label,
                    "dataset_slug": "terrain_stack",
                    "dataset_label": "Terrain Stack",
                    "path": stack_path,
                }
            )
    if not targets:
        # Fallback to base datasets even without config.
        for display_name, dataset_slug, rel_path in DEFAULT_BASE_DATASETS:
            path = rel_path if rel_path.is_absolute() else processed_root / rel_path
            if path.exists():
                targets.append(
                    {
                        "region_slug": "conus",
                        "region_label": "CONUS",
                        "dataset_slug": slugify(dataset_slug, dataset_slug),
                        "dataset_label": display_name,
                        "path": path,
                    }
                )
    return targets


def targets_from_paths(rasters: Sequence[Path], processed_root: Path) -> List[Dict[str, object]]:
    targets: List[Dict[str, object]] = []
    for path in rasters:
        path = Path(path)
        dataset_label = path.stem
        dataset_slug = slugify(dataset_label, dataset_label)
        region_slug = "conus"
        region_label = "CONUS"

        try:
            rel = path.relative_to(processed_root)
        except ValueError:
            rel = None

        if rel is not None and rel.parts:
            if rel.parts[0] == "cutouts" and len(rel.parts) >= 2:
                region_label = rel.parts[1]
                region_slug = slugify(region_label, region_label)
                dataset_label = rel.stem
                dataset_slug = slugify(dataset_label, dataset_label)
            else:
                dataset_label = rel.stem
                dataset_slug = slugify(dataset_label, dataset_label)

        targets.append(
            {
                "region_slug": region_slug,
                "region_label": region_label,
                "dataset_slug": dataset_slug,
                "dataset_label": dataset_label,
                "path": path,
            }
        )
    return targets


def pick_colormap(dataset_slug: str, band_label: str) -> Tuple[str, Optional[Tuple[float, float]]]:
    lower: Optional[float] = None
    upper: Optional[float] = None
    name = f"{dataset_slug.lower()}_{band_label.lower()}"
    if "aspect" in name:
        return "twilight", (0.0, 360.0)
    if "slope" in name:
        lower, upper = 0.0, 90.0
    if "roughness" in name:
        lower, upper = 0.0, None
    if "dem" in name:
        return "terrain", None
    return "viridis", (lower, upper) if lower is not None else None


def compute_display_range(
    data: np.ma.MaskedArray,
    explicit: Optional[Tuple[float, Optional[float]]],
    pct: float,
) -> Tuple[float, float]:
    clipped = data.compressed()
    if clipped.size == 0:
        return (0.0, 1.0)

    lower_bound: float
    upper_bound: float

    if explicit:
        lower_bound, max_bound = explicit
        if max_bound is None:
            upper_bound = float(np.nanpercentile(clipped, pct))
        else:
            upper_bound = max_bound
    else:
        lower_bound = float(np.nanpercentile(clipped, 100.0 - pct))
        upper_bound = float(np.nanpercentile(clipped, pct))

    if lower_bound == upper_bound:
        upper_bound = lower_bound + 1e-6
    return lower_bound, upper_bound


def render_quicklook(
    path: Path,
    output_path: Path,
    dataset_slug: str,
    dataset_label: str,
    region_label: str,
    max_size: int,
    pct: float,
    band: int,
    band_display: str,
) -> Path:
    with rasterio.open(path) as src:
        data = downsample_raster(src, max_size, band=band)

    cmap, explicit_range = pick_colormap(dataset_slug, band_display)
    vmin, vmax = compute_display_range(data, explicit_range, pct)

    band_text = band_display.replace("_", " ").title() if band_display else dataset_label
    title = f"{region_label} – {dataset_label}"
    if band_display:
        title += f" ({band_text})"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title(title)
    ax.axis("off")
    im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label=title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    processed_root = args.processed_dir

    try:
        if not args.rasters and not args.discover:
            targets = gather_default_targets(args.config, processed_root)
        else:
            rasters = ensure_rasters(args.rasters, args.discover, processed_root)
            targets = targets_from_paths(rasters, processed_root)
    except Exception as exc:  # pragma: no cover - CLI guard
        print(exc, file=sys.stderr)
        return 1

    if not targets:
        print("No rasters available for quicklook generation.", file=sys.stderr)
        return 1

    for target in targets:
        raster_path: Path = target["path"]
        if not raster_path.exists():
            print(f"Skipping missing raster: {raster_path}", file=sys.stderr)
            continue

        region_slug = target["region_slug"]
        region_label = target["region_label"]
        dataset_slug = target["dataset_slug"]
        dataset_label = target["dataset_label"]

        output_dir = args.output_dir / region_slug
        print(f"Rendering quicklooks for {region_label} -> {raster_path}", flush=True)

        with rasterio.open(raster_path) as src:
            descriptions = src.descriptions or ()
            band_count = src.count
            for band in range(1, band_count + 1):
                desc = descriptions[band - 1] if descriptions and descriptions[band - 1] else ""
                band_slug = slugify(desc, f"band{band}")
                band_display = desc or ("" if band_count == 1 else band_slug)

                if band_count == 1 and not desc:
                    file_slug = dataset_slug
                    band_display = ""
                else:
                    file_slug = f"{dataset_slug}_{band_slug}"

                output_path = output_dir / f"{file_slug}_quicklook.png"
                if output_path.exists() and not args.overwrite:
                    print(f"  Already exists, skipping: {output_path}", flush=True)
                    continue

                output = render_quicklook(
                    raster_path,
                    output_path,
                    dataset_slug=dataset_slug,
                    dataset_label=dataset_label,
                    region_label=region_label,
                    max_size=args.max_size,
                    pct=args.percentile_clip,
                    band=band,
                    band_display=band_display,
                )
                print(f"  Saved {output}", flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main(sys.argv[1:]))
