# Test Levels

## 1. Purpose

This document defines the test levels used for the Hudson Bay Sea Ice Analysis project and assigns the current software components and processing workflows to the appropriate test levels.

The test levels complement the general testing principles defined in `test-strategy.md`.

The project uses the following test levels:

1. Unit tests
2. Component tests
3. Integration tests
4. End-to-end tests
5. Regression tests

Regression testing is considered a cross-cutting activity rather than an independent architectural test level. A regression test may therefore exist at unit, component, integration or end-to-end level.

---

## 2. Unit Tests

### 2.1 Purpose

Unit tests verify small, isolated pieces of functionality.

They should execute quickly and independently of:

* network access,
* the live NSIDC service,
* GitHub,
* the production data directory,
* the production output directory.

Unit tests should preferably operate on values or small controlled datasets supplied directly by the test.

---

### 2.2 Primary Unit-Test Candidates

The following types of functionality are suitable for unit testing.

#### Data and date handling

Examples include:

* date extraction from filenames,
* date range handling,
* seasonal date boundaries,
* year transitions,
* leap-year handling,
* path construction,
* configuration parsing.

#### Scientific calculations

Examples include:

* absolute sea-ice coverage,
* relative sea-ice coverage,
* concentration normalization,
* pixel-area calculations,
* climatological statistics,
* anomaly calculations,
* annual statistics,
* linear trend calculations.

#### Time-series processing

Examples include:

* calendar interpolation,
* maximum interpolation-gap handling,
* moving-average calculation,
* complete-year filtering.

#### Threshold-event logic

Threshold event detection is particularly important for unit testing.

Tests should cover:

* exact threshold values,
* values below and above thresholds,
* upward crossings,
* downward crossings,
* interpolation of crossing dates,
* persistence requirements,
* missing days,
* gaps in observations,
* seasonal boundaries,
* break-up boundaries,
* freeze-up boundaries,
* year transitions.

#### Data transformation and validation helpers

Examples include:

* duplicate detection,
* sorting,
* value-range validation,
* output schema checks,
* JSON structure validation.

---

## 3. Component Tests

### 3.1 Purpose

Component tests verify complete project components in relative isolation.

Unlike unit tests, component tests may use realistic files, controlled raster data, temporary directories and several internal functions of the component.

The purpose is to verify that a component behaves correctly as a whole.

---

### 3.2 RegionAnalyzer

`RegionAnalyzer` shall be tested as a complete spatial-analysis component.

Tests should verify:

* loading of a valid GeoTIFF,
* interpretation of concentration values,
* handling of special values,
* application of region masks,
* calculation of absolute coverage,
* calculation of relative coverage,
* calculation of pixel-based area,
* extraction of observation dates,
* behavior with invalid or incomplete input data,
* behavior when expected reference information is unavailable.

Small synthetic raster fixtures should be preferred where possible.

---

### 3.3 ReferenceBuilder

`ReferenceBuilder` shall be tested as a complete reference-data component.

Tests should verify:

* creation of reference masks,
* creation of reference metadata,
* expected output structure,
* handling of valid reference data,
* handling of invalid or unsuitable reference data,
* consistency of generated masks and reference metadata.

Reference-building tests should use controlled raster and region fixtures.

---

### 3.4 ResultsManager

`ResultsManager` shall be tested as the persistent-result component.

Tests should verify:

* loading existing results,
* adding new observations,
* preservation of existing results,
* `(date, region)` deduplication,
* sorting,
* saving CSV results,
* creation of `latest.json`,
* determination of the latest processed date,
* behavior with empty or missing result files.

Tests should use temporary directories rather than the production `output/` directory.

---

### 3.5 TimeSeriesAnalyzer

`TimeSeriesAnalyzer` shall receive extensive component-level testing because it contains a large part of the scientific processing logic.

Tests should verify the complete processing stages:

```text
daily results
    ↓
calendar interpolation
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

Component tests should verify that these stages interact correctly and that the resulting data structures contain the expected information.

The most mathematically sensitive individual operations should additionally be covered by unit tests.

---

### 3.6 Downloader

The downloader component shall be tested without depending on the live NSIDC service for normal test execution.

Tests should verify:

* identification of remote files,
* identification of local files,
* date/product key handling,
* recognition of equivalent product versions,
* missing-file detection,
* download result handling,
* synchronization behavior,
* cleanup of temporary GeoTIFF files.

Network behavior should preferably be simulated or mocked.

---

### 3.7 Visualization Components

The visualization components shall be tested primarily for functional behavior rather than pixel-perfect visual similarity.

Tests should verify:

* creation of expected plots,
* correct output paths,
* correct handling of selected regions,
* correct handling of selected plot types,
* required output files,
* behavior with valid and incomplete input data.

Where numerical or structural aspects of the plot are important, these should be tested directly rather than relying solely on image comparison.

Visual regression testing may be introduced later if justified.

---

## 4. Integration Tests

### 4.1 Purpose

Integration tests verify communication and data exchange between multiple components.

The focus is not on the internal correctness of an individual component, but on whether independently functioning components work together correctly.

---

### 4.2 Spatial Processing Integration

The spatial-processing chain should be tested as an integrated workflow:

```text
ReferenceBuilder
       ↓
reference data
       ↓
RegionAnalyzer
       ↓
daily regional results
       ↓
ResultsManager
```

Tests should verify that:

* reference data can be consumed by the spatial analyzer,
* generated regional results have the expected structure,
* results can be persisted without information loss,
* multiple observation dates can be processed incrementally.

---

### 4.3 Temporal Analysis Integration

The temporal-processing chain should be tested as:

```text
ResultsManager
       ↓
persistent daily results
       ↓
TimeSeriesAnalyzer
       ↓
derived time-series results
```

Tests should verify:

* expected input/output schemas,
* region consistency,
* date consistency,
* preservation of existing observations,
* correct propagation of calculated values,
* consistency between derived result files.

---

### 4.4 Analysis-to-Visualization Integration

The analysis outputs shall be tested as inputs to the visualization layer.

Example:

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

Tests should verify that current analysis outputs can be consumed by the visualization components and that all expected plot types are generated.

---

### 4.5 Website Build Integration

The website build shall be tested as an integration between:

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
* generated output is copied to the expected location,
* expected HTML pages exist,
* expected plot resources exist,
* relative resource paths resolve to the generated build structure,
* no second manually maintained copy of scientific output is required.

The test should use an isolated temporary build directory.

---

### 4.6 Pipeline Integration

The individual pipeline stages shall also be tested together where practical:

```text
download
    ↓
process
    ↓
plots
    ↓
build
```

The test should use controlled test data rather than the live production dataset.

The purpose is to verify correct stage ordering, data exchange and failure propagation.

---

## 5. End-to-End Tests

### 5.1 Purpose

End-to-end tests verify complete user-relevant workflows from input data through final generated artifacts.

Because E2E tests are relatively expensive and potentially sensitive to the environment, their number should remain limited.

---

### 5.2 Complete Processing Workflow

A representative E2E workflow is:

```text
controlled input data
        ↓
data processing
        ↓
regional analysis
        ↓
persistent results
        ↓
time-series analysis
        ↓
plot generation
        ↓
website build
```

The test should verify that:

* the complete workflow succeeds,
* all required intermediate outputs are created,
* final scientific outputs exist,
* expected plots exist,
* the website build is complete,
* no unexpected persistent files are modified.

---

### 5.3 Incremental Update Workflow

A second important E2E scenario is an incremental update.

Initial state:

```text
existing historical results
```

New input:

```text
one or more new observations
```

Expected behavior:

```text
existing results
        +
new observations
        ↓
updated persistent results
        ↓
updated derived analysis
        ↓
updated plots
        ↓
updated website build
```

The test should verify that historical observations remain unchanged and that only the intended new data are incorporated.

---

### 5.4 No-New-Data Workflow

The no-new-data case is an important operational scenario.

Expected behavior:

```text
existing dataset
      ↓
update
      ↓
