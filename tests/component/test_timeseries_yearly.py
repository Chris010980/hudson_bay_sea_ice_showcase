"""Component tests for complete-year filtering and annual means
of the TimeSeriesAnalyzer (issue #25).

The tests verify ``filter_complete_years()`` and
``calculate_yearly_means()``:

* a complete non-leap year (365 valid days) is included,
* a complete leap year (366 valid days) is included,
* incomplete years are excluded -- both missing rows and days
  without observations (NaN) count as invalid days,
* a leap year with only 365 valid days is not complete,
* annual means of all four quantities match independently
  calculated expected values,
* multiple regions are evaluated independently per region-year,
* and filtering does not modify the underlying dataframe.

The linear trend and R-squared tasks of issue #25 are documented
separately: the calculation currently lives inline in the
plotting code and is not testable as a unit yet (see
tests/FINDINGS.md, F-007).

Like the previous component tests, ``interpolate_calendar()`` is
never called. Expected values are calculated independently.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.analysis.timeseries_analyzer import TimeSeriesAnalyzer

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


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _row(
    region: str,
    day: date,
    relative: float,
    absolute: float | None = None,
) -> dict:
    """Create a controlled daily observation row."""

    if absolute is None:
        absolute = relative

    return {
        "region": region,
        "date": day.isoformat(),
        "water_pixels": 4,
        "water_area_km2": 2500.0,
        "absolute_ice_area_km2": absolute * 25.0,
        "relative_ice_area_km2": relative * 12.5,
        "absolute_coverage_percent": absolute,
        "relative_coverage_percent": relative,
        "missing_pixels": 0,
    }


def _row_missing(region: str, day: date) -> dict:
    """Create a day without observations (all values NaN)."""

    row = _row(region, day, 0.0)

    for column in [
        "water_pixels",
        "water_area_km2",
        "absolute_ice_area_km2",
        "relative_ice_area_km2",
        "absolute_coverage_percent",
        "relative_coverage_percent",
        "missing_pixels",
    ]:
        row[column] = float("nan")

    return row


def _days_rows(
    region: str,
    start: date,
    count: int,
    relative: float,
    absolute: float | None = None,
) -> list[dict]:
    """Create ``count`` consecutive daily rows starting at ``start``."""

    return [
        _row(
            region,
            start + timedelta(days=offset),
            relative,
            absolute,
        )
        for offset in range(count)
    ]


def _write_summary(
    csv_path: Path,
    rows: list[dict],
) -> Path:
    """Write a controlled ice_coverage_summary.csv input file."""

    pd.DataFrame(rows, columns=EXPECTED_COLUMNS).to_csv(
        csv_path,
        index=False,
    )

    return csv_path


def _load_analyzer(
    timeseries_paths: dict[str, Path],
    rows: list[dict],
) -> TimeSeriesAnalyzer:
    """Load a controlled series without interpolation."""

    csv_path = _write_summary(
        timeseries_paths["csv"],
        rows,
    )

    analyzer = TimeSeriesAnalyzer(
        csv_path=csv_path,
        output_path=timeseries_paths["timeseries"],
        yearly_output_path=timeseries_paths["yearly"],
        events_output_path=timeseries_paths["events"],
    )

    analyzer.load()

    return analyzer


def _yearly_row(
    yearly_df: pd.DataFrame,
    region: str,
    year: int,
) -> pd.Series:
    """Return the single yearly-means row of one region-year."""

    row = yearly_df[
        (yearly_df["region"] == region) & (yearly_df["year"] == year)
    ]

    assert len(row) == 1

    return row.iloc[0]


# ------------------------------------------------------------------
# Task: test complete 365-day years
# ------------------------------------------------------------------


def test_complete_365_day_year_is_included(
    timeseries_paths: dict[str, Path],
) -> None:
    """A non-leap year with all 365 valid days is complete.

    2023 is not a leap year: 365 daily observations (constant
    30 %) form a complete year. The filtered frame contains all
    365 days, the underlying dataframe is not modified, and the
    yearly mean equals the constant observation (30 %).
    """

    rows = _days_rows(
        "Test Region",
        date(2023, 1, 1),
        365,
        30.0,
    )

    analyzer = _load_analyzer(timeseries_paths, rows)

    complete = analyzer.filter_complete_years()

    assert len(complete) == 365
    assert (complete["region"] == "Test Region").all()
    assert "year" not in complete.columns

    # The underlying dataframe is not modified by the filter.
    assert len(analyzer.df) == 365
    assert "year" not in analyzer.df.columns

    analyzer.calculate_yearly_means()

    assert len(analyzer.yearly_df) == 1

    row = _yearly_row(analyzer.yearly_df, "Test Region", 2023)

    assert row["relative_mean_coverage_percent"] == pytest.approx(30.0)


# ------------------------------------------------------------------
# Task: test complete 366-day years
# ------------------------------------------------------------------


def test_complete_366_day_year_is_included(
    timeseries_paths: dict[str, Path],
) -> None:
    """A leap year with all 366 valid days is complete.

    2024 is a leap year: 366 daily observations (constant 60 %)
    form a complete year, including February 29.
    """

    rows = _days_rows(
        "Test Region",
        date(2024, 1, 1),
        366,
        60.0,
    )

    analyzer = _load_analyzer(timeseries_paths, rows)

    complete = analyzer.filter_complete_years()

    assert len(complete) == 366

    assert (
        complete["date"] == pd.Timestamp(date(2024, 2, 29))
    ).sum() == 1

    analyzer.calculate_yearly_means()

    assert len(analyzer.yearly_df) == 1

    row = _yearly_row(analyzer.yearly_df, "Test Region", 2024)

    assert row["relative_mean_coverage_percent"] == pytest.approx(60.0)


# ------------------------------------------------------------------
# Task: test incomplete years
# ------------------------------------------------------------------


def test_incomplete_years_are_excluded(
    timeseries_paths: dict[str, Path],
) -> None:
    """Years with fewer valid days than the calendar expects are
    excluded -- for missing rows as well as for NaN days.

    Variant 1: 2023 (expects 365) with only 364 daily rows.
    Variant 2: 2023 with all 365 rows but December 31 without an
    observation (NaN). Both variants are incomplete; the yearly
    means remain empty.
    """

    # Variant 1: one row missing.
    rows = _days_rows(
        "Test Region",
        date(2023, 1, 1),
        364,
        30.0,
    )

    analyzer = _load_analyzer(timeseries_paths, rows)

    assert analyzer.filter_complete_years().empty

    analyzer.calculate_yearly_means()

    assert analyzer.yearly_df.empty

    # Variant 2: full calendar, but one day has no observation.
    rows = _days_rows(
        "Test Region",
        date(2023, 1, 1),
        364,
        30.0,
    ) + [
        _row_missing("Test Region", date(2023, 12, 31)),
    ]

    analyzer = _load_analyzer(timeseries_paths, rows)

    assert analyzer.filter_complete_years().empty

    analyzer.calculate_yearly_means()

    assert analyzer.yearly_df.empty


# ------------------------------------------------------------------
# Task: leap years require 366 daily observations
# ------------------------------------------------------------------


def test_leap_year_requires_all_366_days(
    timeseries_paths: dict[str, Path],
) -> None:
    """A leap year with 365 valid days is not complete.

    2024 (expects 366) with observations from January 1 to
    December 30 (365 days) is incomplete: the leap day would be
    missing from the calendar.
    """

    rows = _days_rows(
        "Test Region",
        date(2024, 1, 1),
        365,
        30.0,
    )

    analyzer = _load_analyzer(timeseries_paths, rows)

    assert analyzer.filter_complete_years().empty

    analyzer.calculate_yearly_means()

    assert analyzer.yearly_df.empty


# ------------------------------------------------------------------
# Task: test annual mean calculation
# ------------------------------------------------------------------


def test_annual_means_match_independent_calculation(
    timeseries_paths: dict[str, Path],
) -> None:
    """The annual means of all four quantities are exact.

    2023 with two value regimes:

    73 days (01-01..03-14):  relative 10 %, absolute 20 %
    292 days (03-15..12-31): relative 50 %, absolute 100 %

    Independent calculations (73 + 292 = 365):

    relative mean = (73*10 + 292*50) / 365 = 15330 / 365 = 42 %
    absolute mean = (73*20 + 292*100) / 365 = 30660 / 365 = 84 %
    rel. ice area = mean(12.5*relative) = 12.5 * 42 = 525 km2
    abs. ice area = mean(25*absolute)  = 25 * 84  = 2100 km2
    """

    rows = _days_rows(
        "Test Region",
        date(2023, 1, 1),
        73,
        10.0,
        20.0,
    ) + _days_rows(
        "Test Region",
        date(2023, 3, 15),
        292,
        50.0,
        100.0,
    )

    assert len(rows) == 365

    analyzer = _load_analyzer(timeseries_paths, rows)

    analyzer.calculate_yearly_means()

    assert len(analyzer.yearly_df) == 1

    row = _yearly_row(analyzer.yearly_df, "Test Region", 2023)

    assert row["relative_mean_coverage_percent"] == pytest.approx(42.0)
    assert row["absolute_mean_coverage_percent"] == pytest.approx(84.0)
    assert row["relative_mean_ice_area_km2"] == pytest.approx(525.0)
    assert row["absolute_mean_ice_area_km2"] == pytest.approx(2100.0)


# ------------------------------------------------------------------
# Task: test multiple regions
# ------------------------------------------------------------------


def test_multiple_regions_are_evaluated_per_region_year(
    timeseries_paths: dict[str, Path],
) -> None:
    """Completeness and means are evaluated per region-year.

    Region A: 2023 complete (30 %), 2024 with only 10 days.
    Region B: 2023 complete (70 %), 2024 complete (50 %).

    Expected yearly records (sorted by region, year):

    Region A / 2023 -> 30 %
    Region B / 2023 -> 70 %
    Region B / 2024 -> 50 %

    Region A / 2024 is incomplete and must not appear.
    """

    rows = (
        _days_rows("Region A", date(2023, 1, 1), 365, 30.0)
        + _days_rows("Region A", date(2024, 1, 1), 10, 55.0)
        + _days_rows("Region B", date(2023, 1, 1), 365, 70.0)
        + _days_rows("Region B", date(2024, 1, 1), 366, 50.0)
    )

    analyzer = _load_analyzer(timeseries_paths, rows)

    analyzer.calculate_yearly_means()

    yearly_df = analyzer.yearly_df

    assert len(yearly_df) == 3

    assert list(yearly_df["region"]) == [
        "Region A",
        "Region B",
        "Region B",
    ]

    assert list(yearly_df["year"]) == [2023, 2023, 2024]

    assert _yearly_row(yearly_df, "Region A", 2023)[
        "relative_mean_coverage_percent"
    ] == pytest.approx(30.0)

    assert _yearly_row(yearly_df, "Region B", 2023)[
        "relative_mean_coverage_percent"
    ] == pytest.approx(70.0)

    assert _yearly_row(yearly_df, "Region B", 2024)[
        "relative_mean_coverage_percent"
    ] == pytest.approx(50.0)

    # The incomplete Region A / 2024 is not part of the result.
    assert (
        (yearly_df["region"] == "Region A")
        & (yearly_df["year"] == 2024)
    ).sum() == 0
