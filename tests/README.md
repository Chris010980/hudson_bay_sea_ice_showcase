# Test Suite

This directory contains the automated test suite of the `hudson_bay_sea_ice` project.

The test structure follows the test levels defined for the project:

* unit tests
* component tests
* integration tests
* end-to-end tests
* regression tests

The current test infrastructure is established as part of **v0.2 – Test Foundation**. The test suite is being developed incrementally, starting with the scientific core and extending toward integration, end-to-end, and regression testing.

---

## Directory Structure

```text
tests/
├── unit/
├── component/
├── integration/
├── e2e/
└── regression/
```

Each directory has a distinct testing responsibility.

### `unit/`

Unit tests verify individual functions, methods, or small units of logic in isolation.

They should be:

* deterministic
* fast
* independent of external services
* independent of production data
* independent of the repository's persistent `data/` and `output/` directories

Typical candidates include:

* date handling
* scientific calculations
* time-series operations
* threshold logic
* validation and transformation logic

The initial pytest smoke test is currently located here:

```text
tests/unit/test_smoke.py
```

The smoke test verifies that pytest can collect and execute a test successfully. It does not test scientific functionality.

---

### `component/`

Component tests verify complete project components in a controlled environment.

Potential components include:

* `RegionAnalyzer`
* `ReferenceBuilder`
* `ResultsManager`
* `TimeSeriesAnalyzer`
* `NSIDCDownloader`
* visualization components

Component tests may use controlled fixtures such as:

* synthetic GeoTIFF files
* synthetic region definitions
* small CSV datasets
* JSON configuration data

External services such as NSIDC should not be required for the regular component test suite.

---

### `integration/`

Integration tests verify the interaction between multiple project components.

Relevant integration chains include:

```text
ReferenceBuilder
        ↓
RegionAnalyzer
        ↓
ResultsManager
```

and:

```text
persistent daily results
        ↓
TimeSeriesAnalyzer
```

Other integration areas include:

```text
analysis results
        ↓
visualization
```

and:

```text
docs + output
        ↓
build_pages
        ↓
build/
```

Integration tests should use controlled test environments and temporary directories rather than modifying the production dataset.

---

### `e2e/`

End-to-end tests verify complete workflows across multiple pipeline stages.

Relevant workflows include:

* complete processing of a controlled dataset
* incremental updates
* update processing when new observations are available
* behavior when no new observations are available
* generation of the website build

The E2E suite should reproduce realistic pipeline behavior while avoiding unnecessary interaction with live external services.

---

### `regression/`

Regression tests preserve verified behavior and protect against the reintroduction of known problems.

They may cover:

* scientific edge cases
* previously identified defects
* data handling behavior
* pipeline behavior
* output consistency

Regression tests should be based on explicitly verified behavior rather than assumptions about how the system should behave.

---

## Test Isolation

Tests must not modify the project's production data or analysis results.

In particular, regular tests should not write to:

```text
data/
output/
build/
```

Temporary directories and controlled test fixtures should be used instead.

External dependencies such as:

* NSIDC data services
* network access
* GitHub
* GitHub Pages

should be isolated from the regular test suite. Mocked services, synthetic data, or controlled fixtures should be preferred.

Dedicated external-service tests may be introduced separately if required.

---

## Test Development

The test suite is being developed incrementally during v0.2.

The intended development order is:

1. establish the pytest infrastructure
2. test the scientific core
3. test temporal analysis
4. test pipeline and component integration
5. test visualization and website generation
6. add end-to-end and regression coverage
7. integrate quality checks into CI

Tests should generally be implemented at the **lowest test level that adequately verifies the behavior**.

For example, a deterministic scientific calculation should normally be tested as a unit test rather than through a complete pipeline run.

---

## Current Status

The pytest infrastructure has been established.

Current contents:

```text
tests/
├── unit/
│   └── test_smoke.py
├── component/
├── integration/
├── e2e/
└── regression/
```

The smoke test currently verifies only that pytest can collect and execute a test.

Scientific and component-level tests are introduced in subsequent v0.2 issues.
