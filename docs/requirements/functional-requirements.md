# Functional Requirements

This document defines the functional requirements of the Hudson Bay Sea Ice Analysis project.

## FR-01 – Sea-Ice Data Acquisition

The system shall retrieve the available daily sea-ice concentration GeoTIFF files from the configured NSIDC data source.

The downloader shall:

* identify locally missing observations,
* download missing observations,
* support incremental updates,
* recognize equivalent product versions for the same observation date,
* store downloaded files in the configured temporary data directory.

For an initially empty dataset, the system shall download all available observations within the configured acquisition period and process them as a new dataset.

The acquisition and processing period shall optionally be restrictable by a configurable start date and, where required, an end date.

If no new observations are available during an incremental update, the system shall not perform further processing and shall leave the existing analysis results and website unchanged.

---

## FR-02 – Temporary Data Management

Downloaded GeoTIFF files shall be treated as temporary input data.

After successful processing, temporary GeoTIFF files shall be removable from the local working directory.

The persistent historical dataset shall consist of the derived analysis results rather than the downloaded raw GeoTIFF archive.

The system shall provide an option to retain downloaded GeoTIFF files for inspection or debugging.

---

## FR-03 – Spatial Reference Data Preparation

The system shall identify a suitable reference GeoTIFF from the available sea-ice dataset.

The reference dataset shall not contain actual `NaN` or missing values in the relevant spatial domain. The product's explicit value encoding shall be used to distinguish between:

* open water,
* sea ice,
* land,
* coast,
* other explicitly encoded invalid or special values.

Based on the reference dataset, the system shall generate a spatial mask for each configured analysis region.

The generated reference data shall be stored persistently below `output/reference/`.

For each region, a reference summary shall be generated in JSON format containing the relevant characteristics required for subsequent analysis.

The reference masks shall be reusable for subsequent daily processing without being rebuilt for every observation.

---

## FR-04 – Daily Regional Sea-Ice Analysis

For each valid daily GeoTIFF, the system shall extract the sea-ice information for each configured analysis region.

For each region and observation date, the system shall calculate the configured sea-ice coverage metrics.

The analysis shall distinguish between **absolute** and **relative** sea-ice coverage.

### Absolute Sea-Ice Coverage

Absolute sea-ice coverage shall use a binary classification of each water pixel.

For each water pixel:

* if the sea-ice concentration exceeds the configured pixel detection threshold, the complete pixel area shall be counted as ice-covered;
* otherwise, the pixel shall contribute zero ice-covered area.

With the current spatial resolution, one pixel represents an area of **625 km²**.

Thus, each pixel contributes either:

* `0 km²`, or
* `625 km²`.

The resulting value represents the binary, threshold-based ice-covered area of the region.

The pixel detection threshold represents the effective detection/resolution limit of the underlying measurement product. Its exact value and scientific justification are separate from the thresholds used for seasonal event detection.

### Relative Sea-Ice Coverage

Relative sea-ice coverage shall use the measured sea-ice concentration as a weighting factor.

For each water pixel, the ice-covered area contribution shall be calculated as:

$$
A_{\mathrm{ice,pixel}}
=
625\,\mathrm{km^2}
\cdot
c_{\mathrm{pixel}}
$$

where \(c_{\mathrm{pixel}}\) is the normalized sea-ice concentration in the range 0 to 1.

The contributions of all relevant water pixels shall then be summed to obtain the concentration-weighted ice-covered area.

The relative metric therefore represents a continuous, concentration-weighted estimate, whereas the absolute metric represents a binary, threshold-based estimate.

The system shall persist the resulting regional observations for subsequent temporal analysis.

---

## FR-05 – Persistent Analysis Results

The system shall maintain a persistent historical result dataset containing the calculated regional observations.

Results shall be identifiable at least by:

* observation date,
* analysis region.

When new observations are processed, they shall be added to the existing result dataset without duplicating already processed observations.

The system shall maintain information about the latest processed observation to support incremental processing.

