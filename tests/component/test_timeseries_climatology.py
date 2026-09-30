"""Component tests for the daily climatology of the
TimeSeriesAnalyzer (issue #23).

The tests verify ``calculate_climatology(start_year=1981,
end_year=2010)``:

* only observations inside the reference period 1981-2010
  contribute to the climatology (both bounds inclusive),
* observations are grouped by their month-day (``%m-%d``),
* mean and standard deviation match independently calculated
  expected values (sample standard deviation, n-1),
* minimum and maximum match independently calculated values,
* February 29 forms its own month-day group fed only by leap
  years, and dates after February are not shifted between leap
  and non-leap years,
* and absolute and relative coverage remain separate quantities.

The climatology columns are merged onto every row of the same
month-day, including observations outside the reference period
(the basis for later anomaly calculation). Month-days that exist
only outside the reference period receive no climatology (NaN).

Like the moving-average tests, the climatology is tested
independently from interpolation: every input is a complete
daily series that is loaded directly via ``load()``.

Expected values are calculated independently from the
implementation.
"""

from __future__ import annotations

from datetime import date
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
    """Create a controlled daily observation row.

    ``relative`` and ``absolute`` allow separate coverage values
    so that the climatology of both quantities can be verified
    independently. ``absolute`` defaults to ``relative``.
    """

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


def _climatology_frame(
    timeseries_paths: dict[str, Path],
    rows: list[dict],
) -> pd.DataFrame:
    """Load a complete daily series and calculate the climatology.

    ``interpolate_calendar`` is not called, so the climatology is
    tested independently from interpolation.
    """

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

    analyzer.calculate_climatology(
        start_year=1981,
        end_year=2010,
    )

    return analyzer.df


def _region_frame(df: pd.DataFrame, region: str) -> pd.DataFrame:
    """Return one region sorted by date."""

    region_df = df[df["region"] == region].copy()
    region_df.sort_values("date", inplace=True)
    return region_df.reset_index(drop=True)


def _stat(
    region_df: pd.DataFrame,
    day: date,
    column: str,
) -> float:
    """Return a climatology value of a single observation day."""

    row = region_df[
        region_df["date"] == pd.Timestamp(day)
    ]

    assert len(row) == 1

    return row.iloc[0][column]


# ------------------------------------------------------------------
# Task: test reference-period filtering
# ------------------------------------------------------------------

def test_only_reference_period_contributes(
    timeseries_paths: dict[str, Path],
) -> None:
    """Only 1981-2010 observations contribute to the statistics.

    Month-day 07-15 with relative coverage:

    1980 (out): 80 %, 1981 (in): 20 %, 2010 (in): 40 %,
    2011 (out): 90 %

    Expected statistics from the two in-period observations:

    mean = (20 + 40) / 2 = 30 %
    min  = 20 %, max = 40 %
    std  = sqrt(((20-30)^2 + (40-30)^2) / 1) = sqrt(200) ~ 14.1421

    The merged climatology appears on every 07-15 row (including
    1980 and 2011) because the merge is the basis for anomalies.
    The month-day 05-05 of 2015 exists only outside the reference
    period and receives no climatology at all (NaN).
    """

    rows = [
        _row("Test Region", date(1980, 7, 15), 80.0),
        _row("Test Region", date(1981, 7, 15), 20.0),
        _row("Test Region", date(2010, 7, 15), 40.0),
        _row("Test Region", date(2011, 7, 15), 90.0),
        _row("Test Region", date(2015, 5, 5), 33.0),
    ]

    df = _climatology_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _stat(
        region_df, date(1981, 7, 15), "relative_climatology_percent",
    ) == pytest.approx(30.0)

    assert _stat(
        region_df, date(1981, 7, 15), "relative_climatology_min_percent",
    ) == 20.0

    assert _stat(
        region_df, date(1981, 7, 15), "relative_climatology_max_percent",
    ) == 40.0

    assert _stat(
        region_df, date(1981, 7, 15), "relative_climatology_std_percent",
    ) == pytest.approx(14.142136)

    # The merged climatology is attached to every row of the
    # month-day, also outside the reference period.
    for day in (date(1980, 7, 15), date(2011, 7, 15)):
        assert _stat(
            region_df, day, "relative_climatology_percent",
        ) == pytest.approx(30.0)

    # A month-day without in-period observations has no climatology.
    assert pd.isna(_stat(
        region_df, date(2015, 5, 5), "relative_climatology_percent",
    ))


# ------------------------------------------------------------------
# Task: test month-day grouping
# ------------------------------------------------------------------

