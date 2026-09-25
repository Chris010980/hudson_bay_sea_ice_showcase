# Architecture Overview

## Purpose

This document describes the current architecture of the `hudson_bay_sea_ice` project.

The project is a pipeline-oriented scientific data processing application for the automated analysis and visualization of daily sea-ice concentration data for the Hudson Bay region.

The system combines:

* automated acquisition of NSIDC sea-ice data,
* spatial reference preparation,
* spatial analysis of daily GeoTIFF observations,
* persistent storage of regional analysis results,
* temporal and climatological analysis,
* seasonal event detection,
* scientific visualization,
* incremental update orchestration,
* and generation of a self-contained GitHub Pages deployment.

This document describes the **current implementation (as-is architecture)**. Target architecture and planned refactoring are intentionally not covered here.

---

## System Overview

The current system consists of several processing and supporting areas:

```text
                         ┌──────────────────────┐
                         │      NSIDC archive   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Data Acquisition    │
                         │  NSIDCDownloader     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Temporary GeoTIFFs   │
                         │ data/geotiff/        │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴───────────┐
                         │                      │
                         ▼                      ▼
                ┌─────────────────┐    ┌─────────────────┐
                │ Reference       │    │ Spatial         │
                │ Preparation     │───►│ Analysis        │
                │ ReferenceBuilder│    │ RegionAnalyzer  │
                └─────────────────┘    └────────┬────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │ Persistent Daily │
                                       │ Results          │
                                       │ ResultsManager   │
                                       └────────┬─────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │ Temporal         │
                                       │ Analysis         │
                                       │ TimeSeriesAnalyzer│
                                       └────────┬─────────┘
                                                │
                              ┌─────────────────┴─────────────────┐
                              │                                   │
                              ▼                                   ▼
                    ┌──────────────────┐                ┌──────────────────┐
                    │ Derived Analysis │                │ Scientific       │
                    │ Datasets         │───────────────►│ Visualization    │
                    └──────────────────┘                └────────┬─────────┘
                                                                  │
                                                                  ▼
                                                         ┌──────────────────┐
                                                         │ Generated Plots  │
                                                         │ output/plots/    │
                                                         └──────────────────┘

        docs/ ─────────────────────┐
                                   ▼
                            ┌──────────────────┐
        output/ ───────────►│ Website Build    │
                            │ build_pages.py   │
                            └────────┬─────────┘
                                     │
                                     ▼
                                  build/
                                     │
                                     ▼
                               GitHub Pages
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

The `update` stage delegates the end-to-end incremental workflow to `update_pipeline.py`.

---

## Main Architectural Areas

### Data Acquisition

`src/data_download/` is responsible for retrieving sea-ice data from the NSIDC archive.

`NSIDCDownloader`:

* inspects the remote archive,
* determines locally missing observations,
* downloads missing observations,
* identifies equivalent product files for the same observation date,
* manages temporary local GeoTIFF files.

Downloaded observations are stored temporarily under:

```text
data/geotiff/
```

---

### Spatial Reference Preparation

`ReferenceBuilder` creates and maintains the static spatial reference information required by the regional analysis.

The reference consists of:

* predefined regional masks,
* reference pixel information,
* reference metadata.

The reference GeoTIFF is fixed under:

```text
src/config/reference.tif
```

Generated reference products are stored under:

```text
output/reference/
```

The reference products can be reused by subsequent processing runs.

---

### Spatial Analysis

`RegionAnalyzer` processes individual daily GeoTIFF observations.

It uses the reference masks to:

* extract the configured analysis regions,
* identify valid water pixels,
* apply the sea-ice detection threshold,
* calculate absolute sea-ice coverage,
* calculate relative sea-ice coverage,
* produce regional daily observations.

The current implementation uses a fixed sea-ice pixel detection threshold. Parameterizing this value is covered by the project's configurability requirements but is not yet fully implemented.

The resulting records are passed to `ResultsManager`.

---

### Result Management

`ResultsManager` provides persistent storage for the daily regional analysis results.

The primary dataset is:

```text
output/analysis/ice_coverage_summary.csv
```

Additional metadata is stored in:

```text
output/analysis/latest.json
```

The result manager:

* loads existing results,
* identifies already processed dates,
* adds new regional observations,
* removes duplicate date/region records,
* sorts the result dataset,
* saves the persistent result dataset,
* maintains information about the latest processed observation.

---

### Temporal Analysis

`TimeSeriesAnalyzer` derives temporal analysis products from the persistent daily regional results.

Current processing includes:

* calendar interpolation,
* moving averages,
* 1981–2010 climatology,
* climatological mean,
* climatological standard deviation,
* climatological minimum and maximum,
* absolute anomalies,
* relative anomalies,
* annual means,
* seasonal threshold-event detection.

Threshold event detection uses:

```text
10 %
50 %
90 %
```

The resulting datasets are stored under:

```text
output/analysis/
```

---

### Scientific Visualization

The visualization layer is divided into spatial and temporal visualization.

`SeaIcePlotter` creates spatial maps directly from GeoTIFF observations.

`TimeSeriesPlotter` creates temporal and derived scientific plots from the analysis datasets.

The generated figures are stored under:

```text
output/plots/
```

Visualization products are regenerated from the underlying analysis data rather than serving as inputs to subsequent scientific processing stages.

---

### Pipeline Orchestration

The architecture contains two levels of orchestration.

`src/main.py` provides the external command-line dispatcher.

`src/update/update_pipeline.py` coordinates the incremental end-to-end workflow:

```text
NSIDCDownloader

       ↓

