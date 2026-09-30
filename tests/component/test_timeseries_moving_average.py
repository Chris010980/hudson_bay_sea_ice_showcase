"""Component tests for the centered moving average of the
TimeSeriesAnalyzer (issue #22).

The tests verify ``calculate_moving_average(window=3)``, the
documented centered seven-day moving average
(``window_size = 2 * 3 + 1 = 7``):

* interior days average the seven surrounding observations
  (centered window),
* the window extends exactly three days to each side,
* boundary days use the truncated window (``min_periods=1``),
* contiguous valid segments are smoothed independently and days
  without observations receive no moving average,
* all relevant quantities (relative and absolute coverage
  percent and ice areas) are smoothed,
* and the unsmoothed observations are not modified.

Smoothing is tested independently from interpolation: every
input is a complete daily series that is loaded directly via
``load()``; ``interpolate_calendar()`` is never called.

Expected values are calculated independently as arithmetic means
over the documented window.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
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

def _row(region: str, day: date, coverage: float) -> dict:
    """Create a controlled daily observation row.

    ``coverage`` is used for both coverage columns so that expected
    moving-average values remain easy to derive independently.
    """

    return {
        "region": region,
        "date": day.isoformat(),
        "water_pixels": 4,
        "water_area_km2": 2500.0,
        "absolute_ice_area_km2": coverage * 25.0,
        "relative_ice_area_km2": coverage * 12.5,
        "absolute_coverage_percent": coverage,
        "relative_coverage_percent": coverage,
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
        row[column] = np.nan

    return row


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


def _smoothed_frame(
    timeseries_paths: dict[str, Path],
    rows: list[dict],
) -> pd.DataFrame:
    """Load a complete daily series and apply the moving average.

    The series is used exactly as written: ``interpolate_calendar``
    is not called, so smoothing is tested independently from
    interpolation.
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

    analyzer.calculate_moving_average(window=3)

    return analyzer.df


def _region_frame(df: pd.DataFrame, region: str) -> pd.DataFrame:
    """Return one region sorted by date."""

    region_df = df[df["region"] == region].copy()
    region_df.sort_values("date", inplace=True)
    return region_df.reset_index(drop=True)


def _coverage(
    region_df: pd.DataFrame,
    day: date,
    column: str = "relative_coverage_percent",
) -> float:
    """Return the value of a single calendar day."""

    row = region_df[
        region_df["date"] == pd.Timestamp(day)
    ]

    assert len(row) == 1

    return row.iloc[0][column]


def _ma(
    region_df: pd.DataFrame,
    day: date,
) -> float:
    """Return the smoothed relative coverage of a calendar day."""

    return _coverage(
        region_df,
        day,
        column="relative_coverage_percent_ma",
    )


# ------------------------------------------------------------------
# Task: test the centered window
# ------------------------------------------------------------------

def test_centered_window_averages_seven_days(
    timeseries_paths: dict[str, Path],
) -> None:
    """An interior day averages the seven surrounding days.

    Observations 1..9 % on 2026-01-01..01-09. Interior days:

    01-04 = mean(1..7) = 28 / 7 = 4 %
    01-05 = mean(2..8) = 35 / 7 = 5 %
    01-06 = mean(3..9) = 42 / 7 = 6 %
    """

    rows = [
        _row("Test Region", date(2026, 1, day), float(day))
        for day in range(1, 10)
    ]

    df = _smoothed_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert len(region_df) == 9

    assert _ma(region_df, date(2026, 1, 4)) == pytest.approx(4.0)
    assert _ma(region_df, date(2026, 1, 5)) == pytest.approx(5.0)
    assert _ma(region_df, date(2026, 1, 6)) == pytest.approx(6.0)


# ------------------------------------------------------------------
# Task: test the +/- 3 day window
# ------------------------------------------------------------------

