# Data Flow

## Overview

The project processes daily sea-ice concentration observations through several stages.

The primary data flow is:

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

Spatial reference data is prepared separately:

```text
Reference GeoTIFF
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

The generated results are subsequently combined with the static website:

```text
docs/
   │
   ├──────────────┐
   │              │
   ▼              ▼
output/       build_pages
                  │
                  ▼
               build/
                  │
                  ▼
            GitHub Pages
```

## 1. Data Acquisition

The `NSIDCDownloader` accesses the NSIDC archive and compares available observations with locally available files.

Missing observations are downloaded to:

```text
data/geotiff/<year>/<month>/
```

The raw GeoTIFF files are temporary processing inputs.

## 2. Spatial Reference Preparation

Before processing daily observations, `ReferenceBuilder.ensure_reference()` ensures that the static spatial reference data exists.

The reference data contains:

* spatial masks for the analysis regions,
* reference metadata,
* expected regional pixel information.

The resulting files are stored under:

```text
output/reference/
```

## 3. Daily Spatial Analysis

Each downloaded GeoTIFF is processed by `RegionAnalyzer`.

The analyzer:

1. extracts the observation date,
2. loads the raster data,
3. applies the reference masks,
4. handles invalid and missing values,
5. determines sea-ice coverage,
6. calculates regional statistics.

The results are passed to `ResultsManager`.

## 4. Persistent Daily Results

`ResultsManager` stores the daily regional results in:

```text
output/analysis/ice_coverage_summary.csv
```

The dataset is deduplicated by date and region and sorted chronologically.

`latest.json` provides metadata about the most recent processed observation.

## 5. Temporal Analysis

`TimeSeriesAnalyzer` uses the persistent daily result dataset as its input.

The analysis pipeline is:

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

The threshold analysis uses:

```text
10 %
50 %
90 %
```

and determines break-up and freeze-up events subject to the defined seasonal, continuity and persistence conditions.

## 6. Derived Analysis Products

The temporal analysis produces:

```text
output/analysis/
├── ice_coverage_timeseries.csv
├── ice_coverage_yearly.csv
└── ice_coverage_events.csv
```

These files provide the data used by the time-series visualization layer.

## 7. Visualization

Two visualization paths currently exist.

### Spatial visualization

`SeaIcePlotter` uses a GeoTIFF observation to create:

* overview maps,
* maps with analysis regions,
* individual region maps.

### Temporal visualization

`TimeSeriesPlotter` uses the derived CSV datasets to create:

* time-series plots,
* anomaly plots,
* threshold-duration plots,
* polar seasonal plots,
* yearly mean plots.

The generated figures are stored under:

```text
output/plots/
```

## 8. Website Build

The website source is maintained under:

```text
docs/
```

The generated analysis results are maintained under:

```text
output/
```

`build_pages.py` combines both into:

```text
build/
```

The build directory is therefore a deployment artifact rather than the primary source of the website.

## 9. Incremental Update Flow

The automated update pipeline uses the latest processed date to determine the beginning of the next processing interval.

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

If no new data is downloaded, the update pipeline terminates without regenerating the downstream products.
