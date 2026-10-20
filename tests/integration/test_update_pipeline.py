"""Integration tests for the incremental update pipeline (issue
#30).

The tests verify the orchestration implemented by
src/update/update_pipeline.py (docs/testing/test-levels.md,
section 4.6):

    latest processed date + 1 day
          |
          v
    NSIDC download sync
          |
          v  (abort if nothing new is available)
    process new observations (--start-date)
          |
          v  (abort if no new results)
    regenerate plots
          |
          v
    rebuild website
          |
          v
    remove temporary GeoTIFFs (unless --keep-data)

Covered behavior:

* synchronization and processing start after the latest
  processed observation,
* a first run on an empty results state processes every
  locally available observation (issue #99, F-014),
* locally present but unprocessed observations are detected
  and processed even when the sync stage reports zero
  downloads (issue #101, F-016),
* only new observations are processed; existing results remain
  intact and new results are persisted,
* downstream stages run only after successful new observations
  (including the no-new-downloads and no-new-results early
  exits),
* the website build really consumes the updated results,
* and temporary data cleanup follows the configured behavior
  (default cleanup vs. --keep-data vs. early exit).

Test design:

* Since issue #106 the pipeline accepts its collaborators as
  injectable keyword arguments (F-015, resolved), so the
  controlled implementations of the same contracts are passed
  explicitly:
  - ResultsManager: the real class with isolated paths,
  - NSIDCDownloader: a fake that records sync/cleanup calls and
    returns a configurable summary,
  - process stage: a controlled implementation of the
    process_data contract -- it uses the real CLI parser, scans
    the isolated data directory, skips dates before --start-date
    and already persisted dates, runs the real RegionAnalyzer on
    the controlled reference products and persists with the real
    ResultsManager,
  - plots stage: recorded (real plot generation belongs to the
    visualization milestone),
  - build stage: the real build_pages against isolated
    directories.
* The controlled existing-results state is the processed
  observation 2026-03-01; the new observation 2026-03-02 uses the
  same hand-calculated values as
  tests/integration/test_spatial_processing_chain.py:

    Test Region Water (2500 km² water area):
      values 150, 1000, 0, 200 -> 3 ice pixels
      -> absolute 3 * 625 = 1875 km²,
         weighted (150+1000+200) / 1000 * 625 = 843.75 km²,
         coverage 1875 / 2500 = 75 % / 843.75 / 2500 = 33.75 %.
    Test Region Mixed (625 km² water area):
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
from src.data_download.downloader import (
    DownloadSummary,
    NSIDCDownloader,
)

# Persisted rows expected for the controlled observations
# (hand calculation, identical to the spatial chain integration
# tests; see also the module header):

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


class _FakeDownloader:
    """Controlled NSIDCDownloader replacement (records all calls).

    ``downloaded_files`` is configurable per test; ``sync`` and
    ``delete_local_data`` record their invocations.
    """

    def __init__(
        self,
        events: list[str],
        local_base: Path | None = None,
    ) -> None:
        self.events = events
        self.downloaded_files = 1
        self.sync_calls: list[dict] = []
        self.sync_summaries: list[DownloadSummary] = []
        self.delete_calls = 0
        self._local_files = (
            NSIDCDownloader(local_base=local_base)
            if local_base is not None
            else None
        )

    def sync(self, **kwargs) -> DownloadSummary:
        self.events.append("sync")
        self.sync_calls.append(kwargs)
        summary = DownloadSummary(
            checked_files=2,
            downloaded_files=self.downloaded_files,
        )
        self.sync_summaries.append(summary)
        return summary

    def count_local_files_after(self, start_date) -> int:
        """Delegate the local scan to the real downloader."""
        if self._local_files is None:
            return 0
        return self._local_files.count_local_files_after(start_date)

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

        if (
            args.start_date is not None
            and analyzer.date < args.start_date
        ):
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


def _day_1_results(obs_date: date) -> dict:
    """Results of the already processed observation (2026-03-01).

    Hand calculation (see the spatial chain integration tests):

    * Test Region Water (400, 600, 100, 0):
      2 ice pixels -> 1250 km² / 625 km² / 50 % / 25 %,
    * Test Region Mixed (800):
      1 ice pixel -> 625 km² / 500 km² / 100 % / 80 %.
    """
    return {
        "Test Region Water": {
            "region": "Test Region Water",
            "date": obs_date,
            "water_pixels": 4,
            "water_area_km2": 2500.0,
            "absolute_ice_area_km2": 1250.0,
            "relative_ice_area_km2": 625.0,
            "absolute_coverage_percent": 50.0,
            "relative_coverage_percent": 25.0,
            "missing_pixels": 0,
        },
        "Test Region Mixed": {
            "region": "Test Region Mixed",
            "date": obs_date,
            "water_pixels": 1,
            "water_area_km2": 625.0,
            "absolute_ice_area_km2": 625.0,
            "relative_ice_area_km2": 500.0,
            "absolute_coverage_percent": 100.0,
            "relative_coverage_percent": 80.0,
            "missing_pixels": 0,
        },
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


# ------------------------------------------------------------------
# Fixture: controlled existing-results state and collaborators
# ------------------------------------------------------------------


@pytest.fixture
def update_environment(
    test_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> dict:
    """Isolate the complete update pipeline.

    Provides:

    * controlled reference products (water masks + summary),
    * a controlled existing-results state: observation 2026-03-01
      is already persisted (summary CSV + latest.json),
    * a controlled website source directory,
    * and the controlled pipeline collaborators, injected
      explicitly since issue #106 (F-015 resolved).
    """
    data_dir = test_environment["data"]
    output_dir = test_environment["output"]
    analysis_dir = output_dir / "analysis"
    reference_dir = output_dir / "reference"
    filter_dir = reference_dir / "filters"
    html_dir = test_environment["root"] / "html"
    build_dir = test_environment["build"]

    # Controlled reference products (the build->analysis exchange
    # is covered by the spatial chain integration tests).
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
    html_dir.mkdir(parents=True)
    (html_dir / "index.html").write_text(
        "<html><body>site</body></html>",
        encoding="utf-8",
    )

    # Controlled existing-results state: 2026-03-01 processed.
    csv_path = analysis_dir / "ice_coverage_summary.csv"
    latest_json_path = analysis_dir / "latest.json"
    manager = ResultsManager(
        csv_path=csv_path,
        latest_json_path=latest_json_path,
    )
    manager.add_results(_day_1_results(date(2026, 3, 1)))
    manager.save()

    # Controlled collaborators (injected explicitly since
    # issue #106, F-015 resolved).
    events: list[str] = []
    plots_calls: list[list] = []
    process_args: list = []
    process_summaries: list[process_data_module.ProcessSummary] = []

    downloader = _FakeDownloader(
        events,
        data_dir / "geotiff",
    )

    results_factory = functools.partial(
        ResultsManager,
        csv_path=csv_path,
        latest_json_path=latest_json_path,
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

    def plots_stage(argv):
        events.append("plots")
        plots_calls.append(list(argv))

    # Real build stage against isolated directories (the
    # build directories are injectable since issue #106).
    def build_stage(argv):
        events.append("build")
        build_pages_module.main(
            argv,
            html_dir=html_dir,
            output_dir=output_dir,
            build_dir=build_dir,
        )

    return {
        "data_dir": data_dir,
        "csv": csv_path,
        "latest": latest_json_path,
        "reference_json": reference_json,
        "filter_dir": filter_dir,
        "build_dir": build_dir,
        "downloader": downloader,
        "events": events,
        "plots_calls": plots_calls,
        "process_args": process_args,
        "process_summaries": process_summaries,
        "results_factory": results_factory,
        "downloader_factory": lambda: downloader,
        "process_stage": process_stage,
        "plots_stage": plots_stage,
        "build_stage": build_stage,
        "log_file": test_environment["root"] / "update.log",
    }


def _write_update_observations(
    update_environment: dict,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Provide the new observation files for a full update run.

    * geotiff/2026/02_Feb/N_20260228_concentration_v1.0.tif
      -- older than the latest processed observation; must not be
      processed,
    * geotiff/2026/03_Mar/N_20260302_concentration_v1.0.tif
      -- the new observation that must be processed and persisted.
    """
    _write_observation(
        update_environment["data_dir"] / "geotiff" / "2026" / "02_Feb",
        "N_20260228_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[400, 600, 100, 0],
            mixed_values=[800],
        ),
    )
    _write_observation(
        update_environment["data_dir"] / "geotiff" / "2026" / "03_Mar",
        "N_20260302_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[150, 1000, 0, 200],
            mixed_values=[0],
        ),
    )


