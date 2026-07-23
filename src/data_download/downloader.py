"""Download raw NSIDC sea ice GeoTIFF files.

This module owns raw data acquisition only. It does not preprocess rasters,
calculate statistics, or create plots.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from datetime import date
import requests
from bs4 import BeautifulSoup

from src.config.paths import DATA_DIR


DEFAULT_NSIDC_GEOTIFF_URL = (
    "https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/geotiff"
)
DEFAULT_GEOTIFF_DIR = DATA_DIR / "geotiff"
GEOTIFF_FILENAME_PATTERN = re.compile(r"^N_(?P<date>\d{8})_(?P<product>.+?)_v.+\.tif$")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DownloadSummary:
    """Summary returned after a synchronization run."""

    checked_files: int = 0
    downloaded_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0

    def merge(self, other: "DownloadSummary") -> "DownloadSummary":
        """Return a new summary containing this summary plus another one."""

        return DownloadSummary(
            checked_files=self.checked_files + other.checked_files,
            downloaded_files=self.downloaded_files + other.downloaded_files,
            skipped_files=self.skipped_files + other.skipped_files,
            failed_files=self.failed_files + other.failed_files,
        )


class NSIDCDownloader:
    """Synchronize NOAA/NSIDC daily northern hemisphere GeoTIFF files."""

    def __init__(
        self,
        base_url: str = DEFAULT_NSIDC_GEOTIFF_URL,
        local_base: str | Path = DEFAULT_GEOTIFF_DIR,
        product: str = "concentration",
        timeout: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        """Create a downloader for one NSIDC GeoTIFF product.

        Args:
            base_url: Base URL of the NSIDC directory index.
            local_base: Local directory where year/month folders are stored.
            product: Product name fragment to match in remote filenames.
            timeout: Request timeout in seconds.
            session: Optional requests session for connection reuse or tests.
        """

        self.base_url = base_url.rstrip("/") + "/"
        self.local_base = Path(local_base).expanduser().resolve()
        self.product = product
        self.timeout = timeout
        self.session = session or requests.Session()
        logger.debug(
            "Initialized NSIDCDownloader with base_url=%s, local_base=%s, product=%s",
            self.base_url,
            self.local_base,
            self.product,
        )

    def get_remote_years(self) -> list[str]:
        """Return available year directories from the remote index."""

        soup = self._get_index(self.base_url)
        years = [
            href.strip("/")
            for href in self._iter_hrefs(soup)
            if href.strip("/").isdigit()
        ]
        logger.debug("Found %s remote year directories.", len(years))
        return sorted(years)

    def get_remote_months(self, year: str) -> list[str]:
        """Return available month directories for a year."""

        year_url = f"{self.base_url}{year}/"
        soup = self._get_index(year_url)
        months = [
            href.strip("/")
            for href in self._iter_hrefs(soup)
            if "_" in href and href.endswith("/")
        ]
        logger.debug("Found %s remote month directories for %s.", len(months), year)
        return sorted(months)

    def get_remote_files(self, year: str, month: str) -> list[str]:
        """Return matching GeoTIFF files for a year/month directory."""

        month_url = f"{self.base_url}{year}/{month}/"
        soup = self._get_index(month_url)
        files = [
            href
            for href in self._iter_hrefs(soup)
            if self.product in href and href.endswith(".tif")
        ]
        logger.debug("Found %s remote files for %s/%s.", len(files), year, month)
        return sorted(files)

    def get_local_files(self, year: str, month: str) -> list[str]:
        """Return matching local GeoTIFF files for a year/month directory."""

        local_dir = self.local_base / year / month
        logger.info("Checking local directory: %s", local_dir)
        if not local_dir.exists():
            logger.warning("Local directory does not exist yet: %s", local_dir)
            return []

        files = sorted(
            path.name
            for path in local_dir.iterdir()
            if path.is_file() and path.suffix == ".tif" and self.product in path.name
        )
        logger.info(
            "Found %s local %s file(s) in %s.",
            len(files),
            self.product,
            local_dir,
        )
        if files:
            logger.debug("First local file in %s: %s", local_dir, files[0])
        return files

    def download_file(self, year: str, month: str, filename: str) -> bool:
        """Download one file unless it already exists locally.

        Returns:
            ``True`` if the file is present after the call, including files
            that were skipped because they already existed. ``False`` signals
            that the remote request failed and no complete local file was saved.
        """

        remote_url = f"{self.base_url}{year}/{month}/{filename}"
        local_dir = self.local_base / year / month
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / filename
        if local_path.exists():
            logger.info("Skipping existing file %s", local_path)
            return True
        local_match = self._find_equivalent_local_file(local_dir, filename)
        if local_match is not None:
            logger.info(
                "Skipping %s because equivalent local file already exists: %s",
                filename,
                local_match,
            )
            return True

        logger.info("Downloading %s", remote_url)
        response = self.session.get(remote_url, stream=True, timeout=self.timeout)
        if response.status_code != requests.codes.ok:
            logger.warning(
                "Download failed with HTTP %s: %s",
                response.status_code,
                remote_url,
            )
            return False

        with local_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        logger.info("Saved %s", local_path)
        return True

    def sync(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        dry_run: bool = False,
    ) -> DownloadSummary:
        """
        Synchronize GeoTIFF files within a given date range.

        Parameters
        ----------
        start_date
            First day to consider. If None, the complete archive is checked.

        end_date
            Last day to consider. If None, all available files are checked.

        dry_run
            Only compare remote and local files without downloading.
        """

        summary = DownloadSummary()

        years = self.get_remote_years()

        logger.info(
            "Synchronizing GeoTIFF archive%s.",
            " (dry-run)" if dry_run else "",
        )

        for year in years:

            year_int = int(year)

            if (
                start_date is not None
                and year_int < start_date.year
            ):
                continue

            if (
                end_date is not None
                and year_int > end_date.year
            ):
                continue

            remote_months = self.get_remote_months(year)

            for month in remote_months:

                month_int = int(month.split("_")[0])

                if (
                    start_date is not None
                    and year_int == start_date.year
                    and month_int < start_date.month
                ):
                    continue

                if (
                    end_date is not None
                    and year_int == end_date.year
                    and month_int > end_date.month
                ):
                    continue

                logger.info(
                    "Checking %s/%s",
                    year,
                    month,
                )

                remote_files = self.get_remote_files(
                    year,
                    month,
                )

                # -----------------------------------------
                # Filter files by date
                # -----------------------------------------

                filtered_remote_files = []

                for filename in remote_files:

                    key = self._file_key(filename)

                    if key is None:
                        continue

                    file_date = date.fromisoformat(
                        f"{key[0][:4]}-{key[0][4:6]}-{key[0][6:]}"
                    )

                    if (
                        start_date is not None
                        and file_date < start_date
                    ):
                        continue

                    if (
                        end_date is not None
                        and file_date > end_date
                    ):
                        continue

                    filtered_remote_files.append(filename)

                remote_files = filtered_remote_files

                if not remote_files:
                    continue

                local_files = self.get_local_files(
                    year,
                    month,
                )
                local_file_set = set(local_files)
                local_file_keys = {
                    file_key
                    for filename in local_files
                    if (file_key := self._file_key(filename)) is not None
                }
                exact_matches = sum(1 for name in remote_files if name in local_file_set)
                missing_files = [
                    name
                    for name in remote_files
                    if name not in local_file_set and self._file_key(name) not in local_file_keys
                ]
                logger.info(
                    "%s/%s comparison: remote=%s, local=%s, exact_matches=%s, "
                    "missing=%s, skipped=%s.",
                    year,
                    month,
                    len(remote_files),
                    len(local_files),
                    exact_matches,
                    len(missing_files),
                    len(remote_files) - len(missing_files),
                )
                if len(remote_files) - len(missing_files) > exact_matches:
                    logger.info(
                        "%s/%s skipped %s file(s) by matching date and product "
                        "despite different versioned filenames.",
                        year,
                        month,
                        len(remote_files) - len(missing_files) - exact_matches,
                    )
                if remote_files:
                    logger.debug("First remote file for %s/%s: %s", year, month, remote_files[0])
                if missing_files:
                    logger.debug(
                        "First missing file for %s/%s: %s",
                        year,
                        month,
                        missing_files[0],
                    )

                if missing_files:
                    logger.info(
                        "%s/%s has %s missing file(s).",
                        year,
                        month,
                        len(missing_files),
                    )
                else:
                    logger.info("%s/%s is already up to date.", year, month)

                month_summary = DownloadSummary(
                    checked_files=len(remote_files),
                    skipped_files=len(remote_files) - len(missing_files),
                )

                if dry_run:
                    logger.debug(
                        "Dry run: would download %s file(s) for %s/%s.",
                        len(missing_files),
                        year,
                        month,
                    )
                    summary = summary.merge(month_summary)
                    continue

                downloaded = 0
                failed = 0
                for filename in missing_files:
                    if self.download_file(year, month, filename):
                        downloaded += 1
                    else:
                        failed += 1

                if failed:
                    logger.warning(
                        "%s/%s finished with %s failed download(s).",
                        year,
                        month,
                        failed,
                    )

                summary = summary.merge(
                    DownloadSummary(
                        checked_files=month_summary.checked_files,
                        downloaded_files=downloaded,
                        skipped_files=month_summary.skipped_files,
                        failed_files=failed,
                    )
                )

        logger.info("Download sync finished: %s", summary)
        return summary

    def _get_index(self, url: str) -> BeautifulSoup:
        """Fetch and parse one remote HTML directory index."""

        logger.debug("Fetching remote index: %s", url)
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    @staticmethod
    def _file_key(filename: str) -> tuple[str, str] | None:
        """Return a date/product key for a NSIDC GeoTIFF filename."""

        match = GEOTIFF_FILENAME_PATTERN.match(filename)
        if match is None:
            return None

        return match.group("date"), match.group("product")

    def _find_equivalent_local_file(
        self,
        local_dir: Path,
        filename: str,
    ) -> Path | None:
        """Return an existing local file with the same date and product."""

        file_key = self._file_key(filename)
        if file_key is None or not local_dir.exists():
            return None

        for local_path in sorted(local_dir.iterdir()):
            if (
                local_path.is_file()
                and local_path.suffix == ".tif"
                and self._file_key(local_path.name) == file_key
            ):
                return local_path

        return None

    @staticmethod
    def _iter_hrefs(soup: BeautifulSoup) -> list[str]:
        """Return all href values from links in a parsed HTML document."""

        return [
            href
            for link in soup.find_all("a")
            if (href := link.get("href"))
        ]
    
