"""Component tests for RegionAnalyzer data validity (issue #19).

The tests verify the handling of invalid/missing pixels and
reference consistency:

* missing-value code handling (2550),
* special values above the valid SIC range (2510, 2530, 2540, 1001),
* observations without valid water pixels,
* mismatched reference/current water-pixel counts,
* invalid daily observations,
* and region-specific, deterministic results.

The documented encoding (docs/methodology/data-and-inputs.md,
section 3) is:

    0-1000   valid sea-ice concentration
    2510     pole hole
    2530     coast
    2540     land
    2550     missing data

Values above 1000 are excluded from numerical concentration
processing. Missing data within the selected water pixels rejects the
region/day (docs/methodology/coverage-metrics.md, section 10), as
does any deviation between the current valid water-pixel count and
the reference configuration.

All inputs are controlled synthetic fixtures; no production data
or external services are required, and all tests are deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.analysis.region_analyzer import RegionAnalyzer

PIXEL_AREA_KM2 = 625.0


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
    Pixels without an entry are filled with the pole-hole code 2510.
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

    reference_json = (
        test_environment["output"]
        / "reference"
        / "reference_summary.json"
    )

    data = {
        region: {
            "water_pixels": len(indices),
            "water_area_pixel_km2": len(indices) * PIXEL_AREA_KM2,
        }
        for region, indices in expected_reference_masks.items()
    }

    with open(reference_json, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    return {
        "filter_dir": filter_dir,
        "reference_json": reference_json,
    }


def _make_analyzer(
    analyzer_environment: dict[str, Path],
    input_tif: Path,
) -> RegionAnalyzer:
    """Create a RegionAnalyzer with injected controlled paths."""

    return RegionAnalyzer(
        input_tif=input_tif,
        reference_json=analyzer_environment["reference_json"],
        filter_dir=analyzer_environment["filter_dir"],
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
# Task: test missing-value code handling
# ------------------------------------------------------------------


def test_missing_value_code_rejects_region(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Missing data (2550) within the selected water pixels rejects
    the affected region/day.

    The region is not evaluated using a partially available water
    mask, following docs/methodology/coverage-metrics.md section 10.
    The unaffected mixed region remains valid.
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[200, 2550, 400, 600],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "missing_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    assert "Test Region Water" not in results
    assert "Test Region Mixed" in results


def test_all_missing_values_reject_region(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """A fully missing region observation is rejected as well."""

    values = _region_values(
        expected_reference_masks,
        water_values=[2550, 2550, 2550, 2550],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "all_missing_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    assert "Test Region Water" not in results
    assert "Test Region Mixed" in results


# ------------------------------------------------------------------
# Task: test special values above the valid SIC range
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "special_value",
    [2510, 2530, 2540, 1001],
)
def test_special_values_above_valid_range_are_rejected(
    special_value: int,
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Special values above the valid 0-1000 range are never treated
    as valid sea-ice concentration.

    The special value is excluded from the water pixels, so only 3
    of 4 expected water pixels remain valid -> the region is
    rejected through the reference count check.

    Documented codes (docs/methodology/data-and-inputs.md):
    2510 pole hole, 2530 coast, 2540 land, 2550 missing data.
    1001 lies directly above the valid concentration range.
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[200, special_value, 400, 600],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"]
        / f"special_{special_value}_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    assert "Test Region Water" not in results
    assert "Test Region Mixed" in results


# ------------------------------------------------------------------
# Task: test missing water pixels
# ------------------------------------------------------------------


def test_missing_water_pixels_reject_region(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """An observation without any valid water pixel in a region is
    rejected instead of being evaluated against an empty mask.

    All selected pixels carry land/pole codes, so the valid water
    count is 0 instead of the expected 4 -> region skipped.
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[2510, 2540, 2510, 2540],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "no_water_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    assert "Test Region Water" not in results
    assert "Test Region Mixed" in results


# ------------------------------------------------------------------
# Task: test mismatched reference/current water-pixel counts
# ------------------------------------------------------------------