process_data

       ↓

generate_plots

       ↓

build_pages

       ↓

temporary data cleanup
```

The `update` stage therefore combines acquisition, processing, visualization, website generation and temporary-data cleanup into a single incremental workflow.

The `all` stage in `main.py` provides sequential execution of the individual processing stages:

```text
download
    ↓
process
    ↓
plots
    ↓
build
```

The two orchestration paths are intentionally separate: `all` provides explicit sequential stage execution, while `update` implements the operational incremental workflow.

---

### Website Build and Deployment

The website source is located under:

```text
docs/
```

`build_pages.py` combines the website source with the generated project output and creates:

```text
build/
```

The `build/` directory is a generated deployment artifact.

It is not a second source tree and is not used as an input to the scientific analysis.

The resulting artifact is suitable for GitHub Pages deployment.

---

## Data Persistence

The architecture distinguishes three different classes of stored data.

### Temporary Input Data

```text
data/
└── geotiff/
```

Downloaded GeoTIFF observations are temporary processing inputs.

They can be removed after successful processing.

### Persistent Scientific Products

```text
output/
├── analysis/
└── reference/
```

These products contain the persistent scientific state required for subsequent analysis and reproducibility of the current result set.

### Regenerable Visualization and Deployment Products

```text
output/
└── plots/

build/
```

Plots and the website build are generated products.

They can be regenerated from the corresponding source data and website source.

---

## Cross-Cutting Concerns

Several requirements apply across multiple architectural components rather than belonging to a single processing component.

### Configuration

Configuration and project paths are maintained centrally under:

```text
src/config/
```

This includes:

* project paths,
* logging configuration,
* the fixed spatial reference,
* region definitions.

Scientific and operational parameters that are intended to be variable are subject to the project's configurability requirements.

---

### Logging and Diagnostics

The pipeline uses Python logging for operational diagnostics.

Logging covers pipeline execution and processing activities and is configured centrally through the logging configuration.

Logging is intended to provide information about:

* processing stages,
* downloaded and skipped observations,
* failures,
* generated products,
* update execution.

---

### Error Handling

Processing components handle failures locally where appropriate and report failures through the logging system.

The current implementation does not yet provide complete centralized validation and failure propagation for every pipeline stage.

This is part of the current quality gap identified by the requirements.

---

### Testing and Quality Assurance

The project contains a dedicated test directory:

```text
tests/
```

A pytest-based test infrastructure is available through the project dependencies. However, the currently existing test files originate from an earlier implementation phase and no longer correspond to the current component interfaces.

They are therefore not considered valid automated verification of the current implementation.

Testing is nevertheless an explicit architectural concern. The quality strategy defined by the project requirements includes:

* unit and component testing,
* integration testing,
* end-to-end testing,
* regression testing,
* invalid-input and edge-case testing,
* scientific calculation verification,
* output validation,
* and CI-based quality gates.

Systematic automated verification of the current implementation is part of the subsequent quality-assurance work and is documented separately under:

```text
docs/testing/
```

The distinction between operational pipeline execution and formal automated verification is intentional. The current CI workflow provides operational execution of the application, but does not yet constitute a comprehensive automated quality gate.

---

### Output Validation

The requirements define automated output validation as a separate quality concern.

The current implementation does not yet provide a complete centralized output-validation component.

Expected validation includes, among other checks:

* required files,
* expected data structures,
* valid dates and regions,
* numerical ranges,
* duplicate detection,
* successful generation of required figures,
* required website files.

This distinction is intentional: the requirement exists, while the corresponding implementation is not yet complete.

---

### Reproducibility and Traceability

The architecture is based on explicit input data, configuration, source code and generated products.

The current implementation provides partial reproducibility through:

* persistent analysis datasets,
* fixed reference data,
* explicit project configuration,
* documented methodology,
* version-controlled source code.

Complete version and dependency traceability is not yet fully formalized.

---

### CI/CD and Operational Execution

GitHub Actions provides the current automated execution environment.

The workflow:

* installs the Python dependencies,
* executes the incremental update pipeline,
* generates the website deployment artifact,
* uploads the GitHub Pages artifact,
* commits updated scientific output.

The update pipeline itself includes website generation. The current workflow additionally invokes the build stage explicitly before uploading the Pages artifact. This currently results in the website build being executed more than once during an update workflow.

The CI environment therefore provides automated operational execution of the project. It does not yet implement the complete quality-gate strategy defined by the requirements, including systematic automated testing, output validation and static code-quality checks.

---

## Current Architectural Characteristics

The current implementation is characterized by:

* pipeline-oriented processing,
* explicit stage-based CLI control,
* direct Python component calls,
* file-based data exchange between stages,
* separation of acquisition, analysis, visualization and deployment,
* incremental processing based on the latest processed observation date,
* temporary storage of raw observations,
* persistent storage of derived scientific results,
* regenerable visualization products,
* static website deployment.

---

## Architecture Status

This document describes the current state of the implementation.

It does not define:

* a target architecture,
* planned module restructuring,
* dependency inversion,
* final interface design,
* a future plugin architecture,
* future scientific extensions.

Such changes should be defined separately and traced back to the project requirements before implementation.
