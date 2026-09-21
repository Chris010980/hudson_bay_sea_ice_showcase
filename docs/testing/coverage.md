# Test Coverage

## 1. Purpose

This document defines the code coverage strategy for the Hudson Bay Sea Ice Analysis project.

Code coverage is used as a quantitative indicator of how much of the implemented software is exercised by automated tests.

Coverage is an aid for identifying insufficiently tested code. It is not considered a direct measure of software quality or scientific correctness.

The coverage strategy complements the testing strategy defined in `test-strategy.md` and the test-level definitions in `test-levels.md`.

---

## 2. Coverage Objectives

The primary objectives are:

* identify relevant untested code,
* monitor test-suite growth,
* prevent significant regression in test coverage,
* identify critical components that require additional tests,
* provide a measurable quality criterion for CI.

Coverage shall be considered together with:

* test quality,
* scientific correctness,
* edge-case coverage,
* integration coverage,
* regression coverage,
* output validation.

A high coverage percentage shall not be considered sufficient evidence of correct scientific behavior.

---

## 3. Coverage Metrics

The project shall initially focus on the following coverage metrics.

### 3.1 Line coverage

Line coverage measures the proportion of executable source lines that are executed by the automated test suite.

Line coverage shall be the primary project-wide coverage metric.

---

### 3.2 Branch coverage

Branch coverage measures whether different logical branches of the implementation are exercised.

Branch coverage is particularly relevant for code containing:

* conditional processing,
* error handling,
* threshold logic,
* date-dependent behavior,
* optional configuration,
* alternative processing paths.

Branch coverage should be monitored in addition to line coverage where practical.

---

### 3.3 Component-level coverage

Coverage shall also be evaluated for critical scientific and data-processing components.

Particular attention shall be given to:

* `RegionAnalyzer`,
* `TimeSeriesAnalyzer`,
* `ResultsManager`,
* `ReferenceBuilder`,
* incremental update processing.

A high project-wide coverage value shall not compensate for very low coverage of a critical scientific component.

---

## 4. Initial Coverage Target

The initial project-wide target shall be:

> **At least 70 % line coverage.**

This value represents the initial minimum quality gate and is intended to establish a meaningful baseline rather than a final target.

The target shall be reviewed after the first substantial test implementation cycle.

Increasing the threshold shall be considered only after:

* the initial test structure is established,
* critical scientific components have meaningful coverage,
* integration tests are available,
* the project has sufficient experience with the coverage metric.

---

## 5. Critical Component Coverage

The project shall explicitly monitor coverage of critical components independently of the project-wide value.

The following components are considered particularly important because errors can directly affect scientific results or persistent data:

| Component            | Coverage priority |
| -------------------- | ----------------- |
| `RegionAnalyzer`     | High              |
| `TimeSeriesAnalyzer` | High              |
| `ResultsManager`     | High              |
| `ReferenceBuilder`   | High              |
| `update_pipeline.py` | High              |
| `NSIDCDownloader`    | Medium            |
| `TimeSeriesPlotter`  | Medium            |
| `SeaIcePlotter`      | Medium            |
| `build_pages.py`     | Medium            |

The exact component-specific thresholds shall be established after the initial test suite has been implemented and measured.

Until then, component coverage shall primarily be used as a diagnostic metric rather than as an independent blocking CI threshold.

---

## 6. What Coverage Does Not Measure

Code coverage does not establish:

* scientific correctness,
* correctness of expected numerical values,
* correctness of test assertions,
* completeness of edge-case testing,
* quality of test data,
* correctness of external data,
* performance,
* maintainability,
* reproducibility.

For example, a test that executes a threshold-crossing function without checking the resulting date provides coverage but little evidence of scientific correctness.

Tests shall therefore contain meaningful assertions.

---

## 7. Coverage and Scientific Testing

Scientific components require more than high execution coverage.

For scientifically relevant functionality, coverage shall be combined with explicit expected-result tests.

For example:

```text
Input data
    ↓
scientific calculation
    ↓
expected numerical result
```

should be tested directly.

Particular attention shall be given to:

* threshold boundaries,
* interpolation,
* persistence,
* seasonal boundaries,
* leap years,
* missing data,
* absolute versus relative coverage,
* climatology,
* anomalies,
* annual statistics.

A scientific component may therefore require additional tests even when its code coverage already exceeds the project-wide target.

---

## 8. Coverage and Regression Testing

Regression tests contribute to the overall coverage measurement.

When a defect is fixed, the corresponding regression test should ideally execute the previously defective code path.

Coverage reports can therefore help identify whether important historical defect paths remain exercised.

Removing a regression test solely because the affected code is no longer covered shall require consideration of whether the underlying behavior is still relevant.

---

## 9. Excluded Code

Some code may reasonably be excluded from coverage requirements.

Potential examples include:

* defensive branches that cannot reasonably be exercised,
* development-only code,
* explicitly unreachable compatibility code,
* `if __name__ == "__main__"` entry-point guards where appropriate.

Coverage exclusions shall be used sparingly.

Scientific processing logic, error handling and operational paths shall not be excluded merely to increase the reported coverage percentage.

Any non-obvious exclusion should be documented.

---

## 10. Coverage Measurement

Coverage shall be generated automatically using a dedicated coverage tool.

The intended tool is `coverage.py`, integrated with `pytest`.

The coverage process should produce:

* terminal summary,
* machine-readable result for CI,
* HTML report for detailed local analysis.

The exact command-line configuration shall be defined as part of the project's development and CI tooling.

---

## 11. CI Quality Gate

The CI pipeline shall enforce the initial project-wide minimum line coverage target.

The intended behavior is:

```text
tests
  ↓
coverage measurement
  ↓
coverage >= 70 %
      │
   ┌──┴──┐
   │     │
 pass   fail
```

A reduction below the defined minimum shall cause the corresponding CI quality gate to fail.

Coverage should therefore be treated as a regression-control mechanism as well as a development metric.

---

## 12. Coverage Trends

Coverage shall be monitored over time.

The objective is not to maximize the percentage indefinitely, but to prevent deterioration and ensure that newly introduced functionality is appropriately tested.

A lower coverage value may be acceptable temporarily when justified by substantial new functionality, provided that the corresponding tests are added as part of the same development work.

The project should avoid increasing coverage artificially through tests that merely execute code without verifying meaningful behavior.

---

## 13. Relationship to Test Levels

Coverage applies across all runtime test levels.

| Test level  | Contribution to coverage               |
| ----------- | -------------------------------------- |
| Unit        | Primary source of fast code coverage   |
| Component   | Important for complete component paths |
| Integration | Covers component interaction paths     |
| E2E         | Covers complete operational paths      |
| Regression  | Protects previously tested paths       |

Coverage shall therefore not be interpreted as an argument to replace higher-level tests with large numbers of unit tests.

---

## 14. Initial Implementation

The initial coverage implementation shall proceed in stages:

1. establish the test suite,
2. integrate `pytest` with coverage measurement,
3. generate a baseline coverage report,
4. identify untested critical paths,
5. add tests for scientifically important functionality,
6. establish the 70 % project-wide minimum,
7. monitor critical component coverage,
8. integrate the coverage gate into CI.

Component-specific coverage thresholds may be introduced after sufficient baseline data are available.

---

## 15. Review

The coverage strategy shall be reviewed after the first major testing cycle.

The review should consider:

* whether 70 % remains appropriate,
* whether branch coverage should become a formal quality gate,
* whether critical components require independent minimum thresholds,
* whether generated or infrastructure code requires separate treatment,
* whether the coverage report provides useful development feedback.

Coverage requirements shall evolve together with the test strategy and project scope.
