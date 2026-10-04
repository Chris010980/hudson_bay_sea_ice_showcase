"""Component tests for the plot generation CLI (issue #74).

The tests verify the command line entry point in
src/visualization/generate_plots.py (tests/Findings.md, F-019
and F-025):

* argument parsing of the plot CLI (defaults, overview
  options, invalid plot types),
* and the table-driven dispatch: every plot mode reaches the
  correct runner with the parsed options, without executing
  real plotting code.

Test design:

* The plotters are replaced by controlled implementations of
  the SeaIcePlotter and TimeSeriesPlotter contracts; the
  factories are injected through the ``ts_factory`` /
  ``map_plotter_factory`` seams introduced in issue #74.
* Every test passes an explicit --log-file below the pytest
  temporary directory so no production log file is touched.

All tests are deterministic and require no network access.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import src.visualization.generate_plots as generate_plots
from src.visualization.generate_plots import (
    PLOT_TYPES,
    RUNNERS,
    main,
    parse_args,
)
from src.visualization.geotiff_plot import (
    DEFAULT_OUTPUT_PLOT_PATH,
    DEFAULT_REGION_BOUNDS,
)


class _FakeTimeSeriesPlotter:
    """Controlled TimeSeriesPlotter replacement."""

    def __init__(self, events: list[str]) -> None:
        self.events = events

    def plot_timeseries(self) -> None:
        self.events.append("plot_timeseries")

    def plot_polar(self) -> None:
        self.events.append("plot_polar")

    def plot_all(self) -> None:
        self.events.append("plot_all")


class _FakeMapPlotter:
    """Controlled SeaIcePlotter replacement."""

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.regions = ["Test Region Water", "Test Region Mixed"]
        self.saved: list = []
        self.load_error: Exception | None = None

    def load(self) -> None:
        if self.load_error is not None:
            raise self.load_error

        self.events.append("load")

    def plot_overview(self) -> None:
        self.events.append("plot_overview")

    def plot_regions(self) -> None:
        self.events.append("plot_regions")

    def plot_single_region(self, region: str) -> None:
        self.events.append(f"single:{region}")

    def draw_regions(self, selected: list[str]) -> None:
        self.events.append(f"draw:{','.join(selected)}")

    def save(self, output=None, suffix=None) -> None:
        self.saved.append((output, suffix))
        self.events.append("save")


def _ts_factory(events: list[str]):
    """Factory contract returning a controlled plotter."""

    def factory() -> _FakeTimeSeriesPlotter:
        return _FakeTimeSeriesPlotter(events)

    return factory


def _map_factory(plotter: _FakeMapPlotter):
    """Factory contract returning the prepared plotter."""

    def factory(**kwargs) -> _FakeMapPlotter:
        return plotter

    return factory


def _unexpected_ts_factory(events: list[str]):
    """Factory contract that must not be called."""

    def factory() -> _FakeTimeSeriesPlotter:
        events.append("unexpected-ts-plotter")

        return _FakeTimeSeriesPlotter(events)

    return factory


def _unexpected_map_factory(events: list[str]):
    """Factory contract that must not be called."""

    def factory(**kwargs) -> _FakeMapPlotter:
        events.append("unexpected-map-plotter")

        return _FakeMapPlotter(events)

    return factory


def test_parse_args_defaults() -> None:
    """The plot CLI parses with its documented defaults."""

    args = parse_args(["timeseries"])

    assert args.plot_type == "timeseries"
    assert args.log_level == "INFO"
    assert args.output == str(DEFAULT_OUTPUT_PLOT_PATH)
    assert args.bounds == list(DEFAULT_REGION_BOUNDS)
    assert args.input_tiff is None
    assert args.title is None
    assert args.regions is False
    assert args.region is None
    assert args.all_regions is False
    assert args.show is False


def test_parse_args_overview_options() -> None:
    """Every overview option parses with its value."""

    args = parse_args(
        [
            "overview",
            "--input-tiff",
            "data/geotiff/observation.tif",
            "--output",
            "output/plots/map.png",
            "--bounds",
            "-95",
            "-75",
            "50",
            "65",
            "--title",
            "Hudson Bay",
            "--regions",
            "--region",
            "Region A",
            "--all-regions",
            "--show",
        ]
    )

    assert args.plot_type == "overview"
    assert args.input_tiff == "data/geotiff/observation.tif"
    assert args.output == "output/plots/map.png"
    assert args.bounds == [-95.0, -75.0, 50.0, 65.0]
    assert args.title == "Hudson Bay"
    assert args.regions is True
    assert args.region == ["Region A"]
    assert args.all_regions is True
    assert args.show is True


def test_parse_args_rejects_unknown_plot_type() -> None:
    """Unknown plot types are rejected with argparse's exit."""

    with pytest.raises(SystemExit):
        parse_args(["heatmap"])


def test_runners_cover_every_plot_type() -> None:
    """The dispatch table covers exactly the valid plot types."""

    assert set(RUNNERS) == set(PLOT_TYPES)


