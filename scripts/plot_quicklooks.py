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

from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from pyproj import Transformer  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.windows import Window  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("figures/quicklooks")
DEFAULT_PROCESSED_DIR = Path("processed")
DEFAULT_CONFIG = Path("regions.json")

# Default datasets baked into the project.
# Base datasets (global rasters sitting directly under processed/).
DEFAULT_BASE_DATASETS: Tuple[Tuple[str, str, Path], ...] = (
    ("Terrain Stack", "terrain_stack", Path("terrain/terrain_stack.tif")),
    ("Land Cover", "landcover", Path("landcover/landcover_100m_cog.tif")),
    ("Soil Texture", "soil_texture", Path("soil_texture/soil_texture_100m_cog.tif")),
    ("Soil Coarse Fragments", "soil_cfvo", Path("soil/cfvo_100m.tif")),
    ("Soil pH (H2O)", "soil_phh2o", Path("soil/phh2o_100m.tif")),
    ("Soil Nitrogen (%)", "soil_nitrogen", Path("soil/nitrogen_100m.tif")),
    ("Soil Organic Carbon (%)", "soil_soc", Path("soil/soc_100m.tif")),
)

# Named cutouts inherit these datasets when present under processed/cutouts/<region>/.
CUTOUT_DATASETS: Tuple[Tuple[str, str], ...] = (
    ("Terrain Stack", "terrain_stack"),
    ("Land Cover", "landcover"),
    ("Soil Texture", "soil_texture"),
    ("Soil Coarse Fragments", "soil_cfvo"),
    ("Soil pH (H2O)", "soil_phh2o"),
    ("Soil Nitrogen (%)", "soil_nitrogen"),
    ("Soil Organic Carbon (%)", "soil_soc"),
)

# Categorical rasters (we stick to nearest-neighbour sampling + discrete palettes).
CATEGORICAL_DATASETS = {"landcover"}

SOIL_TEXTURE_BAND_LABELS: Tuple[str, str, str] = (
    "Soil Sand (%)",
    "Soil Silt (%)",
    "Soil Clay (%)",
)
SOIL_TEXTURE_SCALE = 0.1
SOIL_TEXTURE_ALT_BASE = Path("soil_texture/soil_texture_100m.tif")
SOIL_PROPERTY_RANGES = {
    "soil_cfvo": (0.0, 60.0),
    "soil_phh2o": (4.0, 9.0),
    "soil_nitrogen": (0.0, 2.0),
    "soil_soc": (0.0, 10.0),
}

NLCD_CLASSES = {
    11: ("Open Water", "#476BA1"),
    12: ("Perennial Ice/Snow", "#A3CCFF"),
    21: ("Developed, Open Space", "#DDC9C9"),
    22: ("Developed, Low Intensity", "#D89382"),
    23: ("Developed, Medium Intensity", "#ED0000"),
    24: ("Developed, High Intensity", "#840000"),
    31: ("Barren Land", "#B2ADA3"),
    41: ("Deciduous Forest", "#68AB5F"),
    42: ("Evergreen Forest", "#1C5F2C"),
    43: ("Mixed Forest", "#B5C58F"),
    51: ("Dwarf Scrub", "#AF963C"),
    52: ("Shrub/Scrub", "#D1BB82"),
    71: ("Grassland/Herbaceous", "#E3E35A"),
    72: ("Sedge/Herbaceous", "#C3E87F"),
    73: ("Lichens", "#B5E9BD"),
    74: ("Moss", "#70A3BA"),
    81: ("Pasture/Hay", "#DEDFA6"),
    82: ("Cultivated Crops", "#E29E8C"),
    90: ("Woody Wetlands", "#C8E6C6"),
    95: ("Herbaceous Wetlands", "#7DC8C5"),
}


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
    """Return a deduplicated list of rasters from explicit paths, discovery, or both."""
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
    # Ordering is deterministic: discovered files first, then explicitly provided ones.
    return rasters


def downsample_raster(
    src: rasterio.io.DatasetReader,
    max_size: int,
    band: int = 1,
    resampling: Resampling = Resampling.average,
) -> np.ma.MaskedArray:
    """Read a raster band at reduced resolution to keep quicklooks speedy."""
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
        resampling=resampling,
        masked=True,
    )
    return data


def slugify(value: str, fallback: str) -> str:
    """Make filesystem-friendly slugs while keeping a human-readable fallback."""
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    cleaned = "_".join(filter(None, cleaned.split("_")))
    return cleaned or fallback


def load_config(path: Path) -> Dict[str, object]:
    """Load regions.json when present; fallback to an empty dict otherwise."""
    if path.exists():
        with path.open() as fp:
            return json.load(fp)
    return {}


