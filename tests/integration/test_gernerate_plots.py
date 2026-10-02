"""Integration tests for the plot generation CLI (issue #32).

The tests verify the analysis-to-visualization integration
(docs/testing/test-levels.md, section 4.4):

    TimeSeriesAnalyzer
          |
          v
    ice_coverage_timeseries.csv
    ice_coverage_yearly.csv
    ice_coverage_events.csv
          |
          v
    generate_plots (CLI)
          |
          v
    plot files

and the orchestration implemented by
src/visualization/generate_plots.py for the plot types "all"
and "timeseries":

* "all": overview map, regions overlay, one map per region
  (from a GeoTIFF), then the complete time-series product set
  of 16 files,
* "all" without a GeoTIFF: documented fallback -- only the
  time-series product set is regenerated,
* "timeseries": only the classic per-region coverage plots.

Test design:

* The controlled analysis products use the same seeding as
  tests/component/test_timeseries_plotter.py (hand
  calculations: anomalies = value - climatology, ice areas =
  percent * water area / 100, durations 132/123 and 163/153
  days with trends -9/-10 d/year and R² = 1.0, annual means
  with trends -10 %/year).
* The visualization stage wires several production paths that
  cannot be redirected through arguments (see
  tests/Findings.md, F-018):

  - generate_plots constructs TimeSeriesPlotter() with
    definition-time production defaults -- the class is
    replaced in the generate_plots namespace with the same
    class wired to the controlled inputs,
  - the plot output directory is redirected by patching the
    timeseries_plot module constant OUTPUT_DIR (read at call
    time),
  - the map products of the "all" mode are written to the
    geotiff_plot default plot path and its suffix variants --
    the constant is patched to the isolated plots directory
    (the --output option is ignored in "all" mode, see F-019),
  - SeaIcePlotter.load_regions() reads
    PROJECT_ROOT/src/config/regions.json -- the geotiff_plot
    PROJECT_ROOT is patched to the isolated test root, which
    receives the synthetic region file.

* The Natural Earth background features (ocean, land,
  coastline) load external shapefiles at draw time and are
  isolated as no-ops (test-levels.md, section 9). The sea-ice
  display itself runs through the real implementation.
* Assertions are functional: expected files, non-empty
  readable PNGs (test-levels.md, section 3.7).
* All tests are deterministic and require no network access.
"""

from __future__ import annotations

import functools
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

import src.visualization.generate_plots as generate_plots_module
import src.visualization.geotiff_plot as geotiff_plot_module
import src.visualization.timeseries_plot as timeseries_module
from src.visualization.geotiff_plot import SeaIcePlotter
from src.visualization.timeseries_plot import TimeSeriesPlotter

# Water areas of the synthetic regions (identical to the other
# test modules of the suite).
_WATER_AREA_KM2 = {
    "Test Region Water": 2500.0,
    "Test Region Mixed": 625.0,
}

# (region, date, relative %, absolute %,
#  relative climatology %, relative sigma,
#  absolute climatology %, absolute sigma)
_TIMESERIES_ROWS = [
    (
        "Test Region Water",
        "2000-01-15",
        90.0,
        45.0,
        80.0,
        5.0,
        40.0,
        2.5,
    ),
    (
        "Test Region Water",
        "2000-07-15",
        20.0,
        10.0,
        25.0,
        5.0,
        12.5,
        2.5,
    ),
    (
        "Test Region Water",
        "2000-10-15",
        60.0,
        30.0,
        55.0,
        5.0,
        27.5,
        2.5,
    ),
    (
        "Test Region Water",
        "2001-01-15",
        80.0,
        40.0,
        80.0,
        5.0,
        40.0,
        2.5,
    ),
    (
        "Test Region Water",
        "2001-07-15",
        30.0,
        15.0,
        25.0,
        5.0,
        12.5,
        2.5,
    ),
    (
        "Test Region Water",
        "2001-10-15",
        50.0,
        25.0,
        55.0,
        5.0,
        27.5,
        2.5,
    ),
    (
        "Test Region Mixed",
        "2000-01-15",
        70.0,
        56.0,
        65.0,
        5.0,
        52.0,
        4.0,
    ),
    (
        "Test Region Mixed",
        "2000-07-15",
        10.0,
        8.0,
        15.0,
        5.0,
        12.0,
        4.0,
    ),
    (
        "Test Region Mixed",
        "2000-10-15",
        40.0,
        32.0,
        35.0,
        5.0,
        28.0,
        4.0,
    ),
    (
        "Test Region Mixed",
        "2001-01-15",
        60.0,
        48.0,
        65.0,
        5.0,
        52.0,
        4.0,
    ),
    (
        "Test Region Mixed",
        "2001-07-15",
        20.0,
        16.0,
        15.0,
        5.0,
        12.0,
        4.0,
    ),
    (
        "Test Region Mixed",
        "2001-10-15",
        30.0,
        24.0,
        35.0,
        5.0,
        28.0,
        4.0,
    ),
]

