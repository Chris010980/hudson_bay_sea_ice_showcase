# Hudson Bay Sea Ice Analysis

Automated analysis and visualization of daily sea-ice concentration in the Hudson Bay region using Python and NSIDC/NOAA satellite data.

The project provides a reproducible, pipeline-oriented workflow for acquiring daily sea-ice concentration observations, performing regional spatial analysis, maintaining persistent time series, deriving climatological and seasonal indicators, generating scientific visualizations, and publishing the results through a static GitHub Pages website.

---

## Overview

Sea-ice conditions in the Hudson Bay system vary strongly throughout the year and differ substantially between its individual subregions.

This project processes daily sea-ice concentration observations to quantify these variations using a consistent spatial and temporal methodology.

The current pipeline covers:

* automated acquisition of daily NSIDC sea-ice concentration GeoTIFFs,
* incremental processing of newly available observations,
* spatial analysis of predefined Hudson Bay regions,
* persistent storage of daily regional results,
* climatological analysis,
* anomaly calculation,
* annual statistics,
* threshold-based break-up and freeze-up analysis,
* scientific visualization,
* automated website generation,
* and GitHub Pages deployment.

The project is designed as a reproducible scientific data-processing application rather than an interactive analysis platform.

---

## Key Features

### Automated data acquisition

The project synchronizes locally available observations with the remote NSIDC/NOAA archive.

The downloader can:

* inspect available remote observations,
* identify missing observations,
* download only newly required files,
* recognize equivalent product-version filenames,
* preserve existing downloaded data,
* and optionally remove temporary GeoTIFF files after processing.

### Incremental processing

The update pipeline determines the latest processed observation and continues from that point instead of rebuilding the complete historical analysis for every update.

The general workflow is:

```text
Latest processed observation
          ↓
Synchronize new observations
          ↓
Process new GeoTIFFs
          ↓
Update persistent results
          ↓
Generate derived time series
          ↓
Generate plots
          ↓
Build website
          ↓
Clean temporary data
```

The workflow is executed automatically through GitHub Actions and can also be triggered manually.

### Regional analysis

Five predefined regions are currently analyzed independently:

* Hudson Bay
* Gulf of Boothia
* Foxe Basin
* Hudson Strait
* Hudson Bay Area

Region definitions are maintained separately from the analysis implementation.

Reusable spatial reference masks are generated from the configured region geometries and stored under `output/reference/`.

### Scientific time-series analysis

The project derives:

* daily regional sea-ice coverage,
* 7-day centered moving averages,
* 1981–2010 climatologies,
* climatological standard deviations,
* absolute anomalies,
* relative anomalies,
* complete-year annual means,
* threshold crossing dates,
* break-up dates,
* freeze-up dates,
* and threshold durations.

### Scientific visualization

The pipeline generates static figures including:

* spatial sea-ice concentration maps,
* regional overview maps,
* regional maps,
* absolute time-series plots,
* relative time-series plots,
* polar seasonal plots,
* annual mean plots,
* anomaly plots,
* and threshold-duration plots.

Generated products are stored below:

```text
output/plots/
```

### Static project website

The project includes a static website documenting:

* the project and its purpose,
* the processing pipeline,
* scientific methodology,
* analysis regions,
* current results,
* and future extensions.

The website source is maintained separately from generated scientific output.

---

## Scientific Methodology

### Input data

The pipeline processes daily sea-ice concentration GeoTIFF products from the northern-hemisphere NSIDC/NOAA archive.

The current spatial processing uses the NSIDC polar stereographic grid in `EPSG:3411`.

The configured raster grid uses a nominal pixel size of:

```text
25 km × 25 km
```

corresponding to a configured pixel area of:

```text
625 km²
```

This area is treated as a project-level calculation assumption rather than an exact physical area correction for the polar stereographic grid.

---

### Sea-ice concentration

The input concentration values use the product's encoded `0–1000` representation.

Valid values are normalized to:

```text
0.0 – 1.0
```

Values above `1000` are treated as special or invalid values rather than valid concentration values.

The pixel-level ice-selection threshold used by the regional analysis is:

```text
15 %
```

This threshold is distinct from the regional seasonal event thresholds of 10%, 50%, and 90%.

---

### Regional coverage metrics

For every region and observation date, the pipeline calculates complementary coverage metrics.

#### Absolute ice coverage

Absolute coverage is based on the number of selected ice-containing pixels multiplied by the configured pixel area.

