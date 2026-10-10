"""Unit tests for the download stage CLI (issues #73, #97).

The tests verify the command line entry point in
src/data_download/download_data.py (tests/Findings.md, F-023):

* parsing of every CLI flag (--base-url, --output-dir,
  --product, appendable --year/--month, --dry-run, logging),
* resolution of a relative --output-dir below the project
  root,
* and construction of the downloader from the parsed options
  through the ``downloader_factory`` seam introduced in
  issue #73.

Since the F-009 correction (issue #98, variant A) the sync()
call arguments are part of the contract: the CLI filters are
mapped to inclusive date ranges by ``build_sync_ranges()`` and
passed to sync() as start_date/end_date/dry_run.

All tests are deterministic and require no network access.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.config.paths import GEOTIFF_DIR
from src.config.settings import DEFAULT_PRODUCT
from src.data_download.download_data import (
    build_sync_ranges,
    main,
    parse_args,
)
from src.data_download.downloader import (
    DEFAULT_GEOTIFF_DIR,
    DEFAULT_NSIDC_GEOTIFF_URL,
    DownloadSummary,
)


class _RecordingStage:
    """Records the complete download stage wiring."""

    def __init__(self) -> None:
        self.construction: list[dict] = []
        self.sync_calls: list[dict] = []
        self.summary = DownloadSummary(
            checked_files=2,
            downloaded_files=1,
        )

    def factory(self, **kwargs) -> _RecordingDownloader:
        """Factory contract: record the construction options."""

        self.construction.append(kwargs)

        return _RecordingDownloader(self)


class _RecordingDownloader:
    """Controlled NSIDCDownloader replacement."""

    def __init__(self, stage: _RecordingStage) -> None:
        self.stage = stage

    def sync(self, **kwargs) -> DownloadSummary:
        """Record the sync call including its arguments."""

        self.stage.sync_calls.append(kwargs)

        return self.stage.summary


def test_parse_args_defaults() -> None:
    """All CLI flags parse with their documented defaults."""

    args = parse_args([])

    assert args.base_url == DEFAULT_NSIDC_GEOTIFF_URL
    assert args.output_dir == str(DEFAULT_GEOTIFF_DIR)
    assert args.product == DEFAULT_PRODUCT
    assert args.years is None
    assert args.months is None
    assert args.dry_run is False
    assert args.log_level == "INFO"


def test_parse_args_appends_year_and_month() -> None:
    """--year and --month are appendable filters."""

    args = parse_args(
        [
            "--year",
            "2024",
            "--year",
            "2025",
            "--month",
            "03",
            "--dry-run",
        ]
    )

    assert args.years == ["2024", "2025"]
    assert args.months == ["03"]
    assert args.dry_run is True


def test_main_builds_downloader_from_parsed_options(
    tmp_path: Path,
) -> None:
    """main() constructs the downloader and runs the sync."""

    stage = _RecordingStage()

    main(
        ["--log-file", str(tmp_path / "download.log")],
        downloader_factory=stage.factory,
    )

    assert stage.construction == [
        {
            "base_url": DEFAULT_NSIDC_GEOTIFF_URL,
            "local_base": DEFAULT_GEOTIFF_DIR,
            "product": DEFAULT_PRODUCT,
        }
    ]
    assert len(stage.sync_calls) == 1


def test_main_resolves_relative_output_dir(tmp_path: Path) -> None:
    """A relative --output-dir resolves below the project root."""

    stage = _RecordingStage()

    main(
        [
            "--output-dir",
            "data/geotiff",
            "--log-file",
            str(tmp_path / "download.log"),
        ],
        downloader_factory=stage.factory,
    )

    assert stage.construction[0]["local_base"] == GEOTIFF_DIR


def test_parse_args_rejects_unknown_option() -> None:
    """Unknown options are rejected with argparse's exit."""

    with pytest.raises(SystemExit):
        parse_args(["--no-such-option"])


def test_build_sync_ranges_without_filters_requests_full_archive() -> (
    None
):
    """Without filters the sync covers the complete archive."""

    assert build_sync_ranges(None, None) == [(None, None)]
    assert build_sync_ranges([], []) == [(None, None)]


def test_build_sync_ranges_maps_years_to_ranges() -> None:
    """Each selected year becomes one inclusive year range."""

    ranges = build_sync_ranges(["2026", "2024"], None)

    assert ranges == [
        (date(2024, 1, 1), date(2024, 12, 31)),
        (date(2026, 1, 1), date(2026, 12, 31)),
    ]


def test_build_sync_ranges_maps_years_and_months() -> None:
    """Year-month selections become month ranges.

    February 2024 is a leap year: the range end is the 29th.
    """

    ranges = build_sync_ranges(["2024"], ["3", "02", "3"])

    assert ranges == [
        (date(2024, 2, 1), date(2024, 2, 29)),
        (date(2024, 3, 1), date(2024, 3, 31)),
    ]


def test_build_sync_ranges_rejects_invalid_selections() -> None:
    """Invalid selections raise a descriptive ValueError."""

    with pytest.raises(ValueError, match="requires --year"):
        build_sync_ranges(None, ["03"])

    with pytest.raises(ValueError, match="Invalid --year"):
        build_sync_ranges(["20x6"], None)

    with pytest.raises(ValueError, match="Invalid --month"):
        build_sync_ranges(["2026"], ["Mar"])

    with pytest.raises(ValueError, match="between 1 and 12"):
        build_sync_ranges(["2026"], ["13"])


def test_parse_args_rejects_month_without_year() -> None:
    """--month without --year exits with argparse's error."""

    with pytest.raises(SystemExit):
        parse_args(["--month", "03"])


def test_main_passes_range_filters_to_sync(tmp_path: Path) -> None:
    """Year/month filters reach sync() as date range + dry_run."""

    stage = _RecordingStage()

    main(
        [
            "--year",
            "2024",
            "--month",
            "03",
            "--dry-run",
            "--log-file",
            str(tmp_path / "download.log"),
        ],
        downloader_factory=stage.factory,
    )

    assert stage.sync_calls == [
        {
            "start_date": date(2024, 3, 1),
            "end_date": date(2024, 3, 31),
            "dry_run": True,
        }
    ]


def test_main_without_filters_calls_unbounded_sync(
    tmp_path: Path,
) -> None:
    """Without filters sync() receives the complete archive."""

    stage = _RecordingStage()

    main(
        ["--log-file", str(tmp_path / "download.log")],
        downloader_factory=stage.factory,
    )

    assert stage.sync_calls == [
        {
            "start_date": None,
            "end_date": None,
            "dry_run": False,
        }
    ]


def test_main_runs_one_sync_per_selected_year(
    tmp_path: Path,
) -> None:
    """Non-contiguous years stay separate sync ranges."""

    stage = _RecordingStage()

    main(
        [
            "--year",
            "2024",
            "--year",
            "2026",
            "--log-file",
            str(tmp_path / "download.log"),
        ],
        downloader_factory=stage.factory,
    )

    assert stage.sync_calls == [
        {
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "dry_run": False,
        },
        {
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "dry_run": False,
        },
    ]
