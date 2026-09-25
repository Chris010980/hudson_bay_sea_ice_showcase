# Test Levels

## 1. Purpose

This document defines the test levels used by the `hudson_bay_sea_ice` project and describes how the project's components and workflows should be tested.

The test levels complement the general principles defined in `test-strategy.md`.

The project distinguishes between:

1. Unit tests
2. Component tests
3. Integration tests
4. End-to-end tests
5. Regression tests

Regression testing is a cross-cutting activity rather than an independent architectural test level. A regression test may therefore be implemented at unit, component, integration or end-to-end level.

The test levels described here define the **v0.1 testing model and intended test responsibilities**. They do not imply that all listed tests are already implemented.

---

## 2. Unit Tests

### 2.1 Purpose

Unit tests verify small, deterministic and isolated pieces of functionality.

They should execute quickly and independently of:

* network access,
* the live NSIDC service,
* GitHub,
* the production data directory,
* the production output directory.

Unit tests should preferably operate on values or small controlled datasets supplied directly by the test.

---

### 2.2 Unit-Test Candidates

Suitable unit-test candidates include:

#### Data and date handling

* date extraction from filenames,
* date-range handling,
* seasonal date boundaries,
* year transitions,
* leap-year handling,
* path construction,
* configuration parsing.

#### Scientific calculations

* concentration normalization,
* pixel-area calculations,
* absolute ice-area calculations,
* relative ice-area calculations,
* coverage calculations,
* climatological statistics,
* anomaly calculations,
* annual statistics,
* numerical helper functions used by visualization or analysis.

#### Time-series processing

* calendar reconstruction,
* interpolation-gap handling,
* moving-average calculation,
* complete-year filtering,
* calendar-day climatology.

#### Threshold-event logic

Threshold-event detection is particularly important for unit testing.

Tests should cover:

* values below and above thresholds,
* exact threshold values,
* upward crossings,
* downward crossings,
* interpolated crossing dates,
* persistence requirements,
* missing observations,
* gaps in observations,
* seasonal boundaries,
* break-up boundaries,
* freeze-up boundaries,
* year transitions.

#### Data transformation and validation

Suitable tests include:

* duplicate detection,
* sorting,
* value-range validation,
* output schema validation,
* JSON structure validation,
* handling of missing or malformed metadata.

---

## 3. Component Tests

### 3.1 Purpose

Component tests verify complete project components in relative isolation.

Unlike unit tests, component tests may use:

* realistic files,
* controlled raster data,
* temporary directories,
* multiple internal functions,
* several processing steps of the same component.

The purpose is to verify that a component behaves correctly as a complete unit of functionality.

---

### 3.2 `RegionAnalyzer`

`RegionAnalyzer` is a high-priority component because its output directly determines the daily scientific coverage metrics.

Component tests should verify:

* loading of a valid GeoTIFF,
* interpretation of concentration values,
* handling of special values,
* application of regional masks,
* absolute coverage calculation,
* relative coverage calculation,
* pixel-based area calculation,
* observation-date handling,
* rejection of invalid or incomplete regional data,
* consistency with the reference water-pixel configuration.

Small synthetic raster fixtures should be preferred wherever possible.

---

### 3.3 `ReferenceBuilder`

`ReferenceBuilder` is responsible for constructing reusable spatial reference products.

Tests should verify:

* generation of regional masks,
* generation of reference metadata,
* expected output structure,
* handling of valid reference data,
* handling of invalid reference data,
* consistency between generated masks and reference metadata.

Controlled raster and region fixtures should be used rather than relying on the production reference dataset for ordinary automated tests.

---

### 3.4 `ResultsManager`

`ResultsManager` is responsible for persistent daily analysis results.

Tests should verify:

* loading of existing results,
* addition of new observations,
* preservation of existing observations,
* `(date, region)` deduplication,
* sorting,
* CSV persistence,
* creation and update of `latest.json`,
* determination of the latest processed date,
* behavior with empty result files,
* behavior when result files do not yet exist.

Tests should use temporary directories.