def test_month_days_are_grouped_separately(
    timeseries_paths: dict[str, Path],
) -> None:
    """Each month-day receives its own statistics.

    01-01: 1981 = 10 %, 1982 = 30 %  ->  mean = 20 %
    01-02: 1981 = 20 %, 1982 = 40 %  ->  mean = 30 %
    """

    rows = [
        _row("Test Region", date(1981, 1, 1), 10.0),
        _row("Test Region", date(1982, 1, 1), 30.0),
        _row("Test Region", date(1981, 1, 2), 20.0),
        _row("Test Region", date(1982, 1, 2), 40.0),
    ]

    df = _climatology_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _stat(
        region_df, date(1981, 1, 1), "relative_climatology_percent",
    ) == pytest.approx(20.0)

    assert _stat(
        region_df, date(1981, 1, 2), "relative_climatology_percent",
    ) == pytest.approx(30.0)


# ------------------------------------------------------------------
# Task: test mean
# ------------------------------------------------------------------

def test_mean_matches_independent_calculation(
    timeseries_paths: dict[str, Path],
) -> None:
    """The mean matches an independently calculated value.

    Month-day 06-15, relative coverage over 1981-1984:
    10, 20, 30, 40 %  ->  mean = 100 / 4 = 25 %

    Absolute coverage: 100, 110, 130, 160 %  ->  mean = 500 / 4
    = 125 %
    """

    rows = [
        _row("Test Region", date(1981, 6, 15), 10.0, 100.0),
        _row("Test Region", date(1982, 6, 15), 20.0, 110.0),
        _row("Test Region", date(1983, 6, 15), 30.0, 130.0),
        _row("Test Region", date(1984, 6, 15), 40.0, 160.0),
    ]

    df = _climatology_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _stat(
        region_df, date(1981, 6, 15), "relative_climatology_percent",
    ) == pytest.approx(25.0)

    assert _stat(
        region_df, date(1981, 6, 15), "absolute_climatology_percent",
    ) == pytest.approx(125.0)


# ------------------------------------------------------------------
# Task: test standard deviation
# ------------------------------------------------------------------

def test_std_matches_independent_calculation(
    timeseries_paths: dict[str, Path],
) -> None:
    """The standard deviation matches an independent calculation.

    Month-day 06-15 over 1981-1984, relative coverage
    10, 20, 30, 40 % with mean 25 %:

    std = sqrt(((10-25)^2 + (20-25)^2 + (30-25)^2 + (40-25)^2) / 3)
        = sqrt((225 + 25 + 25 + 225) / 3)
        = sqrt(500 / 3) ~ 12.9099

    Absolute coverage 100, 110, 130, 160 % with mean 125 %:

    std = sqrt((625 + 225 + 25 + 1225) / 3)
        = sqrt(2100 / 3) ~ 26.4575
    """

    rows = [
        _row("Test Region", date(1981, 6, 15), 10.0, 100.0),
        _row("Test Region", date(1982, 6, 15), 20.0, 110.0),
        _row("Test Region", date(1983, 6, 15), 30.0, 130.0),
        _row("Test Region", date(1984, 6, 15), 40.0, 160.0),
    ]

    df = _climatology_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _stat(
        region_df,
        date(1981, 6, 15),
        "relative_climatology_std_percent",
    ) == pytest.approx(12.909944)

    assert _stat(
        region_df,
        date(1981, 6, 15),
        "absolute_climatology_std_percent",
    ) == pytest.approx(26.457513)


def test_single_observation_has_no_std(
    timeseries_paths: dict[str, Path],
) -> None:
    """A month-day with one observation has an undefined std.

    Month-day 09-20 exists only in 1985 (55 %). The sample
    standard deviation (n-1) of a single value is undefined, so
    the std column is NaN while mean, min and max equal the only
    observation.
    """

    rows = [
        _row("Test Region", date(1985, 9, 20), 55.0),
    ]

    df = _climatology_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert pd.isna(_stat(
        region_df, date(1985, 9, 20), "relative_climatology_std_percent",
    ))

    assert _stat(
        region_df, date(1985, 9, 20), "relative_climatology_percent",
    ) == pytest.approx(55.0)

    assert _stat(
        region_df, date(1985, 9, 20), "relative_climatology_min_percent",
    ) == 55.0

    assert _stat(
        region_df, date(1985, 9, 20), "relative_climatology_max_percent",
    ) == 55.0


# ------------------------------------------------------------------
# Task: test minimum and maximum
# ------------------------------------------------------------------

