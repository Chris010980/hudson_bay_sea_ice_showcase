"""Component tests for daily calendar construction and interpolation
of the TimeSeriesAnalyzer (issue #21).

The tests verify the construction of the continuous daily regional
calendar and the configured interpolation rules of
``interpolate_calendar``:

* missing calendar days are created,
* gaps within the configured maximum of 14 consecutive days are
  linearly interpolated (method="time"),
* a gap of exactly the configured limit is still interpolated,
* gaps exceeding the configured limit remain unbridged in the
  middle (no crossing of unsupported gaps),
* leap-year dates are handled correctly,
* and multiple regions receive independent calendars.

Expected values are calculated independently as linear day-by-day
interpolation between the surrounding observations.

Note on the limit semantics: pandas fills up to ``limit`` values
per direction (``limit_direction="both"``). The tests therefore
assert the unambiguous core behavior: gaps within the limit are
fully interpolated, and the middle of a gap far exceeding the limit
remains NaN, while the observations bounding the gap keep their
original values.

All inputs are controlled synthetic datasets written to the
isolated test environment; no production data is required. The
tests are deterministic.

The input and output paths are provided by the shared
``timeseries_paths`` fixture in tests/conftest.py, which is
reused by all TimeSeriesAnalyzer component test modules.
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

def _row(region: str, day: date, coverage: float) -> dict:
    """Create a controlled daily observation row.

    ``coverage`` is used for both coverage columns so that expected
    interpolation values remain easy to derive independently.
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


def _build_calendar(
    timeseries_paths: dict[str, Path],
    csv_path: Path,
) -> pd.DataFrame:
    """Load the input CSV and construct the interpolated calendar."""

    analyzer = TimeSeriesAnalyzer(
        csv_path=csv_path,
        output_path=timeseries_paths["timeseries"],
        yearly_output_path=timeseries_paths["yearly"],
        events_output_path=timeseries_paths["events"],
    )

    analyzer.load()
    analyzer.interpolate_calendar()

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
    """Return the coverage value of a single calendar day."""

    row = region_df[
        region_df["date"] == pd.Timestamp(day)
    ]

    assert len(row) == 1

    return row.iloc[0][column]


# ------------------------------------------------------------------
# Task: test missing calendar days
# ------------------------------------------------------------------

def test_missing_calendar_days_are_created(
    timeseries_paths: dict[str, Path],
) -> None:
    """The calendar contains every day between first and last
    observation.

    Observations exist for 2026-01-01, 01-03 and 01-05. The
    resulting calendar contains all five days. The single-day gaps
    are linearly interpolated:

    01-02 = (10 + 20) / 2 = 15 %
    01-04 = (20 + 30) / 2 = 25 %
    """

    csv_path = _write_summary(
        timeseries_paths["csv"],
        [
            _row("Test Region", date(2026, 1, 1), 10.0),
            _row("Test Region", date(2026, 1, 3), 20.0),
            _row("Test Region", date(2026, 1, 5), 30.0),
        ],
    )

    df = _build_calendar(timeseries_paths, csv_path)

    region_df = _region_frame(df, "Test Region")

    assert len(region_df) == 5

    expected_dates = pd.date_range(
        date(2026, 1, 1),
        date(2026, 1, 5),
        freq="D",
    )

    assert list(region_df["date"]) == list(expected_dates)

    assert _coverage(region_df, date(2026, 1, 1)) == 10.0
    assert _coverage(region_df, date(2026, 1, 3)) == 20.0
    assert _coverage(region_df, date(2026, 1, 5)) == 30.0

    # Independent linear interpolation of the missing days.
    assert _coverage(region_df, date(2026, 1, 2)) == pytest.approx(15.0)
    assert _coverage(region_df, date(2026, 1, 4)) == pytest.approx(25.0)

    # Interpolation applies to all numeric columns.
    assert _coverage(
        region_df,
        date(2026, 1, 2),
        column="absolute_coverage_percent",
    ) == pytest.approx(15.0)

    # The region column survives the calendar construction.
    assert (region_df["region"] == "Test Region").all()


