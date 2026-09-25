# Spatial Processing

## 1. Purpose

This document describes how the `hudson_bay_sea_ice` pipeline converts the configured geographic regions into reusable raster masks and applies those masks to daily sea-ice concentration observations.

The central design principle is that the spatial reference is prepared once and reused during daily processing.

---

## 2. Reference-Based Processing

The spatial workflow consists of two principal stages:

```text
Reference preparation
        ↓
Reusable regional masks
        ↓
Daily raster analysis
```

The polygon geometry is therefore not evaluated against every daily raster independently.

Instead, the reference-processing stage creates persistent masks describing which raster cells belong to each configured analysis region.

---

## 3. Spatial Reference Grid

The fixed reference raster is:

```text
src/config/reference.tif
```

It establishes the raster grid used for regional analysis.

The regional masks generated from this grid are stored below:

```text
output/reference/
```

The same reference grid is subsequently assumed for daily sea-ice concentration observations.

---

## 4. Coordinate Transformation

The raster reference grid is processed in the configured NSIDC polar stereographic CRS:

```text
EPSG:3411
```

Region geometries are transformed from geographic coordinates to the raster coordinate system using a coordinate transformation based on `pyproj`.

The transformation is performed explicitly using the configured coordinate reference systems.

Longitude values represented in a 0–360° system are normalized to the -180–180° representation where required.

---

## 5. Pixel-Center Representation

The current reference implementation evaluates the position of raster-cell centers relative to the configured region polygons.

The relevant pixel-center coordinates are transformed into geographic coordinates for the polygon test.

The polygon membership test uses:

```text
matplotlib.path.Path.contains_points()
```

A raster cell is therefore classified according to whether its center lies inside the region geometry.

---

## 6. Raster Mask Generation

For each configured region, the reference-processing stage determines:

1. the raster pixels whose centers fall within the region polygon,
2. the subset corresponding to valid water pixels,
3. the number of selected pixels,
4. the corresponding reference water area.

The resulting masks are stored as reusable flattened raster indices.

A typical mask has the form:

```text
output/reference/filters/<region>_water.npy
```

The use of flattened indices allows the daily analyzer to access only the relevant raster values.

---

## 7. Daily Mask Application

For a daily GeoTIFF, the `RegionAnalyzer` loads the corresponding regional water mask and extracts the selected raster values.

Conceptually, the operation is:

```text
daily raster
     ↓
flatten raster
     ↓
apply stored water-pixel indices
     ↓
regional concentration values
```

This avoids repeating the polygon-to-raster conversion for every daily observation.

---

## 8. Validity Checks

After applying a regional mask, the daily analyzer checks the selected values before calculating the regional statistics.

In particular:

* missing value `2550` within the selected region causes the region/day to be rejected;
* the number of valid selected water pixels must agree with the reference configuration.

This ensures that the daily observation is evaluated against the same spatial denominator as the reference dataset.

---

## 9. Pixel Classification

The current regional analysis uses the concentration values of the selected water pixels.

The configured pixel-level detection threshold is:

```text
15 %
```

or:

```text
150
```

on the original 0–1000 concentration scale.

Pixels below this threshold do not contribute to the binary absolute ice area.

Pixels at or above this threshold contribute their complete configured pixel area to the absolute ice area.

Their fractional concentration is additionally used for the relative ice-area calculation.

---

## 10. Polygon Boundary Treatment

The current implementation uses pixel-center inclusion.

It does not calculate the exact geometrical intersection between a raster cell and a polygon boundary.

Consequently, a boundary pixel is either fully included or fully excluded.

No fractional boundary weighting is applied.

This is an explicit characteristic of the v0.1 raster-mask methodology.

---

## 11. Reference Area Validation

The reference-processing stage calculates regional spatial quantities that can be compared with an independent geographic reference.

Natural Earth water/ocean geometry is used for this purpose.

For the comparison, the relevant geometries are transformed to an equal-area projection:

```text
EPSG:6933
```

and their areas are calculated in square kilometres.

The resulting Natural Earth area is used as a plausibility reference.

It does not replace the operational raster-based water mask.

---

## 12. Fixed Spatial Denominator

The operational analysis uses a fixed reference water area.

The daily water area is therefore not dynamically reconstructed from the individual sea-ice raster.

This provides a consistent denominator across the historical time series but also means that changes in the effective coastline or water mask are not represented dynamically.

---

## 13. Spatial Outputs

The reference-processing stage produces reusable spatial products below:

```text
output/reference/
```

These include regional masks and reference metadata required by the daily analyzer.

The daily analysis results are stored separately below:

```text
output/analysis/
```

This separation distinguishes spatial reference products from observation-specific analytical results.

---

## 14. Current Limitations

The v0.1 spatial methodology does not currently include:

* partial-pixel polygon intersection,
* dynamic water masks,
* dynamic coastline information,
* spatial uncertainty propagation,
* area weighting beyond the fixed 625 km² pixel assumption,
* arbitrary user-defined regions at runtime.

The method is therefore intentionally based on a fixed raster reference and reusable binary spatial masks.
