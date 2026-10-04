"""Tests for synthetic raster fixtures."""

from pathlib import Path

import numpy as np
import rasterio


def test_synthetic_raster(synthetic_raster: Path) -> None:
    """Verify the deterministic synthetic raster and its metadata."""
    with rasterio.open(synthetic_raster) as dataset:
        data = dataset.read(1)

        assert dataset.width == 5
        assert dataset.height == 5
        assert dataset.count == 1
        assert dataset.dtypes == ("uint16",)
        assert dataset.crs.to_epsg() == 3411

        assert dataset.transform.a == 25_000
        assert dataset.transform.e == -25_000

        assert data.shape == (5, 5)
        assert data.dtype == np.uint16

        assert data[0, 1] == 149
        assert data[0, 2] == 150
        assert data[0, 3] == 151

        assert 2510 in data
        assert 2530 in data
        assert 2540 in data
        assert 2550 in data
