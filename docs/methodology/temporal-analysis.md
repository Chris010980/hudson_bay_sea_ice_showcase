# Temporal Analysis

## 1. Purpose

This document describes the temporal analysis applied to the persistent daily regional sea-ice coverage dataset.

The `TimeSeriesAnalyzer` transforms the daily regional results into derived time series, climatological statistics, anomalies, annual means and seasonal threshold-event datasets.

---

## 2. Input Dataset

The temporal analysis uses:

```text
output/analysis/ice_coverage_summary.csv
```

The daily regional observations are grouped independently by region and sorted chronologically.

The original persistent daily result dataset is not replaced by the derived temporal analysis.

---

## 3. Calendar Reconstruction

For each region, the analyzer constructs a complete daily calendar between the first and last available observation.

This creates explicit rows for calendar days for which no original observation is available.

The resulting temporal index therefore represents the expected daily time axis rather than only the dates for which an original GeoTIFF was successfully processed.

---

## 4. Missing-Day Interpolation

Numeric columns are interpolated using time-based linear interpolation.

The current configuration is:

```text
method = "time"
limit = 14
limit_direction = "both"
```

The interpolation therefore fills gaps of up to 14 consecutive missing calendar days when suitable values are available.

Interpolation is performed independently for each region.

The `limit_direction="both"` setting also permits interpolation toward the beginning or end of the available regional series within the configured limit.

The interpolation does not constitute the creation of new observations from the original satellite product. Interpolated values are derived values used to obtain a continuous daily analytical time series.

---

## 5. Moving Average

The temporal analysis calculates a centered moving average for selected daily quantities.

The current implementation uses:

```text
window = 3
```

on each side of the current day.

This produces a seven-day centered window:

```text
day - 3
day - 2
day - 1
day
day + 1
day + 2
day + 3
```

The corresponding rolling calculation uses:

```text
window_size = 7
center = True
min_periods = 1
```

The smoothed quantities currently include:

* relative coverage,
* absolute coverage,
* relative ice area,
* absolute ice area.

---

## 6. Contiguous Valid Segments

Moving averages are calculated separately for contiguous valid data segments.

A gap in the underlying values therefore separates two valid segments.

The rolling calculation does not bridge such gaps by using values from both sides.

At the edges of a valid segment, the calculation uses the available values because `min_periods=1` is configured.

---

## 7. Climatological Reference Period

The current climatology uses the period:

```text
1981–2010
```

inclusive.

The climatology is calculated independently for each configured region.

This reference period provides the baseline against which daily observations can be expressed as anomalies.

---

## 8. Calendar-Day Climatology

The climatology is grouped by:

```text
month-day
```

rather than by day-of-year.

This avoids shifting all dates after February when leap years are present in the reference period.

For each region and calendar day, the current implementation calculates statistics for:

* relative ice coverage,
* absolute ice coverage.

The generated climatological statistics include:

* mean,
* standard deviation,
* minimum,
* maximum.

The resulting climatological values are merged back into the complete regional daily time series.

---

## 9. Leap-Day Treatment

Because the climatology is grouped by `month-day`, February 29 is treated as its own calendar-day category when it occurs in the reference data.

It is therefore not automatically shifted onto February 28 or March 1.

The resulting availability of a February 29 climatological value depends on the observations available during the reference period.

---

## 10. Anomalies

Anomalies are calculated as the difference between the observation and the corresponding climatological mean.

For relative coverage:

$$
A_{\mathrm{relative}}
=
C_{\mathrm{relative}}
-
\overline{C}_{\mathrm{relative,1981-2010}}
$$

For absolute coverage:

$$
A_{\mathrm{absolute}}
=
C_{\mathrm{absolute}}
-
\overline{C}_{\mathrm{absolute,1981-2010}}
$$

The anomalies are therefore expressed in **percentage points**, not as relative percentages of the climatological value.

Positive anomalies indicate coverage above the corresponding climatological mean.

Negative anomalies indicate coverage below the corresponding climatological mean.

---

## 11. Annual Means

Annual means are calculated separately for each region.

A calendar year is considered complete only when the expected number of daily observations is available with a valid:

```text
relative_coverage_percent
```

value.

The expected number of days is:

```text
365 days
```

for a normal year and:

```text
366 days
```

for a leap year.

Incomplete region-years are excluded from the annual-mean dataset.

The annual dataset contains the mean values required for long-term comparison of regional sea-ice conditions.

---

## 12. Derived Annual Quantities

The annual analysis provides yearly mean indicators for the sea-ice coverage and area quantities available in the daily dataset.

These annual values form the basis for the corresponding yearly visualizations and can subsequently be used for further statistical analysis.

---

## 13. Trend Analysis

Trend fitting is not performed by the `TimeSeriesAnalyzer`.

The temporal analyzer produces the annual mean dataset.

Trend lines and associated statistics are calculated in the visualization layer when required for the corresponding plots.

This separation keeps the temporal data transformation independent from the presentation-specific trend calculation.

---

## 14. Seasonal Event Analysis

The temporal analysis also invokes the threshold-event analysis described separately in:

```text
Event Detection
```

The current thresholds are:

```text
10 %
50 %
90 %
```

with a persistence requirement of seven consecutive calendar days.

The resulting event records are stored separately from the daily time series.

---

## 15. Generated Temporal Datasets

The temporal analysis produces three derived datasets:

```text
output/analysis/
├── ice_coverage_timeseries.csv
├── ice_coverage_yearly.csv
└── ice_coverage_events.csv
```

### `ice_coverage_timeseries.csv`

Contains the reconstructed daily time series together with derived quantities such as moving averages, climatological statistics and anomalies.

### `ice_coverage_yearly.csv`

Contains annual mean statistics for complete region-years.

### `ice_coverage_events.csv`

Contains the threshold-based break-up and freeze-up event records.

---

## 16. Observed and Derived Values

The temporal dataset should distinguish conceptually between:

* original daily observations,
* interpolated daily values,
* moving-average values,
* climatological values,
* anomaly values,
* annual aggregates,
* event dates.

Only the first category represents direct daily observations from the processed GeoTIFF products.

The remaining quantities are derived analytically.

---

## 17. Current Limitations

The v0.1 temporal methodology has several explicit limitations:

* interpolation is applied to the numeric columns selected by the implementation rather than through a dedicated scientific treatment of each variable;
* interpolation is limited to 14 calendar days;
* bidirectional interpolation can fill values toward the boundaries of the available regional series;
* annual completeness is determined from `relative_coverage_percent`;
* the climatological reference period is fixed to 1981–2010;
* February 29 is treated as a separate calendar day;
* trend fitting is implemented in the visualization layer rather than the temporal analyzer;
* uncertainty propagation is not currently implemented.

These limitations describe the current implementation and are not intended to imply that the resulting derived quantities are equivalent to independently observed measurements.
