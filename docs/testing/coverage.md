# Test Coverage

## 1. Purpose

This document defines the code coverage strategy for the `hudson_bay_sea_ice` project.

Code coverage is used as a quantitative indicator of how much of the implemented software is exercised by automated tests.

Coverage is primarily a diagnostic and regression-control metric. It is not considered a direct measure of software quality, scientific correctness or test effectiveness.

The coverage strategy complements the testing principles defined in `test-strategy.md` and the test-level definitions in `test-levels.md`.

The requirements described in this document define the **v0.1 coverage strategy and target state**. They do not imply that all described coverage mechanisms are already implemented.

---

## 2. Coverage Objectives

The primary objectives of code coverage measurement are to:

* identify relevant untested code,
* monitor growth of the automated test suite,
* detect significant reductions in test coverage,
* identify critical components requiring additional tests,
* provide a measurable quality indicator for CI.

Coverage shall always be considered together with:

* test quality,
* scientific correctness,
* edge-case coverage,
* integration coverage,
* regression coverage,
* output validation.

A high coverage percentage shall not be considered sufficient evidence that the implemented scientific algorithms are correct.

---

## 3. Coverage Metrics

### 3.1 Line Coverage

Line coverage measures the proportion of executable source lines that are executed by the automated test suite.

Line coverage is the primary project-wide coverage metric for v0.1.

It provides a simple and reproducible measure for monitoring whether relevant parts of the implementation are exercised by tests.

---

### 3.2 Branch Coverage

Branch coverage measures whether alternative logical paths through the implementation are exercised.

It is particularly relevant for code containing:

* conditional processing,
* validation and error handling,
* threshold logic,
* date-dependent behavior,
* optional configuration,
* alternative processing paths.

Branch coverage is considered a complementary diagnostic metric in v0.1. It is not initially defined as a blocking project-wide CI threshold.

---

### 3.3 Component-Level Coverage

Coverage should also be evaluated for components whose behavior can directly affect scientific results or persistent project data.

Particular attention should be given to:

* `RegionAnalyzer`,
* `TimeSeriesAnalyzer`,
* `ResultsManager`,
* `ReferenceBuilder`,
* `update_pipeline.py`.

A high project-wide coverage value shall not compensate for insufficient testing of a critical scientific component.

---

## 4. Initial Coverage Target

The initial project-wide target for v0.1 is:

> **At least 70 % line coverage**

The 70 % value represents an initial minimum target rather than a final project-wide coverage objective.

It is intended to establish a measurable baseline after the automated test suite has been expanded and coverage measurement has been integrated.

The target should be reviewed after the first substantial testing cycle.

Increasing the threshold should only be considered after:

* the basic test structure is established,
* critical scientific components have meaningful coverage,
* integration tests are available,
* coverage results have been evaluated over several development cycles.

---

## 5. Critical Component Coverage

The project shall monitor coverage of critical components independently of the project-wide value.

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

The exact component-specific minimum thresholds are not fixed in v0.1.

Until sufficient baseline data are available, component coverage is primarily a diagnostic metric and is not an independent blocking CI threshold.

---

## 6. What Coverage Does Not Measure

Code coverage does not establish:

* scientific correctness,
* correctness of numerical results,
* correctness of test assertions,
* completeness of edge-case testing,
* quality or representativeness of test data,
* correctness of external data,
* performance,
* maintainability,
* reproducibility.

For example, a test may execute a threshold-crossing function while failing to verify whether the calculated event date is scientifically correct.

Such a test contributes to coverage but provides limited evidence of behavioral correctness.

Tests shall therefore contain meaningful assertions that verify expected behavior or expected results.

---

## 7. Coverage and Scientific Testing

Scientific components require more than high execution coverage.

Coverage shall therefore be combined with explicit expected-result tests.

A scientifically relevant test should, where practical, establish a controlled relationship of the form:

```text
controlled input
       ↓
scientific calculation
       ↓
expected result
```

Particular attention should be given to:

