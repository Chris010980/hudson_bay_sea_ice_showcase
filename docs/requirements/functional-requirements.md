# Functional Requirements

This document defines the functional requirements of the `hudson_bay_sea_ice` project.

The requirements describe the intended functional behavior of the system independently of the concrete software implementation. The current implementation status is tracked separately.

---

## FR-01 – Sea-Ice Data Acquisition

The system shall retrieve daily sea-ice concentration GeoTIFF observations from the configured NSIDC data source.

The acquisition process shall:

* identify observations that are not available locally,
* download missing observations,
* support incremental acquisition,
* recognize equivalent product versions representing the same observation date and product,
* store downloaded GeoTIFF files in the configured local data directory.

The system shall support acquisition over a configurable date range.

For an initially empty dataset, the system shall support acquisition of all available observations within the selected acquisition period.

If no new observations are available during an incremental update, the system shall terminate without performing unnecessary downstream processing.

---

## FR-02 – Temporary Data Management

Downloaded GeoTIFF files shall be treated as temporary processing input.

After successful processing, the system shall provide a mechanism to remove the downloaded GeoTIFF files from the local working directory.

The persistent historical dataset shall consist of derived analysis results rather than the complete downloaded raw-data archive.

The system shall provide an option to retain downloaded GeoTIFF files for inspection, debugging, or further processing.

---

## FR-03 – Spatial Reference Data Preparation

The system shall use a fixed reference GeoTIFF as the spatial basis for regional analysis.

The reference GeoTIFF shall be selected during project initialization and stored at the configured reference location.

The reference dataset shall remain unchanged during normal incremental processing and shall be independent of the currently processed observation period.

The reference dataset shall not contain missing observations in the relevant spatial domain. The product's explicit value encoding shall be used to distinguish valid observations from special values such as land, coast, or missing data.

Based on the fixed reference dataset, the system shall generate reusable spatial masks for all configured analysis regions.

The generated reference data shall be stored persistently below:

```text
output/reference/
```

For each configured region, the system shall generate a reference summary containing the spatial characteristics required for subsequent analysis.

Reference masks shall be reusable for subsequent daily observations without being rebuilt for every observation.

If derived reference data is missing, the system shall be able to regenerate it from the fixed reference GeoTIFF.

Changing the reference GeoTIFF shall be treated as a methodological change rather than as part of normal incremental processing.

---

## FR-04 – Daily Regional Sea-Ice Analysis

For each valid daily GeoTIFF observation, the system shall calculate sea-ice statistics for each configured analysis region.

The analysis shall distinguish between absolute and relative sea-ice coverage.

### Absolute Sea-Ice Coverage

Absolute sea-ice coverage shall use a binary classification of water pixels.

A water pixel shall be classified as ice-covered when its sea-ice concentration meets or exceeds the configured pixel detection threshold.

For an ice-covered pixel, the complete pixel area shall contribute to the absolute ice-covered area.

For a pixel below the detection threshold, the contribution shall be zero.

With the current spatial resolution, one pixel represents:

```text
625 km²
```

The resulting absolute ice-covered area shall therefore represent a threshold-based, binary estimate of the ice-covered area.

### Relative Sea-Ice Coverage

Relative sea-ice coverage shall use the measured sea-ice concentration as a weighting factor.

For each water pixel classified as ice-covered, the concentration-weighted ice-covered area shall be calculated from the normalized sea-ice concentration and the pixel area.

The contributions of the relevant ice-covered pixels shall be summed to obtain the regional concentration-weighted ice-covered area.

The system shall calculate corresponding coverage percentages relative to the reference water area of each analysis region.

The resulting regional observations shall be persisted for subsequent temporal analysis.

---

## FR-05 – Persistent Analysis Results

The system shall maintain a persistent historical dataset containing the calculated regional daily observations.

Each observation shall be identifiable at least by:

* observation date,
* analysis region.

When new observations are processed, they shall be added to the existing historical dataset without creating duplicate date/region observations.

The system shall maintain information about the latest processed observation in order to support incremental processing.

The persistent results shall support subsequent temporal, climatological, event, and visualization analyses.

---

