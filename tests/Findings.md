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

| ID    | Issue | Component                           | Category  | Status        |
| ----- | ----- | ----------------------------------- | --------- | ------------- |
| F-001 | #20   | ResultsManager                      | bug       | fixed         |
| F-002 | #20   | ResultsManager                      | bug       | fixed         |
| F-003 | #21   | TimeSeriesAnalyzer                  | semantics | fixed         |
| F-004 | #21   | TimeSeriesAnalyzer                  | design    | fixed         |
| F-005 | #21   | TimeSeriesAnalyzer                  | design    | fixed         |
| F-006 | #21   | TimeSeriesAnalyzer                  | design    | documented    |
| F-007 | #25   | TimeSeriesPlotter                   | design    | fixed         |
| F-008 | #26   | TimeSeriesAnalyzer                  | design    | fixed         |
| F-009 | #28   | download\_data.py / NSIDCDownloader | bug       | fixed         |
| F-010 | #28   | NSIDCDownloader                     | design    | fixed         |
| F-011 | #28   | NSIDCDownloader                     | design    | fixed         |
| F-012 | #28   | NSIDCDownloader                     | design    | fixed         |
| F-013 | #29   | ReferenceBuilder                    | design    | fixed         |
| F-014 | #30   | update\_pipeline                    | bug       | fixed         |
| F-015 | #30   | update\_pipeline / process\_data    | design    | fixed         |
| F-016 | #31   | update\_pipeline / downloader       | design    | fixed         |
| F-017 | #32   | timeseries\_plot                    | design    | fixed         |
| F-018 | #32   | visualization stage                 | design    | fixed         |
| F-019 | #32   | generate\_plots                     | design    | fixed         |
| F-020 | #33   | build\_pages                        | design    | fixed         |
| F-021 | #33   | build\_pages                        | design    | fixed         |

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