# ------------------------------------------------------------------
# Task: test interpolation for gaps within the configured maximum
# ------------------------------------------------------------------

def test_gap_within_maximum_is_interpolated(
    timeseries_paths: dict[str, Path],
) -> None:
    """A gap of 13 missing days is fully interpolated.

    Observations: 2026-01-01 = 10 %, 2026-01-15 = 24 %. The gap
    covers the 13 days in between (below the configured limit of 14)
    and is interpolated linearly with a step of 1 % per day:

    01-02 = 11 %, 01-08 = 17 %, 01-14 = 23 %
    """

    csv_path = _write_summary(
        timeseries_paths["csv"],
        [
            _row("Test Region", date(2026, 1, 1), 10.0),
            _row("Test Region", date(2026, 1, 15), 24.0),
        ],
    )

    df = _build_calendar(timeseries_paths, csv_path)

    region_df = _region_frame(df, "Test Region")

    assert len(region_df) == 15

    assert (
        region_df["relative_coverage_percent"].notna().all()
    )

    assert _coverage(region_df, date(2026, 1, 2)) == pytest.approx(11.0)
    assert _coverage(region_df, date(2026, 1, 8)) == pytest.approx(17.0)
    assert _coverage(region_df, date(2026, 1, 14)) == pytest.approx(23.0)


# ------------------------------------------------------------------
# Task: test interpolation boundaries
# ------------------------------------------------------------------

def test_gap_of_exactly_limit_is_interpolated(
    timeseries_paths: dict[str, Path],
) -> None:
    """A gap of exactly 14 missing days still counts as allowed.

    Observations: 2026-01-01 = 10 %, 2026-01-16 = 40 %. The gap
    covers exactly the 14 days in between (the configured limit)
    and is interpolated linearly with a step of 2 % per day:

    01-02 = 12 %, 01-09 = 26 %, 01-15 = 38 %
    """

    csv_path = _write_summary(
        timeseries_paths["csv"],
        [
            _row("Test Region", date(2026, 1, 1), 10.0),
            _row("Test Region", date(2026, 1, 16), 40.0),
        ],
    )

    df = _build_calendar(timeseries_paths, csv_path)

    region_df = _region_frame(df, "Test Region")

    assert len(region_df) == 16

    assert (
        region_df["relative_coverage_percent"].notna().all()
    )

    assert _coverage(region_df, date(2026, 1, 2)) == pytest.approx(12.0)
    assert _coverage(region_df, date(2026, 1, 9)) == pytest.approx(26.0)
    assert _coverage(region_df, date(2026, 1, 15)) == pytest.approx(38.0)


# ------------------------------------------------------------------
# Task: test gaps exceeding the maximum
# ------------------------------------------------------------------

def test_gap_exceeding_maximum_remains_unbridged(
    timeseries_paths: dict[str, Path],
) -> None:
    """A gap far exceeding the limit is not bridged in the middle.

    Observations: 2026-01-01 = 10 % and 2026-02-10 = 80 % with 39
    missing days in between. The gap exceeds the configured limit
    of 14 consecutive days, so the middle of the gap remains
    without values. The bounding observations keep their original
    values; interpolation does not cross the unsupported gap.
    """

    csv_path = _write_summary(
        timeseries_paths["csv"],
        [
            _row("Test Region", date(2026, 1, 1), 10.0),
            _row("Test Region", date(2026, 2, 10), 80.0),
        ],
    )

    df = _build_calendar(timeseries_paths, csv_path)

    region_df = _region_frame(df, "Test Region")

    # The calendar itself still contains every day.
    assert len(region_df) == 41

    # The middle of the gap remains unbridged.
    assert pd.isna(_coverage(region_df, date(2026, 1, 21)))

    assert region_df["relative_coverage_percent"].isna().sum() > 0

    # The bounding observations keep their original values.
    assert _coverage(region_df, date(2026, 1, 1)) == 10.0
    assert _coverage(region_df, date(2026, 2, 10)) == 80.0


# ------------------------------------------------------------------
# Task: test leap years
# ------------------------------------------------------------------

