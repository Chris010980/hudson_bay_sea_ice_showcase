# CI Quality Gates — v0.1

## 1. Purpose

This document defines the automated quality checks intended for changes to the `hudson_bay_sea_ice` project.

Continuous Integration (CI) provides an automated and reproducible verification layer in addition to local development and manual review.

The purpose of the CI quality gates is to detect changes that:

* break existing functionality,
* violate defined coding standards,
* reduce test coverage,
* introduce static code-quality problems,
* produce invalid analysis outputs,
* break the website build,
* or otherwise violate defined project requirements.

CI checks support the development process but do not replace scientific review or engineering judgment.

The v0.1 document defines the intended quality-gate model. It does not imply that every described gate is already implemented.

---

## 2. Quality Gate Principle

A quality gate defines a condition that should be satisfied before a change is integrated into the stable project state.

The general principle is:

```text
Change
  ↓
Automated CI checks
  ↓
All mandatory gates passed
  ↓
Review / integration
  ↓
main
```

A failed mandatory quality gate should normally prevent integration until the underlying problem has been resolved or the expected behavior has deliberately changed and the corresponding tests or requirements have been updated.

Quality gates should provide objective and reproducible criteria wherever practical.

---

## 3. Scope

CI quality gates cover several areas:

1. test execution,
2. code coverage,
3. formatting and linting,
4. static analysis,
5. dependency and import consistency,
6. scientific and output validation,
7. website/build validation,
8. pipeline-level verification.

Not every check needs to be introduced as a mandatory gate immediately.

The project will progressively strengthen its CI quality gates as the automated test and quality infrastructure is established.

---

## 4. Current Development State

The project has been operated through an automated daily processing workflow.

This operational experience provides practical evidence that the current pipeline functions under its normal operating conditions.

However, operational success does not provide the same type of evidence as systematic automated testing.

The CI quality gates therefore form part of the transition from:

```text
practical operational verification
```

towards:

```text
systematic and reproducible automated verification
```

The existence of a documented quality gate does not imply that the corresponding verification is already fully implemented.

---

## 5. Gate Categories

The project distinguishes between the following gate categories.

### 5.1 Test Gate

The automated test suite must execute successfully.

The test gate should detect:

* failing unit tests,
* failing component tests,
* failing integration tests,
* failing regression tests,
* unexpected test errors.

A successful test run is a basic prerequisite for integration.

---

### 5.2 Coverage Gate

Code coverage is used as a quantitative indicator of how much implementation code is exercised by automated tests.

The initial project target is:

```text
Minimum line coverage: 70 %
```

Coverage should be measured together with the test suite.

Coverage is not considered a measure of scientific correctness by itself. A test suite with high coverage may still fail to verify important numerical or scientific behavior.

The detailed coverage policy is defined in `test-coverage.md`.

The 70% threshold is an initial project target and should become a mandatory gate only once the coverage infrastructure has been established and the baseline is meaningful.

---

## 6. Scientific Test Gate

Tests covering scientific calculations should verify expected behavior and numerical results.

Examples include:

* regional sea-ice coverage,
* absolute versus relative coverage,
* climatological statistics,
* anomalies,
* annual means,
* threshold crossings,
* event dates,
* threshold durations.

A test should not be considered sufficient merely because the relevant code path executes successfully.

Where an expected numerical result can be defined, the test should verify that result within an appropriate tolerance.

Scientific tests should also cover relevant boundary and edge cases.

---

## 7. Formatting Gate

Source code should conform to the project's automated formatting rules.

The formatting gate should detect formatting deviations that can be resolved automatically.

The formatter and its configuration should be defined centrally rather than differently across individual modules.

Formatting failures should normally be corrected before integration.

The exact formatter and configuration are part of the project's development tooling and may be introduced progressively.

---

## 8. Linting Gate

Static linting should identify common implementation problems and violations of project coding standards.

The linting gate may include checks for:

* unused imports,
* undefined names,
* unreachable or suspicious code,
* unnecessary constructs,
* inconsistent implementation patterns,
* selected style violations.

The exact rule set should be selected based on the project codebase rather than adopting an unnecessarily restrictive configuration.

The linting configuration should be version-controlled and executed consistently locally and in CI.

