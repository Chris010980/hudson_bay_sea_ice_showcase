"""Pipeline dispatcher for the Hudson Bay sea ice app."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.data_download.download_data import main as download_data
from src.visualization.generate_plots import main as generate_plots
from src.config.logging_config import DEFAULT_LOG_FILE, configure_logging
from src.analysis.process_data import main as process_data


logger = logging.getLogger(__name__)

STAGES = {
    "download": download_data,
    "process": process_data,
    "plots": generate_plots,
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line options for selecting and running pipeline stages."""

    parser = argparse.ArgumentParser(
        description="Run Hudson Bay sea ice pipeline stages."
    )

    parser.add_argument(
        "stage",
        choices=(*STAGES.keys(), "all"),
        help="Pipeline stage to execute.",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
    )

    parser.add_argument(
        "--log-file",
        default=str(DEFAULT_LOG_FILE),
    )

    # ---------------------------------------------------------
    # Plot options
    # ---------------------------------------------------------

    parser.add_argument(
        "--regions",
        action="store_true",
        help="Draw analysis regions.",
    )

    parser.add_argument(
        "--split-regions",
        action="store_true",
        help="Generate one plot for each region.",
    )

    parser.add_argument(
        "--selected-region",
        nargs="+",
        metavar="REGION",
        help="Only generate plots for selected regions.",
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="Display plots after generation.",
    )

    return parser.parse_args(argv)

def main(argv: Sequence[str] | None = None) -> None:
    """Run one pipeline stage or the complete pipeline."""

    args = parse_args(argv)

    configure_logging(
        level=args.log_level,
        log_file=args.log_file,
    )

    stages = STAGES.values() if args.stage == "all" else (STAGES[args.stage],)

    for stage in stages:

        stage_args = [
            "--log-level",
            args.log_level,
            "--log-file",
            args.log_file,
        ]

        if args.stage == "plots":

            if args.regions:
                stage_args.append("--regions")

            if args.split_regions:
                stage_args.append("--split-regions")

            if args.selected_region:
                stage_args.append("--selected-region")
                stage_args.extend(args.selected_region)

            if args.show:
                stage_args.append("--show")

        logger.info("Running pipeline stage: %s", args.stage)

        stage(stage_args)


if __name__ == "__main__":
    main()
