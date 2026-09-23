# Event Detection

## Purpose

This document describes the detection of seasonal sea-ice break-up and freeze-up events.

Events are derived from the regional relative sea-ice coverage time series using predefined coverage thresholds and a persistence requirement.

The methodology reflects the current implementation of v0.1.

---

## 1. Event types

Two seasonal transition types are detected:

* **break-up**: downward crossing of a sea-ice coverage threshold;
* **freeze-up**: upward crossing of the same threshold.

Events are calculated independently for each analysis region and event year.

---

## 2. Event thresholds

The current implementation evaluates three coverage thresholds:

```text
10%
50%
90%
```

Each threshold is processed independently.

The threshold defines the sea-ice coverage level at which the seasonal transition is considered to occur.

These thresholds are distinct from the 15% pixel-level detection threshold used for the spatial coverage metrics.

---

## 3. Input variable

Event detection uses:

```text
relative_coverage_percent
```

as its input time series.

The event calculation therefore uses the concentration-weighted regional coverage metric rather than the absolute pixel-count coverage.

---

## 4. Persistence requirement

A threshold crossing is accepted only if the threshold condition persists for:

```text
7 consecutive calendar days
```

The crossing day itself is counted as the first persistence day.

For a downward crossing, all seven observations must satisfy:

```text
coverage <= threshold
```

For an upward crossing, all seven observations must satisfy:

```text
coverage >= threshold
```

This persistence criterion prevents a short-lived threshold crossing from automatically defining a seasonal transition.

---

## 5. Calendar continuity

The seven persistence observations must represent consecutive calendar days.

The event detector therefore explicitly checks the date difference between neighboring observations.

A gap in the time series invalidates the persistence sequence.

Missing dates cannot be bridged by simply taking the next available observation.

---

## 6. Break-up detection

Break-up is defined as a downward transition through the selected threshold.

The standard break-up search window is:

```text
March 16 → September 15
```

of the event year.

The detector searches for the first valid persistent downward crossing within this window.

The crossing condition is:

```text
previous value > threshold
current value <= threshold
```

If the threshold is reached exactly, the corresponding observation date is used.

Otherwise, the crossing date is linearly interpolated between the two observations surrounding the threshold.

---

## 7. Freeze-up detection

Freeze-up is defined as an upward transition through the selected threshold.

The standard freeze-up search window is:

```text
September 16 → March 15
```

where March 15 belongs to the following calendar year.

The initial freeze-up search therefore spans the second half of the event year and the beginning of the following year.

---

## 8. Freeze-up start adjustment

The implementation contains an additional rule for cases where the threshold has already been reached by September 16.

The value on September 16 is inspected.

If:

```text
coverage >= threshold
```

the freeze-up search is extended backwards.

The adjusted start date becomes:

```text
break-up date + 1 day
```

This allows the algorithm to detect a freeze-up transition that occurred earlier than the standard September 16 start date.

The corresponding break-up event must exist for this adjustment to be applied.

---

## 9. Relationship between break-up and freeze-up

Freeze-up detection is conditional on successful break-up detection for the same threshold and event year.

If no valid break-up event is found:

```text
freeze-up = None
```

for that threshold/event year.

This establishes a consistent seasonal cycle:

```text
break-up
    ↓
ice-free / low-coverage period
    ↓
freeze-up
```

rather than treating the two transitions as completely independent events.

---

## 10. Crossing-date interpolation

When a threshold is crossed between two observations, the event date is calculated by linear interpolation.

For observations:

```text
(t0, y0)
(t1, y1)
```

and threshold:

```text
T
```

the crossing fraction is:

```text
f = (T - y0) / (y1 - y0)
```

The event date is then placed at the corresponding fraction of the interval between the two observation dates.

This provides a sub-day transition estimate even though the underlying observations are daily.

The interpolation is only performed between two consecutive calendar days satisfying the required crossing condition.

---

## 11. Exact threshold values

The implementation explicitly handles observations that are exactly equal to the threshold.

For example:

```text
coverage = 50%
```

is treated as having reached the 50% threshold.

The corresponding observation date is returned directly rather than performing interpolation.

---

## 12. Event-year definition

Event years are derived from the calendar year of the available observations.

For break-up, the event year corresponds to the year in which the break-up search occurs.

For freeze-up, the search may extend into the following calendar year, but the resulting event remains associated with the original event year.

For example:

```text
event year 2020
    break-up: 2020
    freeze-up: late 2020 / early 2021
```

This allows one seasonal cycle to be represented by a single event year.

---

## 13. Event output

The detected events are stored in:

```text
output/analysis/ice_coverage_events.csv
```

The output contains:

* `region`
* `event_type`
* `event_year`
* `threshold_percent`
* `event_date`

For every region, event year, event type, and threshold, a row is produced even when no valid event date is found.

An absent event is therefore represented explicitly rather than being silently omitted.

---

## 14. Threshold-duration analysis

The event dates are subsequently used by the plotting component to calculate threshold durations.

For a given threshold and event year:

```text
duration
=
freeze-up date
−
break-up date
```

The resulting duration represents the length of the seasonal cycle between the two detected threshold crossings.

The current visualization uses a fixed y-axis range of:

```text
0–365 days
```

---

## 15. Interpretation

The three thresholds represent different aspects of the seasonal transition.

### 90%

Represents a high-coverage threshold and therefore characterizes a transition near the strongly ice-covered state.

### 50%

Represents an intermediate coverage threshold.

### 10%

Represents a low-coverage threshold near the transition to or from an ice-free state.

The thresholds should be interpreted as defined coverage levels rather than as independent physical definitions of the onset or end of the entire ice season.

---

## 16. Distinction from smoothing

Event detection does not use the ±3-day moving average as its input.

The event detector operates on:

```text
relative_coverage_percent
```

directly.

The moving average is a separate derived quantity used for temporal visualization and does not redefine the threshold crossing or persistence criterion.

---

## 17. Current implementation detail

The constructor currently contains:

```python
self.threshold_persistence = 3
```

but this attribute is not used by `calculate_threshold_events()`.

The effective persistence value of the current event calculation is the method default:

```text
persistence = 7
```

This distinction should be resolved in a later cleanup so that the configured parameter and the effective methodology cannot diverge.

---

## 18. Current methodological limitations

The current event detection does not implement:

* probabilistic event detection,
* uncertainty intervals for transition dates,
* alternative persistence models,
* hysteresis-specific physical models,
* nonlinear interpolation,
* multiple competing events within one seasonal window.

The current method is a deterministic threshold-crossing procedure with a seven-day persistence requirement.

Systematic tests for boundary conditions, missing observations, threshold equality, leap years, and event-window behavior are planned as part of the v0.2 testing work.
