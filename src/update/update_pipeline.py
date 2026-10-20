"""
Incremental update pipeline.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable, Sequence
from datetime import timedelta

from src.analysis.process_data import main as process_data
from src.analysis.results_manager import ResultsManager
from src.config.logging_config import add_log_arguments
from src.data_download.downloader import NSIDCDownloader
from src.update.build_pages import main as build_pages
from src.visualization.generate_plots import main as generate_plots

logger = logging.getLogger(__name__)

Stage = Callable[[Sequence[str] | None], object]
"""Signature of a stage invoked by the update pipeline."""

DownloaderFactory = Callable[[], NSIDCDownloader]
"""Constructor contract of the downloader (issue #106)."""

ResultsFactory = Callable[[], ResultsManager]
"""Constructor contract of the results manager (issue #106)."""


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the update-stage-specific options (CLI parity, #106).

    The module CLI and the dispatcher sub-parser share this
    specification, so both entry points expose the identical
    option set.
    """

    parser.add_argument(
        "--keep-data",
        action="store_true",
        help="Keep downloaded GeoTIFF files after processing.",
    )


def parse_args(argv: Sequence[str] | None = None):

    parser = argparse.ArgumentParser(
        description="Update the complete dataset."
    )

    add_log_arguments(parser)

    add_arguments(parser)

    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    results_factory: ResultsFactory = ResultsManager,
    downloader_factory: DownloaderFactory = NSIDCDownloader,
    process_stage: Stage = process_data,
    plots_stage: Stage = generate_plots,
    build_stage: Stage = build_pages,
):
    """Run the incremental update pipeline.

    Since issue #106 the collaborators are injectable keyword
    arguments with the production defaults (F-015); the
    orchestration behavior is unchanged.
    """

    args = parse_args(argv)

    results = results_factory()

    latest = results.get_latest_processed_date()

    start_date = None
    if latest is not None:
        start_date = latest + timedelta(days=1)

    downloader = downloader_factory()

    summary = downloader.sync(start_date=start_date)

    unprocessed_local = downloader.count_local_files_after(latest)

    if unprocessed_local:
        logger.info(
            "Found %s locally present but unprocessed "
            "observation file(s).",
            unprocessed_local,
        )

    if summary.downloaded_files == 0 and unprocessed_local == 0:
        logger.info("Dataset already up to date.")
        return

    process_argv = [
        "--log-level",
        args.log_level,
        "--log-file",
        args.log_file,
    ]

    if start_date is not None:
        process_argv += [
            "--start-date",
            start_date.isoformat(),
        ]

    process_summary = process_stage(process_argv)

    if process_summary.new_results == 0:
        logger.info("Dataset already up to date.")

        return

    logger.info("Generating plots.")

    plots_stage(
        [
            "all",
            "--log-level",
            args.log_level,
            "--log-file",
            args.log_file,
        ]
    )

    logger.info("Building GitHub Pages website.")

    build_stage(
        [
            "--log-level",
            args.log_level,
            "--log-file",
            args.log_file,
        ]
    )

    if not args.keep_data and summary.downloaded_files > 0:
        logger.info("Removing downloaded GeoTIFF files.")

        downloader.delete_local_data()

        logger.info("Temporary GeoTIFF files removed.")
