"""End-to-end test for the incremental update workflow
(issue #41, docs/testing/test-levels.md, section 5.3).

The test runs the real update pipeline over an existing
results history (observation 2026-03-01, produced by the
real spatial chain) and adds the new observation 2026-03-02
(plus an older 2026-02-28 file that must be skipped):

    existing historical results
      + new observation
          |
          v
    update_pipeline.main (collaborators injected, issue #106)
          |
          v
    real process_data stage (real RegionAnalyzer, real
    ResultsManager, real TimeSeriesAnalyzer)
          |
          v
    real plots stage ("all" via the F-018 seams)
          |
          v
    real build_pages stage
          |
          v
    isolated build/ website

The NSIDC download stays a controlled fake (no network,
test-levels.md, section 11 note: E2E tests use controlled or
mocked external input); it delegates the local-archive scan
to the real downloader. The reference products, the history
and both observations use the hand-calculated values of
tests/integration/test_spatial_processing_chain.py.
"""

from __future__ import annotations

import functools
import json
from datetime import date
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

import src.analysis.process_data as process_data_module
import src.analysis.reference_builder as reference_builder_module
import src.update.build_pages as build_pages_module
import src.update.update_pipeline as update_pipeline_module
import src.visualization.generate_plots as generate_plots_module
from src.analysis.reference_builder import ReferenceBuilder
from src.analysis.region_analyzer import RegionAnalyzer
from src.analysis.results_manager import ResultsManager
from src.analysis.timeseries_analyzer import TimeSeriesAnalyzer
from src.data_download.downloader import (
    DownloadSummary,
    NSIDCDownloader,
)
from src.visualization.geotiff_plot import SeaIcePlotter
from src.visualization.timeseries_plot import TimeSeriesPlotter

_DAY_1_MIXED = {
    "region": "Test Region Mixed",
    "date": "2026-03-01",
    "water_pixels": 1,
    "water_area_km2": 625.0,
    "absolute_ice_area_km2": 625.0,
    "relative_ice_area_km2": 500.0,
    "absolute_coverage_percent": 100.0,
    "relative_coverage_percent": 80.0,
    "missing_pixels": 0,
}

_DAY_1_WATER = {
    "region": "Test Region Water",
    "date": "2026-03-01",
    "water_pixels": 4,
    "water_area_km2": 2500.0,
    "absolute_ice_area_km2": 1250.0,
    "relative_ice_area_km2": 625.0,
    "absolute_coverage_percent": 50.0,
    "relative_coverage_percent": 25.0,
    "missing_pixels": 0,
}

_DAY_2_MIXED = {
    "region": "Test Region Mixed",
    "date": "2026-03-02",
    "water_pixels": 1,
    "water_area_km2": 625.0,
    "absolute_ice_area_km2": 0.0,
    "relative_ice_area_km2": 0.0,
    "absolute_coverage_percent": 0.0,
    "relative_coverage_percent": 0.0,
    "missing_pixels": 0,
}

_DAY_2_WATER = {
    "region": "Test Region Water",
    "date": "2026-03-02",
    "water_pixels": 4,
    "water_area_km2": 2500.0,
    "absolute_ice_area_km2": 1875.0,
    "relative_ice_area_km2": 843.75,
    "absolute_coverage_percent": 75.0,
    "relative_coverage_percent": 33.75,
    "missing_pixels": 0,
}

_FLOAT_COLUMNS = {
    "water_area_km2",
    "absolute_ice_area_km2",
    "relative_ice_area_km2",
    "absolute_coverage_percent",
    "relative_coverage_percent",
}

# The plot products expected for the two-day dataset: the map
# products of the "all" mode plus the classical, anomaly and
# polar time-series products. The yearly and threshold-duration
# products require complete region-years and are skipped with a
# warning (F-031 resolution).
_EXPECTED_PLOTS = sorted(
    [
        "spatial/overview.png",
        "spatial/overview_regions.png",
        "spatial/overview_test_region_water.png",
        "spatial/overview_test_region_mixed.png",
        "daily_timeseries/classical_timeseries/relative/"
        "Test_Region_Water_relative.png",
        "daily_timeseries/classical_timeseries/relative/"
        "Test_Region_Mixed_relative.png",
        "daily_timeseries/classical_timeseries/absolute/"
        "Test_Region_Water_absolute.png",
        "daily_timeseries/classical_timeseries/absolute/"
        "Test_Region_Mixed_absolute.png",
        "daily_timeseries/anomalies/relative/"
        "Test_Region_Water_relative_anomaly.png",
        "daily_timeseries/anomalies/relative/"
        "Test_Region_Mixed_relative_anomaly.png",
        "daily_timeseries/anomalies/absolute/"
        "Test_Region_Water_absolute_anomaly.png",
        "daily_timeseries/anomalies/absolute/"
        "Test_Region_Mixed_absolute_anomaly.png",
        "daily_timeseries/polar/relative/"
        "Test_Region_Water_polar_relative.png",
        "daily_timeseries/polar/relative/"
        "Test_Region_Mixed_polar_relative.png",
        "daily_timeseries/polar/absolute/"
        "Test_Region_Water_polar_absolute.png",
        "daily_timeseries/polar/absolute/"
        "Test_Region_Mixed_polar_absolute.png",
    ]
)


