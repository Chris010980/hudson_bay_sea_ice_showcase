# Architecture Overview

## Purpose

This document describes the current architecture of the `hudson_bay_sea_ice` project.

The project is a pipeline-oriented scientific data processing application for the automated analysis and visualization of daily sea-ice concentration data for the Hudson Bay region.

The system combines:

* automated acquisition of NSIDC sea-ice data,
* spatial analysis of daily GeoTIFF observations,
* persistent storage of regional analysis results,
* temporal and climatological analysis,
* scientific visualization,
* and generation of a self-contained GitHub Pages deployment.

This document describes the **current implementation (as-is architecture)**. Target architecture and planned refactoring are intentionally not covered here.

## System Overview

The current processing flow is:

```text
NSIDC data
    │
    ▼
Data acquisition
    │
    ▼
Temporary GeoTIFF files
    │
    ▼
Spatial analysis
    │
    ▼
Persistent daily results
    │
    ▼
Temporal analysis
    │
    ▼
Derived analysis results
    │
    ▼
Scientific visualizations
    │
    ▼
GitHub Pages build
```

The application is controlled through a command-line pipeline dispatcher.

```text
src/main.py
    │
    ├── download
    ├── process
    ├── plots
    ├── build
    ├── update
    └── all
```

## Main Architectural Areas

### Data Acquisition

`src/data_download/` is responsible for retrieving sea-ice data from the NSIDC archive.

The `NSIDCDownloader` determines which observations are missing locally and downloads them into the temporary `data/geotiff/` working directory.

### Spatial Analysis

`src/analysis/` contains the analysis components.

`ReferenceBuilder` prepares the static spatial reference data and region masks.

`RegionAnalyzer` processes individual GeoTIFF observations and calculates regional sea-ice statistics.

### Result Management

`ResultsManager` provides persistence for the daily analysis results.

The primary persistent dataset is:

```text
output/analysis/ice_coverage_summary.csv
```

Additional metadata is stored in `latest.json`.

### Temporal Analysis

`TimeSeriesAnalyzer` derives temporal information from the persistent daily results.

Current analyses include:

* daily calendar-based time series,
* moving averages,
* 1981–2010 climatology,
* climatological standard deviations,
* anomalies,
* annual means,
* break-up events,
* freeze-up events,
* threshold durations.

### Visualization

The visualization layer consists of two main components.

`SeaIcePlotter` creates spatial maps from GeoTIFF observations.

`TimeSeriesPlotter` creates temporal, climatological and event-based plots from the derived analysis datasets.

### Website Build

The static website source is located in `docs/`.

`build_pages.py` combines the website source with the generated `output/` directory and creates the self-contained `build/` directory used for GitHub Pages deployment.

## Data Persistence

The project distinguishes between temporary input data and persistent analysis products.

### Temporary

```text
data/
└── geotiff/
```

Downloaded GeoTIFF files are used as processing input and can be removed after successful processing.

### Persistent

```text
output/
├── analysis/
├── reference/
└── plots/
```

The `output/` directory contains the persistent results required by subsequent analysis and visualization steps.

## Current Architectural Characteristics

The current implementation is characterized by:

* pipeline-oriented processing,
* explicit stage-based CLI control,
* file-based data exchange between processing stages,
* separation of data acquisition, analysis, visualization and website generation,
* incremental processing based on the latest processed observation date,
* temporary storage of raw downloaded observations,
* persistent storage of derived analysis results.

## Architecture Status

This document describes the current state of the implementation.

The following aspects are intentionally not defined here yet:

* target architecture,
* module restructuring,
* dependency inversion,
* final interface design,
* branching strategy,
* test architecture,
* future analysis extensions.

These will be defined after the current system requirements and project scope have been established.
