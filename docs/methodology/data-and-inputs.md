# Data and Inputs

## 1. Purpose

This document describes the scientific input data, spatial reference data and configuration used by the `hudson_bay_sea_ice` analysis pipeline.

The current v0.1 implementation is based on daily sea-ice concentration GeoTIFF observations and a fixed spatial reference configuration.

---

## 2. Primary Scientific Dataset

The primary input consists of daily sea-ice concentration GeoTIFF products provided through the configured NSIDC/NOAA data archive.

The downloader accesses the remote archive and compares available observations with the locally available dataset.

The acquisition process supports:

* inspection of available remote observations,
* comparison with local files,
* incremental download of missing observations,
* recognition of equivalent product-version filenames,
* optional removal of temporary downloaded GeoTIFF files.

The downloaded GeoTIFF files are treated as processing inputs. They are not part of the persistent analytical result dataset.

---

## 3. Concentration Encoding

The current processing assumes the product encoding documented by the configured NSIDC dataset.

The principal concentration range is:

```text
0–1000
```

corresponding to:

```text
0–100 %
```

The current implementation uses the following special-value interpretation:

|  Value | Interpretation      |
| -----: | ------------------- |
| 0–1000 | Valid concentration |
|   2510 | Pole hole           |
|   2530 | Coast               |
|   2540 | Land                |
|   2550 | Missing data        |

Values above `1000` are excluded from numerical concentration processing.

The explicit special-value encoding is retained as part of the input-data assumptions rather than replacing it with generic `NaN` semantics at the source-data level.

---

## 4. Raster Characteristics

The current analysis operates on a 25 km sea-ice concentration raster grid.

The configured pixel area is:

```text
25 km × 25 km = 625 km²
```

The analysis uses the raster grid as the common spatial reference for the regional masks and daily observations.

---

## 5. Spatial Reference Dataset

A fixed reference GeoTIFF is stored at:

```text
src/config/reference.tif
```

This reference dataset provides the raster grid used to construct the persistent regional masks.

The reference processing identifies the spatial characteristics required for subsequent daily analysis and generates reusable reference products below:

```text
output/reference/
```

The reference configuration is therefore separated from the individual daily observations.

---

## 6. Regional Configuration

The spatial analysis regions are defined separately from the analysis implementation in:

```text
src/config/regions.json
```

The current configured regions are:

* Hudson Bay
* Gulf of Boothia
* Foxe Basin
* Hudson Strait
* Hudson Bay Area

The exact polygon definitions are maintained by the configuration rather than being embedded directly in the analysis code.

The regions are processed using the same raster reference grid.

Interactive region selection and arbitrary user-defined regions are not part of the v0.1 implementation.

---

## 7. Coordinate Reference Systems

The daily sea-ice raster is processed using the configured NSIDC polar stereographic coordinate system:

```text
EPSG:3411
```

Region geometries are represented in geographic coordinates and transformed to the raster coordinate system for spatial processing.

Longitude values supplied in the 0–360° representation are normalized to the conventional -180–180° range where required by the spatial processing.

The current implementation uses explicit CRS assumptions rather than dynamically deriving a new analysis projection for each observation.

---

## 8. Reference Water Area

The reference processing determines the water pixels belonging to each configured region.

For every region, the number of selected water pixels is stored together with the corresponding fixed area:

$$
A_{\mathrm{water}}
=
N_{\mathrm{water}}
\cdot
625\ \mathrm{km^2}
$$

The reference information is retained below:

```text
output/reference/
```

and can be reused for subsequent daily processing.

---

## 9. Reference Summary

The reference-processing stage generates summary information describing the spatial reference configuration.

The reference summary contains quantities such as:

* polygon pixel count,
* water-pixel count,
* configured pixel area,
* reference water area,
* comparison with Natural Earth water-area information,
* absolute area differences,
* relative area differences.

The Natural Earth comparison is used as an external plausibility check of the spatial reference definition.

Natural Earth is not used as the operational daily water mask.

---

## 10. Persistent and Temporary Data

The project distinguishes between temporary input data and persistent analytical products.

Temporary daily GeoTIFF files are stored under:

```text
data/geotiff/
```

Persistent analytical results are stored under:

```text
output/analysis/
```

Persistent spatial reference products are stored under:

```text
output/reference/
```

Generated visualizations are stored under:

```text
output/plots/
```

The raw GeoTIFF archive is therefore not required to reproduce the derived result files after successful processing, although retaining the raw inputs can be useful for inspection and debugging.

---

## 11. Input Assumptions

The v0.1 processing relies on the following assumptions:

* observations use the expected raster grid,
* concentration values follow the configured 0–1000 encoding,
* special values use the expected product codes,
* the raster uses the expected spatial reference,
* the configured polygons represent the intended analysis regions,
* the fixed pixel-area assumption is appropriate for the current analysis,
* the reference water mask remains applicable to subsequent observations.

These assumptions define the current processing contract.

---

## 12. Current Validation Scope

The current implementation contains processing-time consistency checks, particularly for the validity of selected regional water pixels.

A more comprehensive input-data validation layer covering all raster metadata and scientific assumptions is planned as a future quality expansion.

Therefore, v0.1 should be understood as an implementation with explicit input assumptions and selected validation checks, rather than as a fully formalized scientific data-validation framework.
