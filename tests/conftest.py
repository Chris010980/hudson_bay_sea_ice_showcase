"""Shared pytest fixtures for the test suite."""

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from pathlib import Path
import pytest

from pyproj import Transformer

@pytest.fixture
def test_environment(tmp_path: Path) -> dict[str, Path]:
    """Provide an isolated temporary filesystem for a test."""
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "output"
    build_dir = tmp_path / "build"

    data_dir.mkdir()
    output_dir.mkdir()
    build_dir.mkdir()

    return {
        "root": tmp_path,
        "data": data_dir,
        "output": output_dir,
        "build": build_dir,
    }


@pytest.fixture
def synthetic_raster(test_environment: dict[str, Path]) -> Path:
    """Create a small deterministic synthetic sea-ice GeoTIFF."""
    raster_path = test_environment["data"] / "synthetic_sea_ice.tif"

    data = np.array(
        [
            [0, 149, 150, 151, 500],
            [1000, 250, 750, 2510, 2530],
            [2540, 2550, 100, 900, 50],
            [800, 300, 150, 151, 149],
            [1000, 500, 0, 2550, 750],
        ],
        dtype=np.uint16,
    )

    transform = from_origin(
        west=0,
        north=125_000,
        xsize=25_000,
        ysize=25_000,
    )

    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": data.dtype,
        "crs": "EPSG:3411",
        "transform": transform,
    }

    with rasterio.open(raster_path, "w", **profile) as dataset:
        dataset.write(data, 1)

    return raster_path

@pytest.fixture
def synthetic_reference_raster(test_environment: dict[str, Path]) -> Path:
    """Create a small deterministic reference water raster.

    Water pixels carry a valid concentration-like value (1), non-water
    pixels carry the coast/land encoding 2510, matching the production
    reference value ranges.
    """
    raster_path = test_environment["data"] / "synthetic_reference.tif"

    data = np.array(
        [
            [1, 1, 1, 2510, 2510],
            [1, 1, 1, 2510, 2510],
            [2510, 1, 1, 1, 2510],
            [2510, 1, 1, 1, 2510],
            [2510, 2510, 1, 1, 1],
        ],
        dtype=np.uint16,
    )

    transform = from_origin(
        west=0,
        north=125_000,
        xsize=25_000,
        ysize=25_000,
    )

    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": data.dtype,
        "crs": "EPSG:3411",
        "transform": transform,
    }

    with rasterio.open(raster_path, "w", **profile) as dataset:
        dataset.write(data, 1)

    return raster_path

def _pixel_rectangle(
    transform,
    row_start: int,
    row_end: int,
    col_start: int,
    col_end: int,
) -> list[list[float]]:
    """Create a geographic polygon covering a raster pixel block.

    The polygon is constructed around the centers of the selected
    raster pixels. A small margin is used so that the selected pixel
    centers are inside the polygon while neighboring pixel centers
    remain outside.
    """

    transformer = Transformer.from_crs(
        "EPSG:3411",
        "EPSG:4326",
        always_xy=True,
    )

    # Pixel-center coordinates of the selected block.
    center_row_start = row_start
    center_row_end = row_end - 1
    center_col_start = col_start
    center_col_end = col_end - 1

    x_min = (
        transform.c
        + (center_col_start + 0.5) * transform.a
    )
    x_max = (
        transform.c
        + (center_col_end + 0.5) * transform.a
    )

    y_max = (
        transform.f
        + (center_row_start + 0.5) * transform.e
    )
    y_min = (
        transform.f
        + (center_row_end + 0.5) * transform.e
    )

    # Half a pixel in raster coordinates.
    margin_x = abs(transform.a) * 0.49
    margin_y = abs(transform.e) * 0.49

    x_min -= margin_x
    x_max += margin_x
    y_min -= margin_y
    y_max += margin_y

    corners_x = [
        x_min,
        x_max,
        x_max,
        x_min,
    ]

    corners_y = [
        y_max,
        y_max,
        y_min,
        y_min,
    ]

    lon, lat = transformer.transform(
        corners_x,
        corners_y,
    )

    return [
        [float(lon_i), float(lat_i)]
        for lon_i, lat_i in zip(lon, lat)
    ]

@pytest.fixture
def synthetic_region_file(
    test_environment: dict[str, Path],
) -> Path:
    """Create deterministic synthetic region definitions."""

    region_file = test_environment["data"] / "regions.json"

    transform = from_origin(
        west=0,
        north=125_000,
        xsize=25_000,
        ysize=25_000,
    )

    data = {
        "regions": {
            "Test Region Water": {
                "description": "Synthetic all-water test region",
                "polygon": _pixel_rectangle(
                    transform,
                    0,
                    2,
                    0,
                    2,
                ),
            },
            "Test Region Mixed": {
                "description": "Synthetic mixed water/non-water test region",
                "polygon": _pixel_rectangle(
                    transform,
                    0,
                    1,
                    2,
                    5,
                ),
            },
        }
    }

    with open(region_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    return region_file

@pytest.fixture
def expected_reference_masks() -> dict[str, np.ndarray]:
    """Return expected water-pixel indices for synthetic regions."""

    return {
        "Test Region Water": np.array(
            [0, 1, 5, 6],
            dtype=np.int64,
        ),
        "Test Region Mixed": np.array(
            [2],
            dtype=np.int64,
        ),
    }

@pytest.fixture
def fixture_dir() -> Path:
    """Return the directory containing static test fixtures."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def daily_observations_csv(fixture_dir: Path) -> Path:
    """Return the deterministic daily observations fixture."""
    return fixture_dir / "analysis" / "daily_observations.csv"


@pytest.fixture
def test_regions_json(fixture_dir: Path) -> Path:
    """Return the deterministic region configuration fixture."""
    return fixture_dir / "config" / "test_regions.json"