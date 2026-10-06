"""Unit tests for the pure threshold-crossing helpers.

The helpers extracted from
``TimeSeriesAnalyzer._find_threshold_crossing()`` in issue #40
are tested directly at unit level (issue #97; docs/testing/
test-levels.md section 2.2, "Threshold-event logic"). The
behavioral crossing search remains pinned by the component
suite (``tests/component/test_timeseries_threshold_crossing.py``,
finding F-008).

The analyzer instance is constructed with in-memory paths but
no file is read or written; the helpers operate on values and
small dataframes supplied by the tests.

All tests are deterministic and require no network access.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.timeseries_analyzer import TimeSeriesAnalyzer


def _analyzer() -> TimeSeriesAnalyzer:
    """Analyzer instance without any filesystem effect."""

    return TimeSeriesAnalyzer(
        csv_path="summary.csv",
        output_path="timeseries.csv",
        yearly_output_path="yearly.csv",
        events_output_path="events.csv",
    )


def _daily_frame(values: list[float]) -> pd.DataFrame:
    """Consecutive daily rows for one coverage column."""

    dates = pd.date_range(
        "2026-03-01",
        periods=len(values),
        freq="D",
    )

    return pd.DataFrame(
        {
            "date": dates,
            "coverage": values,
        }
    )


def test_crossed_between_detects_downward_crossing() -> None:
    """A fall onto or below the threshold crosses downward."""

    crossed = TimeSeriesAnalyzer._crossed_between(
        20.0, 15.0, 15.0, "down"
    )
    assert crossed is True

    crossed = TimeSeriesAnalyzer._crossed_between(
        20.0, 10.0, 15.0, "down"
    )
    assert crossed is True


def test_crossed_between_detects_upward_crossing() -> None:
    """A rise onto or above the threshold crosses upward."""

    crossed = TimeSeriesAnalyzer._crossed_between(
        10.0, 15.0, 15.0, "up"
    )
    assert crossed is True

    crossed = TimeSeriesAnalyzer._crossed_between(
        10.0, 20.0, 15.0, "up"
    )
    assert crossed is True


def test_crossed_between_rejects_non_crossing_pairs() -> None:
    """Pairs without a crossing in the direction are rejected."""

    crossed = TimeSeriesAnalyzer._crossed_between(
        20.0, 10.0, 15.0, "up"
    )
    assert crossed is False

    crossed = TimeSeriesAnalyzer._crossed_between(
        10.0, 20.0, 15.0, "down"
    )
    assert crossed is False


def test_prepare_crossing_data_sorts_and_drops_invalid_rows() -> None:
    """Invalid rows are dropped; valid rows are sorted."""

    df = pd.DataFrame(
        {
            "date": [
                "2026-03-02",
                "not-a-date",
                "2026-03-01",
            ],
            "coverage": [30.0, float("nan"), 10.0],
        }
    )

    data = TimeSeriesAnalyzer._prepare_crossing_data(
        df,
        "coverage",
    )

    assert data is not None
    assert list(data["coverage"]) == [10.0, 30.0]


def test_prepare_crossing_data_returns_none_when_empty() -> None:
    """A dataframe without valid observations yields None."""

    df = pd.DataFrame(
        {
            "date": ["not-a-date"],
            "coverage": [float("nan")],
        }
    )

    assert (
        TimeSeriesAnalyzer._prepare_crossing_data(df, "coverage")
        is None
    )


def test_persistent_segment_returns_requested_window() -> None:
    """The window starts at the crossing day itself."""

    data = _daily_frame([20.0, 10.0, 9.0, 8.0, 7.0])

    segment = TimeSeriesAnalyzer._persistent_segment(
        data,
        start_idx=1,
        persistence=3,
    )

    assert segment is not None
    assert list(segment["coverage"]) == [10.0, 9.0, 8.0]


def test_persistent_segment_requires_enough_following_days() -> None:
    """A window reaching beyond the data yields None."""

    data = _daily_frame([20.0, 10.0, 9.0])

    segment = TimeSeriesAnalyzer._persistent_segment(
        data,
        start_idx=1,
        persistence=4,
    )

    assert segment is None


def test_segment_is_persistent_requires_consecutive_days() -> None:
    """A gap inside the persistence window rejects it."""

    data = pd.DataFrame(
        {
            "date": [
                pd.Timestamp("2026-03-01"),
                pd.Timestamp("2026-03-02"),
                pd.Timestamp("2026-03-04"),
            ],
            "coverage": [10.0, 9.0, 8.0],
        }
    )

    persistent = TimeSeriesAnalyzer._segment_is_persistent(
        data,
        "coverage",
        15.0,
        "down",
    )

    assert persistent is False


def test_segment_is_persistent_requires_threshold_side() -> None:
    """All window days must remain on the target side."""

    persistent = TimeSeriesAnalyzer._segment_is_persistent(
        _daily_frame([10.0, 9.0, 16.0]),
        "coverage",
        15.0,
        "down",
    )
    # numpy bool_: assert truthiness, not identity
    assert not persistent

    persistent = TimeSeriesAnalyzer._segment_is_persistent(
        _daily_frame([10.0, 9.0, 8.0]),
        "coverage",
        15.0,
        "down",
    )
    assert persistent


def test_find_threshold_crossing_validates_arguments() -> None:
    """Empty input answers None; invalid arguments raise."""

    analyzer = _analyzer()
    empty = pd.DataFrame({"date": [], "coverage": []})

    assert (
        analyzer._find_threshold_crossing(
            df=empty,
            column="coverage",
            threshold=15.0,
            direction="down",
            persistence=7,
        )
        is None
    )

    with pytest.raises(ValueError):
        analyzer._find_threshold_crossing(
            df=_daily_frame([20.0, 10.0]),
            column="coverage",
            threshold=15.0,
            direction="down",
            persistence=0,
        )

    with pytest.raises(ValueError):
        analyzer._find_threshold_crossing(
            df=_daily_frame([20.0, 10.0]),
            column="coverage",
            threshold=15.0,
            direction="sideways",
            persistence=7,
        )
