"""Component tests for the NSIDCDownloader (issue #28).

The tests verify the raw-data download stage without requiring the
live NSIDC service, following docs/testing/test-levels.md
(section 3.6): network interactions are represented by controlled,
scripted responses.

Covered behavior:

* local-file discovery,
* remote year/month/file discovery from controlled index pages,
* basic download behavior (store new files, skip existing files),
* recognition of equivalent product versions,
* synchronization logic (missing-file detection, date-range
  filtering, dry run),
* download error handling,
* temporary-data cleanup.

Test design:

* All remote interaction runs against a scripted fake
  ``requests.Session`` injected through the constructor's
  ``session`` parameter; no test opens a network connection. The
  fake base URL uses the reserved ``.test`` domain as a second
  safety net.
* The controlled archive (see ``REMOTE_MONTH_FILES``) spans two
  years, three months and six concentration files. Index pages
  also contain links the downloader must ignore.
* Every downloaded file carries a deterministic payload derived
  from its filename, so file contents are asserted exactly.
* Expected synchronization summaries are calculated by hand in
  the test docstrings.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import requests

from src.data_download import downloader as downloader_module
from src.data_download.downloader import (
    DownloadSummary,
    NSIDCDownloader,
)


BASE_URL = "https://example.test/nsidc/"

# Controlled remote archive used by the discovery and
# synchronization tests: two years, three months, six
# concentration files.
REMOTE_MONTH_FILES: dict[str, dict[str, list[str]]] = {
    "2025": {
        "03_Mar": [
            "N_20250301_concentration_v1.0.tif",
            "N_20250302_concentration_v1.0.tif",
        ],
    },
    "2026": {
        "01_Jan": [
            "N_20260101_concentration_v1.0.tif",
            "N_20260102_concentration_v1.0.tif",
        ],
        "03_Mar": [
            "N_20260301_concentration_v1.0.tif",
            "N_20260302_concentration_v1.0.tif",
        ],
    },
}


# ------------------------------------------------------------------
# Helpers: scripted remote service
# ------------------------------------------------------------------

class _FakeResponse:
    """Minimal stand-in for a ``requests`` response object."""

    def __init__(
        self,
        status_code: int = 200,
        text: str = "",
        chunks: tuple[bytes, ...] = (),
    ) -> None:
        self.status_code = status_code
        self.text = text
        self._chunks = chunks

    def iter_content(self, chunk_size: int = 8192):
        """Return the scripted payload chunks."""
        return iter(self._chunks)

    def raise_for_status(self) -> None:
        """Mimic ``requests``: raise for non-OK status codes."""
        if self.status_code != requests.codes.ok:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class _FakeSession:
    """Scripted stand-in for ``requests.Session``.

    The downloader only uses ``session.get()``. Responses are
    keyed by the exact request URL; unknown URLs answer with HTTP
    404. All requested URLs are recorded so tests can verify
    which remote resources were actually fetched.
    """

    def __init__(
        self,
        responses: dict[str, _FakeResponse] | None = None,
    ) -> None:
        self.responses = dict(responses or {})
        self.requested_urls: list[str] = []

    def get(self, url: str, **kwargs) -> _FakeResponse:
        """Return the scripted response for ``url``."""
        self.requested_urls.append(url)
        return self.responses.get(url, _FakeResponse(status_code=404))


def _html(*hrefs: str) -> str:
    """Build a minimal HTML directory index containing the hrefs."""
    links = "".join(
        f'<a href="{href}">{href}</a>' for href in hrefs
    )
    return f"<html><body>{links}</body></html>"


def _index_url() -> str:
    """URL of the remote year directory index."""
    return BASE_URL


def _year_url(year: str) -> str:
    """URL of a remote year directory index."""
    return f"{BASE_URL}{year}/"


def _month_url(year: str, month: str) -> str:
    """URL of a remote month directory index."""
    return f"{BASE_URL}{year}/{month}/"


def _file_url(year: str, month: str, filename: str) -> str:
    """URL of a remote GeoTIFF file."""
    return f"{BASE_URL}{year}/{month}/{filename}"


def _expected_content(filename: str) -> bytes:
    """Deterministic expected content of a downloaded file."""
    return b"payload:" + filename.encode("ascii")


def _file_response(filename: str) -> _FakeResponse:
    """Scripted response delivering the payload in two chunks."""
    return _FakeResponse(
        chunks=(b"payload:", filename.encode("ascii")),
    )


def _remote_archive() -> dict[str, _FakeResponse]:
    """Script the complete controlled remote NSIDC archive.

    The archive mirrors ``REMOTE_MONTH_FILES``. The year index
    also contains README and parent-directory links; month indexes
    contain parent links, an HTML page and (in 2026/01_Jan) a
    file of another product ("extent") -- all of which the
    downloader must ignore.
    """
    responses: dict[str, _FakeResponse] = {
        _index_url(): _FakeResponse(
            text=_html("../", "README.txt", "2025/", "2026/"),
        ),
    }

    for year, months in REMOTE_MONTH_FILES.items():
        responses[_year_url(year)] = _FakeResponse(
            text=_html("../", *(f"{month}/" for month in months)),
        )

        for month, filenames in months.items():
            month_hrefs = ["../", "index.html", *filenames]
            if (year, month) == ("2026", "01_Jan"):
                month_hrefs.append("N_20260101_extent_v1.0.tif")
            responses[_month_url(year, month)] = _FakeResponse(
                text=_html(*month_hrefs),
            )

            for filename in filenames:
                responses[_file_url(year, month, filename)] = (
                    _file_response(filename)
                )

    return responses


# ------------------------------------------------------------------
# Helpers: local archive and downloader construction
# ------------------------------------------------------------------

def _local_base(test_environment: dict[str, Path]) -> Path:
    """Isolated local GeoTIFF base directory for a test."""
    return test_environment["data"] / "geotiff"


def _seed_local_file(
    local_base: Path,
    year: str,
    month: str,
    filename: str,
    content: bytes = b"local",
) -> None:
    """Store one file in the local archive tree."""
    directory = local_base / year / month
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_bytes(content)


def _make_downloader(
    local_base: Path,
    responses: dict[str, _FakeResponse] | None = None,
) -> tuple[NSIDCDownloader, _FakeSession]:
    """Create a downloader wired to a scripted fake session."""
    session = _FakeSession(responses)
    downloader = NSIDCDownloader(
        base_url=BASE_URL,
        local_base=local_base,
        product="concentration",
        session=session,
    )
    return downloader, session


# ------------------------------------------------------------------
# Task: test local-file discovery
# ------------------------------------------------------------------

def test_local_file_discovery(
    test_environment: dict[str, Path],
) -> None:
    """``get_local_files`` returns the matching local files.

    A missing local directory answers with an empty list. In an
    existing directory only ``.tif`` files whose names contain the
    configured product are returned, sorted by name. Files of
    other products, non-GeoTIFF files and subdirectories are
    ignored.
    """
    local_base = _local_base(test_environment)
    downloader, _ = _make_downloader(local_base)

    # Missing directory: no files, no exception.
    assert downloader.get_local_files("2026", "01_Jan") == []

    month_dir = local_base / "2026" / "01_Jan"
    month_dir.mkdir(parents=True)
    (month_dir / "N_20260102_concentration_v1.0.tif").write_bytes(b"b")
    (month_dir / "N_20260101_concentration_v1.0.tif").write_bytes(b"a")
    (month_dir / "N_20260101_extent_v1.0.tif").write_bytes(b"c")
    (month_dir / "notes.txt").write_bytes(b"d")
    (month_dir / "cache").mkdir()

    assert downloader.get_local_files("2026", "01_Jan") == [
        "N_20260101_concentration_v1.0.tif",
        "N_20260102_concentration_v1.0.tif",
    ]


# ------------------------------------------------------------------
# Task: test remote year/month/file discovery (controlled
# responses)
# ------------------------------------------------------------------

def test_remote_year_and_month_discovery(
    test_environment: dict[str, Path],
) -> None:
    """Year and month directories are parsed from index pages.

    Year links must be numeric after stripping the trailing
    slash; parent and README links are ignored. Month links must
    contain an underscore and end with a slash (NSIDC uses
    ``MM_Mon`` folders); year links inside a year index do not
    count as months.
    """
    responses = {
        _index_url(): _FakeResponse(
            text=_html("../", "README.txt", "2025/", "2026/"),
        ),
        _year_url("2025"): _FakeResponse(
            text=_html("../", "03_Mar/"),
        ),
        _year_url("2026"): _FakeResponse(
            text=_html("../", "2025/", "01_Jan/", "03_Mar/"),
        ),
    }
    downloader, session = _make_downloader(
        _local_base(test_environment),
        responses,
    )

    assert downloader.get_remote_years() == ["2025", "2026"]
    assert downloader.get_remote_months("2026") == ["01_Jan", "03_Mar"]
    assert downloader.get_remote_months("2025") == ["03_Mar"]

    assert session.requested_urls == [
        _index_url(),
        _year_url("2026"),
        _year_url("2025"),
    ]


def test_remote_file_discovery(
    test_environment: dict[str, Path],
) -> None:
    """Remote files are filtered by product and suffix, sorted.

    Only ``.tif`` links whose name contains the configured
    product ("concentration") are returned. Parent links, HTML
    pages and files of other products ("extent") are ignored.
    The unsorted input is returned in sorted order.
    """
    month_page = _html(
        "../",
        "index.html",
        "N_20260102_concentration_v1.0.tif",
        "N_20260101_concentration_v1.0.tif",
        "N_20260101_extent_v1.0.tif",
    )
    downloader, _ = _make_downloader(
        _local_base(test_environment),
        {_month_url("2026", "01_Jan"): _FakeResponse(text=month_page)},
    )

    assert downloader.get_remote_files("2026", "01_Jan") == [
        "N_20260101_concentration_v1.0.tif",
        "N_20260102_concentration_v1.0.tif",
    ]


# ------------------------------------------------------------------
# Basic download behavior
# ------------------------------------------------------------------

def test_download_file_saves_missing_and_skips_existing(
    test_environment: dict[str, Path],
) -> None:
    """``download_file`` stores missing files and never refetches.

    The scripted response delivers the payload in two chunks; the
    saved file must contain their exact concatenation. A second
    call for the same file returns True without a second remote
    request (acceptance criterion: existing local observations
    are not unnecessarily downloaded).
    """
    local_base = _local_base(test_environment)
    filename = "N_20260101_concentration_v1.0.tif"
    url = _file_url("2026", "01_Jan", filename)
    downloader, session = _make_downloader(
        local_base,
        {url: _FakeResponse(chunks=(b"HEADER", b"DATA"))},
    )

    assert downloader.download_file("2026", "01_Jan", filename) is True

    local_path = local_base / "2026" / "01_Jan" / filename
    assert local_path.read_bytes() == b"HEADERDATA"
    assert session.requested_urls == [url]

    # Second call: the file exists and is not fetched again.
    assert downloader.download_file("2026", "01_Jan", filename) is True
    assert session.requested_urls == [url]
    assert local_path.read_bytes() == b"HEADERDATA"


# ------------------------------------------------------------------
# Task: test equivalent local-file detection
# ------------------------------------------------------------------

def test_equivalent_local_file_is_not_downloaded_again(
    test_environment: dict[str, Path],
) -> None:
    """Equivalent product versions are matched by date and product.

    A locally stored v1.0 file makes a remote v2.0 file with the
    same date and product unnecessary: ``download_file`` returns
    True without a remote request and without creating a second
    file. A file of another product ("extent") with the same date
    is not equivalent and is fetched.
    """
    local_base = _local_base(test_environment)
    _seed_local_file(
        local_base,
        "2026",
        "03_Mar",
        "N_20260301_concentration_v1.0.tif",
    )

    concentration_v2 = "N_20260301_concentration_v2.0.tif"
    extent_v2 = "N_20260301_extent_v2.0.tif"
    responses = {
        _file_url("2026", "03_Mar", concentration_v2): _FakeResponse(
            chunks=(b"new-concentration",),
        ),
        _file_url("2026", "03_Mar", extent_v2): _FakeResponse(
            chunks=(b"new-extent",),
        ),
    }
    downloader, session = _make_downloader(local_base, responses)
    month_dir = local_base / "2026" / "03_Mar"

    # Same date + product, different version: skipped.
    assert (
        downloader.download_file("2026", "03_Mar", concentration_v2)
        is True
    )
    assert (
        _file_url("2026", "03_Mar", concentration_v2)
        not in session.requested_urls
    )
    assert sorted(path.name for path in month_dir.iterdir()) == [
        "N_20260301_concentration_v1.0.tif",
    ]

    # Same date, different product: not equivalent, downloaded.
    assert downloader.download_file("2026", "03_Mar", extent_v2) is True
    assert (month_dir / extent_v2).read_bytes() == b"new-extent"


# ------------------------------------------------------------------
# Task: test synchronization logic
# ------------------------------------------------------------------

def test_sync_downloads_missing_and_skips_present(
    test_environment: dict[str, Path],
) -> None:
    """``sync`` downloads missing files and skips present ones.

    Local seed:

    * 2026/01_Jan/N_20260101_concentration_v1.0.tif
      -- exact remote match -> skipped,
    * 2026/03_Mar/N_20260301_concentration_v3.0.tif
      -- same date + product as the remote v1.0 file -> skipped
      as an equivalent version.

    Expected summary over the six remote files:

    * checked    = 6 (2 + 2 + 2 per month),
    * skipped    = 2 (one exact match, one equivalent version),
    * downloaded = 6 - 2 = 4 (2 x 2025/03_Mar, 1 x 2026/01_Jan,
      1 x 2026/03_Mar),
    * failed     = 0.
    """
    local_base = _local_base(test_environment)
    _seed_local_file(
        local_base,
        "2026",
        "01_Jan",
        "N_20260101_concentration_v1.0.tif",
        content=b"seeded-v1",
    )
    _seed_local_file(
        local_base,
        "2026",
        "03_Mar",
        "N_20260301_concentration_v3.0.tif",
        content=b"seeded-v3",
    )
    downloader, session = _make_downloader(
        local_base,
        _remote_archive(),
    )

    summary = downloader.sync()

    assert summary == DownloadSummary(
        checked_files=6,
        downloaded_files=4,
        skipped_files=2,
        failed_files=0,
    )

    # The four missing files were stored with their exact payload.
    for year, month, filename in [
        ("2025", "03_Mar", "N_20250301_concentration_v1.0.tif"),
        ("2025", "03_Mar", "N_20250302_concentration_v1.0.tif"),
        ("2026", "01_Jan", "N_20260102_concentration_v1.0.tif"),
        ("2026", "03_Mar", "N_20260302_concentration_v1.0.tif"),
    ]:
        local_path = local_base / year / month / filename
        assert local_path.exists()
        assert local_path.read_bytes() == _expected_content(filename)

    # The equivalent version was not duplicated ...
    march_dir = local_base / "2026" / "03_Mar"
    assert sorted(path.name for path in march_dir.iterdir()) == [
        "N_20260301_concentration_v3.0.tif",
        "N_20260302_concentration_v1.0.tif",
    ]

    # ... and the seeded files were neither fetched nor modified.
    assert (
        local_base
        / "2026"
        / "01_Jan"
        / "N_20260101_concentration_v1.0.tif"
    ).read_bytes() == b"seeded-v1"
    assert (
        march_dir / "N_20260301_concentration_v3.0.tif"
    ).read_bytes() == b"seeded-v3"
    assert (
        _file_url("2026", "01_Jan", "N_20260101_concentration_v1.0.tif")
        not in session.requested_urls
    )
    assert (
        _file_url("2026", "03_Mar", "N_20260301_concentration_v1.0.tif")
        not in session.requested_urls
    )


def test_sync_respects_date_range(
    test_environment: dict[str, Path],
) -> None:
    """``sync`` filters years, months and files by date range.

    Range 2026-01-02 .. 2026-03-01 over an empty local archive:

    * year 2025 is skipped entirely (year < start year),
    * 2026/01_Jan: N_20260101 (2026-01-01) is before the start
      date and excluded; N_20260102 remains -> downloaded,
    * 2026/03_Mar: N_20260301 (2026-03-01) is on the end date and
      included; N_20260302 (2026-03-02) is after the end date and
      excluded.

    Expected summary: checked=2, downloaded=2, skipped=0,
    failed=0.
    """
    local_base = _local_base(test_environment)
    downloader, session = _make_downloader(
        local_base,
        _remote_archive(),
    )

    summary = downloader.sync(
        start_date=date(2026, 1, 2),
        end_date=date(2026, 3, 1),
    )

    assert summary == DownloadSummary(
        checked_files=2,
        downloaded_files=2,
        skipped_files=0,
        failed_files=0,
    )

    assert (
        local_base
        / "2026"
        / "01_Jan"
        / "N_20260102_concentration_v1.0.tif"
    ).exists()
    assert (
        local_base
        / "2026"
        / "03_Mar"
        / "N_20260301_concentration_v1.0.tif"
    ).exists()

    assert not (local_base / "2025").exists()
    assert not (
        local_base
        / "2026"
        / "01_Jan"
        / "N_20260101_concentration_v1.0.tif"
    ).exists()
    assert not (
        local_base
        / "2026"
        / "03_Mar"
        / "N_20260302_concentration_v1.0.tif"
    ).exists()

    # The filtered-out year directory was never listed.
    assert _year_url("2025") not in session.requested_urls


def test_sync_skips_months_outside_range(
    test_environment: dict[str, Path],
) -> None:
    """Months outside the date range are skipped before listing.

    Range 2026-03-02 .. 2026-03-10:

    * year 2025 is skipped (year filter),
    * month 01_Jan is skipped (month 1 < start month 3) before
      any of its files is fetched,
    * 2026/03_Mar: N_20260301 (2026-03-01) is before the start
      date and excluded; N_20260302 (2026-03-02) is on the start
      date and remains -> downloaded.

    Expected summary: checked=1, downloaded=1, skipped=0,
    failed=0.
    """
    local_base = _local_base(test_environment)
    downloader, session = _make_downloader(
        local_base,
        _remote_archive(),
    )

    summary = downloader.sync(
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 10),
    )

    assert summary == DownloadSummary(
        checked_files=1,
        downloaded_files=1,
        skipped_files=0,
        failed_files=0,
    )

    assert (
        local_base
        / "2026"
        / "03_Mar"
        / "N_20260302_concentration_v1.0.tif"
    ).exists()
    assert not (
        local_base
        / "2026"
        / "03_Mar"
        / "N_20260301_concentration_v1.0.tif"
    ).exists()

    # The excluded year and month directories were never listed.
    assert _year_url("2025") not in session.requested_urls
    assert _month_url("2026", "01_Jan") not in session.requested_urls


def test_sync_dry_run_downloads_nothing(
    test_environment: dict[str, Path],
) -> None:
    """A dry run compares remote and local files without writing.

    Dry run over the full archive with an empty local directory:
    every remote file is missing, but nothing is downloaded.

    Expected summary: checked=6, downloaded=0, skipped=0,
    failed=0. No GeoTIFF URL is requested and no local directory
    is created.
    """
    local_base = _local_base(test_environment)
    downloader, session = _make_downloader(
        local_base,
        _remote_archive(),
    )

    summary = downloader.sync(dry_run=True)

    assert summary == DownloadSummary(
        checked_files=6,
        downloaded_files=0,
        skipped_files=0,
        failed_files=0,
    )

    assert all(
        not url.endswith(".tif") for url in session.requested_urls
    )
    assert not local_base.exists()


# ------------------------------------------------------------------
# Task: test download error handling
# ------------------------------------------------------------------

def test_download_error_is_reported_and_leaves_no_file(
    test_environment: dict[str, Path],
) -> None:
    """Failed downloads are counted and leave no partial file.

    The remote file N_20260101_concentration_v1.0.tif answers
    with HTTP 500:

    * ``download_file`` returns False and stores nothing,
    * ``sync`` counts the file in ``failed_files`` and continues
      with the remaining files and months.

    Expected sync summary: checked=6, downloaded=5, skipped=0,
    failed=1 (the five remaining files are downloaded normally).
    """
    local_base = _local_base(test_environment)
    failing = "N_20260101_concentration_v1.0.tif"
    responses = _remote_archive()
    responses[_file_url("2026", "01_Jan", failing)] = _FakeResponse(
        status_code=500,
    )
    downloader, _ = _make_downloader(local_base, responses)

    assert (
        downloader.download_file("2026", "01_Jan", failing) is False
    )
    assert not (
        local_base / "2026" / "01_Jan" / failing
    ).exists()

    summary = downloader.sync()

    assert summary == DownloadSummary(
        checked_files=6,
        downloaded_files=5,
        skipped_files=0,
        failed_files=1,
    )

    # The failed file was not stored; synchronization continued.
    assert not (
        local_base / "2026" / "01_Jan" / failing
    ).exists()
    assert (
        local_base
        / "2026"
        / "01_Jan"
        / "N_20260102_concentration_v1.0.tif"
    ).exists()
    assert (
        local_base
        / "2025"
        / "03_Mar"
        / "N_20250301_concentration_v1.0.tif"
    ).exists()
    assert (
        local_base
        / "2026"
        / "03_Mar"
        / "N_20260301_concentration_v1.0.tif"
    ).exists()


# ------------------------------------------------------------------
# Task: test temporary data deletion
# ------------------------------------------------------------------

def test_delete_local_data(
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``delete_local_data`` removes only GeoTIFF files.

    All ``.tif`` files below ``data/geotiff`` are deleted. Other
    files survive, and directories that become empty are removed.
    The cleanup root is computed from the module-level ``DATA_DIR``
    instead of the instance configuration, so the test redirects
    that constant to the isolated test environment (never to the
    production ``data/`` directory); see tests/Findings.md
    (F-010).

    Seeded tree below the isolated ``data/geotiff``:

    * 2025/03_Mar/N_20250301_concentration_v1.0.tif -> removed
    * 2026/01_Jan/N_20260101_concentration_v1.0.tif -> removed
    * 2026/01_Jan/notes.txt                        -> survives
    """
    data_root = test_environment["data"]
    geotiff_root = data_root / "geotiff"
    _seed_local_file(
        geotiff_root,
        "2025",
        "03_Mar",
        "N_20250301_concentration_v1.0.tif",
    )
    _seed_local_file(
        geotiff_root,
        "2026",
        "01_Jan",
        "N_20260101_concentration_v1.0.tif",
    )
    (geotiff_root / "2026" / "01_Jan" / "notes.txt").write_bytes(
        b"notes",
    )

    monkeypatch.setattr(downloader_module, "DATA_DIR", data_root)

    NSIDCDownloader.delete_local_data()

    assert not (
        geotiff_root
        / "2025"
        / "03_Mar"
        / "N_20250301_concentration_v1.0.tif"
    ).exists()
    assert not (
        geotiff_root
        / "2026"
        / "01_Jan"
        / "N_20260101_concentration_v1.0.tif"
    ).exists()
    assert (geotiff_root / "2026" / "01_Jan" / "notes.txt").exists()

    # Empty directories are removed; the geotiff root remains.
    assert not (geotiff_root / "2025").exists()
    assert (geotiff_root / "2026" / "01_Jan").exists()
    assert geotiff_root.exists()

    # A second run without GeoTIFF data is a no-op.
    NSIDCDownloader.delete_local_data()
    assert (geotiff_root / "2026" / "01_Jan" / "notes.txt").exists()

    # A missing geotiff directory does not raise.
    monkeypatch.setattr(
        downloader_module,
        "DATA_DIR",
        test_environment["root"] / "missing-data",
    )
    NSIDCDownloader.delete_local_data()