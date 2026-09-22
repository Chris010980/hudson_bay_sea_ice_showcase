# Seasonal Event Detection

## Purpose

This document describes the detection of seasonal sea ice transition dates and the calculation of threshold durations.

The current implementation identifies break-up and freeze-up dates from regional sea ice coverage time series.

Three seasonal thresholds are considered:

```text
10 %
50 %
90 %
```

The event-detection methodology operates on regional time series and is distinct from the pixel detection threshold used for absolute coverage.

---

## Seasonal Events

Two types of seasonal transition are identified.

### Break-up

Break-up describes the seasonal decrease in regional sea ice coverage.

The search period normally extends from:

```text
March 16
```

through:

```text
September 15
```

of the event year.

### Freeze-up

Freeze-up describes the seasonal increase in regional sea ice coverage.

The normal search period extends from:

```text
September 16
```

of the event year through:

```text
March 15
```

of the following year.

---

## Event Thresholds

Break-up and freeze-up are evaluated independently for three regional coverage thresholds:

```text
10 %
50 %
90 %
```

The threshold represents the regional sea ice coverage at which the seasonal transition is identified.

These thresholds are different from the pixel detection threshold used to calculate absolute ice-covered area.

---

## Threshold Crossing

An event is not assigned merely because a time series contains a value close to a threshold.

The implementation requires an actual crossing of the threshold.

For a decreasing break-up transition:

```text
value_before > threshold
value_after  < threshold
```

For an increasing freeze-up transition:

```text
value_before < threshold
value_after  > threshold
```

The crossing date is determined using linear interpolation between the surrounding observations.

This provides a sub-day estimate of the threshold crossing rather than simply assigning the date of one of the two observations.

---

## Temporal Continuity

Threshold detection requires consecutive calendar days around the crossing.

Missing dates are therefore not silently bridged when searching for an event.

This prevents a threshold crossing from being inferred across an extended observational gap.

The requirement for temporal continuity is separate from the interpolation rules used for the general time-series analysis.

---

## Persistence

A detected threshold transition must satisfy the configured persistence requirement.

The current event methodology uses:

```text
7 consecutive calendar days
```

as the persistence criterion.

Persistence is intended to distinguish a sustained seasonal transition from a short-lived fluctuation around the threshold.

Persistence is therefore a separate concept from the threshold value itself.

---

## Break-up Detection

For each threshold, the break-up search examines the regional time series during the break-up season.

Conceptually:

```text
March 16
    ↓
regional coverage decreases
    ↓
threshold crossing
    ↓
persistent post-crossing state
    ↓
break-up date
    ↓
September 15
```

The resulting date is stored together with the region, event year and threshold.

---

## Freeze-up Detection

Freeze-up is searched during the subsequent freeze-up season.

Conceptually:

```text
September 16
    ↓
regional coverage increases
    ↓
threshold crossing
    ↓
persistent post-crossing state
    ↓
freeze-up date
    ↓
March 15 of following year
```

The implementation also allows the beginning of the freeze-up search to be adjusted when the preceding break-up event occurred unusually late.

This prevents a valid early transition immediately following a late break-up from being excluded solely by the nominal September 16 search boundary.

---

## Relationship Between Break-up and Freeze-up

The freeze-up event is associated with the corresponding preceding seasonal cycle.

A freeze-up event is considered valid only when the corresponding threshold was crossed during the preceding break-up season.

This prevents isolated threshold crossings from being interpreted as a complete seasonal cycle.

---

## Event Year

The event year identifies the seasonal cycle to which the event belongs.

For freeze-up, the event year refers to the year in which the freeze-up season begins, even though the event itself may occur during the following calendar year.

This convention allows break-up and freeze-up events belonging to the same seasonal cycle to be compared directly.

---

## Threshold Duration

For a given region, threshold and event year, the seasonal duration is calculated as:

```text
threshold duration
=
freeze-up date
-
break-up date
```

The duration is expressed in days.

The calculation is performed separately for:

```text
10 %
50 %
90 %
```

This produces a measure of the length of the seasonal ice-covered cycle at each threshold.

---

## Distinction Between Threshold Concepts

The project uses several threshold-related concepts that must not be conflated:

| Concept                   | Purpose                                                  |
| ------------------------- | -------------------------------------------------------- |
| Pixel detection threshold | Classify individual pixels for absolute coverage         |
| Event threshold           | Detect regional seasonal transitions                     |
| Persistence               | Require a sustained transition                           |
| Moving-average window     | Smooth short-term variability for analysis/visualization |

These parameters describe different stages or purposes of the analysis.

---

## Missing Data

Threshold detection requires sufficient temporal continuity around the candidate crossing.

Large observational gaps are not bridged simply to obtain an event date.

Consequently, a seasonal event may remain undefined when the available observations do not provide sufficient evidence for a valid threshold crossing.

An undefined event is preferable to assigning an unsupported transition date.

---

## Interpretation

The detected event dates describe transitions in the regional sea ice coverage time series according to the defined thresholds and persistence criteria.

They should not be interpreted as direct observations of the physical moment at which every location in a region freezes or becomes ice-free.

Instead, they represent reproducible statistical transition dates derived from the regional sea ice concentration record.

The three thresholds provide complementary descriptions of the seasonal transition rather than three independent physical events.
