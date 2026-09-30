# Test Findings and Limitations (v0.2)

This document collects findings uncovered while building the v0.2  
test suite: bugs, design inconsistencies, behavioral edge cases of  
dependencies, and deliberate test limitations that were **not**  
resolved on the fly. It is the single source of truth for the  
findings section of the project documentation at the end of v0.2.

## Legend

- Category: `bug` (incorrect behavior) · `design` (inconsistency or  
code smell) · `semantics` (edge case of a dependency's behavior) ·  
`test-limitation` (deliberate restriction of the test suite)
- Status: `fixed` (resolved during v0.2) · `open` (decision or  
documentation pending) · `documented` (accepted as-is)

## Overview

| ID    | Issue | Component          | Category  | Status     |
| ----- | ----- | ------------------ | --------- | ---------- |
| F-001 | #20   | ResultsManager     | bug       | fixed      |
| F-002 | #20   | ResultsManager     | bug       | fixed      |
| F-003 | #21   | TimeSeriesAnalyzer | semantics | open       |
| F-004 | #21   | TimeSeriesAnalyzer | design    | open       |
| F-005 | #21   | TimeSeriesAnalyzer | design    | open       |
| F-006 | #21   | TimeSeriesAnalyzer | design    | documented |

## F-001 — Duplicate detection ran before date normalization

**Component:** `src/analysis/results_manager.py` (`save()`)

**Finding:** `drop_duplicates(subset=["date", "region"])` ran before  
the dates were normalized, so persisted ISO date strings  
(`"2026-03-15"`) and newly added `datetime.date` objects were not  
recognized as the same key and could survive a save as duplicates.

**Impact:** duplicate `(date, region)` rows in call paths that are  
not guarded by `is_date_processed()`. The production pipeline was  
not affected because the guard prevents re-adding processed dates.

**Resolution (v0.2):** all dates are normalized to `YYYY-MM-DD`  
strings before deduplication; verified with a manual run.

**Test note:** implicitly covered by the duplicate-handling tests in  
`tests/component/test_results_manager.py`. A dedicated regression  
test was intentionally deferred until the higher test levels  
(integration/system) are built.

## F-002 — Deprecated `datetime.utcnow()`

**Component:** `src/analysis/results_manager.py` (`_save_latest_json()`)

**Finding:** `datetime.utcnow()` is deprecated since Python 3.12 and  
returns a naive timestamp (no timezone offset).

**Resolution (v0.2):** replaced with  
`datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"`.

## F-003 — pandas interpolation fills `limit` values *per direction*

**Component:** `src/analysis/timeseries_analyzer.py`  
(`interpolate_calendar()`:  
`interpolate(method="time", limit=14, limit_direction="both")`)

**Finding:** pandas fills up to `limit` (14) missing values **per**  
**direction**. For a gap longer than 14 days, up to 14 days at the  
start and up to 14 days at the end of the gap may still be  
interpolated; only the middle of a sufficiently long gap  
(&gt; 2 × 14 days) is guaranteed to remain NaN.

**Impact:** the acceptance criterion *"gaps exceeding the configured*  
*limit remain unbridged"* is only guaranteed for the middle of long  
gaps. Shorter overshoots (e.g. a 15-day gap) may be fully or  
partially bridged depending on the pandas version.

**Recommendation:** decide whether the per-direction fill is the  
intended scientific behavior. If not, restrict the fill (e.g.  
`limit_area` or an explicit gap mask). Either way, document the  
effective semantics in the methodology docs. Quick check: run a  
15-day gap through `interpolate_calendar()` and inspect which days  
are filled.

**Test note:** `tests/component/test_timeseries_calendar.py`  
deliberately asserts only the unambiguous core behavior (gaps ≤ 14  
fully interpolated; middle of a 39-day gap NaN; bounding  
observations unchanged) and does not assert the gap edges.

## F-004 — Stray `from curses import window` import

**Component:** `src/analysis/timeseries_analyzer.py` (module header)

**Finding:** unused, accidental import (IDE auto-import artifact).  
`curses` is Unix-only in the standard library, so the module fails  
to import on Windows.

**Recommendation:** remove the import line.

## F-005 — `save()` return annotation does not match the return value

**Component:** `src/analysis/timeseries_analyzer.py` (`save()`)

**Finding:** annotated `-> Path` but returns the tuple  
`(self.output_path, self.yearly_output_path)`. The events output  
path is written but not returned.

**Recommendation:** correct the annotation to  
`-> tuple[Path, Path]` (and consider returning the events path as  
well).

## F-006 — Inconsistent output-directory creation between managers

**Component:** `src/analysis/results_manager.py`,  
`src/analysis/timeseries_analyzer.py`

**Finding:** `ResultsManager` creates its output directories eagerly  
in `__init__` (`mkdir(parents=True, exist_ok=True)`), while  
`TimeSeriesAnalyzer` creates them only in `save()` — not when the  
input CSV is loaded.

**Impact:** not a production bug (the `ResultsManager` always runs  
first in the pipeline and creates `output/analysis`), but tests that  
seed a summary CSV themselves must pre-create the directory, and the  
analyzer's behavior differs from its sibling class.

**Resolution:** the shared `timeseries_paths` fixture in  
`tests/conftest.py` creates the analysis directory eagerly  
(`analysis_dir.mkdir()`). Production behavior left unchanged and  
documented as a design difference.
