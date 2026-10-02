# Static Analysis Findings Log

**Issue:** #36 (milestone V0.2-06)  
**Policy:** `docs/development/static-analysis-policy.md`  
**Tool basis:** `docs/development/static-analysis.md` (#34)

This log is the single source of truth for static-analysis  
findings in a consistent format: every finding is either fixed,  
accepted with a justification, or deferred with a milestone  
reference. It is the static-analysis counterpart of  
`tests/Findings.md` (dynamic-test findings); cross-references  
use the F-numbers of that document.

    **Classification values**

- `fix` — genuine defect; corrected (or scheduled with an  
explicit change, not merely to improve a tool score),
- `accept` — intentional implementation choice; documented,  
no change,
- `defer` — real but not urgent; scheduled for a milestone  
(default: V0.2-07).

    **Tool versions (reproducibility)**

Recorded after the first run (`pip freeze | grep -iE "^(ruff|vulture|radon)="`):

| Tool    | Version |
| ------- | ------- |
| ruff    | 0.16.10 |
| vulture | 2.16    |
| radon   | 6.0.1   |

---

## Pre-Classified Findings (spot check, issue #34)

These entries were classified from the tool evaluation spot  
check before the first full run; the full run (#36) confirms  
or extends them.

| ID    | Check                            | Location                                                               | Severity      | Classification    | Justification / Reference                                                                                                                                                                                                                                                                              |
| ----- | -------------------------------- | ---------------------------------------------------------------------- | ------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| S-001 | F401 (unused import)             | `src/data_download/…` (`from os import link`)                          | error         | `defer` (V0.2-07) | Genuine defect, already documented as F-012 (tests/Findings.md). Removal is a production-code change; scheduled with the F-009–F-012 downloader family rather than inside a tooling issue.                                                                                                             |
| S-002 | E402 (import not at top of file) | `src/update/build_pages.py`                                            | error         | `defer` (V0.2-07) | The module assigns `logger` before the last import; related to the dead CLI contract documented as F-020. Trivial reorder, but a production-code change — scheduled with the build\_pages cleanup.                                                                                                     |
| S-003 | F811 (duplicate import)          | `tests/conftest.py`                                                    | error         | `fix`             | Test infrastructure file, no production code; `Path` and `pytest` are imported twice. Safe isolated cleanup during #36.                                                                                                                                                                                |
| S-004 | dead code (attribute, deep pass) | `src/visualization/timeseries_plot.py` (`polar_output_dir`)            | informational | `accept`          | Intentional, documented behavior: F-017 (tests/Findings.md), pinned by the issue #32 tests; whitelist entry in `tests/vulture_whitelist.py`.                                                                                                                                                           |
| S-005 | F401 (unused import)             | `src/analysis/timeseries_analyzer.py:19` (`from curses import window`) | error         | `defer` (V0.2-07) | Genuine defect: IDE auto-import of the `curses.window` type triggered by the `window: int = 3` parameter. Unused in the module and a hard `ModuleNotFoundError` on Windows (curses is Unix-only). Production code — scheduled with the V0.2-07 cleanup instead of a silent fix inside a tooling issue. |

---

## Findings from the First Full Run (ruff 0.16.10)

**Statistics:** 401 findings in 40 files.

| Rule                       | Count  | Rule         | Count |
| -------------------------- | ------ | ------------ | ----- |
| E501                       | 162    | F401         | 7     |
| W291                       | 111    | F811         | 5     |
| I001                       | 39     | E402         | 4     |
| W292                       | 34     | C901         | 3     |
| B905                       | 13     | B007         | 3     |
| W293                       | 12     | UP037 / F841 | 2 + 2 |
| UP017 / F821 / F402 / B018 | 1 each |              |       |

Most affected files: `timeseries_analyzer.py` (90),  
`timeseries_plot.py` (49), `downloader.py` (45),  
`geotiff_plot.py` (20), the two authored #32 test modules  
(19 each), `conftest.py` (10).

**Classification** (policy: severity → handling; every entry  
is resolved by a fix in the #36 batch, a documented inline  
exception, or a V0.2-07 deferral):

| ID    | Check                                                    | Location                                                                                                      | Severity | Classification             | Justification / Reference                                                                                                                                                                                                                                |
| ----- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | -------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S-006 | I001/W291/W292/W293 + E501 + UP017/UP037 (≈348 findings) | whole tree                                                                                                    | error    | `fix` (transition commit)  | Semantically empty style findings: trailing whitespace, import order, overlong lines, `timezone.utc`→`UTC`, quoted annotations. Resolved by `ruff check --fix` + `ruff format .` as the isolated, diff-reviewed style commit (policy section 2).         |
| S-007 | F811 (duplicate `ReferenceBuilder` import)               | `src/analysis/process_data.py:18`                                                                             | error    | `fix` (transition commit)  | Exact duplicate of line 16; removal is semantically empty.                                                                                                                                                                                               |
| S-008 | F811/F401 (test side)                                    | `tests/conftest.py:11,12`; `tests/component/test_timeseries_event_window.py:36`                               | error    | `fix` (#36)                | Duplicate `Path`/`pytest` imports (confirms S-003) and one unused `pytest` import. Test infrastructure, no production code.                                                                                                                              |
| S-009 | B905 (`zip()` without `strict=`)                         | 13× in `tests/conftest.py` and 8 test modules                                                                 | warning  | `fix` (#36)                | Adding `strict=True` turns silent length mismatches into hard errors; the green 148-test suite proves the lengths currently match, so the change is behavior-neutral today and protective tomorrow.                                                      |
| S-010 | B007 (loop variable `region` unused)                     | `reference_builder.py:165,226`; `timeseries_analyzer.py:325`                                                  | warning  | `fix` (transition commit)  | Auto-fix rename to `_region`; semantically empty.                                                                                                                                                                                                        |
| S-011 | F401 ×2 + F402                                           | `src/data_download/downloader.py:10,12,455`                                                                   | error    | `defer` (V0.2-07) + `noqa` | Confirms S-001/F-012: unused `from os import link`, unused `shutil`, and `link` shadowed by a loop variable. Deliberately **not** auto-removed — belongs to the planned downloader cleanup (F-009…F-012).                                                |
| S-012 | F401 ×2 + F811                                           | `src/update/update_pipeline.py:11,14,50`                                                                      | error    | `defer` (V0.2-07) + `noqa` | Unused `datetime.date`, unused module import `downloader`, and a redefinition of `downloader` at line 50 — the shadowing pattern is a bug *suspect* (possibly intended monkeypatch-style wiring, cf. F-015) and needs investigation, not blind deletion. |
| S-013 | F401 + F811                                              | `timeseries_analyzer.py:19,304`                                                                               | error    | `defer` (V0.2-07) + `noqa` | Confirms S-005: stray `curses.window` import; the `window: int = 3` parameter then shadows it.                                                                                                                                                           |
| S-014 | F401                                                     | `src/analysis/reference_builder.py:13`                                                                        | error    | `defer` (V0.2-07) + `noqa` | Unused `rasterio.crs.CRS`; removal scheduled with the analysis-stage cleanup.                                                                                                                                                                            |
| S-015 | F841                                                     | `timeseries_analyzer.py:948` (`default_freezeup_window`)                                                      | error    | `defer` (V0.2-07) + `noqa` | **Bug suspect:** the default freeze-up search window is computed via `_get_event_window()` but never used — possible missing wiring in the event search. Protected by the #25/#27 event-window tests as-is; requires semantic review before any change.  |
| S-016 | F841                                                     | `geotiff_plot.py:495` (`subtitle`)                                                                            | error    | `defer` (V0.2-07) + `noqa` | Same computed-but-never-applied pattern (a subtitle that never reaches the figure); candidate for missing wiring in the map plotting.                                                                                                                    |
| S-017 | E402 ×4                                                  | `process_data.py:28`, `timeseries_analyzer.py:28`, `build_pages.py:20` (confirms S-002), `geotiff_plot.py:36` | error    | `defer` (V0.2-07) + `noqa` | Imports after statements. **Not** semantically empty to fix: `process_data.py` bootstraps `sys.path` before importing `src.*`, and the others assign `logger` first — reordering needs a careful per-module review.                                      |
| S-018 | C901 ×3                                                  | `timeseries_analyzer._find_threshold_crossing` (18), `downloader.sync` (20), `generate_plots.main` (12)       | warning  | `defer` (V0.2-07) + `noqa` | Refactoring three central methods is a semantic change with regression risk; deliberately postponed (policy section 5).                                                                                                                                  |
| S-019 | F821 + B018                                              | `tests/vulture_whitelist.py:34`                                                                               | error    | `fix` (configuration)      | Not a code defect: the Vulture whitelist intentionally contains bare symbol names. Resolved with a documented per-file-ignore in `pyproject.toml`, not with code changes.                                                                                |

**Resulting end state of #36:** after the transition commit,  
the S-008/S-009 test-side fixes, the S-019 configuration  
exception and the documented `# noqa` exceptions for  
S-011…S-018, `ruff check .` and `ruff format --check .` pass  
with a green gate; the 18 `noqa` exceptions are the tracked  
V0.2-07 backlog. No production code is changed *merely* to  
improve a tool score — every change traces to an S-entry.

---

## Run Protocol

```console
# Mandatory gates (policy section 8/9)
ruff check .
ruff format --check .

# Advisory dead-code report
vulture src tests tests/vulture_whitelist.py --min-confidence 90

# Advisory complexity report (local only)
radon cc src -s -n C
```

Order of operations for issue #36 (after triage):

1. Append the Ruff configuration to `pyproject.toml`  
 (including the per-file-ignore for the Vulture whitelist,  
 S-019), and add `tests/vulture_whitelist.py`.
2. Documented exceptions first — set the 18 inline  
 `# noqa` directives for S-011 … S-018 (list below).  
 They must be in place **before** the auto-fix, otherwise  
 `ruff check --fix` would delete the deferred (suspect)  
 imports. If a `noqa` comment pushes an import line past  
 72 characters, wrap the import in parentheses and put the  
 comment on the opening line.
3. Transition commit (isolated, diff-reviewed, semantically  
 empty): `ruff check --fix .` followed by `ruff format .`  
 — resolves S-006, S-007, S-010 and the auto-fixable parts  
 of S-008.
4. Test-side fixes: remaining S-008 leftovers (if any) and  
 `strict=True` for the 13 B905 findings (S-009), then  
 `pytest` (must stay 148 passed).
5. Verify the gates: `ruff check .` and `ruff format --check .`  
 are green; `pytest` stays at 148 passed.
6. Run the advisory tools (`vulture`, `radon`) and triage new  
 candidates separately.
7. Existing code is not changed merely to achieve a tool score:  
 every change traces to an S-entry; the 18 `noqa` exceptions  
 are the tracked V0.2-07 backlog.

The 18 documented exceptions (S-011 … S-018):

- `src/data_download/downloader.py`: line 10 `# noqa: F401`  
(S-011/F-012), line 12 `# noqa: F401` (S-011),  
line 455 `# noqa: F402` (S-011)
- `src/update/update_pipeline.py`: line 11 `# noqa: F401` and  
line 14 `# noqa: F401` (S-012), line 50 `# noqa: F811`  
(S-012, bug suspect)
- `src/analysis/timeseries_analyzer.py`: line 19  
`# noqa: F401` (S-013/S-005), line 304 `# noqa: F811`  
(S-013), line 531 `# noqa: C901` (S-018), line 948  
`# noqa: F841` (S-015, bug suspect), line 28  
`# noqa: E402` (S-017)
- `src/analysis/reference_builder.py`: line 13  
`# noqa: F401` (S-014)
- `src/visualization/geotiff_plot.py`: line 36  
`# noqa: E402` (S-017), line 495 `# noqa: F841`  
(S-016, bug suspect)
- `src/analysis/process_data.py`: line 28 `# noqa: E402`  
(S-017, sys.path bootstrap precedes imports)
- `src/update/build_pages.py`: line 20 `# noqa: E402`  
(S-017/S-002)
- `src/visualization/generate_plots.py`: line 83  
`# noqa: C901` (S-018)
