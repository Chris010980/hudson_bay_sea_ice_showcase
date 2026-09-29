"""Tests for shared temporary filesystem fixtures."""

from pathlib import Path


def test_test_environment_is_isolated(test_environment: dict[str, Path]) -> None:
    """Verify that the test environment provides isolated directories."""
    root = test_environment["root"]
    data_dir = test_environment["data"]
    output_dir = test_environment["output"]
    build_dir = test_environment["build"]

    assert root.exists()
    assert root.is_dir()

    assert data_dir.is_dir()
    assert output_dir.is_dir()
    assert build_dir.is_dir()

    assert data_dir.parent == root
    assert output_dir.parent == root
    assert build_dir.parent == root

    assert len({data_dir, output_dir, build_dir}) == 3
