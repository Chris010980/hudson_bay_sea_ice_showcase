"""Unit tests for the seasonal event-window boundaries.

``TimeSeriesAnalyzer._get_event_window()`` restricts an event
search to the documented season boundaries (break-up: March 16
to September 15; freeze-up: September 16 to March 15 of the
following year). The window logic is a pure function of its
arguments and is tested here at unit level (issue #97); the
event calculation built on it is pinned by the component and
integration suites (finding F-008).

No file is read or written. All tests are deterministic and
require no network access.
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


def _region_frame() -> pd.DataFrame:
    """Daily observations around the 2026/2027 season edges."""

    dates = pd.date_range("2026-03-01", "2027-04-01", freq="D")

    return pd.DataFrame(
        {
            "date": dates,
            "coverage": [50.0] * len(dates),
        }
    )


def test_breakup_window_restricts_to_season() -> None:
    """Break-up searches March 16 to September 15 inclusive."""

    window = _analyzer()._get_event_window(
        df_region=_region_frame(),
        event_year=2026,
        event_type="break-up",
    )

    assert window["date"].min() == pd.Timestamp("2026-03-16")
    assert window["date"].max() == pd.Timestamp("2026-09-15")


def test_freezeup_window_spans_year_boundary() -> None:
    """Freeze-up searches into March 15 of the next year."""

    window = _analyzer()._get_event_window(
        df_region=_region_frame(),
        event_year=2026,
        event_type="freeze-up",
    )

    assert window["date"].min() == pd.Timestamp("2026-09-16")
    assert window["date"].max() == pd.Timestamp("2027-03-15")


def test_dynamic_start_after_season_end_returns_empty() -> None:
    """A dynamic start beyond the window end yields no rows."""

    window = _analyzer()._get_event_window(
        df_region=_region_frame(),
        event_year=2026,
        event_type="break-up",
        start_date=pd.Timestamp("2026-10-01"),
    )

    assert window.empty


def test_event_window_rejects_unknown_event_type() -> None:
    """Unknown event types raise a ValueError."""

    with pytest.raises(ValueError):
        _analyzer()._get_event_window(
            df_region=_region_frame(),
            event_year=2026,
            event_type="melt-down",
        )
