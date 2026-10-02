"""Integration tests for the spatial processing chain (issue #29).

The tests verify the controlled chain from reference preparation
to regional results persistence (docs/testing/test-levels.md,
section 4.2):

    ReferenceBuilder
          |
          v
    water masks + reference_summary.json
          |
          v
    RegionAnalyzer
          |
          v
    daily regional results
          |
          v
    ResultsManager
          |
          v
    ice_coverage_summary.csv + latest.json

Covered behavior:

* the real ReferenceBuilder run produces controlled, reproducible
  reference products,
* the real RegionAnalyzer consumes exactly these products,
* persisted results match independently calculated expectations,
* incremental processing preserves existing observations and
  introduces no duplicates,
* and production directories are not modified.

Test design:

* The controlled reference raster and region definitions come
  from the established fixtures in tests/conftest.py; their
  water masks ([0, 1, 5, 6] and [2]) are verified by
  tests/component/test_reference_builder.py.
* Observation GeoTIFFs are created in the isolated test
  environment with hand-chosen concentration values on the
  0-1000 scale (ice pixel threshold: >= 150). Every expected
  metric is calculated by hand in the test docstrings.
* ReferenceBuilder writes to module-level constants; the
  chain_environment fixture redirects them to the isolated test
  environment. The naturalearth ocean dataset is replaced by a
  controlled ocean polygon (pattern from
  tests/component/test_reference_builder.py), so the chain
  requires no production data.
* The nondeterministic ``generated`` timestamp of latest.json is
  only checked for existence and format, never for its value.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

import src.analysis.reference_builder as reference_builder_module
from src.analysis.reference_builder import ReferenceBuilder
from src.analysis.region_analyzer import RegionAnalyzer
from src.analysis.results_manager import ResultsManager
from src.config.paths import PROJECT_ROOT

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

EXPECTED_CSV_COLUMNS = [
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

# Persisted rows expected after the chain runs. All values are
# calculated by hand (see the test docstrings):
#
# Observation day 1 (2026-03-01), reference water areas
# 2500 km² (4 pixels) / 625 km² (1 pixel):
#
#   Test Region Water, values 400, 600, 100, 0:
#     ice pixels (>= 150): 400, 600 -> 2 * 625 = 1250 km²,
#     weighted area: (400 + 600) / 1000 * 625 = 625 km²,
#     coverage: 1250 / 2500 = 50 % / 625 / 2500 = 25 %.
#   Test Region Mixed, value 800:
#     ice pixels: 1 -> 625 km²,
#     weighted area: 800 / 1000 * 625 = 500 km²,
#     coverage: 625 / 625 = 100 % / 500 / 625 = 80 %.
#
# Observation day 2 (2026-03-02):
#
#   Test Region Water, values 150, 1000, 0, 200:
#     ice pixels: 150, 1000, 200 -> 3 * 625 = 1875 km²,
#     weighted area: 1350 / 1000 * 625 = 843.75 km²,
#     coverage: 1875 / 2500 = 75 % / 843.75 / 2500 = 33.75 %.
#   Test Region Mixed, value 0:
#     no ice pixels -> 0 km² / 0 km² / 0 % / 0 %.

_DAY_1_MIXED = {
    "region": "Test Region Mixed",
    "date": "2026-03-01",
    "water_pixels": 1,
    "water_area_km2": 625.0,
    "absolute_ice_area_km2": 625.0,
    "relative_ice_area_km2": 500.0,
    "absolute_coverage_percent": 100.0,
    "relative_coverage_percent": 80.0,
    "missing_pixels": 0,
}

_DAY_1_WATER = {
    "region": "Test Region Water",
    "date": "2026-03-01",
    "water_pixels": 4,
    "water_area_km2": 2500.0,
    "absolute_ice_area_km2": 1250.0,
    "relative_ice_area_km2": 625.0,
    "absolute_coverage_percent": 50.0,
    "relative_coverage_percent": 25.0,
    "missing_pixels": 0,
}

_DAY_2_MIXED = {
    "region": "Test Region Mixed",
    "date": "2026-03-02",
    "water_pixels": 1,
    "water_area_km2": 625.0,
    "absolute_ice_area_km2": 0.0,
    "relative_ice_area_km2": 0.0,
    "absolute_coverage_percent": 0.0,
    "relative_coverage_percent": 0.0,
    "missing_pixels": 0,
}

_DAY_2_WATER = {
    "region": "Test Region Water",
    "date": "2026-03-02",
    "water_pixels": 4,
    "water_area_km2": 2500.0,
    "absolute_ice_area_km2": 1875.0,
    "relative_ice_area_km2": 843.75,
    "absolute_coverage_percent": 75.0,
    "relative_coverage_percent": 33.75,
    "missing_pixels": 0,
}

_FLOAT_COLUMNS = {
    "water_area_km2",
    "absolute_ice_area_km2",
    "relative_ice_area_km2",
    "absolute_coverage_percent",
    "relative_coverage_percent",
}


# ------------------------------------------------------------------
# Controlled naturalearth replacement
# ------------------------------------------------------------------


class _StubGeopandas:
    """geopandas stand-in serving a controlled ocean dataset."""

    def __init__(self, ocean: gpd.GeoDataFrame) -> None:
        self._ocean = ocean

    def read_file(self, path) -> gpd.GeoDataFrame:
        return self._ocean

    def __getattr__(self, name):
        return getattr(gpd, name)


# ------------------------------------------------------------------
# Chain fixture
# ------------------------------------------------------------------


@pytest.fixture
def chain_environment(
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Path]:
    """Isolate the complete spatial chain in the test environment.

    Redirects the ReferenceBuilder module constants (filter
    directory and summary path) to the isolated output directory
    and replaces the naturalearth ocean dataset with a controlled
    ocean polygon covering the polar extent of the synthetic
    regions, so that no production data is read or written.
    """
    reference_dir = test_environment["output"] / "reference"
    mask_dir = reference_dir / "filters"
    summary_file = reference_dir / "reference_summary.json"

    monkeypatch.setattr(
        reference_builder_module,
        "FILTER_DIR",
        mask_dir,
    )
    monkeypatch.setattr(
        reference_builder_module,
        "REFERENCE_SUMMARY",
        summary_file,
    )

    ocean = gpd.GeoDataFrame(
        geometry=[
            Polygon(
                [(-180, 80), (180, 80), (180, 90), (-180, 90)],
            )
        ],
        crs="EPSG:4326",
    )
    monkeypatch.setattr(
        reference_builder_module,
        "gpd",
        _StubGeopandas(ocean),
    )

    analysis_dir = test_environment["output"] / "analysis"

    return {
        "mask_dir": mask_dir,
        "reference_json": summary_file,
        "csv": analysis_dir / "ice_coverage_summary.csv",
        "latest": analysis_dir / "latest.json",
    }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _write_observation(
    data_dir: Path,
    filename: str,
    values: dict[int, int],
) -> Path:
    """Write a controlled daily observation GeoTIFF.

    The raster matches the geometry of the synthetic reference
    raster (5 x 5 pixels, EPSG:3411, 25 km pixels). ``values``
    maps flat pixel indices to concentration values on the 0-1000
    scale; all other pixels carry the land code 2510.
    """
    data = np.full((5, 5), 2510, dtype=np.uint16)

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
        "height": 5,
        "width": 5,
        "count": 1,
        "dtype": data.dtype,
        "crs": "EPSG:3411",
        "transform": transform,
    }

    path = data_dir / filename

    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data, 1)

    return path


def _region_values(
    expected_reference_masks: dict[str, np.ndarray],
    water_values: list[int],
    mixed_values: list[int],
) -> dict[int, int]:
    """Map per-region concentration values to flat pixel indices."""
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


def _build_reference(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
) -> None:
    """Run the real ReferenceBuilder (against the patched paths)."""
    ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    ).build()


def _analyze(
    chain_environment: dict[str, Path],
    observation: Path,
) -> dict:
    """Run the real RegionAnalyzer on the built reference products."""
    return RegionAnalyzer(
        input_tif=observation,
        reference_json=chain_environment["reference_json"],
        filter_dir=chain_environment["mask_dir"],
    ).analyze()


def _make_manager(
    chain_environment: dict[str, Path],
) -> ResultsManager:
    """Create a ResultsManager on the isolated persistence paths."""
    return ResultsManager(
        csv_path=chain_environment["csv"],
        latest_json_path=chain_environment["latest"],
    )


def _assert_row(
    df: pd.DataFrame,
    position: int,
    expected: dict,
) -> None:
    """Assert one persisted CSV row against an expected record."""
    row = df.iloc[position]

    for column, value in expected.items():
        if column in _FLOAT_COLUMNS:
            assert row[column] == pytest.approx(value)
        else:
            assert row[column] == value


def _file_snapshot(path: Path) -> bytes | None:
    """Read a file's bytes for a before/after comparison."""
    if not path.exists():
        return None
    return path.read_bytes()


