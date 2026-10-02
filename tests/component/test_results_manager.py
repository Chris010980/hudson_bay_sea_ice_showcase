"""Component tests for the ResultsManager (issue #20).

The tests verify persistence and identification of daily regional
analysis results:

* adding new results,
* date/region identification via ``is_date_processed``,
* duplicate handling (keep last per date/region),
* sorting and persistence,
* latest processed date handling,
* ``latest.json`` generation,
* empty-result handling,
* and incremental addition with preservation of existing
  observations.

The row schema follows the persisted ``ice_coverage_summary.csv``
schema used by the RegionAnalyzer results (consistent with
tests/component/test_data_fixtures.py):

    region, date, water_pixels, water_area_km2,
    absolute_ice_area_km2, relative_ice_area_km2,
    absolute_coverage_percent, relative_coverage_percent,
    missing_pixels

All tests use temporary directories from the test environment
instead of the production output/ directory, following
docs/testing/test-levels.md (section 3.4). All expected values are
calculated independently. The tests are deterministic: the
non-deterministic ``generated`` timestamp of latest.json is only
checked for existence and format, never for its value.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.analysis.results_manager import ResultsManager

EXPECTED_COLUMNS = [
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

PIXEL_AREA_KM2 = 625.0


# ------------------------------------------------------------------
# Helpers and fixtures
# ------------------------------------------------------------------


def _observation(
    region: str,
    obs_date: date,
    water_pixels: int = 4,
    absolute_ice_area_km2: float = 1250.0,
    relative_ice_area_km2: float = 625.0,
) -> dict:
    """Create a controlled regional observation.

    The observation follows the schema of the RegionAnalyzer
    results. Coverage percentages are derived from the controlled
    areas so that all values remain exactly representable.
    """

    water_area_km2 = water_pixels * PIXEL_AREA_KM2

    return {
        "region": region,
        "date": obs_date,
        "water_pixels": water_pixels,
        "water_area_km2": water_area_km2,
        "absolute_ice_area_km2": absolute_ice_area_km2,
        "relative_ice_area_km2": relative_ice_area_km2,
        "absolute_coverage_percent": (
            100.0 * absolute_ice_area_km2 / water_area_km2
        ),
        "relative_coverage_percent": (
            100.0 * relative_ice_area_km2 / water_area_km2
        ),
        "missing_pixels": 0,
    }


@pytest.fixture
def results_paths(test_environment: dict[str, Path]) -> dict[str, Path]:
    """Provide isolated persistence paths for the ResultsManager."""

    analysis_dir = test_environment["output"] / "analysis"

    return {
        "csv": analysis_dir / "ice_coverage_summary.csv",
        "latest": analysis_dir / "latest.json",
    }


def _make_manager(results_paths: dict[str, Path]) -> ResultsManager:
    """Create a ResultsManager with injected controlled paths."""

    return ResultsManager(
        csv_path=results_paths["csv"],
        latest_json_path=results_paths["latest"],
    )


def _read_csv(csv_path: Path) -> pd.DataFrame:
    """Read the persisted summary CSV."""

    return pd.read_csv(csv_path)


# ------------------------------------------------------------------
# Task: test adding new results
# ------------------------------------------------------------------


def test_new_results_are_persisted(
    results_paths: dict[str, Path],
) -> None:
    """New observations are persisted with the documented schema.

    Expected state after saving two regions for 2026-03-15:
    2 rows with the controlled metric values and normalized
    ISO date strings.
    """

    manager = _make_manager(results_paths)

    manager.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 15),
            ),
            "Test Region Mixed": _observation(
                "Test Region Mixed",
                date(2026, 3, 15),
            ),
        }
    )

    manager.save()

    assert results_paths["csv"].exists()

    df = _read_csv(results_paths["csv"])

    assert len(df) == 2
    assert list(df.columns) == EXPECTED_COLUMNS
    assert set(df["region"]) == {
        "Test Region Water",
        "Test Region Mixed",
    }
    assert (df["date"] == "2026-03-15").all()

    water = df[df["region"] == "Test Region Water"].iloc[0]

    assert water["water_pixels"] == 4
    assert water["water_area_km2"] == 2500.0
    assert water["absolute_ice_area_km2"] == 1250.0
    assert water["relative_ice_area_km2"] == 625.0
    assert water["absolute_coverage_percent"] == 50.0
    assert water["relative_coverage_percent"] == 25.0
    assert water["missing_pixels"] == 0


# ------------------------------------------------------------------
# Task: test date/region identification
# ------------------------------------------------------------------


def test_is_date_processed_identifies_persisted_dates(
    results_paths: dict[str, Path],
) -> None:
    """Processed dates are identified by date and persisted state.

    A fresh manager without persisted results identifies no date as
    processed. After persisting 2026-03-15, a reloaded manager
    identifies exactly this date (as date object and as string).
    """

    fresh = _make_manager(results_paths)

    assert not fresh.is_date_processed(date(2026, 3, 15))

    seed = _make_manager(results_paths)

    seed.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 15),
            ),
        }
    )

    seed.save()

    reloaded = _make_manager(results_paths)

    assert reloaded.is_date_processed(date(2026, 3, 15))
    assert reloaded.is_date_processed("2026-03-15")
    assert not reloaded.is_date_processed(date(2026, 3, 16))


# ------------------------------------------------------------------
# Task: test duplicate handling
# ------------------------------------------------------------------


def test_duplicate_date_region_observations_keep_last(
    results_paths: dict[str, Path],
) -> None:
    """Duplicate date/region observations keep the last values.

    Two observations for (2026-03-15, Test Region Water) are added
    with different values. The implementation keeps the last one:
    exactly one row with absolute area 2000 km².
    """

    manager = _make_manager(results_paths)

    manager.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 15),
                absolute_ice_area_km2=1000.0,
                relative_ice_area_km2=500.0,
            ),
        }
    )

    manager.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 15),
                absolute_ice_area_km2=2000.0,
                relative_ice_area_km2=1000.0,
            ),
        }
    )

    manager.save()

    df = _read_csv(results_paths["csv"])

    assert len(df) == 1

    row = df.iloc[0]

    assert row["region"] == "Test Region Water"
    assert row["absolute_ice_area_km2"] == 2000.0
    assert row["relative_ice_area_km2"] == 1000.0
    assert row["absolute_coverage_percent"] == 80.0


# ------------------------------------------------------------------
# Task: test sorting/persistence
# ------------------------------------------------------------------


def test_results_are_sorted_and_persisted(
    results_paths: dict[str, Path],
) -> None:
    """Rows are persisted sorted by date and region.

    Independent expected order (lexicographic ISO dates, regions
    alphabetically):

    2026-03-15 Test Region Mixed
    2026-03-15 Test Region Water
    2026-03-16 Test Region Mixed
    2026-03-16 Test Region Water

    Reloading the persisted state reproduces the same sorted order.
    """

    manager = _make_manager(results_paths)

    manager.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 16),
            ),
        }
    )
    manager.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 15),
            ),
        }
    )
    manager.add_results(
        {
            "Test Region Mixed": _observation(
                "Test Region Mixed",
                date(2026, 3, 16),
            ),
        }
    )
    manager.add_results(
        {
            "Test Region Mixed": _observation(
                "Test Region Mixed",
                date(2026, 3, 15),
            ),
        }
    )

    manager.save()

    expected_order = [
        ("2026-03-15", "Test Region Mixed"),
        ("2026-03-15", "Test Region Water"),
        ("2026-03-16", "Test Region Mixed"),
        ("2026-03-16", "Test Region Water"),
    ]

    df = _read_csv(results_paths["csv"])

    assert list(zip(df["date"], df["region"])) == expected_order

    reloaded = _make_manager(results_paths)

    assert not reloaded.df_existing.empty
    assert len(reloaded.df_existing) == 4

    assert (
        list(
            zip(
                reloaded.df_existing["date"],
                reloaded.df_existing["region"],
            )
        )
        == expected_order
    )


# ------------------------------------------------------------------
# Task: test latest processed date handling
# ------------------------------------------------------------------


def test_latest_processed_date(
    results_paths: dict[str, Path],
) -> None:
    """The latest processed date is derived from the persisted CSV.

    Without a summary: None. With observations for 2026-03-15,
    2026-03-16 and 2026-03-17: 2026-03-17. An existing but empty
    summary contains no processed date.
    """

    fresh = _make_manager(results_paths)

    assert fresh.get_latest_processed_date() is None
    assert not fresh.has_results()

    seed = _make_manager(results_paths)

    for obs_date in (
        date(2026, 3, 15),
        date(2026, 3, 17),
        date(2026, 3, 16),
    ):
        seed.add_results(
            {
                "Test Region Water": _observation(
                    "Test Region Water",
                    obs_date,
                ),
            }
        )

    seed.save()

    reloaded = _make_manager(results_paths)

    assert reloaded.get_latest_processed_date() == date(2026, 3, 17)
    assert reloaded.has_results()

    pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(
        results_paths["csv"],
        index=False,
    )

    empty = _make_manager(results_paths)

    assert empty.get_latest_processed_date() is None
    assert not empty.has_results()


# ------------------------------------------------------------------
# Task: test latest.json
# ------------------------------------------------------------------


def test_latest_json_reflects_persisted_state(
    results_paths: dict[str, Path],
) -> None:
    """latest.json contains the most recent observation date.

    Persisted state: 2026-03-15 (Water) and 2026-03-16 (Mixed and
    Water). Independent expected payload:

    * date: "2026-03-16" (the maximum persisted date)
    * observations: 3 (all persisted rows)
    * regions: only the rows of the latest date, sorted by region
    * generated: timestamp in UTC format (value not asserted)

    The regions entries match the persisted rows of that date.
    """

    manager = _make_manager(results_paths)

    manager.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 15),
            ),
        }
    )
    manager.add_results(
        {
            "Test Region Mixed": _observation(
                "Test Region Mixed",
                date(2026, 3, 16),
            ),
        }
    )
    manager.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 16),
            ),
        }
    )

    manager.save()

    assert results_paths["latest"].exists()

    with open(results_paths["latest"], encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["dataset"] == "NSIDC G02135"
    assert payload["date"] == "2026-03-16"
    assert payload["observations"] == 3

    assert payload["generated"].endswith("Z")

    regions = payload["regions"]

    assert [entry["region"] for entry in regions] == [
        "Test Region Mixed",
        "Test Region Water",
    ]

    for entry in regions:
        assert entry["date"] == "2026-03-16"
        assert entry["absolute_ice_area_km2"] == 1250.0
        assert entry["missing_pixels"] == 0


# ------------------------------------------------------------------
# Task: test empty-result handling
# ------------------------------------------------------------------


def test_empty_result_handling(
    results_paths: dict[str, Path],
) -> None:
    """Saving without results neither creates nor modifies outputs.

    A manager without any results writes no CSV and no latest.json
    and reports no processed date. A manager with persisted state
    but no new results returns the existing state unchanged.
    """

    fresh = _make_manager(results_paths)

    returned = fresh.save()

    assert returned.empty
    assert not results_paths["csv"].exists()
    assert not results_paths["latest"].exists()
    assert fresh.get_latest_processed_date() is None
    assert not fresh.has_results()

    seed = _make_manager(results_paths)

    seed.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 15),
            ),
        }
    )

    seed.save()

    update = _make_manager(results_paths)

    returned = update.save()

    assert len(returned) == 1

    df = _read_csv(results_paths["csv"])

    assert len(df) == 1


# ------------------------------------------------------------------
# Preservation of existing observations (incremental addition)
# ------------------------------------------------------------------


def test_incremental_add_preserves_existing_observations(
    results_paths: dict[str, Path],
) -> None:
    """Adding a new date preserves the persisted historical rows.

    After persisting 2026-03-15 and adding 2026-03-16, the summary
    contains 3 rows: both 2026-03-15 rows keep their original
    values, and latest.json reflects the new latest date.
    """

    seed = _make_manager(results_paths)

    seed.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 15),
                absolute_ice_area_km2=1250.0,
            ),
            "Test Region Mixed": _observation(
                "Test Region Mixed",
                date(2026, 3, 15),
                absolute_ice_area_km2=625.0,
            ),
        }
    )

    seed.save()

    update = _make_manager(results_paths)

    update.add_results(
        {
            "Test Region Water": _observation(
                "Test Region Water",
                date(2026, 3, 16),
                absolute_ice_area_km2=800.0,
                relative_ice_area_km2=400.0,
            ),
        }
    )

    update.save()

    df = _read_csv(results_paths["csv"])

    assert len(df) == 3

    historical = df[df["date"] == "2026-03-15"]

    assert set(historical["region"]) == {
        "Test Region Water",
        "Test Region Mixed",
    }

    water_15 = historical[
        historical["region"] == "Test Region Water"
    ].iloc[0]

    assert water_15["absolute_ice_area_km2"] == 1250.0

    mixed_15 = historical[
        historical["region"] == "Test Region Mixed"
    ].iloc[0]

    assert mixed_15["absolute_ice_area_km2"] == 625.0

    with open(results_paths["latest"], encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["date"] == "2026-03-16"
    assert payload["observations"] == 3

    regions = payload["regions"]

    assert [entry["region"] for entry in regions] == [
        "Test Region Water"
    ]
    assert regions[0]["absolute_ice_area_km2"] == 800.0
