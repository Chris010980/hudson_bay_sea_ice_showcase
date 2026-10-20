# QA Validation of the Daily Pipeline Output

This document describes the QA validation of the daily
pipeline output (issue #41): the automated check of the real
production products of an update run against the documented
schemas and consistency rules.

The check is implemented by `src/qa/validate_output.py` and
is the automated form of the "malformed output files"
regression case (test-levels.md, section 6.3; see
regression-tests.md).

## Usage

```bash
python -m src.qa.validate_output

The validator reads the production paths from
src/config/paths.py (summary CSV, latest.json, the derived
time-series products, the plot tree, the build directory and
the reference summary). It supports the shared logging
options (--log-level, --log-file).

Exit code: 0 when no issue is found, otherwise the
number of issues. Every issue is logged as an error before
the summary line, so the script can gate a deployment or a
scheduled workflow.

## Checked Rules

### Summary CSV (ice_coverage_summary.csv)

* persisted schema (column set and order),
* ISO date format for every observation,
* no duplicate (date, region) records,
* sorted by (date, region),
* only regions of the reference summary,
* coverage percentages within [0, 100] and not missing.

### latest.json

* required keys (dataset, date, generated,
observations, regions),
* date and observation count match the summary state,
* generated is a UTC timestamp (ends with Z),
* region list matches the regions of the newest observation.

### Derived time-series products

* timeseries: required columns; contains every summary
observation; no duplicate (date, region) rows,
* yearly: empty is valid (fresh dataset, F-031); otherwise
the persisted schema and numeric years,
* events: empty is valid; otherwise the persisted schema and
known event types.

### Plot tree (output/plots/)

* the six daily products per region (classical, anomaly and
polar, relative and absolute) exist and are PNG files,

* the yearly products (threshold duration, yearly mean) are
required once the yearly_timeseries product class exists.

### Website build (build/)

* index.html exists,
* the built summary CSV matches the analysis summary,
* the built latest.json matches the newest observation.

## When to Run

* after the daily update (manually or as a scheduled
follow-up step),
* before deploying the website build,
* after every change to the persistence or plot schema
(then update the schemas in the validator in the same
issue).

## Testability

Every check is a pure function on a dataframe, a payload or
a directory; the CLI entry point accepts all paths as
injectable keyword arguments with the production defaults
(the established injection pattern of issues #73/#106).
tests/unit/test_output_validator.py covers the checks and
both CLI outcome classes (exit code 0 and counted issues).

A future v0.3 candidate is a qa dispatcher subcommand so
the check shares the main.py entry point; until then the
module CLI above is the documented interface.

