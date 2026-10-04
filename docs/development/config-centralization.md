# Configuration Centralization Inventory (issue #85)

## Scope and method

Issue #85 centralizes every project path in
`src/config/paths.py` and every project-wide domain constant in
`src/config/settings.py`. Module-specific constants stay near
their use as named constants with a short rationale. This
document is the complete inventory: resolved findings and the
justified exceptions that remain.

Method: source review of every module in `src/` for path
construction (`PROJECT_ROOT`, `Path(...)`, `os.path`, string
fragments) and numeric literals, cross-checked against the
coverage report of the #40 run.

## Paths - resolved findings

| Module | Finding | Resolution |
| --- | --- | --- |
| `config/logging_config.py` | log file name built from `LOG_DIR` | `LOG_FILE` in `paths.py`, re-exported as `DEFAULT_LOG_FILE` |
| `data_download/downloader.py` | `DEFAULT_GEOTIFF_DIR` built locally; identical second construction in `delete_local_data` | `DEFAULT_GEOTIFF_DIR = GEOTIFF_DIR`; the `delete_local_data` join stays call-time from `DATA_DIR` (test seam, F-010) |
| `data_download/download_data.py` | no local path construction | unchanged |
| `analysis/process_data.py` | glob pattern `"*concentration*.tif"` inline | built from `settings.DEFAULT_PRODUCT` |
| `analysis/reference_builder.py` | `REFERENCE_TIF`, `FILTER_DIR`, `REFERENCE_SUMMARY`, regions.json and ocean.shp built from `PROJECT_ROOT` | `REFERENCE_TIF`, `REFERENCE_FILTERS_DIR`, `REFERENCE_SUMMARY_JSON`, `REGIONS_FILE`, `OCEAN_SHAPEFILE` in `paths.py` (aliases kept) |
| `analysis/region_analyzer.py` | `REFERENCE_JSON` and `FILTER_DIR` duplicated the reference-builder paths | same central constants (aliases kept) |
| `analysis/results_manager.py` | `DEFAULT_RESULTS` and `DEFAULT_LATEST` built from `PROJECT_ROOT` | `ICE_COVERAGE_SUMMARY_CSV` and `LATEST_JSON` (aliases kept) |
| `analysis/timeseries_analyzer.py` | four output CSVs built from `PROJECT_ROOT` | four central CSV constants (aliases kept) |
| `update/build_pages.py` | `BUILD_DIR / "output"` inline | unchanged: the call-time join stays as the test redirect seam (F-018 pattern) |
| `update/update_pipeline.py` | no local path construction | unchanged |
| `src/main.py` | no local path construction | unchanged |
| `visualization/geotiff_plot.py` | overview PNG, regions.json and geotiff fallback dir built locally | `GEOTIFF_OVERVIEW_PLOT` (alias `DEFAULT_OUTPUT_PLOT_PATH` for `generate_plots.py`); regions.json and the fallback dir stay call-time joins from `PROJECT_ROOT`/`DATA_DIR` (test seams, F-018) |
| `visualization/timeseries_plot.py` | input CSVs and plots dir built locally | central CSV constants (aliases kept); `OUTPUT_DIR` kept as module-level alias of `PLOTS_DIR`, still joined with `/ "timeseries"` at construction time (test seam) |

## Constants - resolved findings

| Value | Meaning | Locations | Resolution |
| --- | --- | --- | --- |
| 1000 | concentration scale (tenths of a percent) | `reference_builder`, `region_analyzer`, `geotiff_plot` | `settings.CONCENTRATION_SCALE` |
| 2550 | NSIDC missing-pixel fill value | `reference_builder`, `region_analyzer` | `settings.MISSING_PIXEL_VALUE` |
| 150 | 15 percent ice threshold (tenths) | `region_analyzer` | `settings.ICE_CONCENTRATION_THRESHOLD_TENTHS` |
| 625.0 | 25 km grid pixel area (km2) | `reference_builder`, `region_analyzer` | `settings.PIXEL_AREA_KM2` |
| "concentration" | default NSIDC product | `downloader`, `download_data`, `process_data` | `settings.DEFAULT_PRODUCT` |
| 3411 | NSIDC polar stereographic CRS | `reference_builder`, `geotiff_plot` | `settings.DATA_CRS` / `settings.DATA_EPSG` |
| "EPSG:4326" | WGS 84 | `reference_builder` | `settings.WGS84_CRS` |
| 6933 | equal-area CRS for area computation | `reference_builder` | `settings.AREA_EPSG` |
| 1981 / 2010 | WMO climate normal | `timeseries_analyzer`, `timeseries_plot` | `settings.CLIMATOLOGY_START_YEAR` / `CLIMATOLOGY_END_YEAR` |
| 10.0 / 50.0 / 90.0 | event threshold levels | `timeseries_analyzer` (default), `timeseries_plot` (style keys) | `settings.EVENT_THRESHOLDS_PERCENT`; plot keys mirror it |
| (260.0, 300.0, 50.0, 75.0) | Hudson Bay bounds | `geotiff_plot`, `generate_plots` | `settings.HUDSON_BAY_BOUNDS` (alias `DEFAULT_REGION_BOUNDS`) |
| 300 | figure save dpi | `geotiff_plot`, `timeseries_plot` | `settings.FIGURE_SAVE_DPI` |

