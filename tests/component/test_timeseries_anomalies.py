"""Component tests for the anomalies of the TimeSeriesAnalyzer
(issue #24).

The tests verify ``calculate_anomalies()``, which subtracts the
climatological mean from every observation:

* relative_anomaly_percent  = relative_coverage_percent
                              - relative_climatology_percent
* absolute_anomaly_percent  = absolute_coverage_percent
                              - absolute_climatology_percent

Because the anomalies build on the climatology columns, every
test first runs ``calculate_climatology(1981, 2010)`` exactly as
the production pipeline does. Like the previous component tests,
``interpolate_calendar()`` is never called: anomalies are tested
independently from interpolation.

Verified behaviors:

* the anomaly is the observation minus the climatological mean,
  also for observations outside the reference period (they
  receive the merged climatology),
* observations on month-days without climatology receive NaN,
* positive, negative and zero anomalies match independently
  calculated expected values,
* and absolute and relative anomalies are computed separately
  and are never mixed.

Units: both operands are percentages, so an anomaly is a
difference in percentage points.
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
    so that the anomalies of both quantities can be verified
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


def _anomaly_frame(
    timeseries_paths: dict[str, Path],
    rows: list[dict],
) -> pd.DataFrame:
    """Load a series, calculate the climatology and the anomalies.

    ``interpolate_calendar`` is not called, so the anomalies are
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

    analyzer.calculate_anomalies()

    return analyzer.df


def _region_frame(df: pd.DataFrame, region: str) -> pd.DataFrame:
    """Return one region sorted by date."""

    region_df = df[df["region"] == region].copy()
    region_df.sort_values("date", inplace=True)
    return region_df.reset_index(drop=True)


def _value(
    region_df: pd.DataFrame,
    day: date,
    column: str,
) -> float:
    """Return a value of a single observation day."""

    row = region_df[
        region_df["date"] == pd.Timestamp(day)
    ]

    assert len(row) == 1

    return row.iloc[0][column]


# ------------------------------------------------------------------
# Task: test observation - climatological mean
# ------------------------------------------------------------------

def test_anomaly_is_observation_minus_climatology_mean(
    timeseries_paths: dict[str, Path],
) -> None:
    """The anomaly is the observation minus the climatological mean.

    Month-day 06-15, in-period observations 10, 20, 30 %
    (1981-1983): climatological mean = 60 / 3 = 20 %.

    1981: 10 - 20 = -10
    1982: 20 - 20 =   0
    1983: 30 - 20 = +10

    The out-of-period observation 2015 = 35 % receives the merged
    climatology: 35 - 20 = +15.

    The month-day 05-05 exists only outside the reference period
    (2015 = 44 %), so it has no climatology and its anomaly is
    NaN.
    """

    rows = [
        _row("Test Region", date(1981, 6, 15), 10.0),
        _row("Test Region", date(1982, 6, 15), 20.0),
        _row("Test Region", date(1983, 6, 15), 30.0),
        _row("Test Region", date(2015, 6, 15), 35.0),
        _row("Test Region", date(2015, 5, 5), 44.0),
    ]

    df = _anomaly_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _value(
        region_df,
        date(1981, 6, 15),
        "relative_anomaly_percent",
    ) == pytest.approx(-10.0)

    assert _value(
        region_df,
        date(1982, 6, 15),
        "relative_anomaly_percent",
    ) == pytest.approx(0.0)

    assert _value(
        region_df,
        date(1983, 6, 15),
        "relative_anomaly_percent",
    ) == pytest.approx(10.0)

    # Out-of-period observations receive the merged climatology.
    assert _value(
        region_df,
        date(2015, 6, 15),
        "relative_anomaly_percent",
    ) == pytest.approx(15.0)

    # No climatology -> no anomaly.
    assert pd.isna(_value(
        region_df,
        date(2015, 5, 5),
        "relative_anomaly_percent",
    ))


# ------------------------------------------------------------------
# Task: test positive anomalies
# ------------------------------------------------------------------

def test_positive_anomaly(
    timeseries_paths: dict[str, Path],
) -> None:
    """An observation above the mean produces a positive anomaly.

    Month-day 04-10, in-period observations 12.5 % (1981) and
    27.5 % (1982): climatological mean = 40 / 2 = 20 %.

    The observation 2015 = 41.7 % is above the mean:

    41.7 - 20 = +21.7
    """

    rows = [
        _row("Test Region", date(1981, 4, 10), 12.5),
        _row("Test Region", date(1982, 4, 10), 27.5),
        _row("Test Region", date(2015, 4, 10), 41.7),
    ]

    df = _anomaly_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    anomaly = _value(
        region_df,
        date(2015, 4, 10),
        "relative_anomaly_percent",
    )

    assert anomaly > 0
    assert anomaly == pytest.approx(21.7)


