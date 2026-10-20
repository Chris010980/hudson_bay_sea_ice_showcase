"""Unit tests for the linear trend helper (issue #102, F-007).

The pure function ``compute_linear_trend()`` is verified with
hand calculations: a noisy least-squares fit, a perfect fit,
the constant-series edge (ss_tot == 0, R² undefined) and an
exact two-point fit.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.analysis.timeseries_analyzer import compute_linear_trend


def test_noisy_fit_matches_hand_calculation() -> None:
    """Least-squares fit of (1,1), (2,2), (3,4).

    slope = 1.5, intercept = -2/3, R² = 27/28 (hand values).
    """
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([1.0, 2.0, 4.0])

    slope, intercept, r_squared = compute_linear_trend(x, y)

    assert slope == pytest.approx(1.5)
    assert intercept == pytest.approx(-2.0 / 3.0)
    assert r_squared == pytest.approx(27.0 / 28.0)


def test_perfect_fit_reaches_r_squared_one() -> None:
    """Collinear points are fitted exactly (R² = 1)."""
    x = np.array([2000.0, 2001.0, 2002.0])
    y = 10.0 * (x - 2000.0) + 5.0

    slope, intercept, r_squared = compute_linear_trend(x, y)

    assert slope == pytest.approx(10.0)
    assert intercept == pytest.approx(-19995.0)
    assert r_squared == pytest.approx(1.0)


def test_constant_series_yields_nan_r_squared() -> None:
    """A constant series has ss_tot == 0: R² is undefined (NaN).

    The degenerate fit itself is well-defined: slope 0,
    intercept at the constant level.
    """
    x = np.array([2000.0, 2001.0, 2002.0])
    y = np.array([30.0, 30.0, 30.0])

    slope, intercept, r_squared = compute_linear_trend(x, y)

    assert slope == pytest.approx(0.0)
    assert intercept == pytest.approx(30.0)
    assert np.isnan(r_squared)


def test_two_points_reproduce_them_exactly() -> None:
    """Two points are fitted exactly (slope 2, R² = 1)."""
    x = np.array([0.0, 1.0])
    y = np.array([1.0, 3.0])

    slope, intercept, r_squared = compute_linear_trend(x, y)

    assert slope == pytest.approx(2.0)
    assert intercept == pytest.approx(1.0)
    assert r_squared == pytest.approx(1.0)
