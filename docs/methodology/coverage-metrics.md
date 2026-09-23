# Coverage Metrics

## Purpose

This document defines the sea-ice coverage metrics calculated for each analysis region and observation date.

The current implementation distinguishes between absolute and relative sea-ice coverage.

Both metrics use the same spatial reference area and the same pixel-level sea-ice detection threshold.

---

## 1. Input data

For every region, `RegionAnalyzer` extracts the concentration values corresponding to the persistent reference water mask.

Only values in the valid concentration range

```text
0 <= concentration <= 1000
```

are considered valid water observations.

The special value:

```text
2550
```

is treated as missing data.

If a missing value is present in the selected region, the complete region/day is skipped.

---

## 2. Pixel-level sea-ice detection threshold

A concentration threshold of:

```text
150 = 15%
```

is used to identify sea-ice-covered pixels.

The current implementation uses:

```python
ice = water >= 150
```

Therefore, a concentration of exactly 15% is classified as ice-covered.

This threshold is the **pixel-level detection threshold** used for the coverage metrics.

It is distinct from the seasonal event thresholds of 10%, 50%, and 90%, which are used only for break-up and freeze-up detection.

---

## 3. Absolute ice area

The absolute ice area counts all pixels whose concentration is at least 15%.

Each detected ice pixel contributes its full pixel area:

```text
625 km²
```

The calculation is therefore:

```text
absolute ice area
=
number of pixels with concentration >= 15%
× 625 km²
```

A pixel with a concentration of 15% contributes the same full pixel area as a pixel with a concentration of 100%.

The metric therefore represents the spatial extent of pixels meeting the detection threshold rather than concentration-weighted ice area.

---

## 4. Relative ice area

The relative ice-area calculation uses the concentration of each detected ice pixel.

Only pixels satisfying:

```text
concentration >= 15%
```

contribute to the sum.

For each such pixel:

```text
ice area contribution
=
concentration / 1000 × 625 km²
```

The total relative ice area is therefore:

```text
relative ice area
=
Σ(concentration / 1000 × 625 km²)
```

where the sum is taken only over pixels meeting the 15% detection threshold.

Sub-threshold pixels are not included in this sum.

This is therefore **not** equivalent to taking the simple mean concentration over all water pixels.

---

## 5. Reference water area

Both coverage metrics use the fixed reference water area calculated during reference generation.

For each region:

```text
reference water area
=
reference water pixels × 625 km²
```

The value is stored in:

```text
output/reference/reference_summary.json
```

and subsequently loaded by `RegionAnalyzer`.

The denominator is therefore fixed across the time series.

---

## 6. Absolute coverage

Absolute coverage is calculated as:

```text
absolute coverage
=
absolute ice area
/
reference water area
× 100
```

This metric describes the fraction of the predefined reference water area occupied by pixels that meet the 15% sea-ice detection threshold.

---

## 7. Relative coverage

Relative coverage is calculated as:

```text
relative coverage
=
relative ice area
/
reference water area
× 100
```

Because the numerator is concentration-weighted, the metric accounts for the concentration of the detected ice pixels.

A pixel with 100% concentration contributes 625 km² to the numerator, while a pixel with 50% concentration contributes 312.5 km².

Pixels below the 15% detection threshold do not contribute.

---

## 8. Interpretation

The two metrics describe different aspects of sea-ice conditions.

### Absolute coverage

Measures the spatial extent of pixels classified as ice-covered according to the 15% detection threshold.

### Relative coverage

Measures the concentration-weighted ice area within the same fixed reference water domain.

The relative metric is therefore sensitive not only to how many pixels are classified as ice-covered but also to the concentration within those pixels.

---

## 9. Relationship between the metrics

For the same observation:

```text
relative coverage <= absolute coverage
```

is generally expected because the relative metric weights each detected pixel by its concentration, which is at most 100%.

The two metrics become similar when most detected pixels have high concentration.

They diverge more strongly when a substantial fraction of detected pixels has concentrations close to the 15% threshold.

---

## 10. Quality checks

Before calculating coverage, the implementation checks that:

1. no selected reference pixel contains the missing-data value `2550`;
2. the number of valid water pixels agrees with the reference value.

If either condition fails, the region/day is skipped.

This prevents a partial daily observation from silently changing the effective spatial denominator.

---

## 11. Output fields

For every successfully processed region/day, the analysis stores:

* `water_pixels`
* `water_area_km2`
* `absolute_ice_area_km2`
* `relative_ice_area_km2`
* `absolute_coverage_percent`
* `relative_coverage_percent`
* `missing_pixels`

The date and region are stored alongside these metrics.

The resulting observations form the persistent input for the temporal analysis.

---

## 12. Threshold terminology

The following thresholds must be kept conceptually separate:

| Threshold                       | Current value | Purpose                                             |
| ------------------------------- | ------------: | --------------------------------------------------- |
| Pixel detection threshold       |           15% | Classifies pixels as ice for coverage metrics       |
| Break-up / freeze-up thresholds | 10%, 50%, 90% | Defines seasonal event levels                       |
| Event persistence               |        7 days | Prevents short-lived crossings from defining events |
| Moving-average window           |       ±3 days | Smoothing for temporal visualization/analysis       |

Changing one of these parameters does not automatically imply changing the others.

---

## 13. Methodological scope

The current coverage metrics use a fixed reference water area and a fixed pixel area.

They do not currently account for:

* fractional pixel intersection at region boundaries,
* dynamic daily water-area changes,
* uncertainty estimates of the satellite product,
* concentration uncertainty propagation.

These topics are outside the current v0.1 implementation.
