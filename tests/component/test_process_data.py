"""Component tests for the process stage CLI (issue #73).

The tests verify the command line entry point in
src/analysis/process_data.py (tests/Findings.md, F-024):

* parsing of --start-date/--end-date,
* the processing loop extracted as ``process_geotiffs()``
  (issue #73): inclusive date-filter boundaries, the skip
  path via is_date_processed(), per-file exception counting
  into failed_files, and the ProcessSummary counters,
* and a complete main() run with injected collaborators.

Test design:

* The analyzer is replaced by a controlled implementation
  of the RegionAnalyzer contract (extract_date/analyze/
  results); the real ResultsManager persists to isolated
  temporary paths.

All tests are deterministic and require no network access.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from src.analysis.process_data import (
    ProcessSummary,
    main,
    parse_args,
    process_geotiffs,
)
from src.analysis.results_manager import ResultsManager


def _row(observation_date: date) -> dict:
    """One controlled result row for the given date."""

    return {
        "region": "Test Region",
        "date": observation_date,
        "water_pixels": 1,
        "water_area_km2": 625.0,
        "absolute_ice_area_km2": 625.0,
        "relative_ice_area_km2": 500.0,
        "absolute_coverage_percent": 100.0,
        "relative_coverage_percent": 80.0,
        "missing_pixels": 0,
    }


class _FakeAnalyzer:
    """Controlled RegionAnalyzer replacement."""

    def __init__(
        self,
        observation_date: date,
        error: Exception | None = None,
    ) -> None:
        self.observation_date = observation_date
        self.error = error
        self.date = None
        self.results: dict = {}
        self.analyzed = False

    def extract_date(self) -> date | None:
        self.date = self.observation_date

        return self.date

    def analyze(self) -> dict:
        if self.error is not None:
            raise self.error

        self.analyzed = True

        self.results = {"Test Region": _row(self.date)}

        return self.results


def _analyzer_factory(analyzers: dict[Path, _FakeAnalyzer]):
    """Return a factory resolving analyzers by input path."""

    def factory(tif: Path) -> _FakeAnalyzer:
        return analyzers[tif]

    return factory


def _write_tif(directory: Path, name: str) -> Path:
    """Create an empty GeoTIFF placeholder file."""

    directory.mkdir(parents=True, exist_ok=True)

    path = directory / name
    path.touch()

    return path


def test_parse_args_date_filters() -> None:
    """--start-date/--end-date parse as ISO dates."""

    args = parse_args([])

    assert args.start_date is None
    assert args.end_date is None

    args = parse_args(
        [
            "--start-date",
            "2026-03-01",
            "--end-date",
            "2026-03-31",
        ]
    )

    assert args.start_date == date(2026, 3, 1)
    assert args.end_date == date(2026, 3, 31)


def test_process_geotiffs_processes_new_observations(
    tmp_path: Path,
) -> None:
    """New observations are analyzed and persisted once."""

    csv_path = tmp_path / "summary.csv"
    latest_json_path = tmp_path / "latest.json"
    results = ResultsManager(
        csv_path=csv_path,
        latest_json_path=latest_json_path,
    )
    summary = ProcessSummary()

    tif = tmp_path / "observation.tif"
    tif.touch()
    analyzer = _FakeAnalyzer(date(2026, 3, 2))

    process_geotiffs(
        [tif],
        results,
        summary,
        analyzer_factory=lambda path: analyzer,
    )

    assert summary.processed_files == 1
    assert summary.new_results == 1
    assert summary.skipped_files == 0
    assert summary.failed_files == 0
    assert analyzer.analyzed is True

    results.save()

    frame = pd.read_csv(csv_path)

    assert len(frame) == 1
    assert frame.iloc[0]["region"] == "Test Region"


def test_process_geotiffs_skips_processed_dates(
    tmp_path: Path,
) -> None:
    """Already persisted dates are skipped, not re-analyzed."""

    csv_path = tmp_path / "summary.csv"
    latest_json_path = tmp_path / "latest.json"

    seed = ResultsManager(
        csv_path=csv_path,
        latest_json_path=latest_json_path,
    )
    seed.add_results({"Test Region": _row(date(2026, 3, 1))})
    seed.save()

    results = ResultsManager(
        csv_path=csv_path,
        latest_json_path=latest_json_path,
    )
    summary = ProcessSummary()

    tif = tmp_path / "observation.tif"
    tif.touch()
    analyzer = _FakeAnalyzer(date(2026, 3, 1))

    process_geotiffs(
        [tif],
        results,
        summary,
        analyzer_factory=lambda path: analyzer,
    )

    assert summary.processed_files == 0
    assert summary.skipped_files == 1
    assert analyzer.analyzed is False


def test_process_geotiffs_respects_date_filter_boundaries(
    tmp_path: Path,
) -> None:
    """The --start-date/--end-date boundaries are inclusive."""

    results = ResultsManager(
        csv_path=tmp_path / "summary.csv",
        latest_json_path=tmp_path / "latest.json",
    )
    summary = ProcessSummary()

    tifs = [
        _write_tif(tmp_path, "observation_0.tif"),
        _write_tif(tmp_path, "observation_1.tif"),
        _write_tif(tmp_path, "observation_2.tif"),
        _write_tif(tmp_path, "observation_3.tif"),
    ]
    analyzers = {
        tifs[0]: _FakeAnalyzer(date(2026, 2, 28)),
        tifs[1]: _FakeAnalyzer(date(2026, 3, 1)),
        tifs[2]: _FakeAnalyzer(date(2026, 3, 31)),
        tifs[3]: _FakeAnalyzer(date(2026, 4, 1)),
    }

    process_geotiffs(
        tifs,
        results,
        summary,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        analyzer_factory=_analyzer_factory(analyzers),
    )

    assert summary.processed_files == 2
    assert summary.skipped_files == 0
    assert summary.failed_files == 0
    assert analyzers[tifs[0]].analyzed is False
    assert analyzers[tifs[1]].analyzed is True
    assert analyzers[tifs[2]].analyzed is True
    assert analyzers[tifs[3]].analyzed is False


def test_process_geotiffs_counts_failures(tmp_path: Path) -> None:
    """A failing observation is counted and does not stop the
    loop."""

    results = ResultsManager(
        csv_path=tmp_path / "summary.csv",
        latest_json_path=tmp_path / "latest.json",
    )
    summary = ProcessSummary()

    tifs = [
        _write_tif(tmp_path, "broken.tif"),
        _write_tif(tmp_path, "valid.tif"),
    ]
    analyzers = {
        tifs[0]: _FakeAnalyzer(
            date(2026, 3, 2),
            error=RuntimeError("broken raster"),
        ),
        tifs[1]: _FakeAnalyzer(date(2026, 3, 3)),
    }

    process_geotiffs(
        tifs,
        results,
        summary,
        analyzer_factory=_analyzer_factory(analyzers),
    )

    assert summary.processed_files == 1
    assert summary.failed_files == 1
    assert summary.skipped_files == 0


def test_main_runs_with_injected_dependencies(
    tmp_path: Path,
) -> None:
    """main() orchestrates the injected collaborators."""

    input_dir = tmp_path / "input"
    _write_tif(input_dir, "N_20260302_concentration_v1.0.tif")
    csv_path = tmp_path / "summary.csv"
    latest_json_path = tmp_path / "latest.json"

    events: list[str] = []

    class _FakeBuilder:
        def ensure_reference(self) -> None:
            events.append("reference")

    class _FakeTimeseries:
        def analyze(self) -> None:
            events.append("analyze")

        def save(self) -> None:
            events.append("save")

    analyzer = _FakeAnalyzer(date(2026, 3, 2))

    summary = main(
        ["--log-file", str(tmp_path / "process.log")],
        data_dir=input_dir,
        reference_builder=_FakeBuilder(),
        results=ResultsManager(
            csv_path=csv_path,
            latest_json_path=latest_json_path,
        ),
        analyzer_factory=lambda path: analyzer,
        timeseries=_FakeTimeseries(),
    )

    assert summary.processed_files == 1
    assert summary.new_results == 1
    assert events == ["reference", "analyze", "save"]

    frame = pd.read_csv(csv_path)

    assert len(frame) == 1
