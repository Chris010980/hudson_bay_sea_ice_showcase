"""Unit tests for the complete-year filter (issue #41).

``TimeSeriesAnalyzer.filter_complete_years()`` keeps only
region-years with a valid observation on every calendar day
(docs/testing/test-levels.md, section 2.2, "complete-year
filtering"), including the leap-year day count. The
dataframe is supplied directly; no file is read or written.
"""

from __future__ import annotations

import pandas as pd

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


def _year_frame(year: int, value: float) -> pd.DataFrame:
    """One region observed on every day of the year."""

    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31")

    return pd.DataFrame(
        {
            "region": "Region A",
            "date": dates,
            "relative_coverage_percent": value,
        }
    )


def test_complete_year_is_kept_incomplete_dropped() -> None:
    """365 valid days qualify; 364 do not (2021, no leap)."""

    complete = _year_frame(2021, 50.0)

    incomplete = _year_frame(2021, 50.0).iloc[:-1].copy()
    incomplete["region"] = "Region B"

    analyzer = _analyzer(
        pd.concat([complete, incomplete], ignore_index=True)
    )

    filtered = analyzer.filter_complete_years()

    assert set(filtered["region"]) == {"Region A"}
    assert len(filtered) == 365


def test_leap_year_requires_366_valid_days() -> None:
    """2020 is a leap year: all 366 days must be valid."""

    analyzer = _analyzer(_year_frame(2020, 40.0))

    filtered = analyzer.filter_complete_years()

    assert len(filtered) == 366


def test_empty_dataframe_returns_empty() -> None:
    """An empty input yields an empty result."""

    analyzer = _analyzer(pd.DataFrame())

    assert analyzer.filter_complete_years().empty
