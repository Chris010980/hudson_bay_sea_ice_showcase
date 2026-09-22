# Spatial Processing

## Purpose

This document describes how the daily NSIDC sea ice concentration raster is spatially processed to obtain observations for the predefined Hudson Bay analysis regions.

The current implementation uses reusable raster masks so that the geographic definition of each region remains independent from the daily observation data.

---

## Spatial Processing Workflow

The spatial processing follows the general sequence:

```text
GeoTIFF
   ↓
Raster geometry
   ↓
Region geometry
   ↓
Raster region mask
   ↓
Valid analysis pixels
   ↓
Regional sea ice statistics
```

The reference information required for this process is prepared separately and reused for subsequent observations.

---

## Raster Grid

The input observations are provided on a regular polar stereographic grid.

The current implementation assumes:

* CRS: EPSG:3411
* nominal grid spacing: 25 km
* nominal pixel area: 625 km²

The spatial grid provides the common coordinate system for all daily observations.

---

## Analysis Region Definition

Each analysis region is defined by a geographic polygon.

The current configured regions are:

* Hudson Bay Area
* Hudson Bay
* Foxe Basin
* Gulf of Boothia
* Hudson Strait

The polygons are stored separately from the analysis algorithms.

This allows the geographic definition of a region to be changed without modifying the daily statistical calculation itself.

---

## Region Mask Generation

The reference preparation converts each configured polygon into a raster mask corresponding to the NSIDC grid.

The resulting mask identifies the pixels that belong to the respective analysis region.

Conceptually:

```text
Region polygon
      ↓
transform to raster coordinate system
      ↓
rasterize polygon
      ↓
boolean pixel mask
```

The masks are stored in:

```text
output/reference/filters/
```

and reused during daily analysis.

This avoids repeating the polygon-to-raster conversion for every observation.

---

## Reference Preparation

The `ReferenceBuilder` is responsible for preparing the spatial reference information.

The reference preparation includes:

1. loading the reference GeoTIFF;
2. determining the relevant raster geometry;
3. loading the configured analysis regions;
4. transforming the region geometries to the required coordinate system;
5. constructing the corresponding raster masks;
6. identifying the valid water pixels;
7. storing the reusable masks and reference metadata.

The resulting reference information is used by the regional analysis component.

---

## Valid Analysis Pixels

The regional analysis requires a stable definition of the pixels that represent the relevant water area.

Special NSIDC classification values such as land, coast, pole hole and missing data are not interpreted as sea ice concentration.

The reference information therefore provides the spatial basis for distinguishing pixels that can contribute to regional statistics from pixels that must be excluded.

The exact interpretation of valid pixels is part of the regional coverage methodology described in `coverage-metrics.md`.

---

## Daily Regional Processing

For each daily GeoTIFF:

1. the raster is loaded;
2. the sea ice concentration values are converted to physical concentration values;
3. the corresponding region mask is applied;
4. invalid or unavailable pixels are excluded;
5. the remaining regional pixels are passed to the coverage calculation.

The daily spatial processing does not regenerate the region polygons or masks.

---

## Separation of Spatial and Temporal Analysis

Spatial processing produces daily regional observations.

Temporal processing is performed subsequently on the resulting regional time series.

This separation allows the spatial calculation to remain independent from:

* interpolation;
* moving averages;
* climatology;
* anomaly calculations;
* annual statistics;
* seasonal event detection.

The conceptual data flow is therefore:

```text
Daily GeoTIFF
      ↓
Spatial processing
      ↓
Daily regional statistics
      ↓
Temporal analysis
```

---

## Reference Consistency

The same reference definition is intended to be used for all observations in the historical time series.

This ensures that changes in the resulting regional time series reflect changes in the observations rather than repeated changes in the underlying spatial mask.

Reference data are therefore treated as persistent analysis inputs rather than regenerated as part of every daily observation.

---

## Limitations

The current implementation assumes a fixed spatial grid and a fixed set of analysis regions.

Future extensions may introduce:

* additional regions;
* alternative spatial resolutions;
* additional sea ice products;
* alternative spatial weighting or area calculations.

Such extensions are outside the current methodology.
