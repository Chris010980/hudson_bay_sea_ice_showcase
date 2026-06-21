"""Pipeline dispatcher for the Hudson Bay sea ice app."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from src.data.download_data import main as download_data
from src.generate_plots import main as generate_plots
from src.logging_config import configure_logging
from src.process_data import main as process_data


logger = logging.getLogger(__name__)

STAGES = {
    "download": download_data,
    "process": process_data,
    "plots": generate_plots,
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Hudson Bay sea ice pipeline stages.")
    parser.add_argument(
        "stage",
        choices=(*STAGES.keys(), "all"),
        help="Pipeline stage to execute.",
    )
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging(level=args.log_level, log_file=args.log_file)
    stages = STAGES.values() if args.stage == "all" else (STAGES[args.stage],)

    logger.info("Running pipeline stage: %s", args.stage)
    stage_args = ["--log-level", args.log_level]
    if args.log_file:
        stage_args.extend(["--log-file", args.log_file])

    for stage in stages:
        stage(stage_args)


if __name__ == "__main__":
    main()
