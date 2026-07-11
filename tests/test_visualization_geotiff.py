from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pyproj
import tifffile

os.environ.setdefault("PROJ_LIB", pyproj.datadir.get_data_dir())
os.environ.setdefault("GDAL_DATA", pyproj.datadir.get_data_dir())

from src.visualization.geotiff_plot import _prepare_plot_data, plot_geotiff_region


def test_prepare_plot_data_fills_invalid_values_with_zero() -> None:
    data = np.array([[0.0, np.nan], [0.25, -1.0]], dtype=np.float32)

    prepared = _prepare_plot_data(data)

    assert prepared[0, 0] == 0.0
    assert prepared[0, 1] == 0.0
    assert prepared[1, 0] == 0.25
    assert prepared[1, 1] == 0.0


def test_prepare_plot_data_normalizes_large_values_to_unit_range() -> None:
    data = np.array([[0.0, 2500.0, 1250.0]], dtype=np.float32)

    prepared = _prepare_plot_data(data)

    assert prepared[0, 0] == 0.0
    assert prepared[0, 1] == 1.0
    assert prepared[0, 2] == 0.5


def test_plot_geotiff_region_writes_file(tmp_path: Path) -> None:
    input_path = tmp_path / "sample_concentration.tif"
    output_path = tmp_path / "plot.png"

    data = np.arange(400, dtype=np.float32).reshape(20, 20) / 400.0
    tifffile.imwrite(input_path, data)

    result_path = plot_geotiff_region(
        input_path=input_path,
        output_path=output_path,
        bounds=(260.0, 300.0, 50.0, 75.0),
        title="Sample geotiff plot",
        show=False,
    )

    assert result_path == output_path
    assert output_path.exists()
