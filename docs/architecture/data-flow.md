# Data Flow

## Overview

The project processes daily sea-ice concentration observations through several stages.

The main scientific data flow is:

```text
NSIDC
  │
  ▼
NSIDCDownloader
  │
  ▼
data/geotiff/
  │
  ▼
RegionAnalyzer
  │
  ▼
ice_coverage_summary.csv
  │
  ▼
TimeSeriesAnalyzer
  │
  ├── ice_coverage_timeseries.csv
  ├── ice_coverage_yearly.csv
  └── ice_coverage_events.csv
  │
  ▼
TimeSeriesPlotter
  │
  ▼
output/plots/
```

Spatial reference preparation is a parallel prerequisite:

```text
src/config/reference.tif
       │
       ▼
ReferenceBuilder
       │
       ├── reference_summary.json
       └── filters/*.npy
                    │
                    ▼
              RegionAnalyzer
```

The static website is generated separately from the scientific processing flow:

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
                │
                ▼
          GitHub Pages
```

---

## 1. Data Acquisition

`NSIDCDownloader` accesses the configured NSIDC archive and compares available observations with locally available files.

Missing observations are downloaded to:

```text
data/geotiff/<year>/<month>/
```

The downloaded GeoTIFF files are temporary processing inputs.

The acquisition stage supports incremental synchronization by starting from the latest processed observation where applicable.

---

## 2. Spatial Reference Preparation

Before daily spatial processing, `ReferenceBuilder.ensure_reference()` ensures that the required reference products exist.

The fixed reference dataset is:

```text
src/config/reference.tif
```

Generated reference products include:

```text
output/reference/
├── reference_summary.json
└── filters/
    └── *.npy
```

These products contain the spatial information required by `RegionAnalyzer`.

The reference is independent of the normal incremental processing interval.

---

## 3. Daily Spatial Analysis

Each selected GeoTIFF observation is processed by `RegionAnalyzer`.

The analyzer:

1. extracts the observation date,
2. loads the raster data,
3. applies the reference masks,
4. checks the relevant spatial data,
5. identifies sea-ice pixels,
6. calculates regional absolute sea-ice coverage,
7. calculates regional relative sea-ice coverage,
8. creates regional result records.

The resulting records are passed to `ResultsManager`.

---

## 4. Persistent Daily Results

`ResultsManager` stores the regional daily observations in:

```text
output/analysis/ice_coverage_summary.csv
```

The dataset is:

* associated with observation dates and regions,
* deduplicated by date and region,
* sorted chronologically.

Additional metadata is maintained in:

```text
output/analysis/latest.json
```

The persistent daily result dataset forms the input to the temporal analysis.

---

## 5. Temporal Analysis

`TimeSeriesAnalyzer` reads the persistent daily result dataset and generates derived temporal products.

The current analysis sequence is:

```text
Daily results
     │
     ▼
Calendar interpolation
     │
     ▼
Moving average
     │
     ▼
1981–2010 climatology
     │
     ├── mean
     ├── standard deviation
     ├── minimum
     └── maximum
     │
     ▼
Anomalies
     │
     ▼
Yearly means
     │
     ▼
Threshold events
```

Threshold event analysis uses:

```text
10 %
50 %
90 %
```

and determines break-up and freeze-up events according to the defined seasonal and persistence rules.

---

## 6. Derived Analysis Products

The temporal analysis produces:

```text
output/analysis/
├── ice_coverage_timeseries.csv
├── ice_coverage_yearly.csv
└── ice_coverage_events.csv
```

These datasets are the inputs for the temporal visualization layer.

They also form part of the persistent scientific output of the project.

---

## 7. Spatial Visualization

Spatial visualization uses a GeoTIFF observation as input.

`SeaIcePlotter` creates:

* overview maps,
* maps with analysis-region overlays,
* individual regional maps.

The resulting figures are stored under:

```text
output/plots/
```

This visualization path is separate from the temporal analysis data flow.

---

## 8. Temporal Visualization

`TimeSeriesPlotter` reads the derived temporal datasets and creates:

* time-series plots,
* anomaly plots,
* threshold-duration plots,
* polar seasonal plots,
* yearly mean plots.

The generated figures are stored under:

```text
output/plots/timeseries/
```

Visualization products are regenerable outputs and are not inputs to subsequent scientific analysis stages.

---

## 9. Website Build

The website source is maintained under:

```text
docs/
```

Generated scientific products are maintained under:

```text
output/
```

`build_pages.py` combines these sources into:

```text
build/
```

The build directory is therefore a deployment artifact rather than a scientific processing stage.

The resulting artifact is used for GitHub Pages deployment.

---

## 10. Incremental Update Flow

The automated update workflow uses the latest processed observation to determine the beginning of the next processing interval.

The intended incremental flow is:

```text
latest processed date
        │
        ▼
latest + 1 day
        │
        ▼
NSIDCDownloader.sync()
        │
        ▼
new observations
        │
        ▼
process_data()
        │
        ▼
generate_plots()
        │
        ▼
build_pages()
        │
        ▼
temporary GeoTIFF cleanup
```

If no new observations are available, the current update implementation terminates without regenerating downstream products.

---

## 11. Command-Line Flow

The external CLI exposes the following stages:

```text
src/main.py
    │
    ├── download
    │
    ├── process
    │
    ├── plots
    │
    ├── build
    │
    ├── update
    │
    └── all
```

The individual stages can therefore be executed independently where supported by their interfaces.

The `update` stage is the end-to-end incremental workflow, while `all` provides sequential execution of the individual processing stages.

---

## 12. Operational and Verification Flow

In addition to the scientific data flow, the project contains supporting quality and operational processes.

```text
Source Code
    │
    ├──────────────► Automated Tests
    │
    ├──────────────► CI Execution
    │
    └──────────────► Pipeline Execution
                            │
                            ▼
                    Scientific Outputs
                            │
                            ▼
                    Website Deployment
```

The current automated test suite verifies selected functionality.

Systematic output validation and comprehensive CI quality gates are requirements for the evolving quality strategy but are not yet fully implemented.

---

## 13. Data Lifecycle

The main data lifecycle is:

```text
Remote observation
       │
       ▼
Temporary local GeoTIFF
       │
       ▼
Spatial processing
       │
       ▼
Persistent daily result
       │
       ▼
Derived temporal datasets
       │
       ├──────────────► Scientific plots
       │
       └──────────────► Website build
```

Temporary GeoTIFF files may be removed after successful processing.

Persistent scientific results remain available for subsequent incremental processing and temporal analysis.

Plots and website files are regenerated products.

---

## 14. Architectural Data Boundaries

The current architecture distinguishes the following data boundaries:

### External Data

```text
NSIDC archive
```

### Temporary Processing Data

```text
data/geotiff/
```

### Static Reference Data

```text
src/config/reference.tif
```

### Persistent Scientific Data

```text
output/analysis/
output/reference/
```

### Generated Visualization Data

```text
output/plots/
```

### Website Source

```text
docs/
```

### Deployment Artifact

```text
build/
```

These boundaries are relevant to data integrity, reproducibility, operational safety and deployment.

---

## 15. Current Data-Flow Characteristics

The current implementation is characterized by:

* file-based exchange between major processing stages,
* persistent storage of derived scientific results,
* temporary storage of raw observations,
* reusable spatial reference products,
* regeneration of temporal analysis products from persistent daily results,
* regeneration of plots from analysis products,
* independent generation of the website deployment artifact.

The architecture therefore separates scientific source data, persistent analysis state, generated visualization products and deployment artifacts.