---

## FR-06 – Time-Series Preparation

The system shall derive time-series data from the persistent daily regional results.

Where observations are missing, the system shall support linear interpolation if the temporal gap does not exceed the configured maximum gap.

Interpolation shall be performed on the daily calendar so that complete calendar years can be constructed where the available data and interpolation rules permit this.

Interpolation shall not bridge gaps exceeding the configured maximum gap.

Leap years shall be handled according to the actual calendar, i.e. complete years contain:

* 365 daily values for non-leap years,
* 366 daily values for leap years.

The moving average used for visualization shall be treated independently from the interpolation process.

---

## FR-07 – Climatological Analysis

The system shall calculate a climatological reference based on the configured reference period.

The current reference period is **1981–2010** for daily climatological values.

For each calendar day, the system shall calculate the climatological statistics required for subsequent visualization and anomaly analysis.

At minimum, the climatology shall provide:

* mean,
* standard deviation,
* minimum,
* maximum.

The climatological statistics shall be calculated separately for the relevant sea-ice coverage measures.

The climatology shall account for the actual calendar structure, including February 29 where applicable.

---

## FR-08 – Anomaly Analysis

The system shall calculate anomalies relative to the climatological reference.

The anomaly shall be calculated separately for the corresponding absolute and relative sea-ice coverage measures.

The current definition is:

`anomaly = observed value − climatological mean`

The reference climatology shall cover the period **1981–2010**.

The resulting anomaly data shall be available for visualization and further analysis.

The system shall support both:

* absolute anomalies,
* relative anomalies.

The anomaly shall retain the units and meaning of the corresponding underlying coverage metric.

---

## FR-09 – Annual Analysis

The system shall calculate annual sea-ice coverage statistics.

A complete calendar year shall be defined as the period from **01 January through 31 December**.

A complete year therefore contains:

* 365 daily values in a non-leap year,
* 366 daily values in a leap year.

Annual statistics shall only be calculated according to the defined completeness and interpolation rules.

At minimum, the system shall support annual mean sea-ice coverage.

The system shall calculate a linear trend for the annual values and provide the corresponding coefficient of determination (`R²`).

Linear regression is currently the required trend method. More complex or non-linear trend models are outside the current scope.

---

## FR-10 – Seasonal Threshold Events

The system shall determine sea-ice threshold events for the configured seasonal event thresholds.

The current seasonal event thresholds are:

* 10%,
* 50%,
* 90%.

The system shall determine threshold crossings separately for:

* break-up,
* freeze-up.

The initial seasonal definitions are:

* **break-up season:** 16 March – 15 September,
* **freeze-up season:** 16 September – 15 March of the following year.

The start of the freeze-up search may be dynamically adjusted where required to account for freeze-up occurring earlier than 16 September.

A threshold crossing shall only be considered a valid event if the threshold condition persists for **7 consecutive calendar days**.

The following concepts shall be treated independently:

* pixel detection threshold used for absolute sea-ice coverage,
* seasonal event thresholds used for break-up and freeze-up,
* persistence duration used to validate seasonal events,
* moving-average window used for visualization.

The resulting event dates shall be stored for subsequent analysis.

---

## FR-11 – Scientific Visualization

The system shall generate the complete set of configured analysis visualizations.

The current visualization set includes, where applicable:

* daily time-series plots,
* climatological mean and standard-deviation visualization,
* anomaly plots,
* threshold-duration plots,
* polar seasonal plots,
* annual mean plots,
* trend visualizations,
* overview maps,
* regional maps.

All configured plots shall be generated by default.

The user shall be able to restrict plot generation to selected plot types and/or selected regions.

---

## FR-12 – Pipeline Execution

The system shall provide pipeline stages for:

* data download,
* data processing,
* plot generation,
* website build,
* complete/incremental update.

A complete pipeline run shall perform the following operations:

1. identify and download missing GeoTIFF observations;
2. extract regional data;
3. calculate and persist the resulting values;
4. perform the derived time-series analysis;
5. regenerate the configured visualizations;
6. update the website build.

A successful update with new observations shall therefore result in an updated analysis dataset, updated plots, and an updated website.

If no new observations are available, the pipeline shall terminate successfully without modifying the existing analysis results, plots, or website.

---

## FR-13 – Website Generation

The system shall generate a self-contained website containing the current project information and analysis results.

The public website shall include all currently generated analysis plots.

This includes the currently implemented visualization and analysis types, in particular:

* anomaly plots,
* threshold-duration plots,
* annual and trend plots,
* time-series plots,
* polar plots,
* overview maps,
* regional maps.

The website shall be regenerated whenever new analysis results and corresponding plots are generated.

If no new observations are available, the website shall remain unchanged.

---

## FR-14 – Command-Line Configuration

The system shall provide command-line configuration for the available pipeline stages.

The command-line interface shall support, where applicable:

* selection of pipeline stage,
* logging level,
* log file,
* processing start date,
* processing end date,
* plot type,
* region selection,
* generation of plots for all configured regions,
* display of plots,
* retention of temporary input data.

The available configuration options shall be documented as part of the project documentation.

---

# Resolved Functional Questions

## Initially Empty Dataset

An initially empty dataset shall trigger a full acquisition and processing operation for all observations available within the configured acquisition period.

An optional start date and, where required, end date shall allow the initial processing period to be restricted.

---

## Reference Dataset

The reference dataset shall be the first suitable GeoTIFF without actual `NaN` or missing values in the relevant spatial domain.

The product's explicit value encoding shall be used to distinguish valid and special spatial categories.

Reference masks shall be generated once for the selected reference dataset and stored under `output/reference/`, together with a JSON summary containing the relevant characteristics for each configured region.

---

## Interpolation

Missing observations may be linearly interpolated when the temporal gap is sufficiently small.

Interpolation is intended primarily to enable complete calendar years and thereby consistent annual statistics.

The maximum permitted interpolation gap shall be a configurable analysis parameter.

Leap years shall be treated according to the actual calendar.

---

## Moving Average

The moving average is **not a scientific requirement**.

It is a visualization aid intended to:

* reduce short-term fluctuations,
* improve visual readability,
* reduce strong overlap between curves,
* reduce threshold crossings caused by rapidly oscillating values.

The current seven-day window corresponds to the current `±3 days` implementation.

The smoothing window shall therefore be treated as a configurable heuristic visualization parameter rather than a scientific property of the underlying data.

---

## Complete Year

A complete year is a complete calendar year from 01 January through 31 December.

It contains:

* 365 days in a non-leap year,
* 366 days in a leap year.

---

## Anomalies

Anomalies are calculated relative to the 1981–2010 climatological mean.

The anomaly is the difference between the observation and the corresponding climatological mean:

`anomaly = observation − climatological mean`

This is calculated independently for the absolute and relative sea-ice coverage measures.

---

## Trend Analysis

Linear regression is currently the required trend method.

Some time series may exhibit step-like or otherwise non-linear behavior. This does not currently require a different trend model.

The coefficient of determination (`R²`) shall be reported as an indicator of how well a linear model represents the data. A comparatively low `R²` shall not by itself be interpreted as evidence that no overall trend exists.

---

## Plot Generation

All currently implemented plot types are considered required outputs.

Users may nevertheless restrict execution to selected plot types and/or regions when a complete plot generation is not required.

---

## Public Website

The public website shall contain all currently generated plots.

The website shall therefore evolve together with the analysis pipeline as new visualization and analysis components are introduced.

---

## Successful Pipeline Run

A successful update with new observations shall:

1. download missing observations;
2. extract regional data;
3. calculate and persist new values;
4. update the derived analysis;
5. regenerate the configured plots;
6. update the website.

If no new observations are available, the pipeline shall terminate successfully without modifying the existing analysis results, plots, or website.
