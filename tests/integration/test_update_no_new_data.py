"""Integration tests for the update pipeline's no-new-data
behavior (issue #31).

The tests verify the explicitly documented behavior of the
incremental update pipeline (src/update/update_pipeline.py,
docs/testing/test-levels.md, section 4.6) when no new
observations are available: the existing results state already
covers every observation the data source offers.

Controlled state:

* both available observations (2026-03-01 and 2026-03-02) are
  already processed and persisted (summary CSV + latest.json),
* the remote archive offers exactly these two observations,
* existing plots and an existing website build state are seeded
  as sentinel files.

Because the latest processed observation is 2026-03-02, the
pipeline must start its sync at 2026-03-03 -- a day no
observation exists for. The download stage therefore reports
zero downloads and the pipeline terminates after the sync stage
(the no-new-data condition).

Covered behavior (issue #31 tasks):

* the pipeline recognizes the no-new-data condition and
  terminates successfully after the sync stage,
* no new analysis results are created (results and latest.json
  remain byte-identical),
* no unnecessary downstream processing occurs (no processing,
  plots, website build, or cleanup stage runs),
* existing plots and the website build state remain unchanged,
* and a local archive left over from a --keep-data run is not
  touched by the no-op run (the cleanup stage only runs for a
  completed update with downloads).

Difference to the issue #30 tests
(tests/integration/test_update_pipeline.py):

* issue #30 configures the downloader summary directly
  (``downloaded_files = 0``) to force the early exit; issue #31
  derives the condition from the state: the fake downloader
  computes the downloads from its fixed remote archive and the
  requested start date, so the no-new-data condition follows
  from "all available observations are already processed",
* issue #31 additionally verifies at file level that the
  existing plots and the website build state remain
  byte-identical.

Test design:

* The pipeline wires all collaborators with hard-coded
  production defaults (see tests/Findings.md, F-015), so the
  collaborators are replaced in the
  ``src.update.update_pipeline`` namespace as in
  test_update_pipeline.py: the real ResultsManager on isolated
  paths, a fake downloader modeling the remote archive, the
  controlled process stage with the real CLI parser and the
  real RegionAnalyzer, a recording plots stage (plot generation
  belongs to the visualization milestone), and the real
  build_pages against isolated directories.
* The persisted rows use the same hand-calculated values as
  the spatial chain integration tests:

    2026-03-01, Test Region Water (2500 km² water area):
      values 400, 600, 100, 0 -> 2 ice pixels
      -> absolute 2 * 625 = 1250 km²,
         weighted (400 + 600) / 1000 * 625 = 625 km²,
         coverage 1250 / 2500 = 50 % / 625 / 2500 = 25 %.
    2026-03-01, Test Region Mixed (625 km² water area):
      value 800 -> 1 ice pixel
      -> 625 km² / (800 / 1000) * 625 = 500 km² / 100 % / 80 %.
    2026-03-02, Test Region Water (2500 km² water area):
      values 150, 1000, 0, 200 -> 3 ice pixels
      -> absolute 3 * 625 = 1875 km²,
         weighted (150 + 1000 + 200) / 1000 * 625 = 843.75 km²,
         coverage 1875 / 2500 = 75 % / 843.75 / 2500 = 33.75 %.
    2026-03-02, Test Region Mixed (625 km² water area):
      value 0 -> no ice -> 0 km² / 0 km² / 0 % / 0 %.

* All tests are deterministic and require no network access.
"""

from __future__ import annotations

import functools
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

import src.analysis.process_data as process_data_module
import src.update.build_pages as build_pages_module
import src.update.update_pipeline as update_pipeline_module
from src.analysis.region_analyzer import RegionAnalyzer
from src.analysis.results_manager import ResultsManager
from src.data_download.downloader import DownloadSummary


# Persisted rows expected for the two already processed
# observations (hand calculation, identical to the spatial
# chain integration tests; see also the module header):

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


# ------------------------------------------------------------------
# Controlled collaborators
# ------------------------------------------------------------------

