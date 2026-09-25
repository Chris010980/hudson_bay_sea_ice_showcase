# Requirements Traceability

## 1. Purpose

This document defines how requirements in the `hudson_bay_sea_ice` project are traced to their implementation, verification, and release state.

The purpose of requirements traceability is to establish a structured connection between:

* the project scope,
* functional and non-functional requirements,
* the architectural components affected by those requirements,
* their implementation,
* acceptance criteria,
* verification activities,
* documentation,
* and project releases.

Traceability provides a means of determining not only whether a requirement is implemented, but also whether sufficient evidence exists to demonstrate that the implemented behavior satisfies the requirement.

It also helps identify gaps such as:

* requirements without an identifiable implementation,
* implemented behavior without a documented requirement,
* requirements without appropriate verification,
* verification that covers only part of a requirement,
* tests that do not clearly correspond to expected behavior,
* or implementation behavior that is not adequately represented by the current requirements.

The traceability matrix maintained in this document provides the central overview of these relationships.

---

## 2. Traceability Model

The project uses the following general relationship:

```text
Project Scope
     │
     ▼
Requirement
     │
     ▼
Acceptance Criteria
     │
     ▼
Architecture / Component
     │
     ▼
Implementation
     │
     ▼
Verification
     │
     ├── Automated Test
     ├── Regression Test
     ├── Output Validation
     ├── Static Analysis
     ├── Documentation Review
     ├── Reproducibility Check
     └── Operational Evidence
     │
     ▼
Verification Result
     │
     ▼
Release / Version
```

The model describes a logical relationship rather than a mandatory one-to-one mapping.

A requirement may:

* be implemented by several components,
* affect several architectural areas,
* require several verification mechanisms,
* be verified at different test levels,
* or contain several independently verifiable aspects.

Likewise, one test or verification activity may provide evidence for more than one requirement where the tested behavior genuinely overlaps.

Traceability should therefore represent meaningful relationships rather than artificially enforcing one-to-one mappings.

---

## 3. Requirement Identification

Requirements are identified using stable identifiers.

Functional requirements use the prefix:

```text
FR-XX
```

Non-functional requirements use:

```text
NFR-XX
```

Examples:

```text
FR-04
FR-10
NFR-05
NFR-12
```

The authoritative definitions are maintained in:

```text
functional-requirements.md
non-functional-requirements.md
```

The project scope is defined separately in:

```text
scope.md
```

Requirement identifiers should remain stable once they are referenced by implementation, tests, documentation, or release records.

If a requirement changes substantially in meaning, the change should be documented explicitly rather than silently reusing the identifier for unrelated behavior.

---

## 4. Traceability Levels

Traceability is maintained at several levels.

### 4.1 Scope to Requirements

The project scope defines the system boundary and distinguishes:

* currently supported functionality,
* current data and scientific scope,
* operational scope,
* current quality and verification scope,
* explicit non-goals,
* and potential future extensions.

Requirements formalize the capabilities and quality conditions within that scope.

The relationship is therefore:

```text
Project Scope
     │
     ├── Functional Requirements
     │
     └── Non-Functional Requirements
```

A topic listed only as a future extension or non-goal should not automatically be treated as a current requirement.

---

### 4.2 Requirements to Architecture

Each relevant requirement should be associated with one or more architectural components or areas.

For example:

```text
FR-10 Threshold Events
        │
        ▼
TimeSeriesAnalyzer
```

Cross-cutting requirements may involve several components.

For example, pipeline consistency may involve:

```text
NFR-11 Pipeline Consistency
        │
        ├── main.py
        ├── update_pipeline.py
        ├── process_data.py
        ├── generate_plots.py
        └── build_pages.py
```

The architectural documentation describes these relationships in more detail.

---

### 4.3 Requirements to Implementation

Where practical, the affected implementation should be identifiable.

Implementation references should normally identify:

* a module,
* a class,
* a function,
* a configuration area,
* or a clearly defined filesystem/output area.

For example:

```text
FR-10
  │
  ▼
TimeSeriesAnalyzer
  │
  ├── threshold-event calculation
  ├── threshold crossing detection
  └── persistence handling
```

