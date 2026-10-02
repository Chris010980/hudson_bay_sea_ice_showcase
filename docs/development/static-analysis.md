# Static Analysis Tool Evaluation

**Issue:** #34 (milestone V0.2-06 — Static Analysis &amp; CI)  
**Status:** evaluation document; no production code is changed  
as part of this evaluation.

This document evaluates available Python static-analysis tools  
before selecting the project toolset, and documents the  
recommendation for the subsequent implementation step (#35).

Static analysis complements the existing dynamic test suite  
(148 tests). It is an *information source*: a reported finding  
is an input for a decision, not an obligation — not every  
finding must automatically be removed (see section 7).

---

## 1. Relevant Categories

| #   | Category                          | Question it answers                                                                                        |
| --- | --------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 1   | Coding standards &amp; formatting | Does the code follow a consistent, PEP 8 based style, and is formatting deterministic?                     |
| 2   | Linting                           | Which code locations show bug-prone patterns, undefined names or style violations?                         |
| 3   | Unused declarations               | Which imports, variables and functions are unused *within* a file?                                         |
| 4   | Dead code                         | Which functions, classes or attributes are unused *across* the whole project (including unreachable code)? |
| 5   | Import / dependency analysis      | Are imports sorted and grouped, are declared dependencies actually used, and are all imports declared?     |
| 6   | Complexity / maintainability      | Where is cyclomatic complexity or maintainability a concern?                                               |

Adjacent categories that are **deliberately out of scope** for  
this evaluation:

- **type checking** (mypy, pyright, ty) — a separate  
category with its own cost/benefit profile; should be decided  
in its own step, not bundled into the tool selection here,
- **security scanning** (bandit, pip-audit),
- **dynamic coverage analysis** (coverage.py) — complements  
dead-code findings, but is not static analysis.

---

## 2. Project Context for the Evaluation

- Python 3.12, pytest 9.1.1, `src/`-layout package  
(`src.config`, `src.data_download`, `src.analysis`,  
`src.update`, `src.visualization`, `src.main`), roughly 40  
Python modules including the test suite.
- Scientific stack: numpy, pandas, rasterio, matplotlib,  
cartopy, pyproj, requests.
- Existing conventions (docs/development/coding-standards.md):  
PEP 8 based style, four-space indentation, and explicitly:  
*"The project should use an automated formatter rather than*  
*relying solely on manual formatting"* — the concrete tooling  
is to be defined by this evaluation's successor.
- Practical house style: \~72 character lines, verbose module  
docstrings, `# ---- Task: ... ----` section banners.
- `pyproject.toml` exists (currently pytest configuration  
only) — all shortlisted tools can be configured natively  
there, which favors tools with first-class pyproject  
support.
- Known code-level findings already documented in  
tests/Findings.md (F-001 … F-021) — a static tool will  
partially re-discover these; that is expected and desirable,  
not a duplication problem.

---

## 3. Tool Evaluation by Category

### 3.1 Coding standards and formatting

| Tool                               | Assessment                                                                                                                                                                                 | Verdict                      |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------- |
| **Ruff formatter** (`ruff format`) | Black-compatible deterministic formatter in the same binary as the linter; configurable line length (project: 72); stable formatter since v0.1, actively developed (current line v0.16.x). | **Adopt (candidate)**        |
| Black                              | The established deterministic formatter; near-complete output parity with `ruff format`. A second tool alongside Ruff adds a dependency and a formatter *pair* that must be kept in sync.  | Redundant if Ruff is adopted |
| isort                              | Import sorting; fully covered by Ruff's `I` rules.                                                                                                                                         | Redundant                    |
| pycodestyle / autopep8 / yapf      | Style checkers/fixers; pycodestyle is subsumed by Ruff; yapf and autopep8 offer no advantage over the deterministic formatters.                                                            | Rejected                     |

### 3.2 Linting and unused declarations

| Tool                           | Assessment                                                                                                                                                                                                                                                                                     | Verdict                                               |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **Ruff linter** (`ruff check`) | 900+ rules; native re-implementations of pyflakes, pycodestyle, flake8-bugbear, pyupgrade, pydocstyle and others; covers unused imports (F401) and unused local variables (F841) at file level; one fast binary, first-class `pyproject.toml` configuration.                                   | **Adopt (candidate)**                                 |
| flake8 (+ plugin ecosystem)    | Mature and extensible, but each plugin is a separate dependency; configuration historically not pyproject-native; performance is far below Ruff; rule coverage largely a subset of Ruff.                                                                                                       | Rejected                                              |
| pylint                         | The deepest classic analyzer: naming conventions, duplicate-code detection (R0801), design checks, very thorough — and correspondingly noisy and slow. Overlap with Ruff is large; the unique extras (duplicate code, naming) are desirable but not gate-critical for a codebase of this size. | Deferred (optional advisory; not in the default gate) |

### 3.3 Dead-code detection

| Tool                     | Assessment                                                                                                                                                                                                                                                                                                                                                             | Verdict                     |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| **Vulture**              | AST-based project-wide detection of unused functions, classes, variables, imports and attributes; every finding carries a confidence value (60–100%); also detects unreachable code (after `return`/`raise`, unsatisfiable conditions); false positives are handled via a whitelist file. Running it over `src/` *and* `tests/` additionally highlights untested code. | **Adopt (advisory)**        |
| deadcode                 | Newer AST-based alternative; TOML configuration; less field-proven than Vulture.                                                                                                                                                                                                                                                                                       | Rejected for now            |
| coverage.py (complement) | Dynamic, not static: untested lines are a strong *hint* at dead code but the tool reports coverage, not deadness.                                                                                                                                                                                                                                                      | Adjacent; separate decision |

**Known limitation (applies to all dead-code tools):** Python's  
dynamic nature means implicitly used code (CLI entry points,  
`getattr` patterns, monkeypatched attributes) can be falsely  
reported, and some dead code can be missed. Consequence:  
dead-code findings are **advisory**, never auto-removed, and a  
whitelist documents accepted exceptions.

### 3.4 Import and dependency analysis

| Tool                        | Assessment                                                                                                                                                                                                                                                                                                                   | Verdict                     |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| **Ruff** (`I` rules + F401) | Import grouping/sorting and unused imports *within* files; already part of the linter selection.                                                                                                                                                                                                                             | **Adopt (candidate)**       |
| **deptry**                  | Project-level dependency hygiene: reports unused declared dependencies (DEP002), undeclared imports (DEP001) and transitive usage (DEP003/004); `pyproject.toml` configuration. Prerequisite met: the project declares its dependencies in `requirements.txt` (completed by issue #36 — pandas was imported but undeclared). | **Adopt (advisory)**        |
| FawltyDeps                  | Alternative undeclared/unused dependency checker; similar scope to deptry.                                                                                                                                                                                                                                                   | Rejected (deptry preferred) |
| import-linter               | Enforces architecture *contracts* (e.g., "visualization must not import analysis") via a linting DSL; interesting for the pipeline stage boundaries, but additional concepts for a codebase of this size.                                                                                                                    | Deferred                    |

### 3.5 Complexity and maintainability

| Tool                           | Assessment                                                                                                                                                                                                                                                                                                                                           | Verdict                                            |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| **Ruff** (`C901`, mccabe port) | Per-function cyclomatic complexity as a lint gate; no additional tool if Ruff is adopted.                                                                                                                                                                                                                                                            | **Adopt (candidate gate)**                         |
| radon                          | Rich metric reporting: cyclomatic complexity per block, Maintainability Index, Halstead volume, raw SLOC/comment metrics. By its own documentation it is a *reporting* tool and does not reliably exit non-zero on threshold violations — CI gating would require the companion tool xenon. The Maintainability Index is documented as experimental. | Optional (local advisory reporting; not a CI gate) |
| xenon                          | Exit-code gate on top of radon metrics. Only relevant if radon enters CI.                                                                                                                                                                                                                                                                            | Deferred                                           |
| lizard                         | CC/NLOC metrics; overlaps with radon/ruff.                                                                                                                                                                                                                                                                                                           | Rejected                                           |

---

## 4. Python 3.12 Compatibility and Codebase Check

All shortlisted tools support Python 3.12 (Ruff explicitly  
targets language features up to Python 3.14; black, isort,  
flake8, pylint, vulture, radon and deptry all run on 3.12):

- no syntax-version conflict is expected for the existing  
codebase, which uses standard 3.12 features  
(`X | Y` unions, `from __future__ import annotations`,  
f-strings, pathlib),
- the scientific stack does not affect static analysis — the  
tools parse source, they do not import the analyzed modules,
- a manual spot check of representative source files confirms  
the tools would produce *useful* (not just noisy) findings on  
the current code, consistent with already documented  
findings:
  - the stray `from os import link` import documented as F-012  
  is a textbook F401 (unused import) finding,
  - `src/update/build_pages.py` assigns `logger` *before* the  
  last import (an E402 finding), and its dead CLI options  
  (F-020) correlate with unreferenced argument attributes,
  - `tests/conftest.py` contains duplicated import statements  
  (an F811 finding),
  - the unused `polar_output_dir` attribute documented as F-017  
  is exactly the kind of project-level finding Vulture  
  reports (with a confidence value).

Conclusion: the tools are compatible, and their finding  
categories demonstrably intersect with real, already-known  
issues of this codebase.

---

## 5. Overlap Analysis

| Overlap                                                    | Assessment                                                                                                                                                                                                                      |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ruff vs. flake8/pyflakes/pycodestyle/isort/black/pyupgrade | Ruff re-implements all of them behind one interface; running the originals alongside produces duplicate findings, double configuration and double CI time with no additional coverage. **Do not combine.**                      |
| Ruff `C901` vs. radon                                      | Same core metric (mccabe). Ruff is the gate; radon adds *reporting* depth (MI, Halstead) that Ruff deliberately does not provide. Combination is possible but optional.                                                         |
| Ruff F401/F841 vs. Vulture                                 | Different scopes: Ruff checks unused declarations *within a file*; Vulture checks *project-wide* usage (a function used by nobody). They complement each other; Vulture findings overlap with Ruff only for file-local symbols. |
| pylint vs. Ruff                                            | Large rule overlap; pylint's unique value is duplicate-code detection and naming checks. Keeping pylint out of the default gate avoids duplicated findings; it can be added later as an advisory pass.                          |
| deptry vs. Ruff                                            | No overlap: Ruff cannot compare imports against *declared dependencies*; deptry does exactly that. Complementary.                                                                                                               |

---

## 6. Limitations Summary

- **Ruff:** no type inference (not a type checker); individual  
rules can conflict with the formatter (e.g., implicit string  
concatenation) — resolved by rule selection in the  
configuration, not by tool count.
- **Vulture:** false positives on dynamic/implicit usage;  
whitelist effort grows with dynamic patterns (CLI entry  
points, monkeypatching).
- **radon:** reporting tool by design; unreliable exit codes  
for CI gating (xenon needed); Maintainability Index  
documented as experimental.
- **deptry:** requires a dependency manifest; provided by  
`requirements.txt` (completeness improved during #36: pandas  
was imported but undeclared and is now declared).
- **All tools:** findings are heuristics. The project  
explicitly does not assume that every reported finding must  
be removed — each finding is triaged like the entries in  
tests/Findings.md (fix, document, or whitelist).

---

## 7. Recommendation for the Implementation Step (#35)

    **Core gate (CI-blocking):**

1. **Ruff** as the single linting *and* formatting tool  
 (`ruff check` + `ruff format`), configured in  
 `pyproject.toml`:
    - line length 72 (house style),
    - rule set: `E`/`W` (pycodestyle), `F` (pyflakes,  
  incl. F401/F811/F841), `I` (isort), `B` (bugbear),  
  `UP` (pyupgrade), `C901` (complexity gate),
    - excludes for non-source trees (`build/`, `output/`,  
  `data/`, `.venv/`, `docs/`).

    **Advisory (report, triage, whitelist — not gate):**

2. **Vulture** over `src/` and `tests/`, minimum confidence  
 \~90%, with a whitelist file for accepted exceptions; run  
 locally and as a non-blocking CI report.
3. **radon** (optional) as a local reporting tool for  
 complexity/maintainability trends; no CI gate.

    **Deferred / conditional:**

4. **deptry** as a non-blocking advisory report against  
 `requirements.txt`.
5. **pylint** as an optional advisory pass (duplicate-code,  
 naming); not in the default gate.
6. **import-linter** for stage-boundary contracts; candidate  
 for a later milestone.
7. **Type checking** (mypy/ty/pyright): explicitly a separate  
 future decision, not part of V0.2-06.

**Explicitly not adopted:** flake8, black, isort, yapf,  
autopep8, lizard, xenon, deadcode, FawltyDeps.

The concrete configuration values, the pre-commit/CI wiring and  
the handling of the initial finding backlog are the subject of  
issue #35.

---

## 8. References

- Ruff: [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)
- Vulture: [https://github.com/jendrikseipp/vulture](https://github.com/jendrikseipp/vulture)
- radon: [https://radon.readthedocs.io/](https://radon.readthedocs.io/)
- xenon: [https://github.com/rubik/xenon](https://github.com/rubik/xenon)
- pylint: [https://pylint.readthedocs.io/](https://pylint.readthedocs.io/)
- deptry: [https://deptry.com/](https://deptry.com/)
- import-linter: [https://import-linter.readthedocs.io/](https://import-linter.readthedocs.io/)
- FawltyDeps: [https://github.com/tweag/FawltyDeps](https://github.com/tweag/FawltyDeps)
