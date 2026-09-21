# Contribution Guide

## 1. Purpose

This document describes the development workflow for contributing changes to the `hudson_bay_sea_ice` project.

It defines the expected workflow from the initial idea or issue through implementation, verification, review, and integration into the stable `main` branch.

The contribution process is intended to ensure that changes are:

* clearly defined,
* limited to a coherent scope,
* reproducible,
* tested appropriately,
* documented where necessary,
* traceable through version control.

The workflow is deliberately lightweight and is intended to support the project's current development model without introducing unnecessary process overhead.

---

## 2. Before Starting a Change

Before implementing a change, the developer should determine:

* what problem or requirement is being addressed,
* whether the change is already covered by the documented project scope,
* which component or components are affected,
* whether the change affects scientific methodology,
* whether existing behavior must be preserved,
* which tests and documentation may need to be updated.

For larger changes, the relevant requirement, architectural component, or development task should be identifiable before implementation begins.

If the requested behavior is outside the current project scope, the scope should be reviewed before implementation rather than silently expanding the system.

---

## 3. Choose the Change Type

The change should be classified according to its primary purpose.

Typical categories are:

| Type       | Purpose                                                   |
| ---------- | --------------------------------------------------------- |
| `feature`  | New functionality                                         |
| `fix`      | Correction of existing behavior                           |
| `refactor` | Structural improvement without intended functional change |
| `docs`     | Documentation-only change                                 |

The corresponding branch naming convention is defined in:

```text id="p2h2s8"
docs/development/branching-strategy.md
```

Examples:

```text id="7z0v3b"
feature/anomaly-analysis
fix/threshold-event-detection
refactor/results-manager
docs/update-methodology
```

---

## 4. Create a Development Branch

New non-trivial changes should normally be developed on a separate branch based on the current `main` branch.

Before creating the branch, update the local repository:

```bash
git checkout main
git pull
```

Create the development branch:

```bash
git checkout -b feature/example-change
```

The branch should remain focused on one coherent change.

Unrelated modifications should not be added simply because they happen to be discovered during development.

---

## 5. Understand the Existing Implementation

Before modifying an existing component, the relevant implementation and its interfaces should be understood.

Depending on the change, this may include:

* reading the affected source module,
* inspecting related components,
* checking existing tests,
* checking relevant requirements,
* reviewing architecture and data-flow documentation,
* examining existing output or regression behavior.

Changes should preferably extend or modify the existing architecture rather than introducing parallel implementations of the same responsibility.

---

## 6. Implement the Change

Implementation should follow the coding standards defined in:

```text id="9td2v5"
docs/development/coding-standards.md
```

The implementation should remain focused on the intended change.

During implementation:

* avoid unrelated refactoring,
* preserve existing behavior unless a change is intended,
* use existing project interfaces where appropriate,
* avoid unnecessary duplication,
* keep scientific parameters explicit,
* add appropriate logging,
* handle expected failure conditions explicitly.

If the implementation changes scientific behavior, the relevant methodology and requirements should be reviewed as part of the change.

---

## 7. Tests

New or modified behavior should be accompanied by appropriate automated tests.

The required test level depends on the type and scope of the change.

Relevant test levels include:

* unit tests,
* component tests,
* integration tests,
* end-to-end tests,
* regression tests.

The testing strategy and test-level definitions are documented in:

```text id="p6y0lo"
docs/development/tests/testing-strategy.md
docs/development/tests/test-levels.md
```

For scientific calculations, tests should verify expected results rather than merely checking that execution succeeds.

Relevant boundary conditions, invalid inputs, missing data, and previously fixed defects should be covered where applicable.

A change should not deliberately reduce test coverage without a documented reason.

---

## 8. Scientific Changes

Changes affecting scientific results require particular care.

Examples include changes to:

* sea-ice coverage calculations,
* pixel detection thresholds,
* spatial masks,
* interpolation,
* climatological calculations,
* anomaly calculations,
* annual statistics,
* threshold-event detection,
* event persistence,
* trend calculations.

For such changes, the developer should identify:

1. the affected scientific requirement,
2. the affected component,
3. the expected change in behavior,
4. the tests required to verify the behavior,
5. the documentation that needs to be updated.

If existing results are expected to change, this should be intentional and documented.

Scientific changes should not be presented as purely technical refactoring if they alter the meaning or numerical results of the analysis.

---

## 9. Documentation

Documentation should be updated whenever a change affects documented behavior.

Depending on the change, this may include:

* requirements,
* methodology,
* architecture,
* data-flow documentation,
* CLI documentation,
* website documentation,
* development documentation.

Documentation should distinguish between:

* current implementation,
* defined requirements,
* planned extensions,
* known limitations.

Changes to scientific methodology should be documented explicitly.

---

## 10. Local Verification

Before integrating a change, the developer should perform the applicable local checks.

At minimum, this should include:

```text id="n2xv2h"
1. Run relevant tests
2. Run the affected pipeline/component where practical
3. Check generated results
4. Check for unintended changes
5. Run applicable code-quality checks
```

For changes affecting the complete pipeline, the normal pipeline execution should be considered where practical.

For changes affecting visualizations, generated figures should be inspected rather than relying exclusively on successful execution.

For changes affecting scientific calculations, representative numerical results should be checked against expected behavior.

---

## 11. Inspect the Git Diff