Line numbers are intentionally not used as stable traceability identifiers because they change frequently during development.

Implementation references describe the current implementation and should not be interpreted as a target architecture.

---

### 4.4 Requirements to Acceptance Criteria

Requirements should be expressed in a way that allows their fulfillment to be verified.

Acceptance criteria describe observable conditions indicating that the requirement has been fulfilled.

For example, FR-10 may require that:

* the defined thresholds are evaluated,
* the defined persistence period is respected,
* missing calendar days are not incorrectly bridged,
* break-up and freeze-up use the defined seasonal windows,
* threshold crossings are determined according to the documented method,
* and resulting event information is stored in the expected output.

Acceptance criteria should describe expected behavior rather than implementation details where possible.

---

### 4.5 Requirements to Verification

Verification provides evidence that the implemented behavior satisfies the requirement.

Depending on the requirement, verification may be provided by:

* unit tests,
* component tests,
* integration tests,
* end-to-end tests,
* regression tests,
* automated output validation,
* static analysis,
* documentation review,
* reproducibility procedures,
* or operational evidence.

The appropriate verification mechanism depends on the nature and risk of the requirement.

Operational evidence demonstrates that functionality has been exercised successfully, but it is not automatically equivalent to systematic automated verification.

This distinction is particularly important for the current v0.1 baseline.

---

### 4.6 Requirements to Tests

Tests provide automated verification evidence for requirements.

A requirement may be covered by several tests at different levels:

```text
FR-10
 │
 ├── Unit test
 │      threshold crossing
 │
 ├── Component test
 │      complete event calculation
 │
 └── Regression test
        previously validated event result
```

The appropriate test level depends on the requirement and its associated risk.

The testing strategy is defined in:

```text
docs/testing/test-strategy.md
```

The available test levels are described in:

```text
docs/testing/test-levels.md
```

Coverage is described in:

```text
docs/testing/coverage.md
```

CI quality gates are described in:

```text
docs/testing/ci-quality-gates.md
```

Test references should be added to the traceability matrix as the automated test suite is expanded.

---

### 4.7 Requirements to Documentation

Some requirements require documentation evidence in addition to executable implementation.

This is particularly relevant for:

* scientific methodology,
* supported data products,
* configuration,
* CLI behavior,
* project scope,
* reproducibility,
* operational behavior,
* limitations,
* and development procedures.

The existence of executable code therefore does not by itself establish complete fulfillment of a documentation-related requirement.

---

### 4.8 Requirements to Releases

Traceability should allow a requirement to be associated with the project version in which it is implemented and, where applicable, the version in which systematic verification is established.

For example:

```text
FR-04

implementation baseline: v0.1
verification extended:   v0.2
```

or:

```text
FR-10

implementation baseline: v0.1
automated verification: v0.2
```

This distinction is useful because functionality may already exist in an operational baseline while its formal verification is introduced later.

---

## 5. Traceability Status

The following status categories are used:

| Status               | Meaning                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------ |
| `defined`            | Requirement is documented, but implementation status has not yet been established.         |
| `implemented`        | Relevant functionality exists in the current implementation.                               |
| `verified`           | Appropriate verification evidence has been established for the relevant requirement.       |
| `partially verified` | Meaningful verification evidence exists, but relevant verification coverage is incomplete. |
| `planned`            | The requirement or corresponding capability is intentionally deferred to a future version. |
| `not applicable`     | The requirement does not apply to the current implementation.                              |

The status describes the **current state**, not necessarily the version in which the functionality was first introduced.

A requirement may therefore be:

```text
implemented
```

while still lacking systematic automated verification.

`partially verified` should only be used when meaningful verification evidence already exists.

Where functionality exists but no meaningful verification beyond implementation and operational use has yet been established, `implemented` is preferable to `partially verified`.

The version column separately records the relevant implementation or verification baseline.

---

## 6. Current Baseline

The current v0.1 baseline represents an implemented and operationally exercised version of the system.