#### Relative ice coverage

Relative coverage accounts for the fractional sea-ice concentration within the selected pixels.

It is therefore not simply an arithmetic mean of concentration over all pixels in the region.

Both metrics are normalized against the fixed reference water area of the region.

The resulting daily analysis contains, among other fields:

```text
water_pixels
water_area_km2
absolute_ice_area_km2
relative_ice_area_km2
absolute_coverage_percent
relative_coverage_percent
missing_pixels
```

The fixed spatial denominator ensures that regional coverage remains comparable across observations.

---

### Spatial reference data

The project creates reusable spatial reference products from the configured region geometries.

The processing uses:

* the raster geometry,
* the configured `EPSG:3411` spatial reference,
* region polygons,
* and a fixed reference water mask.

Pixels are included or excluded as complete raster cells. Partial-pixel intersection is not currently used.

The generated masks are cached and reused during subsequent daily processing.

---

### Temporal processing

The daily regional results form the basis for the subsequent time-series analysis.

For each region, the time-series processing reconstructs the complete daily calendar between the first and last available observations.

Short gaps can be interpolated using time-based interpolation. The current implementation allows interpolation across gaps of up to 14 days.

A centered 7-day moving average is calculated using three days on either side of the observation.

Annual statistics are calculated only for complete calendar years with valid daily coverage values.

---

### Climatology and anomalies

The current climatological reference period is:

```text
1981–2010
```

Climatological statistics are calculated by calendar day.

The resulting reference data include:

* mean,
* standard deviation,
* minimum,
* maximum.

Anomalies are calculated as the difference between an observation and the corresponding climatological mean.

Both absolute and relative coverage anomalies are supported.

---

### Seasonal event detection

Seasonal event detection is based on relative regional sea-ice coverage.

Three thresholds are currently evaluated:

```text
90 %
50 %
10 %
```

Break-up is defined as a downward threshold crossing, while freeze-up is defined as an upward crossing.

A valid crossing requires persistence for seven consecutive calendar days.

Threshold dates are determined by linear interpolation between observations surrounding the crossing where appropriate.

The seasonal search windows distinguish between break-up and freeze-up and account for the transition between calendar years.

The resulting event information includes threshold dates and threshold-duration values.

---

## Processing Pipeline

The command-line application provides the following stages:

```text
download
process
plots
build
update
all
```

### `download`

Synchronizes the local GeoTIFF archive with the available remote observations.

### `process`

Processes daily observations and updates the persistent regional analysis results.

### `plots`

Generates the scientific visualization products from the processed analysis data.

### `build`

Builds the static website deployment artifact from the website source and generated scientific outputs.

### `update`

Runs the incremental update workflow.

The update stage determines the latest processed observation and performs the required downstream processing for newly available observations.

### `all`

Provides execution of the complete processing workflow.

---

## Project Architecture

The project follows a pipeline-oriented architecture with dedicated components for the major processing areas.

```text
Data Acquisition
      │
      ▼
Spatial Analysis
      │
      ▼
Result Management
      │
      ▼
Temporal Analysis
      │
      ▼
Visualization
      │
      ▼
Website Build
```

The actual implementation uses direct Python component calls and file-based exchange between processing stages.

The main components are:

| Component            | Responsibility                                     |
| -------------------- | -------------------------------------------------- |
| `NSIDCDownloader`    | Remote data discovery and incremental download     |
| `ReferenceBuilder`   | Creation of reusable spatial reference products    |
| `RegionAnalyzer`     | Daily regional sea-ice analysis                    |
| `ResultsManager`     | Persistent storage and management of daily results |
| `TimeSeriesAnalyzer` | Temporal, climatological and event analysis        |
| `SeaIcePlotter`      | Spatial sea-ice visualization                      |
| `TimeSeriesPlotter`  | Time-series and seasonal visualization             |
| `update_pipeline.py` | Incremental workflow orchestration                 |
| `build_pages.py`     | Static website build                               |

The main command-line entry point is:

```text
src/main.py
```

---

## Project Structure

The repository is organized into source code, scientific data products, tests, documentation, and generated deployment artifacts.

