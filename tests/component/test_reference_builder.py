"""Component tests for the ReferenceBuilder (issue #17).

The tests verify reference raster loading, missing-value validation,
region configuration loading, region mask creation, reference
water-pixel counting, reference-area calculation, and reusable
reference output generation.

All tests use the controlled synthetic fixtures from tests/conftest.py
and the isolated test_environment instead of the production data/ and
output/ directories, following docs/testing/test-levels.md (section
3.3) and tests/fixtures/README.md. The naturalearth ocean dataset is
replaced by a controlled ocean polygon so that no production data is
required. The tests are deterministic and need no network access.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.errors import RasterioIOError
from pyproj import Transformer
from shapely.geometry import Polygon
from shapely.ops import transform as shapely_transform

import src.analysis.reference_builder as reference_builder_module
from src.analysis.reference_builder import ReferenceBuilder


EXPECTED_SUMMARY_KEYS = {
    "polygon_pixels",
    "water_pixels",
    "pixel_area_km2",
    "water_area_pixel_km2",
    "expected_water_pixels",
    "naturalearth_water_area_km2",
    "difference_km2",
    "difference_percent",
}


# ------------------------------------------------------------------
# Controlled ocean replacement
# ------------------------------------------------------------------

class _StubGeopandas:
    """geopandas stand-in serving a controlled synthetic ocean dataset."""

    def __init__(self, ocean: gpd.GeoDataFrame):
        self._ocean = ocean

    def read_file(self, path) -> gpd.GeoDataFrame:
        return self._ocean

    def __getattr__(self, name):
        return getattr(gpd, name)


@pytest.fixture
def synthetic_ocean(monkeypatch: pytest.MonkeyPatch) -> gpd.GeoDataFrame:
    """Replace the naturalearth ocean file with a controlled ocean polygon.

    The polygon covers the complete polar extent of the synthetic
    regions, so the intersection equals each region polygon itself.
    """

    ocean = gpd.GeoDataFrame(
        geometry=[Polygon([(-180, 80), (180, 80), (180, 90), (-180, 90)])],
        crs="EPSG:4326",
    )

    monkeypatch.setattr(
        reference_builder_module,
        "gpd",
        _StubGeopandas(ocean),
    )

    return ocean


# ------------------------------------------------------------------
# Reference raster loading
# ------------------------------------------------------------------

def test_reference_raster_loading(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
) -> None:
    """Verify that the reference raster is loaded correctly."""
    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )

    builder._load_reference()

    assert builder.band is not None
    assert builder.transform is not None

    assert builder.band.shape == (5, 5)
    assert builder.band.dtype == np.uint16

    expected = np.array(
        [
            [1, 1, 1, 2510, 2510],
            [1, 1, 1, 2510, 2510],
            [2510, 1, 1, 1, 2510],
            [2510, 1, 1, 1, 2510],
            [2510, 2510, 1, 1, 1],
        ],
        dtype=np.uint16,
    )

    assert np.array_equal(builder.band, expected)


# ------------------------------------------------------------------
# Missing-value validation
# ------------------------------------------------------------------

def test_reference_raster_rejects_missing_values(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
) -> None:
    """Verify that missing-value code 2550 is detected."""
    invalid_raster = synthetic_reference_raster.parent / "invalid_reference.tif"

    with rasterio.open(synthetic_reference_raster) as src:
        data = src.read(1).astype(np.uint16)
        profile = src.profile.copy()

    data[0, 0] = 2550

    profile["dtype"] = "uint16"

    with rasterio.open(invalid_raster, "w", **profile) as dst:
        dst.write(data, 1)

    builder = ReferenceBuilder(
        reference_tif=invalid_raster,
        region_file=synthetic_region_file,
    )

    builder._load_reference()

    with pytest.raises(
        RuntimeError,
        match=r"Reference contains 1 missing pixels\.",
    ):
        builder._check_missing_values()


def test_missing_reference_file_is_detected(
    test_environment: dict[str, Path],
    synthetic_region_file: Path,
) -> None:
    """Verify that a non-existent reference raster is rejected."""
    builder = ReferenceBuilder(
        reference_tif=test_environment["data"] / "does_not_exist.tif",
        region_file=synthetic_region_file,
    )

    with pytest.raises(RasterioIOError):
        builder._load_reference()


# ------------------------------------------------------------------
# Region configuration loading
# ------------------------------------------------------------------

def test_region_configuration_loading(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
) -> None:
    """Verify that region configuration is loaded correctly."""
    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )

    builder._load_regions()

    assert set(builder.regions) == {
        "Test Region Water",
        "Test Region Mixed",
    }

    for region in builder.regions.values():
        assert "coords" in region
        assert "polygon" in region

        assert region["coords"].shape[1] == 2
        assert region["polygon"].is_valid


def test_region_configuration_wraps_longitudes_above_180(
    synthetic_reference_raster: Path,
    test_environment: dict[str, Path],
) -> None:
    """Verify that longitudes above 180 degrees are wrapped to [-180, 180]."""
    region_file = test_environment["data"] / "regions_unwrapped.json"

    data = {
        "regions": {
            "Test Region Unwrapped": {
                "description": "Region with longitudes above 180 degrees",
                "polygon": [
                    [170.0, 50.0],
                    [190.0, 51.0],
                    [191.0, 50.5],
                    [-170.0, 50.2],
                ],
            }
        }
    }

    with open(region_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=region_file,
    )

    builder._load_regions()

    lons = builder.regions["Test Region Unwrapped"]["coords"][:, 0]

    assert np.allclose(lons, [170.0, -170.0, -169.0, -170.0])
    assert np.all(lons <= 180.0)


def test_missing_region_file_is_detected(
    synthetic_reference_raster: Path,
    test_environment: dict[str, Path],
) -> None:
    """Verify that a non-existent region configuration is rejected."""
    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=test_environment["data"] / "missing_regions.json",
    )

    with pytest.raises(FileNotFoundError):
        builder._load_regions()


# ------------------------------------------------------------------
# Region mask creation
# ------------------------------------------------------------------

def test_region_masks_contain_expected_pixels(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
    test_environment: dict[str, Path],
) -> None:
    """Verify that region masks contain the expected water pixels."""
    mask_dir = test_environment["output"] / "reference" / "filters"
    mask_dir.mkdir(parents=True)

    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )
    builder.mask_dir = mask_dir

    builder._load_reference()
    builder._load_regions()
    builder._create_region_masks()

    for region, expected_indices in expected_reference_masks.items():
        mask_file = mask_dir / f"{region}_water.npy"

        assert mask_file.exists()

        actual_indices = np.load(mask_file)

        assert np.array_equal(actual_indices, expected_indices)


# ------------------------------------------------------------------
# Reference water-pixel counts
# ------------------------------------------------------------------

def test_reference_water_pixel_counts(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
    test_environment: dict[str, Path],
) -> None:
    """Verify the expected number of water pixels per region."""
    mask_dir = test_environment["output"] / "reference" / "filters"
    mask_dir.mkdir(parents=True)

    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )
    builder.mask_dir = mask_dir

    builder._load_reference()
    builder._load_regions()
    builder._create_region_masks()

    for region, expected_indices in expected_reference_masks.items():
        summary = builder.reference_summary[region]

        expected_count = len(expected_indices)

        assert summary["water_pixels"] == expected_count
        assert summary["expected_water_pixels"] == expected_count
        assert summary["pixel_area_km2"] == 625


# ------------------------------------------------------------------
# Reference-area calculation
# ------------------------------------------------------------------

def test_reference_area_calculation(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
    test_environment: dict[str, Path],
) -> None:
    """Verify the pixel-based reference water-area calculation."""
    mask_dir = test_environment["output"] / "reference" / "filters"
    mask_dir.mkdir(parents=True)

    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )
    builder.mask_dir = mask_dir

    builder._load_reference()
    builder._load_regions()
    builder._create_region_masks()

    expected_pixel_area_km2 = 625.0

    for region, expected_indices in expected_reference_masks.items():
        expected_area = len(expected_indices) * expected_pixel_area_km2

        actual_area = builder.reference_summary[region][
            "water_area_pixel_km2"
        ]

        assert actual_area == expected_area


def test_reference_area_matches_independent_computation(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    synthetic_ocean: gpd.GeoDataFrame,
) -> None:
    """Verify naturalearth reference areas against an independent computation.

    The expected areas are derived with shapely/pyproj instead of the
    geopandas overlay used by the implementation, so the test verifies
    the acceptance criterion that reference-area calculations match
    independently calculated expected values.
    """
    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )

    builder._load_regions()

    # Controlled pixel-based water areas, independent of mask creation.
    pixel_areas_km2 = {
        "Test Region Water": 2500.0,
        "Test Region Mixed": 625.0,
    }

    for region, area in pixel_areas_km2.items():
        builder.reference_summary[region] = {
            "polygon_pixels": 4,
            "water_pixels": 4,
            "pixel_area_km2": 625,
            "water_area_pixel_km2": area,
            "expected_water_pixels": 4,
        }

    builder._calculate_reference_areas()

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)

    for region, pixel_area in pixel_areas_km2.items():
        entry = builder.reference_summary[region]

        expected_area_km2 = (
            shapely_transform(
                transformer.transform,
                builder.regions[region]["polygon"],
            ).area
            / 1e6
        )

        assert entry["naturalearth_water_area_km2"] == pytest.approx(
            expected_area_km2,
            abs=0.1,
        )

        expected_difference = pixel_area - expected_area_km2

        assert entry["difference_km2"] == pytest.approx(
            expected_difference,
            abs=0.15,
        )
        assert entry["difference_percent"] == pytest.approx(
            100.0 * expected_difference / expected_area_km2,
            abs=0.02,
        )


# ------------------------------------------------------------------
# Reusable reference output generation
# ------------------------------------------------------------------

def test_reference_output_generation(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    synthetic_ocean: gpd.GeoDataFrame,
) -> None:
    """Verify that build creates reusable reference outputs."""
    output_dir = test_environment["output"] / "reference"
    mask_dir = output_dir / "filters"
    summary_file = output_dir / "reference_summary.json"

    monkeypatch.setattr(
        reference_builder_module,
        "FILTER_DIR",
        mask_dir,
    )
    monkeypatch.setattr(
        reference_builder_module,
        "REFERENCE_SUMMARY",
        summary_file,
    )

    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )

    builder.build()

    assert summary_file.exists()
    assert mask_dir.is_dir()

    with open(summary_file, encoding="utf-8") as file:
        summary = json.load(file)

    assert set(summary) == set(expected_reference_masks)

    for region, expected_indices in expected_reference_masks.items():
        mask_file = mask_dir / f"{region}_water.npy"

        assert mask_file.exists()

        actual_indices = np.load(mask_file)

        assert np.array_equal(actual_indices, expected_indices)

        assert set(summary[region]) == EXPECTED_SUMMARY_KEYS
        assert summary[region]["water_pixels"] == len(expected_indices)
        assert summary[region]["water_area_pixel_km2"] == (
            len(expected_indices) * 625.0
        )


def test_ensure_reference_builds_when_summary_is_missing(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that a missing summary triggers a rebuild."""
    output_dir = test_environment["output"] / "reference"
    mask_dir = output_dir / "filters"
    summary_file = output_dir / "reference_summary.json"

    monkeypatch.setattr(
        reference_builder_module,
        "FILTER_DIR",
        mask_dir,
    )
    monkeypatch.setattr(
        reference_builder_module,
        "REFERENCE_SUMMARY",
        summary_file,
    )

    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )

    build_mock = Mock()
    monkeypatch.setattr(builder, "build", build_mock)

    builder.ensure_reference()

    build_mock.assert_called_once()


