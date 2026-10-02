"""Component tests for the TimeSeriesPlotter (issue #32).

The tests verify that the implemented time-series visualization
consumes persistent analysis results and produces the expected
plot products (docs/testing/test-levels.md, section 3.7).

Covered products (src/visualization/timeseries_plot.py):

* plot_timeseries(): Cartesian coverage plots per region
  -> output/plots/timeseries/{region}_{relative,absolute}.png
* plot_anomalies(): anomaly plots per region
  -> .../timeseries/anomalies/
     {region}_{relative,absolute}_anomaly.png
* plot_threshold_durations(): seasonal duration plots
  -> .../timeseries/thresholds/
     {region}_threshold_duration.png
* plot_yearly_means(): annual mean plots with linear trend
  -> .../timeseries/{region}_yearly_mean_relative.png
* plot_polar(): polar coverage plots per region
  -> .../timeseries/{region}_polar_{relative,absolute}.png
  (polar_output_dir is configured but never used, see
  tests/Findings.md, F-017)
* plot_all(): the complete product set (16 files)

Test design:

* The controlled inputs are the three persisted analysis
  products of the TimeSeriesAnalyzer (ice_coverage_timeseries.csv,
  ice_coverage_yearly.csv, ice_coverage_events.csv), seeded with
  the column schema the analyzer writes. The dataset contains
  the regions "Test Region Water" (2500 km² water area) and
  "Test Region Mixed" (625 km²) with sample dates for the
  years 2000 and 2001, both inside the 1981-2010 climatology
  window the plotter displays.
* Hand calculations (the seeded values follow them):

    anomaly = value - climatology
      Water 2000-01-15: 90 - 80 = +10 (relative),
                         45 - 40 = +5 (absolute).
    ice area = percent * water area / 100
      Water 2000-01-15: 90 * 2500 / 100 = 2250 km².
    threshold durations (identical for every threshold, so the
    hand calculation stays minimal):
      Water 2000: 2000-07-01 -> 2000-11-10 = 132 days
             2001: 2001-07-05 -> 2001-11-05 = 123 days
             -> linear trend -9 d/year, R² = 1.0 (exact
                two-point fit).
      Mixed 2000: 2000-06-10 -> 2000-11-20 = 163 days
             2001: 2001-06-15 -> 2001-11-15 = 153 days
             -> linear trend -10 d/year, R² = 1.0.
    annual means: Water 50 -> 40 %, Mixed 70 -> 60 % relative
             -> linear trend -10 %/year each, R² = 1.0.

* Assertions are functional (test-levels.md, section 3.7):
  expected files, output paths, non-empty readable PNGs. Pixel
  identity is deliberately not asserted.
* The output location is redirected by patching the module
  constant OUTPUT_DIR (read at call time); the input paths are
  constructor-injectable. The non-injectable production
  defaults of the visualization stage are documented in
  tests/Findings.md, F-018.
* Plot generation must not modify the scientific analysis
  values: the three input files remain byte-identical.
* All tests are deterministic and require no network access.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import src.visualization.timeseries_plot as timeseries_module
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

# (region, event year, break-up date, freeze-up date); identical
# for every threshold (10, 50, 90 %). See the module header for
# the resulting durations.
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

# The complete product set of plot_all() (paths relative to the
# isolated plots directory; the polar files live in the
# timeseries directory, see F-017).
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


# ------------------------------------------------------------------
# Controlled inputs
# ------------------------------------------------------------------


def _seed_timeseries_csv(analysis_dir: Path) -> Path:
    """Write the controlled time-series product.

    The columns follow the schema the TimeSeriesAnalyzer
    persists (the plotting-relevant subset). Derived values
    follow the hand calculations of the module header:
    anomalies are value - climatology, ice areas are
    percent * water area / 100, the moving averages equal the
    observed values of the controlled sample dates.
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
    """Write the controlled threshold events product.

    Break-up and freeze-up dates are identical for every
    threshold; the resulting durations and trends are the hand
    calculations of the module header.
    """
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


