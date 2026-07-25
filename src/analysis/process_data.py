"""Command line entry point for preprocessing raw sea ice data."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from datetime import date

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.config.logging_config import DEFAULT_LOG_FILE, configure_logging
from src.analysis.reference_builder import ReferenceBuilder

from src.analysis.reference_builder import ReferenceBuilder
from src.analysis.region_analyzer import RegionAnalyzer
from src.analysis.results_manager import ResultsManager

from src.config.paths import DATA_DIR

logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line options for the preprocessing stage."""

    parser = argparse.ArgumentParser(description="Preprocess raw sea ice data.")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="Only process GeoTIFFs from this date onwards.",
    )

    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="Only process GeoTIFFs up to this date.",
    )

    return parser.parse_args(argv)


def main(argv=None):

    args = parse_args(argv)

    configure_logging(
        level=args.log_level,
        log_file=args.log_file,
    )

    builder = ReferenceBuilder()

    builder.ensure_reference()

    results = ResultsManager()

    geotiffs = sorted(
        DATA_DIR.rglob("*concentration*.tif")
    )

    for tif in geotiffs:

        try:

            analyzer = RegionAnalyzer(tif)

            analyzer._extract_date()

            if (
                args.start_date is not None
                and analyzer.date < args.start_date
            ):
                continue

            if (
                args.end_date is not None
                and analyzer.date > args.end_date
            ):
                continue

            if results.is_date_processed(
                analyzer.date,
            ):

                logger.info(
                    "Skipping %s",
                    analyzer.date,
                )

                continue

            analyzer.analyze()

            results.add_results(
                analyzer.results,
            )

        except Exception as exc:

            logger.error(
                "Failed to process %s: %s",
                tif.name,
                exc,
            )

    results.save()

if __name__ == "__main__":
    main()