no new observations
```

The system should recognize that no update is necessary.

The test should verify the defined no-change behavior for:

* persistent scientific results,
* generated analysis outputs,
* plots,
* website artifacts.

This test is particularly important because the update pipeline and CI build process currently have separate responsibilities that need to remain consistent.

---

## 6. Regression Tests

### 6.1 Purpose

Regression tests ensure that previously verified behavior remains correct after future changes.

Regression tests are not restricted to a single test level.

---

### 6.2 Scientific Regression Cases

The following areas should receive permanent regression coverage as relevant defects or edge cases are identified:

* threshold crossing,
* persistence,
* break-up/freeze-up seasonal boundaries,
* late freeze-up,
* year transitions,
* leap years,
* missing observations,
* interpolation gaps,
* climatology boundaries,
* anomaly calculation,
* absolute versus relative coverage.

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
* failed cleanup,
* incorrect build paths,
* missing website resources,
* accidental modification of persistent data.

---

## 7. Test Fixtures

Test fixtures shall be designed according to the behavior being tested.

The project should distinguish between:

### Unit fixtures

Small in-memory values or minimal datasets.

### Component fixtures

Small files representing realistic component inputs.

Examples:

* synthetic GeoTIFFs,
* region definitions,
* CSV files,
* JSON files.

### Integration fixtures

Small collections of files representing a complete processing state.

### Regression fixtures

Known datasets representing previously verified behavior or known defects.

Fixtures shall be version-controlled where practical and should remain small enough to keep test execution efficient.

---

## 8. Test Isolation and Temporary Data

Automated tests shall not modify production project data.

Tests requiring filesystem operations shall use temporary directories or explicitly isolated test directories.

In particular, normal test execution shall not modify:

```text
data/
output/
build/
logs/
```

unless a test explicitly creates an isolated equivalent of these structures in a temporary location.

Tests of cleanup operations shall verify that files outside the intended temporary scope remain untouched.

---

## 9. External Dependencies

The following external dependencies shall normally be isolated from the regular test suite:

* NSIDC remote archives,
* network access,
* GitHub,
* GitHub Pages,
* external web services.

Mocking or controlled fixtures should be used where the behavior of an external service needs to be tested.

Dedicated integration tests may test external interactions separately.

---

## 10. Test Level Selection Guidelines

Not every behavior requires all test levels.

The following general rules apply:

| Situation                       | Preferred level                      |
| ------------------------------- | ------------------------------------ |
| Small deterministic calculation | Unit                                 |
| Scientific algorithm            | Unit + Component                     |
| Complete project component      | Component                            |
| Interaction between components  | Integration                          |
| Complete processing workflow    | E2E                                  |
| Previously fixed defect         | Regression at lowest suitable level  |
| External service interaction    | Component/Integration with isolation |
| Output schema validation        | Component/Integration                |
| Complete website build          | Integration/E2E                      |

Tests should generally be implemented at the **lowest level that can adequately verify the required behavior**.

Higher-level tests should be added where component interaction itself is part of the requirement.

---

## 11. Relationship to Project Components

The current implementation can be mapped to the test levels as follows:

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

`*` End-to-end coverage should normally use controlled or mocked external input rather than the live external service.

This table describes the intended testing responsibility. It does not imply that all listed tests already exist.

---

## 12. Test Priority

Not all components have the same testing priority.

The initial focus should be on functionality where an implementation error can directly change scientific results or persistent data.

Priority areas are therefore:

1. `RegionAnalyzer`
2. `TimeSeriesAnalyzer`
3. `ResultsManager`
4. `ReferenceBuilder`
5. incremental update behavior
6. output validation
7. visualization and website build
8. downloader and external-service integration

This prioritization does not replace the general testing strategy. It defines the recommended order for establishing the initial test suite.

---

## 13. Test Level Boundaries

The boundaries between test levels should remain clear.

A unit test should not become a disguised integration test simply because it is convenient to construct a large project object graph.

Likewise, an E2E test should not attempt to verify every mathematical intermediate value individually.

The intended separation is:

```text
Unit
  → Is this individual behavior mathematically/logically correct?

Component
  → Does this complete component behave correctly?

Integration
  → Do the components exchange and process data correctly?

E2E
  → Does the complete workflow produce the intended result?

Regression
  → Does previously verified behavior remain correct?
```

This separation is intended to keep the test suite understandable, maintainable and diagnostically useful.
