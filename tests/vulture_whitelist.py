"""Whitelist for Vulture dead-code findings (issues #35, #36).

Every entry names a symbol that Vulture reports as unused
although the usage is intentional or outside static reach
(docs/development/static-analysis-policy.md, section 6). Each
entry carries a justification comment that links one of:

* an S-entry in docs/development/static-analysis-findings.md,
* a finding in tests/Findings.md (F-001 ... F-021).

The whitelist is primarily relevant for periodic deep passes at
``--min-confidence 60``; the standard advisory run uses
``--min-confidence 90`` (policy section 4).

Standard run:

    vulture src tests tests/vulture_whitelist.py \
        --min-confidence 90

Deep pass (triage required for every reported candidate):

    vulture src tests tests/vulture_whitelist.py \
        --min-confidence 60

New entries are added during finding triage only -- never
prophylactically.
"""

# F-017 (tests/Findings.md): TimeSeriesPlotter._configure_style
# assigns polar_output_dir but never reads it; the polar plots
# are saved into the timeseries directory (pinned by the
# issue #32 tests). Kept until the visualization redesign in
# V0.2-07; see also S-004 in the static-analysis findings log.
polar_output_dir