class _ArchiveDownloader:
    """Controlled NSIDCDownloader replacement.

    Models a fixed remote archive: ``sync(start_date=...)``
    reports the available observations from ``start_date``
    onwards as downloads. Together with the seeded results state
    this makes the no-new-data condition follow from the state
    instead of a configured summary. ``sync`` and
    ``delete_local_data`` record their invocations.
    """

    def __init__(
        self,
        events: list[str],
        available_dates: list[date],
    ) -> None:
        self.events = events
        self.available_dates = sorted(available_dates)
        self.sync_calls: list[dict] = []
        self.sync_summaries: list[DownloadSummary] = []
        self.delete_calls = 0

    def sync(self, **kwargs) -> DownloadSummary:
        self.events.append("sync")
        self.sync_calls.append(kwargs)

        start_date = kwargs["start_date"]
        new_dates = [
            obs_date
            for obs_date in self.available_dates
            if obs_date >= start_date
        ]

        summary = DownloadSummary(
            checked_files=len(self.available_dates),
            downloaded_files=len(new_dates),
        )
        self.sync_summaries.append(summary)

        return summary

    def delete_local_data(self) -> None:
        self.events.append("delete")
        self.delete_calls += 1


def _process_observations(
    args,
    data_dir: Path,
    csv_path: Path,
    latest_json_path: Path,
    reference_json: Path,
    filter_dir: Path,
) -> process_data_module.ProcessSummary:
    """Controlled implementation of the process-stage contract.

    Follows src/analysis/process_data.main(): the same CLI
    arguments are parsed (real parser), only GeoTIFFs from
    --start-date onwards are processed, already persisted dates
    are skipped, and new results are persisted with the real
    ResultsManager. The raster analysis runs through the real
    RegionAnalyzer on the controlled reference products.

    In the issue #31 scenarios this stage must never be reached;
    it is provided with the same contract as in
    test_update_pipeline.py so that a changed pipeline fails on
    the stage-order assertion instead of with a confusing error.
    """
    summary = process_data_module.ProcessSummary()

    manager = ResultsManager(
        csv_path=csv_path,
        latest_json_path=latest_json_path,
    )

    for tif in sorted(data_dir.rglob("*concentration*.tif")):
        analyzer = RegionAnalyzer(
            input_tif=tif,
            reference_json=reference_json,
            filter_dir=filter_dir,
        )
        analyzer._extract_date()

        if args.start_date is not None and analyzer.date < args.start_date:
            continue

        if manager.is_date_processed(analyzer.date):
            summary.skipped_files += 1
            continue

        manager.add_results(analyzer.analyze())

        summary.processed_files += 1
        summary.new_results += 1

    manager.save()

    return summary


# ------------------------------------------------------------------
# Controlled inputs
# ------------------------------------------------------------------

def _write_observation(
    directory: Path,
    filename: str,
    values: dict[int, int],
) -> Path:
    """Write a controlled daily observation GeoTIFF.

    The raster matches the geometry of the synthetic reference
    products (5 x 5 pixels, EPSG:3411, 25 km pixels). ``values``
    maps flat pixel indices to concentration values on the 0-1000
    scale; all other pixels carry the land code 2510.
    """
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
    return (
        dict(
            zip(
                expected_reference_masks["Test Region Water"],
                water_values,
            )
        )
        | dict(
            zip(
                expected_reference_masks["Test Region Mixed"],
                mixed_values,
            )
        )
    )


def _results_for(
    obs_date: date,
    rows: list[dict],
) -> dict[str, dict]:
    """Build the ResultsManager input for one observation.

    Maps each expected row to the add_results contract (region
    name -> result record) with the observation date as a
    datetime.date (the ResultsManager normalizes it on save).
    """
    return {
        row["region"]: {**row, "date": obs_date}
        for row in rows
    }


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
# Fixture: a state where all available observations are already
# processed
# ------------------------------------------------------------------

