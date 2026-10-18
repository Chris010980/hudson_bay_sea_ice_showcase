# Hard-Wiring Inventory (issue #73)

Date: 2026-10-04

Scope: the CLI-heavy modules without meaningful test coverage
(`src/main.py` 0 %, `src/data_download/download_data.py` 0 %,
`src/analysis/process_data.py` 48 % before #73), extended to
the update stage and the build stage per the #73 scope note.
This inventory is the basis for the CLI tests; the CLI
restructure (#74) and the CLI argument-parity issue build on
these seams.

## Resolved in #73

| Module | Hard wiring | Seam introduced |
| --- | --- | --- |
| `src/main.py` | stage dispatch through the module-level `STAGES` map and direct function calls in the "all" branch | injectable `stages` mapping parameter on `main()`; `STAGES` stays as the production default |
| `src/main.py` | stage argv construction inline in `main()` | extracted pure helper `build_stage_args(args)` |
| `src/data_download/download_data.py` | `NSIDCDownloader` constructed inline | injectable `downloader_factory` parameter |
| `src/analysis/process_data.py` | `DATA_DIR.rglob(f"*{DEFAULT_PRODUCT}*.tif")` inline | injectable `data_dir` and `product` parameters |
| `src/analysis/process_data.py` | `ReferenceBuilder()`, `ResultsManager()`, `TimeSeriesAnalyzer()` with hard-wired production defaults | injectable keyword arguments with the previous defaults |
| `src/analysis/process_data.py` | processing loop inline in `main()` | extracted `process_geotiffs()` with injectable `analyzer_factory` |
| `src/analysis/process_data.py` | call of the private `RegionAnalyzer._extract_date()` (audit remark from #75) | public `RegionAnalyzer.extract_date()` wrapper |

## Resolved in #106

| Module | Hard wiring | Seam introduced |
| --- | --- | --- |
| `src/update/update_pipeline.py` | stage functions and collaborators bound as module-level names | injectable keyword arguments `results_factory`, `downloader_factory`, `process_stage`, `plots_stage`, `build_stage` with the production defaults (F-015 resolved) |
| `src/update/build_pages.py` | `HTML_DIR`/`OUTPUT_DIR`/`BUILD_DIR` read from module constants in `main()` | injectable keyword arguments `html_dir`, `output_dir`, `build_dir` with the module constants as defaults (F-018 resolved) |
| `src/visualization/timeseries_plot.py` | `TimeSeriesPlotter` reads the module alias `OUTPUT_DIR` at construction time | injectable `output_dir` constructor parameter (default `OUTPUT_DIR`) (F-018 resolved) |
| `src/visualization/geotiff_plot.py` | `SeaIcePlotter` regions.json default, GeoTIFF fallback directory and default output path read from module constants | injectable `region_file`, `data_dir`, `default_output_path` constructor parameters; the fallback defaults remain call-time module reads (F-018 resolved) |

## Remaining, justified

| Item | Justification |
| --- | --- |
| `sys.path` bootstrap at import time in `main.py`, `download_data.py`, `process_data.py` | required for direct script execution (`python src/main.py`); imports as a package bypass it, so tests are unaffected |
| stage imports at module level in `main.py` (the `STAGES` defaults) | required for direct dispatch; importing the dispatcher loads all stage modules; no side effects beyond module initialization (the matplotlib "Agg" backend selection in `geotiff_plot.py` is documented with #40) |
| `download_data.py`: `sync()` receives `years`/`months` kwargs the downloader API does not accept | functional defect F-009 (every CLI download run fails with a TypeError); the fix needs a design decision (map `--year`/`--month` to a date range, or extend `sync()`) and a separate functional-correction issue; #73 does not change behavior |
| `logging_config.configure_logging` mutates global logging state | CLI bootstrap by design; tests pass an explicit `--log-file` below their temporary directory |

## Seam documentation for CLI tests

* `main.main(argv, stages=...)` — dispatch with injected stage
  entry points; `build_stage_args(args)` builds the forwarded
  argv list; `main.parse_args(argv)` parses the dispatcher CLI.
* `download_data.main(argv, downloader_factory=...)` — the
  factory is called with `base_url`, `local_base`, `product`.
* `process_data.main(argv, data_dir=..., product=...,
  reference_builder=..., results=..., analyzer_factory=...,
  timeseries=...)` — full collaborator injection; the loop is
  also directly testable via `process_data.process_geotiffs()`.
* `RegionAnalyzer.extract_date()` — public date extraction.
* `update_pipeline.main(argv, results_factory=...,
  downloader_factory=..., process_stage=..., plots_stage=...,
  build_stage=...)` — full collaborator injection (issue
  #106, F-015 resolved).
* `build_pages.main(argv, html_dir=..., output_dir=...,
  build_dir=...)` — directory injection (issue #106, F-018
  resolved).
* Since issue #106 every stage module exposes its
  stage-specific options through `add_arguments(parser)` and
  the shared logging options through
  `src.config.logging_config.add_log_arguments(parser)`; the
  dispatcher sub-parsers are built from the same functions,
  so dispatcher and direct invocations expose the identical
  option set (CLI parity).

The component smoke tests live in `tests/component/`:
`test_main.py` (dispatcher), `test_download_data.py`
(download stage), `test_process_data.py` (process stage).

## Verification

* All quality gates green; 166 tests (148 + 18 new); pipeline
  behavior unchanged — production call paths receive identical
  arguments (the dispatcher forwards identical argv lists; the
  "all" sequence runs download, process, plots, build in the
  same order).
* Coverage: `src/main.py`, `src/data_download/download_data.py`
  and `src/analysis/process_data.py` move from 0 %/0 %/48 % to
  near-full coverage, clearly above the #74 targets
  (main.py >= 70 %, download_data.py >= 80 %).
* `grep -rn "noqa" src/` shows no exceptions since #74
  removed the last directive (`generate_plots.main` C901).
