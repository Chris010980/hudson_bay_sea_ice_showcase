"""Shared logging setup for command line entry points."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.config.paths import LOG_DIR, LOG_FILE

DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
DEFAULT_LOG_FILE = LOG_FILE


def add_log_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the logging options shared by every stage CLI.

    The dispatcher and the stage modules call this helper so
    the shared options (names, defaults, help texts) have a
    single source of truth (issue #106, CLI parity).
    """

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


def configure_logging(
    level: str = "INFO",
    log_file: str | Path | None = DEFAULT_LOG_FILE,
) -> None:
    """Configure console and file logging for command line scripts.

    Args:
        level: Logging level name such as ``INFO`` or ``DEBUG``.
        log_file: Optional log file path. Relative paths are stored
            under the project-level ``logs`` directory; ``None``
            disables file logging.
    """

    numeric_level = _parse_log_level(level)
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file is not None:
        log_path = Path(log_file)
        if not log_path.is_absolute():
            log_path = LOG_DIR / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=numeric_level,
        format=DEFAULT_LOG_FORMAT,
        handlers=handlers,
        force=True,
    )


def _parse_log_level(level: str) -> int:
    """Translate a logging level name into the integer expected
    by logging.
    """

    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        valid_levels = ", ".join(
            ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        )
        raise ValueError(
            f"Unknown log level '{level}'. Use one of: {valid_levels}."
        )

    return numeric_level
