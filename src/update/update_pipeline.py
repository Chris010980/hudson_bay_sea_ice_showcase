"""
Incremental update pipeline.
"""

from __future__ import annotations

import argparse
import logging

from collections.abc import Sequence
from datetime import timedelta, date

from src.analysis.results_manager import ResultsManager
from src.data_download.downloader import NSIDCDownloader
from src.analysis.process_data import main as process_data
from src.visualization.generate_plots import main as generate_plots

logger = logging.getLogger(__name__)

def parse_args(argv: Sequence[str] | None = None):

    parser = argparse.ArgumentParser(
        description="Update the complete dataset."
    )

    parser.add_argument(
        "--keep-data",
        action="store_true",
    )

    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file")

    return parser.parse_args(argv)

def main(argv=None):

    args = parse_args(argv)

    results = ResultsManager()

    latest = results.get_latest_processed_date()

    start_date = None
    if latest is not None:
        start_date = latest + timedelta(days=1)

    downloader = NSIDCDownloader()

    downloader.sync(
        start_date=start_date,
    )

    process_data(
        [
            "--log-level",
            args.log_level,
            "--log-file",
            args.log_file,
            "--start-date",
            start_date.isoformat(),
        ]
    )

    logger.info("Generating plots.")

    generate_plots(
        [
            "all",
            "--log-level",
            args.log_level,
            "--log-file",
            args.log_file,
        ]
    )

    if not args.keep_data:

        logger.info("Removing downloaded GeoTIFF files.")

        NSIDCDownloader.delete_local_data()

        logger.info("Temporary GeoTIFF files removed.")