"""Command line entry point for preprocessing raw sea ice data."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.config.logging_config import DEFAULT_LOG_FILE, configure_logging


logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line options for the preprocessing stage."""

    parser = argparse.ArgumentParser(description="Preprocess raw sea ice data.")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the preprocessing stage once it has been migrated."""

    args = parse_args(argv)
    configure_logging(level=args.log_level, log_file=args.log_file)
    logger.warning("Preprocessing stage is not migrated yet.")


if __name__ == "__main__":
    main()
