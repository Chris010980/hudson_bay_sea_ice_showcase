# Functional Requirements

## Purpose

This document defines the functional requirements of the `hudson_bay_sea_ice` project.

The requirements describe what the system shall do from a functional perspective. They form the basis for subsequent architecture decisions, user stories, acceptance criteria and tests.

The initial draft is based on the current project scope and implementation. Details that still require clarification are explicitly marked as **TBD**.

---

## FR-01 — Sea-Ice Data Acquisition

### FR-01.1 — Retrieve Sea-Ice Observations

The system shall be able to retrieve daily sea-ice concentration observations from the configured NSIDC data source.

### FR-01.2 — Detect Missing Observations

The system shall determine which relevant observations are not yet available in the local working directory.

### FR-01.3 — Avoid Unnecessary Downloads

The system shall not download observations that are already available locally and considered equivalent according to the configured product identification.

### FR-01.4 — Store Downloaded Observations

The system shall store downloaded GeoTIFF observations in the configured temporary data directory using the project directory structure.

### FR-01.5 — Incremental Acquisition

The system shall support downloading observations starting from a specified date.

### FR-01.6 — Initial Data Acquisition

The system shall support an initial acquisition when no previously processed observation exists.

**TBD:** Exact behavior and starting date for an empty dataset.

---

## FR-02 — Temporary Data Management

### FR-02.1 — Temporary Working Data

The system shall treat downloaded GeoTIFF observations as temporary processing input.

### FR-02.2 — Cleanup

The system shall be able to remove locally downloaded GeoTIFF observations after successful processing.

### FR-02.3 — Optional Data Retention

The update pipeline shall provide an option to retain downloaded GeoTIFF observations for inspection or debugging.

---

## FR-03 — Spatial Reference Preparation

### FR-03.1 — Reference Data

The system shall maintain the spatial reference data required for regional sea-ice analysis.

### FR-03.2 — Region Masks

The system shall provide spatial masks for the configured analysis regions.

### FR-03.3 — Reference Initialization

The system shall automatically create the required reference data when it does not yet exist.

### FR-03.4 — Reference Metadata

The system shall store metadata describing the generated reference data.

**TBD:** Exact rules for detecting outdated or invalid reference data.

---

## FR-04 — Daily Sea-Ice Analysis

### FR-04.1 — Process GeoTIFF Observations

The system shall process individual daily sea-ice concentration GeoTIFF observations.

### FR-04.2 — Determine Observation Date

The system shall determine the observation date associated with each input observation.

### FR-04.3 — Handle Invalid Data

The system shall identify and exclude invalid or missing raster values according to the configured product-specific rules.

### FR-04.4 — Regional Analysis

The system shall calculate sea-ice statistics for each configured analysis region.

### FR-04.5 — Relative Sea-Ice Coverage

The system shall calculate relative sea-ice coverage for each analysis region.

### FR-04.6 — Absolute Sea-Ice Coverage

The system shall calculate absolute sea-ice coverage for each analysis region.

### FR-04.7 — Prevent Duplicate Processing

The system shall detect observations that have already been processed and avoid processing them again.

### FR-04.8 — Continue After Individual Processing Errors

A failure while processing an individual observation shall be recorded without unnecessarily terminating the processing of other observations.

**TBD:** Exact failure semantics and criteria for considering a processing run successful.

---

## FR-05 — Persistent Analysis Results

### FR-05.1 — Store Daily Results

The system shall persist daily regional analysis results.

### FR-05.2 — Maintain Chronological Results

Persisted results shall be maintained in chronological order.

### FR-05.3 — Prevent Duplicate Results

The system shall prevent duplicate date/region observations in the persistent result dataset.

### FR-05.4 — Track Latest Observation

The system shall maintain information about the latest processed observation.

### FR-05.5 — Reload Existing Results

The system shall be able to load previously generated analysis results for subsequent processing.

---

## FR-06 — Time-Series Preparation

### FR-06.1 — Generate Daily Time Series

The system shall generate daily regional time-series data from the persistent analysis results.

### FR-06.2 — Calendar-Based Processing

The system shall support a continuous calendar-day representation of the regional time series.

### FR-06.3 — Handle Short Data Gaps

The system shall support interpolation of numerical observations across configured short gaps.

**TBD:** Maximum gap length and interpolation policy should be defined as an explicit scientific requirement rather than only as an implementation parameter.

### FR-06.4 — Moving Average

The system shall calculate a centered moving average for the regional time series.

The current implementation uses a seven-day window corresponding to approximately ±3 days around the observation date.

**TBD:** Whether the seven-day window is a permanent scientific requirement.

---

## FR-07 — Climatological Analysis

### FR-07.1 — Reference Period

The system shall calculate climatological statistics using the configured reference period.

The current reference period is 1981–2010.

### FR-07.2 — Daily Climatology

The system shall calculate climatological statistics for individual calendar days.

### FR-07.3 — Climatological Mean

The system shall calculate the climatological mean sea-ice coverage.

### FR-07.4 — Climatological Variability

The system shall calculate the climatological standard deviation.

### FR-07.5 — Additional Climatological Statistics

The system shall support calculation of minimum and maximum climatological values.

---

## FR-08 — Anomaly Analysis

### FR-08.1 — Calculate Anomalies

The system shall calculate deviations of observations from the corresponding climatological values.

### FR-08.2 — Relative Anomalies

The system shall provide relative anomaly values.

### FR-08.3 — Absolute Anomalies

The system shall provide absolute anomaly values.

### FR-08.4 — Climatological Uncertainty Context

