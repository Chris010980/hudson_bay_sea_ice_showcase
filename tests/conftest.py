"""Shared pytest fixtures for the test suite."""

from pathlib import Path

import pytest


@pytest.fixture
def test_environment(tmp_path: Path) -> dict[str, Path]:
    """Provide an isolated temporary filesystem for a test."""
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "output"
    build_dir = tmp_path / "build"

    data_dir.mkdir()
    output_dir.mkdir()
    build_dir.mkdir()

    return {
        "root": tmp_path,
        "data": data_dir,
        "output": output_dir,
        "build": build_dir,
    }

