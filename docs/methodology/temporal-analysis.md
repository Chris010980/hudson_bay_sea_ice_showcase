# Temporal Analysis

## Purpose

This document describes the temporal analysis applied to the daily regional sea ice coverage observations.

The temporal analysis transforms daily regional statistics into continuous time series, climatological reference values, anomalies, annual statistics and other derived quantities.

---

## Input

The temporal analysis operates on the persistent daily regional results produced by the spatial analysis.

For each observation, the dataset contains a date, region and the corresponding coverage metrics.

The two coverage measures are analysed separately:

* relative sea ice coverage;
* absolute sea ice coverage.

---

## Calendar-Based Time Series

The temporal analysis uses a daily calendar as the temporal reference.

For each region, the observations are aligned to a continuous daily date index.

This allows missing observation dates to be identified explicitly and provides a consistent temporal basis for subsequent calculations.

Leap years are represented using their actual calendar length.

---

## Missing Observations and Interpolation

Short gaps in the daily time series may be interpolated.

The current implementation uses linear interpolation for gaps up to a configured maximum length.

The current maximum interpolation gap is:

```text
14 days
```

Longer gaps are not bridged by interpolation.

The purpose of this procedure is to provide a regular daily time series for statistical and visualization purposes without creating artificial values across long periods without observations.

Interpolation therefore does not imply that the original satellite observation existed on the interpolated date.

---

## Moving Average

The current time-series analysis uses a centered moving average as a visualization and analysis aid.

The current configuration corresponds to a seven-day window:

```text
day - 3
day
day + 3
```

The moving average reduces short-term variability and makes seasonal transitions easier to inspect.

It is a processing aid rather than an independent scientific observation.

The moving average must therefore be distinguished from:

* the original daily observation;
* the interpolation procedure;
* the climatological mean;
* the seasonal event persistence criterion.

The moving average does not replace the underlying daily observations in the persistent results.

---

## Climatology

A climatological reference is calculated for the period:

```text
1981–2010
```

For each calendar day, the historical observations within the reference period are grouped together.

The climatology currently provides:

* mean;
* standard deviation;
* minimum;
* maximum.

The calculation is performed separately for relative and absolute coverage.

The climatological mean represents the typical value for a given calendar day during the reference period.

The standard deviation describes the interannual variability around that climatological mean.

---

## Calendar-Day Alignment

Climatological values are associated with calendar days rather than absolute dates.

For example, observations from different years corresponding to the same month and day contribute to the same climatological distribution.

This allows an observation from an arbitrary year to be compared with the corresponding climatological state.

Leap-day handling follows the calendar representation used by the analysis implementation.

---

## Anomalies

Anomalies describe the deviation of an observation from the corresponding climatological mean.

For an observation `x` and climatological mean `μ`:

```text
absolute anomaly
=
x - μ
```

The project calculates anomalies separately for:

* relative coverage;
* absolute coverage.

The anomaly therefore retains the unit and physical meaning of the underlying metric.

---

## Relative and Absolute Anomaly Measures

The project distinguishes between the underlying coverage metrics and their anomalies.

For relative coverage, the anomaly describes the deviation of the observed percentage coverage from the climatological percentage.

For absolute coverage, the anomaly describes the deviation of the observed ice-covered area from the climatological area.

The anomaly calculations do not change the underlying daily coverage data.

---

## Complete Calendar Years

Annual statistics are calculated only for complete calendar years.

A complete year must contain the required daily observations from:

```text
January 1
```

through:

```text
December 31
```

with the appropriate number of days for leap years.

Incomplete years are not treated as full-year observations for the annual statistics.

---

## Annual Mean

For each complete calendar year and region, the mean coverage is calculated.

The calculation is performed separately for:

* relative coverage;
* absolute coverage.

The annual mean provides a compact measure of the overall sea ice conditions during a given calendar year.

---

## Linear Trend

The annual means are used to calculate a linear regression over time.

The current implementation derives:

* linear trend;
* coefficient of determination, `R²`.

The linear trend provides a simple description of the change in annual mean coverage over the analysed period.

It is not intended to imply that the underlying sea ice evolution is necessarily linear.

No non-linear trend model is currently part of the methodology.

---

## Separation of Analysis Products

The temporal analysis produces several derived datasets with different purposes:

```text
Daily regional observations
        ↓
Calendar-aligned time series
        ├── moving averages
        ├── climatology
        ├── anomalies
        ├── annual means
        └── seasonal event analysis
```

The derived products are stored separately from the persistent daily regional observations.

---

## Interpretation

Temporal analysis provides several complementary perspectives:

* daily time series show short-term and seasonal variability;
* moving averages make broader seasonal behaviour easier to inspect;
* climatology provides a fixed historical reference;
* anomalies show departures from that reference;
* annual means summarize complete calendar years;
* linear trends describe long-term change in annual means.

These quantities should therefore be interpreted in relation to the specific calculation from which they originate.
