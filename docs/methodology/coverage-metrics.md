# Coverage Metrics

## Purpose

This document defines the regional sea ice coverage quantities calculated from the daily sea ice concentration observations.

The project currently derives two complementary measures:

1. relative sea ice coverage;
2. absolute sea ice coverage.

These quantities describe different aspects of the same regional observation and must not be interpreted as interchangeable metrics.

---

## Regional Pixel Set

For each analysis region, the spatial processing defines a set of relevant water pixels.

Each pixel represents an area of:

```text
625 km²
```

For a valid pixel, the sea ice concentration is represented as a fractional value:

```text
0 ≤ c ≤ 1
```

where:

* `c = 0` corresponds to 0 % concentration;
* `c = 1` corresponds to 100 % concentration.

Invalid and special-value pixels are excluded from the numerical calculation.

---

## Relative Sea Ice Coverage

Relative sea ice coverage represents the mean fractional sea ice concentration across the relevant regional pixels.

Conceptually:

```text
relative coverage
=
mean(sea ice concentration)
```

Expressed as a percentage:

```text
relative coverage [%]
=
mean(c) × 100
```

This measure accounts for the concentration assigned to each valid pixel.

For example, a collection of pixels with concentrations of 0.2, 0.5 and 0.8 has a mean concentration of:

```text
(0.2 + 0.5 + 0.8) / 3
=
0.5
```

corresponding to 50 % relative coverage.

---

## Absolute Sea Ice Coverage

Absolute coverage represents the physical area classified as ice-covered according to the project's pixel detection criterion.

For each relevant water pixel, the current implementation applies a detection threshold.

A pixel above the threshold contributes its complete pixel area:

```text
625 km²
```

A pixel at or below the threshold contributes:

```text
0 km²
```

Conceptually:

```text
absolute ice area
=
number of detected ice pixels × 625 km²
```

The resulting quantity represents an area rather than a concentration-weighted area.

---

## Pixel Detection Threshold

The pixel detection threshold is a property of the absolute/binary coverage calculation.

The current implementation uses a concentration threshold of:

```text
15 %
```

or:

```text
0.15
```

A relevant water pixel is therefore classified as ice-covered when its concentration exceeds the configured detection threshold.

This threshold has a different purpose from the seasonal event thresholds used for break-up and freeze-up detection.

### Distinct threshold concepts

The project distinguishes:

```text
Pixel detection threshold
        ↓
binary pixel classification
        ↓
absolute ice-covered area
```

from:

```text
Seasonal event threshold
        ↓
regional time-series crossing
        ↓
break-up / freeze-up date
```

The pixel detection threshold must therefore not be interpreted as a seasonal definition of break-up or freeze-up.

---

## Absolute and Relative Metrics Compared

The two metrics answer different questions.

| Metric            | Interpretation                                                 |
| ----------------- | -------------------------------------------------------------- |
| Relative coverage | How large is the mean sea ice concentration across the region? |
| Absolute coverage | How much area consists of pixels classified as ice-covered?    |

A region can therefore have similar relative coverage but different absolute coverage when its spatial extent differs.

Likewise, the two measures can respond differently to partial concentration within individual pixels.

---

## Units

The current outputs use:

### Relative coverage

```text
%
```

### Absolute coverage

```text
km²
```

The corresponding quantities remain separate throughout the analysis pipeline and visualization.

---

## Relation to Temporal Analysis

The daily coverage metrics form the input to the temporal analysis.

For each region, the resulting daily observations can subsequently be used to calculate:

* moving averages;
* climatological statistics;
* anomalies;
* annual means;
* seasonal event dates;
* threshold durations.

The temporal methodology is described in `temporal-analysis.md` and `event-detection.md`.

---

## Methodological Considerations

The two coverage measures should not be treated as interchangeable estimates of exactly the same quantity.

Relative coverage retains information about fractional concentration within pixels.

Absolute coverage uses a binary interpretation of pixels according to the detection threshold.

The choice between the two metrics therefore depends on the scientific question being addressed.

---

## Current Scope

The current implementation uses a fixed pixel area of 625 km² and a fixed pixel detection threshold.

Future work may examine the scientific implications of this threshold in more detail and evaluate whether alternative definitions are appropriate for different products or spatial resolutions.
