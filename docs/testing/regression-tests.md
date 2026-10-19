# Regression Tests

This document maps the regression cases of
`docs/testing/test-levels.md`, section 6, to the tests that
protect them (issue #41).

Regression testing is a cross-cutting activity, not an
independent test level: every case below is implemented at
the lowest level that adequately verifies the protected
behavior (test-levels.md, sections 6.1 and 10). The suite
uses **no pytest markers**; a regression test is an ordinary
test of its level, and this map is the regression view.

Findings are registered in `tests/Findings.md` (F-001 …
F-031); the map below references the relevant entries.

## 6.2 Scientific Regression Cases

| Case | Protecting tests | Notes |
| ---- | ---------------- | ----- |
| Threshold crossing | `tests/component/test_timeseries_threshold_crossing.py`, `tests/unit/test_threshold_crossing_helpers.py` | inclusive threshold edges (F-008, #103) |
| Persistence | `tests/component/test_timeseries_threshold_crossing.py` | persistence windows, consecutive-day requirement |
| Break-up / freeze-up boundaries | `tests/unit/test_event_window_bounds.py`, `tests/component/test_timeseries_event_window.py` | seasonal windows (Mar 16 / Sep 15 / Sep 16 / Mar 15) |
| Late freeze-up | `tests/component/test_timeseries_event_window.py` | extended freeze-up search after an early break-up |
| Year transitions | `tests/component/test_timeseries_event_window.py`, `tests/unit/test_yearly_means.py` | freeze-up across the year boundary; per-year aggregation |
| Leap years | `tests/unit/test_complete_year_filter.py`, `tests/unit/test_climatology_anomalies.py`, `tests/component/test_timeseries_calendar.py` | 366-day requirement; leap day as its own calendar group |
| Missing observations | `tests/unit/test_interpolation_gaps.py`, `tests/unit/test_calendar_reconstruction.py` | NaN stays visible; regions without observations |
| Interpolation gaps | `tests/unit/test_interpolation_gaps.py`, `tests/component/test_timeseries_calendar.py` | F-003 semantics (#103): total gap size, forward-only fill |
| Climatology boundaries | `tests/unit/test_climatology_anomalies.py`, `tests/component/test_timeseries_climatology.py` | window statistics attached outside the window |
| Anomaly calculation | `tests/unit/test_climatology_anomalies.py`, `tests/component/test_timeseries_anomalies.py` | value minus climatological mean |
| Absolute versus relative coverage | `tests/unit/test_region_metrics.py`, `tests/component/test_region_analyzer.py` | hand calculations; ice threshold >= 150 inclusive |

## 6.3 Data Regression Cases

| Case | Protecting tests | Notes |
| ---- | ---------------- | ----- |
| Duplicate `(date, region)` records | `tests/unit/test_results_merge.py`, `tests/component/test_results_manager.py`, `tests/integration/test_spatial_processing_chain.py` | keep-last deduplication (F-001) |
| Accidental loss of historical results | `tests/integration/test_update_pipeline.py`, `tests/e2e/test_incremental_update.py` | history rows byte-identical across the update |
| Incorrect latest-date detection | `tests/component/test_results_manager.py`, `tests/integration/test_update_pipeline.py` | latest.json reflects the newest processed date |
| Malformed output files | not yet automated | validated in the QA step of the v0.2 readiness review; the empty-derived-product edge is covered by F-031 and the E2E tests |
| Inconsistent derived datasets | `tests/e2e/test_complete_workflow.py`, `tests/e2e/test_incremental_update.py` | derived CSVs consistent with the persisted results; plot stage operable on fresh datasets (F-031) |

## 6.4 Pipeline Regression Cases

| Case | Protecting tests | Notes |
| ---- | ---------------- | ----- |
| Incorrect stage ordering | `tests/integration/test_update_pipeline.py`, `tests/e2e/test_incremental_update.py` | recorded stage order sync -> process -> plots -> build -> cleanup |
| Skipped processing stages | `tests/integration/test_update_pipeline.py`, `tests/integration/test_update_no_new_data.py` | no-new-downloads and no-new-results early exits (#31) |
| Incorrect cleanup | `tests/integration/test_update_pipeline.py`, `tests/integration/test_update_no_new_data.py` | cleanup tied to downloads; `--keep-data` honored |
| Incorrect build paths | `tests/integration/test_build_pages.py` | build root, `build/output/` deployment path (F-020, F-021) |
| Missing website resources | `tests/integration/test_build_pages.py`, `tests/e2e/test_complete_workflow.py` | fail-fast on missing `output/`; built site contains the analysis products |
| Unintended modification of persistent scientific data | `tests/integration/test_spatial_processing_chain.py`, `tests/integration/test_update_no_new_data.py`, `tests/e2e/test_complete_workflow.py` | production directory snapshots before/after |

## Gap Closure (issue #41)

* The interpolation-gap edges (F-003/F-030) are now pinned at
  the unit level (`tests/unit/test_interpolation_gaps.py`).
* The fresh-dataset crash of the plot stage is fixed and
  pinned by both E2E tests (F-031).
* The malformed-output validation remains a manual QA step
  of the v0.2 readiness review (no automated schema
  validation yet); automating it is a v0.3 backlog candidate.

## Maintenance

When a new finding is registered in `tests/Findings.md`, add
its protecting test to the matching table above in the same
issue. When a regression case gains its first automated test,
replace the "not yet automated" note.