The pipeline has been executed repeatedly in its intended operational workflow, including data acquisition, spatial processing, temporal analysis, visualization, and website generation. This provides practical operational evidence for the implemented functionality.

However, operational execution is not considered equivalent to systematic automated verification. The repository contains pytest-based test infrastructure, but the currently existing tests originate from an earlier implementation phase and no longer match the current software interfaces. They are therefore not considered valid automated verification of the current implementation.

Consequently, requirements shall distinguish between:

* **implemented** – the required functionality exists in the current implementation,
* **operationally exercised** – the functionality has been exercised through the operational pipeline,
* **automatically verified** – the functionality is covered by valid automated tests or automated validation,
* **partially implemented / verified** – only part of the requirement is currently fulfilled,
* **planned** – the requirement is intentionally assigned to a later development phase.

The v0.1 baseline therefore provides substantial implementation and operational evidence, but does not claim comprehensive automated verification.

---

## 7. Functional Requirements Traceability Matrix

The following matrix records the current implementation baseline and the available verification evidence.

The matrix deliberately distinguishes implementation from verification.

| ID    | Requirement                          | Component(s)                                              | Current Implementation                                                                                                                  | Acceptance / Verification                                                                                   | Current Evidence                                                                                     | Status             | Version |
| ----- | ------------------------------------ | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------ | ------- |
| FR-01 | Sea-ice data acquisition             | `NSIDCDownloader`, download stage                         | Incremental synchronization with configured NSIDC source; missing observations and equivalent product versions are handled              | Required observations can be identified and acquired incrementally                                          | Regular pipeline operation; downloader tests to be added                                             | implemented        | v0.1    |
| FR-02 | Temporary data management            | `NSIDCDownloader`, update pipeline                        | GeoTIFF observations are stored temporarily and can be removed after processing; `--keep-data` controls cleanup                         | Temporary data is removed or retained according to the execution option                                     | Regular update operation; cleanup tests to be added                                                  | implemented        | v0.1    |
| FR-03 | Spatial reference data preparation   | `ReferenceBuilder`                                        | Fixed `src/config/reference.tif`; reusable regional masks and reference summary under `output/reference/`                               | Reference masks are available, reusable, and derived from the fixed reference dataset                       | Regular pipeline operation; reference-builder tests to be added                                      | implemented        | v0.1    |
| FR-04 | Daily regional sea-ice analysis      | `RegionAnalyzer`                                          | Regional absolute and relative sea-ice coverage calculated from daily GeoTIFF observations                                              | Coverage follows the documented concentration threshold, pixel area, region masks, and coverage definitions | Operational results; scientific unit/component tests outstanding                                     | implemented        | v0.1    |
| FR-05 | Persistent analysis results          | `ResultsManager`                                          | Historical daily regional results stored in CSV; duplicate `(date, region)` entries are removed on save; latest state stored separately | Results remain identifiable by date and region and are persisted without unintended duplicate records       | Existing implementation and generated outputs; persistence tests outstanding                         | implemented        | v0.1    |
| FR-06 | Time-series preparation              | `TimeSeriesAnalyzer`                                      | Calendar reindexing, interpolation, and centered moving-average processing are implemented                                              | Calendar continuity and maximum interpolation-gap behavior follow the defined method                        | Existing generated time-series products; scientific tests outstanding                                | implemented        | v0.1    |
| FR-07 | Climatological analysis              | `TimeSeriesAnalyzer`                                      | 1981–2010 daily climatology with mean, standard deviation, minimum, and maximum is generated                                            | Climatological statistics correspond to the defined reference period and calendar treatment                 | Generated climatological products; scientific tests outstanding                                      | implemented        | v0.1    |
| FR-08 | Anomaly analysis                     | `TimeSeriesAnalyzer`                                      | Absolute and relative anomalies are calculated from climatological means                                                                | Anomalies equal observation minus corresponding climatological mean and retain the defined units            | Generated analysis products; scientific tests outstanding                                            | implemented        | v0.1    |
| FR-09 | Annual analysis                      | `TimeSeriesAnalyzer`                                      | Complete calendar years are identified and annual means are generated                                                                   | Annual statistics use complete years according to the defined calendar-year criterion                       | Generated yearly products; scientific tests outstanding                                              | implemented        | v0.1    |
| FR-10 | Seasonal threshold events            | `TimeSeriesAnalyzer`                                      | Break-up, freeze-up, threshold crossing and persistence logic implemented for 10 %, 50 %, and 90 % thresholds                           | Seasonal windows, persistence, crossing logic and stored event results satisfy the documented definitions   | Generated event products and operational use; scientific unit/component/regression tests outstanding | implemented        | v0.1    |
| FR-11 | Scientific visualization             | `SeaIcePlotter`, `TimeSeriesPlotter`, `generate_plots.py` | Spatial, regional, temporal, anomaly, threshold, polar and annual visualizations are implemented                                        | Required plot types can be generated from current analysis products                                         | Existing GeoTIFF visualization tests and generated figures; broader plot tests outstanding           | partially verified | v0.1    |
| FR-12 | Pipeline execution and orchestration | `main.py`, `update_pipeline.py`                           | Individual stages and an incremental end-to-end update are available                                                                    | Required processing sequence produces consistent downstream products when new observations are processed    | Regular pipeline operation; integration/E2E tests outstanding                                        | implemented        | v0.1    |
| FR-13 | Website generation                   | `build_pages.py`                                          | Static website source from `docs/` is combined with generated `output/` into `build/`                                                   | Generated deployment artifact contains the current website and required analysis products                   | Successful local/CI builds; automated build validation outstanding                                   | implemented        | v0.1    |
| FR-14 | Command-line interface               | `main.py` and stage entry points                          | Pipeline stages expose documented command-line options for logging, processing, plotting, updating and building                         | Supported options produce the documented stage behavior                                                     | Operational CLI use; CLI tests outstanding                                                           | implemented        | v0.1    |

