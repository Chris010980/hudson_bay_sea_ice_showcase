# Spatial Processing

## Purpose

This document describes how the raster data are spatially assigned to the predefined analysis regions and how the reference water areas are established.

The methodology reflects the current implementation of v0.1.

---

## 1. Spatial analysis concept

The daily sea-ice concentration data are provided on a regular raster grid.

The project does not dynamically rasterize the region polygons for every daily observation. Instead, a dedicated reference processing step creates reusable pixel masks for each analysis region.

The resulting masks are subsequently applied to every daily GeoTIFF.

The workflow is therefore:

```text
Reference GeoTIFF
       ↓
Region polygons
       ↓
Pixel-center coordinates
       ↓
Point-in-polygon test
       ↓
Water-pixel mask
       ↓
Reusable region mask
       ↓
Daily GeoTIFF analysis
```

This separates the spatial definition of the analysis regions from the processing of individual observations.

---

## 2. Coordinate transformation

The reference raster is assumed to use:

```text
EPSG:3411
```

For every raster cell, the center coordinate is calculated from the raster transform.

The raster coordinates are then transformed to geographic coordinates:

```text
EPSG:3411 → EPSG:4326
```

The transformation uses `pyproj.Transformer` with `always_xy=True`.

The resulting longitude/latitude coordinates are used for comparison with the region polygons.

---

## 3. Region polygons

The region definitions are stored in:

```text
src/config/regions.json
```

Each region contains a polygon defined by geographic coordinates.

Before the polygons are used, longitudes greater than 180° are converted to the corresponding negative longitude:

```python
coords[:, 0] = np.where(
    coords[:, 0] > 180,
    coords[:, 0] - 360,
    coords[:, 0],
)
```

This converts a possible 0–360° longitude convention to the −180–180° convention used by the geographic coordinates generated from the raster.

---

## 4. Pixel-center point-in-polygon method

The current implementation assigns raster cells to a region based on the location of their center point.

For every raster cell:

1. calculate the cell center,
2. transform the center to longitude/latitude,
3. test whether the point lies inside the region polygon.

The implementation uses:

```python
matplotlib.path.Path.contains_points()
```

The method therefore represents a **pixel-center point-in-polygon classification**.

It is not equivalent to a polygon rasterization or an area-weighted intersection between raster cells and polygons.

Consequently, a pixel is either included or excluded as a complete 625 km² cell.

Partial pixel coverage at polygon boundaries is not represented.

---

## 5. Region mask construction

For every region, the polygon mask is first generated from the pixel-center test.

The number of pixels inside the polygon is recorded as:

```text
polygon_pixels
```

The polygon mask is then combined with the valid-water condition:

```text
0 <= concentration <= 1000
```

This produces the water mask used for the regional analysis.

The resulting number of valid reference water pixels is recorded as:

```text
water_pixels
```

---

## 6. Fixed pixel area

Each valid raster cell is assigned an area of:

```text
625 km²
```

The reference water area is therefore calculated as:

```text
water_pixels × 625 km²
```

This value is stored as:

```text
water_area_pixel_km2
```

and is subsequently used as the fixed denominator for daily regional coverage calculations.

The daily denominator is therefore not recalculated from each individual observation.

---

## 7. Persistent reference masks

The generated masks are stored as NumPy arrays:

```text
output/reference/filters/
```

Each region receives a file of the form:

```text
<region>_water.npy
```

The stored values are flattened raster indices.

For a daily observation, these indices can therefore be applied directly to the flattened raster:

```python
values = self.band.flat[indices]
```

This avoids repeating the geometric region calculation for every daily observation.

---

## 8. Reference summary

The reference-processing stage writes:

```text
output/reference/reference_summary.json
```

For each region, the summary contains values including:

* polygon pixel count,
* water pixel count,
* pixel area,
* reference water area,
* Natural Earth water area,
* absolute area difference,
* relative area difference.

The summary is subsequently loaded by `RegionAnalyzer`.

---

## 9. Natural Earth comparison

An independent water-area comparison is performed using Natural Earth ocean geometry.

For each region, the region polygon is intersected with the Natural Earth ocean dataset.

The resulting geometry is transformed to:

```text
EPSG:6933
```

and its area is calculated in square kilometres.

This value is stored as:

```text
naturalearth_water_area_km2
```

The difference between the raster-derived reference area and the Natural Earth area is also stored.

The Natural Earth result is therefore a reference comparison rather than the source of the operational daily water mask.

---

## 10. Daily application of the masks

During daily analysis, `RegionAnalyzer` loads the reference mask for each region and extracts the corresponding raster values.

For example:

```python
indices = np.load(
    self.filter_dir / f"{region_name}_water.npy"
)

values = self.band.flat[indices]
```

The daily values are then checked against the reference expectations.

A region/day is rejected if:

* one or more selected pixels contains `2550`, or
* the number of valid water pixels differs from the reference water-pixel count.

This ensures that the daily calculation is performed only when the expected spatial set of valid water pixels is available.

---

## 11. Spatial consistency

The reference masks establish a fixed spatial basis for the entire time series.

This has two important consequences:

### Fixed spatial domain

The same raster cells are used for a region on every day.

### Fixed reference denominator

The same reference water area is used as the denominator for daily coverage.

Consequently, temporal changes in the resulting coverage values represent changes in the sea-ice concentration of the predefined spatial domain rather than changes in the spatial definition of the region.

---

## 12. Current methodological limitations

The current implementation has several documented characteristics that should be considered when interpreting the results:

* the raster CRS is assumed to be EPSG:3411 rather than read dynamically from the file;
* region assignment is based on pixel centers;
* boundary pixels are not area-weighted;
* every included pixel contributes its full 625 km²;
* the reference mask is based on one reference GeoTIFF;
* reference-mask consistency is checked by expected pixel count, but the source raster/grid identity is not comprehensively validated.

These are methodological and implementation characteristics of v0.1. They should not be interpreted as evidence that the pipeline is untested; the pipeline has been operationally exercised and its outputs have been inspected during development.

More systematic validation of these assumptions is planned for v0.2.

---

## 13. Scope of this methodology

This document defines the spatial processing required to establish and apply the regional masks.

It does not define:

* sea-ice coverage metrics,
* temporal interpolation,
* climatology,
* anomaly calculation,
* annual statistics,
* seasonal threshold events.

These are described in the corresponding methodology documents.
