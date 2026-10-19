"""Unit tests for the small-gap interpolation (issue #41).

``_interpolate_small_gaps()`` is the pure module helper of
the calendar interpolation (docs/testing/test-levels.md,
section 2.2, "interpolation-gap handling"). The tests pin
the F-003 semantics of issue #103: gaps of at most 14
consecutive missing days are filled forward-looking, longer
gaps stay missing, and missing days without a preceding
observation are never filled.

No file is read or written. All tests are deterministic and
require no network access.
"""

from __future__ import annotations

import pandas as pd

from src.analysis.timeseries_analyzer import (
    _interpolate_small_gaps,
)


def _frame(values: list[float]) -> pd.DataFrame:
    """One numeric column indexed by consecutive days."""

    index = pd.date_range(
        "2026-01-01",
        periods=len(values),
        freq="D",
    )

    return pd.DataFrame({"coverage": values}, index=index)


def test_small_gap_is_filled_linearly() -> None:
    """A two-day gap within the limit is bridged linearly."""

    filled = _interpolate_small_gaps(
        _frame([10.0, float("nan"), float("nan"), 16.0]),
        14,
    )

    assert list(filled["coverage"]) == [10.0, 12.0, 14.0, 16.0]


def test_gap_at_the_limit_is_filled() -> None:
    """A gap of exactly 14 days is still interpolated."""

    values = [10.0] + [float("nan")] * 14 + [25.0]

    filled = _interpolate_small_gaps(_frame(values), 14)

    coverage = filled["coverage"].reset_index(drop=True)

    assert coverage[0] == 10.0
    assert coverage[1] == 11.0
    assert coverage[14] == 24.0
    assert coverage[15] == 25.0


def test_gap_beyond_the_limit_stays_missing() -> None:
    """A gap of 15 days exceeds the limit and stays NaN."""

    values = [10.0] + [float("nan")] * 15 + [26.0]

    filled = _interpolate_small_gaps(_frame(values), 14)

    coverage = filled["coverage"].reset_index(drop=True)

    assert coverage.iloc[1:16].isna().all()
    assert coverage[0] == 10.0
    assert coverage[16] == 26.0


def test_leading_missing_days_are_never_filled() -> None:
    """Missing days without a preceding observation stay NaN."""

    filled = _interpolate_small_gaps(
        _frame([float("nan"), float("nan"), 10.0, 12.0]),
        14,
    )

    assert filled["coverage"][:2].isna().all()


def test_trailing_gap_holds_the_last_value_within_limit() -> None:
    """Trailing gaps are forward-looking (F-003).

    Within the limit the last observed value is held; beyond
    the limit the missing days stay NaN.
    """

    within = _interpolate_small_gaps(
        _frame([10.0, 12.0, float("nan"), float("nan")]),
        14,
    )

    assert list(within["coverage"]) == [10.0, 12.0, 12.0, 12.0]

    beyond = _interpolate_small_gaps(
        _frame([10.0, 12.0] + [float("nan")] * 15),
        14,
    )

    assert beyond["coverage"].iloc[2:].isna().all()
