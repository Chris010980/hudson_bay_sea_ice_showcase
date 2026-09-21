# Coding Standards

## 1. Purpose

This document defines the coding standards for the `hudson_bay_sea_ice` project.

The purpose is to establish a consistent and maintainable implementation style and to support:

* readability,
* maintainability,
* testability,
* scientific reproducibility,
* clear separation of responsibilities,
* consistent error handling and logging,
* reliable automation.

The standards apply to Python source code and, where applicable, to scripts and configuration directly supporting the Python application.

The standards describe project conventions rather than general Python language rules. Where no project-specific rule is defined, standard Python conventions should be followed.

---

## 2. General Principles

Code should favor:

* clarity over cleverness,
* explicit behavior over implicit assumptions,
* small and focused functions,
* clear interfaces,
* deterministic behavior,
* testability,
* meaningful names,
* minimal duplication.

Implementation decisions should support the current project architecture rather than introducing additional abstraction without a concrete need.

Code should not be made more complex solely for hypothetical future requirements.

---

## 3. Python Version

The project currently targets:

```text
Python 3.12
```

Code may therefore use language and standard-library features available in the supported Python version.

Compatibility with older Python versions is not a project requirement unless the supported platform specification is changed.

The supported Python version should be documented consistently in:

* project documentation,
* dependency configuration,
* CI configuration,
* and development setup instructions.

---

## 4. Formatting and Style

Python code should follow standard Python formatting conventions, primarily based on PEP 8.

The project should use an automated formatter rather than relying solely on manual formatting.

Formatting should be applied consistently across the source tree.

Examples of preferred practices include:

* four spaces for indentation,
* no tabs for indentation,
* readable line lengths,
* consistent spacing around operators,
* imports grouped consistently,
* no unnecessary trailing whitespace.

Formatting should not be manually customized on a file-by-file basis without a project-level reason.

The exact formatter and configuration are defined by the project's development tooling.

---

## 5. Naming

Names should communicate their purpose and domain meaning.

### 5.1 Variables and functions

Use `snake_case`:

```python
start_date
reference_summary
calculate_threshold_events()
```

Avoid unnecessarily abbreviated names:

```python
# Preferred
reference_summary

# Avoid
ref_sum
```

Common scientific or domain-specific abbreviations may be used where they are established and unambiguous.

### 5.2 Classes

Use `PascalCase`:

```python
RegionAnalyzer
ResultsManager
TimeSeriesAnalyzer
NSIDCDownloader
```

### 5.3 Constants

Module-level constants should use uppercase `snake_case`:

```python
DEFAULT_RESULTS
DEFAULT_LOG_FILE
THRESHOLDS
```

### 5.4 Boolean values

Boolean variables and arguments should use names that clearly indicate a condition or state:

```python
keep_data
show_plot
has_results
is_processed
```

---

## 6. Type Hints

Type hints should be used for public functions, methods, and interfaces where they improve clarity and static analysis.

New code should use modern Python typing syntax where supported by Python 3.12.

For example:

```python
def load_results(path: Path) -> pd.DataFrame:
    ...
```

Return types should be specified for functions and methods unless there is a clear reason not to do so.

Types should describe the actual interface rather than merely satisfying a static checker.

Type hints should not be used to introduce unnecessary complexity into simple local code.

---

## 7. Functions and Methods

Functions and methods should have one clear responsibility.

A function that performs several logically independent operations should normally be split into smaller functions when doing so improves:

* readability,
* testability,
* error handling,
* reuse,
* or separation of responsibilities.

Functions should avoid hidden side effects where practical.

For example, a calculation function should preferably not also modify unrelated files or global state.

Functions that intentionally perform side effects should make this clear through their name, documentation, or surrounding interface.

---

## 8. Classes and Responsibilities

Classes should represent a coherent responsibility within the project architecture.

The existing architectural separation should be preserved.

For example:

* `NSIDCDownloader` handles external data acquisition and local raw-data management.
* `ReferenceBuilder` prepares static spatial reference data.
* `RegionAnalyzer` performs daily spatial analysis.
* `ResultsManager` manages persistent daily results.
* `TimeSeriesAnalyzer` performs temporal and climatological analysis.
* Plotter classes generate visualizations.
* Pipeline modules orchestrate processing stages.

