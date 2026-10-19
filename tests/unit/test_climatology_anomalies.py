"""Unit tests for climatology and anomalies (issue #41).

``TimeSeriesAnalyzer.calculate_climatology()`` and
``calculate_anomalies()`` implement the calendar-day
climatology and the anomaly subtraction (docs/testing/
test-levels.md, section 2.2, "calendar-day climatology" and
"anomaly calculations"). The dataframe is supplied directly;
no file is read or written.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analysis.timeseries_analyzer import TimeSeriesAnalyzer


def _analyzer(df: pd.DataFrame) -> TimeSeriesAnalyzer:
    """Analyzer whose dataframe is supplied directly."""

    analyzer = TimeSeriesAnalyzer(
        csv_path="summary.csv",
        output_path="timeseries.csv",
        yearly_output_path="yearly.csv",
        events_output_path="events.csv",
    )

    analyzer.df = df

    return analyzer


def _frame(rows: list[tuple]) -> pd.DataFrame:
    """Observation rows of (day, coverage) for one region."""

    coverage = [float(row[1]) for row in rows]

    df = pd.DataFrame(
        {
            "region": "Region A",
            "date": pd.to_datetime([row[0] for row in rows]),
        }
    )

    df["relative_coverage_percent"] = coverage
    df["absolute_coverage_percent"] = coverage

    return df


def test_climatology_averages_matching_calendar_days() -> None:
    """The mean of the window years is stored per month-day."""

    analyzer = _analyzer(
        _frame(
            [
                ("2021-03-01", 40.0),
                ("2022-03-01", 60.0),
            ]
        )
    )

    analyzer.calculate_climatology(
        start_year=2021,
        end_year=2022,
    )

    df = analyzer.df

    assert list(df["relative_climatology_percent"]) == [
        50.0,
        50.0,
    ]
    assert list(df["relative_climatology_min_percent"]) == [
        40.0,
        40.0,
    ]
    assert list(df["relative_climatology_max_percent"]) == [
        60.0,
        60.0,
    ]

    std = df["relative_climatology_std_percent"]

    assert std.iloc[0] == pytest.approx(np.sqrt(200.0))


def test_days_outside_the_window_reuse_the_climatology() -> None:
    """Days outside the window receive the window statistics.

    The 2021-2022 window restricts which observations build
    the climatology; the merged statistics are attached to
    every row so that anomalies can be computed outside the
    window as well. A calendar day seen once has a NaN
    standard deviation.
    """

    analyzer = _analyzer(
        _frame(
            [
                ("2021-03-01", 40.0),
                ("2023-03-01", 80.0),
            ]
        )
    )

    analyzer.calculate_climatology(
        start_year=2021,
        end_year=2022,
    )

    df = analyzer.df

    assert list(df["relative_climatology_percent"]) == [
        40.0,
        40.0,
    ]
    assert list(df["relative_climatology_min_percent"]) == [
        40.0,
        40.0,
    ]
    assert list(df["relative_climatology_max_percent"]) == [
        40.0,
        40.0,
    ]
    assert df["relative_climatology_std_percent"].isna().all()


def test_anomalies_subtract_the_climatology() -> None:
    """The anomaly is the value minus the climatological mean."""

    analyzer = _analyzer(
        _frame(
            [
                ("2021-03-01", 40.0),
                ("2022-03-01", 60.0),
            ]
        )
    )

    analyzer.calculate_climatology(
        start_year=2021,
        end_year=2022,
    )

    analyzer.calculate_anomalies()

    assert list(analyzer.df["relative_anomaly_percent"]) == [
        -10.0,
        10.0,
    ]
    assert list(analyzer.df["absolute_anomaly_percent"]) == [
        -10.0,
        10.0,
    ]


def test_leap_day_forms_its_own_calendar_group() -> None:
    """February 29 groups under its own month-day key."""

    analyzer = _analyzer(
        _frame(
            [
                ("2020-02-29", 100.0),
                ("2021-03-01", 40.0),
            ]
        )
    )

    analyzer.calculate_climatology(
        start_year=2020,
        end_year=2021,
    )

    df = analyzer.df

    assert list(df["month_day"]) == ["02-29", "03-01"]
    assert df["relative_climatology_percent"].iloc[0] == 100.0
    assert df["relative_climatology_percent"].iloc[1] == 40.0