def test_leap_year_calendar(
    timeseries_paths: dict[str, Path],
) -> None:
    """Leap-year dates are created and interpolated correctly.

    2028 is a leap year: the calendar between 2028-02-27 and
    2028-03-02 contains 2028-02-29, and the 3-day gap is
    interpolated linearly with a step of 5 % per day:

    02-28 = 15 %, 02-29 = 20 %, 03-01 = 25 %

    In the non-leap year 2027, the calendar between 02-27 and 03-01
    contains no 02-29 and the single missing day is interpolated:

    02-28 = 13 %
    """

    csv_path = _write_summary(
        timeseries_paths["csv"],
        [
            _row("Test Region", date(2028, 2, 27), 10.0),
            _row("Test Region", date(2028, 3, 2), 30.0),
        ],
    )

    df = _build_calendar(timeseries_paths, csv_path)

    leap_df = _region_frame(df, "Test Region")

    assert len(leap_df) == 5

    assert _coverage(leap_df, date(2028, 2, 29)) == pytest.approx(20.0)
    assert _coverage(leap_df, date(2028, 2, 28)) == pytest.approx(15.0)
    assert _coverage(leap_df, date(2028, 3, 1)) == pytest.approx(25.0)

    csv_path = _write_summary(
        timeseries_paths["csv"],
        [
            _row("Test Region", date(2027, 2, 27), 10.0),
            _row("Test Region", date(2027, 3, 1), 16.0),
        ],
    )

    df = _build_calendar(timeseries_paths, csv_path)

    nonleap_df = _region_frame(df, "Test Region")

    assert len(nonleap_df) == 3

    assert list(nonleap_df["date"]) == list(
        pd.date_range(date(2027, 2, 27), date(2027, 3, 1), freq="D")
    )

    assert _coverage(nonleap_df, date(2027, 2, 28)) == pytest.approx(13.0)


# ------------------------------------------------------------------
# Task: test multiple regions
# ------------------------------------------------------------------

def test_multiple_regions_receive_independent_calendars(
    timeseries_paths: dict[str, Path],
) -> None:
    """Each region gets its own calendar bounded by its own
    observations, and interpolation stays within the region.

    Region A: 2026-01-01 = 10 %, 01-05 = 30 % (step 5 % per day)
    Region B: 2026-01-03 = 0 %, 01-07 = 40 % (step 10 % per day)

    The regions share the dates 01-03 and 01-05 with different
    values, which must not leak into each other.
    """

    csv_path = _write_summary(
        timeseries_paths["csv"],
        [
            _row("Region A", date(2026, 1, 1), 10.0),
            _row("Region A", date(2026, 1, 5), 30.0),
            _row("Region B", date(2026, 1, 3), 0.0),
            _row("Region B", date(2026, 1, 7), 40.0),
        ],
    )

    df = _build_calendar(timeseries_paths, csv_path)

    assert len(df) == 10

    region_a = _region_frame(df, "Region A")

    assert list(region_a["date"]) == list(
        pd.date_range(date(2026, 1, 1), date(2026, 1, 5), freq="D")
    )

    assert _coverage(region_a, date(2026, 1, 2)) == pytest.approx(15.0)
    assert _coverage(region_a, date(2026, 1, 3)) == pytest.approx(20.0)
    assert _coverage(region_a, date(2026, 1, 4)) == pytest.approx(25.0)

    region_b = _region_frame(df, "Region B")

    assert list(region_b["date"]) == list(
        pd.date_range(date(2026, 1, 3), date(2026, 1, 7), freq="D")
    )

    assert _coverage(region_b, date(2026, 1, 4)) == pytest.approx(10.0)
    assert _coverage(region_b, date(2026, 1, 5)) == pytest.approx(20.0)
    assert _coverage(region_b, date(2026, 1, 6)) == pytest.approx(30.0)

    # Shared dates keep region-specific values (no cross-region
    # interpolation).
    assert _coverage(region_a, date(2026, 1, 3)) == pytest.approx(20.0)
    assert _coverage(region_b, date(2026, 1, 3)) == 0.0

    assert _coverage(region_a, date(2026, 1, 5)) == 30.0
    assert _coverage(region_b, date(2026, 1, 5)) == pytest.approx(20.0)