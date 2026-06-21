"""Command line entry point for plot generation."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from src.logging_config import configure_logging


logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sea ice plots.")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging(level=args.log_level, log_file=args.log_file)
    logger.warning("Visualization stage is not migrated yet.")


if __name__ == "__main__":
    main()