---

## 9. Static Type Checking

Static type checking should be introduced where it provides meaningful additional assurance.

The project uses type hints for public interfaces and important functions.

Type checking should initially focus on identifying genuine interface and data-flow errors rather than requiring complete typing of every existing implementation detail immediately.

A type-checking gate may therefore be introduced progressively.

The selected tool and strictness level should be documented in the project's development tooling.

---

## 10. Unused Code and Dependency Checks

The project should detect unnecessary or unused implementation elements where practical.

Relevant checks may include:

* unused imports,
* unused variables,
* unreachable declarations,
* unused functions or classes,
* unnecessary dependencies,
* inconsistent imports.

Static analysis should support maintainability without treating every potentially unused declaration as an automatic defect.

Findings that require human judgment should be reviewed rather than automatically removed.

---

## 11. Import and Architecture Checks

The project's architectural separation should be supported by automated checks where practical.

The current system is organized around components for:

```text
Data Acquisition
       ↓
Spatial Analysis
       ↓
Result Management
       ↓
Temporal Analysis
       ↓
Visualization
       ↓
Website Build
```

This is a conceptual dependency direction rather than a strict statement that every component depends exclusively on the preceding component.

Architecture checks should therefore focus on clearly defined boundaries rather than preventing all cross-component dependencies.

Such checks may be introduced after the current architecture and dependency boundaries have been sufficiently established.

---

## 12. Output Validation Gate

Important generated outputs should be validated automatically.

Validation should cover, where applicable:

### Analysis Results

* required files exist,
* required columns exist,
* expected data types are present,
* dates are valid,
* configured regions are present,
* duplicate `(date, region)` records are absent,
* values lie within expected ranges,
* required derived outputs are generated.

### Metadata

* `latest.json` is structurally valid,
* reported dates are consistent with generated results,
* required metadata fields exist.

### Website

* required HTML pages exist,
* required output resources exist,
* referenced local files exist,
* generated paths are consistent,
* the build contains the expected structure.

The exact validation rules should be developed together with the corresponding output-validation tests.

---

## 13. Pipeline / Integration Gate

Changes affecting the pipeline should be verified at an appropriate integration level.

Depending on the change, CI should verify relevant stages such as:

```text
download
   ↓
process
   ↓
plots
   ↓
build
```

The complete production data pipeline should not necessarily run against external NSIDC data for every code change.

Tests should use controlled fixtures or representative test data where practical.

A separate scheduled or extended workflow may verify the complete operational workflow.

This distinction prevents CI from becoming unnecessarily slow or dependent on external network availability for every development change.

---

## 14. Website Build Gate

Changes affecting the website or generated outputs should verify that the GitHub Pages build can be generated successfully.

At minimum, the build gate should detect:

* build failures,
* missing required pages,
* missing generated resources,
* invalid relative paths,
* missing output files expected by the website.

The build should remain self-contained and should not depend on files that are intentionally excluded from the deployment artifact.

The deployment artifact should represent the corresponding scientific output state.

---

## 15. Regression Gate

Known defects and previously verified scientific behavior should be protected by regression tests.

When a defect is fixed:

```text
Defect
  ↓
Fix
  ↓
Regression test
  ↓
CI
```

The regression test should remain part of the automated test suite unless the underlying behavior is intentionally changed.

Regression tests are particularly important for scientific algorithms where apparently small implementation changes may affect historical results.

---

## 16. Documentation Gate

Changes that modify documented behavior should update the corresponding documentation.

The CI system may initially verify only basic documentation properties, such as:

* required documentation files exist,
* documentation pages can be built,
* required generated resources are available.

More advanced documentation consistency checks may be introduced later.

The responsibility for determining whether a methodological or architectural change requires documentation remains with the developer and reviewer.

---

## 17. Security and Operational Safety Checks

CI should prevent accidental inclusion or execution of unsafe project artifacts where practical.

Relevant checks may include:

* preventing unintended secrets from being committed,
* validating repository-controlled scripts,
* ensuring destructive cleanup is limited to intended directories,
* avoiding accidental modification of persistent results,
* verifying that generated artifacts remain within their expected locations.

