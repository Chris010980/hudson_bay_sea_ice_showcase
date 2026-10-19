"""Unit tests for the yearly means (issue #41).

``TimeSeriesAnalyzer.calculate_yearly_means()`` aggregates
complete region-years only and stores the linear trend of
the relative annual means (docs/testing/test-levels.md,
section 2.2, "annual statistics"). The dataframe is supplied
directly; no file is read or written.
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


def _year_frame(region: str, year: int, value: float):
    """One region observed on every day of the year."""

    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31")

    df = pd.DataFrame(
        {
            "region": region,
            "date": dates,
        }
    )

    for column in (
        "relative_coverage_percent",
        "absolute_coverage_percent",
        "relative_ice_area_km2",
        "absolute_ice_area_km2",
    ):
        df[column] = value

    return df


def test_yearly_means_use_complete_years_only() -> None:
    """Incomplete region-years do not contribute (2021/2022)."""

    analyzer = _analyzer(
        pd.concat(
            [
                _year_frame("Region A", 2021, 40.0),
                _year_frame("Region A", 2022, 60.0),
                _year_frame("Region B", 2021, 30.0).iloc[:-1],
            ],
            ignore_index=True,
        )
    )

    analyzer.calculate_yearly_means()

    yearly = analyzer.yearly_df

    assert list(yearly["region"]) == ["Region A", "Region A"]
    assert list(yearly["year"]) == [2021, 2022]
    assert list(yearly["relative_mean_coverage_percent"]) == [
        40.0,
        60.0,
    ]


def test_trend_columns_store_the_relative_fit() -> None:
    """Means 40 (2021) and 60 (2022): slope 20, R² = 1."""

    analyzer = _analyzer(
        pd.concat(
            [
                _year_frame("Region A", 2021, 40.0),
                _year_frame("Region A", 2022, 60.0),
            ],
            ignore_index=True,
        )
    )

    analyzer.calculate_yearly_means()

    yearly = analyzer.yearly_df

    assert yearly["relative_mean_trend_slope"].iloc[0] == (
        pytest.approx(20.0)
    )
    assert yearly["relative_mean_trend_intercept"].iloc[0] == (
        pytest.approx(-40380.0)
    )
    assert yearly["relative_mean_trend_r_squared"].iloc[0] == (
        pytest.approx(1.0)
    )


def test_single_year_keeps_nan_trend_columns() -> None:
    """Fewer than two complete years keep NaN trend columns."""

    analyzer = _analyzer(_year_frame("Region A", 2021, 50.0))

    analyzer.calculate_yearly_means()

    yearly = analyzer.yearly_df

    assert len(yearly) == 1
    assert np.isnan(yearly["relative_mean_trend_slope"].iloc[0])


def test_missing_columns_raise_value_error() -> None:
    """A missing input column fails with a ValueError."""

    frame = _year_frame("Region A", 2021, 50.0).drop(
        columns=["relative_ice_area_km2"]
    )

    analyzer = _analyzer(frame)

    with pytest.raises(ValueError):
        analyzer.calculate_yearly_means()


def test_empty_dataframe_yields_empty_yearly_table() -> None:
    """An empty input yields an empty yearly table."""

    analyzer = _analyzer(pd.DataFrame())

    analyzer.calculate_yearly_means()

    assert analyzer.yearly_df.empty