```text
hudson_bay_sea_ice/
│
├── data/
│   └── geotiff/
│       └── <year>/<month>/
│
├── output/
│   ├── analysis/
│   ├── reference/
│   └── plots/
│
├── src/
│   ├── analysis/
│   ├── config/
│   ├── data_download/
│   ├── update/
│   └── visualization/
│
├── tests/
│
├── docs/
│   ├── requirements/
│   ├── architecture/
│   ├── methodology/
│   └── development/
│
├── build/
│
├── requirements.txt
└── ...
```

### `data/`

Temporary processing input, primarily downloaded GeoTIFF observations.

These files are not part of the website deployment artifact.

### `output/analysis/`

Persistent scientific results.

The main outputs include:

```text
ice_coverage_summary.csv
ice_coverage_timeseries.csv
ice_coverage_yearly.csv
ice_coverage_events.csv
latest.json
```

### `output/reference/`

Reusable spatial reference products such as region masks and reference metadata.

### `output/plots/`

Generated scientific visualization products.

### `src/`

Python implementation of the processing pipeline.

### `tests/`

Automated tests and test fixtures.

### `docs/`

Source files for the project website and detailed project documentation.

### `build/`

Generated GitHub Pages deployment artifact.

`build/` is generated and should not be treated as a second source tree.

---

## Website and Deployment

The project website is implemented as a static website.

The source is maintained under:

```text
docs/
```

Generated scientific results remain under:

```text
output/
```

The build process combines these inputs into:

```text
build/
```

Conceptually:

```text
docs/
   +
output/analysis/
   +
output/plots/
        │
        ▼
   build_pages.py
        │
        ▼
     build/
        │
        ▼
   GitHub Pages
```

This separation prevents generated scientific output from being duplicated inside the website source tree.

The website therefore acts as a presentation and documentation layer over the reproducible scientific processing pipeline.

---

## Automation

GitHub Actions provides the current automated operational environment.

The scheduled workflow:

1. installs the required Python environment,
2. executes the incremental update pipeline,
3. generates updated scientific outputs,
4. builds the website deployment artifact,
5. uploads the GitHub Pages artifact,
6. and commits updated persistent analysis output.

The workflow can also be triggered manually.

The production workflow is intentionally separated from the future CI quality-gate system. Operational execution demonstrates that the pipeline can run automatically, while systematic automated verification is being developed separately.

---

## Reproducibility

The project is designed around explicit inputs, configuration, source code, and generated products.

Reproducibility is supported by:

* version-controlled source code,
* documented scientific methodology,
* explicit configuration,
* fixed spatial reference data,
* persistent analysis results,
* documented processing stages,
* a defined Python environment,
* and regenerable visualization products.

Complete dependency and version traceability is not yet fully formalized in v0.1.

The project therefore distinguishes between the current reproducibility baseline and future improvements to formal verification and dependency traceability.

---

## Testing and Quality Assurance

Testing is an integral part of the project development strategy.

The defined test model contains:

1. unit tests,
2. component tests,
3. integration tests,
4. end-to-end tests,
5. regression tests.

Particular emphasis is placed on scientifically critical components such as:

* `RegionAnalyzer`,
* `TimeSeriesAnalyzer`,
* `ResultsManager`,
* `ReferenceBuilder`,
* and incremental update processing.

Scientific tests are expected to use controlled inputs and explicitly defined expected results wherever practical.

Important edge cases include:

* threshold boundaries,
* seasonal boundaries,
* leap years,
* missing observations,
* interpolation limits,
* incomplete years,
* invalid raster values,
* and incremental updates.

An initial project-wide line-coverage target of **70%** is defined.

This is a v0.1 quality target rather than a statement that the complete project currently satisfies the threshold.

Likewise, the documented CI quality-gate model represents the intended quality infrastructure; systematic mandatory coverage, static-analysis, and output-validation gates are part of the subsequent quality-assurance development.

---

## Requirements and Documentation

The project documentation is organized around several complementary views of the system.

### Requirements

* project scope,
* functional requirements,
* non-functional requirements,
* requirements traceability.

### Architecture

* architecture overview,
* component responsibilities,
* data flow.

### Methodology

* coverage metrics,
* data and inputs,
* spatial processing,
* temporal analysis,
* event detection.

### Development and Testing

* test strategy,
* test levels,
* test coverage,
* CI quality gates.

The documentation distinguishes between:

```text
implemented
partially verified
verified
planned
```

This distinction is particularly important for a scientific project where implemented functionality and systematically verified functionality are not necessarily equivalent.

---

## Current Scope

The current system focuses on quantitative analysis of daily sea-ice concentration and derived coverage indicators.

