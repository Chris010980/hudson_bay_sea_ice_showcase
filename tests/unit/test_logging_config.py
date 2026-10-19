"""Unit tests for the logging configuration (issue #41).

``_parse_log_level()`` and ``configure_logging()`` are the
shared logging setup of every CLI entry point (docs/testing/
test-levels.md, section 2.2, "configuration parsing").
``configure_logging`` uses ``force=True`` and reconfigures
the global logger; the other CLI tests reconfigure it again
with their own isolated log files.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from src.config.logging_config import (
    _parse_log_level,
    configure_logging,
)


def test_log_level_names_map_to_logging_levels() -> None:
    """Known names map to the logging module levels."""

    assert _parse_log_level("INFO") == logging.INFO
    assert _parse_log_level("debug") == logging.DEBUG


def test_unknown_log_level_raises_value_error() -> None:
    """Unknown names fail with the documented ValueError."""

    with pytest.raises(ValueError, match="Unknown log level"):
        _parse_log_level("VERBOSE")


def test_configure_logging_writes_the_log_file(
    tmp_path: Path,
) -> None:
    """The file handler writes records to the log file."""

    log_file = tmp_path / "pipeline.log"

    configure_logging(
        level="INFO",
        log_file=log_file,
    )

    logging.getLogger("unit_logging_test").info("recorded")

    for handler in logging.getLogger().handlers:
        handler.flush()

    assert "recorded" in log_file.read_text(encoding="utf-8")