def test_ensure_reference_builds_when_mask_is_missing(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that a missing mask file triggers a rebuild."""
    output_dir = test_environment["output"] / "reference"
    mask_dir = output_dir / "filters"
    summary_file = output_dir / "reference_summary.json"

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        reference_builder_module,
        "FILTER_DIR",
        mask_dir,
    )
    monkeypatch.setattr(
        reference_builder_module,
        "REFERENCE_SUMMARY",
        summary_file,
    )

    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )

    build_mock = Mock()
    monkeypatch.setattr(builder, "build", build_mock)

    builder.ensure_reference()

    build_mock.assert_called_once()


def test_existing_reference_is_reused(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that an existing complete reference is not rebuilt."""
    output_dir = test_environment["output"] / "reference"
    mask_dir = output_dir / "filters"
    summary_file = output_dir / "reference_summary.json"

    mask_dir.mkdir(parents=True)

    summary = {
        region: {
            "water_pixels": len(expected_indices),
            "water_area_pixel_km2": len(expected_indices) * 625.0,
        }
        for region, expected_indices in expected_reference_masks.items()
    }

    with open(summary_file, "w", encoding="utf-8") as file:
        json.dump(summary, file)

    for region, expected_indices in expected_reference_masks.items():
        np.save(
            mask_dir / f"{region}_water.npy",
            expected_indices,
        )

    monkeypatch.setattr(
        reference_builder_module,
        "REFERENCE_SUMMARY",
        summary_file,
    )
    monkeypatch.setattr(
        reference_builder_module,
        "FILTER_DIR",
        mask_dir,
    )

    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )

    build_mock = Mock()
    monkeypatch.setattr(builder, "build", build_mock)

    builder.ensure_reference()

    build_mock.assert_not_called()

    for region, expected_indices in expected_reference_masks.items():
        mask_file = mask_dir / f"{region}_water.npy"

        assert np.array_equal(
            np.load(mask_file),
            expected_indices,
        )