def test_window_extends_exactly_three_days_each_side(
    timeseries_paths: dict[str, Path],
) -> None:
    """The window covers exactly three days to each side.

    Constant observations of 10 % on 2026-01-01..01-13 with a
    single spike of 80 % on 01-07. The spike changes the moving
    average only within a distance of three days:

    01-03 (distance 4): mean = 10 %          (spike excluded)
    01-04 (distance 3): (6*10 + 80) / 7 = 20 %
    01-07 (spike):      (6*10 + 80) / 7 = 20 %
    01-10 (distance 3): (6*10 + 80) / 7 = 20 %
    01-11 (distance 4): mean = 10 %          (spike excluded)
    """

    rows = [
        _row(
            "Test Region",
            date(2026, 1, day),
            80.0 if day == 7 else 10.0,
        )
        for day in range(1, 14)
    ]

    df = _smoothed_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _ma(region_df, date(2026, 1, 3)) == pytest.approx(10.0)
    assert _ma(region_df, date(2026, 1, 4)) == pytest.approx(20.0)
    assert _ma(region_df, date(2026, 1, 7)) == pytest.approx(20.0)
    assert _ma(region_df, date(2026, 1, 10)) == pytest.approx(20.0)
    assert _ma(region_df, date(2026, 1, 11)) == pytest.approx(10.0)


# ------------------------------------------------------------------
# Task: test boundary behavior
# ------------------------------------------------------------------

def test_boundary_days_use_truncated_window(
    timeseries_paths: dict[str, Path],
) -> None:
    """Boundary days average the available part of the window.

    Observations 10..70 % on 2026-01-01..01-07. With
    ``min_periods=1`` the window shrinks at the edges of the
    series:

    01-01 = (10 + 20 + 30 + 40) / 4 = 25 %
    01-02 = 150 / 5 = 30 %
    01-03 = 210 / 6 = 35 %
    01-04 = 280 / 7 = 40 %
    01-05 = 270 / 6 = 45 %
    01-06 = 250 / 5 = 50 %
    01-07 = (40 + 50 + 60 + 70) / 4 = 55 %
    """

    rows = [
        _row("Test Region", date(2026, 1, day), float(day * 10))
        for day in range(1, 8)
    ]

    df = _smoothed_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    expected = [25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0]

    for day, value in enumerate(expected, start=1):
        assert _ma(region_df, date(2026, 1, day)) == pytest.approx(value)


# ------------------------------------------------------------------
# Task: test contiguous valid segments
# ------------------------------------------------------------------

def test_contiguous_segments_are_smoothed_independently(
    timeseries_paths: dict[str, Path],
) -> None:
    """Segments of valid days are smoothed independently.

    Segment A: 2026-01-01..01-05 with 10, 20, 30, 40, 50 %.
    Missing:   2026-01-06..01-09 (no observations).
    Segment B: 2026-01-10..01-12 with 50, 40, 30 %.

    Days without observations receive no moving average, and the
    rolling window does not cross the missing block: it is
    truncated at the segment boundaries.

    Segment A (independently computed):

    01-01 = (10 + 20 + 30 + 40) / 4 = 25 %
    01-02 = 150 / 5 = 30 %
    01-03 = 150 / 5 = 30 %
    01-04 = 150 / 5 = 30 %
    01-05 = (20 + 30 + 40 + 50) / 4 = 35 %

    Segment B: mean(50, 40, 30) = 40 % on all three days.
    """

    rows = [
        _row("Test Region", date(2026, 1, 5), 50.0),
        _row("Test Region", date(2026, 1, 1), 10.0),
        _row("Test Region", date(2026, 1, 2), 20.0),
        _row_missing("Test Region", date(2026, 1, 7)),
        _row("Test Region", date(2026, 1, 3), 30.0),
        _row_missing("Test Region", date(2026, 1, 6)),
        _row("Test Region", date(2026, 1, 4), 40.0),
        _row_missing("Test Region", date(2026, 1, 9)),
        _row("Test Region", date(2026, 1, 11), 40.0),
        _row_missing("Test Region", date(2026, 1, 8)),
        _row("Test Region", date(2026, 1, 10), 50.0),
        _row("Test Region", date(2026, 1, 12), 30.0),
    ]

    df = _smoothed_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert len(region_df) == 12

    # Days without observations receive no moving average.
    for day in (6, 7, 8, 9):
        assert pd.isna(_ma(region_df, date(2026, 1, day)))

    # Segment A is smoothed on its own.
    assert _ma(region_df, date(2026, 1, 1)) == pytest.approx(25.0)
    assert _ma(region_df, date(2026, 1, 2)) == pytest.approx(30.0)
    assert _ma(region_df, date(2026, 1, 3)) == pytest.approx(30.0)
    assert _ma(region_df, date(2026, 1, 4)) == pytest.approx(30.0)
    assert _ma(region_df, date(2026, 1, 5)) == pytest.approx(35.0)

    # Segment B is smoothed on its own.
    for day in (10, 11, 12):
        assert _ma(region_df, date(2026, 1, day)) == pytest.approx(40.0)


