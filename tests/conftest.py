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
    """Create a small deterministic reference water raster."""
    raster_path = test_environment["data"] / "synthetic_reference.tif"

    data = np.array(
        [
            [1, 1, 1, 0, 0],
            [1, 1, 1, 0, 0],
            [0, 1, 1, 1, 0],
            [0, 1, 1, 1, 0],
            [0, 0, 1, 1, 1],
        ],
        dtype=np.uint8,
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
    """Create a geographic polygon around a raster pixel block."""

    transformer = Transformer.from_crs(
        "EPSG:3411",
        "EPSG:4326",
        always_xy=True,
    )

    x_min = transform.c
    x_max = transform.c + col_end * transform.a

    y_max = transform.f + row_start * transform.e
    y_min = transform.f + row_end * transform.e

    corners_x = [x_min, x_max, x_max, x_min]
    corners_y = [y_max, y_max, y_min, y_min]

    lon, lat = transformer.transform(corners_x, corners_y)

    return [
        [float(lon[0]), float(lat[0])],
        [float(lon[1]), float(lat[1])],
        [float(lon[2]), float(lat[2])],
        [float(lon[3]), float(lat[3])],
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