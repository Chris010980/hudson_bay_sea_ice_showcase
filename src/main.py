"""Pipeline dispatcher for the Hudson Bay sea ice app."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.analysis.process_data import main as process_data
from src.config.logging_config import DEFAULT_LOG_FILE, configure_logging
from src.data_download.download_data import main as download_data
from src.visualization.generate_plots import main as generate_plots


logger = logging.getLogger(__name__)

STAGES = {
    "download": download_data,
    "process": process_data,
    "plots": generate_plots,
}


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared by all pipeline stages."""

    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level.",
    )

    parser.add_argument(
        "--log-file",
        default=str(DEFAULT_LOG_FILE),
        help="Path to the log file.",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line options."""

    parser = argparse.ArgumentParser(
        description="Hudson Bay Sea Ice processing pipeline."
    )

    subparsers = parser.add_subparsers(
        dest="stage",
        required=True,
        metavar="STAGE",
    )

    # -------------------------------------------------------------
    # download
    # -------------------------------------------------------------

    download_parser = subparsers.add_parser(
        "download",
        help="Download the latest NSIDC data.",
    )

    _add_common_arguments(download_parser)

    # -------------------------------------------------------------
    # process
    # -------------------------------------------------------------

    process_parser = subparsers.add_parser(
        "process",
        help="Process downloaded GeoTIFF files.",
    )

    _add_common_arguments(process_parser)

    # -------------------------------------------------------------
    # plots
    # -------------------------------------------------------------

    plots_parser = subparsers.add_parser(
        "plots",
        help="Generate overview plots.",
    )

    _add_common_arguments(plots_parser)

    plots_parser.add_argument(
        "--regions",
        action="store_true",
        help="Overlay analysis regions.",
    )

    plots_parser.add_argument(
        "--region",
        nargs="+",
        metavar="REGION",
        help="Generate plots only for the selected region(s).",
    )

    plots_parser.add_argument(
        "--all-regions",
        action="store_true",
        help="Generate one plot for every analysis region.",
    )

    plots_parser.add_argument(
        "--show",
        action="store_true",
        help="Display figures after saving.",
    )

    # -------------------------------------------------------------
    # all
    # -------------------------------------------------------------

    all_parser = subparsers.add_parser(
        "all",
        help="Run the complete processing pipeline.",
    )

    _add_common_arguments(all_parser)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the selected pipeline stage."""

    args = parse_args(argv)

    configure_logging(
        level=args.log_level,
        log_file=args.log_file,
    )

    if args.stage == "all":

        logger.info("Running complete pipeline.")

        download_data(
            [
                "--log-level",
                args.log_level,
                "--log-file",
                args.log_file,
            ]
        )

        process_data(
            [
                "--log-level",
                args.log_level,
                "--log-file",
                args.log_file,
            ]
        )

        generate_plots(
            [
                "--log-level",
                args.log_level,
                "--log-file",
                args.log_file,
            ]
        )

        return

    stage_args = [
        "--log-level",
        args.log_level,
        "--log-file",
        args.log_file,
    ]

    if args.stage == "plots":

        if args.regions:
            stage_args.append("--regions")

        if args.region:
            stage_args.append("--region")
            stage_args.extend(args.region)

        if args.all_regions:
            stage_args.append("--all-regions")

        if args.show:
            stage_args.append("--show")

    logger.info("Running pipeline stage: %s", args.stage)

    STAGES[args.stage](stage_args)


if __name__ == "__main__":
    main()