**Resolution (#103, 2026-10-17):** the per-direction fill is
not the intended scientific behavior. The gap limit now
applies to the total gap size: a gap is interpolated only when
at most `INTERPOLATION_LIMIT_DAYS` consecutive days are
missing between two observed values, and it is then filled
completely in the forward direction. Longer gaps stay
missing entirely (no edge fills), and missing days without a
preceding observation are never backfilled. Small gaps keep
single missing days from excluding a region-year; real data
outages remain visible.

**Test note:** `test_gap_just_above_limit_is_not_filled_at_all`
and `test_leading_missing_days_are_never_filled` in
`tests/component/test_timeseries_calendar.py` pin both decided
edges (15-day gap unfilled; forward-only fill);
`test_gap_exceeding_maximum_remains_unbridged` now asserts that
no day of a 39-day gap is filled. Backlog F-030 resolved.

## F-004 — Stray `from curses import window` import

**Component:** `src/analysis/timeseries_analyzer.py` (module header)

**Finding:** unused, accidental import (IDE auto-import artifact).  
`curses` is Unix-only in the standard library, so the module fails  
to import on Windows.

**Recommendation:** remove the import line.

**Resolution (#39, 2026-10-04):** import removed; the module  
now also imports cleanly on Windows (S-005 / S-013 closed).

## F-005 — `save()` return annotation does not match the return value

**Component:** `src/analysis/timeseries_analyzer.py` (`save()`)

**Finding:** annotated `-> Path` but returns the tuple  
`(self.output_path, self.yearly_output_path)`. The events output  
path is written but not returned.

**Recommendation:** correct the annotation to  
`-> tuple[Path, Path]` (and consider returning the events path as  
well).

**Resolution (#102, 2026-10-17):** the return value was removed
instead. No caller ever consumed the tuple, and the written
paths are constructor state, so `save()` is now annotated
`-> None` and returns nothing. The same contract is applied to
`ResultsManager.save()`, which returned the persisted frame
without any caller using it. A return value can be re-added
cleanly if a consumer ever needs one.

**Test note:** `test_save_returns_none` in
`tests/component/test_results_manager.py` and
`tests/component/test_timeseries_yearly.py` pins the None
contract on both save paths. Backlog F-026 resolved.

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

**Resolution (#102, 2026-10-17):** the design decision is the
data-product variant. The pure module function
`compute_linear_trend(x, y)` in
`src/analysis/timeseries_analyzer.py` returns slope, intercept
and R² (NaN for zero total variance); the analyzer persists the
trend of the relative annual means per region as the columns
`relative_mean_trend_slope`, `relative_mean_trend_intercept`
and `relative_mean_trend_r_squared` in the yearly product.
`plot_yearly_means()` reads the stored values instead of
refitting, and the threshold-duration plot calls the same
helper for its inline fit. The yearly figure remains
byte-stable: the stored values are exactly the previous
polyfit results.

**Test note:** `tests/unit/test_linear_trend.py` pins the helper
with hand calculations (noisy fit, perfect fit, constant
series, two points);
`test_yearly_means_include_trend_columns`
(`tests/component/test_timeseries_yearly.py`) pins the stored
per-region columns including the single-year NaN edge. Backlog
F-026 resolved.

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

**Resolution (#103, 2026-10-17):** the strict-threshold
semantics is decided: an observation exactly on the threshold
lies on the target side. The crossing conditions are
inclusive (`down`: y0 >= threshold, y1 <= threshold, y0 > y1;
`up`: y0 <= threshold, y1 >= threshold, y0 < y1), so a series
that sits exactly on a threshold and continues in the event
direction now registers a crossing dated to the day on the
threshold (fraction 0). Two equal days (including both
exactly on the threshold) remain no crossing. With the
inclusive conditions the interpolated fraction is provably in
[0, 1], so the last remaining range guard in
`_persistent_crossing_at` was removed as unreachable.

**Test note:** `test_exact_threshold_observation` and the new
`test_threshold_equality_edges`
(`tests/component/test_timeseries_threshold_crossing.py`) pin
the decided edges; `test_crossed_between_handles_threshold_equality`
(`tests/unit/test_threshold_crossing_helpers.py`) pins the
condition helper. All other pinning tests stay green
unchanged. Backlog F-030 resolved.

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

**Resolution (#98, 2026-10-06):** variant A implemented. The
CLI keeps its appendable --year/--month flags; the new pure
helper ``build_sync_ranges()`` maps the selection to one
inclusive start/end date range per selected year (or per
year-month combination), and ``main()`` loops over the
ranges, merges the per-range ``DownloadSummary`` results and
passes only the supported ``start_date`` / ``end_date`` /
``dry_run`` arguments to ``sync()``. Invalid selections
(month without year, non-numeric or out-of-range values) are
rejected by ``parse_args()`` via ``parser.error()``. The
unfiltered default remains a single sync call; with filters
each range logs its own synchronizing/finished pair.

**Test note:** the download CLI parsing, construction wiring
and the sync() call arguments are tested in
`tests/unit/test_download_data.py` (issues #73/#97; the
argument contract added in #98). Backlog F-023 resolved.

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

**Status update (#104, 2026-10-18):** fixed. The cleanup root is  
an injectable keyword-only parameter,  
``delete_local_data(*, geotiff_root=GEOTIFF_DIR)``, following  
the #73/#74 injection pattern with the central ``GEOTIFF_DIR``  
from ``paths.py`` as the production default. The call-time  
``DATA_DIR / "geotiff"`` join and its namespace seam are gone;  
``update_pipeline`` calls the cleanup without arguments, so  
production behavior is unchanged. The docstring now matches the  
implemented semantics (empty month/year directories are  
removed, other files survive).  

**Test note (#104):** the test injects the isolated cleanup  
root via ``geotiff_root`` instead of monkeypatching ``DATA_DIR``;  
the new  
``test_delete_local_data_default_root_is_geotiff_dir`` pins the  
production default. The namespace patch is gone.  

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

**Resolution (#100, 2026-10-09):** downloads are atomic. Each
attempt streams into a ``<filename>.part`` temp file in the
target directory; only a complete stream is moved to the final
path with ``os.replace()``. ``requests.RequestException`` is
caught per attempt and retried at most
``DOWNLOAD_MAX_ATTEMPTS`` (3) times before the file is skipped
(counted in ``failed_files``; the sync run continues). Temp
files are removed after every failed attempt and at the end,
so interrupted downloads never leave a partial file at the
final path. Non-OK HTTP statuses keep the previous immediate
``False`` behavior without retry.

**Test note:** issue #28 covers the handled HTTP-error path;
issue #100 adds the retry-and-atomicity tests
(`test_interrupted_download_recovers_on_retry`,
`test_interrupted_download_gives_up_after_three_attempts`,
`test_stale_temp_file_is_removed_before_downloading`) in
`tests/component/test_nsidc_downloader.py`.

## F-012 — Stray `from os import link` import

**Component:** `src/data_download/downloader.py` (module header)

**Finding:** unused, accidental import (IDE auto-import artifact,  
same pattern as F-004). Harmless because `os` is always  
available, but dead code.

**Recommendation:** remove the import line.

**Resolution (#39, 2026-10-04):** import removed together  
with the undocumented companion `import shutil` (S-011);  
the loop-variable shadowing (F402) resolved itself with  
the removal.

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

**Status update (#104, 2026-10-18):** fixed. The constructor  
accepts the injectable keyword-only output paths ``mask_dir``  
(default ``REFERENCE_FILTERS_DIR``) and ``summary_path``  
(default ``REFERENCE_SUMMARY_JSON``), analogous to  
``RegionAnalyzer`` and the #73/#74 injection pattern; ``build()``,  
``_save_summary()`` and ``ensure_reference()`` read the  
instance attributes instead of the module constants. The  
naturalearth ocean read stays on the module constant  
``OCEAN_SHAPEFILE`` (config-centralization policy: reads use  
``paths.py`` as the single source of truth); tests keep  
stubbing the ``gpd`` collaborator, which is a collaborator  
stub, not a path seam.  

**Test note (#104):** the four component build-path tests and  
the integration chain  
(``tests/integration/test_spatial_processing_chain.py``) inject  
``mask_dir``/``summary_path`` through the constructor; the new  
``test_reference_builder_output_defaults_are_central`` pins the  
production defaults. The ``FILTER_DIR``/``REFERENCE_SUMMARY``  
namespace patches are gone.  

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

**Resolution (#99, 2026-10-09):** the process stage receives
--start-date only when a latest processed date exists. On a
first run the pipeline requests the complete remote archive
(sync without start_date; locally present files are skipped
by the sync's equivalence check) and processes every locally
available observation (no --start-date). Incremental runs are
unchanged. The masking scenario (files present locally but
never processed) remains a separate decision (F-016).

**Test note:**
`test_update_first_run_processes_all_observations`
(`tests/integration/test_update_pipeline.py`, issue #99) pins
the first-run path. Backlog F-027 resolved.

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

**Status update (#73, 2026-10-04):** partially resolved for
`src/analysis/process_data.py`: the stage now accepts injected
collaborators and paths (reference builder, results manager,
analyzer factory, time-series analyzer, data directory). For
`src/update/update_pipeline.py` the namespace-replacement test
design (issue #30) remains; a full configuration injection is
`#74` scope.

**Status update (#106, 2026-10-18):** fully resolved for
`update_pipeline.py`. The pipeline accepts its collaborators
as injectable keyword arguments with the production defaults
(`results_factory`, `downloader_factory`, `process_stage`,
`plots_stage`, `build_stage`), following the #73/#74 injection
pattern; the update integration tests pass the controlled
implementations explicitly and the namespace replacements in
the `src.update.update_pipeline` module are gone.

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

**Resolution (#101, 2026-10-16):** the no-new-data decision
now reconciles both sources independently. The sync stage is
unchanged (a locally present file needs no re-download), and
the pipeline additionally compares the local archive against
the processed state: the new
`NSIDCDownloader.count_local_files_after(latest)` counts the
local GeoTIFF files whose observation date lies after the
latest processed date (all local files when no processed state
exists), and the early exit now requires zero downloads AND
zero locally present but unprocessed files. Locally present
unprocessed observations are therefore detected and
processed; the process stage's deduplication
(`is_date_processed`) keeps the run idempotent, and the
cleanup stays tied to downloads (a masking run's local files
remain, as pinned for leftovers in the issue #31 tests).

**Test note:** issue #31 pins the documented no-new-data
behavior for a fully processed state. Issue #101 adds the
deliberate masking tests:
`test_update_processes_local_files_without_downloads`
(`tests/integration/test_update_pipeline.py`) pins the
pipeline-level scenario, and
`test_count_local_files_after_ignores_processed_files`,
`test_count_local_files_after_without_boundary_counts_all`
and `test_count_local_files_after_missing_directory`
(`tests/component/test_nsidc_downloader.py`) cover the
counting method. Backlog F-028 resolved.

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

**Resolution (#38, 2026-10-04):** the unused attribute was  
removed from `_configure_style()`. The polar products remain  
in `output/plots/timeseries/` next to the Cartesian plots, as  
pinned by the issue #32 tests; the whitelist entry (S-004)  
was removed together with the attribute.

**Status update (#113, 2026-10-17):** reopened and resolved by
the plot-tree restructure. The products are now organized by
scientific product class: the polar plots live in
`output/plots/daily_timeseries/polar/{relative,absolute}/`,
in their own directory per quantity — the original F-017
intention (a dedicated polar output directory) is realized as
part of the product-class tree. The previous tree
(`output/plots/timeseries/` with `anomalies/` and
`thresholds/` subdirectories, polar files next to the
Cartesian plots, overview maps at the plots root as
`sea_ice_geotiff_overview*.png`) is documented here for
traceability; no product remains in the legacy locations.

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

**Status update (#74, 2026-10-04):** partially resolved.
The first bullet is addressed: `generate_plots.main()`
accepts the plotter through the injectable `ts_factory`
seam since issue #74, and the integration tests pass the
controlled `TimeSeriesPlotter` explicitly instead of
replacing the generate_plots namespace. The `SeaIcePlotter`
paths (regions.json default, `DEFAULT_OUTPUT_PLOT_PATH` in
"all" mode) remain namespace-patched and stay open.

**Status update (#106, 2026-10-18):** fully resolved. All
remaining seams are injectable now: the plotter accepts the
output directory through the `output_dir` constructor
parameter; `SeaIcePlotter` accepts `region_file`, `data_dir`
and `default_output_path` (the regions.json fallback and the
GeoTIFF fallback directory keep their production defaults as
call-time module reads), and `build_pages.main()` accepts
`html_dir`/`output_dir`/`build_dir` with the module constants
as defaults. Every visualization and build test injects the
isolated paths explicitly; the namespace patches of the
issue #32/#33 test designs are gone.

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

**Status update (#74, 2026-10-04):** partially resolved.
The `return True` inconsistency is removed — every `main()`
path returns `None` again — and the dead `args.output` read
in "all" mode is gone. `main()` is split into pure parsing,
the table-driven `RUNNERS` dispatch, and one runner per plot
mode with injectable plotter factories (#73 pattern). The
`--output` behavior in "all" mode and the unused `--title`
option remain open for the CLI parity issue.

**Status update (#106, 2026-10-18):** fully resolved. The CLI
contract is consistent now: the dispatcher and the module CLI
share one argument specification per stage
(`add_arguments` plus `logging_config.add_log_arguments`),
every live option is forwarded with its value, and the dead
`--title` option is removed. `--output` is deliberately
honored by the "overview" mode only: the "all" mode writes
the map products to the spatial product class of the #113
plot tree, where a per-figure output path would break the
product-class layout (documented intended behavior). The
"all" pipeline mode now forwards the required positional
plot type, so a real dispatcher run no longer exits in the
argument parser.

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

**Status update (#105, 2026-10-18):** fixed. Both decisions  \
implemented: ``--log-level``/``--log-file`` are wired through  \
``configure_logging()`` in ``main()`` exactly like every other  \
stage (dispatcher and update_pipeline forward them unchanged),  \
and the misleading ``--clean`` option is removed — the build  \
always starts from scratch, which the reproducible-rebuild  \
tests already pin. ``parse_args`` now carries the shared  \
logging defaults (level ``INFO``, file ``DEFAULT_LOG_FILE``).  

**Test note (#105):** ``test_parse_args_logging_defaults_match_other_stages``  \
pins the shared defaults,  \
``test_parse_args_rejects_removed_clean_option`` pins the  \
removal; every integration test passes an explicit argv with  \
``--log-file`` under the isolated root. Backlog F-029 resolved.  

## F-021 — Missing `output/` only logs a warning

**Component:** `src/update/build_pages.py` (`copy_directory()`,  
`main()`)

**Finding:** `main()` guards `HTML_DIR` with an explicit  
`FileNotFoundError`, but not `OUTPUT_DIR`: if the output  
directory is missing, `copy_directory()` only logs a warning  
and the build succeeds, silently deploying a website without  
any scientific products (`build/output/` is absent).

Related design note: `HTML_DIR`, `OUTPUT_DIR` and `BUILD_DIR`  
are definition-time module constants of the same  
non-injectable family as F-010, F-013, F-015 and F-018; the  
issue #33 tests redirect them with `monkeypatch.setattr` on  
the `build_pages` module.

**Recommendation:** fail fast on a missing output directory or  
document the tolerance explicitly as intended behavior  
(milestone V0.2-07).

**Status update (#77, 2026-10-04):** path update only. The
static website source moved from `docs/` to the dedicated
top-level `html/` folder (`HTML_DIR` in `src/config/paths.py`);
`docs/` now contains only the project documentation, and
`build/` remains the generated GitHub Pages artifact. The
namespace seam and the tolerated missing-`output/` behavior
are unchanged; the finding stays open (decision F-029).

**Status update (#105, 2026-10-18):** fixed. Fail-fast decided:
a missing ``OUTPUT_DIR`` raises ``FileNotFoundError`` like a
missing ``HTML_DIR`` — silently deploying a website without any
scientific products would hide an upstream failure in the
scheduled update workflow. The ``copy_directory()`` warning
branch remains as a generic helper guard but is unreachable
from ``main()``.

**Test note (#105):** the former tolerance test
``test_missing_output_directory_is_tolerated`` is rewritten as
``test_missing_output_directory_fails_the_build`` and asserts
the ``FileNotFoundError`` plus an unpopulated build directory.
The namespace seam (module constants) is unchanged and remains
documented under F-018. Backlog F-029 resolved.

* * *

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
| F-003 | gap tests + gap-edge tests in `tests/component/test_timeseries_calendar.py` (#103) | resolved (#103) |
| F-004 | none — import removed in #39; no test required | resolved (#39) |
| F-005 | `test_save_returns_none` + `test_empty_result_handling` (`tests/component/test_results_manager.py`); `test_save_returns_none` (`tests/component/test_timeseries_yearly.py`) (#102) | resolved (#102) |
| F-006 | `timeseries_paths` fixture in `tests/conftest.py` (eager `analysis_dir.mkdir()`, documented) | mapping verified |
| F-007 | `tests/unit/test_linear_trend.py`; `test_yearly_means_include_trend_columns` (`tests/component/test_timeseries_yearly.py`) (#102) | resolved (#102); backlog F-026 resolved |
| F-008 | `test_exact_threshold_observation` + `test_threshold_equality_edges` (`tests/component/test_timeseries_threshold_crossing.py`), `test_crossed_between_handles_threshold_equality` (`tests/unit/test_threshold_crossing_helpers.py`) (#103) | resolved (#103) |
| F-009 | `tests/unit/test_download_data.py` (sync argument contract, #98) | resolved (#98) |
| F-010 | `test_delete_local_data` (`tests/component/test_nsidc_downloader.py`) | mapping verified |
| F-011 | `test_download_error_is_reported_and_leaves_no_file` + 3 retry/atomicity tests (#100) | resolved (#100) |
| F-012 | none — import removed in #39; no test required | resolved (#39) |
| F-013 | 14 tests in `tests/component/test_reference_builder.py` | mapping verified |
| F-014 | `test_update_first_run_processes_all_observations` (`tests/integration/test_update_pipeline.py`, #99) | resolved (#99) |
| F-015 | 6 tests in `tests/integration/test_update_pipeline.py` + 4 in `test_update_no_new_data.py` (collaborators injected, #106) | resolved (#106) |
| F-016 | `test_no_new_data_keeps_leftover_local_data` + 3 further tests in `tests/integration/test_update_no_new_data.py`; masking tests in `tests/integration/test_update_pipeline.py` + `tests/component/test_nsidc_downloader.py` (#101) | resolved (#101); backlog F-028 resolved |
| F-017 | `test_plot_polar_creates_polar_plots` (`tests/component/test_timeseries_plotter.py`) | resolved (#113; plot tree restructure) |
| F-018 | `tests/component/test_timeseries_plotter.py` (7 tests), `tests/component/test_sea_ice_map_plot.py` (3), `tests/integration/test_generate_plots.py` (3) — paths injected since #106 | resolved (#106) |
| F-019 | `tests/unit/test_generate_plots_cli.py` + `tests/integration/test_generate_plots.py` (CLI parity, #106) | resolved (#106); overview mode → F-025 |
| F-020 | 8 tests in `tests/integration/test_build_pages.py` | resolved (#105) |
| F-021 | `test_missing_output_directory_fails_the_build` | resolved (#105) |

Audit notes:

- **F-004 / F-012 resolved in #39**: both stray imports were
  removed together with the undocumented third exception
  (`import shutil`, tracked by S-011). The remaining `noqa`
  exceptions (S-017 E402, S-018 C901) suppress other rule
  families and are handled by #40.
- **F-019**: the cosmetic `--regions` help-text line break is
  resolved in the current source; the functional parts (return
  value, `--output` in "all" mode) remain open and are now
  assigned the test gap F-025.
- No entry had to be marked outdated, duplicated, or
  no-longer-reproducible.

### Test inventory vs. documentation

All 33 test files are accounted for. Files without an F-entry
document no findings; they remain documented through their
introducing issues (see file docstrings).

| Test file | Documented subject | F-entries |
| --- | --- | --- |
| `unit/test_smoke.py` | pytest infrastructure | — |
| `unit/test_download_data.py` | download CLI parsing/dispatch (#73; unit level #97) | F-023 |
| `unit/test_downloader_helpers.py` | downloader pure helpers (#97) | — |
| `unit/test_event_window_bounds.py` | event-window boundaries (#97) | F-008 |
| `unit/test_generate_plots_cli.py` | plot CLI parsing/dispatch (#74; unit level #97) | F-019, F-025 |
| `unit/test_main.py` | pipeline dispatcher (#73; unit level #97) | F-022 |
| `unit/test_moving_average.py` | moving-average unit calculation (#97) | — |
| `unit/test_process_data.py` | process CLI parsing/dispatch (#73; unit level #97) | F-024 |
| `unit/test_region_analyzer_extract_date.py` | filename date extraction (#97) | — |
| `unit/test_threshold_crossing_helpers.py` | threshold-crossing helpers (#97) | F-008 |
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
  for the #73 hard-wiring inventory. Resolved in #73: the public
  `RegionAnalyzer.extract_date()` wrapper is called instead.
- #76 review outcome: the `tests/component/` files for
  calendar, moving average, climatology, and anomalies
  construct `TimeSeriesAnalyzer` and write controlled CSV
  inputs — they exercise the complete component with real
  file I/O, not isolated units, and remain component tests.
  No test met the unit criterion (mocked, no I/O); only the
  fixture verification tests were moved to
  `tests/fixture_tests/`.

Layout update (issue #97): the pure parsing and dispatch tests
of the CLI entry points (issues #73/#74) were reclassified as
unit tests and moved to `tests/unit/` together with new
pure-helper unit tests (issue #97). The unit level now
comprises ten files; the inventory table above was updated
accordingly.

### Missing tests (audit backlog F-022 … F-030)

Overview additions — merge these rows into the Overview table:

| ID | Issue | Component | Category | Status |
| --- | --- | --- | --- | --- |
| F-022 | #75 | main.py (dispatcher) | gap | resolved (#73; unit level #97) |
| F-023 | #75 | download_data.py (CLI) | gap | resolved (#73; sync contract #98) |
| F-024 | #75 | process_data.py (CLI) | gap | resolved (#73; unit level #97) |
| F-025 | #75 | generate_plots.py (overview mode) | gap | resolved (#106) |
| F-026 | #75 | timeseries_analyzer.py (trend, save) | gap | resolved (#102) |
| F-027 | #75 | update_pipeline.py (first run) | gap | resolved (#99) |
| F-028 | #75 | update_pipeline.py (masking) | gap | resolved (#101) |
| F-029 | #75 | build_pages.py (CLI options) | gap | resolved (#105) |
| F-030 | #75 | timeseries_analyzer.py (gap edges) | gap | resolved (#103) |

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

**Status update (#73, 2026-10-04):** resolved. The dispatcher
received the injectable `stages` mapping and the extracted
`build_stage_args()`; `tests/unit/test_main.py` covers
argument parsing, flag forwarding, and the "all" sequence with
injected stage doubles. The argument-parity review between
dispatcher and stage modules remains with #74.

**Status update (#106, 2026-10-18):** the parity review is
resolved: every stage sub-parser is built from the same
`add_arguments` specification as the stage module CLI, and
the new dispatcher tests pin the option parity (see F-019).

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

**Status update (#73, 2026-10-04):** partially resolved.
`parse_args` and the constructor wiring are covered by
`tests/unit/test_download_data.py` via the new
`downloader_factory` seam. The `sync()` call itself remains
unasserted because the wiring is broken (F-009 design decision
pending); the functional contract test comes with the F-009
fix.

**Status update (#98, 2026-10-06):** fully resolved. The
F-009 fix (variant A) is implemented and the `sync()` call
arguments are asserted in `tests/unit/test_download_data.py`;
nothing remains open here.

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

**Status update (#73, 2026-10-04):** resolved. The loop is
extracted as `process_geotiffs()` with an injectable analyzer
factory; `tests/component/test_process_data.py` covers the
inclusive date-filter boundaries, the `is_date_processed()`
skip path, the exception counting, and a complete `main()`
run with injected collaborators.

**Status update (#74, 2026-10-04):** partially resolved.
`tests/component/test_generate_plots_cli.py` covers the
dispatch of every plot mode with controlled plotters: the
overview branches (plain, `--regions`, `--region`,
`--all-regions`, `--show`), the "all" product sequence, and
the missing-GeoTIFF fallback. The `--output` decision for
"all" mode and the real-rendering overview integration
remain with the CLI parity issue and
`tests/component/test_sea_ice_map_plot.py`.

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

**Status update (#106, 2026-10-18):** resolved. The overview
mode branches are covered by
`tests/unit/test_generate_plots_cli.py` (plain, `--regions`,
`--region`, `--all-regions`, `--show`), the `--output`
contract is decided (overview only, see F-019), and the option
parity between the dispatcher and the stage modules is pinned
by `test_dispatcher_subparsers_match_stage_modules`.

## F-026 — Trend/R² and `save()` return unasserted

**Component:** `src/analysis/timeseries_analyzer.py` (84 %
coverage)

**Finding:** the inline trend/R² computation is untestable (F-007)
and `save()` returns an unasserted tuple (F-005).

**Recommendation:** after the F-007 extraction (design decision
pending), add trend/R² unit tests; add a `save()` return-value
test.

**Dependencies:** F-005, F-007 extraction.

**Status update (#102, 2026-10-17):** resolved. The trend/R²
extraction (F-007) and the consistent `save()` contract
(F-005) are implemented; `tests/unit/test_linear_trend.py`,
`test_yearly_means_include_trend_columns` and the two
`test_save_returns_none` tests close both parts of the gap.

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

**Status update (#101, 2026-10-16):** resolved. The F-016
masking semantics is decided and pinned by
`test_update_processes_local_files_without_downloads`
(`tests/integration/test_update_pipeline.py`) and the three
`count_local_files_after` tests
(`tests/component/test_nsidc_downloader.py`).

## F-029 — build_pages CLI options untested

**Component:** `src/update/build_pages.py` (`parse_args()`, `main()`)

**Finding:** the CLI options are dead (F-020) and the missing-
`output/` behavior is pinned by
`test_missing_output_directory_fails_the_build` (F-021, fixed
in #105); no test covers the intended option wiring, because
there is none.

**Recommendation:** add option tests once the F-020/F-021
decisions are made (wire or remove the options; fail-fast or
documented tolerance).

**Dependencies:** F-020, F-021 decisions (#74).

**Status update (#105, 2026-10-18):** resolved. Both decisions
are made and implemented: the logging options are wired
(F-020), the dead --clean option is removed, and the missing
output/ directory fails fast (F-021). The option contract is
pinned by the two new parse_args tests plus the rewritten
failure-propagation test in `tests/integration/test_build_pages.py`.

## F-030 — Interpolation gap-edge semantics undecided and untested

**Component:** `src/analysis/timeseries_analyzer.py`
(`interpolate_calendar()`)

**Finding:** F-003 documents the per-direction `limit` fill; the
calendar tests deliberately exclude the gap edges, so the actual
edge behavior is unasserted for any pandas version.

**Recommendation:** decide the intended semantics (F-003),
then add gap-edge tests that pin the decision.

**Dependencies:** F-003 decision.

**Status update (#103, 2026-10-17):** resolved. The F-003 gap
semantics is decided (total gap size, forward-only fill) and
pinned by the gap-edge tests in
`tests/component/test_timeseries_calendar.py`; the F-008
strict-threshold decision is pinned alongside
(see F-003 / F-008 resolutions).