def _assert_png_product(path: Path) -> None:
    """Assert a persisted plot product is a non-empty readable PNG."""
    assert path.exists()

    content = path.read_bytes()

    assert len(content) > 0
    assert content.startswith(b"\x89PNG\r\n\x1a\n")

    image = plt.imread(path)

    assert image.size > 0


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    """Read the complete state below ``root``.

    Returns the relative POSIX path of every regular file mapped
    to its content. Comparing two snapshots therefore verifies
    both the file inventory and the file contents.
    """
    snapshot: dict[str, bytes] = {}

    for path in sorted(root.rglob("*")):
        if path.is_file():
            key = path.relative_to(root).as_posix()
            snapshot[key] = path.read_bytes()

    return snapshot


# ------------------------------------------------------------------
# Fixture: controlled analysis products and isolated outputs
# ------------------------------------------------------------------


@pytest.fixture
def timeseries_plot_environment(
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Isolate the TimeSeriesPlotter.

    Provides the three controlled analysis products (schema of
    the TimeSeriesAnalyzer outputs) and a plotter wired to
    isolated input and output paths.
    """
    output_dir = test_environment["output"]
    analysis_dir = output_dir / "analysis"
    plots_dir = output_dir / "plots"

    analysis_dir.mkdir()

    timeseries_csv = _seed_timeseries_csv(analysis_dir)
    yearly_csv = _seed_yearly_csv(analysis_dir)
    events_csv = _seed_events_csv(analysis_dir)

    # The output directory is read from the module constant at
    # construction time, so it can be redirected here (the input
    # defaults are not redirectable this way, see F-018).
    monkeypatch.setattr(timeseries_module, "OUTPUT_DIR", plots_dir)

    plotter = TimeSeriesPlotter(
        csv_file=timeseries_csv,
        yearly_csv_file=yearly_csv,
        events_csv_file=events_csv,
    )

    return {
        "plotter": plotter,
        "analysis_dir": analysis_dir,
        "plots_dir": plots_dir,
        "timeseries_csv": timeseries_csv,
        "yearly_csv": yearly_csv,
        "events_csv": events_csv,
    }


# ------------------------------------------------------------------
# Task: test time-series plot generation
# ------------------------------------------------------------------


def test_plot_timeseries_creates_region_plots(
    timeseries_plot_environment: dict,
) -> None:
    """The classic time-series plots are created for every region.

    Two products per region (relative and absolute coverage),
    saved to output/plots/timeseries/. The plotter loads its
    inputs on demand (no explicit load() required).
    """
    env = timeseries_plot_environment

    env["plotter"].plot_timeseries()

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


# ------------------------------------------------------------------
# Task: test anomaly plots
# ------------------------------------------------------------------


def test_plot_anomalies_creates_anomaly_plots(
    timeseries_plot_environment: dict,
) -> None:
    """Relative and absolute anomaly plots are created per region.

    The products are saved to the anomalies subdirectory; the
    timeseries directory itself receives no files.
    """
    env = timeseries_plot_environment

    env["plotter"].load()
    env["plotter"].plot_anomalies()

    timeseries_dir = env["plots_dir"] / "timeseries"
    anomalies_dir = timeseries_dir / "anomalies"

    expected = {
        "Test_Region_Water_relative_anomaly.png",
        "Test_Region_Water_absolute_anomaly.png",
        "Test_Region_Mixed_relative_anomaly.png",
        "Test_Region_Mixed_absolute_anomaly.png",
    }

    actual = {path.name for path in anomalies_dir.glob("*.png")}

    assert actual == expected

    for name in expected:
        _assert_png_product(anomalies_dir / name)

    assert {path.name for path in timeseries_dir.iterdir()} == {
        "anomalies",
    }


# ------------------------------------------------------------------
# Task: test threshold-duration plots
# ------------------------------------------------------------------


def test_plot_threshold_durations_creates_duration_plots(
    timeseries_plot_environment: dict,
) -> None:
    """Threshold duration plots are created per region.

    One product per region in the thresholds subdirectory,
    derived from the break-up/freeze-up events of the
    controlled event product (durations 132/123 days for
    Test Region Water and 163/153 days for Test Region Mixed,
    trends -9 and -10 d/year with R² = 1.0 each; see the module
    header).
    """
    env = timeseries_plot_environment

    env["plotter"].load()
    env["plotter"].plot_threshold_durations()

    timeseries_dir = env["plots_dir"] / "timeseries"
    thresholds_dir = timeseries_dir / "thresholds"

    expected = {
        "Test_Region_Water_threshold_duration.png",
        "Test_Region_Mixed_threshold_duration.png",
    }

    actual = {path.name for path in thresholds_dir.glob("*.png")}

    assert actual == expected

    for name in expected:
        _assert_png_product(thresholds_dir / name)

    assert {path.name for path in timeseries_dir.iterdir()} == {
        "thresholds",
    }


# ------------------------------------------------------------------
# Task: test annual plots
# ------------------------------------------------------------------


def test_plot_yearly_means_creates_annual_plots(
    timeseries_plot_environment: dict,
) -> None:
    """Annual mean plots with linear trend are created per region.

    One relative product per region (the absolute means are
    part of the yearly CSV but not plotted). The controlled
    years 2000/2001 give the trends of the module header
    (-10 %/year, R² = 1.0).
    """
    env = timeseries_plot_environment

    env["plotter"].plot_yearly_means()

    timeseries_dir = env["plots_dir"] / "timeseries"

    expected = {
        "Test_Region_Water_yearly_mean_relative.png",
        "Test_Region_Mixed_yearly_mean_relative.png",
    }

    actual = {path.name for path in timeseries_dir.glob("*.png")}

    assert actual == expected

    for name in expected:
        _assert_png_product(timeseries_dir / name)


# ------------------------------------------------------------------
# Task: test polar plots
# ------------------------------------------------------------------


def test_plot_polar_creates_polar_plots(
    timeseries_plot_environment: dict,
) -> None:
    """Polar coverage plots are created per region.

    Two products per region (relative and absolute). Pinned
    implemented behavior: the files are saved into the
    timeseries directory (the configured polar_output_dir is
    never used, see tests/Findings.md, F-017).
    """
    env = timeseries_plot_environment

    env["plotter"].plot_polar()

    timeseries_dir = env["plots_dir"] / "timeseries"

    expected = {
        "Test_Region_Water_polar_relative.png",
        "Test_Region_Water_polar_absolute.png",
        "Test_Region_Mixed_polar_relative.png",
        "Test_Region_Mixed_polar_absolute.png",
    }

    actual = {path.name for path in timeseries_dir.glob("*.png")}

    assert actual == expected

    for name in expected:
        _assert_png_product(timeseries_dir / name)

    assert not (env["plots_dir"] / "polar").exists()


# ------------------------------------------------------------------
# Task: validate expected output files
# ------------------------------------------------------------------


def test_plot_all_creates_the_complete_product_set(
    timeseries_plot_environment: dict,
) -> None:
    """plot_all() generates exactly the complete product set.

    The 16 expected files of the five product families are
    created; no additional PNG products appear in the isolated
    output tree.
    """
    env = timeseries_plot_environment

    env["plotter"].plot_all()

    actual = sorted(
        path.relative_to(env["plots_dir"]).as_posix()
        for path in env["plots_dir"].rglob("*.png")
    )

    assert actual == sorted(_ALL_TIMESERIES_PRODUCTS)


# ------------------------------------------------------------------
# Acceptance criterion: plot generation does not modify
# scientific analysis values
# ------------------------------------------------------------------


def test_plot_generation_does_not_modify_analysis_results(
    timeseries_plot_environment: dict,
) -> None:
    """Generating all plots leaves the analysis products untouched.

    The three persisted analysis products remain byte-identical
    (no rewrite, no reformatting, no new columns persisted).
    """
    env = timeseries_plot_environment

    analysis_before = _snapshot_tree(env["analysis_dir"])

    env["plotter"].plot_all()

    assert _snapshot_tree(env["analysis_dir"]) == analysis_before
