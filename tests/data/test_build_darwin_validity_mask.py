from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts import build_darwin_validity_mask as mask_builder


def test_validity_mask_from_band_marks_only_unmasked_cells() -> None:
    band = np.ma.array(
        [[1, 2, 3], [4, 5, 6]],
        mask=[[False, True, False], [True, False, True]],
    )

    mask = mask_builder._validity_mask_from_band(band)

    assert mask.dtype == np.uint8
    assert mask.tolist() == [[1, 0, 1], [0, 1, 0]]


def test_write_region_validity_mask_writes_aligned_uint8_raster(tmp_path: Path) -> None:
    region_dir = tmp_path / "lat10_lon20"
    region_dir.mkdir()
    landcover_path = region_dir / mask_builder.LANDCOVER_FILENAME
    output_path = region_dir / mask_builder.MASK_FILENAME

    profile = {
        "driver": "GTiff",
        "height": 2,
        "width": 3,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_origin(20.0, 30.0, 1.0, 1.0),
        "nodata": -9999.0,
    }
    values = np.array(
        [[1.0, -9999.0, 3.0], [4.0, 5.0, -9999.0]],
        dtype=np.float32,
    )
    with rasterio.open(landcover_path, "w", **profile) as dst:
        dst.write(values, 1)

    wrote = mask_builder.write_region_validity_mask(landcover_path, output_path)

    assert wrote is True
    assert output_path.exists()
    with rasterio.open(output_path) as ds:
        assert ds.crs == rasterio.crs.CRS.from_epsg(4326)
        assert ds.transform == profile["transform"]
        assert ds.nodata == 0
        assert ds.dtypes == ("uint8",)
        assert ds.read(1).tolist() == [[1, 0, 1], [1, 1, 0]]


def test_build_all_region_validity_masks_skips_existing_outputs(tmp_path: Path) -> None:
    region_dir = tmp_path / "lat0_lon0"
    region_dir.mkdir()
    landcover_path = region_dir / mask_builder.LANDCOVER_FILENAME
    output_path = region_dir / mask_builder.MASK_FILENAME

    with rasterio.open(
        landcover_path,
        "w",
        driver="GTiff",
        height=1,
        width=1,
        count=1,
        dtype="uint8",
        crs="EPSG:4326",
        transform=from_origin(0.0, 1.0, 1.0, 1.0),
        nodata=255,
    ) as dst:
        dst.write(np.array([[1]], dtype=np.uint8), 1)

    output_path.write_bytes(b"existing")

    written, skipped, missing_landcover = mask_builder.build_all_region_validity_masks(regions_root=tmp_path)

    assert (written, skipped, missing_landcover) == (0, 1, 0)
    assert output_path.read_bytes() == b"existing"


def test_audit_mask_against_landcover_counts_false_negatives(tmp_path: Path) -> None:
    region_dir = tmp_path / "lat0_lon0"
    region_dir.mkdir()

    profile = {
        "driver": "GTiff",
        "height": 1,
        "width": 2,
        "count": 1,
        "dtype": "uint8",
        "crs": "EPSG:4326",
        "transform": from_origin(0.0, 1.0, 1.0, 1.0),
        "nodata": 0,
    }
    with rasterio.open(region_dir / mask_builder.LANDCOVER_FILENAME, "w", **profile) as dst:
        dst.write(np.array([[5, 8]], dtype=np.uint8), 1)
    with rasterio.open(region_dir / mask_builder.MASK_FILENAME, "w", **profile) as dst:
        dst.write(np.array([[1, 0]], dtype=np.uint8), 1)

    summary = mask_builder.audit_mask_against_landcover(
        [(0.5, 0.5), (0.5, 1.5)],
        regions_root=tmp_path,
    )

    assert summary.coord_count == 2
    assert summary.mask_keep_count == 1
    assert summary.landcover_keep_count == 2
    assert summary.matched_count == 1
    assert summary.false_negative_count == 1
    assert summary.false_positive_count == 0
