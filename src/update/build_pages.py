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

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing build directory before building.",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
    )

    parser.add_argument(
        "--log-file",
    )

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


def main(argv: Sequence[str] | None = None):

    parse_args(argv)

    if not HTML_DIR.exists():
        raise FileNotFoundError(
            f"Website directory not found: {HTML_DIR}"
        )

    if BUILD_DIR.exists():
        logger.info("Removing previous build directory.")

        shutil.rmtree(BUILD_DIR)

    BUILD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger.info("Copying website.")

    copy_directory(
        HTML_DIR,
        BUILD_DIR,
    )

    logger.info("Copying generated output.")

    copy_directory(
        OUTPUT_DIR,
        BUILD_DIR / "output",
    )

    logger.info("Website build completed.")

    return BUILD_DIR
