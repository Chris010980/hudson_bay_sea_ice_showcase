"""Component tests for the RegionAnalyzer (issue #18).

The tests verify the scientific calculation of daily regional
sea-ice coverage against independently calculated expected values:

* threshold-based absolute ice area,
* concentration-weighted relative ice area,
* reference water-area handling,
* the 15 % pixel detection threshold including its exact boundary,
* 0 % and 100 % concentration cases,
* mixed concentration rasters,
* and the configured 625 km² pixel area.

Expected values follow docs/methodology/coverage-metrics.md:
ice pixel = concentration >= 15 % (>= 150 on the 0-1000 scale),
absolute ice area = N_ice * 625 km², relative ice area =
sum(C / 1000 * 625 km²) over ice pixels, and coverage percentages
relative to the reference water area.

All inputs are controlled synthetic fixtures from tests/conftest.py
or controlled raster files created in the isolated test environment.
No production data or external services are required, and all tests
are deterministic.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.analysis.region_analyzer import RegionAnalyzer

PIXEL_AREA_KM2 = 625.0

EXPECTED_RESULT_KEYS = {
    "region",
    "date",
    "water_pixels",
    "water_area_km2",
    "absolute_ice_area_km2",
    "relative_ice_area_km2",
    "absolute_coverage_percent",
    "relative_coverage_percent",
    "missing_pixels",
}


# ------------------------------------------------------------------
# Helpers and fixtures
# ------------------------------------------------------------------


def _write_concentration_raster(
    path: Path,
    values: dict[int, int],
    shape: tuple[int, int] = (5, 5),
) -> Path:
    """Write a synthetic concentration GeoTIFF with controlled values.

    ``values`` maps flat raster indices to concentration values.
    Pixels without an entry are filled with the pole hole code 2510.
    """

    data = np.full(shape, 2510, dtype=np.uint16)

    for flat_index, value in values.items():
        data.flat[flat_index] = value

    transform = from_origin(
        west=0,
        north=125_000,
        xsize=25_000,
        ysize=25_000,
    )

    profile = {
        "driver": "GTiff",
        "height": shape[0],
        "width": shape[1],
        "count": 1,
        "dtype": data.dtype,
        "crs": "EPSG:3411",
        "transform": transform,
    }

    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data, 1)

    return path


def _write_reference_json(
    path: Path,
    reference_masks: dict[str, np.ndarray],
    water_areas_km2: dict[str, float] | None = None,
) -> Path:
    """Write a controlled reference summary for the RegionAnalyzer."""

    data = {}

    for region, indices in reference_masks.items():
        water_area = (
            water_areas_km2[region]
            if water_areas_km2 is not None
            else len(indices) * PIXEL_AREA_KM2
        )

        data[region] = {
            "water_pixels": len(indices),
            "water_area_pixel_km2": water_area,
        }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    return path


@pytest.fixture
def analyzer_environment(
    test_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> dict[str, Path]:
    """Provide reference masks and a reference summary in isolation."""

    filter_dir = test_environment["output"] / "reference" / "filters"
    filter_dir.mkdir(parents=True)

    for region, indices in expected_reference_masks.items():
        np.save(filter_dir / f"{region}_water.npy", indices)

    reference_json = _write_reference_json(
        test_environment["output"]
        / "reference"
        / "reference_summary.json",
        expected_reference_masks,
    )

    return {
        "filter_dir": filter_dir,
        "reference_json": reference_json,
    }


def _make_analyzer(
    analyzer_environment: dict[str, Path],
    input_tif: Path,
    pixel_area_km2: float = PIXEL_AREA_KM2,
) -> RegionAnalyzer:
    """Create a RegionAnalyzer with injected controlled paths."""

    return RegionAnalyzer(
        input_tif=input_tif,
        reference_json=analyzer_environment["reference_json"],
        filter_dir=analyzer_environment["filter_dir"],
        pixel_area_km2=pixel_area_km2,
    )


def _region_values(
    expected_reference_masks: dict[str, np.ndarray],
    water_values: list[int],
    mixed_values: list[int],
) -> dict[int, int]:
    """Map per-region concentration values to flat raster indices."""

    return dict(
        zip(
            expected_reference_masks["Test Region Water"],
            water_values,
            strict=True,
        )
    ) | dict(
        zip(
            expected_reference_masks["Test Region Mixed"],
            mixed_values,
            strict=True,
        )
    )


# ------------------------------------------------------------------
# Task: test absolute ice coverage
# ------------------------------------------------------------------


def test_absolute_ice_coverage_is_threshold_based(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Absolute ice area counts pixels at or above 15 % concentration.

    Independent calculation:
    4 water pixels with 20 %, 40 %, 60 %, 80 % are all ice
    -> absolute area = 4 * 625 km² = 2500 km²
    1 water pixel with 50 % is ice
    -> absolute area = 1 * 625 km² = 625 km²
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[200, 400, 600, 800],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "absolute_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    assert (
        results["Test Region Water"]["absolute_ice_area_km2"] == 2500.0
    )
    assert (
        results["Test Region Mixed"]["absolute_ice_area_km2"] == 625.0
    )


# ------------------------------------------------------------------
# Task: test concentration-weighted relative ice coverage
# ------------------------------------------------------------------


def test_relative_ice_coverage_is_concentration_weighted(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Relative ice area weights ice pixels by their concentration.

    Independent calculation:
    (200 + 400 + 600 + 800) / 1000 * 625 km² = 1250 km²
    500 / 1000 * 625 km² = 312.5 km²

    Absolute and relative metrics remain distinguishable: the
    binary absolute area (2500 km²) differs from the weighted
    relative area (1250 km²).
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[200, 400, 600, 800],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "relative_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    assert results["Test Region Water"][
        "relative_ice_area_km2"
    ] == pytest.approx(1250.0)
    assert results["Test Region Mixed"][
        "relative_ice_area_km2"
    ] == pytest.approx(312.5)

    assert (
        results["Test Region Water"]["relative_ice_area_km2"]
        != results["Test Region Water"]["absolute_ice_area_km2"]
    )


# ------------------------------------------------------------------
# Task: test reference water area handling
# ------------------------------------------------------------------


def test_coverage_uses_reference_water_area(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Coverage percentages use the reference water area as denominator.

    A controlled reference area of 5000 km² (not 4 * 625 km²)
    verifies that the denominator comes from the reference
    configuration rather than being recomputed:

    absolute coverage = 2500 / 5000 * 100 % = 50 %
    relative coverage = 1250 / 5000 * 100 % = 25 %
    mixed absolute coverage = 625 / 5000 * 100 % = 12.5 %
    mixed relative coverage = 312.5 / 5000 * 100 % = 6.25 %
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[200, 400, 600, 800],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "reference_area_20260315.tif",
        values,
    )

    reference_json = _write_reference_json(
        test_environment["output"]
        / "reference"
        / "custom_summary.json",
        expected_reference_masks,
        water_areas_km2={
            "Test Region Water": 5000.0,
            "Test Region Mixed": 5000.0,
        },
    )

    analyzer = RegionAnalyzer(
        input_tif=raster,
        reference_json=reference_json,
        filter_dir=analyzer_environment["filter_dir"],
    )

    results = analyzer.analyze()

    water = results["Test Region Water"]

    assert water["water_area_km2"] == 5000.0
    assert water["absolute_coverage_percent"] == pytest.approx(50.0)
    assert water["relative_coverage_percent"] == pytest.approx(25.0)

    mixed = results["Test Region Mixed"]

    assert mixed["water_area_km2"] == 5000.0
    assert mixed["absolute_coverage_percent"] == pytest.approx(12.5)
    assert mixed["relative_coverage_percent"] == pytest.approx(6.25)


# ------------------------------------------------------------------
# Task: test the 15 % pixel detection threshold
# ------------------------------------------------------------------


def test_pixel_detection_threshold(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Pixels below 15 % are not ice; pixels above 15 % are ice.

    Independent calculation for values 14.9 %, 15.1 %, 10 %, 100 %:
    ice pixels are 15.1 % and 100 %
    -> absolute area = 2 * 625 km² = 1250 km²
    -> relative area = (151 + 1000) / 1000 * 625 km² = 719.375 km²

    The mixed region value of 8 % is below the threshold and
    contributes nothing.
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[149, 151, 100, 1000],
        mixed_values=[80],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "threshold_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    water = results["Test Region Water"]

    assert water["absolute_ice_area_km2"] == 1250.0
    assert water["relative_ice_area_km2"] == pytest.approx(719.375)

    mixed = results["Test Region Mixed"]

    assert mixed["absolute_ice_area_km2"] == 0.0
    assert mixed["relative_ice_area_km2"] == 0.0


# ------------------------------------------------------------------
# Task: test the exact 15 % boundary
# ------------------------------------------------------------------


def test_exact_threshold_boundary(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """A concentration of exactly 15 % counts as ice (>= threshold).

    Independent calculation for values 15 %, 14.9 %, 15 %, 14.9 %:
    ice pixels are the two exact 15 % pixels
    -> absolute area = 2 * 625 km² = 1250 km²
    -> relative area = (150 + 150) / 1000 * 625 km² = 187.5 km²
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[150, 149, 150, 149],
        mixed_values=[149],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "boundary_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    water = results["Test Region Water"]

    assert water["absolute_ice_area_km2"] == 1250.0
    assert water["relative_ice_area_km2"] == pytest.approx(187.5)

    assert results["Test Region Mixed"]["absolute_ice_area_km2"] == 0.0


