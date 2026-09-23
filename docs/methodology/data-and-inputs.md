# Data and Inputs

## Purpose

This document describes the input data used by the Hudson Bay Sea Ice Analysis pipeline and the handling of input data before spatial and temporal analysis.

The project uses daily sea-ice concentration GeoTIFF files as its primary observational input. In addition, a dedicated reference GeoTIFF and predefined geographic region polygons are used to establish the spatial basis for the regional analysis.

The methodology described here reflects the current implementation of v0.1.

---

## 1. Primary observational data

The primary input consists of daily sea-ice concentration GeoTIFF files.

The files are obtained from the NSIDC/NOAA data source and contain sea-ice concentration on a regular raster grid.

Each raster cell represents an area of:
**625 km²**
corresponding to the 25 km × 25 km spatial resolution used by the product.

The daily files are treated as independent observations. The processing pipeline determines which observations are available and processes only newly available data during incremental updates.

---

## 2. Sea-ice concentration encoding

Sea-ice concentration values are stored as integer values on a scale from 0 to 1000 for valid concentration measurements.

The concentration is interpreted as:

|        Stored value | Interpretation                                            |
| ------------------: | --------------------------------------------------------- |
|                 `0` | 0% sea-ice concentration                                  |
|              `1000` | 100% sea-ice concentration                                |
|            `0–1000` | valid concentration range                                 |
|              `2550` | missing data                                              |
| values above `1000` | non-water / special values and excluded from the analysis |

The analysis therefore treats values in the interval

`0 <= concentration <= 1000`

as valid water-related concentration values.

Values above `1000` are not included in the regional coverage calculations.

---

## 3. Missing data

The value `2550` is explicitly treated as a missing-data marker.

Missing data are handled differently during reference generation and daily analysis.

### Reference data

The reference GeoTIFF must not contain any `2550` values.

If missing pixels are detected anywhere in the reference raster, reference generation is aborted.

This ensures that the reference masks are generated from a spatially complete reference raster.

The reference GeoTIFF is not selected as part of each processing run.
It is a fixed project-level reference dataset selected during initial
project setup and subsequently stored under src/config/reference.tif.

### Daily observations

For daily regional analysis, the predefined reference masks identify the pixels belonging to each region.

If any of these pixels contains the missing-data value `2550`, the corresponding region/day is not included in the analysis.

The region is skipped rather than replacing the missing value by an estimate.

This preserves the distinction between an unavailable observation and an observed concentration value.

---

## 4. Reference GeoTIFF

A dedicated GeoTIFF is used as the spatial reference for the regional analysis:

```text
src/config/reference.tif
```

The reference raster is used to:

* establish the spatial grid,
* identify valid water pixels,
* construct the region masks,
* determine the fixed reference water area of each region.

The reference raster is therefore part of the methodological definition of the regional analysis rather than merely an auxiliary visualization input.

---

## 5. Region definitions

The analysis regions are defined in:

```text
src/config/regions.json
```

The current regions are:

* Hudson Bay
* Gulf of Boothia
* Foxe Basin
* Hudson Strait
* overall analysis region

Region polygons are provided as geographic coordinates.

The input coordinates may use a longitude convention in which longitudes exceed 180°. During reference generation, longitudes greater than 180° are converted to the corresponding range between −180° and +180°.

For example:

```text
longitude > 180°
        ↓
longitude - 360°
```

This conversion provides a consistent coordinate convention for the spatial analysis.

---

## 6. Coordinate reference systems

The current implementation assumes the raster grid uses:

```text
EPSG:3411
```

This CRS is used when transforming raster pixel-center coordinates to geographic coordinates for region assignment.

The region polygons themselves are interpreted as:

```text
EPSG:4326
```

The current implementation uses these CRS definitions explicitly rather than deriving them dynamically from the GeoTIFF metadata.

---

## 7. Reference water area

For each analysis region, the reference processing determines the number of valid water pixels.

The water mask is defined by:

```text
0 <= concentration <= 1000
```

The resulting number of water pixels is multiplied by the fixed pixel area:

```text
625 km²
```

This produces the reference water area used as the denominator for subsequent daily coverage calculations.

The reference summary is stored in:

```text
output/reference/reference_summary.json
```

The summary contains, among other values:

* number of polygon pixels,
* number of reference water pixels,
* pixel area,
* reference water area,
* Natural Earth water-area comparison,
* absolute and relative area differences.

---

## 8. Spatial reference validation

The reference water area is additionally compared with a water-area estimate derived from Natural Earth ocean data.

Natural Earth is used only for this reference comparison.

It does **not** define the daily analysis masks or daily sea-ice coverage.

The comparison provides an independent spatial plausibility check on the reference area represented by the raster grid.

The comparison values are stored in `reference_summary.json`.

---

## 9. Incremental input processing

The daily update pipeline does not require all historical GeoTIFF files to remain permanently available.

The GeoTIFF observations can be treated as temporary processing inputs.

The persistent analytical state is represented by the generated result files, including:

```text
output/analysis/ice_coverage_summary.csv
```

During an update, the pipeline determines the latest processed observation and processes subsequent available observations.

This allows the historical analysis to be extended without reprocessing the complete input archive during every update.

---

## 10. Methodological assumptions

The current implementation relies on the following assumptions:

1. Daily input GeoTIFFs use the expected spatial grid.
2. The raster grid is compatible with the reference masks.
3. The raster encoding uses the documented concentration and special-value scheme.
4. The reference raster is spatially complete.
5. Each analysis region can be represented by its predefined polygon.
6. Each valid reference water pixel represents 625 km².
7. The fixed reference water area is an appropriate denominator for the regional coverage metrics.

These assumptions are currently enforced partly through implementation checks and partly through the structure of the processing pipeline.

Systematic automated validation of all assumptions is part of the planned quality-assurance work for v0.2.

---

## 11. Outputs relevant to subsequent analysis

The spatial processing stage produces persistent regional observations containing:

* observation date,
* region,
* reference water-pixel count,
* reference water area,
* absolute ice area,
* relative ice area,
* absolute coverage,
* relative coverage,
* missing-pixel status.

These results form the input to the subsequent temporal analysis.

---

## 12. Scope of this methodology

This document describes the input data and their interpretation within the current pipeline.

It does not define:

* the spatial polygon-to-raster procedure,
* the detailed coverage metrics,
* temporal interpolation,
* climatology,
* anomaly calculation,
* threshold-event detection.

These topics are described in the corresponding methodology documents.