def _run_update(env: dict, argv: list[str] | None = None) -> None:
    """Run the pipeline with the injected collaborators (#106)."""

    update_pipeline_module.main(
        [
            *(argv or ()),
            "--log-file",
            str(env["log_file"]),
        ],
        results_factory=env["results_factory"],
        downloader_factory=env["downloader_factory"],
        process_stage=env["process_stage"],
        plots_stage=env["plots_stage"],
        build_stage=env["build_stage"],
    )


# ------------------------------------------------------------------
# Task: execute the update pipeline with new observations
# ------------------------------------------------------------------


def test_update_processes_only_new_observations(
    update_environment: dict,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """A full update run processes only the new observation.

    Existing state: 2026-03-01 is processed. Provided files:
    2026-02-28 (older, must be skipped) and 2026-03-02 (new).

    Expected behavior:

    * sync starts at 2026-03-02 (latest processed date + 1 day),
    * the process stage receives --start-date 2026-03-02,
    * the stages run in the order sync -> process -> plots ->
      build -> cleanup,
    * the existing rows remain intact and the 2026-03-02 results
      are persisted with the hand-calculated values (no
      2026-02-28 rows),
    * the real website build consumes the updated results,
    * and the downloaded GeoTIFFs are removed.
    """
    _write_update_observations(
        update_environment,
        expected_reference_masks,
    )

    _run_update(update_environment)

    env = update_environment

    # Processing starts after the latest processed observation.
    assert env["downloader"].sync_calls == [
        {"start_date": date(2026, 3, 2)},
    ]
    assert env["process_args"][0].start_date == date(2026, 3, 2)

    # Correct stage ordering.
    assert env["events"] == [
        "sync",
        "process",
        "plots",
        "build",
        "delete",
    ]

    # Results: existing rows intact, new rows persisted.
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

    # The pre-start-date observation was not processed.
    assert "2026-02-28" not in set(df["date"])

    with open(env["latest"], encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["date"] == "2026-03-02"
    assert payload["observations"] == 4

    # Downstream stages: plots requested for all products.
    assert env["plots_calls"][0][0] == "all"

    # The real website build regenerated the site with the
    # updated results.
    build_dir = env["build_dir"]

    assert (build_dir / "index.html").exists()
    assert (build_dir / "output" / "analysis" / "latest.json").exists()

    built_csv = pd.read_csv(
        build_dir / "output" / "analysis" / "ice_coverage_summary.csv",
    )
    assert len(built_csv) == 4

    # Temporary data cleanup happened.
    assert env["downloader"].delete_calls == 1


# ------------------------------------------------------------------
# Task: verify the no-new-data early exit
# ------------------------------------------------------------------


def test_update_without_downloads_stops_after_sync(
    update_environment: dict,
) -> None:
    """Without new downloads the pipeline stops after the sync.

    Nothing is processed, no derived products are regenerated,
    the temporary-data cleanup does not run, and the existing
    results remain untouched (docs/testing/test-levels.md,
    section 5.4).
    """
    env = update_environment
    env["downloader"].downloaded_files = 0

    _run_update(env)

    assert env["events"] == ["sync"]

    assert env["process_args"] == []
    assert env["plots_calls"] == []
    assert env["downloader"].delete_calls == 0

    # The build directory was not populated.
    assert list(env["build_dir"].iterdir()) == []

    # Existing results remain intact.
    df = pd.read_csv(env["csv"])

    assert len(df) == 2
    _assert_row(df, 0, _DAY_1_MIXED)
    _assert_row(df, 1, _DAY_1_WATER)


# ------------------------------------------------------------------
# Task: verify the no-new-results early exit
# ------------------------------------------------------------------


def test_update_without_new_results_stops_after_processing(
    update_environment: dict,
) -> None:
    """Downloads without new results stop before downstream stages.

    The download stage reports one downloaded file, but no
    processable observation exists, so the process stage returns
    ``new_results == 0``. The pipeline then terminates:

    * no plots and no website build run,
    * the existing results remain untouched,
    * and the configured behavior for this exit path is pinned:
      the pipeline returns before the temporary-data cleanup, so
      the downloaded files are not removed in this scenario.
    """
    env = update_environment

    _run_update(env)

    assert env["events"] == ["sync", "process"]

    assert env["process_summaries"][0].new_results == 0
    assert env["plots_calls"] == []
    assert list(env["build_dir"].iterdir()) == []

    # Configured behavior: early return skips the cleanup.
    assert env["downloader"].delete_calls == 0

    # Existing results remain intact.
    df = pd.read_csv(env["csv"])

    assert len(df) == 2
    _assert_row(df, 0, _DAY_1_MIXED)
    _assert_row(df, 1, _DAY_1_WATER)


# ------------------------------------------------------------------
# Task: verify temporary data cleanup follows the configuration
# ------------------------------------------------------------------


def test_update_keep_data_skips_cleanup(
    update_environment: dict,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """--keep-data keeps the downloaded GeoTIFF files.

    The full update runs as in the default case (processing,
    plots, website build, updated results), but the temporary
    data is not removed.
    """
    _write_update_observations(
        update_environment,
        expected_reference_masks,
    )

    _run_update(update_environment, ["--keep-data"])

    env = update_environment

    assert env["events"] == [
        "sync",
        "process",
        "plots",
        "build",
    ]

    # No cleanup with --keep-data.
    assert env["downloader"].delete_calls == 0

    # The update itself completed normally.
    df = pd.read_csv(env["csv"])

    assert len(df) == 4
    _assert_row(df, 0, _DAY_1_MIXED)
    _assert_row(df, 1, _DAY_1_WATER)
    _assert_row(df, 2, _DAY_2_MIXED)
    _assert_row(df, 3, _DAY_2_WATER)


# ------------------------------------------------------------------
# Task: verify the first run on an empty results state (F-014)
# ------------------------------------------------------------------


def test_update_first_run_processes_all_observations(
    update_environment: dict,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """A first run on an empty results state completes (F-014).

    The seeded results state is removed, so the pipeline finds
    no latest processed date (``start_date is None``). The
    crash path fixed in issue #99 passed ``--start-date
    None.isoformat()``; the pinned behavior instead requests
    the complete archive and processes every locally available
    observation:

    * sync runs without a start date,
    * the process stage receives no --start-date,
    * both provided observations (2026-02-28 and 2026-03-02)
      are processed and persisted,
    * the run completes through plots, build and cleanup.
    """

    env = update_environment

    # Empty results state: no summary CSV, no latest.json.
    env["csv"].unlink()
    env["latest"].unlink()

    _write_update_observations(env, expected_reference_masks)

    _run_update(env)

    # Full run: sync and process stage operate unbounded.
    assert env["downloader"].sync_calls == [{"start_date": None}]
    assert env["process_args"][0].start_date is None

    # The complete run through all stages.
    assert env["events"] == [
        "sync",
        "process",
        "plots",
        "build",
        "delete",
    ]

    # Every available observation was processed (no 02-28
    # pre-start-date filtering on the first run).
    df = pd.read_csv(env["csv"])

    assert len(df) == 4
    _assert_row(df, 0, dict(_DAY_1_MIXED, date="2026-02-28"))
    _assert_row(df, 1, dict(_DAY_1_WATER, date="2026-02-28"))
    _assert_row(df, 2, _DAY_2_MIXED)
    _assert_row(df, 3, _DAY_2_WATER)

    with open(env["latest"], encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["date"] == "2026-03-02"
    assert payload["observations"] == 4


# ------------------------------------------------------------------
# Task: verify locally present files are processed even without
# new downloads (F-016)
# ------------------------------------------------------------------


def test_update_processes_local_files_without_downloads(
    update_environment: dict,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Locally present files are processed despite zero
    downloads (F-016).

    The sync stage reports zero downloads because the new
    observation 2026-03-02 is already present locally (e.g.
    downloaded by an earlier run whose processing never
    happened). The processed state ends at 2026-03-01, so the
    pipeline must not report "no new data": the local file is
    unprocessed and must be processed now.

    Expected behavior:

    * the sync starts at 2026-03-02 and reports zero
      downloads,
    * the pipeline continues past the sync stage and passes
      --start-date 2026-03-02 to the process stage,
    * the previously masked 2026-03-02 results are persisted
      with the hand-calculated values and the plots and build
      stages run,
    * the cleanup does not run: it stays tied to downloads, so
      the local archive remains (the same leftover behavior
      pinned by the issue #31 tests).
    """
    env = update_environment

    # The masking state: the new observation is locally
    # present, so the sync stage has nothing to download.
    _write_update_observations(env, expected_reference_masks)
    env["downloader"].downloaded_files = 0

    _run_update(env)

    # The sync stage was satisfied by the local files.
    assert env["downloader"].sync_calls == [
        {"start_date": date(2026, 3, 2)},
    ]
    assert env["downloader"].sync_summaries[0].downloaded_files == 0

    # The pipeline continued past the sync stage.
    assert env["process_args"][0].start_date == date(2026, 3, 2)
    assert env["events"] == [
        "sync",
        "process",
        "plots",
        "build",
    ]

    # The previously masked observation is persisted.
    df = pd.read_csv(env["csv"])

    assert len(df) == 4
    _assert_row(df, 0, _DAY_1_MIXED)
    _assert_row(df, 1, _DAY_1_WATER)
    _assert_row(df, 2, _DAY_2_MIXED)
    _assert_row(df, 3, _DAY_2_WATER)

    with open(env["latest"], encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["date"] == "2026-03-02"
    assert payload["observations"] == 4

    # Cleanup stays tied to downloads: the local files remain.
    assert env["downloader"].delete_calls == 0
