"""Shared pytest fixtures for the test suite."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import os
import sys
from pathlib import Path
import pytest

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


