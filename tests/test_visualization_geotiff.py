from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pyproj
import tifffile

os.environ.setdefault("PROJ_LIB", pyproj.datadir.get_data_dir())
os.environ.setdefault("GDAL_DATA", pyproj.datadir.get_data_dir())

from src.visualization.geotiff_plot import plot_geotiff_region


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
