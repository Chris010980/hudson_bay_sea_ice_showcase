"""Unit tests for the daily calendar reconstruction (#41).

``TimeSeriesAnalyzer.interpolate_calendar()`` rebuilds the
continuous daily index per region and delegates the gap fill
to ``_interpolate_small_gaps`` (docs/testing/test-levels.md,
section 2.2, "calendar reconstruction"). The analyzer's
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


def _observations(rows: list[tuple]) -> pd.DataFrame:
    """Observation rows of (region, day, coverage)."""

    df = pd.DataFrame(
        {
            "region": [row[0] for row in rows],
            "date": pd.to_datetime([row[1] for row in rows]),
        }
    )

    coverage = [float(row[2]) for row in rows]

    for column in (
        "relative_coverage_percent",
        "absolute_coverage_percent",
        "relative_ice_area_km2",
        "absolute_ice_area_km2",
    ):
        df[column] = coverage

    return df


def test_missing_day_is_reconstructed_linearly() -> None:
    """A one-day gap is filled and the region is restored."""

    analyzer = _analyzer(
        _observations(
            [
                ("Region A", "2026-03-01", 50.0),
                ("Region A", "2026-03-03", 70.0),
            ]
        )
    )

    analyzer.interpolate_calendar()

    region_a = analyzer.df[analyzer.df["region"] == "Region A"]

    assert len(region_a) == 3
    assert list(region_a["relative_coverage_percent"]) == [
        50.0,
        60.0,
        70.0,
    ]
    assert region_a["region"].notna().all()


def test_regions_are_reconstructed_independently() -> None:
    """The reconstruction of one region never fills another."""

    analyzer = _analyzer(
        _observations(
            [
                ("Region A", "2026-03-01", 50.0),
                ("Region A", "2026-03-03", 70.0),
                ("Region B", "2026-03-02", 30.0),
            ]
        )
    )

    analyzer.interpolate_calendar()

    region_b = analyzer.df[analyzer.df["region"] == "Region B"]

    assert len(region_b) == 1
    assert region_b["relative_coverage_percent"].item() == 30.0


def test_long_gap_is_not_reconstructed() -> None:
    """A gap beyond the interpolation limit stays missing."""

    rows = [("Region A", "2026-01-01", 10.0)]
    rows += [
        ("Region A", f"2026-01-{day:02d}", 50.0)
        for day in range(18, 21)
    ]

    analyzer = _analyzer(_observations(rows))

    analyzer.interpolate_calendar()

    region_a = analyzer.df[analyzer.df["region"] == "Region A"]

    assert len(region_a) == 20
    assert region_a["relative_coverage_percent"].isna().sum() == 16
