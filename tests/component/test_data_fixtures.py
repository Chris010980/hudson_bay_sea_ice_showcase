"""Tests for deterministic CSV and JSON fixtures."""

import json
from pathlib import Path

import pandas as pd


def test_daily_observations_fixture(
    daily_observations_csv: Path,
) -> None:
    """Verify the deterministic daily observations fixture."""
    assert daily_observations_csv.exists()

    data = pd.read_csv(daily_observations_csv)

    expected_columns = [
        "region",
        "date",
        "water_pixels",
        "water_area_km2",
        "absolute_ice_area_km2",
        "relative_ice_area_km2",
        "absolute_coverage_percent",
        "relative_coverage_percent",
        "missing_pixels",
    ]

    assert list(data.columns) == expected_columns

    assert len(data) == 6
    assert data["region"].nunique() == 2
    assert data["date"].nunique() == 3
    assert data["missing_pixels"].eq(0).all()


def test_regions_json_fixture(
    test_regions_json: Path,
) -> None:
    """Verify the deterministic region configuration fixture."""
    assert test_regions_json.exists()

    with open(test_regions_json, encoding="utf-8") as file:
        data = json.load(file)

    assert set(data["regions"]) == {
        "Test Region A",
        "Test Region B",
    }

    for region in data["regions"].values():
        assert "description" in region
        assert "polygon" in region
        assert len(region["polygon"]) == 4