class _StubGeopandas:
    """geopandas stand-in serving a controlled ocean dataset."""

    def __init__(self, ocean: gpd.GeoDataFrame) -> None:
        self._ocean = ocean

    def read_file(self, path) -> gpd.GeoDataFrame:
        return self._ocean

    def __getattr__(self, name):
        return getattr(gpd, name)


class _ReferenceReady:
    """Reference guard of the process stage contract.

    The controlled reference products are built once by the
    fixture; the real ``ensure_reference()`` rebuild is a
    no-op for the update run.
    """

    def ensure_reference(self) -> None:
        return None


class _FakeDownloader:
    """Controlled NSIDCDownloader replacement (records all calls).

    The local-archive scan is delegated to the real downloader
    on the isolated data directory; the network sync itself is
    controlled.
    """

    def __init__(
        self,
        events: list[str],
        local_base: Path | None = None,
    ) -> None:
        self.events = events
        self.downloaded_files = 1
        self.sync_calls: list[dict] = []
        self.delete_calls = 0
        self._local_files = (
            NSIDCDownloader(local_base=local_base)
            if local_base is not None
            else None
        )

    def sync(self, **kwargs) -> DownloadSummary:
        self.events.append("sync")
        self.sync_calls.append(kwargs)
        return DownloadSummary(
            checked_files=2,
            downloaded_files=self.downloaded_files,
        )

    def count_local_files_after(self, start_date) -> int:
        """Delegate the local scan to the real downloader."""
        if self._local_files is None:
            return 0
        return self._local_files.count_local_files_after(start_date)

    def delete_local_data(self) -> None:
        self.events.append("delete")
        self.delete_calls += 1


def _no_background(self) -> None:
    """Replace a Natural Earth background draw with a no-op."""
    return None


def _write_observation(
    directory: Path,
    filename: str,
    values: dict[int, int],
) -> Path:
    """Write a controlled daily observation GeoTIFF."""
    data = np.full((5, 5), 2510, dtype=np.uint16)

    for flat_index, value in values.items():
        data.flat[flat_index] = value

    transform = from_origin(
        west=0,
        north=125_000,
        xsize=25_000,
        ysize=25_000,
    )

    profile = {
        "driver": "GTiff",
        "height": 5,
        "width": 5,
        "count": 1,
        "dtype": data.dtype,
        "crs": "EPSG:3411",
        "transform": transform,
    }

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename

    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data, 1)

    return path


def _region_values(
    expected_reference_masks: dict[str, np.ndarray],
    water_values: list[int],
    mixed_values: list[int],
) -> dict[int, int]:
    """Map per-region concentration values to flat pixel indices."""
    return dict(
        zip(
            expected_reference_masks["Test Region Water"],
            water_values,
            strict=True,
        )
    ) | dict(
        zip(
            expected_reference_masks["Test Region Mixed"],
            mixed_values,
            strict=True,
        )
    )


def _assert_row(
    df: pd.DataFrame,
    position: int,
    expected: dict,
) -> None:
    """Assert one persisted CSV row against an expected record."""
    row = df.iloc[position]

    for column, value in expected.items():
        if column in _FLOAT_COLUMNS:
            assert row[column] == pytest.approx(value)
        else:
            assert row[column] == value


def _assert_png_product(path: Path) -> None:
    """Assert a persisted plot product is a non-empty readable PNG."""
    assert path.exists()

    content = path.read_bytes()

    assert len(content) > 0
    assert content.startswith(b"\x89PNG\r\n\x1a\n")

    image = plt.imread(path)

    assert image.size > 0


