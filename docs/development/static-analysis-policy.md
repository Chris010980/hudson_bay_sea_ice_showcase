# Static Analysis Policy

**Issue:** #35 (milestone V0.2-06 — Static Analysis &amp; CI)  
**Basis:** tool evaluation in `docs/development/static-analysis.md`  
(issue #34).

This policy defines which static-analysis findings are treated  
as errors, warnings or informational results, and how  
exceptions are documented. The handling rules below are written  
category-first (tool-agnostic); the concrete tool binding comes  
from the completed #34 evaluation and the #36 implementation.

Static analysis complements the dynamic test suite. A finding  
is an *input for a decision* — the policy defines which  
decisions are mandatory, not that every finding must be  
removed.

---

## 1. Severity Classes

| Class                                           | Meaning                                                                                           | Merge behavior       |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------- |
| **Error** (mandatory check)                     | Must be resolved or carry a documented exception before merge.                                    | Blocking             |
| **Warning** (advisory check, triage required)   | Must be *classified* before merge: fix, accept (documented), or defer with a milestone reference. | Non-blocking in v0.2 |
| **Informational** (advisory check, report only) | Reviewed opportunistically; no per-merge obligation.                                              | Non-blocking         |

---

## 2. Coding-Standard Expectations

- The project style is PEP 8 based  
(`docs/development/coding-standards.md`) with a house line  
length of **72 characters**.
- The **automated formatter is the normative formatting**  
**target**: what the formatter produces is the project style.
  - Transition rule for the introduction (#36): one isolated,  
  semantically empty formatting commit for the whole tree,  
  reviewed as a pure diff. After that commit the formatting  
  check is mandatory.
- Mandatory (error) style checks:
  - formatter check (`ruff format --check .`),
  - pycodestyle rule classes `E`/`W`, including `E501`  
  (line length 72) — the codebase already adheres to this  
  in the reviewed modules,
  - import order (`I`, auto-fixable).
- Informational for v0.2: docstring style checks, naming  
conventions beyond PEP 8 (no tool gate; conventions are  
enforced through the existing coding standards).

---

## 3. Unused Imports and Declarations

Unused declarations are defects until proven otherwise:

- **Error:** unused imports (`F401`), redefinitions/shadowed  
imports (`F811`), unused local variables (`F841`).
- Handling: remove or fix the declaration. An inline  
`# noqa` is only permitted with a **technical justification**  
**comment** and an entry in the findings log  
(`docs/development/static-analysis-findings.md`).

---

## 4. Dead-Code Handling

Dead code (project-wide unused functions, classes, attributes,  
unreachable code) is **advisory**, never auto-removed:

- **Informational:** dead-code findings at high confidence  
(standard run, `--min-confidence 90`).
- Periodic deep passes at lower confidence surface attribute  
and method candidates; every candidate must be triaged:
  1. genuine defect → fix (normal change process),
  2. intentional, documented behavior → whitelist entry with  
   justification (e.g., the `polar_output_dir` finding  
   F-017),
  3. unclear → investigate before the next quality milestone;  
   whitelist only with a justification.
- The whitelist file is version-controlled; every entry  
carries a comment with its justification reference.

Rationale: dynamic-language dead-code analysis has real false  
positives (CLI entry points, monkeypatched module constants,  
dynamically dispatched methods). Behavior is ultimately  
protected by the test suite, not by the dead-code tool.

---

## 5. Complexity Thresholds

- Cyclomatic complexity (mccabe) threshold: **10** per function  
or method, applied to `src/` only.
- Severity: **warning** — findings must be triaged (refactor,  
accept with comment, or defer); not gate-blocking in v0.2.  
Promotion to error is a candidate for a later milestone.
- No threshold on `tests/`: test functions are deliberately  
linear scenario scripts.
- Maintainability metrics (Maintainability Index, Halstead) are  
**informational** local reports only; the Maintainability  
Index is documented as experimental and is not used for  
decisions.

---

## 6. Scientifically and Technically Justified Exceptions

Exceptions are *documented deviations*, not check waivers. Two  
mechanisms exist:

1. **Inline exception:** `# noqa: <CODE>  # <short reason>` —  
 only for single-location, technically justified cases  
 (e.g., a formula that must stay on one line for review  
 against the hand calculation).
2. **Whitelist entry** (dead code): name plus justification  
 comment in `tests/vulture_whitelist.py`.

Every exception must be traceable:

- an **S-entry** in  
`docs/development/static-analysis-findings.md`, and
- a cross-reference to `tests/Findings.md` whenever the  
finding corresponds to already-documented intentional  
behavior (F-001 … F-021).

Typical justified categories in this project:

- numerically motivated formatting (hand-calculated formulas),
- intentional design findings deferred to milestone V0.2-07,
- test-isolation patterns invisible to static analysis  
(monkeypatched module constants, namespace doubles),
- CLI entry points (`main`, `parse_args`) invoked from outside  
the analyzed code.

---

## 7. Exclusions

Static analysis applies to Python source only. Excluded from  
all checks: `build/`, `output/`, `data/`, `docs/`, `releases/`,  
`.idea/`, `.venv/`.

Cleanup behavior and scientific data trees are covered by the  
test suite (test-levels.md, section 8), not by linting.

---

## 8. Checks Bound to CI (implemented in issue #37)

The CI wiring lives in  
`.github/workflows/quality-gate.yml`. It runs on every push  
(branch `stable` excluded — it only receives automatic  
output commits from the daily update workflow) and on pull  
requests to `main`.

| Check                                                                        | CI job         | Mode in CI                                                                              |
| ---------------------------------------------------------------------------- | -------------- | --------------------------------------------------------------------------------------- |
| `ruff check .`                                                               | `static-gates` | **Mandatory** (blocking)                                                                |
| `ruff format --check .`                                                      | `static-gates` | **Mandatory** (blocking)                                                                |
| `pytest --cov=src`                                                           | `test-gates`   | **Mandatory** (blocking)                                                                |
| Coverage report (`term-missing` console output plus `coverage.xml` artifact) | `test-gates`   | Reporting only — no threshold in v0.2; a threshold is a candidate for a later milestone |
| `vulture src tests tests/vulture_whitelist.py --min-confidence 90`           | `static-gates` | **Advisory** — `continue-on-error: true` (reports findings, never blocks)               |
| `radon cc` / `radon mi`                                                      | —              | Local only, no CI (section 5)                                                           |

CI behavior contract:

- A failing **mandatory** step turns the workflow red; a red  
quality gate blocks the merge. Mandatory failures therefore  
prevent successful quality validation.
- An **advisory** step runs with `continue-on-error: true`:  
findings surface as a failing step with a warning  
annotation in the run log, while the job and the workflow  
stay green. Advisory findings cannot block development;  
the triage obligation (sections 4 and 5) is unchanged.
- The CI wiring was validated in #37 on all three paths:  
green run (success), deliberate mandatory violation  
(blocking), deliberate advisory finding (non-blocking).

---

## 9. Severity Mapping Summary

| Check / rule class                      | Severity                          |
| --------------------------------------- | --------------------------------- |
| Formatter check                         | Error                             |
| `E`, `W` (incl. E501)                   | Error                             |
| `F401`, `F811`, `F841`                  | Error                             |
| `I` (import order)                      | Error (auto-fixable)              |
| `B` (likely-bug patterns)               | Warning (triage)                  |
| `UP` (syntax modernization)             | Warning (triage; safe auto-fixes) |
| `C901` complexity &gt; 10 (`src/` only) | Warning (triage)                  |
| Dead code (Vulture)                     | Informational (+ whitelist)       |
| Maintainability metrics                 | Informational (local only)        |