# ------------------------------------------------------------------
# Task: test negative anomalies
# ------------------------------------------------------------------

def test_negative_anomaly(
    timeseries_paths: dict[str, Path],
) -> None:
    """An observation below the mean produces a negative anomaly.

    Month-day 05-05, in-period observations 15 % (1981) and
    25 % (1982): climatological mean = 40 / 2 = 20 %.

    The observation 2015 = 4.8 % is below the mean:

    4.8 - 20 = -15.2
    """

    rows = [
        _row("Test Region", date(1981, 5, 5), 15.0),
        _row("Test Region", date(1982, 5, 5), 25.0),
        _row("Test Region", date(2015, 5, 5), 4.8),
    ]

    df = _anomaly_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    anomaly = _value(
        region_df,
        date(2015, 5, 5),
        "relative_anomaly_percent",
    )

    assert anomaly < 0
    assert anomaly == pytest.approx(-15.2)


# ------------------------------------------------------------------
# Task: test zero anomalies
# ------------------------------------------------------------------

def test_zero_anomaly(
    timeseries_paths: dict[str, Path],
) -> None:
    """An observation equal to the mean produces exactly zero.

    Month-day 07-07 with in-period observations 10 % (1981),
    30 % (1982) and 20 % (1995):

    climatological mean = 60 / 3 = 20 %

    1995: 20 - 20 = 0

    The surrounding observations anchor the mean: -10 (1981)
    and +10 (1982).
    """

    rows = [
        _row("Test Region", date(1981, 7, 7), 10.0),
        _row("Test Region", date(1982, 7, 7), 30.0),
        _row("Test Region", date(1995, 7, 7), 20.0),
    ]

    df = _anomaly_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _value(
        region_df,
        date(1981, 7, 7),
        "relative_anomaly_percent",
    ) == pytest.approx(-10.0)

    assert _value(
        region_df,
        date(1982, 7, 7),
        "relative_anomaly_percent",
    ) == pytest.approx(10.0)

    assert _value(
        region_df,
        date(1995, 7, 7),
        "relative_anomaly_percent",
    ) == 0.0


# ------------------------------------------------------------------
# Task: test absolute coverage anomalies
# ------------------------------------------------------------------

def test_absolute_coverage_anomaly(
    timeseries_paths: dict[str, Path],
) -> None:
    """The absolute anomaly uses the absolute climatology.

    Month-day 07-04 with relative coverage constant at 50 % and
    absolute coverage 100 % (1981), 200 % (1982):

    absolute climatological mean = 300 / 2 = 150 %

    The out-of-period observation 2015 = 120 %:

    absolute anomaly = 120 - 150 = -30
    relative anomaly =  50 -  50 =   0
    """

    rows = [
        _row("Test Region", date(1981, 7, 4), 50.0, 100.0),
        _row("Test Region", date(1982, 7, 4), 50.0, 200.0),
        _row("Test Region", date(2015, 7, 4), 50.0, 120.0),
    ]

    df = _anomaly_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    assert _value(
        region_df,
        date(2015, 7, 4),
        "absolute_anomaly_percent",
    ) == pytest.approx(-30.0)

    # The constant relative coverage produces a zero relative
    # anomaly: the two quantities stay separate.
    assert _value(
        region_df,
        date(2015, 7, 4),
        "relative_anomaly_percent",
    ) == 0.0


# ------------------------------------------------------------------
# Task: test relative coverage anomalies (not mixed)
# ------------------------------------------------------------------

def test_relative_coverage_anomaly_is_not_mixed(
    timeseries_paths: dict[str, Path],
) -> None:
    """The relative anomaly uses the relative climatology.

    Month-day 08-09 with absolute coverage constant at 50 % and
    relative coverage 10 % (1981), 30 % (1982):

    relative climatological mean = 40 / 2 = 20 %

    The out-of-period observation 2015 = 35 %:

    relative anomaly = 35 - 20 = +15
    absolute anomaly = 50 - 50 =   0
    """

    rows = [
        _row("Test Region", date(1981, 8, 9), 10.0, 50.0),
        _row("Test Region", date(1982, 8, 9), 30.0, 50.0),
        _row("Test Region", date(2015, 8, 9), 35.0, 50.0),
    ]

    df = _anomaly_frame(timeseries_paths, rows)

    region_df = _region_frame(df, "Test Region")

    relative_anomaly = _value(
        region_df,
        date(2015, 8, 9),
        "relative_anomaly_percent",
    )

    absolute_anomaly = _value(
        region_df,
        date(2015, 8, 9),
        "absolute_anomaly_percent",
    )

    assert relative_anomaly == pytest.approx(15.0)
    assert absolute_anomaly == 0.0

    # The quantities are never mixed.
    assert relative_anomaly != absolute_anomaly