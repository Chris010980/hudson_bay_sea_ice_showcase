# Components

## Overview

The current implementation consists of components with distinct technical responsibilities.

| Component             | Location                               | Responsibility                                            |
| --------------------- | -------------------------------------- | --------------------------------------------------------- |
| Pipeline Dispatcher   | `src/main.py`                          | CLI dispatch and stage selection                          |
| NSIDC Downloader      | `src/data_download/downloader.py`      | Remote data acquisition and temporary data management     |
| Download CLI          | `src/data_download/download_data.py`   | CLI entry point for data acquisition                      |
| Reference Builder     | `src/analysis/reference_builder.py`    | Static spatial reference and regional mask preparation    |
| Region Analyzer       | `src/analysis/region_analyzer.py`      | Daily regional sea-ice analysis                           |
| Results Manager       | `src/analysis/results_manager.py`      | Persistent daily result management                        |
| Processing Stage      | `src/analysis/process_data.py`         | Spatial processing and temporal-analysis orchestration    |
| Time Series Analyzer  | `src/analysis/timeseries_analyzer.py`  | Temporal, climatological and event analysis               |
| GeoTIFF Plotter       | `src/visualization/geotiff_plot.py`    | Spatial visualization                                     |
| Time Series Plotter   | `src/visualization/timeseries_plot.py` | Temporal and derived visualization                        |
| Plot Generator        | `src/visualization/generate_plots.py`  | Visualization-stage orchestration                         |
| Update Pipeline       | `src/update/update_pipeline.py`        | Incremental end-to-end orchestration                      |
| Pages Builder         | `src/update/build_pages.py`            | GitHub Pages deployment artifact generation               |
| Logging Configuration | `src/config/logging_config.py`         | Central logging configuration                             |
| Project Paths         | `src/config/paths.py`                  | Central project path definitions                          |
| Region Configuration  | `src/config/regions.json`              | Spatial region definitions                                |
| Test Infrastructure   | `tests/`                               | Location for automated verification of the implementation |

---

## Pipeline Dispatcher

### `src/main.py`

The pipeline dispatcher provides the main command-line interface.

Available stages are:

```text
download
process
plots
build
update
all
```

It:

* parses the selected stage,
* configures logging,
* forwards stage-specific arguments,
* invokes the corresponding stage.

The dispatcher does not contain the scientific calculations themselves.

---

## Data Acquisition

### `NSIDCDownloader`

Location:

```text
src/data_download/downloader.py
```

Responsibilities:

* inspect the remote NSIDC archive,
* inspect locally available observations,
* identify missing observations,
* identify equivalent product files,
* download missing files,
* manage temporary downloaded data,
* remove temporary GeoTIFF files when requested.

Temporary data are stored under:

```text
data/geotiff/
```

### `download_data.py`

Location:

```text
src/data_download/download_data.py
```

Provides the command-line entry point for the acquisition stage.

---

## Spatial Reference Preparation

### `ReferenceBuilder`

Location:

```text
src/analysis/reference_builder.py
```

Responsibilities:

* use the fixed reference GeoTIFF,
* prepare reference spatial information,
* create regional masks,
* determine reference pixel information,
* write reusable reference products.

Reference products are stored under:

```text
output/reference/
```

The reference GeoTIFF itself is maintained at:

```text
src/config/reference.tif
```

The reference is intentionally separate from the normal incremental acquisition interval.

---

## Daily Spatial Analysis

### `RegionAnalyzer`

Location:

```text
src/analysis/region_analyzer.py
```

Processes one daily GeoTIFF observation.

It:

* determines the observation date,
* loads the raster,
* applies the predefined regional masks,
* checks the relevant spatial data,
* determines sea-ice pixels using the current sea-ice detection threshold,
* calculates absolute sea-ice coverage,
* calculates relative sea-ice coverage,
* produces regional analysis records.

The current detection threshold is defined by the implementation rather than being fully configurable.

The results are passed to `ResultsManager`.

---

## Result Management

### `ResultsManager`

Location:

```text
src/analysis/results_manager.py
```

Responsibilities:

* load existing daily results,
* determine whether a date has already been processed,
* add new regional results,
* remove duplicate date/region records,
* sort the dataset,
* save the persistent dataset,
* maintain `latest.json`.

Primary output:

```text
output/analysis/ice_coverage_summary.csv
```

---

## Processing Orchestration

### `process_data.py`

Location:

```text
src/analysis/process_data.py
```

Coordinates the daily processing stage.

The current sequence is:

```text
ReferenceBuilder
      ↓
GeoTIFF discovery
      ↓
RegionAnalyzer
      ↓
ResultsManager
      ↓
TimeSeriesAnalyzer
```

It also provides a `ProcessSummary` containing counts for:

* processed files,
* skipped files,
* failed files,
* newly added results.

---

## Temporal Analysis

### `TimeSeriesAnalyzer`

Location:

```text
src/analysis/timeseries_analyzer.py
```

Transforms the persistent daily regional result dataset into derived temporal datasets.

Current processing includes:

* calendar interpolation,
* moving averages,
* climatology,
* climatological standard deviation,
* climatological minimum and maximum,
* anomalies,
* annual means,
* seasonal threshold-event detection.

The threshold analysis uses:

```text
10 %
50 %
90 %
```

Generated datasets include:

```text
output/analysis/
├── ice_coverage_timeseries.csv
├── ice_coverage_yearly.csv
└── ice_coverage_events.csv
```

---

## Visualization

### `SeaIcePlotter`

Location:

```text
src/visualization/geotiff_plot.py
```

Provides spatial visualization of GeoTIFF observations.

Current plot types include:

* overview maps,
* region overlays,
* individual regional maps.

The current implementation uses the configured NSIDC polar stereographic CRS, EPSG:3411.

### `TimeSeriesPlotter`

Location:

```text
src/visualization/timeseries_plot.py
```

Creates plots from the derived analysis datasets.

Current plot families include:

* time series,
* anomaly plots,
* threshold-duration plots,
* polar seasonal plots,
* yearly mean plots.

### `generate_plots.py`

Location:

```text
src/visualization/generate_plots.py
```

Provides the visualization CLI stage and coordinates the visualization components.

Generated figures are stored under:

```text
output/plots/
```

---

## Incremental Update Orchestration

### `update_pipeline.py`

Location:

```text
src/update/update_pipeline.py
```

Coordinates the incremental update workflow.

The intended sequence is:

```text
Determine latest processed observation
              ↓
NSIDCDownloader.sync()
              ↓
process_data
              ↓
generate_plots
              ↓
build_pages
              ↓
temporary GeoTIFF cleanup
```

The processing start date is derived from the latest processed observation.

The update pipeline is the primary orchestration component for scheduled incremental execution.

---

## Website Build

### `build_pages.py`

Location:

```text
src/update/build_pages.py
```

Creates the static deployment artifact by combining:

```text
docs/
output/
```

into:

```text
build/
```

The resulting directory contains the website source together with the generated analysis products required by the static site.

`build/` is a generated artifact and is not a source directory.

---

## Configuration Components

### `paths.py`

Location:

```text
src/config/paths.py
```

Provides central project path definitions used by the processing components.

### `logging_config.py`

Location:

```text
src/config/logging_config.py
```

Provides centralized logging configuration.

### `regions.json`

Location:

```text
src/config/regions.json
```

Contains the configured spatial analysis regions used by the reference preparation and spatial analysis components.

### `reference.tif`

Location:

```text
src/config/reference.tif
```

Provides the fixed spatial reference dataset used to establish the analysis grid and regional masks.

---

## Quality Assurance Components

### Test Infrastructure

Location:

```text
tests/
```

The project contains pytest-based test infrastructure.

The existing test files originate from an earlier implementation phase and no longer correspond to the current component interfaces. They are therefore not considered a valid automated test suite for the current implementation.

The `tests/` directory remains the designated location for automated verification.

Future test coverage is intended to include:

* scientific calculation tests,
* component tests,
* integration tests,
* end-to-end tests,
* regression tests,
* invalid-input and edge-case tests,
* and output-validation tests.

The corresponding testing strategy is documented separately under:

```text
docs/testing/
```

---

## Component Relationships

The principal relationships are:

```text
NSIDCDownloader
       │
       ▼
  GeoTIFF data
       │
       ▼
RegionAnalyzer ◄──── ReferenceBuilder
       │
       ▼
ResultsManager
       │
       ▼
TimeSeriesAnalyzer
       │
       ▼
TimeSeriesPlotter
```

Spatial visualization follows a separate path:

```text
GeoTIFF
   │
   ▼
SeaIcePlotter
   │
   ▼
spatial plots
```

Website generation consumes the static website source and generated project output:

```text
docs/ ──────────┐
                ▼
             build_pages
                ▲
                │
output/ ────────┘
                │
                ▼
              build/
```

The update pipeline coordinates these components:

```text
UpdatePipeline
      │
      ├── NSIDCDownloader
      │
      ├── process_data
      │      ├── ReferenceBuilder
      │      ├── RegionAnalyzer
      │      ├── ResultsManager
      │      └── TimeSeriesAnalyzer
      │
      ├── generate_plots
      │      ├── SeaIcePlotter
      │      └── TimeSeriesPlotter
      │
      └── build_pages
```

---

## Architectural Observation

The current components are separated broadly according to their technical responsibilities.

However, several components also contain orchestration logic and communicate through direct function calls and filesystem-based artifacts.

The current architecture therefore represents a pragmatic pipeline implementation rather than a fully decoupled component architecture.

This is an architectural characteristic of the current implementation and is not itself treated as a defect.

Potential restructuring, dependency inversion and interface refinement belong to the target-architecture discussion and are not defined by this document.
