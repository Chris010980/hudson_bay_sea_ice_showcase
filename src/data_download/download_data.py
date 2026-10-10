"""Command line entry point for raw NSIDC data downloads."""

from __future__ import annotations

import argparse
import calendar
import logging
import sys
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.config.logging_config import (
    DEFAULT_LOG_FILE,
    configure_logging,
)
from src.config.paths import resolve_project_path
from src.config.settings import DEFAULT_PRODUCT
from src.data_download.downloader import (
    DEFAULT_GEOTIFF_DIR,
    DEFAULT_NSIDC_GEOTIFF_URL,
    DownloadSummary,
    NSIDCDownloader,
)

logger = logging.getLogger(__name__)

DownloaderFactory = Callable[..., NSIDCDownloader]
"""Constructor contract of the download stage (issue #73)."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line options for the NSIDC download stage."""

    parser = argparse.ArgumentParser(
        description="Download raw NSIDC GeoTIFF data."
    )
    parser.add_argument("--base-url", default=DEFAULT_NSIDC_GEOTIFF_URL)
    parser.add_argument(
        "--output-dir", default=str(DEFAULT_GEOTIFF_DIR)
    )
    parser.add_argument("--product", default=DEFAULT_PRODUCT)
    parser.add_argument("--year", action="append", dest="years")
    parser.add_argument("--month", action="append", dest="months")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))

    args = parser.parse_args(argv)

    try:
        build_sync_ranges(args.years, args.months)
    except ValueError as exc:
        parser.error(str(exc))

    return args


def _parse_selected_numbers(
    values: Sequence[str],
    flag: str,
) -> list[int]:
    """Return the sorted unique numbers of a filter selection.

    Raises ValueError for non-numeric values so parse_args can
    reject them with argparse's error exit.
    """

    try:
        return sorted({int(value) for value in values})
    except ValueError as exc:
        raise ValueError(f"Invalid {flag} value: {exc}") from exc


def _year_ranges(
    year_numbers: Sequence[int],
) -> list[tuple[date, date]]:
    """One inclusive full-year range per selected year."""

    return [
        (
            date(year, 1, 1),
            date(year, 12, 31),
        )
        for year in year_numbers
    ]


def _year_month_ranges(
    year_numbers: Sequence[int],
    month_numbers: Sequence[int],
) -> list[tuple[date, date]]:
    """One inclusive month range per year-month combination."""

    if any(month < 1 or month > 12 for month in month_numbers):
        raise ValueError("--month values must be between 1 and 12.")

    return [
        (
            date(year, month, 1),
            date(year, month, calendar.monthrange(year, month)[1]),
        )
        for year in year_numbers
        for month in month_numbers
    ]


def build_sync_ranges(
    years: Sequence[str] | None,
    months: Sequence[str] | None,
) -> list[tuple[date | None, date | None]]:
    """Map --year/--month selections to sync() date ranges.

    Variant A of the F-009 correction (issue #98): the
    appendable CLI filters are translated into one inclusive
    ``start_date``/``end_date`` range per selected year (or
    per selected year-month combination) instead of extending
    the downloader API. Without filters the complete archive
    is requested as a single unbounded range.

    Raises ValueError for invalid selections so parse_args can
    reject them with argparse's error exit.
    """

    if not years:
        if months:
            raise ValueError("--month requires --year.")
        return [(None, None)]

    year_numbers = _parse_selected_numbers(years, "--year")

    if not months:
        return _year_ranges(year_numbers)

    month_numbers = _parse_selected_numbers(months, "--month")

    return _year_month_ranges(year_numbers, month_numbers)


def main(
    argv: Sequence[str] | None = None,
    *,
    downloader_factory: DownloaderFactory = NSIDCDownloader,
) -> None:
    """Run the raw-data download stage from command line arguments."""

    args = parse_args(argv)
    configure_logging(level=args.log_level, log_file=args.log_file)
    output_dir = resolve_project_path(args.output_dir)

    logger.info("Download output directory resolved to: %s", output_dir)

    downloader = downloader_factory(
        base_url=args.base_url,
        local_base=output_dir,
        product=args.product,
    )
    summary = DownloadSummary()

    for start_date, end_date in build_sync_ranges(
        args.years,
        args.months,
    ):
        summary = summary.merge(
            downloader.sync(
                start_date=start_date,
                end_date=end_date,
                dry_run=args.dry_run,
            )
        )

    logger.info(
        "Download stage complete: "
        "checked=%s, downloaded=%s, skipped=%s, failed=%s",
        summary.checked_files,
        summary.downloaded_files,
        summary.skipped_files,
        summary.failed_files,
    )


if __name__ == "__main__":
    main()