## FR-06 – Time-Series Preparation

The system shall derive daily time-series data from the persistent regional observations.

The system shall construct a daily calendar for each analysis region.

Where observations are missing, the system shall support temporal interpolation for gaps that do not exceed the configured maximum interpolation gap.

Gaps exceeding the permitted interpolation range shall not be bridged by interpolation.

Interpolation shall be independent of the moving-average operation used for visualization.

Leap years shall be handled according to the actual calendar.

A complete calendar year shall contain:

* 365 daily values in a non-leap year,
* 366 daily values in a leap year.

The maximum interpolation gap shall be defined as an explicit analysis parameter.

---

## FR-07 – Climatological Analysis

The system shall calculate a daily climatological reference from the historical regional time series.

The current climatological reference period shall be:

```text
1981–2010
```

For each calendar day, the system shall calculate the climatological statistics required for subsequent analysis and visualization.

At minimum, the climatology shall provide:

* mean,
* standard deviation,
* minimum,
* maximum.

The climatological statistics shall be calculated separately for the relevant sea-ice coverage measures.

The calendar structure shall be respected, including February 29 where applicable.

---

## FR-08 – Anomaly Analysis

The system shall calculate sea-ice coverage anomalies relative to the climatological reference.

The anomaly shall be calculated as:

```text
anomaly = observed value − climatological mean
```

The system shall calculate anomalies separately for the relevant absolute and relative sea-ice coverage measures.

The anomaly reference shall use the 1981–2010 climatology.

Anomalies shall retain the units and physical meaning of their corresponding coverage measures.

The resulting anomaly data shall be available for visualization and further analysis.

---

## FR-09 – Annual Analysis

The system shall calculate annual sea-ice coverage statistics from the daily regional time series.

A complete calendar year shall be defined as:

```text
01 January – 31 December
```

Complete years shall contain:

* 365 daily values in non-leap years,
* 366 daily values in leap years.

Annual statistics shall only be calculated for region-years satisfying the defined completeness and interpolation rules.

At minimum, the system shall calculate annual mean sea-ice coverage.

The system shall support calculation of a linear trend from the annual values and the corresponding coefficient of determination (`R²`).

Nonlinear trend models are outside the current functional scope.

---

## FR-10 – Seasonal Threshold Event Analysis

The system shall identify seasonal sea-ice events based on predefined sea-ice coverage thresholds.

The current thresholds shall be:

```text
10 %
50 %
90 %
```

The system shall determine both:

* break-up events,
* freeze-up events.

Break-up analysis shall cover the seasonal period from:

```text
16 March – 15 September
```

Freeze-up analysis shall cover the period from:

```text
16 September – 15 March of the following year
```

The freeze-up search period may be adjusted dynamically when required by the observed seasonal state.

A threshold crossing shall only be classified as a valid event when the required threshold condition persists for the configured number of consecutive calendar days.

The current persistence requirement shall be:

```text
7 consecutive days
```

The persistence requirement shall be evaluated independently for each threshold.

The pixel-level sea-ice detection threshold, seasonal event thresholds, persistence requirement, and visualization smoothing shall be treated as separate analysis parameters.

Event dates shall be persisted together with the associated region, event type, event year, and threshold.

---

## FR-11 – Scientific Visualization

The system shall provide scientific visualizations for the generated sea-ice analysis products.

The visualization scope shall include:

* daily sea-ice coverage time series,
* climatological analysis products and their visualization where implemented,
* anomaly time series,
* threshold-duration and seasonal event visualizations,
* polar seasonal representations,
* annual mean coverage,
* annual trend information,
* overview maps,
* regional sea-ice maps,
* and maps showing the defined analysis regions.

Standard visualization products shall be generated as part of a complete plot run. Individual plot types may be selected through the command-line interface where supported.

Visualization generation shall:

* use the persistent analysis results as input,
* preserve the distinction between absolute and relative sea-ice coverage,
* apply documented temporal smoothing only as a presentation aid where configured,
* support regional selection where applicable,
* and generate reproducible output files in the configured plot directory.

The visualization layer shall not alter the underlying scientific analysis results.