# (region, event year, break-up date, freeze-up date)
_EVENT_ROWS = [
    ("Test Region Water", 2000, "2000-07-01", "2000-11-10"),
    ("Test Region Water", 2001, "2001-07-05", "2001-11-05"),
    ("Test Region Mixed", 2000, "2000-06-10", "2000-11-20"),
    ("Test Region Mixed", 2001, "2001-06-15", "2001-11-15"),
]

_THRESHOLDS = (10.0, 50.0, 90.0)

# (region, year, relative mean %, absolute mean %)
_YEARLY_ROWS = [
    ("Test Region Water", 2000, 50.0, 25.0),
    ("Test Region Water", 2001, 40.0, 20.0),
    ("Test Region Mixed", 2000, 70.0, 56.0),
    ("Test Region Mixed", 2001, 60.0, 48.0),
]

# The complete time-series product set (paths relative to the
# isolated plots directory; see test_timeseries_plotter.py).
_ALL_TIMESERIES_PRODUCTS = [
    "timeseries/Test_Region_Mixed_absolute.png",
    "timeseries/Test_Region_Mixed_polar_absolute.png",
    "timeseries/Test_Region_Mixed_polar_relative.png",
    "timeseries/Test_Region_Mixed_relative.png",
    "timeseries/Test_Region_Mixed_yearly_mean_relative.png",
    "timeseries/Test_Region_Water_absolute.png",
    "timeseries/Test_Region_Water_polar_absolute.png",
    "timeseries/Test_Region_Water_polar_relative.png",
    "timeseries/Test_Region_Water_relative.png",
    "timeseries/Test_Region_Water_yearly_mean_relative.png",
    "timeseries/anomalies/Test_Region_Mixed_absolute_anomaly.png",
    "timeseries/anomalies/Test_Region_Mixed_relative_anomaly.png",
    "timeseries/anomalies/Test_Region_Water_absolute_anomaly.png",
    "timeseries/anomalies/Test_Region_Water_relative_anomaly.png",
    "timeseries/thresholds/Test_Region_Mixed_threshold_duration.png",
    "timeseries/thresholds/Test_Region_Water_threshold_duration.png",
]

# The map products of the "all" mode: the default plot path and
# its suffix variants (the --output option is ignored in "all"
# mode, see F-019).
_MAP_PRODUCTS = [
    "sea_ice_geotiff_overview.png",
    "sea_ice_geotiff_overview_regions.png",
    "sea_ice_geotiff_overview_test_region_water.png",
    "sea_ice_geotiff_overview_test_region_mixed.png",
]


# ------------------------------------------------------------------
# Controlled inputs
# ------------------------------------------------------------------


def _seed_timeseries_csv(analysis_dir: Path) -> Path:
    """Write the controlled time-series product.

    Same seeding as tests/component/test_timeseries_plotter.py;
    the columns follow the schema the TimeSeriesAnalyzer
    persists (the plotting-relevant subset).
    """
    records = []

    for (
        region,
        date_string,
        relative,
        absolute,
        relative_climatology,
        relative_sigma,
        absolute_climatology,
        absolute_sigma,
    ) in _TIMESERIES_ROWS:
        water_area = _WATER_AREA_KM2[region]

        records.append(
            {
                "date": date_string,
                "region": region,
                "relative_coverage_percent": relative,
                "absolute_coverage_percent": absolute,
                "relative_ice_area_km2": relative * water_area / 100.0,
                "absolute_ice_area_km2": absolute * water_area / 100.0,
                "relative_coverage_percent_ma": relative,
                "absolute_coverage_percent_ma": absolute,
                "relative_climatology_percent": relative_climatology,
                "relative_climatology_std_percent": relative_sigma,
                "absolute_climatology_percent": absolute_climatology,
                "absolute_climatology_std_percent": absolute_sigma,
                "relative_anomaly_percent": relative
                - relative_climatology,
                "absolute_anomaly_percent": absolute
                - absolute_climatology,
                "month_day": date_string[5:],
            }
        )

    path = analysis_dir / "ice_coverage_timeseries.csv"
    pd.DataFrame(records).to_csv(path, index=False)

    return path


