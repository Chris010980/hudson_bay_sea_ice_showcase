# Test Fixtures

This directory contains deterministic static data used by the test suite.

## `analysis/daily_observations.csv`

Small synthetic daily regional observations.

Purpose:

- test persistent analysis results
- test CSV loading
- test date handling
- test time-series processing
- provide deterministic numeric values for assertions

The data is synthetic and does not represent real Hudson Bay observations.

## `config/test_regions.json`

Small synthetic region definitions following the structure of the production region configuration.

Purpose:

- test configuration loading
- provide deterministic region definitions
- support spatial component and integration tests

The regions are synthetic and independent of the production configuration.