---

### 3.5 `TimeSeriesAnalyzer`

`TimeSeriesAnalyzer` receives high testing priority because it contains several scientifically relevant transformations.

The component should be tested as a complete processing chain:

```text
daily results
      ↓
calendar reconstruction
      ↓
interpolation
      ↓
moving average
      ↓
climatology
      ↓
anomalies
      ↓
annual means
      ↓
threshold events
```

Component tests should verify that these processing stages interact correctly and that the generated datasets contain the expected structure and values.

Mathematically sensitive operations should additionally be covered by focused unit tests.

---

### 3.6 `NSIDCDownloader`

The downloader should be tested without requiring the live NSIDC service during normal test execution.

Tests should cover:

* remote-file identification,
* local-file identification,
* date and product-key handling,
* recognition of equivalent product versions,
* missing-file detection,
* download-result handling,
* synchronization behavior,
* temporary-data cleanup.

Network interactions should normally be mocked or represented by controlled fixtures.

Dedicated external-service tests may be added separately when required.

---

### 3.7 Visualization Components

The visualization components should primarily be tested for functional behavior rather than pixel-perfect visual identity.

Tests should verify:

* creation of expected plots,
* correct output paths,
* handling of configured regions,
* handling of selected plot types,
* existence of required output files,
* behavior with valid and incomplete input data.

Where numerical or structural properties of a plot are important, those properties should be tested directly.

Visual regression testing may be introduced later if the project requires it.

---

## 4. Integration Tests

### 4.1 Purpose

Integration tests verify the interaction and data exchange between multiple project components.

The focus is not on whether one component works in isolation, but whether independently functioning components can exchange their outputs and continue processing correctly.

---

### 4.2 Spatial Processing Integration

The spatial-processing chain should be tested as:

```text
ReferenceBuilder
      ↓
reference products
      ↓
RegionAnalyzer
      ↓
daily regional results
      ↓
ResultsManager
```

Tests should verify that:

* reference products can be consumed by the spatial analyzer,
* regional results have the expected structure,
* results can be persisted without unintended information loss,
* multiple observation dates can be processed incrementally.

---

### 4.3 Temporal Analysis Integration

The temporal-processing chain should be tested as:

```text
persistent daily results
      ↓
TimeSeriesAnalyzer
      ↓
derived temporal datasets
```

Tests should verify:

* expected input and output schemas,
* region consistency,
* date consistency,
* preservation of existing observations,
* correct propagation of calculated values,
* consistency between generated temporal result files.

---

### 4.4 Analysis-to-Visualization Integration

The outputs of the analysis layer shall be usable as inputs to the visualization layer.

The relevant flow is:

```text
TimeSeriesAnalyzer
      ↓
ice_coverage_timeseries.csv
ice_coverage_yearly.csv
ice_coverage_events.csv
      ↓
TimeSeriesPlotter
      ↓
plot files
```

Tests should verify that the current analysis outputs can be consumed by the plotting components and that the expected plot products are generated.

The spatial plotting chain should be tested analogously using the outputs of the spatial-analysis layer.

---

### 4.5 Website Build Integration

The website build should be tested as an integration between the static website source and generated project outputs:

```text
docs/
  +
output/
  ↓
build_pages
  ↓
build/
```

Tests should verify:

* website source files are copied,
* required analysis output is copied,
* required plot resources are copied,
* expected HTML pages exist,
* expected resource paths are present,
* the generated directory structure matches the GitHub Pages deployment structure.

The build should be executed against an isolated temporary directory.

No manually maintained second copy of scientific output should be required.

---

### 4.6 Pipeline Integration

Where practical, the main processing stages should also be tested together:

```text
download
   ↓
process
   ↓
plots
   ↓
build
```

The tests should use controlled input data rather than the live production dataset.

The primary purpose is to verify:

* correct stage ordering,
* correct data exchange,
* expected handling of intermediate outputs,
* failure propagation,
* correct final output locations.

---

## 5. End-to-End Tests

### 5.1 Purpose