The matrix represents the **current implementation baseline**.

It does not imply that every requirement has already achieved complete automated verification.

---

## 8. Non-Functional Requirements Traceability Matrix

Non-functional requirements are traced using the same general model, but their verification often spans multiple components and verification mechanisms.

| ID     | Requirement                          | Relevant Area                                                | Current Implementation / Evidence                                                                                 | Verification Mechanism                                                        | Status             | Version |
| ------ | ------------------------------------ | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------ | ------- |
| NFR-01 | Scientific correctness               | Analysis / methodology                                       | Scientific methods are documented and implemented across spatial and temporal analysis components                 | Scientific unit tests, component tests, result validation, methodology review | partially verified | v0.1    |
| NFR-02 | Data integrity                       | Downloader / processing / `ResultsManager`                   | Persistent derived results, duplicate handling, temporary raw-data separation and reference masks exist           | Input/output validation, persistence tests, integrity checks                  | partially verified | v0.1    |
| NFR-03 | Reliability and error handling       | Downloader / processing / pipeline                           | Individual components contain exception handling and logging; processing failures are recorded                    | Error-path tests, integration tests, controlled failure tests                 | partially verified | v0.1    |
| NFR-04 | Maintainability                      | Architecture / source tree                                   | Acquisition, analysis, visualization, update and website-build responsibilities are separated into modules        | Code review, static analysis, architectural review                            | partially verified | v0.1    |
| NFR-05 | Testability and quality assurance    | `tests/`, pytest                                             | pytest is available and an initial GeoTIFF visualization test module exists                                       | Expanded test suite, coverage, CI execution and quality gates                 | partially verified | v0.1    |
| NFR-06 | Static code quality                  | Source tree / CI                                             | No dedicated formatting, linting or type-checking configuration is currently established                          | Automated static-analysis checks                                              | defined            | v0.1    |
| NFR-07 | Performance                          | Incremental pipeline / reference processing                  | Incremental processing and reusable reference masks reduce unnecessary work                                       | Representative benchmarks and performance measurements                        | defined            | v0.1    |
| NFR-08 | Reproducibility                      | Source / configuration / data / dependencies                 | Methodology, fixed reference data, source code and dependency requirements are documented                         | Reproducibility procedure using defined inputs and environment                | partially verified | v0.1    |
| NFR-09 | Version and methodology traceability | Git / requirements / methodology / releases                  | Source, requirements and methodology are version controlled and documented                                        | Release review and change traceability                                        | partially verified | v0.1    |
| NFR-10 | Logging and diagnostics              | `logging_config.py`, pipeline stages                         | Central logging configuration and persistent log file are implemented                                             | Configuration review and operational inspection                               | implemented        | v0.1    |
| NFR-11 | Pipeline operational consistency     | `main.py`, `update_pipeline.py`, processing, plotting, build | Defined update sequence connects acquisition, processing, visualization and website generation                    | Integration/E2E tests and output consistency validation                       | partially verified | v0.1    |
| NFR-12 | Automated output validation          | Analysis / visualization / website                           | No independent systematic output-validation layer currently exists                                                | Automated schema, range, file, consistency and website checks                 | defined            | v0.1    |
| NFR-13 | Configurability                      | Configuration / analysis / CLI                               | CLI configuration exists, while some scientific parameters remain implementation-defined or hard-coded            | Configuration tests and review of parameter handling                          | partially verified | v0.1    |
| NFR-14 | Extensibility                        | Architecture / components                                    | Functional areas are separated into dedicated modules and configuration areas                                     | Architectural review and extension tests                                      | partially verified | v0.1    |
| NFR-15 | Platform and environment             | Python / dependencies / CI                                   | Python 3.12 and `ubuntu-latest` are explicitly defined in CI; dependencies are declared in `requirements.txt`     | CI execution and environment documentation                                    | implemented        | v0.1    |
| NFR-16 | Website quality                      | `docs/`, `build/`, GitHub Pages                              | Website source and generated deployment artifact are separated; build combines documentation and current outputs  | Build validation, resource validation and deployment checks                   | partially verified | v0.1    |
| NFR-17 | Documentation                        | Documentation tree                                           | Scope, requirements, architecture, methodology, development and testing documentation are established             | Documentation review                                                          | implemented        | v0.1    |
| NFR-18 | Security and operational safety      | Downloader / cleanup / build / CI                            | External downloads and destructive filesystem operations are identifiable and restricted to project-managed areas | Safety review, failure-path tests and destructive-operation tests             | partially verified | v0.1    |

