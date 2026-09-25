# Coverage Metrics

## 1. Purpose

This document defines the sea-ice coverage metrics calculated by the `hudson_bay_sea_ice` analysis pipeline.

The metrics are calculated independently for each configured spatial region and observation date. They distinguish between a binary, threshold-based ice coverage and a concentration-weighted ice coverage.

The current implementation uses the regional water area derived from a fixed spatial reference dataset as the denominator for the reported coverage percentages.

---

## 2. Input Concentration Values

The NSIDC sea-ice concentration product stores concentration values on a scaled integer representation.

The current implementation treats values in the range

```text
0–1000
```

as valid sea-ice concentration values.

The physical concentration is obtained by dividing the stored value by `1000`.

Values above `1000` represent special or non-concentration classifications and are not treated as valid concentration values during regional analysis.

The value

```text
2550
```

represents missing data.

If a missing value occurs within the selected reference water pixels of a daily observation, the corresponding region/day is rejected rather than being evaluated using a partially available water mask.

---

## 3. Pixel Detection Threshold

A water pixel is classified as ice-covered when its sea-ice concentration reaches the configured pixel detection threshold.

The current threshold is:

```text
150 / 1000 = 0.15 = 15 %
```

Thus:

```text
ice pixel = concentration >= 15 %
```

This threshold is used for the calculation of the binary absolute ice area.

It is distinct from the seasonal event thresholds of 10 %, 50 % and 90 %. The 15 % threshold is applied at pixel level, whereas the 10/50/90 % thresholds are applied to regional coverage time series.

---

## 4. Spatial Resolution and Pixel Area

The analysis uses a 25 km × 25 km raster grid.

For the current implementation, one raster cell is assigned an area of:

```text
625 km²
```

This fixed pixel area is used for all regional area calculations.

The implementation therefore assumes that a selected raster cell contributes its complete configured pixel area to the corresponding regional area.

No partial pixel-area weighting is currently applied at polygon boundaries.

---

## 5. Absolute Ice Area

The absolute ice area uses a binary classification of the water pixels.

For every selected water pixel:

* concentration below 15 % → `0 km²`
* concentration of at least 15 % → `625 km²`

The absolute ice area is therefore:

$$
A_{\mathrm{absolute}}
=
N_{\mathrm{ice}}
\cdot
625\ \mathrm{km^2}
$$

where \(N_{\mathrm{ice}}\) is the number of selected water pixels with a concentration of at least 15 %.

This metric represents the area of pixels classified as ice-covered according to the configured detection threshold.

---

## 6. Relative Ice Area

The relative ice area uses the measured sea-ice concentration as an area weighting factor.

For an individual pixel:

$$
A_{\mathrm{ice,pixel}}
=
\frac{C}{1000}
\cdot
625\ \mathrm{km^2}
$$

where \(C\) is the stored concentration value.

The regional relative ice area is therefore the sum of the concentration-weighted contributions of the selected water pixels.

In the current implementation, only pixels meeting the 15 % pixel detection threshold contribute to this calculation.

The metric therefore does not represent the arithmetic mean concentration over all water pixels. It represents a concentration-weighted ice-covered area based on the configured pixel classification.

---

## 7. Reference Water Area

The reference water area is derived from the fixed spatial reference dataset.

For each region:

$$
A_{\mathrm{water}}
=
N_{\mathrm{water}}
\cdot
625\ \mathrm{km^2}
$$

where \(N_{\mathrm{water}}\) is the number of water pixels contained in the reusable regional reference mask.

This denominator remains fixed for subsequent daily observations.

The daily processing additionally verifies that the number of valid selected water pixels agrees with the reference configuration.

---

## 8. Absolute Coverage

Absolute coverage is the fraction of the reference water area classified as ice-covered:

$$
\mathrm{Coverage}_{\mathrm{absolute}}
=
\frac{A_{\mathrm{absolute}}}
{A_{\mathrm{water}}}
\cdot 100
$$

The resulting value is reported as a percentage.

---

## 9. Relative Coverage

Relative coverage is calculated from the concentration-weighted ice area:

$$
\mathrm{Coverage}_{\mathrm{relative}}
=
\frac{A_{\mathrm{relative}}}
{A_{\mathrm{water}}}
\cdot 100
$$

The metric accounts for the fractional sea-ice concentration of the selected pixels rather than treating every detected pixel as completely ice-covered.

Under the current definitions, the relative coverage is expected to be less than or equal to the absolute coverage because the latter assigns the full pixel area to every pixel exceeding the 15 % detection threshold.

---

## 10. Quality Checks

Before a daily regional result is accepted, the current analysis performs consistency checks including:

* detection of missing values within the selected reference water pixels,
* comparison of the current valid water-pixel count with the reference water-pixel count.

If these checks fail, the corresponding regional observation is skipped.

The resulting dataset records the relevant area and coverage quantities together with the associated water-pixel information.

---

## 11. Stored Metrics

The persistent daily analysis contains the quantities required to reconstruct and interpret the coverage calculation, including:

```text
water_pixels
water_area_km2
absolute_ice_area_km2
relative_ice_area_km2
absolute_coverage_percent
relative_coverage_percent
missing_pixels
```

These values form the basis for the subsequent temporal analysis.

---

## 12. Distinction Between Thresholds

Three different concepts must be distinguished:

| Threshold        | Purpose                                     |
| ---------------- | ------------------------------------------- |
| 15 %             | Pixel-level ice detection                   |
| 10 %, 50 %, 90 % | Regional seasonal event detection           |
| 7 days           | Persistence requirement for seasonal events |

The thresholds therefore operate at different levels of the analysis and must not be interpreted interchangeably.

---

## 13. Current Limitations

The v0.1 implementation uses a fixed spatial representation and fixed reference water area.

It does not currently account for:

* partial pixel intersections at region boundaries,
* dynamically changing water areas,
* spatially varying pixel areas,
* uncertainty propagation,
* uncertainty in the underlying sea-ice concentration product.

The calculated metrics should therefore be interpreted as results of the defined raster-based methodology rather than as an exact geometrical reconstruction of the physical coastline or water area.