Before committing, inspect the changes:

```bash
git status
git diff
```

The developer should verify that:

* only intended files are changed,
* temporary files are not included,
* generated artifacts are not accidentally added,
* debugging code is removed,
* unrelated formatting changes are avoided,
* configuration changes are intentional.

For larger changes, reviewing the complete diff is part of the verification process.

---

## 12. Commit Changes

Commits should describe coherent development steps.

A commit message should communicate what was changed.

Examples:

```text id="w8e4pr"
Add threshold duration plots
Fix freeze-up event detection
Refactor results persistence
Update methodology documentation
Add tests for climatology calculation
```

Commits should avoid mixing unrelated changes.

Small commits are generally preferable when they make the development history easier to understand, but the project does not require an artificially strict commit granularity.

---

## 13. Keep the Branch Up to Date

For longer-running development branches, changes from `main` may need to be incorporated before integration.

The appropriate method depends on the situation and should avoid unnecessary disruption to the development history.

Before merging, the developer should ensure that the branch has been checked against the current `main` state when this is relevant to the change.

---

## 14. Review Before Integration

Before merging a change into `main`, the following questions should be considered:

### Functionality

* Does the implementation satisfy the intended requirement?
* Does existing functionality still behave as expected?
* Are failure conditions handled appropriately?

### Scientific correctness

* Are calculations consistent with the documented methodology?
* Are units and parameter meanings correct?
* Are expected numerical results covered by tests?
* Are changes to existing results intentional?

### Architecture

* Does the change respect component responsibilities?
* Does it introduce unnecessary coupling?
* Does it duplicate existing functionality?

### Quality

* Are tests present and appropriate?
* Are relevant quality checks passing?
* Is the code readable and maintainable?
* Are logging and error handling sufficient?

### Documentation

* Are affected documents updated?
* Are scientific or behavioral changes documented?
* Is the relationship to requirements clear?

---

## 15. Integration into `main`

A completed change is integrated into `main` only after the applicable verification has been completed.

The exact merge mechanism and review requirements may evolve with the project and are not prescribed by this document beyond the requirement that the resulting `main` state remains stable and usable.

After integration, the development branch can normally be removed.

The resulting commit history should allow the change to be traced back to its development branch and, where applicable, to the corresponding requirement and tests.

---

## 16. CI Verification

Automated CI checks provide an additional verification layer.

Depending on the current project stage, CI may include:

* automated tests,
* coverage measurement,
* formatting checks,
* linting,
* static type checks,
* unused-code detection,
* output validation,
* website/build validation.

The mandatory CI checks and their acceptance criteria are defined separately in:

```text id="j0f9j3"
docs/development/tests/ci-quality-gates.md
```

Local verification should be performed before pushing a change so that CI is used primarily as an additional reproducibility and integration check rather than as the first place where obvious problems are discovered.

---

## 17. Handling Failed Checks

A failed test or quality check should be investigated before a change is integrated.

Failures should not be bypassed merely to allow a merge.

If a check fails because the expected behavior has intentionally changed, the corresponding:

* implementation,
* test,
* requirement,
* or documentation

should be updated consistently.

If a check exposes an unrelated pre-existing problem, the problem should be documented and handled separately where practical rather than silently hiding it within the current change.

---

## 18. Changes to Generated Results

The project generates analysis results, visualizations, and a GitHub Pages build artifact.

Changes to generated outputs should be interpreted in the context of their source code and input data.

When generated scientific results change because of an intentional methodological or implementation change, the change should be traceable to the corresponding source-code modification.

Generated files should not be manually modified to make a test or visual result appear correct.

The project-specific rules for persistent outputs and deployment artifacts remain defined by the project architecture and pipeline documentation.

---

## 19. Hotfixes and Urgent Fixes

Urgent corrections to the stable pipeline may be implemented using a `fix/*` branch based on `main`.

The normal verification principles still apply:

* identify the affected behavior,
* implement the smallest appropriate change,
* add or update tests where applicable,
* run relevant checks,
* verify the resulting pipeline behavior,
* document the change if required.

An urgent fix should not become an excuse to bypass reproducibility or deliberately introduce undocumented scientific changes.

---

## 20. Contribution Workflow Summary

The normal contribution workflow can be summarized as:

```text id="1r7v0a"
Requirement / Issue
        ↓
Understand current implementation
        ↓
Create development branch
        ↓
Implement change
        ↓
Add / update tests
        ↓
Update documentation
        ↓
Run local verification
        ↓
Inspect diff
        ↓
Commit changes
        ↓
CI checks
        ↓
Review
        ↓
Merge into main
        ↓
Stable project state
```

The level of verification should be proportional to the impact of the change.

A documentation typo does not require the same validation as a modification to the sea-ice coverage calculation or threshold-event detection.

---

## 21. Relationship to Other Development Documents

This guide describes the practical contribution workflow.

Related documents define the individual aspects in more detail:

* `branching-strategy.md` — branch types and branch lifecycle
* `coding-standards.md` — implementation and code-quality conventions
* `tests/testing-strategy.md` — overall testing strategy
* `tests/test-levels.md` — responsibilities of the different test levels
* `tests/coverage.md` — code coverage objectives and metrics
* `tests/ci-quality-gates.md` — mandatory automated quality checks
* `../requirements/requirements-traceability.md` — traceability between requirements, implementation, and verification