The NFR matrix represents the current state of the project.

In particular, `defined` does not mean that the requirement is unimportant or postponed as a project feature. It means that the requirement is established, but the corresponding verification or quality mechanism is not yet sufficiently implemented.

---

## 9. Test Traceability

Test traceability links requirements to automated verification where valid tests exist.

The existing test files from the early development phase are not considered part of the valid v0.1 verification baseline because their tested interfaces no longer correspond to the current implementation.

In particular, tests that depend on obsolete functions or interfaces shall not be adapted solely to restore a passing test result. Such tests are treated as obsolete and are replaced by tests derived from the current software interfaces and requirements.

The v0.2 test strategy shall establish systematic automated verification for the current implementation, including:

* unit tests for critical scientific calculations,
* component tests for analysis and data-processing components,
* integration tests for interactions between pipeline stages,
* end-to-end tests for representative pipeline workflows,
* regression tests for established scientific results where appropriate,
* invalid-input and edge-case tests,
* visualization and output validation,
* and CI-based execution of the applicable test suite.

Until this test suite has been established, the absence of an automated test does not imply that the corresponding functionality is unimplemented. It indicates that the functionality currently lacks systematic automated verification.

---

## 10. Regression Traceability

Regression tests should be associated with the requirement, behavior, or defect that motivated them where practical.

A regression test should document:

* what previously failed,
* which behavior must remain stable,
* and which requirement is affected.

For example:

```text
FR-10
  │
  ▼
freeze-up event detection
  │
  ▼
regression case:
late break-up / early freeze-up
```

Regression testing is particularly important for scientific calculations because apparently small algorithmic changes may alter historical results.

Where an intentional methodological change changes previously generated results, the change should be documented as a scientific or implementation change rather than treated automatically as a regression.

---

## 11. Scientific Result Changes