def test_main_dispatches_timeseries(tmp_path: Path) -> None:
    """timeseries only builds the time-series plotter."""

    events: list[str] = []

    main(
        [
            "timeseries",
            "--log-file",
            str(tmp_path / "plots.log"),
        ],
        ts_factory=_ts_factory(events),
        map_plotter_factory=_unexpected_map_factory(events),
    )

    assert events == ["plot_timeseries"]


def test_main_dispatches_polar(tmp_path: Path) -> None:
    """polar only builds the time-series plotter."""

    events: list[str] = []

    main(
        [
            "polar",
            "--log-file",
            str(tmp_path / "plots.log"),
        ],
        ts_factory=_ts_factory(events),
        map_plotter_factory=_unexpected_map_factory(events),
    )

    assert events == ["plot_polar"]


def test_main_all_generates_every_product(tmp_path: Path) -> None:
    """all writes every map product, then the time series."""

    events: list[str] = []
    plotter = _FakeMapPlotter(events)

    main(
        [
            "all",
            "--log-file",
            str(tmp_path / "plots.log"),
        ],
        ts_factory=_ts_factory(events),
        map_plotter_factory=_map_factory(plotter),
    )

    assert events == [
        "load",
        "plot_overview",
        "save",
        "plot_regions",
        "save",
        "single:Test Region Water",
        "save",
        "single:Test Region Mixed",
        "save",
        "plot_all",
    ]
    assert plotter.saved == [
        (None, None),
        (None, "regions"),
        (None, "test_region_water"),
        (None, "test_region_mixed"),
    ]


def test_main_all_without_geotiff_regenerates_timeseries(
    tmp_path: Path,
) -> None:
    """A missing GeoTIFF skips the map products."""

    events: list[str] = []
    plotter = _FakeMapPlotter(events)
    plotter.load_error = FileNotFoundError("missing")

    main(
        [
            "all",
            "--log-file",
            str(tmp_path / "plots.log"),
        ],
        ts_factory=_ts_factory(events),
        map_plotter_factory=_map_factory(plotter),
    )

    assert events == ["plot_all"]


def test_main_overview_plain(tmp_path: Path) -> None:
    """A plain overview saves to the requested output."""

    events: list[str] = []
    plotter = _FakeMapPlotter(events)

    main(
        [
            "overview",
            "--output",
            "output/plots/map.png",
            "--log-file",
            str(tmp_path / "plots.log"),
        ],
        ts_factory=_unexpected_ts_factory(events),
        map_plotter_factory=_map_factory(plotter),
    )

    assert events == ["load", "plot_overview", "save"]
    assert plotter.saved == [("output/plots/map.png", None)]


def test_main_overview_with_regions_overlay(tmp_path: Path) -> None:
    """--regions draws the region overlay and saves."""

    events: list[str] = []
    plotter = _FakeMapPlotter(events)

    main(
        [
            "overview",
            "--regions",
            "--output",
            "output/plots/map.png",
            "--log-file",
            str(tmp_path / "plots.log"),
        ],
        ts_factory=_unexpected_ts_factory(events),
        map_plotter_factory=_map_factory(plotter),
    )

    assert events == ["load", "plot_regions", "save"]


def test_main_overview_with_selected_regions(tmp_path: Path) -> None:
    """--region overviews and draws the selected regions."""

    events: list[str] = []
    plotter = _FakeMapPlotter(events)

    main(
        [
            "overview",
            "--region",
            "Region A",
            "--output",
            "output/plots/map.png",
            "--log-file",
            str(tmp_path / "plots.log"),
        ],
        ts_factory=_unexpected_ts_factory(events),
        map_plotter_factory=_map_factory(plotter),
    )

    assert events == ["load", "plot_overview", "draw:Region A", "save"]


def test_main_overview_all_regions(tmp_path: Path) -> None:
    """--all-regions saves one figure per region slug."""

    events: list[str] = []
    plotter = _FakeMapPlotter(events)

    main(
        [
            "overview",
            "--all-regions",
            "--output",
            "output/plots/map.png",
            "--log-file",
            str(tmp_path / "plots.log"),
        ],
        ts_factory=_unexpected_ts_factory(events),
        map_plotter_factory=_map_factory(plotter),
    )

    assert events == [
        "load",
        "single:Test Region Water",
        "save",
        "single:Test Region Mixed",
        "save",
    ]
    assert plotter.saved == [
        (Path("output/plots/map_test_region_water.png"), None),
        (Path("output/plots/map_test_region_mixed.png"), None),
    ]


def test_main_overview_show_displays_figure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--show displays the figure after saving."""

    events: list[str] = []
    plotter = _FakeMapPlotter(events)
    shown: list[str] = []

    class _FakePyplot:
        def show(self) -> None:
            shown.append("show")

    monkeypatch.setattr(generate_plots, "plt", _FakePyplot())

    main(
        [
            "overview",
            "--show",
            "--output",
            "output/plots/map.png",
            "--log-file",
            str(tmp_path / "plots.log"),
        ],
        ts_factory=_unexpected_ts_factory(events),
        map_plotter_factory=_map_factory(plotter),
    )

    assert events == ["load", "plot_overview", "save"]
    assert shown == ["show"]
