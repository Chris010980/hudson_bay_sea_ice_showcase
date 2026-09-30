"""Component tests for the seasonal event windows and the
persistence requirement of the TimeSeriesAnalyzer (issue #27).

The tests verify ``calculate_threshold_events()`` with the
production defaults (thresholds 10/50/90 %, persistence 7 days)
over the full seasonal pipeline:

* break-up (downward crossing) is searched between March 16 and
  September 15 of the event year,
* freeze-up (upward crossing) is searched between September 16
  and March 15 of the following year,
* the crossing day itself counts as the first persistence day;
  seven consecutive calendar days must remain on the target side,
* a freeze-up event is only meaningful after a corresponding
  break-up of the same threshold,
* if the threshold is already reached on September 16, the
  freeze-up search is extended backwards to the day after the
  break-up event (dynamic window adjustment),
* and freeze-up dates in the following calendar year belong to
  the event year of their season.

Test design: every crossing lands exactly on its threshold
(e.g. a drop from 80 % to exactly 50 %), so the expected event
dates are exact calendar days -- the interpolation mathematics
itself is covered by issue #26. The inputs use the minimal
schema the event calculation consumes (region, date,
relative_coverage_percent). All tests are deterministic.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.analysis.timeseries_analyzer import TimeSeriesAnalyzer


EXPECTED_COLUMNS = [
    "region",
    "date",
    "relative_coverage_percent",
]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _timeline(
    pieces: list[tuple[date, int, float]],
    region: str = "Test Region",
) -> list[dict]:
    """Create constant-value daily segments.

    Each piece is ``(start, days, value)``: ``days`` consecutive
    daily rows starting at ``start`` with a constant coverage
    value.
    """

    rows = []

    for start, days, value in pieces:
        for offset in range(days):
            rows.append(
                {
                    "region": region,
                    "date": (
                        start + timedelta(days=offset)
                    ).isoformat(),
                    "relative_coverage_percent": value,
                }
            )

    return rows


def _events_frame(
    timeseries_paths: dict[str, Path],
    rows: list[dict],
) -> pd.DataFrame:
    """Load a controlled series and calculate the threshold events.

    ``calculate_threshold_events()`` is called with the production
    defaults: thresholds (10, 50, 90) %, persistence 7 days,
    column relative_coverage_percent.
    """

    csv_path = timeseries_paths["csv"]

    pd.DataFrame(rows, columns=EXPECTED_COLUMNS).to_csv(
        csv_path,
        index=False,
    )

    analyzer = TimeSeriesAnalyzer(
        csv_path=csv_path,
        output_path=timeseries_paths["timeseries"],
        yearly_output_path=timeseries_paths["yearly"],
        events_output_path=timeseries_paths["events"],
    )

    analyzer.load()

    return analyzer.calculate_threshold_events()


def _event(
    events_df: pd.DataFrame,
    region: str,
    event_year: int,
    event_type: str,
    threshold: float,
) -> pd.Timestamp | None:
    """Return the event date of one unique event record."""

    row = events_df[
        (events_df["region"] == region)
        & (events_df["event_year"] == event_year)
        & (events_df["event_type"] == event_type)
        & (events_df["threshold_percent"] == threshold)
    ]

    assert len(row) == 1

    return row.iloc[0]["event_date"]


def _assert_no_event(
    result: pd.Timestamp | None,
) -> None:
    """Assert that no event was found."""

    assert result is None or pd.isna(result)


# ------------------------------------------------------------------
# Task: test seven consecutive calendar days
# ------------------------------------------------------------------

def test_seven_consecutive_days_are_required(
    timeseries_paths: dict[str, Path],
) -> None:
    """Exactly seven qualifying days satisfy the persistence
    requirement; six do not.

    Case 1: 80 % until 03-20, exactly 50 % on 03-21, 40 % on
    03-22..03-27 (7 consecutive days at or below 50 %), back to
    80 % on 03-28. The break-up is accepted: 2026-03-21.

    Case 2: like case 1, but only six qualifying days
    (03-21..03-26); the series returns to 80 % on 03-27.
    No break-up is accepted.
    """

    # Case 1: exactly seven qualifying days.
    rows = _timeline(
        [
            (date(2026, 1, 1), 79, 80.0),   # 01-01 .. 03-20
            (date(2026, 3, 21), 1, 50.0),   # 03-21 (exact)
            (date(2026, 3, 22), 6, 40.0),   # 03-22 .. 03-27
            (date(2026, 3, 28), 1, 80.0),   # 03-28
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    # One record per threshold and event type.
    assert len(events) == 6

    assert _event(
        events, "Test Region", 2026, "break-up", 50.0,
    ) == pd.Timestamp(2026, 3, 21)

    # Case 2: only six qualifying days.
    rows = _timeline(
        [
            (date(2026, 1, 1), 79, 80.0),   # 01-01 .. 03-20
            (date(2026, 3, 21), 1, 50.0),   # 03-21 (exact)
            (date(2026, 3, 22), 5, 40.0),   # 03-22 .. 03-26
            (date(2026, 3, 27), 4, 80.0),   # 03-27 .. 03-30
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    _assert_no_event(_event(
        events, "Test Region", 2026, "break-up", 50.0,
    ))


# ------------------------------------------------------------------
# Task: test persistence failure
# ------------------------------------------------------------------

def test_persistence_failure_yields_no_event(
    timeseries_paths: dict[str, Path],
) -> None:
    """A crossing whose persistence window is violated is not an
    event -- and a later persistent crossing is still found.

    Case 1: the drop to 50 % on 03-21 is followed by a return to
    60 % on 03-24 (inside the persistence window); the series
    stays at 60 %. No break-up is accepted.

    Case 2: the first drop (03-21) fails the persistence check,
    but a second drop to exactly 50 % on 03-27 persists for
    seven days (03-27..04-02). The break-up is accepted as
    2026-03-27 -- the failed crossing does not block the search.
    """

    # Case 1: values return above the threshold too early.
    rows = _timeline(
        [
            (date(2026, 1, 1), 79, 80.0),   # 01-01 .. 03-20
            (date(2026, 3, 21), 1, 50.0),   # 03-21 (exact)
            (date(2026, 3, 22), 2, 40.0),   # 03-22 .. 03-23
            (date(2026, 3, 24), 70, 60.0),  # 03-24 .. 06-01
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    _assert_no_event(_event(
        events, "Test Region", 2026, "break-up", 50.0,
    ))

    # Case 2: the first crossing fails, a later one persists.
    rows = _timeline(
        [
            (date(2026, 1, 1), 79, 80.0),   # 01-01 .. 03-20
            (date(2026, 3, 21), 1, 50.0),   # 03-21 (exact)
            (date(2026, 3, 22), 2, 40.0),   # 03-22 .. 03-23
            (date(2026, 3, 24), 3, 60.0),   # 03-24 .. 03-26
            (date(2026, 3, 27), 1, 50.0),   # 03-27 (exact)
            (date(2026, 3, 28), 9, 40.0),   # 03-28 .. 04-05
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    assert _event(
        events, "Test Region", 2026, "break-up", 50.0,
    ) == pd.Timestamp(2026, 3, 27)


# ------------------------------------------------------------------
# Task: test the break-up search window
# ------------------------------------------------------------------

def test_breakup_is_restricted_to_its_window(
    timeseries_paths: dict[str, Path],
) -> None:
    """Only crossings between March 16 and September 15 count
    as break-up.

    Case 1: the persistent drop to 50 % happens on 03-10, before
    the window starts on 03-16. The window itself only contains
    values already below the threshold: no break-up.

    Case 2: the series stays at 80 % until 09-20 and drops to
    50 % on 09-21, after the window ends on 09-15: no break-up.
    """

    # Case 1: drop before the window starts.
    rows = _timeline(
        [
            (date(2026, 1, 1), 68, 80.0),    # 01-01 .. 03-09
            (date(2026, 3, 10), 1, 50.0),   # 03-10 (exact)
            (date(2026, 3, 11), 188, 40.0), # 03-11 .. 09-15
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    _assert_no_event(_event(
        events, "Test Region", 2026, "break-up", 50.0,
    ))

    # Case 2: drop after the window ends.
    rows = _timeline(
        [
            (date(2026, 1, 1), 263, 80.0),  # 01-01 .. 09-20
            (date(2026, 9, 21), 1, 50.0),  # 09-21 (exact)
            (date(2026, 9, 22), 9, 40.0),  # 09-22 .. 09-30
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    _assert_no_event(_event(
        events, "Test Region", 2026, "break-up", 50.0,
    ))


# ------------------------------------------------------------------
# Task: test the freeze-up search window (inside)
# ------------------------------------------------------------------

def test_freezeup_is_detected_within_its_window(
    timeseries_paths: dict[str, Path],
) -> None:
    """A rise inside the freeze-up window is a freeze-up event.

    Season 2026: break-up on 03-21 (80 -> 50 -> 40 %), values
    stay at 40 % until 10-17, rise to exactly 50 % on 10-18 and
    to 60 % on 10-19..10-24 (seven consecutive days at or above
    50 % since 10-18).

    The freeze-up window starts on 09-16 (the value on 09-16 is
    40 %, below the threshold). Expected freeze-up: 2026-10-18.
    """

    rows = _timeline(
        [
            (date(2026, 1, 1), 79, 80.0),    # 01-01 .. 03-20
            (date(2026, 3, 21), 1, 50.0),   # 03-21 (exact)
            (date(2026, 3, 22), 210, 40.0), # 03-22 .. 10-17
            (date(2026, 10, 18), 1, 50.0),  # 10-18 (exact)
            (date(2026, 10, 19), 6, 60.0),  # 10-19 .. 10-24
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    assert _event(
        events, "Test Region", 2026, "break-up", 50.0,
    ) == pd.Timestamp(2026, 3, 21)

    assert _event(
        events, "Test Region", 2026, "freeze-up", 50.0,
    ) == pd.Timestamp(2026, 10, 18)


# ------------------------------------------------------------------
# Task: test the freeze-up search window (outside)
# ------------------------------------------------------------------

def test_freezeup_after_window_end_is_ignored(
    timeseries_paths: dict[str, Path],
) -> None:
    """A rise after March 15 of the following year is outside
    the freeze-up window and is ignored.

    Season 2026: break-up on 03-21, values stay at 40 % until
    03-17 of 2027, rise to exactly 50 % on 03-18 -- after the
    freeze-up window of the 2026 season ends on 03-15/2027.
    No freeze-up is accepted for the 2026 season.
    """

    rows = _timeline(
        [
            (date(2026, 1, 1), 79, 80.0),    # 01-01 .. 03-20
            (date(2026, 3, 21), 1, 50.0),   # 03-21 (exact)
            (date(2026, 3, 22), 361, 40.0), # 03-22 .. 03-17/27
            (date(2027, 3, 18), 1, 50.0),   # 03-18 (exact)
            (date(2027, 3, 19), 6, 60.0),   # 03-19 .. 03-24/27
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    assert _event(
        events, "Test Region", 2026, "break-up", 50.0,
    ) == pd.Timestamp(2026, 3, 21)

    _assert_no_event(_event(
        events, "Test Region", 2026, "freeze-up", 50.0,
    ))


# ------------------------------------------------------------------
# Task: test the freeze-up / break-up dependency
# ------------------------------------------------------------------

def test_freezeup_requires_preceding_breakup(
    timeseries_paths: dict[str, Path],
) -> None:
    """Without a break-up there is no meaningful freeze-up.

    The series never exceeds 50 % during the break-up window
    (constant 40 %), so no break-up exists. The rise on 10-16
    inside the nominal freeze-up window does not produce a
    freeze-up event.
    """

    rows = _timeline(
        [
            (date(2026, 1, 1), 288, 40.0),  # 01-01 .. 10-15
            (date(2026, 10, 16), 1, 50.0),  # 10-16 (exact)
            (date(2026, 10, 17), 14, 60.0), # 10-17 .. 10-30
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    _assert_no_event(_event(
        events, "Test Region", 2026, "break-up", 50.0,
    ))

    _assert_no_event(_event(
        events, "Test Region", 2026, "freeze-up", 50.0,
    ))


# ------------------------------------------------------------------
# Task: test the freeze-up year transition
# ------------------------------------------------------------------

def test_freezeup_year_transition(
    timeseries_paths: dict[str, Path],
) -> None:
    """A freeze-up in the following calendar year belongs to the
    event year of its season.

    Season 2026: break-up on 03-21, values stay at 40 % through
    2026 and until 01-09/2027, rise to exactly 50 % on 01-10/2027
    and to 60 % until 03-15/2027 (seven qualifying days from
    01-10).

    The freeze-up record carries event_year 2026 with an event
    date in 2027: 2027-01-10.
    """

    rows = _timeline(
        [
            (date(2026, 1, 1), 79, 80.0),    # 01-01 .. 03-20
            (date(2026, 3, 21), 1, 50.0),   # 03-21 (exact)
            (date(2026, 3, 22), 285, 40.0), # 03-22 .. 12-31
            (date(2027, 1, 1), 9, 40.0),   # 01-01 .. 01-09
            (date(2027, 1, 10), 1, 50.0),  # 01-10 (exact)
            (date(2027, 1, 11), 64, 60.0), # 01-11 .. 03-15
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    freezeup = _event(
        events, "Test Region", 2026, "freeze-up", 50.0,
    )

    assert freezeup == pd.Timestamp(2027, 1, 10)

    # The following-year date is represented in the 2026 season.
    assert freezeup.year == 2027


# ------------------------------------------------------------------
# Task: test the dynamic freeze-up search adjustment
# ------------------------------------------------------------------

def test_dynamic_freezeup_adjustment(
    timeseries_paths: dict[str, Path],
) -> None:
    """A freeze-up before September 16 is found when the
    threshold is already reached on September 16.

    Season 2026: break-up on 03-21, values stay at 40 % until
    08-09, rise to exactly 50 % on 08-10 and to 60 % until the
    end of September (value on 09-16: 60 % >= 50 %).

    Because the threshold is already reached on September 16, the
    freeze-up search is extended backwards to the day after the
    break-up (03-22). The August crossing is inside the extended
    window: freeze-up 2026-08-10. Without the adjustment the
    rise would precede the nominal window start (09-16) and the
    event would be missed.
    """

    rows = _timeline(
        [
            (date(2026, 1, 1), 79, 80.0),    # 01-01 .. 03-20
            (date(2026, 3, 21), 1, 50.0),   # 03-21 (exact)
            (date(2026, 3, 22), 141, 40.0), # 03-22 .. 08-09
            (date(2026, 8, 10), 1, 50.0),   # 08-10 (exact)
            (date(2026, 8, 11), 51, 60.0),  # 08-11 .. 09-30
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    assert _event(
        events, "Test Region", 2026, "break-up", 50.0,
    ) == pd.Timestamp(2026, 3, 21)

    assert _event(
        events, "Test Region", 2026, "freeze-up", 50.0,
    ) == pd.Timestamp(2026, 8, 10)


# ------------------------------------------------------------------
# Task: test persistence independently for each threshold
# ------------------------------------------------------------------

def test_persistence_is_independent_per_threshold(
    timeseries_paths: dict[str, Path],
) -> None:
    """Each threshold receives its own break-up date.

    Staged seasonal decline of 2026 (each stage crosses one
    threshold exactly and persists for at least seven days):

    95 % until 04-09 -> exactly 90 % on 04-10, 85 % until 05-09
    -> exactly 50 % on 05-10, 40 % until 06-09 -> exactly 10 %
    on 06-10, 10 % until 09-15.

    Expected break-up dates (2026):

    90 % -> 04-10
    50 % -> 05-10
    10 % -> 06-10
    """

    rows = _timeline(
        [
            (date(2026, 1, 1), 99, 95.0),   # 01-01 .. 04-09
            (date(2026, 4, 10), 1, 90.0),   # 04-10 (exact)
            (date(2026, 4, 11), 29, 85.0),  # 04-11 .. 05-09
            (date(2026, 5, 10), 1, 50.0),   # 05-10 (exact)
            (date(2026, 5, 11), 30, 40.0),  # 05-11 .. 06-09
            (date(2026, 6, 10), 1, 10.0),   # 06-10 (exact)
            (date(2026, 6, 11), 97, 10.0),  # 06-11 .. 09-15
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    assert _event(
        events, "Test Region", 2026, "break-up", 90.0,
    ) == pd.Timestamp(2026, 4, 10)

    assert _event(
        events, "Test Region", 2026, "break-up", 50.0,
    ) == pd.Timestamp(2026, 5, 10)

    assert _event(
        events, "Test Region", 2026, "break-up", 10.0,
    ) == pd.Timestamp(2026, 6, 10)


# ------------------------------------------------------------------
# Task: test threshold failure independently
# ------------------------------------------------------------------

def test_threshold_failure_is_independent(
    timeseries_paths: dict[str, Path],
) -> None:
    """A threshold without a persistent crossing stays event-free
    while the other thresholds have events.

    Season 2026: 95 % until 04-09 -> exactly 90 % on 04-10,
    60 % on 04-11..04-20, exactly 90 % on 04-21, 95 % until
    09-16. The timeline includes September 16 because the
    dynamic adjustment reads the coverage value of that day.

    Break-up: only the 90 % threshold is crossed (the 60 %
    stage stays above 50 % and 10 %); 50 % and 10 % have no
    break-up and therefore no freeze-up.

    Freeze-up of 90 %: the value on 09-16 is 95 % >= 90 %, so the
    search is extended backwards to the day after the break-up
    (04-11). The rise on 04-21 is found as freeze-up 2026-04-21.
    """

    rows = _timeline(
        [
            (date(2026, 1, 1), 99, 95.0),   # 01-01 .. 04-09
            (date(2026, 4, 10), 1, 90.0),   # 04-10 (exact)
            (date(2026, 4, 11), 10, 60.0),  # 04-11 .. 04-20
            (date(2026, 4, 21), 1, 90.0),   # 04-21 (exact)
            (date(2026, 4, 22), 148, 95.0), # 04-22 .. 09-16
        ]
    )

    events = _events_frame(timeseries_paths, rows)

    # Only the 90 % threshold has a break-up.
    assert _event(
        events, "Test Region", 2026, "break-up", 90.0,
    ) == pd.Timestamp(2026, 4, 10)

    _assert_no_event(_event(
        events, "Test Region", 2026, "break-up", 50.0,
    ))

    _assert_no_event(_event(
        events, "Test Region", 2026, "break-up", 10.0,
    ))

    # The freeze-up of 90 % is found via the dynamic adjustment.
    assert _event(
        events, "Test Region", 2026, "freeze-up", 90.0,
    ) == pd.Timestamp(2026, 4, 21)

    # Without a break-up there is no freeze-up for 50 % / 10 %.
    _assert_no_event(_event(
        events, "Test Region", 2026, "freeze-up", 50.0,
    ))

    _assert_no_event(_event(
        events, "Test Region", 2026, "freeze-up", 10.0,
    ))