# ------------------------------------------------------------------
# Task: test 0 % and 100 % concentration cases
# ------------------------------------------------------------------


def test_zero_concentration_case(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """0 % concentration yields zero ice area and zero coverage."""

    values = _region_values(
        expected_reference_masks,
        water_values=[0, 0, 0, 0],
        mixed_values=[0],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "zero_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    for region in ("Test Region Water", "Test Region Mixed"):
        assert results[region]["absolute_ice_area_km2"] == 0.0
        assert results[region]["relative_ice_area_km2"] == 0.0
        assert results[region]["absolute_coverage_percent"] == 0.0
        assert results[region]["relative_coverage_percent"] == 0.0


def test_full_concentration_case(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """100 % concentration yields the complete water area as ice.

    Independent calculation:
    absolute area = relative area = 4 * 625 km² = 2500 km²
    coverage = 2500 / 2500 * 100 % = 100 %

    At 100 % concentration the binary and weighted metrics coincide.
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[1000, 1000, 1000, 1000],
        mixed_values=[1000],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "full_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    water = results["Test Region Water"]

    assert water["absolute_ice_area_km2"] == 2500.0
    assert water["relative_ice_area_km2"] == 2500.0
    assert water["absolute_coverage_percent"] == 100.0
    assert water["relative_coverage_percent"] == 100.0

    mixed = results["Test Region Mixed"]

    assert mixed["absolute_ice_area_km2"] == 625.0
    assert mixed["relative_ice_area_km2"] == 625.0
    assert mixed["absolute_coverage_percent"] == 100.0
    assert mixed["relative_coverage_percent"] == 100.0


# ------------------------------------------------------------------
# Task: test mixed concentration rasters
# ------------------------------------------------------------------


def test_mixed_concentration_raster(
    synthetic_raster: Path,
    analyzer_environment: dict[str, Path],
) -> None:
    """Verify the analysis against the mixed synthetic sea-ice fixture.

    The water region contains 0 %, 14.9 %, 100 % and 25 %:
    -> ice pixels: 100 % and 25 % (2 pixels)
    -> absolute area = 2 * 625 km² = 1250 km²
    -> relative area = (1000 + 250) / 1000 * 625 km² = 781.25 km²
    -> absolute coverage = 1250 / 2500 * 100 % = 50 %
    -> relative coverage = 781.25 / 2500 * 100 % = 31.25 %

    The mixed region contains exactly 15 %:
    -> absolute area = 625 km², absolute coverage = 100 %
    -> relative area = 150 / 1000 * 625 km² = 93.75 km²,
       relative coverage = 15 %

    Absolute and relative metrics remain distinguishable.
    """

    results = _make_analyzer(
        analyzer_environment, synthetic_raster
    ).analyze()

    water = results["Test Region Water"]

    assert water["absolute_ice_area_km2"] == 1250.0
    assert water["relative_ice_area_km2"] == pytest.approx(781.25)
    assert water["absolute_coverage_percent"] == pytest.approx(50.0)
    assert water["relative_coverage_percent"] == pytest.approx(31.25)

    mixed = results["Test Region Mixed"]

    assert mixed["absolute_ice_area_km2"] == 625.0
    assert mixed["relative_ice_area_km2"] == pytest.approx(93.75)
    assert mixed["absolute_coverage_percent"] == 100.0
    assert mixed["relative_coverage_percent"] == pytest.approx(15.0)


# ------------------------------------------------------------------
# Task: test the configured 625 km² pixel area
# ------------------------------------------------------------------


def test_configured_pixel_area(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """The configured pixel area scales all area calculations.

    Independent calculation with pixel_area_km2 = 100 km² and
    4 ice pixels of 20 %, 40 %, 60 %, 80 %:
    -> absolute area = 4 * 100 km² = 400 km²
    -> relative area = 2000 / 1000 * 100 km² = 200 km²

    The default configuration uses the documented 625 km².
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[200, 400, 600, 800],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "pixel_area_20260315.tif",
        values,
    )

    default_analyzer = _make_analyzer(analyzer_environment, raster)
    assert default_analyzer.pixel_area_km2 == 625.0

    analyzer = _make_analyzer(
        analyzer_environment,
        raster,
        pixel_area_km2=100.0,
    )
    assert analyzer.pixel_area_km2 == 100.0

    results = analyzer.analyze()

    water = results["Test Region Water"]

    assert water["absolute_ice_area_km2"] == 400.0
    assert water["relative_ice_area_km2"] == pytest.approx(200.0)


# ------------------------------------------------------------------
# Result structure and observation date
# ------------------------------------------------------------------


def test_result_structure_and_observation_date(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """A complete result contains the documented metrics and date."""

    values = _region_values(
        expected_reference_masks,
        water_values=[200, 400, 600, 800],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "sea_ice_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    water = results["Test Region Water"]

    assert set(water) == EXPECTED_RESULT_KEYS
    assert water["region"] == "Test Region Water"
    assert water["date"] == date(2026, 3, 15)
    assert water["water_pixels"] == 4
    assert water["water_area_km2"] == 2500.0
    assert water["missing_pixels"] == 0


# ------------------------------------------------------------------
# Quality checks: invalid regional observations
# ------------------------------------------------------------------


def test_unreadable_input_returns_empty_results(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
) -> None:
    """An unreadable GeoTIFF yields empty results instead of an error."""

    analyzer = _make_analyzer(
        analyzer_environment,
        test_environment["data"] / "does_not_exist.tif",
    )

    results = analyzer.analyze()

    assert results == {}
    assert analyzer.band is None