A class should not gradually become a general-purpose container for unrelated functionality.

Changes that introduce substantial overlap between components should be reviewed against the architecture before implementation.

---

## 9. Separation of Computation and Side Effects

Where practical, scientific calculations should be separated from filesystem, network, plotting, and other external side effects.

This separation improves testability and makes scientific calculations easier to verify independently.

For example:

```text
Input data
    ↓
calculation
    ↓
result
```

should preferably be separable from:

```text
download file
write CSV
create figure
```

This is particularly important for scientific calculations such as:

* regional coverage,
* climatological statistics,
* anomalies,
* annual means,
* threshold crossings,
* event durations.

Pure or predominantly computational functions should be preferred where practical, but the architecture should not be artificially complicated merely to achieve complete purity.

---

## 10. Scientific Parameters

Scientific parameters must not be hidden in arbitrary implementation details.

Parameters that affect scientific results should be:

* clearly named,
* documented,
* given an identifiable default where applicable,
* distinguishable from purely technical parameters.

Examples include:

* pixel detection threshold,
* seasonal event thresholds,
* event persistence,
* climatology period,
* interpolation limits,
* moving-average window.

Different concepts must remain conceptually distinct.

In particular, the following must not be conflated:

1. pixel detection threshold used for binary/absolute coverage,
2. seasonal thresholds used for break-up and freeze-up detection,
3. persistence required for an event crossing,
4. moving-average window used as a visualization aid.

Changes to scientific parameters should be traceable through version control and documented where they affect the interpretation of existing results.

---

## 11. Units and Domain Meaning

Values representing physical quantities should have an unambiguous unit and meaning.

Where the unit is not obvious from the variable name or surrounding interface, it should be documented explicitly.

Examples include:

```text
km²
%
days
date
```

Variables should distinguish between quantities that have different scientific meanings even if they use the same physical unit.

For example, absolute and relative sea-ice coverage should not be represented by ambiguously named variables.

---

## 12. Data Handling

Data transformations should preserve the intended meaning of the source data.

Code handling external or scientific data should explicitly account for:

* missing values,
* invalid values,
* expected data ranges,
* date handling,
* coordinate/reference systems,
* units,
* special product codes.

Magic numbers should be avoided when they represent scientific or domain-specific meanings.

For example, a threshold such as:

```python
150
```

should not appear repeatedly without indicating what the value represents.

Domain constants should preferably have a descriptive name and a documented meaning.

---

## 13. Error Handling

Errors should be handled at the level where meaningful action can be taken.

Code should not silently suppress unexpected errors.

Broad exception handling such as:

```python
except Exception:
    pass
```

should not be used.

If an exception is intentionally caught, the code should:

* handle the condition appropriately,
* log relevant information where appropriate,
* preserve enough context for diagnosis,
* avoid hiding unrelated failures.

Pipeline-level orchestration may catch errors to allow controlled handling of individual inputs, provided that the failure remains visible and the resulting state is unambiguous.

---

## 14. Logging

The project uses Python's `logging` framework.

Logging should be preferred over direct `print()` statements for operational information.

Messages should provide useful context, particularly for:

* pipeline stages,
* input files,
* dates,
* processing decisions,
* skipped data,
* warnings,
* errors,
* output generation.

Logging should describe what happened and, where useful, why.

Example:

```python
logger.info("Skipping %s: already processed.", analyzer.date)
```

rather than:

```python
print("skip")
```

Debug-level logging may be used for detailed diagnostic information that would otherwise make normal pipeline output unnecessarily verbose.

Logging configuration belongs to the application configuration rather than being independently configured by individual components.

---

## 15. File and Path Handling

Filesystem paths should use `pathlib.Path`.

Hard-coded platform-specific path syntax should be avoided.

Project paths should preferably be derived from the centralized project path configuration rather than reconstructed independently in multiple modules.

Temporary data, persistent analysis results, generated visualizations, and website build artifacts should remain in their defined project locations.

Code should not silently write generated files into source directories unless this is explicitly part of the project structure.

---

## 16. External Data and Network Access

Network access should be isolated to components responsible for external data acquisition.

