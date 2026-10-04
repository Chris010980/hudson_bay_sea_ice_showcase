# Test Suite

This directory contains the automated test suite of the `hudson_bay_sea_ice` project.

The test structure follows the test model defined in `docs/testing/test-levels.md` and the general principles defined in `test-strategy.md`.

The project distinguishes between:

- unit tests
- component tests
- integration tests
- end-to-end tests
- regression testing

Regression testing is a cross-cutting activity rather than an independent technical test level. A regression test may therefore be implemented at unit, component, integration, or end-to-end level.

The current test infrastructure is established as part of **v0.2 – Test Foundation**. The test suite is being developed incrementally, starting with the scientific core and extending toward integration, end-to-end, and regression testing.

---

## Directory Structure

```text
tests/
├── fixtures/
│   ├── analysis/
│   ├── config/
│   └── README.md
├── fixture_tests/
├── unit/
├── component/
├── integration/
├── e2e/
└── regression/
```

Each directory has a distinct testing responsibility.

### `unit/`

Unit tests verify small, deterministic, and isolated pieces of functionality.

They should be:

- deterministic
- fast
- independent of external services
- independent of production data
- independent of the repository's persistent `data/` and `output/` directories

Typical candidates include:

- date handling
- scientific calculations
- time-series operations
- threshold logic
- validation and transformation logic

Unit tests should preferably operate on values or small controlled datasets supplied directly by the test.

The initial pytest smoke test is currently located here:

```text
tests/unit/test_smoke.py
```

The smoke test verifies that pytest can collect and execute a test successfully. It does not test scientific functionality.

### `fixture_tests/`

Fixture verification tests check the test infrastructure
itself: the shared pytest fixtures defined in
`tests/conftest.py` and the static fixture data below
`tests/fixtures/`.

They verify that:

- the shared fixtures provide the documented deterministic
  data,
- the isolated `test_environment` directories behave as
  specified.

`fixture_tests/` is an organizational directory, not a test
level of the test model. The tests exercise real files and
directories, but their subject is the test infrastructure
rather than a production component, so they are kept separate
from `component/`.

### `component/`

Component tests verify complete project components in a controlled environment.

Unlike unit tests, component tests may use:

- realistic file formats
- controlled raster data
- temporary directories
- multiple internal functions
- several processing steps of the same component

Potential components include:

- `RegionAnalyzer`
- `ReferenceBuilder`
- `ResultsManager`
- `TimeSeriesAnalyzer`
- `NSIDCDownloader`
- visualization components

Component tests should verify the behavior of a complete component rather than only individual helper functions.

External services such as NSIDC should not be required for the regular component test suite. External interactions should normally be mocked or represented by controlled fixtures.

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

The purpose is to verify data exchange and interaction between components, not to repeat every individual component assertion.

### `e2e/`

End-to-end tests verify complete user-relevant or pipeline-relevant workflows across multiple stages.

Relevant workflows include:

- complete processing of a controlled dataset
- incremental updates
- update processing when new observations are available
- behavior when no new observations are available
- generation of the website build

E2E tests should reproduce realistic pipeline behavior while avoiding unnecessary interaction with live external services.

Because E2E tests are comparatively expensive, they should remain limited and complement rather than replace lower-level tests.

### `regression/`

Regression testing protects previously verified behavior against unintended changes.

Regression testing is a **cross-cutting activity**, not an independent technical test level. A regression test may therefore also be a unit, component, integration, or E2E test.

Regression tests may cover:

- scientific edge cases
- previously identified defects
- data handling behavior
- pipeline behavior
- output consistency

Regression tests should be based on explicitly verified behavior rather than assumptions about how the system should behave.

---

## Test Naming Conventions

Test names should describe the behavior or property being verified.

Test functions should generally follow:

```text
test_<behavior_under_test>
```

Examples:

```text
test_calculates_relative_coverage
test_rejects_missing_pixels
test_interpolates_short_gaps
test_detects_persistent_threshold_crossing
```

Names should describe **what the test verifies**, rather than implementation details.

Avoid generic names such as:

```text
test_function_1
test_case_1
test_processing
```

A failed test should provide a useful first indication of the behavior that is affected.

Test files should generally follow:

```text
test_<subject>.py
```

Examples:

```text
test_smoke.py
test_raster_fixtures.py
test_data_fixtures.py
test_region_fixtures.py
```

The file name should identify the primary subject or purpose of the tests contained in the file.

---

## Fixture Conventions

Fixtures provide controlled inputs and reusable test environments.

Static fixture data is organized below:

```text
tests/
└── fixtures/
    ├── analysis/
    ├── config/
    └── README.md
```

Shared pytest fixtures are defined in:

```text
tests/conftest.py
```

The tests that verify the fixtures themselves are located in:

```text
tests/fixture_tests/

Fixture names should describe **what the test receives**, rather than how the fixture is implemented.

Examples include:

```text
test_environment
synthetic_raster
fixture_dir
daily_observations_csv
test_regions_json
```

Static fixture files should use descriptive names that indicate their content and purpose.

For example:

```text
tests/fixtures/analysis/daily_observations.csv
tests/fixtures/config/test_regions.json
```

Existing fixtures should be reused whenever they provide suitable controlled input.

A new fixture should be introduced when an existing fixture cannot represent the required test case clearly.

Fixtures should remain:

- small
- deterministic
- self-contained
- independent of external services
- independent of production data

The detailed fixture strategy is documented in:

```text
tests/fixtures/README.md
```

---

## Test Level Selection

New tests should generally be implemented at the **lowest test level that adequately verifies the behavior**.

Use the following guidelines:

| Test level | Use when |
| --- | --- |
| Unit | A function, method, or small piece of logic can be tested in isolation |
| Component | A complete project component needs to be verified in a controlled environment |
| Integration | Multiple components or processing stages need to be verified together |
| E2E | A complete user-relevant or pipeline-relevant workflow needs to be verified |
| Regression | Previously verified behavior needs protection against unintended changes |

Regression is not a separate technical level. Its appropriate implementation level depends on the behavior being protected.

For example, a deterministic scientific calculation should normally be tested as a unit test rather than through a complete pipeline execution.

Conversely, the interaction between `ReferenceBuilder`, `RegionAnalyzer`, and `ResultsManager` belongs at the integration level because the interaction between those components is part of the behavior being tested.

Higher-level tests should be added when the interaction or workflow itself is relevant.

The detailed responsibilities of each test level are defined in `test-levels.md`.

---

## Assertions

Assertions should verify the behavior described by the test name.

A test should preferably have a clear purpose rather than combining unrelated checks.

For example:

```text
test_calculates_relative_coverage
```

should primarily verify the calculation of relative coverage.

A separate test can verify:

```text
test_rejects_missing_pixels
```

This keeps individual tests focused and makes failures easier to interpret.

Use exact comparisons where the expected result is deterministic and exact.

For floating-point scientific calculations, use an appropriate numerical tolerance where exact equality is not guaranteed by the calculation.

Assertions should verify meaningful behavior rather than implementation details that are not part of the intended component behavior.

---

## Test Isolation

Tests must not modify the project's production data or analysis results.

Regular tests should not write to:

```text
data/
output/
build/
```

Tests should also avoid modifying production configuration files under:

```text
src/config/
```

Temporary directories and controlled test fixtures should be used instead.

The shared `test_environment` fixture provides an isolated temporary filesystem:

```text
root/
├── data/
├── output/
└── build/
```

Tests should use this fixture, or pytest's `tmp_path` fixture directly, whenever temporary filesystem operations are required.

Static fixtures below `tests/fixtures/` are test inputs and should be treated as read-only.

If a test needs to modify fixture data, the fixture should first be copied into a temporary test directory.

Tests must not depend on files created by another test. Each test should establish the state it requires through its own fixtures or setup.

---

## External Dependencies

The regular test suite should be independent of external services.

In particular, regular tests should not require:

- NSIDC data services
- network access
- external APIs
- GitHub
- GitHub Pages
- production infrastructure

Synthetic data, controlled fixtures, temporary directories, and mocked external interactions should be preferred.

Dedicated tests for external-service integration may be introduced separately when required. Such tests should not be required for normal deterministic test-suite execution.

---

## Deterministic Test Data

Test data should be deterministic.

A test using the same fixture and the same code should receive the same input on every test run.

Fixtures should therefore:

- use explicitly defined values
- avoid uncontrolled random data
- avoid current dates and times
- avoid external data sources
- avoid network requests
- avoid environment-dependent values
- avoid dependencies on the production dataset

Synthetic values should be selected so that relevant scientific or processing behavior can be asserted explicitly.

The test suite should prefer small, focused datasets over copies of complete production datasets.

---

## Test Development

The test suite is being developed incrementally during v0.2.

The intended development order is:

1. establish the pytest infrastructure
2. establish reusable deterministic fixtures
3. test the scientific core
4. test temporal analysis
5. test pipeline and component integration
6. test visualization and website generation
7. add end-to-end and regression coverage
8. integrate quality checks into CI

When adding a new test, consider:

1. What behavior is being protected?
2. What is the lowest test level that can adequately verify it?
3. Can an existing fixture be reused?
4. Does the test require temporary filesystem state?
5. Does the test introduce a dependency on an external service?
6. Are the expected results deterministic and explicitly defined?

Tests should follow the conventions documented in this file and the detailed test-level and fixture documentation.

---

## Current Status

The pytest infrastructure, the deterministic fixture
foundation, the scientific component suites, and the
integration suites are established (issues #18–#33). The
suite layout was reorganized in issue #76: fixture
verification tests moved to `tests/fixture_tests/`, the
plot-generation integration file was renamed
(`test_generate_plots.py`), and the unit-vs-component
review confirmed that all remaining `tests/component/`
files are genuine component tests. The suite currently
comprises 148 tests in 24 files:

```text
tests/
├── fixtures/
│   ├── analysis/
│   │   └── daily_observations.csv
│   ├── config/
│   │   └── test_regions.json
│   └── README.md
│
├── unit/
│   └── test_smoke.py
│
├── fixture_tests/
│   ├── test_data_fixtures.py
│   ├── test_filesystem_fixtures.py
│   ├── test_raster_fixtures.py
│   └── test_region_fixtures.py
│
├── component/
│   ├── test_nsidc_downloader.py
│   ├── test_reference_builder.py
│   ├── test_region_analyzer.py
│   ├── test_region_analyzer_validity.py
│   ├── test_results_manager.py
│   ├── test_sea_ice_map_plot.py
│   ├── test_timeseries_anomalies.py
│   ├── test_timeseries_calendar.py
│   ├── test_timeseries_climatology.py
│   ├── test_timeseries_event_window.py
│   ├── test_timeseries_moving_average.py
│   ├── test_timeseries_plotter.py
│   ├── test_timeseries_threshold_crossing.py
│   └── test_timeseries_yearly.py
│
├── integration/
│   ├── test_build_pages.py
│   ├── test_generate_plots.py
│   ├── test_spatial_processing_chain.py
│   ├── test_update_no_new_data.py
│   └── test_update_pipeline.py
│
├── conftest.py          # shared fixtures
├── Findings.md          # per-test findings and audit (#75)
└── vulture_whitelist.py # documented vulture exceptions
