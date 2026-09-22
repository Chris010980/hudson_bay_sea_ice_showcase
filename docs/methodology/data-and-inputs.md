# Data and Inputs

## Purpose

This document describes the input data used by the Hudson Bay Sea Ice Analysis pipeline and the interpretation of the sea ice concentration product before spatial and temporal analysis.

The project uses daily passive microwave sea ice concentration observations provided by the National Snow and Ice Data Center (NSIDC). The original observations are distributed as GeoTIFF raster products and form the basis for all derived regional statistics.

The methodology described here refers to the current implementation of the project.

---

## Sea Ice Concentration Dataset

The analysis is based on the NOAA / NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration.

The dataset provides daily gridded sea ice concentration observations covering the historical satellite record.

The current processing pipeline uses the GeoTIFF representation of the product.

### Main characteristics

| Property                   | Current implementation         |
| -------------------------- | ------------------------------ |
| Data source                | NOAA / NSIDC                   |
| Data type                  | Daily sea ice concentration    |
| Format                     | GeoTIFF                        |
| Spatial reference          | Polar Stereographic, EPSG:3411 |
| Nominal spatial resolution | 25 km × 25 km                  |
| Pixel area                 | 625 km²                        |
| Temporal coverage          | Historical record to present   |

The precise product version and file naming convention are handled by the data acquisition component.

---

## Raster Representation

Each GeoTIFF contains sea ice concentration values encoded as scaled integer values.

For valid concentration pixels, the stored value is converted to a fractional concentration:

```text
concentration = stored_value / 1000
```

Consequently, the physical concentration range represented by valid values is:

```text
0.0 ≤ concentration ≤ 1.0
```

or, expressed as a percentage:

```text
0 % ≤ concentration ≤ 100 %
```

The conversion is performed before regional statistics are calculated.

---

## Special Classification Values

The NSIDC product uses values outside the physical concentration range for special classifications.

The current implementation distinguishes the following values:

| Value | Interpretation |
| ----: | -------------- |
|  2510 | Pole hole      |
|  2530 | Coast          |
|  2540 | Land           |
|  2550 | Missing data   |

These values must not be interpreted as physical sea ice concentration.

The processing pipeline therefore identifies values above the valid concentration range and excludes them from numerical concentration calculations.

---

## Invalid and Missing Observations

Pixels classified as land, coast, pole hole or missing data are not treated as observations of sea ice concentration.

The distinction between different special-value classes is relevant during preprocessing and reference-mask construction, because the analysis requires a defined set of valid water pixels for each region.

Missing observations are also relevant at the temporal-analysis level. A missing daily regional observation is not automatically interpreted as zero ice coverage.

The subsequent temporal processing defines explicitly how gaps in the regional time series are handled.

---

## Spatial Reference

The current implementation uses the NSIDC polar stereographic grid represented by EPSG:3411.

The raster geometry and the predefined analysis regions must be spatially compatible so that each region can be converted into a raster mask.

The spatial reference is therefore part of the methodological definition of the analysis and not merely a plotting parameter.

---

## Analysis Regions

The project does not analyse the complete raster indiscriminately. Instead, predefined geographic regions are used to extract regional sea ice statistics.

The current configuration contains:

* Hudson Bay Area
* Hudson Bay
* Foxe Basin
* Gulf of Boothia
* Hudson Strait

The regions are defined independently from the analysis code and are converted into raster masks during reference preparation.

---

## Reference Data

A reference GeoTIFF is used to construct the spatial reference information required for regional processing.

The reference preparation identifies the relevant raster pixels for each configured region and stores reusable masks under:

```text
output/reference/
```

The resulting masks allow subsequent daily observations to be processed against a fixed spatial definition.

Reference preparation is therefore separated from daily observation processing.

---

## Input Data Lifecycle

Raw GeoTIFF observations are treated as temporary processing inputs.

The current pipeline follows the general sequence:

```text
NSIDC archive
      ↓
downloaded GeoTIFF
      ↓
temporary local data
      ↓
regional analysis
      ↓
persistent derived results
      ↓
temporary GeoTIFF may be removed
```

The historical dataset maintained by the project consists of derived regional statistics rather than a permanent local copy of every downloaded GeoTIFF.

The downloader provides an option to retain the downloaded files when required.

---

## Methodological Scope

This document describes the interpretation of the input product. It does not define:

* the calculation of absolute and relative coverage;
* temporal interpolation;
* climatological statistics;
* anomalies;
* annual statistics;
* break-up and freeze-up detection;
* visualization methods.

These aspects are described in the corresponding methodology documents.