The anomaly data shall retain the corresponding climatological standard deviation required for interpretation.

**TBD:** Exact mathematical definitions and naming of relative versus absolute anomaly measures should be fixed in the scientific methodology.

---

## FR-09 — Annual Analysis

### FR-09.1 — Annual Means

The system shall calculate annual mean sea-ice coverage.

### FR-09.2 — Complete Years

The system shall identify and process complete calendar years according to the configured completeness rules.

### FR-09.3 — Annual Trends

The system shall support calculation of a linear trend for annual mean sea-ice coverage.

### FR-09.4 — Trend Quality Indicator

The system shall provide the coefficient of determination (R²) for the calculated linear trend.

**TBD:** Whether linear regression and R² are the definitive statistical indicators for all future trend analyses.

---

## FR-10 — Seasonal Threshold Events

### FR-10.1 — Threshold Analysis

The system shall identify seasonal threshold crossings for configured sea-ice coverage thresholds.

The current thresholds are:

* 10 %
* 50 %
* 90 %

### FR-10.2 — Break-Up

The system shall determine break-up dates based on downward threshold crossings during the break-up season.

### FR-10.3 — Freeze-Up

The system shall determine freeze-up dates based on upward threshold crossings during the freeze-up season.

### FR-10.4 — Crossing Validation

A threshold event shall only be accepted when the configured crossing criteria are satisfied.

These criteria currently include:

* actual threshold crossing,
* consecutive calendar-day observations,
* persistence,
* linear interpolation of the crossing time.

### FR-10.5 — Seasonal Constraints

The system shall apply the configured seasonal windows when identifying break-up and freeze-up events.

### FR-10.6 — Break-Up / Freeze-Up Relationship

A freeze-up event shall only be considered valid when the corresponding break-up event exists according to the configured event rules.

### FR-10.7 — Threshold Duration

The system shall calculate the duration between break-up and freeze-up for corresponding thresholds.

---

## FR-11 — Scientific Visualization

### FR-11.1 — Spatial Overview

The system shall generate a spatial overview visualization of a sea-ice concentration observation.

### FR-11.2 — Region Visualization

The system shall support visualization of the configured analysis regions on the spatial map.

### FR-11.3 — Individual Region Maps

The system shall support generation of maps for individual analysis regions.

### FR-11.4 — Time-Series Plots

The system shall generate regional sea-ice time-series plots.

### FR-11.5 — Climatology Visualization

Time-series plots shall support visualization of the 1981–2010 climatological mean and variability.

### FR-11.6 — Anomaly Plots

The system shall generate anomaly plots for the regional time series.

### FR-11.7 — Threshold-Duration Plots

The system shall generate threshold-duration plots for the configured thresholds.

### FR-11.8 — Polar Seasonal Plots

The system shall generate polar representations of seasonal sea-ice coverage.

### FR-11.9 — Yearly Mean Plots

The system shall generate plots of annual mean sea-ice coverage including the configured trend information.

### FR-11.10 — Latest Observation

The visualization system shall support highlighting the latest available observation where applicable.

---

## FR-12 — Pipeline Execution

### FR-12.1 — Individual Pipeline Stages

The system shall allow the major processing stages to be executed independently.

The current stages are:

```text
download
process
plots
build
update
```

### FR-12.2 — Complete Pipeline

The system shall provide a command for executing the complete processing pipeline.

### FR-12.3 — Incremental Update

The system shall provide an incremental update operation that processes only newly available observations.

### FR-12.4 — Update Ordering

The incremental update shall execute the relevant stages in the required order:

```text
download
→ process
→ plots
→ build
→ cleanup
```

### FR-12.5 — No-Change Update

If no new relevant observations are available, the update operation shall terminate without unnecessarily regenerating downstream products.

**TBD:** Whether downstream products should nevertheless be rebuildable independently.

---

## FR-13 — Website Generation

### FR-13.1 — Static Website Source

The system shall maintain the website source independently from generated analysis output.

### FR-13.2 — Website Build

The system shall generate a self-contained website build from the static website source and generated output.

### FR-13.3 — Deployment Directory

The build process shall generate the website in the configured deployment directory.

### FR-13.4 — Generated Results in Website

The generated website shall provide access to the relevant current analysis results and visualizations.

### FR-13.5 — Reproducible Build

The website build shall be reproducible from the current website source and generated output.

---

## FR-14 — Command-Line Configuration

### FR-14.1 — Logging Configuration

The pipeline shall allow the logging level to be configured from the command line.

### FR-14.2 — Log File

The pipeline shall allow the log file location to be configured.

### FR-14.3 — Plot Selection

The plotting stage shall allow selection of the requested plot category.

### FR-14.4 — Region Selection

The plotting interface shall support generation of plots for selected regions.

### FR-14.5 — Optional Raw Data Retention

The update interface shall support optional retention of downloaded raw observations.

---

## Open Functional Questions

The following points should be resolved before these requirements are considered final:

1. What is the exact behavior for an initially empty dataset?
2. What defines a valid reference-data version?
3. What are the scientifically justified interpolation rules?
4. Is the seven-day moving average a fixed scientific requirement?
5. What exactly constitutes a complete year?
6. What are the definitive mathematical definitions of relative and absolute anomalies?
7. What persistence duration is required for threshold events?
8. What are the exact seasonal boundaries for all event calculations?
9. Which trend methods are scientifically required?
10. Which plots are mandatory versus optional?
11. What exactly must be included in the public website?
12. What constitutes a successful complete pipeline run?