@pytest.fixture
def e2e_update_environment(
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
) -> dict:
    """Isolate the incremental update workflow.

    Provides:

    * controlled reference products built by the real
      ReferenceBuilder (injected paths, controlled ocean),
    * a controlled existing history: observation 2026-03-01 is
      processed through the real spatial chain and the derived
      products are generated by the real TimeSeriesAnalyzer,
    * a controlled website source directory,
    * and the pipeline collaborators of issue #106: the real
      process stage (real process_data.main with injected
      collaborators), the real plots stage ("all" via the
      F-018 seams) and the real build stage; only the NSIDC
      network sync is a controlled fake.
    """
    data_dir = test_environment["data"]
    output_dir = test_environment["output"]

    geotiff_dir = data_dir / "geotiff"
    analysis_dir = output_dir / "analysis"
    reference_dir = output_dir / "reference"
    filter_dir = reference_dir / "filters"
    reference_json = reference_dir / "reference_summary.json"
    plots_dir = output_dir / "plots"
    html_dir = test_environment["root"] / "html"
    build_dir = test_environment["build"]

    csv_path = analysis_dir / "ice_coverage_summary.csv"
    latest_json_path = analysis_dir / "latest.json"
    timeseries_csv = analysis_dir / "ice_coverage_timeseries.csv"
    yearly_csv = analysis_dir / "ice_coverage_yearly.csv"
    events_csv = analysis_dir / "ice_coverage_events.csv"

    # Controlled reference products (real ReferenceBuilder).
    ocean = gpd.GeoDataFrame(
        geometry=[
            Polygon(
                [(-180, 80), (180, 80), (180, 90), (-180, 90)],
            )
        ],
        crs="EPSG:4326",
    )
    monkeypatch.setattr(
        reference_builder_module,
        "gpd",
        _StubGeopandas(ocean),
    )

    ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
        mask_dir=filter_dir,
        summary_path=reference_json,
    ).build()

    # Controlled history: 2026-03-01 processed by the real chain.
    observation_1 = _write_observation(
        geotiff_dir / "2026" / "03_Mar",
        "N_20260301_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[400, 600, 100, 0],
            mixed_values=[800],
        ),
    )

    manager = ResultsManager(
        csv_path=csv_path,
        latest_json_path=latest_json_path,
    )

    analyzer = RegionAnalyzer(
        input_tif=observation_1,
        reference_json=reference_json,
        filter_dir=filter_dir,
    )
    manager.add_results(analyzer.analyze())
    manager.save()

    # Derived products of the history (real TimeSeriesAnalyzer).
    timeseries = TimeSeriesAnalyzer(
        csv_path=csv_path,
        output_path=timeseries_csv,
        yearly_output_path=yearly_csv,
        events_output_path=events_csv,
    )

    timeseries.analyze()
    timeseries.save()

    # Controlled website source.
    html_dir.mkdir()
    (html_dir / "index.html").write_text(
        "<html><body>site</body></html>",
        encoding="utf-8",
    )

    # The Natural Earth background features of the map products
    # load shapefiles at draw time; they are replaced with no-ops
    # (test-levels.md, section 9).
    for method_name in (
        "_draw_ocean",
        "_draw_land",
        "_draw_coastline",
    ):
        monkeypatch.setattr(
            SeaIcePlotter,
            method_name,
            _no_background,
        )

    # Pipeline collaborators (injected explicitly, issue #106).
    events: list[str] = []

    downloader = _FakeDownloader(
        events,
        geotiff_dir,
    )

    results_factory = functools.partial(
        ResultsManager,
        csv_path=csv_path,
        latest_json_path=latest_json_path,
    )

    def process_stage(argv):
        """Real process stage on the isolated directories."""
        events.append("process")

        return process_data_module.main(
            argv,
            data_dir=geotiff_dir,
            reference_builder=_ReferenceReady(),
            analyzer_factory=functools.partial(
                RegionAnalyzer,
                reference_json=reference_json,
                filter_dir=filter_dir,
            ),
            results=ResultsManager(
                csv_path=csv_path,
                latest_json_path=latest_json_path,
            ),
            timeseries=TimeSeriesAnalyzer(
                csv_path=csv_path,
                output_path=timeseries_csv,
                yearly_output_path=yearly_csv,
                events_output_path=events_csv,
            ),
        )

    def plots_stage(argv):
        """Real plots stage ("all") via the F-018 seams."""
        events.append("plots")

        generate_plots_module.main(
            argv,
            ts_factory=functools.partial(
                TimeSeriesPlotter,
                csv_file=timeseries_csv,
                yearly_csv_file=yearly_csv,
                events_csv_file=events_csv,
                output_dir=plots_dir,
            ),
            map_plotter_factory=functools.partial(
                SeaIcePlotter,
                region_file=synthetic_region_file,
                data_dir=geotiff_dir,
                default_output_path=(
                    plots_dir / "spatial" / "overview.png"
                ),
            ),
        )

    def build_stage(argv):
        """Real build stage against the isolated directories."""
        events.append("build")

        build_pages_module.main(
            argv,
            html_dir=html_dir,
            output_dir=output_dir,
            build_dir=build_dir,
        )

    return {
        "data_dir": data_dir,
        "geotiff_dir": geotiff_dir,
        "csv": csv_path,
        "latest": latest_json_path,
        "timeseries": timeseries_csv,
        "plots_dir": plots_dir,
        "build_dir": build_dir,
        "downloader": downloader,
        "events": events,
        "results_factory": results_factory,
        "downloader_factory": lambda: downloader,
        "process_stage": process_stage,
        "plots_stage": plots_stage,
        "build_stage": build_stage,
        "log_file": test_environment["root"] / "update.log",
    }


