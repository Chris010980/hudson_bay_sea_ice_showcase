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
- Category (audit, #75): `gap` (verified missing test coverage,
  proposed as backlog) · Status (audit, #75): `proposed` (backlog
  candidate, not yet scheduled or decided)

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
| F-013 | #29   | ReferenceBuilder                    | design    | open       |
| F-014 | #30   | update\_pipeline                    | bug       | open       |
| F-015 | #30   | update\_pipeline / process\_data    | design    | open       |
| F-016 | #31   | update\_pipeline / downloader       | design    | open       |
| F-017 | #32   | timeseries\_plot                    | design    | open       |
| F-018 | #32   | visualization stage                 | design    | open       |
| F-019 | #32   | generate\_plots                     | design    | open       |
| F-020 | #33   | build\_pages                        | design    | open       |
| F-021 | #33   | build\_pages                        | design    | open       |

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

## F-013 — ReferenceBuilder writes to non-injectable module constants

**Component:** `src/analysis/reference_builder.py`  
(`FILTER_DIR`, `REFERENCE_SUMMARY`, `_calculate_reference_areas()`)

**Finding:** the builder saves water masks and the reference  
summary to the module-level constants `FILTER_DIR` and  
`REFERENCE_SUMMARY` (derived from `PROJECT_ROOT`), and reads the  
naturalearth ocean dataset via a `PROJECT_ROOT` path. None of  
these paths can be redirected through the constructor. Tests must  
monkeypatch the module constants and stub the `gpd` import to  
avoid reading or writing production data (pattern established in  
`tests/component/test_reference_builder.py` and reused by the  
issue #29 integration chain). Same design pattern as F-010.

**Impact:** not a production bug, but a testability constraint:  
every test that runs the real `build()` needs module-level  
patching instead of plain dependency injection.

**Recommendation:** add injectable output paths (mask directory  
and summary path) to the constructor with the current constants  
as defaults, analogous to `RegionAnalyzer`, which already accepts  
`reference_json` and `filter_dir` parameters.

## F-014 — First pipeline run crashes with `None.isoformat()`

**Component:** `src/update/update_pipeline.py` (`main()`)

**Finding:** on the first update run (no persisted results yet),  
`get_latest_processed_date()` returns `None`, so the pipeline  
computes `start_date = None + 1 day = None` and passes it on:  
`process_data([..., "--start-date", start_date.isoformat(), ...])`  
raises `AttributeError: 'NoneType' object has no attribute 'isoformat'`.

**Impact:** a complete first run (empty results state) is currently  
not operable; only incremental updates over an existing results  
state work.

**Recommendation:** pass `--start-date` only when `start_date is not None` (`process_data` already treats it as an optional  
argument) or define an explicit fallback (e.g. earliest observation  
date).

**Test note:** issue #30 deliberately covers only the incremental  
path; a first-run test can be added once the fix is decided  
(milestone V0.2-07).

## F-015 — Pipeline stages wire collaborators with hard-wired production defaults

**Component:** `src/update/update_pipeline.py`,  
`src/analysis/process_data.py`

**Finding:** the pipeline and the processing stage construct all  
collaborators with hard-coded production defaults  
(`NSIDCDownloader()`, `ResultsManager()`, `ReferenceBuilder()`,  
`RegionAnalyzer(tif)`, `TimeSeriesAnalyzer()`), and several of  
these defaults are bound at function-definition time rather than  
read from module constants at call time. As a result, a complete  
update run cannot be redirected into an isolated test environment  
by patching module constants; the collaborators would read and  
write production directories. Same design pattern as F-010 and  
F-013.

**Impact:** not a production bug, but a testability constraint:  
issue #30 replaces the collaborators in the  
`src.update.update_pipeline` namespace with controlled  
implementations of the same contracts instead of running the  
untouched pipeline end to end.

**Recommendation:** pass an injectable configuration (data,  
output, build directories) through the pipeline stages for  
milestone V0.2-07, so integration tests can run the real  
orchestration against isolated directories.

## F-016 — Locally present files can mask unprocessed observations as "no new data"

**Component:** `src/update/update_pipeline.py` (`main()`),  
`src/data_download/downloader.py` (`sync()`)

**Finding:** the pipeline treats `downloaded_files == 0` as the  
no-new-data condition and terminates after the sync stage. But  
`sync()` also counts nothing when a requested file is already  
present locally: an observation that was downloaded in an  
earlier run but never processed (the `new_results == 0` early  
exit keeps downloaded files — pinned by the issue #30 tests; a  
crash between download and processing; a partial file from  
F-011) is skipped by every later sync. The pipeline then  
reports "no new data" forever, although an observation in the  
requested date range is missing from the results.

**Impact:** unprocessed observations can become permanently  
invisible to the incremental update once their file exists in  
the local archive.

**Recommendation:** base the no-new-data decision on the  
processed-state boundary (e.g. also run the process stage when  
processable files from `start_date` onwards exist locally), or  
let `sync()` re-validate existing files, or remove downloaded  
files on the no-new-results exit path.

**Test note:** issue #31 pins the documented no-new-data  
behavior for a fully processed state; the masking scenario  
requires the real `sync()` semantics (local file check) and is  
documented here instead.

## F-017 — `polar_output_dir` is configured but never used

**Component:** `src/visualization/timeseries_plot.py`  
(`_configure_style()`, `_plot_polar_region()`)

**Finding:** `_configure_style()` sets  
`self.polar_output_dir = OUTPUT_DIR / "polar"`, but  
`_plot_polar_region()` saves to `self.output_dir` (the  
timeseries directory) as `{region}_polar_{suffix}.png`. The  
attribute is never read, so the polar products land in  
`output/plots/timeseries/` next to the Cartesian plots instead  
of the configured `output/plots/polar/` directory.

**Recommendation:** save the polar plots to  
`self.polar_output_dir` or remove the unused attribute. The  
issue #32 tests pin the implemented behavior (polar files in  
the timeseries directory).