## Module-specific constants (named near use)

| Module | Constant | Value | Rationale |
| --- | --- | --- | --- |
| `downloader.py` | `HTTP_TIMEOUT_SECONDS` | 30 | HTTP transport tuning, single module |
| `downloader.py` | `DOWNLOAD_CHUNK_BYTES` | 8192 | download streaming chunk size |
| `downloader.py` | `DEFAULT_NSIDC_GEOTIFF_URL` | NSIDC endpoint | data source URL, single consumer pair |
| `timeseries_analyzer.py` | `INTERPOLATION_LIMIT_DAYS` | 14 | max interpolated calendar gap |
| `timeseries_analyzer.py` | `DEFAULT_MOVING_AVERAGE_WINDOW` | 3 | moving-average half-width (days) |
| `timeseries_analyzer.py` | `DEFAULT_PERSISTENCE_DAYS` | 7 | event persistence (days) |
| `timeseries_analyzer.py` | `BREAKUP_WINDOW_START/END`, `FREEZEUP_WINDOW_START/END` | (3,16)/(9,15), (9,16)/(3,15) | event window calendar boundaries |
| `geotiff_plot.py` | `PROJECTION_SEMIMAJOR_AXIS_M` etc. | 6378273, 6356889.449, 90, -80, 70 | NSIDC projection parameters |
| `timeseries_plot.py` | `DAY_OF_YEAR_AXIS_YEAR` | 2000 | placeholder year for day-of-year axes |
| `timeseries_plot.py` | `SECONDS_PER_DAY` | 86400.0 | duration unit conversion |

## Justified exceptions (documented, unchanged)

* Call-time path joins that tests redirect via namespace
  replacement (F-010/F-018 seams): `downloader.DATA_DIR` in
  `delete_local_data`, `geotiff_plot.PROJECT_ROOT` and
  `geotiff_plot.DATA_DIR` in `find_concentration_geotiff` and
  `load_regions`, `build_pages.BUILD_DIR` in `main`, and
  `timeseries_plot.OUTPUT_DIR` in the plotter constructor. The
  source of every name is still `paths.py`; the joins read the
  module-level names at call time so the tests can isolate
  them.
* Plot styling values in `geotiff_plot.py` and
  `timeseries_plot.py` (figure sizes, margins, fontsizes, gray
  tones, zorders, alphas, grid widths, rcParams, graticule
  lists): mostly already named attributes or rcParams keys; the
  remaining inline literals are only meaningful in situ.
* Calendar facts (365/366, month 1/day 1, month 12/day 31) in
  completeness checks and polar plotting: self-explanatory in
  context.
* Axis ranges (`set_ylim(0, 365)`, `set_ylim(-100, 100)`): plot
  presentation, evident from context.
* Percent factors (100, 100.0) in coverage computations and
  logger format strings (`%6.1f`, `%8.0f`): presentation, not
  configuration.
* Unit conversion `1e6` (m2 to km2) in `reference_builder.py`:
  inline with explanatory context.
* `PROJ_LIB`/`GDAL_DATA` environment defaults in
  `geotiff_plot.py`: library data-dir bootstrap, not a project
  path.
* `threshold_style` keys 10.0/50.0/90.0 in `timeseries_plot.py`
  mirror `settings.EVENT_THRESHOLDS_PERCENT`; kept literal to
  stay table-driven (comment at the definition).
* Display strings containing the climate normal
  ("1981-2010 climatology" legend labels): presentation text.

## Verification

* `grep -rn 'PROJECT_ROOT / ' src/` - `src/config/paths.py`
  (by design) plus the documented call-time seams in
  `geotiff_plot.py`, `downloader.py` and `build_pages.py`
  (see justified exceptions).
* `grep -rn '"geotiff"' src/` - `src/config/paths.py` plus the
  `delete_local_data` seam in `downloader.py`.
* `grep -rn 'EPSG:' src/` - only `src/config/settings.py`.
* `grep -rnE '== 2550|<= 1000|>= 150|625\.0|1981|2010' src/` -
  no code hits; remaining hits are comments and display labels.
* All gates green; 148 tests unchanged; pipeline behavior
  byte-identical.
