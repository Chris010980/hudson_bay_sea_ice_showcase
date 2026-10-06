"""Unit tests for the moving-average calculation (issue #97).

``TimeSeriesAnalyzer.calculate_moving_average()`` is tested
here on a small in-memory dataframe per docs/testing/
test-levels.md section 2.2 ("moving-average calculation").
The component suite
(``tests/component/test_timeseries_moving_average.py``) pins
the same calculation through the complete CSV-based component
workflow.

No file is read or written. All tests are deterministic and
require no network access.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.timeseries_analyzer import TimeSeriesAnalyzer


def _frame(values: list[float]) -> pd.DataFrame:
    """Daily observation rows for one region."""

    dates = pd.date_range(
        "2026-01-01",
        periods=len(values),
        freq="D",
    )

    return pd.DataFrame(
        {
            "region": "Test Region",
            "date": dates,
            "relative_coverage_percent": values,
            "absolute_coverage_percent": values,
            "relative_ice_area_km2": values,
            "absolute_ice_area_km2": values,
        }
    )


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


def test_moving_average_smooths_contiguous_values() -> None:
    """The centered mean is computed over the valid segment."""

    analyzer = _analyzer(_frame([10.0, 20.0, 30.0]))

    analyzer.calculate_moving_average(window=1)

    ma = analyzer.df["relative_coverage_percent_ma"]

    assert list(ma) == [15.0, 20.0, 25.0]


def test_moving_average_respects_gap_boundaries() -> None:
    """NaN days separate segments; each is smoothed on its own.

    At a segment boundary the centered window is truncated to
    the available days (``min_periods=1``), so both days of a
    two-day segment average to the segment mean.
    """

    analyzer = _analyzer(_frame([10.0, 20.0, float("nan"), 40.0, 50.0]))

    analyzer.calculate_moving_average(window=1)

    ma = list(analyzer.df["relative_coverage_percent_ma"])

    assert ma[:2] == [15.0, 15.0]
    assert np.isnan(ma[2])
    assert ma[3:] == [45.0, 45.0]
