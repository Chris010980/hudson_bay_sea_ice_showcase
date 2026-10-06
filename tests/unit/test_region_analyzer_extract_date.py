"""Unit tests for the RegionAnalyzer date extraction.

``RegionAnalyzer.extract_date()`` is the public seam through
which the process stage reads the observation date from the
GeoTIFF filename (issue #73). It is a pure filename-to-date
mapping and is tested here at unit level per docs/testing/
test-levels.md section 2.2 ("date extraction from filenames").

The analyzer is constructed with in-memory values only; no
GeoTIFF is read and no reference data is loaded.

All tests are deterministic and require no network access.
"""

from __future__ import annotations

from datetime import date

from src.analysis.region_analyzer import RegionAnalyzer


def _analyzer(filename: str) -> RegionAnalyzer:
    """Analyzer for one input filename, nothing else."""

    return RegionAnalyzer(
        input_tif=f"data/geotiff/2026/03_Mar/{filename}",
    )


def test_extract_date_parses_observation_date() -> None:
    """The eight-digit date token maps to the observation."""

    analyzer = _analyzer("N_20260301_concentration_v1.0.tif")

    assert analyzer.extract_date() == date(2026, 3, 1)
    assert analyzer.date == date(2026, 3, 1)


def test_extract_date_returns_none_without_date_token() -> None:
    """A filename without a date token leaves the date None."""

    analyzer = _analyzer("overview_map.png")

    assert analyzer.extract_date() is None
    assert analyzer.date is None
