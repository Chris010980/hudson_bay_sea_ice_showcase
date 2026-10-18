"""Pipeline dispatcher for the Hudson Bay sea ice app."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.analysis.process_data import (
    add_arguments as add_process_arguments,
)
from src.analysis.process_data import main as process_data
from src.config.logging_config import (
    add_log_arguments,
    configure_logging,
)
from src.data_download.download_data import (
    add_arguments as add_download_arguments,
)
from src.data_download.download_data import main as download_data
from src.update.build_pages import main as build_pages
from src.update.update_pipeline import (
    add_arguments as add_update_arguments,
)
from src.update.update_pipeline import main as update_pipeline
from src.visualization.generate_plots import (
    add_arguments as add_plots_arguments,
)
from src.visualization.generate_plots import main as generate_plots

logger = logging.getLogger(__name__)

Stage = Callable[[Sequence[str] | None], None]
"""Signature of a pipeline stage entry point."""

STAGES: Mapping[str, Stage] = {
    "download": download_data,
    "process": process_data,
    "plots": generate_plots,
    "build": build_pages,
    "update": update_pipeline,
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line options.

    Every stage sub-parser is built from the same argument
    specification the stage module uses for its own CLI
    (``add_arguments`` plus the shared logging options), so
    the dispatcher and the direct invocations expose the
    identical option set (CLI parity, issue #106).
    """

    parser = argparse.ArgumentParser(
        description="Hudson Bay Sea Ice processing pipeline."
    )

    subparsers = parser.add_subparsers(
        dest="stage",
        required=True,
        metavar="STAGE",
    )

    download_parser = subparsers.add_parser(
        "download",
        help="Download the latest NSIDC data.",
    )

    add_log_arguments(download_parser)
    add_download_arguments(download_parser)

    process_parser = subparsers.add_parser(
        "process",
        help="Process downloaded GeoTIFF files.",
    )

    add_log_arguments(process_parser)
    add_process_arguments(process_parser)

    plots_parser = subparsers.add_parser(
        "plots",
        help="Generate plots.",
    )

    add_log_arguments(plots_parser)
    add_plots_arguments(plots_parser)

    build_parser = subparsers.add_parser(
        "build",
        help="Build the GitHub Pages website.",
    )

    add_log_arguments(build_parser)

    update_parser = subparsers.add_parser(
        "update",
        help="Download only new data and update all results.",
    )

    add_log_arguments(update_parser)
    add_update_arguments(update_parser)

    all_parser = subparsers.add_parser(
        "all",
        help="Run the complete processing pipeline.",
    )

    add_log_arguments(all_parser)

    return parser.parse_args(argv)


def _download_stage_args(args: argparse.Namespace) -> list[str]:
    """Forward the download stage options with their values."""

    stage_args = [
        "--base-url",
        args.base_url,
        "--output-dir",
        args.output_dir,
        "--product",
        args.product,
    ]

    for year in args.years or []:
        stage_args.extend(["--year", year])

    for month in args.months or []:
        stage_args.extend(["--month", month])

    if args.dry_run:
        stage_args.append("--dry-run")

    return stage_args


def _process_stage_args(args: argparse.Namespace) -> list[str]:
    """Forward the process stage date filters."""

    stage_args: list[str] = []

    if args.start_date is not None:
        stage_args.extend(
            [
                "--start-date",
                args.start_date.isoformat(),
            ]
        )

    if args.end_date is not None:
        stage_args.extend(
            [
                "--end-date",
                args.end_date.isoformat(),
            ]
        )

    return stage_args


def _plots_stage_args(args: argparse.Namespace) -> list[str]:
    """Forward the plots stage options with their values."""

    stage_args = [args.plot_type]

    if args.input_tiff is not None:
        stage_args.extend(
            [
                "--input-tiff",
                args.input_tiff,
            ]
        )

    stage_args.extend(
        [
            "--output",
            args.output,
            "--bounds",
            *(str(bound) for bound in args.bounds),
        ]
    )

    if args.regions:
        stage_args.append("--regions")

    if args.region:
        stage_args.append("--region")
        stage_args.extend(args.region)

    if args.all_regions:
        stage_args.append("--all-regions")

    if args.show:
        stage_args.append("--show")

    return stage_args


def _update_stage_args(args: argparse.Namespace) -> list[str]:
    """Forward the update stage options."""

    if args.keep_data:
        return ["--keep-data"]

    return []


STAGE_ARGS: Mapping[str, Callable[[argparse.Namespace], list[str]]] = {
    "download": _download_stage_args,
    "process": _process_stage_args,
    "plots": _plots_stage_args,
    "update": _update_stage_args,
}
"""Per-stage argument builders (CLI parity, issue #106)."""


def build_stage_args(args: argparse.Namespace) -> list[str]:
    """Build the argument list forwarded to the selected stage.

    Every live option of the stage modules is forwarded with
    its value (CLI parity, issue #106).
    """

    stage_args = [
        "--log-level",
        args.log_level,
        "--log-file",
        args.log_file,
    ]

    builder = STAGE_ARGS.get(args.stage)

    if builder is not None:
        stage_args.extend(builder(args))

    return stage_args


def main(
    argv: Sequence[str] | None = None,
    *,
    stages: Mapping[str, Stage] = STAGES,
) -> None:
    """Run the selected pipeline stage."""

    args = parse_args(argv)

    configure_logging(
        level=args.log_level,
        log_file=args.log_file,
    )

    if args.stage == "all":
        logger.info("Running complete pipeline.")

        stage_args = [
            "--log-level",
            args.log_level,
            "--log-file",
            args.log_file,
        ]

        stages["download"](stage_args)

        stages["process"](stage_args)

        # The plots stage requires its positional plot type;
        # "all" regenerates the complete product set (#106).
        stages["plots"]([*stage_args, "all"])

        stages["build"](stage_args)

        return

    stage_args = build_stage_args(args)

    logger.info("Running pipeline stage: %s", args.stage)

    stages[args.stage](stage_args)


if __name__ == "__main__":
    main()
