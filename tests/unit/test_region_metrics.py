"""Unit tests for the region coverage metrics (issue #41).

``compute_region_metrics()`` is the pure scientific core of
``RegionAnalyzer._analyze_region`` (docs/testing/
test-levels.md, section 2.2, "scientific calculations"):
ice classification, absolute and relative ice areas and the
derived coverage percentages, verified with hand values
(ice threshold: >= 150 tenths; pixel area: 625 km²).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from src.analysis.region_analyzer import compute_region_metrics

_REFERENCE = {
    "water_pixels": 4,
    "water_area_pixel_km2": 2500.0,
}


def _metrics(water: list[int]) -> dict:
    """Metrics of one region over the given water values."""

    return compute_region_metrics(
        region_name="Region A",
        observation_date=date(2026, 3, 1),
        water=np.array(water),
        reference=_REFERENCE,
        pixel_area_km2=625.0,
    )


def test_metrics_match_the_hand_calculation() -> None:
    """Water [400, 150, 149, 0]: two ice pixels (>= 150).

    absolute ice area = 2 * 625 = 1250 km²,
    relative ice area = (400 + 150) / 1000 * 625 = 343.75,
    absolute coverage = 100 * 1250 / 2500 = 50 %,
    relative coverage = 100 * 343.75 / 2500 = 13.75 %.
    """
    metrics = _metrics([400, 150, 149, 0])

    assert metrics["region"] == "Region A"
    assert metrics["date"] == date(2026, 3, 1)
    assert metrics["water_pixels"] == 4
    assert metrics["water_area_km2"] == 2500.0
    assert metrics["absolute_ice_area_km2"] == pytest.approx(1250.0)
    assert metrics["relative_ice_area_km2"] == pytest.approx(343.75)
    assert metrics["absolute_coverage_percent"] == (pytest.approx(50.0))
    assert metrics["relative_coverage_percent"] == (
        pytest.approx(13.75)
    )
    assert metrics["missing_pixels"] == 0


def test_ice_threshold_is_inclusive() -> None:
    """150 counts as ice, 149 does not (hand values)."""

    metrics = _metrics([149, 150])

    assert metrics["absolute_ice_area_km2"] == pytest.approx(625.0)
    assert metrics["absolute_coverage_percent"] == (pytest.approx(25.0))


def test_relative_area_normalizes_concentration() -> None:
    """Concentration tenths are scaled to km² (hand values)."""

    metrics = _metrics([1000, 500])

    assert metrics["relative_ice_area_km2"] == pytest.approx(937.5)


def test_water_pixels_come_from_the_reference() -> None:
    """The stored pixel count mirrors the reference summary."""

    metrics = _metrics([100, 200, 300, 400])

    assert metrics["water_pixels"] == _REFERENCE["water_pixels"]