## F-018 — Non-injectable production paths in the visualization stage

**Component:** `src/visualization/timeseries_plot.py`,  
`src/visualization/geotiff_plot.py`

**Finding:** several production paths of the visualization  
stage cannot be redirected through constructors or arguments  
(same design family as F-010, F-013 and F-015):

- `TimeSeriesPlotter.__init__` binds the default input paths  
(`RESULTS_CSV`, `YEARLY_CSV`, `EVENTS_CSV`) as default  
argument values at function-definition time; patching the  
module constants does not change the defaults. Callers that  
construct the plotter without arguments  
(`generate_plots.main`) always read the production analysis  
directory.
- `SeaIcePlotter.load_regions()` defaults to  
`PROJECT_ROOT / "src/config/regions.json"` and `load()` never  
passes `region_file`, so the region definitions cannot be  
injected through the public API.
- `SeaIcePlotter.save()` without arguments writes to the  
import-time constant `DEFAULT_OUTPUT_PLOT_PATH`; the  
`generate_plots` "all" mode relies on this for every map  
product.

**Impact:** not a production bug, but tests must replace  
module constants or classes in the caller's namespace to keep  
plot generation away from the production `output/` tree (the  
pattern used by the issue #32 tests).

**Recommendation:** pass an injectable configuration through  
the visualization stage (milestone V0.2-07).

## F-019 — Inconsistent `generate_plots.main()` CLI contract

**Component:** `src/visualization/generate_plots.py` (`main()`)

**Finding:** `main()` is annotated `-> None` but returns `True`  
at the end of the "overview" branch and `None` on every other  
path ("timeseries", "polar", "all"). In addition, the `--output`  
option is only honored in "overview" mode: in "all" mode the map  
products are always written to `DEFAULT_OUTPUT_PLOT_PATH` and  
its suffix variants, and the parsed `args.output` value is  
ignored.

**Recommendation:** unify the return behavior (return `None`  
everywhere or a small result object) and honor `--output` in  
"all" mode as documented. Minor cosmetic defect in the same  
function: the `--regions` help text contains an accidental  
line break ("Overlay a  
nalysis regions").

## F-020 — The CLI options of `build_pages` are dead

**Component:** `src/update/build_pages.py` (`parse_args()`,  
`main()`)

**Finding:** `main()` calls `parse_args(argv)` but discards the  
result, so none of the three options has any effect:

- `--clean` suggests opt-in removal of the build directory,  
but `main()` unconditionally deletes `BUILD_DIR` on every  
run if it exists,
- `--log-level` and `--log-file` are parsed but never used; the  
module logger is not configured anywhere in `main()`.

**Impact:** misleading CLI contract. Also a test-relevant edge  
case: `main()` without arguments would parse the *pytest*  
command line and fail on unknown options, so callers must  
always pass an explicit argv.

**Recommendation:** either wire the options (configure logging,  
make `--clean` the opt-out it documents) or remove them  
(milestone V0.2-07).

## F-021 — Missing `output/` only logs a warning

**Component:** `src/update/build_pages.py` (`copy_directory()`,  
`main()`)

**Finding:** `main()` guards `DOCS_DIR` with an explicit  
`FileNotFoundError`, but not `OUTPUT_DIR`: if the output  
directory is missing, `copy_directory()` only logs a warning  
and the build succeeds, silently deploying a website without  
any scientific products (`build/output/` is absent).

Related design note: `DOCS_DIR`, `OUTPUT_DIR` and `BUILD_DIR`  
are definition-time module constants of the same  
non-injectable family as F-010, F-013, F-015 and F-018; the  
issue #33 tests redirect them with `monkeypatch.setattr` on  
the `build_pages` module.

**Recommendation:** fail fast on a missing output directory or  
document the tolerance explicitly as intended behavior  
(milestone V0.2-07).

---

## Documentation Audit (2026-10-03, issue #75)

Cross-check of this document against the actual test suite:
24 test files (1 unit, 4 fixture, 14 component, 5
integration; layout after the #76 reorganization),
148 tests, plus the shared fixtures in `tests/conftest.py`.
Release-level documentation (Test Strategy, Coverage) is
maintained separately in V0.2-08 (#42).

Layout update (2026-10-03, issue #76): the four fixture
verification files moved from `tests/component/` to the new
`tests/fixture_tests/` directory, and
`tests/integration/test_generate_plots.py` was renamed to
`test_generate_plots.py` (typo fix). No test logic changed;
the suite still comprises 148 tests in 24 files. The path
references in this audit section were updated accordingly.

### Entry verification (F-001 … F-021)

| ID | Covering tests (verified in source) | Audit result |
| --- | --- | --- |
| F-001 | `test_duplicate_date_region_observations_keep_last`, `test_incremental_add_preserves_existing_observations` (`tests/component/test_results_manager.py`) | mapping verified |
| F-002 | none referenced (fixed during v0.2) | as documented |
| F-003 | gap tests in `tests/component/test_timeseries_calendar.py` | mapping verified; gap edges → F-030 |
| F-004 | none — import retained as `# noqa: F401` | see audit notes |
| F-005 | none — `save()` return tuple unasserted | gap → F-026 |
| F-006 | `timeseries_paths` fixture in `tests/conftest.py` (eager `analysis_dir.mkdir()`, documented) | mapping verified |
| F-007 | none — trend/R² not testable yet | gap → F-026 |
| F-008 | `test_exact_threshold_observation` + 9 further tests in `tests/component/test_timeseries_threshold_crossing.py` | mapping verified |
| F-009 | none — CLI wiring untested and currently broken | gap → F-023 |
| F-010 | `test_delete_local_data` (`tests/component/test_nsidc_downloader.py`) | mapping verified |
| F-011 | `test_download_error_is_reported_and_leaves_no_file` | mapping verified; remaining paths → F-023 |
| F-012 | none — import retained as `# noqa: F401` | see audit notes |
| F-013 | 14 tests in `tests/component/test_reference_builder.py` | mapping verified |
| F-014 | none — first-run path deliberately untested (issue #30 covered incremental only) | gap → F-027 |
| F-015 | 4 tests in `tests/integration/test_update_pipeline.py` | mapping verified |
| F-016 | `test_no_new_data_keeps_leftover_local_data` + 3 further tests in `tests/integration/test_update_no_new_data.py` | mapping verified; masking scenario → F-028 |
| F-017 | `test_plot_polar_creates_polar_plots` (`tests/component/test_timeseries_plotter.py`) | mapping verified |
| F-018 | `tests/component/test_timeseries_plotter.py` (7 tests), `tests/component/test_sea_ice_map_plot.py` (3), `tests/integration/test_generate_plots.py` (3) | mapping verified |
| F-019 | `tests/integration/test_generate_plots.py` (all products, GeoTIFF fallback, timeseries type) | mapping verified; overview mode → F-025 |
| F-020 | 6 tests in `tests/integration/test_build_pages.py` | mapping verified; option wiring → F-029 |
| F-021 | `test_missing_output_directory_is_tolerated` | mapping verified; decision → F-029 |

Audit notes:

- **F-004 / F-012 are not resolved**: both stray imports are still
  present in the source, now guarded as documented
  `# noqa: F401` exceptions. Their removal is tracked by the
  static-analysis backlog (S-011 … S-018, issues #39/#40). The
  downloader module also carries a third such exception
  (`import shutil  # noqa: F401`) that has no F-entry of its own.
- **F-019**: the cosmetic `--regions` help-text line break is
  resolved in the current source; the functional parts (return
  value, `--output` in "all" mode) remain open and are now
  assigned the test gap F-025.
- No entry had to be marked outdated, duplicated, or
  no-longer-reproducible.

### Test inventory vs. documentation

All 24 test files are accounted for. Files without an F-entry
document no findings; they remain documented through their
introducing issues (see file docstrings).

| Test file | Documented subject | F-entries |
| --- | --- | --- |
| `unit/test_smoke.py` | pytest infrastructure | — |
| `fixture_tests/test_data_fixtures.py` | deterministic CSV/JSON fixtures | — |
| `fixture_tests/test_filesystem_fixtures.py` | `test_environment` isolation | — |
| `fixture_tests/test_raster_fixtures.py` | synthetic raster fixture | — |
| `fixture_tests/test_region_fixtures.py` | region/reference fixtures | — |
| `component/test_nsidc_downloader.py` | NSIDC downloader (#28) | F-009, F-010, F-011, F-012 |
| `component/test_reference_builder.py` | ReferenceBuilder (#29) | F-013 |
| `component/test_region_analyzer.py` | RegionAnalyzer (#18) | — |
| `component/test_region_analyzer_validity.py` | RegionAnalyzer validity checks | — |
| `component/test_results_manager.py` | ResultsManager (#20) | F-001, F-002, F-006 |
| `component/test_sea_ice_map_plot.py` | SeaIcePlotter (#32) | F-018 |
| `component/test_timeseries_anomalies.py` | anomaly calculation | — |
| `component/test_timeseries_calendar.py` | calendar interpolation | F-003 |
| `component/test_timeseries_climatology.py` | climatology | — |
| `component/test_timeseries_event_window.py` | event windows (#27) | F-008 |
| `component/test_timeseries_moving_average.py` | moving average (#22) | — |
| `component/test_timeseries_plotter.py` | TimeSeriesPlotter (#32) | F-007, F-017, F-018 |
| `component/test_timeseries_threshold_crossing.py` | threshold crossing (#26) | F-008 |
| `component/test_timeseries_yearly.py` | complete years / annual means (#25) | — |
| `integration/test_build_pages.py` | Pages build (#33) | F-020, F-021 |
| `integration/test_generate_plots.py` | plot generation CLI (#32) | F-018, F-019 |
| `integration/test_spatial_processing_chain.py` | spatial processing chain (#29) | F-013, F-015 |
| `integration/test_update_no_new_data.py` | no-new-data behavior (#31) | F-014, F-015, F-016 |
| `integration/test_update_pipeline.py` | update orchestration (#30) | F-014, F-015, F-016 |

Audit remarks (for the follow-up issues):

- `tests/integration/test_generate_plots.py` — filename typo
  ("gernerate") resolved by the #76 rename.
- `src/analysis/process_data.py` (`main()`) calls the private
  `RegionAnalyzer._extract_date()` — design/testability candidate
  for the #73 hard-wiring inventory.
- #76 review outcome: the `tests/component/` files for
  calendar, moving average, climatology, and anomalies
  construct `TimeSeriesAnalyzer` and write controlled CSV
  inputs — they exercise the complete component with real
  file I/O, not isolated units, and remain component tests.
  No test met the unit criterion (mocked, no I/O); only the
  fixture verification tests were moved to
  `tests/fixture_tests/`.

### Missing tests (audit backlog F-022 … F-030)

Overview additions — merge these rows into the Overview table:

| ID | Issue | Component | Category | Status |
| --- | --- | --- | --- | --- |
| F-022 | #75 | main.py (dispatcher) | gap | proposed |
| F-023 | #75 | download_data.py (CLI) | gap | proposed |
| F-024 | #75 | process_data.py (CLI) | gap | proposed |
| F-025 | #75 | generate_plots.py (overview mode) | gap | proposed |
| F-026 | #75 | timeseries_analyzer.py (trend, save) | gap | proposed |
| F-027 | #75 | update_pipeline.py (first run) | gap | proposed |
| F-028 | #75 | update_pipeline.py (masking) | gap | proposed |
| F-029 | #75 | build_pages.py (CLI options) | gap | proposed |
| F-030 | #75 | timeseries_analyzer.py (gap edges) | gap | proposed |

## F-022 — Pipeline dispatcher has no tests

**Component:** `src/main.py` (0 % coverage, 70 stmts)

**Finding:** the CLI dispatcher (six stages: download, process,
plots, build, update, all) has no test at all: argument parsing,
`--log-level`/`--log-file` propagation, forwarding of the plots
flags (`--regions`, `--region`, `--all-regions`, `--show`) and of
`--keep-data` to the update stage, and the "all" sequence are
unverified.

**Recommendation:** unit tests against injected stage doubles
(monkeypatching the module-level `STAGES` map works today);
proper seams per #73 preferred.

**Dependencies:** #73, #74.

## F-023 — Download CLI untested and currently broken

**Component:** `src/data_download/download_data.py` (0 % coverage)

**Finding:** no test covers the CLI flags (`--base-url`,
`--output-dir`, `--product`, appendable `--year`/`--month`,
`--dry-run`), and the `main()` wiring fails at runtime with the
F-009 `TypeError` — a test of the wiring would currently fail.

**Recommendation:** `parse_args` unit tests can be added
immediately (pure function); the `main()` wiring test is blocked
by the F-009 fix (functional correction, milestone V0.2-07).

**Dependencies:** F-009 fix, #74.

## F-024 — Process CLI date-filter paths untested

**Component:** `src/analysis/process_data.py` (47 % coverage,
arg-parsing lines 68–145)

**Finding:** untested: `--start-date`/`--end-date` filtering
(inclusive boundaries), the skip path via
`is_date_processed()`, the per-file exception counting into
`failed_files`, and the `ProcessSummary` return value.

**Recommendation:** component tests with injected collaborators
per #73; `parse_args` unit tests possible immediately.

**Dependencies:** #73.

## F-025 — Overview plot mode and `--output` untested

**Component:** `src/visualization/generate_plots.py` (67 %
coverage)

**Finding:** the "overview" mode branches (plain, `--regions`,
`--region`, `--all-regions`, `--bounds`, `--title`, `--output`)
have no test, and `--output` is ignored in "all" mode (F-019) —
including the computed-but-unused `output = Path(args.output)`.

**Recommendation:** mode-dispatch tests after the F-019 fix;
the overview-mode branches can be tested against injected
plotters.

**Dependencies:** F-019 fix, #73.

## F-026 — Trend/R² and `save()` return unasserted

**Component:** `src/analysis/timeseries_analyzer.py` (84 %
coverage)

**Finding:** the inline trend/R² computation is untestable (F-007)
and `save()` returns an unasserted tuple (F-005).

**Recommendation:** after the F-007 extraction (design decision
pending), add trend/R² unit tests; add a `save()` return-value
test.

**Dependencies:** F-005, F-007 extraction.

## F-027 — First-run pipeline test missing

**Component:** `src/update/update_pipeline.py` (`main()`)

**Finding:** F-014 documents the first-run crash
(`None.isoformat()`); issue #30 deliberately covered only the
incremental path, so the empty-results-state behavior remains
unverified.

**Recommendation:** add the first-run test once the F-014 fix
decision is made (proposed there: omit `--start-date` when
`None`).

**Dependencies:** F-014 fix decision.

## F-028 — Masking scenario test missing

**Component:** `src/update/update_pipeline.py`, `NSIDCDownloader.sync()`

**Finding:** F-016 documents that locally present but unprocessed
files can mask observations as "no new data" forever. The
documented no-new-data tests pin the fully-processed state only;
the masking scenario has no test.

**Recommendation:** add the test once the F-016 semantics
decision is made (re-validate files vs. processed-state boundary).

**Dependencies:** F-016 decision.

## F-029 — build_pages CLI options untested

**Component:** `src/update/build_pages.py` (`parse_args()`, `main()`)

**Finding:** the CLI options are dead (F-020) and the missing-
`output/` tolerance is pinned by
`test_missing_output_directory_is_tolerated` (F-021); no test
covers the intended option wiring, because there is none.

**Recommendation:** add option tests once the F-020/F-021
decisions are made (wire or remove the options; fail-fast or
documented tolerance).

**Dependencies:** F-020, F-021 decisions (#74).

## F-030 — Interpolation gap-edge semantics undecided and untested

**Component:** `src/analysis/timeseries_analyzer.py`
(`interpolate_calendar()`)

**Finding:** F-003 documents the per-direction `limit` fill; the
calendar tests deliberately exclude the gap edges, so the actual
edge behavior is unasserted for any pandas version.

**Recommendation:** decide the intended semantics (F-003),
then add gap-edge tests that pin the decision.

**Dependencies:** F-003 decision.