def test_incremental_update_updates_all_products(
    e2e_update_environment: dict,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """An update run incorporates the new observation everywhere.

    Existing history: 2026-03-01 (processed, derived products
    generated). New inputs: 2026-02-28 (older than the latest
    processed date; must be skipped) and 2026-03-02 (new).

    Verified (test-levels.md, section 5.3):

    * the stages run in the order sync -> process -> plots ->
      build -> cleanup and processing starts after the latest
      processed observation,
    * the existing historical rows remain unchanged,
    * the new observation is incorporated, no duplicates are
      introduced and the pre-start-date file is not processed,
    * the derived time-series product is updated consistently,
    * the expected plots are regenerated as readable PNGs,
    * and the generated website reflects the updated results.
    """
    env = e2e_update_environment

    # History snapshot before the update.
    history_before = pd.read_csv(env["csv"])
    history_before = history_before[
        history_before["date"] == "2026-03-01"
    ].reset_index(drop=True)

    # New inputs: one older, one new observation.
    _write_observation(
        env["geotiff_dir"] / "2026" / "02_Feb",
        "N_20260228_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[400, 600, 100, 0],
            mixed_values=[800],
        ),
    )

    _write_observation(
        env["geotiff_dir"] / "2026" / "03_Mar",
        "N_20260302_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[150, 1000, 0, 200],
            mixed_values=[0],
        ),
    )

    update_pipeline_module.main(
        [
            "--log-file",
            str(env["log_file"]),
        ],
        results_factory=env["results_factory"],
        downloader_factory=env["downloader_factory"],
        process_stage=env["process_stage"],
        plots_stage=env["plots_stage"],
        build_stage=env["build_stage"],
    )

    # Correct stage ordering and update boundary.
    assert env["events"] == [
        "sync",
        "process",
        "plots",
        "build",
        "delete",
    ]

    assert env["downloader"].sync_calls == [
        {"start_date": date(2026, 3, 2)},
    ]

    # Results: history intact, new observation incorporated,
    # no duplicates, pre-start-date file not processed.
    df = pd.read_csv(env["csv"])

    assert len(df) == 4

    expected_rows = [
        _DAY_1_MIXED,
        _DAY_1_WATER,
        _DAY_2_MIXED,
        _DAY_2_WATER,
    ]

    for position, expected in enumerate(expected_rows):
        _assert_row(df, position, expected)

    assert "2026-02-28" not in set(df["date"])

    history_after = df[df["date"] == "2026-03-01"].reset_index(
        drop=True
    )

    pd.testing.assert_frame_equal(
        history_after,
        history_before,
    )

    with open(env["latest"], encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["date"] == "2026-03-02"
    assert payload["observations"] == 4

    # The derived time-series product is updated consistently.
    timeseries_df = pd.read_csv(env["timeseries"])

    assert len(timeseries_df) == 4

    # The expected plots are regenerated as readable PNGs.
    actual_plots = sorted(
        path.relative_to(env["plots_dir"]).as_posix()
        for path in env["plots_dir"].rglob("*.png")
    )

    assert actual_plots == _EXPECTED_PLOTS

    for path in env["plots_dir"].rglob("*.png"):
        _assert_png_product(path)

    # No yearly/threshold products exist for the two-day dataset
    # (complete region-years are required, see F-031).
    assert not (env["plots_dir"] / "yearly_timeseries").exists()

    # The generated website reflects the updated results.
    assert (env["build_dir"] / "index.html").exists()

    with open(
        env["build_dir"] / "output" / "analysis" / "latest.json",
        encoding="utf-8",
    ) as file:
        built_payload = json.load(file)

    assert built_payload["date"] == "2026-03-02"

    built_csv = pd.read_csv(
        env["build_dir"]
        / "output"
        / "analysis"
        / "ice_coverage_summary.csv",
    )

    assert len(built_csv) == 4

    # The temporary-data cleanup ran (tied to the download).
    assert env["downloader"].delete_calls == 1