def _seed_yearly_csv(analysis_dir: Path) -> Path:
    """Write the controlled annual means product."""
    records = []

    for region, year, relative, absolute in _YEARLY_ROWS:
        water_area = _WATER_AREA_KM2[region]

        records.append(
            {
                "region": region,
                "year": year,
                "relative_mean_coverage_percent": relative,
                "absolute_mean_coverage_percent": absolute,
                "relative_mean_ice_area_km2": relative
                * water_area
                / 100.0,
                "absolute_mean_ice_area_km2": absolute
                * water_area
                / 100.0,
            }
        )

    path = analysis_dir / "ice_coverage_yearly.csv"
    pd.DataFrame(records).to_csv(path, index=False)

    return path


def _seed_events_csv(analysis_dir: Path) -> Path:
    """Write the controlled threshold events product."""
    records = []

    for region, event_year, breakup, freezeup in _EVENT_ROWS:
        for threshold in _THRESHOLDS:
            records.append(
                {
                    "region": region,
                    "event_type": "break-up",
                    "event_year": event_year,
                    "threshold_percent": threshold,
                    "event_date": breakup,
                }
            )
            records.append(
                {
                    "region": region,
                    "event_type": "freeze-up",
                    "event_year": event_year,
                    "threshold_percent": threshold,
                    "event_date": freezeup,
                }
            )

    path = analysis_dir / "ice_coverage_events.csv"
    pd.DataFrame(records).to_csv(path, index=False)

    return path


