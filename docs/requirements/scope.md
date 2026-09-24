# Project Scope

## 1. Purpose

This document defines the scope of the `hudson_bay_sea_ice` project.

The project provides an automated Python-based pipeline for acquiring, processing, analyzing, visualizing, and publishing daily sea-ice concentration observations for the Hudson Bay region.

The scope describes the capabilities that are currently part of the system and distinguishes them from explicitly excluded or future functionality.

Functional and non-functional requirements are defined separately in:

```text
docs/requirements/functional-requirements.md
docs/requirements/non-functional-requirements.md
```

The scope therefore defines the system boundary, while the requirements define the expected behavior and quality characteristics within that boundary.

---

## 2. System Scope

The current system covers the following capabilities:

1. acquisition of daily NSIDC sea-ice concentration GeoTIFF data,
2. incremental synchronization of newly available observations,
3. spatial preprocessing and regional analysis,
4. persistent storage of daily analysis results,
5. temporal and climatological analysis,
6. anomaly and annual-statistics generation,
7. threshold-based seasonal event analysis,
8. scientific visualization,
9. pipeline orchestration and command-line execution,
10. automated incremental updates,
11. generation of a static project website,
12. automated preparation of the website for GitHub Pages deployment.

The system is implemented as a Python application with separate components for data acquisition, analysis, visualization, update orchestration, and website generation.

---

## 3. Data Scope

The current data acquisition component processes daily sea-ice concentration GeoTIFF products provided through the NSIDC/NOAA daily northern-hemisphere archive.

The downloader supports:

* remote archive inspection,
* identification of available observations,
* comparison with locally available files,
* incremental download of missing observations,
* recognition of equivalent files with different product-version filenames,
* optional removal of temporary local GeoTIFF files after processing.

Raw GeoTIFF observations are treated as processing input data and are not part of the generated website artifact.

The current implementation does not acquire or process additional external scientific datasets as part of the automated update pipeline.

---

## 4. Spatial Scope

The analysis is based on predefined spatial regions.

The current regions are:

* Hudson Bay,
* Gulf of Boothia,
* Foxe Basin,
* Hudson Strait,
* Hudson Bay Area.

The exact spatial definitions are maintained separately from the analysis implementation.

The system generates both:

* an overall spatial overview,
* and regional analysis products for the configured regions.

Spatial processing is based on the available sea-ice concentration raster data and the corresponding predefined analysis masks.

Interactive region definition or arbitrary user-defined spatial selection is not currently part of the system.

---

## 5. Temporal Scope

The system processes daily observations.

The current temporal analysis includes:

* daily regional time series,
* complete calendar-year statistics where sufficient data are available,
* a 1981–2010 climatological reference period,
* climatological means,
* climatological standard deviations,
* absolute anomalies,
* relative anomalies,
* annual mean indicators,
* seasonal break-up analysis,
* seasonal freeze-up analysis,
* threshold-duration analysis.

The temporal analysis is designed around daily sea-ice concentration observations and preserves historical results rather than rebuilding the complete dataset for every incremental update.

---

## 6. Scientific Scope

The scientific scope is limited to sea-ice concentration and derived sea-ice coverage indicators.

The current analysis provides:

* relative sea-ice coverage,
* absolute sea-ice coverage,
* climatological means,
* climatological standard deviations,
* absolute anomalies,
* relative anomalies,
* annual mean values,
* threshold crossing dates,
* break-up dates,
* freeze-up dates,
* threshold-duration values,
* seasonal representations of the analyzed time series.

Threshold-based analyses currently use the following concentration levels:

```text
10 %
50 %
90 %
```

The precise interpretation of these metrics and the corresponding analysis methodology are documented separately under:

```text
docs/methodology/
```

The project is intended to provide reproducible quantitative analysis of the available observations. It does not currently attempt to model or predict future sea-ice conditions.

---

## 7. Analysis and Persistence Scope

Processed observations are stored as persistent analysis results.

The current result structure includes:

```text
output/analysis/
├── ice_coverage_summary.csv
├── ice_coverage_timeseries.csv
├── ice_coverage_yearly.csv
├── ice_coverage_events.csv
└── latest.json
```

The result-management component is responsible for maintaining the historical analysis dataset and avoiding duplicate processing of already processed observation dates.

Derived reference products, including regional water masks and reference metadata, are stored separately under:

```text
output/reference/
```

These products can be reused by subsequent processing runs.

---

## 8. Visualization Scope

The current visualization scope includes:

* spatial sea-ice concentration maps,
* overview maps,
* maps showing analysis regions,
* individual regional maps,
* absolute time-series plots,
* relative time-series plots,
* polar seasonal plots,
* annual mean plots,
* absolute anomaly plots,
* relative anomaly plots,
* threshold-duration plots.

Generated visualization products are stored under:

```text
output/plots/
```

The visualization components are designed to consume the processed analysis results and generate reproducible static figures.

Interactive visualization is not currently part of the system scope.

---

## 9. Pipeline and Automation Scope

The project provides a command-line pipeline with the following stages:

```text
download
process
plots
build
update
all
```

The pipeline supports:

* individual execution of processing stages,
* execution of the complete processing workflow,
* incremental updates based on the latest processed observation,
* regeneration of affected analysis products,
* regeneration of visualizations,
* generation of the website deployment artifact.

The incremental update workflow currently follows the general sequence:

```text
Determine latest processed date
        ↓
Synchronize newly available observations
        ↓
Process new observations
        ↓
Update persistent analysis results
        ↓
Generate analysis products
        ↓
Generate visualizations
        ↓
Build website
        ↓
Optionally remove temporary GeoTIFF files
```

The GitHub Actions workflow executes this update process automatically on a scheduled basis and can also be triggered manually.

---

## 10. Website and Deployment Scope

The project contains a static website providing project documentation, methodology, pipeline information, regional descriptions, current results, and future-development information.

The website source is maintained under:

```text
docs/
```

Generated scientific results remain under:

```text
output/
```

The website build process combines the static website source with the generated analysis results and visualization products into:

```text
build/
```

The `build/` directory is a generated deployment artifact and is not a second source tree.

The resulting artifact is suitable for deployment through GitHub Pages.

The website therefore provides both:

* documentation of the project,
* and access to the current generated scientific results.

The website is currently static. Interactive application functionality is outside the current scope.

---

## 11. Quality and Verification Scope

Testing and quality assurance are part of the project scope.

The current project contains an automated pytest-based test infrastructure and tests for selected visualization functionality.

However, systematic automated verification does not yet cover all functional and non-functional requirements.

The current scope therefore includes:

* automated unit/component testing where implemented,
* regression testing as the test suite is expanded,
* CI-based quality checks,
* validation of generated outputs,
* verification of scientific calculations,
* reproducibility checks.

The current implementation should not be interpreted as having complete automated verification coverage.

The detailed verification strategy is defined separately in the testing documentation.

---

## 12. Operational Scope

The system is designed to operate as a reproducible batch-processing pipeline.

Operational functionality currently includes:

* scheduled execution through GitHub Actions,
* manual workflow execution,
* incremental data acquisition,
* persistent result updates,
* logging,
* error handling within processing stages,
* generated output management,
* GitHub Pages deployment.

The system is not intended to provide a continuously running service or real-time data-processing API.

---

## 13. Current Non-Goals

The following capabilities are explicitly outside the current system scope:

* sea-ice thickness analysis,
* sea-ice volume analysis,
* physical sea-ice modelling,
* future sea-ice prediction,
* interactive region selection,
* arbitrary user-defined analysis regions,
* surface-current analysis,
* integration of additional external scientific datasets,
* interactive web applications,
* real-time streaming processing,
* a continuously running server-side analysis service.

These topics may be considered future extensions, but they are not current system requirements.

---

## 14. Future Extensions

Potential future extensions include:

* sea-ice thickness and volume analysis,
* higher-resolution auxiliary sea-ice products,
* additional scientific datasets,
* interactive regional selection,
* additional environmental or oceanographic variables,
* extended anomaly and climatology analysis,
* additional scientific indicators,
* expanded automated verification,
* further CI quality gates.

Such extensions must be evaluated against the project requirements and scope before becoming part of the supported system.

---

## 15. Scope Status

This document describes the current system boundary and implementation scope.

It should be interpreted together with:

```text
functional-requirements.md
non-functional-requirements.md
requirements-traceability.md
```

The relationship is:

```text
Scope
  │
  ├── defines what belongs to the system
  │
  ▼
Requirements
  │
  ├── define required behavior and quality
  │
  ▼
Architecture
  │
  ├── defines system structure
  │
  ▼
Implementation
  │
  ├── provides the actual functionality
  │
  ▼
Testing and Verification
```

Changes to the supported system capabilities should be reflected consistently in the scope, requirements, architecture, implementation, and traceability documentation.