The following are intentionally outside the current v0.1 scope:

* sea-ice thickness,
* sea-ice volume,
* physical sea-ice modelling,
* future sea-ice prediction,
* interactive region selection,
* arbitrary user-defined analysis regions,
* surface-current analysis,
* real-time streaming processing,
* interactive web applications,
* and integration of additional scientific datasets into the automated production workflow.

Potential future extensions include higher-resolution data products, additional environmental variables, expanded anomaly analysis, interactive exploration, and additional scientific indicators.

---

## Limitations

The current implementation has several methodological and engineering limitations that are documented explicitly rather than hidden behind the generated results.

In particular:

* the regional denominator is based on a fixed reference water mask,
* the configured pixel area is a nominal calculation assumption,
* partial-pixel spatial intersections are not used,
* temporal interpolation is limited to defined gaps,
* annual statistics require complete calendar years,
* the climatology uses the fixed 1981–2010 reference period,
* the current quality infrastructure does not yet provide complete systematic verification of all requirements,
* and full dependency/version traceability is not yet formalized.

These limitations are part of the v0.1 documentation baseline and can be addressed through future, explicitly documented changes.

---

## Future Development

Potential extensions include:

* expanded automated test coverage,
* systematic CI quality gates,
* automated output validation,
* additional scientific indicators,
* higher-resolution sea-ice products,
* sea-ice thickness and volume,
* additional spatial regions,
* interactive regional analysis,
* additional environmental or oceanographic variables,
* and extended climatological and anomaly analysis.

Future functionality should be introduced through corresponding requirements, methodological documentation, implementation changes, and appropriate verification.

---

## Technology

The project is implemented in Python.

The main technology areas include:

* Python 3.12
* NumPy
* Pandas
* Rasterio
* GeoPandas
* PyProj
* Matplotlib
* Cartopy
* SciPy
* pytest

The exact dependency versions are maintained in:

```text
requirements.txt
```

The project uses GitHub Actions for automated operational execution and GitHub Pages for static website deployment.

---

## Getting Started

Create and activate a Python environment and install the project dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The main command-line interface is:

```bash
python src/main.py
```

The available processing stages are:

```text
download
process
plots
build
update
all
```

For example:

```bash
python src/main.py download
python src/main.py process
python src/main.py plots
python src/main.py build
```

The incremental production workflow is:

```bash
python src/main.py update
```

The exact command-line options are documented in the source code and project documentation.

---

## Local Website Preview

The generated website can be previewed locally from the project root.

After building the website:

```bash
python src/main.py build
```

start a local HTTP server from the repository root:

```bash
python -m http.server 8000
```

The generated `build/` directory can then be used as the static deployment artifact.

---

## Project Status

**Version: v0.1**

The v0.1 baseline represents a functioning automated scientific processing pipeline with:

* automated data acquisition,
* incremental processing,
* persistent regional analysis,
* temporal and climatological analysis,
* threshold-based seasonal analysis,
* scientific visualization,
* automated website generation,
* GitHub Actions execution,
* and GitHub Pages deployment.

The v0.1 release also establishes the project's formal requirements, architecture, methodology, and testing documentation.

The next development stage focuses primarily on strengthening systematic verification, test coverage, CI quality gates, output validation, and additional scientific functionality.

---

## License and Data Sources

The project processes sea-ice concentration data provided through the NSIDC/NOAA data infrastructure.

The scientific data products remain subject to the terms and attribution requirements of their respective providers.

Project-specific source code, documentation, configuration, and generated products are maintained separately from the external source datasets.

---

## Documentation

For detailed information, see the project documentation in `docs/`.

In particular:

```text
docs/
├── requirements/
│   ├── scope.md
│   ├── functional-requirements.md
│   ├── non-functional-requirements.md
│   └── requirements-traceability.md
│
├── architecture/
│   ├── overview.md
│   ├── components.md
│   └── data-flow.md
│
├── methodology/
│   ├── coverage-metrics.md
│   ├── data-and-inputs.md
│   ├── spatial-processing.md
│   ├── temporal-analysis.md
│   └── event-detection.md
│
└── development/
    └── tests/
        ├── test-strategy.md
        ├── test-levels.md
        ├── test-coverage.md
        └── ci-quality-gates.md
```

The README provides the project-level overview; the detailed documentation should be consulted for the exact scientific definitions, architectural responsibilities, requirements, and verification strategy.
