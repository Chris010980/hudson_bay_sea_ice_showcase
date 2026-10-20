"""
Build the GitHub Pages website.

The build step combines the static website located in ``html/`` with the
latest generated analysis results stored in ``output/`` and creates a
self-contained ``build/`` directory suitable for GitHub Pages
deployment.
"""

from __future__ import annotations

import argparse
import logging
import shutil
from collections.abc import Sequence
from pathlib import Path

from src.config.logging_config import (
    add_log_arguments,
    configure_logging,
)
from src.config.paths import (
    BUILD_DIR,
    HTML_DIR,
    OUTPUT_DIR,
)

logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None):

    parser = argparse.ArgumentParser(
        description="Build GitHub Pages website."
    )

    add_log_arguments(parser)

    return parser.parse_args(argv)


def copy_directory(source: Path, destination: Path):

    if not source.exists():
        logger.warning("Directory does not exist: %s", source)

        return

    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    html_dir: Path = HTML_DIR,
    output_dir: Path = OUTPUT_DIR,
    build_dir: Path = BUILD_DIR,
) -> Path:
    """Build the GitHub Pages website.

    Since issue #106 the three directories are injectable
    keyword arguments with the production defaults (F-018);
    the build behavior is unchanged.
    """

    args = parse_args(argv)

    configure_logging(
        level=args.log_level,
        log_file=args.log_file,
    )

    if not html_dir.exists():
        raise FileNotFoundError(
            f"Website directory not found: {html_dir}"
        )

    if not output_dir.exists():
        raise FileNotFoundError(
            f"Output directory not found: {output_dir}"
        )

    if build_dir.exists():
        logger.info("Removing previous build directory.")

        shutil.rmtree(build_dir)

    build_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger.info("Copying website.")

    copy_directory(
        html_dir,
        build_dir,
    )

    logger.info("Copying generated output.")

    copy_directory(
        output_dir,
        build_dir / "output",
    )

    logger.info("Website build completed.")

    return build_dir