def test_min_and_max_match_independent_calculation(
    timeseries_paths: dict[str, Path],
) -> None:
    """Minimum and maximum match independently picked values.

    Month-day 12-01 over 1981-1983, relative coverage
    15, 70, 42 %  ->  min = 15 %, max = 70 %

    Absolute coverage 5, 90, 40 %  ->  min = 5 %, max = 90 %
    """

    rows = [
        _row("Test Region", date(1981, 12, 1), 15.0, 5.0),
        _row("Test Region", date(1982, 12, 1), 70.0, 90.0),
        _row("Test Region", date(1983, 12, 1), 42.0, 40.0),
    ]

    df = _climatology_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _stat(
        region_df, date(1981, 12, 1), "relative_climatology_min_percent",
    ) == 15.0

    assert _stat(
        region_df, date(1981, 12, 1), "relative_climatology_max_percent",
    ) == 70.0

    assert _stat(
        region_df, date(1981, 12, 1), "absolute_climatology_min_percent",
    ) == 5.0

    assert _stat(
        region_df, date(1981, 12, 1), "absolute_climatology_max_percent",
    ) == 90.0


# ------------------------------------------------------------------
# Task: test February 29 handling
# ------------------------------------------------------------------

def test_feb_29_forms_its_own_leap_year_group(
    timeseries_paths: dict[str, Path],
) -> None:
    """February 29 is its own month-day, fed only by leap years.

    02-29 observations (leap years within the reference period):
    1984 = 50 %, 1988 = 70 %, 1992 = 30 %

    mean = 150 / 3 = 50 %, min = 30 %, max = 70 %

    Dates after February are grouped by month-day, not by
    day-of-year: 03-01 of the leap year 1984 (11 %) and of the
    non-leap year 1985 (22 %) share one group:

    mean = (11 + 22) / 2 = 16.5 %
    """

    rows = [
        _row("Test Region", date(1984, 2, 29), 50.0),
        _row("Test Region", date(1988, 2, 29), 70.0),
        _row("Test Region", date(1992, 2, 29), 30.0),
        _row("Test Region", date(1984, 3, 1), 11.0),
        _row("Test Region", date(1985, 3, 1), 22.0),
    ]

    df = _climatology_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    for day in (date(1984, 2, 29), date(1988, 2, 29), date(1992, 2, 29)):
        assert _stat(
            region_df, day, "relative_climatology_percent",
        ) == pytest.approx(50.0)

        assert _stat(
            region_df, day, "relative_climatology_min_percent",
        ) == 30.0

        assert _stat(
            region_df, day, "relative_climatology_max_percent",
        ) == 70.0

    # 03-01 of leap and non-leap years belongs to one group.
    assert _stat(
        region_df, date(1984, 3, 1), "relative_climatology_percent",
    ) == pytest.approx(16.5)

    assert _stat(
        region_df, date(1985, 3, 1), "relative_climatology_percent",
    ) == pytest.approx(16.5)


# ------------------------------------------------------------------
# Task: test absolute and relative coverage separately
# ------------------------------------------------------------------

def test_absolute_and_relative_remain_separate(
    timeseries_paths: dict[str, Path],
) -> None:
    """Both quantities receive their own, distinct statistics.

    Month-day 08-01 over 1981-1983:

    relative: 10, 20, 30 %  ->  mean = 20 %, std = 10 %,
                               min = 10 %, max = 30 %
    absolute: 40, 60, 80 %  ->  mean = 60 %, std = 20 %,
                               min = 40 %, max = 80 %

    The two value ranges are disjoint, so a swapped or merged
    calculation cannot pass these assertions.
    """

    rows = [
        _row("Test Region", date(1981, 8, 1), 10.0, 40.0),
        _row("Test Region", date(1982, 8, 1), 20.0, 60.0),
        _row("Test Region", date(1983, 8, 1), 30.0, 80.0),
    ]

    df = _climatology_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _stat(
        region_df, date(1981, 8, 1), "relative_climatology_percent",
    ) == pytest.approx(20.0)

    assert _stat(
        region_df, date(1981, 8, 1), "absolute_climatology_percent",
    ) == pytest.approx(60.0)

    assert _stat(
        region_df, date(1981, 8, 1), "relative_climatology_std_percent",
    ) == pytest.approx(10.0)

    assert _stat(
        region_df, date(1981, 8, 1), "absolute_climatology_std_percent",
    ) == pytest.approx(20.0)

    assert _stat(
        region_df, date(1981, 8, 1), "relative_climatology_min_percent",
    ) == 10.0

    assert _stat(
        region_df, date(1981, 8, 1), "absolute_climatology_min_percent",
    ) == 40.0

    assert _stat(
        region_df, date(1981, 8, 1), "relative_climatology_max_percent",
    ) == 30.0

    assert _stat(
        region_df, date(1981, 8, 1), "absolute_climatology_max_percent",
    ) == 80.0