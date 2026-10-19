"""Unit tests for the results merge helper (issue #41).

``merge_results()`` is the pure persistence core of
``ResultsManager.save()`` (docs/testing/test-levels.md,
section 2.2, "duplicate detection" and "sorting"):
concatenation, date normalization, keep-last deduplication
on (date, region) and sorting.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from src.analysis.results_manager import merge_results


def _rows(rows: list[tuple]) -> pd.DataFrame:
    """Stored result rows of (day, region, coverage)."""

    return pd.DataFrame(
        {
            "date": [row[0] for row in rows],
            "region": [row[1] for row in rows],
            "relative_coverage_percent": [
                float(row[2]) for row in rows
            ],
        }
    )


def test_duplicate_date_region_keeps_the_new_value() -> None:
    """A re-observed (date, region) replaces the stored row."""

    merged = merge_results(
        _rows([("2026-03-01", "Region A", 50.0)]),
        [
            {
                "date": "2026-03-01",
                "region": "Region A",
                "relative_coverage_percent": 70.0,
            }
        ],
    )

    assert len(merged) == 1
    assert merged["relative_coverage_percent"].item() == 70.0


def test_results_are_sorted_by_date_and_region() -> None:
    """The merged table is sorted by date then region."""

    merged = merge_results(
        pd.DataFrame(),
        [
            {
                "date": "2026-03-02",
                "region": "Region B",
                "relative_coverage_percent": 10.0,
            },
            {
                "date": "2026-02-15",
                "region": "Region B",
                "relative_coverage_percent": 20.0,
            },
        ],
    )

    assert list(merged["date"]) == ["2026-02-15", "2026-03-02"]


def test_dates_are_normalized_to_iso_strings() -> None:
    """date objects become YYYY-MM-DD strings."""

    merged = merge_results(
        pd.DataFrame(),
        [
            {
                "date": date(2026, 3, 2),
                "region": "Region A",
                "relative_coverage_percent": 30.0,
            }
        ],
    )

    assert merged["date"].item() == "2026-03-02"


def test_existing_rows_are_preserved() -> None:
    """Stored rows survive the merge alongside new rows."""

    merged = merge_results(
        _rows([("2026-03-01", "Region A", 50.0)]),
        [
            {
                "date": "2026-03-02",
                "region": "Region B",
                "relative_coverage_percent": 10.0,
            }
        ],
    )

    assert len(merged) == 2
    assert set(merged["region"]) == {"Region A", "Region B"}