When a code or methodology change intentionally modifies scientific results, the change should be traceable to:

1. the relevant requirement or methodological decision,
2. the affected implementation,
3. the tests or verification activities supporting the change,
4. the affected generated outputs,
5. and the project version containing the change.

Existing results should not automatically be treated as an immutable reference if the underlying scientific methodology has intentionally changed.

Instead, the traceability should distinguish:

```text
Previous implementation
        │
        ▼
Methodological / implementation change
        │
        ▼
New implementation
        │
        ▼
Updated expected results
```

This distinction is necessary to separate genuine regressions from intentional changes to the scientific method.

---

## 12. v0.1

The v0.1 baseline comprises the implemented and operationally exercised functionality documented by the current architecture, requirements, and methodology.

This includes:

* daily data acquisition,
* incremental processing,
* spatial reference preparation,
* regional sea-ice analysis,
* persistent daily results,
* temporal analysis,
* climatological and event-related analysis implemented in the current pipeline,
* generated scientific plots,
* automated website generation,
* and the GitHub Actions-based operational update workflow.

The v0.1 baseline is considered an operationally established implementation rather than a formally validated software release.

Systematic automated testing, output validation, static code-quality checks, and corresponding CI quality gates are part of v0.2.

## 13. v0.2

The v0.2 quality-assurance and formalization phase shall build on the existing v0.1 implementation.

Its primary goals include:

* establishing valid automated tests for the current implementation,
* covering critical scientific calculations and data transformations,
* adding integration and end-to-end verification,
* introducing regression and edge-case testing,
* adding automated output validation,
* introducing static code-quality checks,
* strengthening reproducibility and provenance information,
* and integrating the resulting quality checks into continuous integration.

The v0.2 work shall verify and formalize the existing functionality rather than redefining the v0.1 scientific baseline.

---

## 14. Maintenance

The traceability information should be updated when:

* a requirement is added or removed,
* a requirement changes meaning,
* implementation responsibility changes,
* a scientific method changes,
* a test is added or removed,
* a significant regression is identified,
* a verification mechanism is introduced or removed,
* a requirement becomes verified,
* functionality is deferred or becomes obsolete,
* or a release changes supported project behavior.

Traceability should be reviewed as part of significant releases.

Small implementation changes do not necessarily require changes to the matrix if the existing requirement-to-component relationship remains valid.

---

## 15. Relationship to Other Documentation

Requirements traceability connects the project scope, requirements, architecture, implementation, methodology, testing and releases.

The overall relationship is:

```text
                         Project Scope
                              │
                              ▼
                  Functional / Non-Functional
                       Requirements
                              │
                              ▼
                         Architecture
                              │
                              ▼
                        Implementation
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        Methodology       Testing         Operations
             │                │                │
             │                ├── Test Strategy│
             │                ├── Test Levels  │
             │                ├── Coverage     │
             │                └── CI Gates     │
             │                                 │
             └────────────────┬────────────────┘
                              ▼
                        Verification
                              │
                              ▼
                           Release
```

The relevant documentation includes:

* `scope.md` — project boundaries, current scope, non-goals and future extensions
* `functional-requirements.md` — functional requirements
* `non-functional-requirements.md` — quality and operational requirements
* `../architecture/overview.md` — architectural structure and system boundaries
* `../architecture/components.md` — component responsibilities
* `../architecture/data-flow.md` — data and processing flow
* `../methodology/data-and-inputs.md` — input data and reference data methodology
* `../methodology/spatial-processing.md` — spatial processing methodology
* `../methodology/coverage-metrics.md` — coverage definitions and calculations
* `../methodology/temporal-analysis.md` — temporal and climatological analysis
* `../methodology/event-detection.md` — seasonal event detection
* `../testing/test-strategy.md` — testing strategy
* `../testing/test-levels.md` — test levels
* `../testing/coverage.md` — test coverage
* `../testing/ci-quality-gates.md` — automated quality gates

Requirements traceability therefore acts as the connection between **scope, requirements, architecture, implementation, methodology, verification and releases**. It does not replace these documents; it provides the relationship between them.
