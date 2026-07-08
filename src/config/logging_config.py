"""Shared logging setup for command line entry points."""

from __future__ import annotations

import logging
from pathlib import Path

from src.paths import LOG_DIR

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_LOG_FILE = LOG_DIR / "hudson_bay_sea_ice.log"


def configure_logging(
    level: str = "INFO",
    log_file: str | Path | None = DEFAULT_LOG_FILE,
) -> None:
    """Configure console and file logging for command line scripts.

    Args:
        level: Logging level name such as ``INFO`` or ``DEBUG``.
        log_file: Optional log file path. Relative paths are stored under the
            project-level ``logs`` directory; ``None`` disables file logging.
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
    """Translate a logging level name into the integer expected by logging."""

    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        valid_levels = ", ".join(("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))
        raise ValueError(f"Unknown log level '{level}'. Use one of: {valid_levels}.")

    return numeric_level
