"""Component tests for the threshold crossing detection of the
TimeSeriesAnalyzer (issue #26).

The tests verify ``_find_threshold_crossing()``, the mathematical
core of the break-up and freeze-up detection. The method is tested
directly at the component level; the seasonal event windows and
the freeze-up window extension are not part of this issue.

Documented rules of the implementation:

* a crossing occurs between two observations on consecutive
  calendar days,
* downward crossing ("down"): y0 > threshold and y1 <= threshold,
* upward crossing ("up"): y0 < threshold and y1 >= threshold,
* the crossing day itself counts as the first persistence day;
  ``persistence`` consecutive calendar days must remain on the
  target side of the threshold (production default: 7),
* the crossing date is interpolated linearly:

      crossing = previous_day + fraction * 1 day
      fraction  = (threshold - y0) / (y1 - y0)

* an observation exactly on the threshold (y1 == threshold)
  returns the current day without interpolation,
* a series already at the threshold (y0 == threshold) does not
  count as a crossing (strict inequality),
* missing observations are dropped: a missing day breaks the
  consecutive-day requirement,
* and a crossing that is found without a persistent crossing
  yields None.

All expected fractions are calculated independently in the test
docstrings. All inputs are controlled in-memory series; the tests
are deterministic.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.analysis.timeseries_analyzer import TimeSeriesAnalyzer

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _analyzer(
    timeseries_paths: dict[str, Path],
) -> TimeSeriesAnalyzer:
    """Construct the analyzer without any file access."""

    return TimeSeriesAnalyzer(
        csv_path=timeseries_paths["csv"],
        output_path=timeseries_paths["timeseries"],
        yearly_output_path=timeseries_paths["yearly"],
        events_output_path=timeseries_paths["events"],
    )


def _daily_frame(
    values: list[float],
    start: date = date(2026, 6, 1),
) -> pd.DataFrame:
    """Create a controlled daily observation series."""

    return pd.DataFrame(
        {
            "date": pd.date_range(
                start,
                periods=len(values),
                freq="D",
            ),
            "relative_coverage_percent": values,
        }
    )


def _find(
    analyzer: TimeSeriesAnalyzer,
    frame: pd.DataFrame,
    threshold: float,
    direction: str,
    persistence: int = 7,
) -> pd.Timestamp | None:
    """Run the crossing search on the production column."""

    return analyzer._find_threshold_crossing(
        df=frame,
        column="relative_coverage_percent",
        threshold=threshold,
        direction=direction,
        persistence=persistence,
    )


def _assert_crossing(
    result: pd.Timestamp | None,
    day: date,
    fraction: float,
) -> None:
    """Assert an interpolated crossing date.

    ``fraction`` is the independently calculated position of the
    threshold between the two surrounding observations:

    fraction = (threshold - y0) / (y1 - y0)
    """

    assert result is not None

    assert result.normalize() == pd.Timestamp(day)

    offset_days = (result - pd.Timestamp(day)).total_seconds() / 86400.0

    assert offset_days == pytest.approx(fraction)


def _assert_no_crossing(
    result: pd.Timestamp | None,
) -> None:
    """Assert that no crossing was found."""

    assert result is None


# ------------------------------------------------------------------
# Task: test downward crossings
# ------------------------------------------------------------------


def test_downward_crossing_is_detected(
    timeseries_paths: dict[str, Path],
) -> None:
    """A downward crossing of 50 % is detected and interpolated.

    2026-06-01: 80 %, 06-02: 80 %, 06-03..06-10: 40 %.

    The crossing occurs between 06-02 (80 %) and 06-03 (40 %);
    06-03..06-09 (7 consecutive days) remain at or below 50 %.

    Independent interpolation:

    fraction = (50 - 80) / (40 - 80) = 30 / 40 = 0.75
    crossing = 06-02 + 0.75 days = 06-02 18:00

    The same series contains no upward crossing.
    """

    analyzer = _analyzer(timeseries_paths)

    frame = _daily_frame(
        [80.0, 80.0] + [40.0] * 8,
    )

    result = _find(
        analyzer,
        frame,
        threshold=50.0,
        direction="down",
    )

    _assert_crossing(result, date(2026, 6, 2), 0.75)

    # The direction is distinguished: no upward crossing exists.
    _assert_no_crossing(
        _find(
            analyzer,
            frame,
            threshold=50.0,
            direction="up",
        )
    )


# ------------------------------------------------------------------
# Task: test upward crossings
# ------------------------------------------------------------------


def test_upward_crossing_is_detected(
    timeseries_paths: dict[str, Path],
) -> None:
    """An upward crossing of 50 % is detected and interpolated.

    2026-06-01: 20 %, 06-02: 20 %, 06-03..06-10: 70 %.

    The crossing occurs between 06-02 (20 %) and 06-03 (70 %);
    06-03..06-09 remain at or above 50 %.

    Independent interpolation:

    fraction = (50 - 20) / (70 - 20) = 30 / 50 = 0.6
    crossing = 06-02 + 0.6 days = 06-02 14:24

    The same series contains no downward crossing.
    """

    analyzer = _analyzer(timeseries_paths)

    frame = _daily_frame(
        [20.0, 20.0] + [70.0] * 8,
    )

    result = _find(
        analyzer,
        frame,
        threshold=50.0,
        direction="up",
    )

    _assert_crossing(result, date(2026, 6, 2), 0.6)

    # The direction is distinguished: no downward crossing exists.
    _assert_no_crossing(
        _find(
            analyzer,
            frame,
            threshold=50.0,
            direction="down",
        )
    )


# ------------------------------------------------------------------
# Task: test the 10 % threshold
# ------------------------------------------------------------------


def test_10_percent_threshold(
    timeseries_paths: dict[str, Path],
) -> None:
    """The 10 % break-up threshold is detected independently.

    2026-06-01: 30 %, 06-02: 30 %, 06-03..06-09: 0 %.

    Independent interpolation:

    fraction = (10 - 30) / (0 - 30) = 20 / 30 = 2/3
    crossing = 06-02 + 2/3 days = 06-02 16:00

    The rows are passed unsorted; the search sorts internally.
    """

    analyzer = _analyzer(timeseries_paths)

    frame = pd.DataFrame(
        {
            "date": [
                pd.Timestamp(2026, 6, 3),
                pd.Timestamp(2026, 6, 1),
                pd.Timestamp(2026, 6, 5),
                pd.Timestamp(2026, 6, 2),
                pd.Timestamp(2026, 6, 4),
                pd.Timestamp(2026, 6, 7),
                pd.Timestamp(2026, 6, 6),
                pd.Timestamp(2026, 6, 9),
                pd.Timestamp(2026, 6, 8),
            ],
            "relative_coverage_percent": [
                0.0,
                30.0,
                0.0,
                30.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
        }
    )

    result = _find(
        analyzer,
        frame,
        threshold=10.0,
        direction="down",
    )

    _assert_crossing(result, date(2026, 6, 2), 2 / 3)


# ------------------------------------------------------------------
# Task: test the 50 % threshold
# ------------------------------------------------------------------


def test_50_percent_threshold(
    timeseries_paths: dict[str, Path],
) -> None:
    """The 50 % freeze-up threshold is detected independently.

    2026-06-01: 20 %, 06-02: 20 %, 06-03..06-10: 80 %.

    Independent interpolation:

    fraction = (50 - 20) / (80 - 20) = 30 / 60 = 0.5
    crossing = 06-02 + 0.5 days = 06-02 12:00
    """

    analyzer = _analyzer(timeseries_paths)

    frame = _daily_frame(
        [20.0, 20.0] + [80.0] * 8,
    )

    result = _find(
        analyzer,
        frame,
        threshold=50.0,
        direction="up",
    )

    _assert_crossing(result, date(2026, 6, 2), 0.5)


# ------------------------------------------------------------------
# Task: test the 90 % threshold
# ------------------------------------------------------------------


def test_90_percent_threshold(
    timeseries_paths: dict[str, Path],
) -> None:
    """The 90 % freeze-up threshold is detected independently.

    2026-06-01: 80 %, 06-02: 80 %, 06-03..06-10: 100 %.

    Independent interpolation:

    fraction = (90 - 80) / (100 - 80) = 10 / 20 = 0.5
    crossing = 06-02 + 0.5 days = 06-02 12:00
    """

    analyzer = _analyzer(timeseries_paths)

    frame = _daily_frame(
        [80.0, 80.0] + [100.0] * 8,
    )

    result = _find(
        analyzer,
        frame,
        threshold=90.0,
        direction="up",
    )

    _assert_crossing(result, date(2026, 6, 2), 0.5)


# ------------------------------------------------------------------
# Task: test exact threshold observations
# ------------------------------------------------------------------


def test_exact_threshold_observation(
    timeseries_paths: dict[str, Path],
) -> None:
    """Exact threshold observations are handled asymmetrically.

    Case 1 -- observation exactly on the threshold (y1 == 50):
    06-01: 80 %, 06-02: 80 %, 06-03..06-09: 50 %.
    The crossing date is the current day 06-03 itself
    (no interpolation, fraction = 0).

    Case 2 -- previous observation exactly on the threshold
    (y0 == 50): 06-01: 50 %, 06-02..06-09: 40 % and below.
    The strict condition (y0 > threshold) is not met: the series
    registers no crossing at all, although it falls below the
    threshold on 06-02 (documented implementation semantics, see
    tests/FINDINGS.md, F-008).
    """

    analyzer = _analyzer(timeseries_paths)

    # Case 1: y1 == threshold -> exact current date.
    frame = _daily_frame(
        [80.0, 80.0] + [50.0] * 7,
    )

    result = _find(
        analyzer,
        frame,
        threshold=50.0,
        direction="down",
    )

    _assert_crossing(result, date(2026, 6, 3), 0.0)

    # Case 2: y0 == threshold -> no crossing (strict inequality).
    frame = _daily_frame(
        [50.0] + [40.0] * 8,
    )

    result = _find(
        analyzer,
        frame,
        threshold=50.0,
        direction="down",
    )

    _assert_no_crossing(result)


# ------------------------------------------------------------------
# Task: test interpolated crossings
# ------------------------------------------------------------------


def test_interpolated_crossing_date(
    timeseries_paths: dict[str, Path],
) -> None:
    """The interpolated crossing date matches an independent value.

    2026-06-01: 60 %, 06-02: 60 %, 06-03..06-10: 20 %.

    Independent interpolation:

    fraction = (50 - 60) / (20 - 60) = 10 / 40 = 0.25
    crossing = 06-02 + 0.25 days = 06-02 06:00
    """

    analyzer = _analyzer(timeseries_paths)

    frame = _daily_frame(
        [60.0, 60.0] + [20.0] * 8,
    )

    result = _find(
        analyzer,
        frame,
        threshold=50.0,
        direction="down",
    )

    _assert_crossing(result, date(2026, 6, 2), 0.25)

    # The fraction 0.25 is exactly representable: 06:00 sharp.
    assert result == pd.Timestamp(2026, 6, 2, 6, 0)


# ------------------------------------------------------------------
# Task: test missing crossings
# ------------------------------------------------------------------


def test_missing_crossing_returns_none(
    timeseries_paths: dict[str, Path],
) -> None:
    """Without a persistent crossing the result is None.

    Case 1 -- no crossing at all: the series stays at 80 %.
    Case 2 -- crossing without enough subsequent days: the series
    drops to 40 % but ends before the 7-day persistence window
    is complete.
    Case 3 -- crossing across a missing day: observations exist
    for 06-01 (80 %) and 06-03 (40 %), 06-02 is missing; the two
    observations are not consecutive calendar days.
    """

    analyzer = _analyzer(timeseries_paths)

    # Case 1: never below the threshold.
    frame = _daily_frame([80.0] * 10)

    _assert_no_crossing(
        _find(
            analyzer,
            frame,
            threshold=50.0,
            direction="down",
        )
    )

    # Case 2: insufficient days after the crossing.
    frame = _daily_frame(
        [80.0, 80.0, 40.0, 40.0, 40.0],
    )

    _assert_no_crossing(
        _find(
            analyzer,
            frame,
            threshold=50.0,
            direction="down",
        )
    )

    # Case 3: gap in the daily observations.
    frame = pd.DataFrame(
        {
            "date": [
                pd.Timestamp(2026, 6, 1),
                pd.Timestamp(2026, 6, 3),
            ],
            "relative_coverage_percent": [80.0, 40.0],
        }
    )

    _assert_no_crossing(
        _find(
            analyzer,
            frame,
            threshold=50.0,
            direction="down",
        )
    )


# ------------------------------------------------------------------
# Task: test non-persistent crossings
# ------------------------------------------------------------------


def test_non_persistent_crossing_is_rejected(
    timeseries_paths: dict[str, Path],
) -> None:
    """A crossing that does not persist is not an event -- but a
    later persistent crossing is still found.

    Series 1: 06-01..06-02: 80 %, 06-03..06-04: 40 %,
    06-05..06-13: 60 %. The 80 % -> 40 % crossing is not
    persistent (the series returns above 50 % on 06-05 within
    the persistence window) and no later crossing follows:
    None.

    Series 2: 06-01..06-02: 80 %, 06-03..06-04: 40 %,
    06-05..06-06: 60 %, 06-07..06-13: 20 %. The first crossing
    fails the persistence check, the second crossing
    (06-06 -> 06-07, 60 % -> 20 %) persists:

    fraction = (50 - 60) / (20 - 60) = 10 / 40 = 0.25
    crossing = 06-06 + 0.25 days = 06-06 06:00
    """

    analyzer = _analyzer(timeseries_paths)

    # Series 1: only the non-persistent crossing exists.
    frame = _daily_frame(
        [80.0, 80.0, 40.0, 40.0] + [60.0] * 9,
    )

    _assert_no_crossing(
        _find(
            analyzer,
            frame,
            threshold=50.0,
            direction="down",
        )
    )

    # Series 2: a later persistent crossing is still found.
    frame = _daily_frame(
        [80.0, 80.0, 40.0, 40.0, 60.0, 60.0] + [20.0] * 7,
    )

    result = _find(
        analyzer,
        frame,
        threshold=50.0,
        direction="down",
    )

    _assert_crossing(result, date(2026, 6, 6), 0.25)


# ------------------------------------------------------------------
# Task: test the persistence window boundary
# ------------------------------------------------------------------


def test_persistence_window_boundary(
    timeseries_paths: dict[str, Path],
) -> None:
    """Exactly seven qualifying days satisfy the persistence
    requirement; six do not.

    The crossing day (06-03) counts as the first persistence
    day. With persistence=7, the window 06-03..06-09 must stay
    at or below the threshold.

    Case 1: exactly 7 days at 40 % (06-03..06-09) -> detected.
    fraction = (50 - 80) / (40 - 80) = 0.75

    Case 2: only 6 days at 40 % (06-03..06-08) -> None.
    """

    analyzer = _analyzer(timeseries_paths)

    # Case 1: exactly enough days.
    frame = _daily_frame(
        [80.0, 80.0] + [40.0] * 7,
    )

    result = _find(
        analyzer,
        frame,
        threshold=50.0,
        direction="down",
    )

    _assert_crossing(result, date(2026, 6, 2), 0.75)

    # Case 2: one day short.
    frame = _daily_frame(
        [80.0, 80.0] + [40.0] * 6,
    )

    _assert_no_crossing(
        _find(
            analyzer,
            frame,
            threshold=50.0,
            direction="down",
        )
    )
