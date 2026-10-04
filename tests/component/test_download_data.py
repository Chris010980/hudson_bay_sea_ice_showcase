"""Component tests for the download stage CLI (issue #73).

The tests verify the command line entry point in
src/data_download/download_data.py (tests/Findings.md, F-023):

* parsing of every CLI flag (--base-url, --output-dir,
  --product, appendable --year/--month, --dry-run, logging),
* resolution of a relative --output-dir below the project
  root,
* and construction of the downloader from the parsed options
  through the ``downloader_factory`` seam introduced in
  issue #73.

Deliberately NOT asserted: the arguments of the sync() call.
The current wiring passes years/months, which the downloader
API does not accept (tests/Findings.md, F-009); the functional
correction is tracked separately and will add the contract
test.

All tests are deterministic and require no network access.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.paths import GEOTIFF_DIR
from src.config.settings import DEFAULT_PRODUCT
from src.data_download.download_data import main, parse_args
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
        """Record the sync call; kwargs not asserted (F-009)."""

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