* concentration thresholds,
* absolute versus relative coverage,
* missing-data handling,
* interpolation,
* persistence requirements,
* threshold crossing,
* seasonal boundaries,
* leap years,
* climatology,
* anomalies,
* annual statistics.

For numerical algorithms, tests should preferably use small deterministic datasets for which the expected result can be calculated independently.

A component may therefore require additional tests even when its measured code coverage already exceeds the project-wide target.

---

## 8. Coverage and Regression Testing

Regression tests contribute to the overall coverage measurement.

When a defect is corrected, a corresponding regression test should, where practical, execute the previously defective code path and verify the corrected behavior.

Coverage reports can therefore help determine whether important historical defect paths remain exercised.

Regression tests should not be removed merely because their corresponding code path currently has high coverage. Their purpose is to protect previously verified behavior.

---

## 9. Excluded Code

Coverage exclusions shall be used sparingly.

Potential exclusions include:

* explicitly unreachable compatibility code,
* development-only code,
* defensive paths that cannot reasonably be exercised,
* appropriate `if __name__ == "__main__"` entry-point guards.

Scientific processing logic, validation logic and operational pipeline paths shall not be excluded merely to increase the reported coverage percentage.

Non-obvious exclusions should be documented in the coverage configuration or project documentation.

---

## 10. Coverage Measurement

Coverage should be generated automatically using `coverage.py` together with `pytest`.

The intended coverage workflow is:

```text
pytest
   ↓
coverage measurement
   ↓
coverage report
```

The coverage process should provide:

* a terminal summary for local development,
* a machine-readable result for CI,
* an HTML report for detailed investigation.

The exact command-line configuration and CI integration are implementation details of the project tooling and may evolve independently of this methodological document.

---

## 11. CI Quality Gate

The project intends to establish a project-wide minimum line-coverage quality gate of 70 %.

The intended future CI behavior is:

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

A measured coverage below the configured minimum should cause the corresponding CI quality gate to fail.

This mechanism is intended as a regression-control measure.

For v0.1, this requirement represents the **target CI behavior** and should not be interpreted as evidence that the coverage gate is already fully implemented.

---

## 12. Coverage Trends

Coverage should be monitored over time.

The objective is not to maximize the percentage indefinitely, but to:

* prevent significant deterioration,
* ensure that new functionality is appropriately tested,
* identify components that remain insufficiently tested.

Temporary reductions may be acceptable when substantial new functionality is introduced, provided that the corresponding tests are added as part of the same development work.

Artificially increasing coverage through tests that merely execute code without verifying meaningful behavior should be avoided.

---

## 13. Relationship to Test Levels

Coverage is collected across the complete automated test suite.

| Test level  | Contribution to coverage             |
| ----------- | ------------------------------------ |
| Unit        | Primary source of fast code coverage |
| Component   | Exercises complete component paths   |
| Integration | Exercises interaction paths          |
| E2E         | Exercises complete operational paths |
| Regression  | Protects previously verified paths   |

Coverage shall not be interpreted as a reason to replace higher-level tests with large numbers of unit tests.

Different test levels provide different types of evidence, while coverage only measures which executable code paths were exercised.

---

## 14. Initial Implementation

The v0.1 coverage implementation should proceed incrementally:

1. establish and maintain the automated test suite,
2. integrate `pytest` with coverage measurement,
3. generate an initial baseline coverage report,
4. identify untested critical paths,
5. add tests for scientifically important functionality,
6. establish the 70 % project-wide minimum,
7. monitor critical component coverage,
8. integrate the coverage threshold into CI.

Component-specific thresholds may be introduced later when sufficient baseline data are available.

---

## 15. Review

The coverage strategy should be reviewed after the first major testing cycle.

The review should consider:

* whether 70 % remains an appropriate minimum,
* whether branch coverage should become a formal quality gate,
* whether critical components require independent thresholds,
* whether generated or infrastructure code requires separate treatment,
* whether the coverage reports provide useful development feedback.

Coverage requirements should evolve together with the test strategy and the scope of the project.
