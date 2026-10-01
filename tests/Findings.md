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

| ID    | Issue | Component                           | Category  | Status     |
| ----- | ----- | ----------------------------------- | --------- | ---------- |
| F-001 | #20   | ResultsManager                      | bug       | fixed      |
| F-002 | #20   | ResultsManager                      | bug       | fixed      |
| F-003 | #21   | TimeSeriesAnalyzer                  | semantics | open       |
| F-004 | #21   | TimeSeriesAnalyzer                  | design    | open       |
| F-005 | #21   | TimeSeriesAnalyzer                  | design    | open       |
| F-006 | #21   | TimeSeriesAnalyzer                  | design    | documented |
| F-007 | #25   | TimeSeriesPlotter                   | design    | open       |
| F-008 | #26   | TimeSeriesAnalyzer                  | design    | open       |
| F-009 | #28   | download\_data.py / NSIDCDownloader | bug       | open       |
| F-010 | #28   | NSIDCDownloader                     | design    | open       |
| F-011 | #28   | NSIDCDownloader                     | design    | open       |
| F-012 | #28   | NSIDCDownloader                     | design    | open       |

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

## F-007 — Trend and R² calculation is not testable as a unit

**Component:** `src/visualization/timeseries_plot.py`  
(`_plot_threshold_duration_region()`)

**Finding:** the linear trend  
(`np.polyfit(event_year, duration_days, 1)`) and the coefficient of  
determination (`r_squared = 1 - ss_res / ss_tot`, `NaN` for fewer  
than two points or zero total variance) are computed inline inside a  
plotting method and are never returned or stored. There is no  
testable unit for the trend in `src/analysis/`.

**Impact:** the issue #25 tasks "Test linear trend" and "Test R²"  
cannot be implemented as component tests against the current  
structure; assertions would require figure-level tests of  
matplotlib label text.

**Recommendation:** extract the calculation into a small testable  
function or method and have the plotter consume it; then add the  
component tests. Deferred to a follow-up issue (issue #25 closed  
without the trend part). Open design decision for that issue:  
whether the trend calculation should live on the  
`TimeSeriesAnalyzer` (data product, e.g. a trend column in the  
yearly/events datasets) or as a small helper next to the plotting  
code (presentation-only quantity).

## F-008 — Dead branches and strict-threshold edge in `_find_threshold_crossing`

**Component:** `src/analysis/timeseries_analyzer.py`  
(`_find_threshold_crossing()`)

**Finding (dead code):** the special cases  
`if y0 == threshold: return previous["date"]` and  
`if y1 == y0: return current["date"]` are unreachable. The  
crossing conditions require `y0 > threshold and y1 <= threshold`  
("down") or `y0 < threshold and y1 >= threshold` ("up"), which  
exclude both `y0 == threshold` and `y1 == y0`.

**Finding (semantic edge):** a series that sits *exactly on* the  
threshold on the day before it falls below registers no crossing  
at all, because `y0 > threshold` fails strictly. Example: SIC is  
50 % on March 17 and 40 % on March 18 — the 50 % break-up is  
missed, while 60 % → 40 % on the same days would be interpolated  
correctly. The asymmetry is deliberate for `y1 == threshold`  
(exact observation returns the current day) but undocumented for  
the `y0 == threshold` side.

**Impact:** possible missed events when observations land exactly  
on a threshold (10/50/90) before continuing in the event  
direction.

**Recommendation:** decide whether "at the threshold the day  
before" should count as a crossing; either relax the condition or  
seed the first observation of the window as strictly above/below.  
Otherwise remove the two dead branches to avoid confusion. The  
behavior is documented by  
`tests/component/test_timeseries_threshold_crossing.py`  
(`test_exact_threshold_observation`).

## F-009 — CLI passes unsupported arguments to `sync()`

**Component:** `src/data_download/download_data.py` (`main()`),  
`src/data_download/downloader.py` (`NSIDCDownloader.sync()`)

**Finding:** the CLI entry point calls  
`downloader.sync(years=args.years, months=args.months, dry_run=args.dry_run)`, but `sync()` only accepts `start_date`,  
`end_date` and `dry_run`. Every invocation of `download_data.py`  
therefore fails at runtime with  
`TypeError: sync() got an unexpected keyword argument 'years'`.

**Impact:** the documented CLI flags `--year` and `--month`  
cannot work; the raw-data download stage is currently not  
operable from the command line.

**Recommendation:** align the CLI with the API — either map the  
selected years/months to a `start_date`/`end_date` range or  
extend `sync()` with explicit year/month filters. Requires a  
design decision and a functional-correction issue (milestone  
V0.2-07).

**Test note:** not covered by issue #28, which tests the  
downloader component directly; the CLI wiring belongs to the  
pipeline integration tests.

## F-010 — `delete_local_data()` is hard-wired to `DATA_DIR / "geotiff"`

**Component:** `src/data_download/downloader.py`  
(`NSIDCDownloader.delete_local_data()`)

**Finding:** the cleanup is a `@staticmethod` that always  
operates on the module-level `DATA_DIR / "geotiff"` and ignores  
the instance's `local_base`. It cannot be redirected through the  
constructor, so tests must monkeypatch the module-level  
`DATA_DIR` to avoid touching production data. In addition, the  
docstring promises to remove the files "while preserving the  
directory structure", but the implementation also removes empty  
year/month directories (`rmdir`).

**Recommendation:** make the cleanup operate on the configured  
`local_base` (instance method or explicit root parameter) and  
align the docstring with the implemented semantics.

**Test note:** `tests/component/test_nsidc_downloader.py`  
(`test_delete_local_data`) pins the implemented behavior:  
`.tif` files removed, other files preserved, empty directories  
removed.

## F-011 — `download_file()` writes non-atomically and lets request exceptions escape

**Component:** `src/data_download/downloader.py`  
(`download_file()`, `sync()`)

**Finding:** downloads are written directly to the final  
destination. A request that fails mid-stream (exception during  
`iter_content`) leaves a partial `.tif` behind, which later  
synchronization runs treat as an existing file and skip — a  
corrupted observation can enter the archive permanently. Request  
exceptions (timeouts, connection errors) are not caught at all:  
they propagate out of `download_file()` and abort the entire  
`sync()` run instead of being counted in `failed_files`.

**Recommendation:** download to a temporary file and rename it  
after success; catch per-file request exceptions and count them  
as failed downloads.

**Test note:** issue #28 covers only the handled error path  
(non-OK HTTP status → `False`, no file, counted as failed).

## F-012 — Stray `from os import link` import

**Component:** `src/data_download/downloader.py` (module header)

**Finding:** unused, accidental import (IDE auto-import artifact,  
same pattern as F-004). Harmless because `os` is always  
available, but dead code.

**Recommendation:** remove the import line.
