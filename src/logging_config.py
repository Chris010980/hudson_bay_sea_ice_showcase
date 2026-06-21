"""Shared logging setup for command line entry points."""

from __future__ import annotations

import logging
from pathlib import Path


DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
) -> None:
    """Configure application logging for CLI scripts."""

    numeric_level = _parse_log_level(level)
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=numeric_level,
        format=DEFAULT_LOG_FORMAT,
        handlers=handlers,
        force=True,
    )


def _parse_log_level(level: str) -> int:
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        valid_levels = ", ".join(("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))
        raise ValueError(f"Unknown log level '{level}'. Use one of: {valid_levels}.")

    return numeric_level
