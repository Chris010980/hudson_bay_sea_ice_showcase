# Non-Functional Requirements

This document defines the non-functional requirements for the Hudson Bay Sea Ice Analysis project.

The requirements describe quality attributes and engineering constraints of the system. They are independent of the current implementation status. The current degree of fulfillment is assessed separately in the project quality and development documentation.

---

## NFR-01 – Scientific Correctness

The system shall implement and document the scientific methodology used for sea-ice analysis consistently and reproducibly.

The methodology shall explicitly define:

* input data and data product,
* spatial reference data,
* pixel interpretation,
* absolute and relative sea-ice coverage,
* pixel detection threshold,
* seasonal event thresholds,
* event persistence,
* interpolation rules,
* moving-average processing,
* climatology period,
* anomaly calculation,
* annual statistics,
* trend calculation.

Changes to scientifically relevant methods or parameters shall be documented and traceable.

Scientific calculations shall be covered by automated tests using defined expected results and relevant edge cases.

---

## NFR-02 – Data Integrity

The system shall preserve the integrity of persistent analysis results.

Persistent results shall:

* preserve previously processed historical observations,
* contain no duplicate `(date, region)` records,
* be deterministically sorted where applicable,
* use defined and consistent data types,
* contain valid values within their defined physical and numerical ranges,
* remain structurally valid after incremental updates.

Updates shall not unintentionally modify or delete previously valid historical results.

Output files shall be written in a manner that minimizes the risk of leaving corrupted persistent results after a failed operation.

---

## NFR-03 – Reliability and Error Handling

The system shall handle expected operational and data-related error conditions in a controlled manner.

This includes, where applicable:

* no new observations,
* empty input datasets,
* missing observations,
* incomplete time series,
* invalid or unusable input files,
* unavailable reference data,
* malformed external data,
* individual processing failures,
* invalid configuration,
* failed downloads,
* failed output generation.

Errors shall be logged with sufficient information to identify the affected processing step and input.

An error in one independent input observation shall not unnecessarily invalidate unrelated valid observations.

---

## NFR-04 – Maintainability

The software shall be structured into components with clearly defined responsibilities.

Components shall:

* have focused responsibilities,
* minimize unnecessary coupling,
* expose clear interfaces,
* avoid unnecessary duplication,
* be independently testable,
* use consistent naming and coding conventions.

Internal implementation details shall not unnecessarily be used as external component interfaces.

The architecture shall support further development without requiring unrelated components to be modified unnecessarily.

---

## NFR-05 – Testability and Quality Assurance

The system shall be covered by an automated testing strategy.

The test strategy shall include appropriate tests at multiple levels, including:

* unit tests,
* component tests,
* integration tests,
* end-to-end tests where appropriate,
* regression tests for established behavior.

New non-trivial functions and methods shall normally receive automated unit tests.

Scientific calculations shall have explicit tests for:

* expected results,
* boundary conditions,
* invalid inputs,
* relevant edge cases.

Important interfaces between components shall be tested at component or integration level.

The project shall define and monitor a minimum initial line-coverage target of **70 %**. Coverage shall be treated as a quality indicator and shall not be used as the sole measure of test quality.

The detailed test strategy is defined separately in the testing documentation.

---

## NFR-06 – Static Code Quality

The project shall use automated static quality checks.

The quality checks shall cover, as appropriate:

* code formatting,
* linting,
* unused imports and declarations,
* obvious code defects,
* type consistency,
* dependency/import structure,
* architectural constraints.

Static checks shall be executable automatically in the development and CI environments.

The concrete tools, configuration and quality gates shall be defined separately as part of the development and CI setup.

---

## NFR-07 – Performance

The system shall provide sufficient performance for its intended operational use.

For the normal daily incremental update, the expected total processing time shall be approximately **2–3 minutes** in the defined reference environment and for the expected data volume.

Performance measurements shall be based on representative processing scenarios.

Performance optimization shall not compromise scientific correctness, data integrity or reproducibility.

The reference environment and measurement procedure shall be documented when performance testing is introduced.

---

## NFR-08 – Reproducibility

A defined combination of:

* source code,
* Python version,
* dependencies,
* configuration,
* reference data,
* input data,
* scientific parameters

shall produce reproducible analysis results within the defined reproducibility scope.

The project shall document the Python version and dependency requirements.

Scientific parameters relevant to generated results shall be identifiable.

Exact bit-for-bit reproducibility across arbitrary environments is not required.

---

## NFR-09 – Version and Methodology Traceability

Scientific results shall be traceable to the software and methodology used to generate them.

The project shall maintain traceability through:

* version-controlled source code,
* Git history and/or release tags,
* dependency specifications,
* documented scientific methodology,
* relevant configuration and parameter definitions,
* reference-data information.

Where practical, generated result metadata shall identify the relevant software or methodology version.

Changes to scientific processing shall be distinguishable from changes that only affect presentation or infrastructure.

---

## NFR-10 – Logging

The system shall provide structured operational logging.

Logging shall:

* provide sufficient information to understand pipeline execution,
* identify important processing steps,
* report warnings and errors explicitly,
* support configurable log levels,
* support console logging,
* support file logging where required.

At minimum, `INFO` and `DEBUG` operation shall be supported.

CI execution shall provide concise but sufficient logs for diagnosing failed pipeline stages.

---

## NFR-11 – Pipeline Success and Operational Consistency

The pipeline shall execute its defined stages in a deterministic and documented order.

A successful update with new observations shall perform all required downstream processing stages, including:

1. data acquisition,
2. spatial analysis,
3. persistent result update,
4. temporal analysis,
5. visualization,
6. website build where applicable.

If no new observations are available, the update shall not modify persistent scientific results or regenerate outputs unnecessarily.

The responsibilities of the update pipeline and the website build stage shall be clearly defined.

A failed required stage shall result in an identifiable unsuccessful pipeline execution.

---

## NFR-12 – Automated Output Validation

Generated scientific outputs shall be automatically validated.

Validation shall check, where applicable:

* required files,
* required columns,
* data types,
* valid dates,
* valid region identifiers,
* duplicate records,
* numerical ranges,
* missing values,
* JSON structure,
* consistency between related output files.

Website build outputs shall additionally be checked for required resources and expected output structure.

Output validation shall be executable automatically as part of the testing or CI process.

---

## NFR-13 – Configurability

Scientifically relevant and operationally relevant parameters shall be configurable where appropriate.

This includes, at minimum, parameters such as:

* moving-average window,
* threshold-event persistence,
* interpolation limits where configurable.

The following parameters shall be treated as explicit scientific configuration candidates:

* pixel detection threshold,
* event thresholds,
* climatology period,
* interpolation limits,
* moving-average parameters.

Parameter values affecting scientific results shall not be hidden implicitly in unrelated implementation code.

The configuration mechanism shall preserve clear defaults and documented parameter meanings.

---

## NFR-14 – Extensibility

The system shall support future extensions without requiring fundamental restructuring of the existing processing pipeline.

Potential future extensions include:

* additional analysis regions,
* sea-ice thickness,
* sea-ice volume,
* additional data products,
* additional scientific analysis methods,
* interactive region selection,
* additional visualization types.

Future extensions shall not be considered implemented merely because the current architecture permits them.

---

## NFR-15 – Platform Support

The officially supported execution environment shall be:

* Python 3.12,
* Linux/Ubuntu.

The CI environment shall use a supported Python 3.12 environment.

Windows and macOS shall not be considered officially supported unless explicitly added to the project scope.

Platform-specific assumptions should be avoided where reasonably practical.

---

## NFR-16 – Website Quality

The generated GitHub Pages website shall represent the same analysis state as the corresponding generated scientific outputs.

The website shall:

* contain all required current pages,
* reference existing resources,
* contain the current generated plots,
* use the corresponding current analysis results,
* remain internally consistent after updates,
* be buildable automatically,
* be deployable as a self-contained artifact.

The build process shall not require a second manually maintained copy of generated scientific data.

If no new scientific data are available, the website content shall remain unchanged unless an explicit website-only change has been introduced.

---

## NFR-17 – Documentation

The project shall document:

* project scope,
* scientific methodology,
* data sources,
* regions,
* data flow,
* software architecture,
* pipeline stages,
* configuration,
* command-line interfaces,
* generated outputs,
* website structure,
* known limitations,
* testing strategy.

Documentation shall distinguish between:

* current implementation,
* defined requirements,
* future extensions.

Changes to requirements or scientific methodology shall be reflected in the corresponding documentation.

---

## NFR-18 – Security and Operational Safety

The system shall operate without requiring unnecessary privileges.

External input data shall be treated as untrusted input and validated before being used for scientific processing.

Destructive operations shall be restricted to their intended scope.

In particular:

* temporary raw data cleanup shall not remove persistent analysis results,
* website build cleanup shall not remove source data,
* persistent result files shall not be deleted as part of normal cleanup,
* CI operations shall operate only on the intended repository and build artifacts.

Operations with destructive effects shall be clearly identifiable and, where practical, protected by tests or explicit preconditions.