End-to-end tests verify complete user-relevant processing workflows from controlled input data to final generated artifacts.

Because E2E tests are comparatively expensive and more environment-dependent, their number should remain limited.

They should complement rather than replace unit, component and integration tests.

---

### 5.2 Complete Processing Workflow

A representative E2E scenario is:

```text
controlled input data
        ↓
spatial processing
        ↓
regional analysis
        ↓
persistent results
        ↓
temporal analysis
        ↓
plot generation
        ↓
website build
```

The test should verify that:

* the complete workflow succeeds,
* required intermediate outputs are created,
* final analytical outputs exist,
* expected plots exist,
* the website build is complete,
* no unintended production files are modified.

The workflow should use controlled data and isolated paths.

---

### 5.3 Incremental Update Workflow

Incremental processing is an important operational use case.

Initial state:

```text
existing historical results
```

New input:

```text
one or more new observations
```

Expected processing:

```text
existing results
      +
new observations
      ↓
updated persistent results
      ↓
updated temporal analysis
      ↓
updated plots
      ↓
updated website build
```

The test should verify that:

* existing historical observations remain unchanged,
* new observations are incorporated,
* duplicate observations are not introduced,
* derived outputs are updated consistently,
* the generated website reflects the updated results.

---

### 5.4 No-New-Data Workflow

The no-new-data case is an important operational scenario.

The current update pipeline determines whether observations newer than the latest processed date are available.

When no new observations are available, the update pipeline currently terminates without processing new downstream scientific products.

The corresponding test should therefore verify the **actual v0.1 no-change behavior**, including:

* recognition that no new observations are available,
* preservation of existing persistent scientific results,
* absence of unintended duplicate processing,
* absence of unintended modifications to existing derived outputs.

If the desired future behavior changes so that plots or the website are rebuilt even without new observations, that should be treated as a separate implementation change rather than silently incorporated into the current test documentation.

---

## 6. Regression Tests

### 6.1 Purpose

Regression tests ensure that previously verified behavior remains correct after future changes.

Regression testing is cross-cutting and may be implemented at any of the other test levels.

---

### 6.2 Scientific Regression Cases

Permanent regression tests should be added for relevant defects and important edge cases, including:

* threshold crossing,
* persistence,
* break-up and freeze-up boundaries,
* late freeze-up,
* year transitions,
* leap years,
* missing observations,
* interpolation gaps,
* climatology boundaries,
* anomaly calculation,
* absolute versus relative coverage.

A regression test should contain a meaningful assertion about the behavior that is being protected.

---

### 6.3 Data Regression Cases

Regression tests should protect against:

* duplicate `(date, region)` records,
* accidental loss of historical results,
* incorrect latest-date detection,
* malformed output files,
* inconsistent derived datasets.

---

### 6.4 Pipeline Regression Cases

Pipeline regression tests should protect against:

* incorrect stage ordering,
* skipped processing stages,
* incorrect cleanup,
* incorrect build paths,
* missing website resources,
* unintended modification of persistent scientific data.

---

## 7. Test Fixtures

Fixtures should be selected according to the behavior being tested.

### Unit Fixtures

Small in-memory values or minimal deterministic datasets.

### Component Fixtures

Small files representing realistic component inputs, such as:

* synthetic GeoTIFFs,
* region definitions,
* CSV files,
* JSON files.

### Integration Fixtures

Small collections of files representing a complete controlled processing state.

### Regression Fixtures

Known datasets representing previously verified behavior or previously detected defects.

Fixtures should remain small and deterministic wherever possible.

Version-controlled fixtures should be preferred when they are stable and sufficiently small.

---

## 8. Test Isolation and Temporary Data

Automated tests shall not modify production project data.

Tests involving filesystem operations shall use temporary directories or explicitly isolated test directories.

Normal test execution should not modify:

```text
data/
output/
build/
logs/
```

unless a test deliberately creates an isolated equivalent of these directories in a temporary location.

Cleanup behavior should itself be tested to ensure that only files inside the intended temporary scope are removed.

---

