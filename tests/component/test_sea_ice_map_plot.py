"""Component tests for SeaIcePlotter (issue #32).

The tests verify that the implemented GeoTIFF/map visualization
consumes a controlled observation raster and produces the
expected map products (docs/testing/test-levels.md, section
3.7):

* a plain overview map of the concentration raster,
* an overview with the analysis regions overlaid,
* one map per analysis region.

Test design:

* The input raster, the map bounds and the output path are
  constructor/argument-injectable; the controlled observation
  uses the suite's raster geometry (5 x 5 pixels, EPSG:3411,
  25 km pixels) with the observation date 2026-03-02 encoded in
  the filename (exercising the metadata extraction).
* SeaIcePlotter.load_regions() reads the region definitions
  from PROJECT_ROOT/src/config/regions.json, which cannot be
  injected through the public API (see tests/Findings.md,
  F-018). The test patches the geotiff_plot PROJECT_ROOT to
  the isolated test root and places the shared synthetic region
  file there.
* The Natural Earth background features (ocean, land,
  coastline) load external shapefiles at draw time and are
  isolated as no-ops (test-levels.md, section 9: external
  dependencies). The sea-ice display itself -- the EPSG:3411
  raster reprojected into the polar-stereographic map -- runs
  through the real implementation.
* Assertions are functional (test-levels.md, section 3.7):
  expected files, non-empty readable PNGs, extracted metadata.
  Pixel identity is deliberately not asserted.
* All tests are deterministic and require no network access.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import src.visualization.geotiff_plot as geotiff_plot_module
from src.visualization.geotiff_plot import SeaIcePlotter


# ------------------------------------------------------------------
# Controlled inputs
# ------------------------------------------------------------------

def _write_observation(directory: Path, filename: str) -> Path:
    """Write a controlled observation GeoTIFF.

    5 x 5 pixels, EPSG:3411, 25 km pixels; concentration values
    on the 0-1000 scale and the land code 2510. The filename
    carries the observation date for the metadata extraction.
    """
    data = np.array(
        [
            [900, 800, 700, 2510, 2510],
            [600, 500, 400, 2510, 2510],
            [300, 200, 100, 0, 2510],
            [0, 2510, 2510, 2510, 2510],
            [2510, 2510, 2510, 2510, 2510],
        ],
        dtype=np.uint16,
    )

    profile = {
        "driver": "GTiff",
        "height": 5,
        "width": 5,
        "count": 1,
        "dtype": data.dtype,
        "crs": "EPSG:3411",
        "transform": from_origin(
            west=0,
            north=125_000,
            xsize=25_000,
            ysize=25_000,
        ),
    }

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename

    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data, 1)

    return path


def _assert_png_product(path: Path) -> None:
    """Assert a persisted plot product is a non-empty readable PNG."""
    assert path.exists()

    content = path.read_bytes()

    assert len(content) > 0
    assert content.startswith(b"\x89PNG\r\n\x1a\n")

    image = plt.imread(path)

    assert image.size > 0


def _no_background(self) -> None:
    """Replace a Natural Earth background draw with a no-op."""
    return None


# ------------------------------------------------------------------
# Fixture: isolated project root and offline map rendering
# ------------------------------------------------------------------

@pytest.fixture
def map_plot_environment(
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    synthetic_region_file: Path,
) -> dict:
    """Isolate the SeaIcePlotter.

    Provides an isolated project root with the shared synthetic
    region definitions (for the hard-wired regions.json path)
    and an isolated plots directory.
    """
    root = test_environment["root"]
    plots_dir = test_environment["output"] / "plots"

    plots_dir.mkdir()

    # SeaIcePlotter.load_regions() reads the region definitions
    # from PROJECT_ROOT / "src/config/regions.json" (not
    # injectable, F-018); the controlled project root receives
    # the synthetic region file of the suite.
    region_target = root / "src" / "config" / "regions.json"
    region_target.parent.mkdir(parents=True)
    shutil.copyfile(synthetic_region_file, region_target)

    monkeypatch.setattr(geotiff_plot_module, "PROJECT_ROOT", root)

    # The Natural Earth background features load shapefiles at
    # draw time; they are external dependencies and are replaced
    # with no-ops (test-levels.md, section 9).
    for method_name in (
        "_draw_ocean",
        "_draw_land",
        "_draw_coastline",
    ):
        monkeypatch.setattr(SeaIcePlotter, method_name, _no_background)

    return {
        "data_dir": test_environment["data"],
        "plots_dir": plots_dir,
    }


# ------------------------------------------------------------------
# Task: test GeoTIFF/map plots (plain overview)
# ------------------------------------------------------------------

def test_overview_plot_is_created_from_geotiff(
    map_plot_environment: dict,
) -> None:
    """The plain overview map is created from a GeoTIFF.

    The observation date is extracted from the filename, the
    configured regions are loaded, and the product is saved to
    the requested destination (save() returns the resolved
    output path).
    """
    env = map_plot_environment

    observation = _write_observation(
        env["data_dir"] / "geotiff" / "2026" / "03_Mar",
        "N_20260302_concentration_v1.0.tif",
    )

    plotter = SeaIcePlotter(input_path=observation)
    plotter.load()

    # Metadata extracted from the filename.
    assert plotter.date == datetime(2026, 3, 2)

    # Region definitions loaded from the isolated project root.
    assert set(plotter.regions) == {
        "Test Region Water",
        "Test Region Mixed",
    }

    plotter.plot_overview()

    output = plotter.save(env["plots_dir"] / "sea_ice_overview.png")

    assert output == env["plots_dir"] / "sea_ice_overview.png"
    _assert_png_product(output)


# ------------------------------------------------------------------
# Task: test GeoTIFF/map plots (regions overlay)
# ------------------------------------------------------------------

def test_regions_overlay_plot_is_created(
    map_plot_environment: dict,
) -> None:
    """An overview map with all analysis regions overlaid is created."""
    env = map_plot_environment

    observation = _write_observation(
        env["data_dir"] / "geotiff" / "2026" / "03_Mar",
        "N_20260302_concentration_v1.0.tif",
    )

    plotter = SeaIcePlotter(input_path=observation)
    plotter.load()
    plotter.plot_regions()

    output = plotter.save(
        env["plots_dir"] / "sea_ice_overview_regions.png",
    )

    _assert_png_product(output)


# ------------------------------------------------------------------
# Task: test GeoTIFF/map plots (single region)
# ------------------------------------------------------------------

def test_single_region_plot_is_created(
    map_plot_environment: dict,
) -> None:
    """A dedicated map for one selected region is created."""
    env = map_plot_environment

    observation = _write_observation(
        env["data_dir"] / "geotiff" / "2026" / "03_Mar",
        "N_20260302_concentration_v1.0.tif",
    )

    plotter = SeaIcePlotter(input_path=observation)
    plotter.load()
    plotter.plot_single_region("Test Region Water")

    output = plotter.save(
        env["plots_dir"] / "sea_ice_overview_test_region_water.png",
    )

    _assert_png_product(output)