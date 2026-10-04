"""Command line entry point for preprocessing raw sea ice data."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.analysis.reference_builder import ReferenceBuilder
from src.analysis.region_analyzer import RegionAnalyzer
from src.analysis.results_manager import ResultsManager
from src.analysis.timeseries_analyzer import TimeSeriesAnalyzer
from src.config.logging_config import (
    DEFAULT_LOG_FILE,
    configure_logging,
)
from src.config.paths import DATA_DIR
from src.config.settings import DEFAULT_PRODUCT

logger = logging.getLogger(__name__)

AnalyzerFactory = Callable[[Path], RegionAnalyzer]
"""Constructor contract of the process stage (issue #73)."""


@dataclass(slots=True)
class ProcessSummary:
    processed_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    new_results: int = 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line options for the preprocessing stage."""

    parser = argparse.ArgumentParser(
        description="Preprocess raw sea ice data."
    )
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


def process_geotiffs(
    geotiffs: Sequence[Path],
    results: ResultsManager,
    summary: ProcessSummary,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    analyzer_factory: AnalyzerFactory = RegionAnalyzer,
) -> None:
    """Process GeoTIFF observations into results rows.

    Extracted from ``main()`` in issue #73 so the loop is
    testable with injected collaborators; the behavior is
    unchanged.
    """

    for tif in geotiffs:
        try:
            analyzer = analyzer_factory(tif)

            analyzer.extract_date()

            if start_date is not None and analyzer.date < start_date:
                continue

            if end_date is not None and analyzer.date > end_date:
                continue

            if results.is_date_processed(
                analyzer.date,
            ):
                summary.skipped_files += 1

                logger.info(
                    "Skipping %s",
                    analyzer.date,
                )

                continue

            analyzer.analyze()

            results.add_results(
                analyzer.results,
            )

            summary.processed_files += 1
            summary.new_results += 1

        except Exception as exc:
            summary.failed_files += 1

            logger.error(
                "Failed to process %s: %s",
                tif.name,
                exc,
            )


def main(
    argv: Sequence[str] | None = None,
    *,
    data_dir: Path = DATA_DIR,
    product: str = DEFAULT_PRODUCT,
    reference_builder: ReferenceBuilder | None = None,
    results: ResultsManager | None = None,
    analyzer_factory: AnalyzerFactory = RegionAnalyzer,
    timeseries: TimeSeriesAnalyzer | None = None,
) -> ProcessSummary:
    """Run the preprocessing stage from command line arguments.

    Since issue #73 the collaborators and paths are injectable
    keyword arguments with the previous production defaults;
    the pipeline behavior is unchanged.
    """

    args = parse_args(argv)

    configure_logging(
        level=args.log_level,
        log_file=args.log_file,
    )

    builder = (
        reference_builder
        if reference_builder is not None
        else ReferenceBuilder()
    )

    builder.ensure_reference()

    manager = results if results is not None else ResultsManager()

    summary = ProcessSummary()

    geotiffs = sorted(data_dir.rglob(f"*{product}*.tif"))

    process_geotiffs(
        geotiffs,
        manager,
        summary,
        start_date=args.start_date,
        end_date=args.end_date,
        analyzer_factory=analyzer_factory,
    )

    manager.save()

    logger.info("Running time series analysis.")

    ts = timeseries if timeseries is not None else TimeSeriesAnalyzer()

    ts.analyze()

    ts.save()

    logger.info(summary)

    return summary


if __name__ == "__main__":
    main()