## 9. External Dependencies

The following external dependencies should normally be isolated from the regular test suite:

* NSIDC remote archives,
* network access,
* GitHub,
* GitHub Pages,
* external web services.

Mocking and controlled fixtures should be used when external interactions need to be represented in ordinary automated tests.

Dedicated integration tests may exercise actual external services separately where this provides meaningful additional coverage.

Such tests should not be required for every normal test-suite execution.

---

## 10. Test Level Selection Guidelines

Not every behavior requires tests at every level.

| Situation                       | Preferred level                      |
| ------------------------------- | ------------------------------------ |
| Small deterministic calculation | Unit                                 |
| Scientific algorithm            | Unit + Component                     |
| Complete project component      | Component                            |
| Interaction between components  | Integration                          |
| Complete processing workflow    | E2E                                  |
| Previously fixed defect         | Regression at lowest suitable level  |
| External-service interaction    | Component/Integration with isolation |
| Output-schema validation        | Component/Integration                |
| Complete website build          | Integration/E2E                      |

Tests should generally be implemented at the **lowest level that can adequately verify the required behavior**.

Higher-level tests should be added when the interaction itself is part of the requirement.

---

## 11. Relationship to Project Components

The following table describes the **intended testing responsibility** of the current project components.

It is not an inventory of tests that already exist.

| Component               |   Unit  | Component | Integration |      E2E     |
| ----------------------- | :-----: | :-------: | :---------: | :----------: |
| `main.py`               |    –    |     ✓     |      ✓      |       ✓      |
| `NSIDCDownloader`       |    ✓    |     ✓     |      ✓      |      ✓*      |
| `download_data.py`      | limited |     ✓     |      ✓      |      ✓*      |
| `ReferenceBuilder`      |    ✓    |     ✓     |      ✓      |      ✓*      |
| `RegionAnalyzer`        |    ✓    |     ✓     |      ✓      |      ✓*      |
| `ResultsManager`        |    ✓    |     ✓     |      ✓      |      ✓*      |
| `process_data.py`       | limited |     ✓     |      ✓      |       ✓      |
| `TimeSeriesAnalyzer`    |    ✓    |     ✓     |      ✓      |       ✓      |
| `SeaIcePlotter`         |    ✓    |     ✓     |      ✓      |      ✓*      |
| `TimeSeriesPlotter`     |    ✓    |     ✓     |      ✓      |       ✓      |
| `generate_plots.py`     | limited |     ✓     |      ✓      |       ✓      |
| `update_pipeline.py`    | limited |     ✓     |      ✓      |       ✓      |
| `build_pages.py`        | limited |     ✓     |      ✓      |       ✓      |
| GitHub Pages deployment |    –    |     –     |   limited   | dedicated CI |

`*` E2E tests should use controlled or mocked external input rather than depend on the live external service.

The table defines where tests are appropriate; it does not imply that every check in the table is already implemented.

---

## 12. Test Priority

Initial testing effort should focus on functionality where implementation errors can directly affect scientific results or persistent project data.

The recommended v0.1 priority is:

1. `RegionAnalyzer`
2. `TimeSeriesAnalyzer`
3. `ResultsManager`
4. `ReferenceBuilder`
5. incremental update behavior
6. output validation
7. visualization and website build
8. downloader and external-service integration

This priority defines the recommended order for expanding the automated test suite.

It does not imply that lower-priority components are unimportant.

---

## 13. Test Level Boundaries

The boundaries between test levels should remain clear.

A unit test should not become a disguised integration test simply because constructing a larger project object graph appears convenient.

Likewise, an E2E test should not attempt to verify every individual mathematical intermediate value.

The intended separation is:

```text
Unit
  → Is this individual behavior mathematically or logically correct?

Component
  → Does this complete component behave correctly?

Integration
  → Do the components exchange and process data correctly?

E2E
  → Does the complete workflow produce the intended artifacts and results?

Regression
  → Does previously verified behavior remain correct?
```

This separation is intended to keep the test suite understandable, maintainable and diagnostically useful.