def _write_observation(directory: Path, filename: str) -> Path:
    """Write a controlled observation GeoTIFF.

    5 x 5 pixels, EPSG:3411, 25 km pixels; concentration values
    on the 0-1000 scale and the land code 2510.
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
# Fixture: isolated CLI environment
# ------------------------------------------------------------------


@pytest.fixture
def generate_plots_environment(
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    synthetic_region_file: Path,
) -> dict:
    """Isolate the generate_plots CLI.

    Provides the controlled analysis products, an isolated
    plots directory and the namespace replacements required to
    keep the CLI away from the production output tree (see
    tests/Findings.md, F-018).
    """
    root = test_environment["root"]
    data_dir = test_environment["data"]
    output_dir = test_environment["output"]
    plots_dir = output_dir / "plots"
    analysis_dir = output_dir / "analysis"

    analysis_dir.mkdir()
    plots_dir.mkdir()

    # Controlled analysis products (TimeSeriesAnalyzer schema).
    timeseries_csv = _seed_timeseries_csv(analysis_dir)
    yearly_csv = _seed_yearly_csv(analysis_dir)
    events_csv = _seed_events_csv(analysis_dir)

    # Controlled region definitions below the patched project
    # root (SeaIcePlotter.load_regions(), see F-018).
    region_target = root / "src" / "config" / "regions.json"
    region_target.parent.mkdir(parents=True)
    shutil.copyfile(synthetic_region_file, region_target)

    # Namespace replacements (F-018).
    monkeypatch.setattr(geotiff_plot_module, "PROJECT_ROOT", root)
    monkeypatch.setattr(geotiff_plot_module, "DATA_DIR", data_dir)
    monkeypatch.setattr(
        geotiff_plot_module,
        "DEFAULT_OUTPUT_PLOT_PATH",
        plots_dir / "sea_ice_geotiff_overview.png",
    )

    for method_name in (
        "_draw_ocean",
        "_draw_land",
        "_draw_coastline",
    ):
        monkeypatch.setattr(SeaIcePlotter, method_name, _no_background)

    monkeypatch.setattr(timeseries_module, "OUTPUT_DIR", plots_dir)

    # generate_plots constructs TimeSeriesPlotter() with the
    # definition-time production defaults; the class is replaced
    # in the generate_plots namespace with the same class wired
    # to the controlled inputs.
    monkeypatch.setattr(
        generate_plots_module,
        "TimeSeriesPlotter",
        functools.partial(
            TimeSeriesPlotter,
            csv_file=timeseries_csv,
            yearly_csv_file=yearly_csv,
            events_csv_file=events_csv,
        ),
    )

    return {
        "data_dir": data_dir,
        "plots_dir": plots_dir,
        "log_file": root / "generate_plots.log",
    }


# ------------------------------------------------------------------
# Task: test the "all" plot type creates every product
# ------------------------------------------------------------------


def test_generate_all_products_from_cli(
    generate_plots_environment: dict,
) -> None:
    """The "all" CLI run creates the complete visualization set.

    Map products (plain overview, regions overlay, one map per
    region) at the default plot path and its suffix variants,
    plus the complete time-series product set of 16 files
    (docs/testing/test-levels.md, section 4.4).
    """
    env = generate_plots_environment

    observation = _write_observation(
        env["data_dir"] / "geotiff" / "2026" / "03_Mar",
        "N_20260302_concentration_v1.0.tif",
    )

    generate_plots_module.main(
        [
            "all",
            "--input-tiff",
            str(observation),
            "--log-file",
            str(env["log_file"]),
        ],
    )

    actual = sorted(
        path.relative_to(env["plots_dir"]).as_posix()
        for path in env["plots_dir"].rglob("*.png")
    )

    expected = sorted(_MAP_PRODUCTS + _ALL_TIMESERIES_PRODUCTS)

    assert actual == expected

    for name in _MAP_PRODUCTS:
        _assert_png_product(env["plots_dir"] / name)

    for name in _ALL_TIMESERIES_PRODUCTS:
        _assert_png_product(env["plots_dir"] / name)


# ------------------------------------------------------------------
# Task: test the documented no-GeoTIFF fallback
# ------------------------------------------------------------------


def test_generate_all_without_geotiff_falls_back_to_timeseries(
    generate_plots_environment: dict,
) -> None:
    """Without a GeoTIFF the "all" run regenerates only plots.

    The downloader's data directory contains no concentration
    GeoTIFF, so the map plotter cannot be constructed; the
    documented fallback runs the time-series stage alone and no
    map product is created.
    """
    env = generate_plots_environment

    generate_plots_module.main(
        [
            "all",
            "--log-file",
            str(env["log_file"]),
        ],
    )

    actual = sorted(
        path.relative_to(env["plots_dir"]).as_posix()
        for path in env["plots_dir"].rglob("*.png")
    )

    assert actual == sorted(_ALL_TIMESERIES_PRODUCTS)

    for name in _MAP_PRODUCTS:
        assert not (env["plots_dir"] / name).exists()


# ------------------------------------------------------------------
# Task: test the "timeseries" plot type scope
# ------------------------------------------------------------------


def test_generate_timeseries_type_creates_region_plots(
    generate_plots_environment: dict,
) -> None:
    """The "timeseries" CLI type regenerates the classic plots only.

    Pinned implemented behavior: the type produces the two
    per-region coverage plots; the anomaly, threshold-duration,
    polar and annual products are not part of it (only the
    "all" type runs plot_all()).
    """
    env = generate_plots_environment

    generate_plots_module.main(
        [
            "timeseries",
            "--log-file",
            str(env["log_file"]),
        ],
    )

    timeseries_dir = env["plots_dir"] / "timeseries"

    expected = {
        "Test_Region_Water_relative.png",
        "Test_Region_Water_absolute.png",
        "Test_Region_Mixed_relative.png",
        "Test_Region_Mixed_absolute.png",
    }

    actual = {path.name for path in timeseries_dir.glob("*.png")}

    assert actual == expected

    for name in expected:
        _assert_png_product(timeseries_dir / name)

    # No other product family was generated.
    assert not (timeseries_dir / "anomalies").exists()
    assert not (timeseries_dir / "thresholds").exists()
