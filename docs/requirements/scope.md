# Project Scope

## Purpose

This document describes the current scope of the `hudson_bay_sea_ice` project.

The scope is based on the current implementation and is intended as a starting point for the later definition of formal requirements.

## Current Scope

The project currently covers the automated processing and visualization of daily sea-ice concentration observations for the Hudson Bay region.

The current system includes:

1. acquisition of NSIDC sea-ice concentration data,
2. spatial processing of daily GeoTIFF observations,
3. regional sea-ice coverage analysis,
4. persistent storage of daily analysis results,
5. temporal and climatological analysis,
6. threshold-based seasonal event analysis,
7. scientific visualization,
8. automated incremental updates,
9. generation of a GitHub Pages website.

## Spatial Scope

The current analysis is based on predefined regions in and around Hudson Bay.

The currently used regions include:

* Hudson Bay,
* Gulf of Boothia,
* Foxe Basin,
* Hudson Strait,
* the overall Hudson Bay analysis area.

The exact region definitions are maintained separately from the analysis logic.

## Temporal Scope

The system processes daily observations.

The temporal analysis currently includes:

* complete calendar years,
* a 1981–2010 climatological reference period,
* seasonal break-up and freeze-up analysis.

## Scientific Scope

The current analysis focuses on sea-ice concentration and derived sea-ice coverage indicators.

Current derived quantities include:

* relative sea-ice coverage,
* absolute sea-ice coverage,
* climatological means,
* climatological standard deviations,
* anomalies,
* annual means,
* break-up dates,
* freeze-up dates,
* threshold-duration values.

Threshold-based analyses currently use:

```text
10 %
50 %
90 %
```

## Automation Scope

The project supports incremental updates.

The update process can:

* determine the latest processed observation,
* download newly available observations,
* process new observations,
* regenerate analysis products,
* regenerate plots,
* rebuild the GitHub Pages deployment,
* remove temporary GeoTIFF files.

## Visualization Scope

The current visualization scope includes:

* spatial sea-ice maps,
* regional maps,
* temporal time-series plots,
* anomaly plots,
* threshold-duration plots,
* polar seasonal plots,
* yearly mean plots.

## Website Scope

The project contains a static documentation and results website.

The website source is located under:

```text
docs/
```

Generated analysis results are maintained separately under:

```text
output/
```

A build step combines both into:

```text
build/
```

for GitHub Pages deployment.

## Current Non-Goals

The following areas are **not currently implemented as part of the existing system** and therefore should not yet be treated as established project requirements:

* sea-ice thickness analysis,
* sea-ice volume analysis,
* higher-resolution auxiliary sea-ice products,
* interactive region selection,
* surface-current analysis,
* additional external datasets,
* a redesigned target architecture,
* a finalized automated test architecture.

These topics may become future scope, but their inclusion has not yet been defined as a requirement.

## Scope Status

This document represents the **current implementation scope**.

It is not yet the final project specification.

The next step is to distinguish:

```text
Current implementation
        ↓
Required project capabilities
        ↓
Explicit non-goals
        ↓
Future extensions
```

Formal functional and non-functional requirements will be defined separately.
