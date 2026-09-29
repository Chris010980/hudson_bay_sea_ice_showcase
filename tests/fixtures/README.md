# Test Fixtures

This directory contains deterministic test data used by the project test suite.

The fixtures provide small, controlled inputs for testing spatial processing, scientific calculations, persistent analysis results, and temporal analysis without relying on production data or external services.

## Purpose

Test fixtures provide known inputs with predictable outputs.

They are used to:

* isolate tests from production data,
* avoid dependencies on NSIDC or other external services,
* keep scientific tests deterministic,
* provide small datasets that are fast to process,
* support reproducible assertions,
* and provide reusable inputs for future component and integration tests.

Fixtures should represent the structure and relevant characteristics of production data where this is useful for testing, but they must remain independent of the actual production datasets.

## Fixture Categories

The current fixture structure is:

```text
tests/
└── fixtures/
    ├── analysis/
    │   └── daily_observations.csv
    ├── config/
    │   └── test_regions.json
    └── README.md
```

In addition to these static fixtures, some tests use dynamically created fixtures such as temporary directories and synthetic raster files.

### Analysis Fixtures

`analysis/daily_observations.csv` contains a small synthetic dataset representing daily regional sea-ice analysis results.

The structure follows the schema of the production `ice_coverage_summary.csv` output:

* region
* date
* water pixel and area information
* absolute and relative ice area
* absolute and relative coverage
* missing-pixel information

The dataset contains a small number of regions and dates with controlled values.

**Intended use:**

* testing CSV loading,
* testing persistent analysis results,
* testing date handling,
* testing `ResultsManager`,
* testing temporal processing,
* and providing deterministic input for future integration tests.

This fixture does not represent real Hudson Bay observations.

### Configuration Fixtures

`config/test_regions.json` contains synthetic region definitions following the structure of the production region configuration.

The regions are intentionally small and independent of the real Hudson Bay regions.

**Intended use:**

* testing configuration loading,
* testing region handling,
* testing spatial component behavior,
* and providing controlled input for spatial integration tests.

The fixture must remain independent of `src/config/regions.json`.

### Synthetic Raster Fixtures

Synthetic raster data is created dynamically by the pytest fixture `synthetic_raster`.

The raster is intentionally small and contains controlled sea-ice concentration values, including values representing relevant special cases used by the analysis code.

The raster metadata is explicitly defined, including:

* raster dimensions,
* data type,
* CRS,
* pixel size,
* and geotransform.

**Intended use:**

* testing raster handling,
* testing spatial processing,
* testing sea-ice concentration thresholds,
* testing invalid/special values,
* and future `RegionAnalyzer` component tests.

The synthetic raster must never depend on an NSIDC GeoTIFF.

### Temporary Filesystem Fixtures

The `test_environment` fixture creates an isolated temporary directory structure for tests.

The environment currently provides:

```text
root/
├── data/
├── output/
└── build/
```

The directories are created below pytest's temporary test directory.

**Intended use:**

* testing file creation and output handling,
* testing components that require a data/output directory structure,
* testing build-related operations,
* and isolating filesystem operations from the repository.

Tests must use this temporary environment instead of writing test output into the project's production directories.

## Intended Test Levels

Fixtures are primarily intended for the following test levels.

| Fixture              | Unit | Component | Integration | E2E | Regression |
| -------------------- | ---: | --------: | ----------: | --: | ---------: |
| Temporary filesystem |    — |         ✓ |           ✓ |   ✓ |          — |
| Synthetic raster     |    — |         ✓ |           ✓ |   — |          ✓ |
| Test regions         |    — |         ✓ |           ✓ |   — |          ✓ |
| Daily observations   |    — |         ✓ |           ✓ |   — |          ✓ |

The table describes the intended use of the fixtures. A fixture may be reused at several test levels when this provides a controlled and meaningful test.

Unit tests should generally prefer small in-memory values when no filesystem or external representation is required. Static fixtures become useful when the behavior being tested depends on the corresponding file format or data structure.

## Deterministic Data

Fixtures must be deterministic.

A test using the same fixture and the same code should receive the same input on every test run.

Therefore fixtures should:

* use explicitly defined values,
* avoid random data unless a fixed random seed is part of the test,
* avoid current dates and times,
* avoid external data sources,
* avoid network requests,
* avoid environment-dependent values,
* and avoid dependencies on the production dataset.

Synthetic values should be selected so that important scientific or processing behavior can be asserted explicitly.

For example, the daily observation fixture contains controlled coverage values rather than copied observations from the production dataset. This makes expected results straightforward to calculate and verify.

## Isolation Requirements

Tests using fixtures must remain isolated from production data and production outputs.

In particular:

* tests must not modify `data/`,
* tests must not modify `output/`,
* tests must not modify `build/`,
* tests must not modify `src/config/`,
* and tests must not depend on files generated by a previous test.

Filesystem-based tests should use pytest's temporary directories, such as the `test_environment` fixture, whenever they need to create or modify files.

Static fixtures under `tests/fixtures/` are test inputs and must be treated as read-only by tests.

If a test needs to modify fixture data, it should first copy the fixture into a temporary test directory.

## External-Service Independence

The regular fixture-based test suite must not require access to external services.

In particular, tests using these fixtures must not require:

* NSIDC,
* network access,
* external APIs,
* remote datasets,
* or production infrastructure.

The downloader and other external-service integrations can be tested separately using mocks, controlled responses, or dedicated integration tests.

The purpose of the reusable fixtures is to provide a stable local basis for testing the processing logic independently of those external dependencies.

## Reusing Fixtures

Fixtures should be reused whenever several tests require the same type of controlled input.

Shared pytest fixtures are defined in `tests/conftest.py`. Static fixture files are exposed through pytest fixtures rather than hard-coding paths in individual tests.

Future tests should therefore prefer existing fixtures before creating duplicate test data.

For example:

* use `daily_observations_csv` for tests requiring the standard synthetic daily-analysis CSV,
* use `test_regions_json` for tests requiring the synthetic region configuration,
* use `synthetic_raster` for tests requiring a controlled GeoTIFF,
* and use `test_environment` for tests requiring isolated filesystem paths.

A new fixture should be introduced when existing fixtures cannot represent the required test case clearly.

New fixtures should remain small and focused. A fixture should contain only the data required to exercise the behavior being tested.

## Extending the Fixture Set

Additional fixtures may be added as the test suite grows.

Potential future categories include:

* time-series datasets specifically designed for interpolation and climatology tests,
* threshold-event datasets with known break-up and freeze-up dates,
* reference summaries,
* generated `latest.json` data,
* and controlled visualization inputs.

Such fixtures should follow the same principles:

1. deterministic,
2. small,
3. self-contained,
4. independent of external services,
5. isolated from production data,
6. and documented together with their intended test use.

The fixture set should grow together with the test suite rather than attempting to reproduce the complete production dataset.