def gather_default_targets(config_path: Path, processed_root: Path) -> List[Dict[str, object]]:
    """Build a list of quicklook jobs from the config file and known datasets."""
    config = load_config(config_path)
    targets: List[Dict[str, object]] = []

    base_config = config.get("base", {}) if isinstance(config, dict) else {}
    base_enabled = base_config.get("quicklook", True)
    base_label = base_config.get("name", "CONUS")
    base_slug = slugify(base_label, "conus")

    if base_enabled:
        for display_name, dataset_slug, rel_path in DEFAULT_BASE_DATASETS:
            path = rel_path if rel_path.is_absolute() else processed_root / rel_path
            if not path.exists() and dataset_slug == "soil_texture":
                alt = processed_root / SOIL_TEXTURE_ALT_BASE
                if alt.exists():
                    path = alt
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
        for display_name, dataset_slug in CUTOUT_DATASETS:
            cutout_path = processed_root / "cutouts" / region_slug / f"{dataset_slug}.tif"
            if not cutout_path.exists():
                continue
            targets.append(
                {
                    "region_slug": region_slug,
                    "region_label": region_label,
                    "dataset_slug": slugify(dataset_slug, dataset_slug),
                    "dataset_label": display_name,
                    "path": cutout_path,
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
    """Infer region labels/slugs from file paths when users pass --rasters."""
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
    if "landcover" in dataset_slug.lower():
        return "tab20", (0.0, 95.0)
    if "soil_texture" in dataset_slug.lower():
        return "YlGnBu", (0.0, 60.0)
    if dataset_slug.lower() in ("soil_cfvo",):
        return "YlOrBr", SOIL_PROPERTY_RANGES["soil_cfvo"]
    if dataset_slug.lower() in ("soil_nitrogen",):
        return "YlGn", SOIL_PROPERTY_RANGES["soil_nitrogen"]
    if dataset_slug.lower() in ("soil_soc",):
        return "PuRd", SOIL_PROPERTY_RANGES["soil_soc"]
    if dataset_slug.lower() in ("soil_phh2o",):
        return "viridis", SOIL_PROPERTY_RANGES["soil_phh2o"]
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
    """Turn masked raster values into display-friendly min/max bounds."""
    clipped = data.compressed()
    if clipped.size == 0:
        # No valid pixels—fallback to a harmless default range.
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
    """Render a single band quicklook PNG and return the output path."""
    categorical = any(token in dataset_slug for token in CATEGORICAL_DATASETS)
    resampling_method = Resampling.nearest if categorical else Resampling.average

    with rasterio.open(path) as src:
        data = downsample_raster(src, max_size, band=band, resampling=resampling_method)
        if dataset_slug == "soil_texture":
            data = np.ma.array(data, copy=False).astype(np.float32)
            data *= SOIL_TEXTURE_SCALE

    band_text = band_display.replace("_", " ").title() if band_display else dataset_label
    title = f"{region_label} – {dataset_label}"
    if band_display:
        title += f" ({band_text})"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title(title)
    ax.axis("off")

    if categorical:
        filled = np.ma.filled(data, 0)
        unique_codes = sorted({int(code) for code in np.unique(filled) if int(code) != 0})
        if not unique_codes:
            ax.text(0.5, 0.5, "No land cover classes", transform=ax.transAxes, ha="center", va="center")
        else:
            colors: List[str] = []
            labels: List[str] = []
            for code in unique_codes:
                label, color = NLCD_CLASSES.get(code, (f"Class {code}", "#808080"))
                colors.append(color)
                labels.append(f"{code}: {label}")
            cmap = ListedColormap(colors)
            boundaries = np.array(unique_codes + [unique_codes[-1] + 1])
            norm = BoundaryNorm(boundaries, cmap.N)
            masked = np.ma.masked_where(filled == 0, filled)
            ax.imshow(masked, cmap=cmap, norm=norm, interpolation="nearest")
            handles = [Patch(facecolor=colors[i], edgecolor="black", label=labels[i]) for i in range(len(labels))]
            ncol = max(1, min(4, len(handles)))
            legend = ax.legend(
                handles=handles,
                loc="lower center",
                bbox_to_anchor=(0.5, -0.1),
                frameon=False,
                ncol=ncol,
            )
            if legend:
                fig.subplots_adjust(bottom=0.15)
    else:
        cmap, explicit_range = pick_colormap(dataset_slug, band_display)
        vmin, vmax = compute_display_range(data, explicit_range, pct)
        im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="none")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label=band_text or dataset_label)

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
            # Default path: rely on regions.json + known datasets to decide what to plot.
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
            soil_labels: Optional[Tuple[str, ...]] = None
            if dataset_slug == "soil_texture":
                if len(SOIL_TEXTURE_BAND_LABELS) >= band_count:
                    soil_labels = tuple(SOIL_TEXTURE_BAND_LABELS[:band_count])

            for band in range(1, band_count + 1):
                if soil_labels:
                    desc = soil_labels[band - 1]
                else:
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