def _directory_snapshot(directory: Path) -> list[str]:
    """List a directory's entries for a before/after comparison."""
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.iterdir())


# ------------------------------------------------------------------
# Task: create a controlled reference raster and run the
# ReferenceBuilder
# ------------------------------------------------------------------


def test_reference_products_are_controlled_and_reproducible(
    chain_environment: dict[str, Path],
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """The real ReferenceBuilder builds the reference products.

    Independent expectations for the 5 x 5 reference raster with
    25 km pixels:

    * Test Region Water: 4 polygon pixels, all water
      -> mask indices [0, 1, 5, 6],
         water area = 4 * 625 km² = 2500 km²,
    * Test Region Mixed: 3 polygon pixels, 1 water pixel
      -> mask indices [2], water area = 625 km².

    A second run rebuilds identical artifacts (acceptance
    criterion: intermediate artifacts are controlled and
    reproducible).
    """
    summary_texts = []

    for _ in range(2):
        _build_reference(
            synthetic_reference_raster,
            synthetic_region_file,
        )

        for (
            region,
            expected_indices,
        ) in expected_reference_masks.items():
            mask_file = (
                chain_environment["mask_dir"] / f"{region}_water.npy"
            )
            assert mask_file.exists()
            assert np.array_equal(np.load(mask_file), expected_indices)

        summary_texts.append(
            chain_environment["reference_json"].read_text(
                encoding="utf-8",
            ),
        )

    summary = json.loads(summary_texts[0])

    assert summary["Test Region Water"]["water_pixels"] == 4
    assert summary["Test Region Water"]["water_area_pixel_km2"] == (
        2500.0
    )
    assert summary["Test Region Mixed"]["water_pixels"] == 1
    assert summary["Test Region Mixed"]["water_area_pixel_km2"] == (
        625.0
    )

    # The rebuild is reproducible down to the file content.
    assert summary_texts[0] == summary_texts[1]


# ------------------------------------------------------------------
# Task: create controlled observation GeoTIFFs and run the
# RegionAnalyzer
# ------------------------------------------------------------------


def test_analyzer_results_match_independent_calculations(
    chain_environment: dict[str, Path],
    test_environment: dict[str, Path],
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """The RegionAnalyzer consumes the built reference products.

    Observation 2026-03-01 (see module header for the hand
    calculation):

    * Test Region Water (400, 600, 100, 0 on 4 water pixels):
      2 ice pixels -> 1250 km² absolute, 625 km² weighted,
      50 % / 25 % coverage,
    * Test Region Mixed (800 on 1 water pixel):
      1 ice pixel -> 625 km² absolute, 500 km² weighted,
      100 % / 80 % coverage.
    """
    _build_reference(
        synthetic_reference_raster,
        synthetic_region_file,
    )

    observation = _write_observation(
        test_environment["data"],
        "N_20260301_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[400, 600, 100, 0],
            mixed_values=[800],
        ),
    )

    results = _analyze(chain_environment, observation)

    assert set(results) == {
        "Test Region Water",
        "Test Region Mixed",
    }

    water = results["Test Region Water"]

    assert set(water) == EXPECTED_RESULT_KEYS
    assert water["date"] == date(2026, 3, 1)
    assert water["water_pixels"] == 4
    assert water["water_area_km2"] == 2500.0
    assert water["absolute_ice_area_km2"] == pytest.approx(1250.0)
    assert water["relative_ice_area_km2"] == pytest.approx(625.0)
    assert water["absolute_coverage_percent"] == pytest.approx(50.0)
    assert water["relative_coverage_percent"] == pytest.approx(25.0)
    assert water["missing_pixels"] == 0

    mixed = results["Test Region Mixed"]

    assert set(mixed) == EXPECTED_RESULT_KEYS
    assert mixed["date"] == date(2026, 3, 1)
    assert mixed["water_pixels"] == 1
    assert mixed["water_area_km2"] == 625.0
    assert mixed["absolute_ice_area_km2"] == pytest.approx(625.0)
    assert mixed["relative_ice_area_km2"] == pytest.approx(500.0)
    assert mixed["absolute_coverage_percent"] == pytest.approx(100.0)
    assert mixed["relative_coverage_percent"] == pytest.approx(80.0)
    assert mixed["missing_pixels"] == 0


# ------------------------------------------------------------------
# Task: persist results with the ResultsManager and validate the
# final persisted results
# ------------------------------------------------------------------


def test_persisted_results_match_independent_calculations(
    chain_environment: dict[str, Path],
    test_environment: dict[str, Path],
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """The persisted CSV and latest.json match the hand calculation.

    Final persisted results for 2026-03-01, sorted by region
    (see module header):

    * Test Region Mixed: 625 km² / 500 km² / 100 % / 80 %,
    * Test Region Water: 1250 km² / 625 km² / 50 % / 25 %.

    latest.json must describe the latest date with both
    observations; only the format of ``generated`` is checked.
    """
    _build_reference(
        synthetic_reference_raster,
        synthetic_region_file,
    )

    observation = _write_observation(
        test_environment["data"],
        "N_20260301_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[400, 600, 100, 0],
            mixed_values=[800],
        ),
    )

    results = _analyze(chain_environment, observation)

    manager = _make_manager(chain_environment)
    manager.add_results(results)
    manager.save()

    df = pd.read_csv(chain_environment["csv"])

    assert list(df.columns) == EXPECTED_CSV_COLUMNS
    assert len(df) == 2

    _assert_row(df, 0, _DAY_1_MIXED)
    _assert_row(df, 1, _DAY_1_WATER)

    with open(
        chain_environment["latest"],
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    assert payload["dataset"] == "NSIDC G02135"
    assert payload["date"] == "2026-03-01"
    assert payload["observations"] == 2
    assert isinstance(payload["generated"], str)
    assert payload["generated"].endswith("Z")

    assert [record["region"] for record in payload["regions"]] == [
        "Test Region Mixed",
        "Test Region Water",
    ]

    latest_by_region = {
        record["region"]: record for record in payload["regions"]
    }
    assert latest_by_region["Test Region Water"][
        "relative_coverage_percent"
    ] == pytest.approx(25.0)
    assert latest_by_region["Test Region Mixed"][
        "absolute_coverage_percent"
    ] == pytest.approx(100.0)


def test_incremental_processing_preserves_observations(
    chain_environment: dict[str, Path],
    test_environment: dict[str, Path],
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """Incremental processing preserves results without duplicates.

    Day 1 (2026-03-01) is persisted first; a later run adds day 2
    (2026-03-02). Expected final rows, sorted by (date, region):

    1. day 1 Mixed  (625 / 500 km², 100 % / 80 %),
    2. day 1 Water  (1250 / 625 km², 50 % / 25 %),
    3. day 2 Mixed  (0 / 0 km², 0 % / 0 %),
    4. day 2 Water  (1875 / 843.75 km², 75 % / 33.75 %).

    Re-persisting the already processed day 2 must not introduce
    duplicates (keep-last per date/region), and latest.json must
    reflect the newest date.
    """
    _build_reference(
        synthetic_reference_raster,
        synthetic_region_file,
    )

    observation_1 = _write_observation(
        test_environment["data"],
        "N_20260301_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[400, 600, 100, 0],
            mixed_values=[800],
        ),
    )
    observation_2 = _write_observation(
        test_environment["data"],
        "N_20260302_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[150, 1000, 0, 200],
            mixed_values=[0],
        ),
    )

    # First pipeline run: day 1 only.
    manager = _make_manager(chain_environment)
    manager.add_results(
        _analyze(chain_environment, observation_1),
    )
    manager.save()

    # Second pipeline run with a fresh manager instance.
    manager = _make_manager(chain_environment)
    assert manager.is_date_processed(date(2026, 3, 1))
    assert not manager.is_date_processed(date(2026, 3, 2))

    day_2_results = _analyze(chain_environment, observation_2)
    manager.add_results(day_2_results)
    manager.save()

    df = pd.read_csv(chain_environment["csv"])

    assert len(df) == 4

    expected_rows = [
        _DAY_1_MIXED,
        _DAY_1_WATER,
        _DAY_2_MIXED,
        _DAY_2_WATER,
    ]

    for position, expected in enumerate(expected_rows):
        _assert_row(df, position, expected)

    with open(
        chain_environment["latest"],
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    assert payload["date"] == "2026-03-02"
    assert payload["observations"] == 4

    # Third run: re-persisting day 2 introduces no duplicates.
    manager = _make_manager(chain_environment)
    manager.add_results(day_2_results)
    manager.save()

    df = pd.read_csv(chain_environment["csv"])

    assert len(df) == 4
    for position, expected in enumerate(expected_rows):
        _assert_row(df, position, expected)


# ------------------------------------------------------------------
# Acceptance criterion: production data directories are not
# modified
# ------------------------------------------------------------------


def test_production_directories_are_not_modified(
    chain_environment: dict[str, Path],
    test_environment: dict[str, Path],
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """A complete chain run leaves all production directories
    untouched.

    Snapshots of the production reference directory (mask files
    and reference summary) and the production analysis outputs
    (summary CSV and latest.json) are compared before and after a
    full chain run in the isolated environment.
    """
    production_filters = (
        PROJECT_ROOT / "output" / "reference" / "filters"
    )
    production_summary = (
        PROJECT_ROOT / "output" / "reference" / "reference_summary.json"
    )
    production_csv = (
        PROJECT_ROOT
        / "output"
        / "analysis"
        / "ice_coverage_summary.csv"
    )
    production_latest = (
        PROJECT_ROOT / "output" / "analysis" / "latest.json"
    )

    before = {
        "filters": _directory_snapshot(production_filters),
        "summary": _file_snapshot(production_summary),
        "csv": _file_snapshot(production_csv),
        "latest": _file_snapshot(production_latest),
    }

    # Full chain run: reference build, analysis, persistence.
    _build_reference(
        synthetic_reference_raster,
        synthetic_region_file,
    )

    observation = _write_observation(
        test_environment["data"],
        "N_20260301_concentration_v1.0.tif",
        _region_values(
            expected_reference_masks,
            water_values=[400, 600, 100, 0],
            mixed_values=[800],
        ),
    )

    manager = _make_manager(chain_environment)
    manager.add_results(_analyze(chain_environment, observation))
    manager.save()

    assert _directory_snapshot(production_filters) == before["filters"]
    assert _file_snapshot(production_summary) == before["summary"]
    assert _file_snapshot(production_csv) == before["csv"]
    assert _file_snapshot(production_latest) == before["latest"]
