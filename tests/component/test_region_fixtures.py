"""Tests for deterministic region and reference-data fixtures."""

from pathlib import Path
import json

import numpy as np
import rasterio


def test_synthetic_reference_raster(
    synthetic_reference_raster: Path,
) -> None:
    """Verify the deterministic reference raster."""
    with rasterio.open(synthetic_reference_raster) as dataset:
        data = dataset.read(1)

        assert dataset.width == 5
        assert dataset.height == 5
        assert dataset.count == 1
        assert dataset.dtypes == ("uint16",)
        assert dataset.crs.to_epsg() == 3411

        assert dataset.transform.a == 25_000
        assert dataset.transform.e == -25_000

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

        assert np.array_equal(data, expected)


def test_synthetic_region_file(
    synthetic_region_file: Path,
) -> None:
    """Verify the deterministic region definitions."""
    assert synthetic_region_file.exists()

    with open(synthetic_region_file, encoding="utf-8") as file:
        data = json.load(file)

    assert "regions" in data

    regions = data["regions"]

    assert set(regions) == {
        "Test Region Water",
        "Test Region Mixed",
    }

    for region in regions.values():
        assert "polygon" in region
        assert isinstance(region["polygon"], list)
        assert len(region["polygon"]) >= 3

        for point in region["polygon"]:
            assert len(point) == 2
            assert all(isinstance(value, float) for value in point)


def test_expected_reference_masks(
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Verify the explicitly defined expected reference masks."""
    assert set(expected_reference_masks) == {
        "Test Region Water",
        "Test Region Mixed",
    }

    assert np.array_equal(
        expected_reference_masks["Test Region Water"],
        np.array([0, 1, 5, 6], dtype=np.int64),
    )

    assert np.array_equal(
        expected_reference_masks["Test Region Mixed"],
        np.array([2], dtype=np.int64),
    )