The project should not grant CI more permissions than necessary for its required tasks.

---

## 18. Quality Gate Levels

Not every check has the same importance.

The project distinguishes between:

### Mandatory Gates

Failure blocks integration.

Examples include:

* test suite failures,
* coverage below a defined mandatory threshold,
* required build failures,
* critical output-validation failures.

### Advisory Checks

Findings are reported but do not initially block integration.

Examples may include:

* non-critical static-analysis findings,
* incomplete type coverage,
* selected architectural warnings.

Advisory checks may become mandatory once the project has established a reliable baseline.

---

## 19. Initial Gate Set

The initial quality-gate strategy is introduced incrementally.

### v0.1

The v0.1 release documents the intended CI quality model but does not require the complete quality-gate infrastructure to be implemented.

The existing operational pipeline remains the baseline.

The development infrastructure should at minimum document:

* intended automated tests,
* coverage measurement,
* static checks,
* build validation,
* output validation,
* the distinction between mandatory and advisory checks.

### v0.2

The planned v0.2 quality baseline should introduce the first systematic mandatory gates.

The initial target is:

```text
pytest
   +
coverage
   +
formatting
   +
linting
   +
basic static analysis
   +
required build validation
```

Additional gates should be introduced once the corresponding checks are reliable and sufficiently tested.

---

## 20. CI and Local Development

CI checks should be reproducible locally wherever practical.

A developer should be able to run the relevant checks before pushing a change.

The local and CI environments should use:

* the supported Python version,
* the same dependency definitions,
* the same project configuration,
* the same quality-check tools.

CI should therefore confirm the result of local verification rather than provide an entirely different development environment.

---

## 21. Handling Exceptions

A quality gate may occasionally need to be bypassed or temporarily relaxed.

Such exceptions should be rare and justified.

Examples include:

* a known external-service outage,
* a temporary infrastructure problem,
* an intentionally staged migration of a quality check,
* a deliberately changed scientific expectation.

A temporary exception should not silently become permanent.

If a gate is intentionally disabled or relaxed, the reason and expected resolution should be documented where appropriate.

---

## 22. Quality Gates and Requirements Traceability

CI quality gates provide verification evidence for requirements.

The relationship is:

```text
Requirement
     ↓
Acceptance Criteria
     ↓
Implementation
     ↓
Test
     ↓
CI Quality Gate
     ↓
Verification
```

Not every requirement is verified by a single CI check.

For example:

```text
FR-10 Threshold Events
       │
       ├── unit tests
       ├── component tests
       └── regression tests
                │
                ▼
           Test Gate
```

Likewise:

```text
NFR-05 Testability
       │
       ├── pytest
       ├── coverage
       ├── test structure
       └── CI execution
```

The detailed requirement relationships are maintained in:

```text
docs/requirements/requirements-traceability.md
```

---

## 23. Quality Gates and Releases

A release should document the state of the quality infrastructure at the time of release.

For example, a release may distinguish between:

* requirements implemented,
* requirements systematically verified,
* coverage target achieved,
* static checks enabled,
* known quality limitations.

This prevents a release from being interpreted as having a level of automated verification that was not actually present.

The release tag identifies the exact source state to which the quality information applies.

---

## 24. Maintenance of Quality Gates

Quality gates should evolve with the project.

They should be reviewed when:

* the testing strategy changes,
* new test levels are introduced,
* coverage targets change,
* new static-analysis tools are adopted,
* the architecture changes,
* new output types are introduced,
* deployment behavior changes,
* significant defects reveal a missing verification mechanism.

Quality gates should remain aligned with the project's requirements and should not become a collection of checks that no longer provide meaningful assurance.

---

## 25. Summary

The CI quality-gate strategy follows the principle:

```text
Run the tests
      ↓
Measure coverage
      ↓
Check code quality
      ↓
Validate important outputs
      ↓
Validate the build
      ↓
Verify the result
```

The goal is not to maximize the number of automated checks.

The goal is to establish a small set of meaningful, reproducible quality gates that provide evidence that a change:

* preserves existing behavior,
* satisfies defined requirements,
* does not unintentionally alter scientific results,
* maintains code quality,
* produces valid outputs,
* and leaves the project in a stable state.