Scientific analysis and visualization components should operate on locally available data rather than performing implicit network access.

External data should be treated as potentially incomplete or invalid.

Acquisition code should therefore validate basic assumptions before passing data to downstream processing.

Network failures should result in informative errors or controlled pipeline behavior rather than silent failure.

---

## 17. Documentation and Docstrings

Public modules, classes, functions, and methods should have documentation where their purpose or behavior is not obvious.

Docstrings should explain:

* purpose,
* important parameters,
* return values where useful,
* important side effects,
* relevant scientific meaning or assumptions.

Docstrings should not merely repeat the function name.

Scientific algorithms should document assumptions that are necessary to understand or reproduce the calculation.

Documentation should be updated when behavior changes.

---

## 18. Comments

Comments should explain **why** code behaves in a particular way rather than simply repeating **what** the code does.

Preferred:

```python
# Do not bridge longer gaps because missing observations must
# remain distinguishable from interpolated values.
```

Avoid comments such as:

```python
# Add one to the index.
index += 1
```

Comments should be kept current. Obsolete comments should be removed rather than retained for historical context.

---

## 19. Imports and Dependencies

Imports should be explicit and organized consistently.

Unused imports should not remain in the codebase.

Duplicate imports should be avoided.

A dependency should only be introduced when it provides meaningful functionality that justifies the additional maintenance and reproducibility cost.

Standard-library functionality should be preferred where it provides an adequate solution.

Dependency versions and supported versions are managed separately through the project's dependency configuration.

---

## 20. Testing Considerations

Code should be written so that important behavior can be tested independently.

New non-trivial functions and methods should normally be accompanied by appropriate automated tests.

Scientific calculations should be tested using known expected results rather than merely checking that the code executes successfully.

Tests should cover relevant:

* normal cases,
* boundary conditions,
* invalid inputs,
* missing data,
* special cases,
* regression cases.

The complete testing strategy is defined in:

```text
docs/development/tests/testing-strategy.md
```

The different test levels are defined in:

```text
docs/development/tests/test-levels.md
```

---

## 21. Scientific Reproducibility

Code affecting scientific results should be deterministic unless non-deterministic behavior is explicitly required.

Scientific behavior should not depend on:

* local machine state,
* uncontrolled random values,
* implicit current dates,
* undocumented configuration,
* unavailable external resources.

When behavior necessarily depends on external data or environment state, that dependency should be explicit and documented.

Changes to scientific algorithms should be traceable through version control and, where appropriate, reflected in the project documentation and test suite.

---

## 22. Generated and Temporary Files

Generated files should not be confused with source code.

In particular:

* raw downloaded GeoTIFF files are temporary working data,
* analysis results are persistent project outputs,
* plots are generated outputs,
* `build/` is a generated website artifact.

Generated or temporary files should only be committed when explicitly required by the project.

The distinction between source, temporary input data, persistent results, and generated deployment artifacts should be preserved.

---

## 23. Refactoring

Refactoring should preserve existing behavior unless a functional change is explicitly intended.

A refactoring should preferably:

* have a clearly defined purpose,
* remain limited to the relevant component,
* preserve scientific behavior,
* be supported by appropriate tests.

Refactoring and functional changes should not be unnecessarily mixed in the same change.

If a refactoring changes scientific behavior, it is no longer considered purely technical refactoring and should be documented and tested accordingly.

---

## 24. Automated Quality Checks

The project should progressively automate compliance with these standards.

Relevant checks may include:

* code formatting,
* linting,
* unused-code detection,
* import validation,
* static type checking,
* test execution,
* coverage measurement,
* output validation.

The exact tools, configurations, and mandatory checks are defined in the project's CI quality gates.

This document therefore defines the expected coding principles without duplicating the technical CI configuration.

---

## 25. Exceptions

Not every rule can be applied mechanically.

An exception may be appropriate when:

* the underlying library requires a different pattern,
* a scientific implementation requires a deliberate deviation,
* a performance consideration justifies a different approach,
* compatibility with an external interface requires it.

Exceptions should be intentional and documented where they would otherwise be unclear to future maintainers.

The goal of the coding standards is consistent, understandable, and maintainable code — not compliance for its own sake.