@pytest.fixture
def no_new_data_environment(
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    expected_reference_masks: dict[str, np.ndarray],
) -> dict:
    """Isolate the update pipeline in a fully processed state.

    Provides:

    * controlled reference products (water masks + summary),
    * a fully processed existing-results state: the observations
      2026-03-01 and 2026-03-02 are persisted (summary CSV +
      latest.json), and the remote archive offers exactly these
      two observations,
    * sentinel files for the existing plots and the existing
      website build state,
    * and namespace replacements for the pipeline collaborators
      in src/update/update_pipeline.py.
    """
    data_dir = test_environment["data"]
    output_dir = test_environment["output"]
    analysis_dir = output_dir / "analysis"
    reference_dir = output_dir / "reference"
    filter_dir = reference_dir / "filters"
    plots_dir = output_dir / "plots"
    docs_dir = test_environment["root"] / "docs"
    build_dir = test_environment["build"]

    data_dir.mkdir(parents=True, exist_ok=True)

    # Controlled reference products (the complete existing state
    # of a configured project).
    filter_dir.mkdir(parents=True)
    for region, indices in expected_reference_masks.items():
        np.save(filter_dir / f"{region}_water.npy", indices)

    reference_json = reference_dir / "reference_summary.json"
    reference_json.write_text(
        json.dumps(
            {
                region: {
                    "water_pixels": len(indices),
                    "water_area_pixel_km2": len(indices) * 625.0,
                }
                for region, indices in expected_reference_masks.items()
            },
            indent=4,
        ),
        encoding="utf-8",
    )

    # Controlled website source.
    docs_dir.mkdir(parents=True)
    (docs_dir / "index.html").write_text(
        "<html><body>site</body></html>",
        encoding="utf-8",
    )

    # Fully processed existing-results state: both available
    # observations are persisted.
    csv_path = analysis_dir / "ice_coverage_summary.csv"
    latest_json_path = analysis_dir / "latest.json"
    manager = ResultsManager(
        csv_path=csv_path,
        latest_json_path=latest_json_path,
    )
    manager.add_results(
        _results_for(date(2026, 3, 1), [_DAY_1_WATER, _DAY_1_MIXED]),
    )
    manager.add_results(
        _results_for(date(2026, 3, 2), [_DAY_2_WATER, _DAY_2_MIXED]),
    )
    manager.save()

    # Existing plots (sentinel files; the plots stage is
    # recorded, so the sentinels model the products of the last
    # completed update).
    plots_dir.mkdir()
    (plots_dir / "timeseries.png").write_bytes(
        b"existing plot: timeseries\n",
    )
    (plots_dir / "yearly_overview.png").write_bytes(
        b"existing plot: yearly overview\n",
    )

    # Existing website build state (a plausible result of the
    # last completed update).
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "index.html").write_text(
        "<html><body>built site</body></html>",
        encoding="utf-8",
    )
    built_analysis_dir = build_dir / "output" / "analysis"
    built_analysis_dir.mkdir(parents=True)
    (built_analysis_dir / "ice_coverage_summary.csv").write_bytes(
        csv_path.read_bytes(),
    )
    (built_analysis_dir / "latest.json").write_bytes(
        latest_json_path.read_bytes(),
    )

    # Collaborator replacements.
    events: list[str] = []
    plots_calls: list[list] = []
    process_args: list = []
    process_summaries: list[process_data_module.ProcessSummary] = []

    downloader = _ArchiveDownloader(
        events,
        available_dates=[date(2026, 3, 1), date(2026, 3, 2)],
    )
    monkeypatch.setattr(
        update_pipeline_module,
        "NSIDCDownloader",
        lambda: downloader,
    )
    monkeypatch.setattr(
        update_pipeline_module,
        "ResultsManager",
        functools.partial(
            ResultsManager,
            csv_path=csv_path,
            latest_json_path=latest_json_path,
        ),
    )

    def process_stage(argv):
        events.append("process")
        args = process_data_module.parse_args(argv)
        process_args.append(args)
        summary = _process_observations(
            args,
            data_dir=data_dir,
            csv_path=csv_path,
            latest_json_path=latest_json_path,
            reference_json=reference_json,
            filter_dir=filter_dir,
        )
        process_summaries.append(summary)
        return summary

    monkeypatch.setattr(
        update_pipeline_module,
        "process_data",
        process_stage,
    )

    def plots_stage(argv):
        events.append("plots")
        plots_calls.append(list(argv))

    monkeypatch.setattr(
        update_pipeline_module,
        "generate_plots",
        plots_stage,
    )

    # Real build stage against isolated directories (must not
    # run; if it did, it would wipe the seeded build state).
    monkeypatch.setattr(build_pages_module, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(build_pages_module, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(build_pages_module, "BUILD_DIR", build_dir)

    def build_stage(argv):
        events.append("build")
        build_pages_module.main(argv)

    monkeypatch.setattr(
        update_pipeline_module,
        "build_pages",
        build_stage,
    )

    return {
        "data_dir": data_dir,
        "csv": csv_path,
        "latest": latest_json_path,
        "plots_dir": plots_dir,
        "build_dir": build_dir,
        "downloader": downloader,
        "events": events,
        "plots_calls": plots_calls,
        "process_args": process_args,
        "process_summaries": process_summaries,
        "log_file": test_environment["root"] / "update.log",
    }


# ------------------------------------------------------------------
# Task: run the update pipeline and verify no unnecessary
# downstream processing occurs
# ------------------------------------------------------------------

def test_no_new_data_stops_after_sync(
    no_new_data_environment: dict,
) -> None:
    """A fully processed state terminates after the sync stage.

    Both available observations (2026-03-01, 2026-03-02) are
    already processed and the local data directory is empty (the
    GeoTIFFs were cleaned up by the previous run).

    Expected behavior:

    * the sync starts at 2026-03-03 (the day after the latest
      processed observation) and reports zero downloads, because
      the source offers no observation from that day onwards,
    * the pipeline recognizes the no-new-data condition and
      terminates successfully after the sync stage,
    * no processing, plotting, website build, or cleanup stage
      runs.
    """
    env = no_new_data_environment

    update_pipeline_module.main(
        ["--log-file", str(env["log_file"])],
    )

    # The no-new-data condition: everything the source offers is
    # older than the day after the latest processed observation.
    assert env["downloader"].sync_calls == [
        {"start_date": date(2026, 3, 3)},
    ]
    assert env["downloader"].sync_summaries[0].downloaded_files == 0

    # The pipeline terminated after the sync stage.
    assert env["events"] == ["sync"]

    # No unnecessary downstream processing.
    assert env["process_args"] == []
    assert env["plots_calls"] == []

    # No cleanup: nothing was downloaded, nothing to remove.
    assert env["downloader"].delete_calls == 0
    assert list(env["data_dir"].rglob("*.tif")) == []


# ------------------------------------------------------------------
# Task: verify no new analysis results are created
# ------------------------------------------------------------------

def test_no_new_data_leaves_analysis_results_unchanged(
    no_new_data_environment: dict,
) -> None:
    """The no-op run does not touch the analysis results.

    The summary CSV and latest.json must remain byte-identical
    (no rewrite, no regenerated timestamp), and the persisted
    rows still hold the hand-calculated values of the two
    processed observations.
    """
    env = no_new_data_environment

    analysis_before = _snapshot_tree(env["csv"].parent)

    update_pipeline_module.main(
        ["--log-file", str(env["log_file"])],
    )

    # Byte-identical: no file was rewritten, no file was added.
    assert _snapshot_tree(env["csv"].parent) == analysis_before

    # The persisted rows are the two processed observations.
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

    with open(env["latest"], encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["date"] == "2026-03-02"
    assert payload["observations"] == 4


# ------------------------------------------------------------------
# Task: verify existing plots and the website/build state
# remain unchanged
# ------------------------------------------------------------------

def test_no_new_data_leaves_plots_and_build_unchanged(
    no_new_data_environment: dict,
) -> None:
    """Existing plots and the build state stay byte-identical.

    The controlled environment contains sentinel plot files and
    a seeded website build state. Neither the inventory nor the
    content of either directory may change: the plots stage must
    not run, and the real build stage would have wiped the build
    directory (rmtree) if it had been invoked erroneously.
    """
    env = no_new_data_environment

    plots_before = _snapshot_tree(env["plots_dir"])
    build_before = _snapshot_tree(env["build_dir"])

    update_pipeline_module.main(
        ["--log-file", str(env["log_file"])],
    )

    # Stage evidence: no plots and no build ran.
    assert env["events"] == ["sync"]
    assert env["plots_calls"] == []

    # File-level evidence: inventory and content unchanged.
    assert _snapshot_tree(env["plots_dir"]) == plots_before
    assert _snapshot_tree(env["build_dir"]) == build_before


# ------------------------------------------------------------------
# Task: verify existing outputs remain unchanged (leftover local
# data from a --keep-data run)
# ------------------------------------------------------------------

def test_no_new_data_keeps_leftover_local_data(
    no_new_data_environment: dict,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Leftover local data from a --keep-data run is untouched.

    State: the local archive still contains the already
    processed observations 2026-03-01 and 2026-03-02 (e.g. from a
    previous --keep-data run).

    The no-op run neither reports them as downloads (the sync
    starts after the latest processed observation) nor removes
    them (the cleanup is tied to a completed update with
    downloads) -- pinned documented behavior of the early exit.
    """
    env = no_new_data_environment

    # Leftover local archive from a previous --keep-data run.
    _write_observation(
        env["data_dir"] / "geotiff" / "2026" / "03_Mar",
        "N_20260301_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[400, 600, 100, 0],
            mixed_values=[800],
        ),
    )
    _write_observation(
        env["data_dir"] / "geotiff" / "2026" / "03_Mar",
        "N_20260302_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[150, 1000, 0, 200],
            mixed_values=[0],
        ),
    )

    data_before = _snapshot_tree(env["data_dir"])

    update_pipeline_module.main(
        ["--log-file", str(env["log_file"])],
    )

    # Terminated after the sync stage, no cleanup ran.
    assert env["events"] == ["sync"]
    assert env["downloader"].delete_calls == 0

    # Inventory and content of the local archive unchanged.
    assert _snapshot_tree(env["data_dir"]) == data_before