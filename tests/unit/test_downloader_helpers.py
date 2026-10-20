"""Unit tests for the pure NSIDCDownloader helpers (issue #97).

The helpers extracted from ``sync()`` in issue #40 are pure
functions of their arguments: the filename key, the year and
month range checks, and the missing-file comparison. They are
tested here at unit level per docs/testing/test-levels.md
section 2.2; the synchronization behavior built on them
remains pinned by the component suite
(``tests/component/test_nsidc_downloader.py``).

The downloader instance operates on in-memory values only; no
network request is made and no directory is created.

All tests are deterministic and require no network access.
"""

from __future__ import annotations

from datetime import date

from src.data_download.downloader import (
    DownloadSummary,
    NSIDCDownloader,
)


def _downloader() -> NSIDCDownloader:
    """Downloader instance without any filesystem effect."""

    return NSIDCDownloader(
        base_url="https://example.test/nsidc/",
        local_base="geotiff",
        product="concentration",
    )


def test_file_key_parses_nsidc_filename() -> None:
    """Date and product are extracted from a valid name."""

    key = NSIDCDownloader._file_key("N_20260301_concentration_v2.0.tif")

    assert key == ("20260301", "concentration")


def test_file_key_rejects_invalid_filenames() -> None:
    """Names without date, version or .tif suffix yield None."""

    for filename in (
        "README.txt",
        "N_20260301_concentration.tif",
        "N_20260301_concentration_v2.0.nc",
        "20260301_concentration_v2.0.tif",
    ):
        assert NSIDCDownloader._file_key(filename) is None


def test_year_in_range_respects_bounds() -> None:
    """Years inside the range pass; outside years do not."""

    downloader = _downloader()

    start = date(2025, 6, 1)
    end = date(2026, 3, 1)

    assert downloader._year_in_range(2025, start, end) is True
    assert downloader._year_in_range(2026, start, end) is True
    assert downloader._year_in_range(2024, start, end) is False
    assert downloader._year_in_range(2027, start, end) is False


def test_year_in_range_without_bounds() -> None:
    """Without bounds every year passes."""

    downloader = _downloader()

    assert downloader._year_in_range(1978, None, None) is True


def test_month_in_range_respects_same_year_bounds() -> None:
    """Months of the bound years are filtered by the bounds."""

    downloader = _downloader()

    start = date(2026, 2, 15)
    end = date(2026, 3, 1)

    assert downloader._month_in_range(2026, 1, start, end) is False
    assert downloader._month_in_range(2026, 2, start, end) is True
    assert downloader._month_in_range(2026, 3, start, end) is True
    assert downloader._month_in_range(2026, 4, start, end) is False


def test_month_in_range_ignores_other_years() -> None:
    """Only the bound years restrict the month."""

    downloader = _downloader()

    start = date(2026, 2, 15)
    end = date(2026, 3, 1)

    assert downloader._month_in_range(2025, 1, start, end) is True
    assert downloader._month_in_range(2027, 12, start, end) is True


def test_missing_files_reports_exact_matches() -> None:
    """Missing files and exact matches are reported."""

    downloader = _downloader()

    remote = [
        "N_20260101_concentration_v1.0.tif",
        "N_20260102_concentration_v1.0.tif",
    ]
    local = ["N_20260101_concentration_v1.0.tif"]

    missing, exact_matches = downloader._missing_files(
        remote,
        local,
    )

    assert missing == ["N_20260102_concentration_v1.0.tif"]
    assert exact_matches == 1


def test_missing_files_treats_equivalent_versions_as_present() -> None:
    """A local file of the same date and product counts."""

    downloader = _downloader()

    remote = ["N_20260101_concentration_v2.0.tif"]
    local = ["N_20260101_concentration_v1.0.tif"]

    missing, exact_matches = downloader._missing_files(
        remote,
        local,
    )

    assert missing == []
    assert exact_matches == 0


def test_missing_files_ignores_unparseable_local_names() -> None:
    """Local names without a file key never match."""

    downloader = _downloader()

    remote = ["N_20260101_concentration_v1.0.tif"]
    local = ["notes.txt"]

    missing, exact_matches = downloader._missing_files(
        remote,
        local,
    )

    assert missing == ["N_20260101_concentration_v1.0.tif"]
    assert exact_matches == 0


def test_download_summary_merge_sums_all_counters() -> None:
    """merge() adds the counters of both summaries."""

    merged = DownloadSummary(
        checked_files=1,
        downloaded_files=2,
        skipped_files=3,
        failed_files=4,
    ).merge(
        DownloadSummary(
            checked_files=5,
            downloaded_files=6,
            skipped_files=7,
            failed_files=8,
        )
    )

    assert merged == DownloadSummary(
        checked_files=6,
        downloaded_files=8,
        skipped_files=10,
        failed_files=12,
    )
