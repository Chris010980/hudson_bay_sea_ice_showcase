# Branching Strategy

## 1. Purpose

This document defines the Git branching strategy for the `hudson_bay_sea_ice` project.

The purpose of the branching strategy is to:

* keep the stable project state reproducible,
* separate ongoing development from stable releases,
* allow individual changes to be developed and reviewed independently,
* make changes traceable,
* reduce the risk of introducing unfinished changes into the stable branch.

The branching strategy is intentionally kept lightweight. The project is currently maintained by a small development team, and the workflow should therefore provide useful safeguards without introducing unnecessary process overhead.

---

## 2. Repository Branches

The project uses the following branch categories:

| Branch       | Purpose                                                                 |
| ------------ | ----------------------------------------------------------------------- |
| `main`       | Stable and releasable project state                                     |
| `feature/*`  | Development of a new feature or larger change                           |
| `fix/*`      | Correction of an existing implementation or documentation issue         |
| `docs/*`     | Documentation-only changes, where a separate branch is useful           |
| `refactor/*` | Structural or technical refactoring without intended functional changes |

Not every change requires a separate branch. Small documentation corrections or similarly trivial changes may be made directly on `main` if they do not affect the stable or operational state of the project.

---

## 3. `main` Branch

The `main` branch represents the current stable state of the project.

Changes merged into `main` should therefore satisfy the following conditions:

* the implementation is considered usable,
* the documented project scope is respected,
* required checks pass,
* the change does not knowingly leave the pipeline in a broken state,
* relevant documentation is updated where necessary.

`main` should always represent a state that can be checked out and used as a reproducible project version.

The branch is also the basis for project releases and version tags.

---

## 4. Feature and Change Branches

New development should normally be performed in a separate branch created from the current `main` branch.

Examples:

```text
feature/anomaly-analysis
feature/region-selection
fix/threshold-event-detection
docs/update-methodology
refactor/results-manager
```

Branch names should be:

* descriptive,
* short enough to remain readable,
* written in lowercase,
* separated by hyphens,
* prefixed according to the type of change.

A branch should represent one coherent change or closely related set of changes.

Large unrelated modifications should not be combined into a single branch merely because they are developed at the same time.

---

## 5. Branch Lifecycle

The general development workflow is:

```text
main
  │
  ├── feature/...
  │
  ├── fix/...
  │
  └── docs/...
       │
       ▼
   development
       │
       ▼
   verification
       │
       ▼
      main
```

A typical change follows these steps:

1. Update the local `main` branch.
2. Create a suitable branch from `main`.
3. Implement the change.
4. Add or update relevant documentation and tests.
5. Run the applicable local quality checks.
6. Review the changes.
7. Merge the branch into `main`.
8. Remove the completed development branch where appropriate.

The exact review and merge mechanism is defined separately in the contribution guide.

---

## 6. Commits

Commits should represent coherent development steps.

A commit should preferably:

* contain one logical change,
* avoid unrelated modifications,
* use a concise and descriptive message,
* leave the repository in a meaningful state where practical.

Large generated files, temporary data, local environments, and other development artifacts should not be committed unless they are explicitly part of the repository.

Scientific result files that are intentionally version-controlled are subject to the project's data and reproducibility rules.

---

## 7. Releases and Version Tags

Releases are created from stable states of `main`.

A release should be associated with a Git tag, for example:

```text
v0.1.0
v0.2.0
v0.2.1
```

The exact versioning scheme and release criteria are defined separately if required.

For the initial development phase, the important principle is that a version tag identifies a specific, reproducible state of:

* source code,
* documentation,
* configuration,
* dependencies,
* and relevant project metadata.

This allows later results or observations to be related to the implementation that produced them.

---

## 8. Long-Lived Development Branches

No permanent `develop` branch is required by the current project structure.

A permanent integration branch may be introduced later if the development process grows sufficiently to justify it.

Until then, short-lived feature and fix branches provide the separation between ongoing development and the stable `main` branch without adding another long-lived branch.

If a `develop` branch or another permanent integration branch is introduced, this document should be updated before adopting it as part of the regular workflow.

---

## 9. Branching and Scientific Reproducibility

Branching is not only a software-development mechanism in this project. It also contributes to scientific traceability.

Changes affecting scientific results should therefore be traceable to the corresponding Git history.

In particular, changes to:

* analysis algorithms,
* scientific thresholds,
* reference data,
* interpolation rules,
* climatological definitions,
* event-detection logic,
* calculation methods,

should be identifiable in the version history.

A release tag provides a stable reference to the implementation used for a particular project state.

Branching alone does not guarantee scientific reproducibility. Reproducibility additionally depends on dependency versions, configuration, input data, reference data, and documented methodology.

---

## 10. Relationship to Other Development Documents

This document defines the branching model only.

The related development processes are documented separately:

* `coding-standards.md` — coding and implementation conventions
* `contribution-guide.md` — workflow for making and integrating changes
* `tests/testing-strategy.md` — overall testing strategy
* `tests/test-levels.md` — test levels and their responsibilities
* `tests/coverage.md` — code coverage measurement
* `tests/ci-quality-gates.md` — automated quality checks and CI requirements
* `../requirements/requirements-traceability.md` — relationship between requirements, implementation, and verification

The documents should be kept consistent when the development workflow changes.