# ------------------------------------------------------------------
# Task: test all relevant smoothed quantities
# ------------------------------------------------------------------

def test_all_relevant_quantities_are_smoothed(
    timeseries_paths: dict[str, Path],
) -> None:
    """Every documented quantity receives its own _ma column.

    Observations 10, 20, 30 % on 2026-01-01..01-03. With the
    three-day series every window covers the full series, so each
    moving average equals the overall mean:

    relative_coverage_percent_ma = mean(10, 20, 30) = 20 %
    absolute_coverage_percent_ma = 20 %
    absolute_ice_area_km2_ma     = mean(250, 500, 750) = 500
    relative_ice_area_km2_ma     = mean(125, 250, 375) = 250
    """

    rows = [
        _row("Test Region", date(2026, 1, day), float(day * 10))
        for day in range(1, 4)
    ]

    df = _smoothed_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    expected_ma_columns = {
        "relative_coverage_percent_ma": 20.0,
        "absolute_coverage_percent_ma": 20.0,
        "absolute_ice_area_km2_ma": 500.0,
        "relative_ice_area_km2_ma": 250.0,
    }

    for column, expected in expected_ma_columns.items():
        assert column in region_df.columns

        for day in (1, 2, 3):
            assert _coverage(
                region_df,
                date(2026, 1, day),
                column=column,
            ) == pytest.approx(expected)


# ------------------------------------------------------------------
# Task: smoothing does not modify the unsmoothed observations
# ------------------------------------------------------------------

def test_smoothing_preserves_unsmoothed_observations(
    timeseries_paths: dict[str, Path],
) -> None:
    """The original observations survive the smoothing unchanged.

    Observations 10, 20, 40, 80, 160 % on 2026-01-01..01-05.
    The moving average of 01-03 is

    mean(10, 20, 40, 80, 160) = 310 / 5 = 62 %,

    which differs from the observation of 40 % -- while the
    observation columns keep their exact original values.
    """

    rows = [
        _row("Test Region", date(2026, 1, day), value)
        for day, value in enumerate(
            [10.0, 20.0, 40.0, 80.0, 160.0],
            start=1,
        )
    ]

    df = _smoothed_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert list(region_df["date"]) == list(
        pd.date_range(date(2026, 1, 1), date(2026, 1, 5), freq="D")
    )

    assert (region_df["region"] == "Test Region").all()

    assert list(region_df["relative_coverage_percent"]) == [
        10.0, 20.0, 40.0, 80.0, 160.0,
    ]

    assert list(region_df["absolute_coverage_percent"]) == [
        10.0, 20.0, 40.0, 80.0, 160.0,
    ]

    assert list(region_df["absolute_ice_area_km2"]) == [
        250.0, 500.0, 1000.0, 2000.0, 4000.0,
    ]

    assert list(region_df["relative_ice_area_km2"]) == [
        125.0, 250.0, 500.0, 1000.0, 2000.0,
    ]

    # The smoothed value differs from the observation it derives
    # from.
    assert _ma(region_df, date(2026, 1, 3)) == pytest.approx(62.0)