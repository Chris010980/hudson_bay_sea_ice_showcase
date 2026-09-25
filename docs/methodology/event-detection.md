# Event Detection

## 1. Purpose

This document defines the threshold-based seasonal event detection used by the `hudson_bay_sea_ice` temporal analysis.

The current implementation identifies break-up and freeze-up dates from the regional relative sea-ice coverage time series.

---

## 2. Input Metric

Seasonal events are calculated from:

```text
relative_coverage_percent
```

The event detector therefore operates on regional relative ice coverage rather than on individual raster pixels or absolute ice area.

The moving-average time series is not used for event detection.

---

## 3. Thresholds

The current implementation evaluates three regional coverage thresholds independently:

```text
10 %
50 %
90 %
```

Each threshold produces a separate break-up and freeze-up event.

The thresholds represent regional coverage levels.

They should therefore not be interpreted directly as physical definitions of melt onset, complete melt, freeze onset or complete freeze.

---

## 4. Break-Up Events

A break-up event is defined as a downward crossing of a specified coverage threshold.

For two consecutive daily observations \(y_0\) and \(y_1\), a downward crossing occurs when:

$$
y_0 > T
$$

and

$$
y_1 \leq T
$$

where \(T\) is the selected threshold.

The search window for break-up is:

```text
16 March – 15 September
```

of the event year.

---

## 5. Freeze-Up Events

A freeze-up event is defined as an upward crossing of a specified coverage threshold.

For two consecutive daily observations:

$$
y_0 < T
$$

and

$$
y_1 \geq T
$$

The normal freeze-up search window is:

```text
16 September – 15 March
```

where the end date lies in the following calendar year.

Freeze-up is therefore associated with the break-up season rather than being restricted to the calendar year in which the event date occurs.

---

## 6. Persistence Requirement

A threshold crossing is accepted only when the resulting threshold state persists for:

```text
7 consecutive calendar days
```

The crossing day itself counts as the first persistence day.

For break-up, all seven observations must remain at or below the threshold.

For freeze-up, all seven observations must remain at or above the threshold.

The seven observations must also correspond to consecutive calendar days.

This persistence requirement prevents isolated short-term threshold crossings from being interpreted as seasonal events.

---

## 7. Crossing Requirement

The implementation requires an actual transition across the threshold.

For a downward crossing:

```text
previous > threshold
current  <= threshold
```

For an upward crossing:

```text
previous < threshold
current  >= threshold
```

Observations that are not consecutive calendar days cannot form a crossing.

This ensures that an unobserved temporal gap is not implicitly interpreted as a threshold transition.

---

## 8. Event Date Interpolation

Once a persistent crossing has been identified, the event date is determined by linear interpolation between the two observations surrounding the threshold.

For observations \((t_0,y_0)\) and \((t_1,y_1)\), the interpolated threshold time is:

$$
t
=
t_0
+
\frac{T-y_0}{y_1-y_0}
(t_1-t_0)
$$

Special cases are handled directly:

* if the previous observation is exactly equal to the threshold, its date is returned;
* if the current observation is exactly equal to the threshold, its date is returned;
* if both values are equal, the current observation date is used.

The interpolation is therefore linear and deterministic.

---

## 9. Freeze-Up Window Adjustment

The normal freeze-up search begins on 16 September.

The implementation contains an additional condition for cases where the regional coverage on 16 September is already at or above the selected threshold.

In this situation, the freeze-up search window is extended backward to the day after the corresponding break-up event.

This adjustment requires a valid break-up event.

It prevents the normal 16 September start date from excluding an earlier upward crossing when the region is already above the threshold at the beginning of the normal freeze-up window.

---

## 10. Event-Year Convention

Each event record contains an `event_year`.

This year identifies the seasonal cycle in which the event analysis was performed.

A freeze-up event can therefore have an actual calendar date in the following year while retaining the preceding seasonal event year.

For example, a freeze-up associated with the 2025 seasonal cycle may occur in January 2026.

---

## 11. Missing Events

The detector creates event records for the configured region, event type, event year and threshold even when no valid event date can be determined.

In such cases the event date remains unavailable.

This distinguishes:

```text
event was not detected
```

from:

```text
event record does not exist
```

---

## 12. Threshold Duration

The event dataset provides the basis for calculating threshold-specific seasonal duration:

$$
D_T
=
t_{\mathrm{freeze-up},T}
-
t_{\mathrm{break-up},T}
$$

The duration is therefore calculated independently for each threshold.

The corresponding duration plots use the detected break-up and freeze-up dates rather than the underlying daily concentration values.

---

## 13. Relation to Temporal Smoothing

The temporal analysis also generates a centered seven-day moving average.

This smoothed series is intended for visualization and interpretation of the seasonal development.

The event detector itself operates on the unsmoothed `relative_coverage_percent` series.

Consequently, the reported event dates are not threshold crossings of the moving-average series.

---

## 14. Limitations

The v0.1 event detection is intentionally deterministic and threshold-based.

It does not currently model:

* uncertainty in event dates,
* uncertainty of the underlying concentration observations,
* alternative persistence criteria,
* hysteresis between freeze-up and break-up,
* nonlinear interpolation,
* multiple competing seasonal crossings,
* probabilistic event detection.

The selected thresholds and persistence period are methodological parameters of the current implementation and should be interpreted accordingly.