def test_water_count_mismatch_rejects_region(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """The current valid water-pixel count must match the reference.

    One of four selected pixels is land (2540):
    3 valid water pixels != 4 expected -> region skipped.
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[200, 2540, 400, 600],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "mismatch_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    assert "Test Region Water" not in results
    assert "Test Region Mixed" in results


def test_reference_count_inconsistency_is_detected(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """A reference configuration that disagrees with the actual
    valid water pixels is detected.

    The reference declares 3 water pixels, but the daily observation
    provides 4 valid concentration pixels at the mask positions:
    4 != 3 -> the region is rejected instead of silently evaluated
    against an inconsistent reference.
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[200, 400, 600, 800],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "ref_inconsistent_20260315.tif",
        values,
    )

    reference_json = (
        test_environment["output"]
        / "reference"
        / "inconsistent_summary.json"
    )

    data = {
        "Test Region Water": {
            "water_pixels": 3,
            "water_area_pixel_km2": 3 * PIXEL_AREA_KM2,
        },
        "Test Region Mixed": {
            "water_pixels": 1,
            "water_area_pixel_km2": PIXEL_AREA_KM2,
        },
    }

    with open(reference_json, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    analyzer = RegionAnalyzer(
        input_tif=raster,
        reference_json=reference_json,
        filter_dir=analyzer_environment["filter_dir"],
    )

    results = analyzer.analyze()

    assert "Test Region Water" not in results
    assert "Test Region Mixed" in results


# ------------------------------------------------------------------
# Task: test invalid daily observations
# ------------------------------------------------------------------


def test_invalid_daily_observation_yields_empty_results(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
) -> None:
    """Unreadable daily observations produce empty results rather
    than silently wrong ones.

    Covers a non-existent input file and a corrupt GeoTIFF.
    """

    corrupt = test_environment["data"] / "corrupt_20260315.tif"
    corrupt.write_bytes(b"this is not a valid geotiff")

    invalid_inputs = [
        test_environment["data"] / "does_not_exist.tif",
        corrupt,
    ]

    for input_tif in invalid_inputs:
        analyzer = _make_analyzer(analyzer_environment, input_tif)

        assert analyzer.analyze() == {}
        assert analyzer.band is None


# ------------------------------------------------------------------
# Task: test region-specific results
# ------------------------------------------------------------------


def test_invalid_region_does_not_affect_valid_regions(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """An invalid region is rejected region-specifically: it neither
    corrupts nor removes the results of valid regions.

    Mixed region (1 water pixel, 50 % concentration):
    absolute area = 1 * 625 km² = 625 km² -> 100 % coverage
    relative area = 500 / 1000 * 625 km² = 312.5 km² -> 50 % coverage
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[2550, 200, 400, 600],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "region_specific_20260315.tif",
        values,
    )

    results = _make_analyzer(analyzer_environment, raster).analyze()

    assert set(results) == {"Test Region Mixed"}

    mixed = results["Test Region Mixed"]

    assert mixed["absolute_ice_area_km2"] == 625.0
    assert mixed["relative_ice_area_km2"] == pytest.approx(312.5)
    assert mixed["absolute_coverage_percent"] == 100.0
    assert mixed["relative_coverage_percent"] == pytest.approx(50.0)
    assert mixed["missing_pixels"] == 0


def test_region_results_are_deterministic(
    test_environment: dict[str, Path],
    analyzer_environment: dict[str, Path],
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Repeated analyses of the same observation produce identical
    results for all valid regions.
    """

    values = _region_values(
        expected_reference_masks,
        water_values=[200, 400, 600, 800],
        mixed_values=[500],
    )

    raster = _write_concentration_raster(
        test_environment["data"] / "deterministic_20260315.tif",
        values,
    )

    first = _make_analyzer(analyzer_environment, raster).analyze()
    second = _make_analyzer(analyzer_environment, raster).analyze()

    assert first == second
    assert set(first) == {"Test Region Water", "Test Region Mixed"}
