# Non-Functional Requirements

This document defines the non-functional requirements of the Hudson Bay Sea Ice Analysis project.

## NFR-01 – Scientific Correctness

The system shall implement the documented scientific methodology consistently.

Scientific calculations shall use explicitly defined:

* input data,
* spatial reference data,
* thresholds,
* interpolation rules,
* climatological periods,
* statistical methods,
* analysis parameters.

Changes to scientific methodology shall be documented and traceable.

---

## NFR-02 – Data Integrity

Persistent analysis data shall not be unintentionally overwritten or lost during incremental processing.

The system shall ensure that:

* existing historical observations are preserved,
* duplicate observations for the same `(date, region)` combination are not created,
* new observations are appended or otherwise incorporated without duplicating existing observations,
* persistent CSV and JSON files remain structurally valid after processing.

A processing failure shall not intentionally result in a corrupted persistent result dataset.

---

## NFR-03 – Reliability

The pipeline shall handle expected operational conditions without manual intervention where possible.

In particular, it shall correctly handle:

* already up-to-date datasets,
* initially empty datasets,
* missing input observations,
* incomplete temporal data,
* invalid or unusable input files,
* processing failures of individual observations.

A failure affecting an individual input observation shall be reported clearly and shall not silently produce invalid scientific results.

---

## NFR-04 – Maintainability

The source code shall be structured into clearly defined components with responsibilities that can be understood and tested independently.

New functionality shall follow the existing project structure and coding conventions.

Non-trivial functions and methods shall be sufficiently small and focused to permit isolated testing where practical.

Duplicated logic shall be avoided where a shared implementation can be used without reducing clarity.

---

## NFR-05 – Testability and Quality Assurance

The project shall use automated tests to verify the correctness of individual components and their interactions.

As an initial quality target:

* new non-trivial functions and methods shall normally be accompanied by appropriate unit tests;
* scientifically relevant calculations shall have explicit tests for expected results and relevant edge cases;
* important component interfaces shall be covered by component or integration tests;
* the project shall initially target a minimum overall **70% line coverage**.

The coverage threshold shall be evaluated after the first development and testing cycles and may be revised based on the observed distribution and importance of tested code.

Coverage shall be treated as a quality indicator and not as the sole measure of test quality.

---

## NFR-06 – Static Code Quality

Static analysis shall be used to identify relevant code-quality issues before changes are integrated into the stable codebase.

The initial static-analysis toolchain shall be evaluated during the quality-assurance phase.

The evaluation shall consider, where appropriate:

* formatting and linting,
* type checking,
* unused-code detection,
* import and architectural dependency checks.

Specific tools and mandatory thresholds shall be defined after this evaluation.

---

## NFR-07 – Performance

A normal daily incremental update shall complete within approximately **2–3 minutes** under the expected execution environment and data volume.

Performance measurements shall be evaluated using representative update scenarios rather than empty or artificially small datasets.

Performance optimization shall not compromise scientific correctness or data integrity.

---

## NFR-08 – Reproducibility

The analysis shall be reproducible for defined input data, software versions, configuration and analysis parameters.

The project shall provide sufficient information to identify the conditions under which a result was generated, including where applicable:

* Python version,
* software/code version,
* dependency versions,
* reference dataset,
* analysis parameters,
* relevant configuration,
* documented analysis methodology.

The project's dependency specification shall be maintained so that the required Python environment can be recreated.

Bit-for-bit reproducibility across arbitrary environments is not currently required.

---

## NFR-09 – Version and Methodology Traceability

Software, dependencies, reference data and relevant analysis parameters shall be identifiable for generated results.

The project shall use:

* Git history and/or tags for software versions,
* dependency specifications for the Python environment,
* documented configuration for analysis parameters,
* reference metadata for generated reference data,
* project documentation for scientific methodology.

The concrete mechanism for storing result-generation metadata shall be defined during implementation.

---

## NFR-10 – Observability and Logging

The pipeline shall provide sufficient logging to determine the operational status and outcome of a processing run.

The default CI execution shall use a concise logging level that reports relevant progress, warnings and errors without producing unnecessarily large logs.

A more detailed logging level, such as `DEBUG`, shall remain available for diagnosis and troubleshooting.

Important failures shall be reported explicitly and shall not be hidden by reduced logging.

---

## NFR-11 – Pipeline Success and Operational Consistency

A successful pipeline run shall satisfy the corresponding functional success criteria defined in the Functional Requirements.

For an update with new observations, the pipeline shall successfully complete the required processing stages and produce valid updated outputs.

For an update without new observations, the pipeline shall terminate successfully without modifying existing analysis results, plots or the website.

The individual stages shall provide sufficient status information to identify where a failed pipeline run stopped.

---

## NFR-12 – Automated Output Validation

Persistent machine-readable outputs shall be validated automatically after processing.

At minimum, the validation shall cover the generated CSV and JSON files used by subsequent analysis, plotting and website generation.

Validation shall check, where applicable:

* required fields/columns,
* expected data types,
* valid dates,
* valid region identifiers,
* absence of duplicate `(date, region)` observations,
* validity of required numerical values,
* expected JSON structure.

Output validation shall be part of the automated quality-assurance process.

---

## NFR-13 – Configurability of Analysis Parameters

Analysis parameters that materially affect scientific or visualization results shall not be unnecessarily hard-coded.

At minimum, the following parameters shall be configurable:

* moving-average window,
* threshold-event persistence duration.

Other parameters may become configurable as the scientific methodology is further developed, including:

* interpolation maximum gap,
* pixel detection threshold,
* seasonal event thresholds,
* climatological reference period.

Configuration mechanisms shall preserve reproducibility by making the parameter values used for a result identifiable.

---

## NFR-14 – Extensibility

The architecture shall support the future addition of analysis regions and sea-ice-related analysis methods without fundamental restructuring of the existing processing pipeline.

The design should allow future extensions such as:

* interactive selection of analysis regions,
* additional regional datasets,
* sea-ice thickness analysis,
* sea-ice volume analysis,
* additional analysis and visualization methods.

Future functionality does not need to be implemented as part of the current project scope.

---

## NFR-15 – Platform Support

The officially supported development and execution environment shall be:

* Python 3.12,
* Linux/Ubuntu.

The project may work on other operating systems such as Windows and macOS, but cross-platform compatibility is currently not a verified requirement.

Platform-specific assumptions shall nevertheless be avoided where this can be achieved without unnecessary complexity.

---

## NFR-16 – Website Quality

The generated public website shall provide a consistent and functional presentation of the current project results.

Generated plots and machine-readable result data used by the website shall correspond to the same analysis state.

The website build shall not contain references to missing generated resources.

The website shall remain unchanged when an update produces no new observations.

---

## NFR-17 – Documentation

The project shall document the relevant scientific methodology, software usage and pipeline operation sufficiently to allow the project to be understood and reproduced by another technically competent user.

Documentation shall cover, where applicable:

* project scope,
* scientific methodology,
* data sources,
* analysis regions,
* processing pipeline,
* configuration,
* command-line usage,
* generated outputs,
* website generation,
* relevant limitations and assumptions.

---

## NFR-18 – Security and Operational Safety

The pipeline shall not require unnecessary privileges for normal execution.

Downloaded external data shall be treated as untrusted input and shall be validated sufficiently before being incorporated into persistent analysis results.

The system shall avoid destructive operations on persistent analysis results during normal incremental updates.

Temporary data cleanup shall not remove persistent analysis results or website source files.