Not all planned visualization products are required to be fully implemented in the v0.1 baseline. Missing or incomplete visualization components are tracked as implementation work and may be completed as part of subsequent development iterations.

---

## FR-12 – Pipeline Execution

The system shall provide separate pipeline stages for:

* data acquisition,
* data processing,
* plot generation,
* website building,
* complete/incremental updating.

A complete pipeline run shall perform the following operations in the defined order:

1. identify and acquire the required GeoTIFF observations;
2. prepare or verify the required reference data;
3. process the daily observations for all configured regions;
4. persist the resulting regional observations;
5. perform the derived temporal and climatological analyses;
6. generate the configured visualization products;
7. build the GitHub Pages website.

The incremental update process shall:

1. determine the latest processed observation;
2. request only observations after the latest processed date;
3. process newly acquired observations;
4. regenerate the derived analysis products;
5. regenerate the visualization products;
6. rebuild the website;
7. remove temporary GeoTIFF input data unless retention has been requested.

If no new observations are available, the incremental pipeline shall terminate without modifying the existing analysis results, plots, or website.

A successful update containing new observations shall therefore produce a consistent set of updated analysis results, visualizations, and website content.

---

## FR-13 – Website Generation

The system shall generate a self-contained static website containing the current project documentation and generated analysis results.

The generated website shall combine:

* the static website source,
* the current analysis results,
* the current visualization products.

The website shall include all visualization products generated by the current analysis pipeline, including:

* anomaly plots,
* threshold-duration plots,
* annual mean and trend plots,
* time-series plots,
* polar plots,
* overview maps,
* regional maps.

The website shall be regenerated after new analysis results and visualization products have been generated.

The generated website shall be deployable independently of the project source directory.

If no new observations are available during an incremental update, the existing website shall remain unchanged.

---

## FR-14 – Command-Line Configuration

The system shall provide a command-line interface for the available pipeline stages.

The command-line interface shall support, where applicable:

* pipeline-stage selection,
* logging-level selection,
* log-file selection,
* processing start date,
* processing end date,
* visualization-type selection,
* analysis-region selection,
* generation for all configured regions,
* optional display of generated plots,
* retention of temporary GeoTIFF input data.

The available command-line options shall be documented as part of the project documentation.

---

## Resolved Functional Decisions

The following decisions define the interpretation of the requirements.

### Initially Empty Dataset

An initially empty dataset shall trigger a full acquisition and processing operation for the selected acquisition period.

The acquisition and processing period may be restricted by start and end dates.

### Reference Dataset

The project uses a fixed reference GeoTIFF selected during initial project setup.

The reference GeoTIFF is not selected dynamically during normal processing.

Derived reference masks and summary data may be regenerated from this fixed reference when required.

Changing the reference dataset constitutes a methodological change and is outside normal incremental processing.

### Interpolation

Interpolation is permitted only for gaps not exceeding the configured maximum interpolation gap.

Interpolation is performed on the daily calendar and is intended to support complete-year analysis where sufficient data are available.

### Moving Average

The moving average is a visualization aid and is not itself a scientific requirement.

It may be used to reduce short-term fluctuations and improve visual readability.

The current implementation uses a centered seven-day window corresponding to ±3 days.

The smoothing operation shall remain independent of the underlying daily analysis results.

### Complete Year

A complete year covers 01 January through 31 December.

Completeness is evaluated separately for each analysis region.

### Anomaly Definition

An anomaly is defined as:

```text
observed value − climatological mean
```

The anomaly is therefore an absolute deviation from the climatological mean in the units of the underlying quantity.

### Trend Definition

The current trend analysis uses linear regression on annual values.

The coefficient of determination (`R²`) shall be reported together with the linear trend.

A low `R²` shall not by itself be interpreted as evidence that no trend exists.

### Visualization Scope

All currently implemented visualization types are considered part of the public project output.

Individual pipeline runs may restrict visualization generation for operational or development purposes.

### Successful Update

A successful incremental update with new observations shall result in synchronized updates of:

```text
historical analysis results
        ↓
derived time-series results
        ↓
plots
        ↓
GitHub Pages build
```

An update without new observations shall not modify these products.
