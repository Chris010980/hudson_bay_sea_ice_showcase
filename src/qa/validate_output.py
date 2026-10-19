"""QA validation of the daily pipeline output (issue #41).

The validator checks the real production outputs of the
daily update against the documented schemas and consistency
rules (docs/testing/qa-validation.md; regression case
"malformed output files", test-levels.md section 6.3).
Every check is a pure function returning the list of issues;
``main()`` aggregates them over the configured paths and
returns the issue count, so the script can gate a
deployment through its exit code.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.config.logging_config import (
    add_log_arguments,
    configure_logging,
)
from src.config.paths import (
    BUILD_DIR,
    ICE_COVERAGE_EVENTS_CSV,
    ICE_COVERAGE_SUMMARY_CSV,
    ICE_COVERAGE_TIMESERIES_CSV,
    ICE_COVERAGE_YEARLY_CSV,
    LATEST_JSON,
    PLOTS_DIR,
    REFERENCE_SUMMARY_JSON,
)

logger = logging.getLogger(__name__)

# Schemas of the persisted products (ice_coverage_summary
# columns of the ResultsManager, yearly/events columns of the
# TimeSeriesAnalyzer).

SUMMARY_COLUMNS = [
    "region",
    "date",
    "water_pixels",
    "water_area_km2",
    "absolute_ice_area_km2",
    "relative_ice_area_km2",
    "absolute_coverage_percent",
    "relative_coverage_percent",
    "missing_pixels",
]

TIMESERIES_REQUIRED_COLUMNS = [
    "region",
    "date",
    "relative_coverage_percent",
    "absolute_coverage_percent",
    "relative_anomaly_percent",
    "absolute_anomaly_percent",
]

YEARLY_COLUMNS = [
    "region",
    "year",
    "relative_mean_coverage_percent",
    "absolute_mean_coverage_percent",
    "relative_mean_ice_area_km2",
    "absolute_mean_ice_area_km2",
    "relative_mean_trend_slope",
    "relative_mean_trend_intercept",
    "relative_mean_trend_r_squared",
]

EVENTS_COLUMNS = [
    "region",
    "event_type",
    "event_year",
    "threshold_percent",
    "event_date",
]

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def validate_summary_frame(
    df: pd.DataFrame,
    expected_regions: set[str],
) -> list[str]:
    """Check schema, dates, ordering, regions and bounds."""

    issues: list[str] = []

    if df.empty:
        return ["Summary CSV contains no observations."]

    if list(df.columns) != SUMMARY_COLUMNS:
        issues.append(
            "Summary columns differ from the persisted schema."
        )

    dates = pd.to_datetime(
        df["date"],
        format="%Y-%m-%d",
        errors="coerce",
    )

    if dates.isna().any():
        issues.append("Summary contains malformed (non-ISO) dates.")

    if df.duplicated(subset=["date", "region"]).any():
        issues.append("Summary contains duplicate (date, region) rows.")

    ordered = df.sort_values(
        ["date", "region"],
    ).reset_index(drop=True)

    if (
        not df[["date", "region"]]
        .reset_index(drop=True)
        .equals(ordered[["date", "region"]])
    ):
        issues.append("Summary is not sorted by (date, region).")

    unknown = set(df["region"]) - expected_regions

    if unknown:
        issues.append(f"Summary contains unknown regions: {unknown}.")

    for column in (
        "relative_coverage_percent",
        "absolute_coverage_percent",
    ):
        values = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        if values.isna().any() or not values.between(0.0, 100.0).all():
            issues.append(
                f"Summary column {column} has values outside"
                " [0, 100] or missing."
            )

    return issues


def validate_latest_json(
    payload: dict,
    summary_df: pd.DataFrame,
) -> list[str]:
    """Check the latest marker against the summary state."""

    issues: list[str] = []

    required = {
        "dataset",
        "date",
        "generated",
        "observations",
        "regions",
    }

    missing = required - set(payload)

    if missing:
        return [f"latest.json is missing keys: {sorted(missing)}."]

    latest_date = summary_df["date"].max()

    if payload["date"] != latest_date:
        issues.append(
            "latest.json date does not match the newest"
            " summary observation."
        )

    if payload["observations"] != len(summary_df):
        issues.append(
            "latest.json observation count does not match"
            " the summary row count."
        )

    if not str(payload["generated"]).endswith("Z"):
        issues.append("latest.json generated timestamp is malformed.")

    latest_regions = set(
        summary_df[summary_df["date"] == latest_date]["region"]
    )

    payload_regions = {
        record["region"] for record in payload["regions"]
    }

    if payload_regions != latest_regions:
        issues.append(
            "latest.json regions do not match the regions"
            " of the newest observation."
        )

    return issues


def validate_timeseries_frame(
    summary_df: pd.DataFrame,
    timeseries_df: pd.DataFrame,
) -> list[str]:
    """Check that the time series contains every observation."""

    missing_columns = [
        column
        for column in TIMESERIES_REQUIRED_COLUMNS
        if column not in timeseries_df.columns
    ]

    if missing_columns:
        return [
            f"Timeseries product is missing columns: {missing_columns}."
        ]

    issues: list[str] = []

    summary_keys = set(
        zip(
            summary_df["date"],
            summary_df["region"],
            strict=True,
        )
    )

    timeseries_keys = set(
        zip(
            timeseries_df["date"],
            timeseries_df["region"],
            strict=True,
        )
    )

    if not summary_keys <= timeseries_keys:
        issues.append(
            "Timeseries product is missing summary observations."
        )

    if timeseries_df.duplicated(subset=["date", "region"]).any():
        issues.append(
            "Timeseries product contains duplicate (date, region) rows."
        )

    return issues


def validate_yearly_frame(yearly_df: pd.DataFrame) -> list[str]:
    """Check the yearly product schema (empty is valid)."""

    if yearly_df.empty:
        return []

    if list(yearly_df.columns) != YEARLY_COLUMNS:
        return [
            "Yearly product columns differ from the persisted schema."
        ]

    years = pd.to_numeric(
        yearly_df["year"],
        errors="coerce",
    )

    if years.isna().any():
        return ["Yearly product contains malformed years."]

    return []


def validate_events_frame(events_df: pd.DataFrame) -> list[str]:
    """Check the events product schema (empty is valid)."""

    if events_df.empty:
        return []

    if list(events_df.columns) != EVENTS_COLUMNS:
        return [
            "Events product columns differ from the persisted schema."
        ]

    unknown = set(events_df["event_type"]) - {
        "break-up",
        "freeze-up",
    }

    if unknown:
        return [f"Events product contains unknown types: {unknown}."]

    return []


def _daily_products(region: str) -> list[str]:
    """Expected daily plot products of one region."""

    safe = region.replace(" ", "_")

    return [
        "daily_timeseries/classical_timeseries/relative/"
        f"{safe}_relative.png",
        "daily_timeseries/classical_timeseries/absolute/"
        f"{safe}_absolute.png",
        "daily_timeseries/anomalies/relative/"
        f"{safe}_relative_anomaly.png",
        "daily_timeseries/anomalies/absolute/"
        f"{safe}_absolute_anomaly.png",
        f"daily_timeseries/polar/relative/{safe}_polar_relative.png",
        f"daily_timeseries/polar/absolute/{safe}_polar_absolute.png",
    ]


def _yearly_products(region: str) -> list[str]:
    """Expected yearly plot products of one region."""

    safe = region.replace(" ", "_")

    return [
        "yearly_timeseries/thresholds/relative/"
        f"{safe}_threshold_duration.png",
        "yearly_timeseries/yearly_means/relative/"
        f"{safe}_yearly_mean_relative.png",
    ]


def validate_plots_inventory(
    plots_dir: Path,
    regions: set[str],
) -> list[str]:
    """Check the plot products of every region.

    The daily products are required for every region. The
    yearly products are required only when the
    ``yearly_timeseries`` product class exists (fresh
    datasets without complete years skip them, F-031).
    """

    issues: list[str] = []

    for region in sorted(regions):
        expected = _daily_products(region)

        if (plots_dir / "yearly_timeseries").exists():
            expected += _yearly_products(region)

        for name in expected:
            path = plots_dir / name

            if not path.exists():
                issues.append(f"Missing plot product: {name}.")

            elif not path.read_bytes().startswith(_PNG_MAGIC):
                issues.append(f"Plot product is not a PNG: {name}.")

    return issues


def validate_build_inventory(
    build_dir: Path,
    summary_df: pd.DataFrame,
) -> list[str]:
    """Check the built website against the summary state."""

    issues: list[str] = []

    if not (build_dir / "index.html").exists():
        issues.append("Build is missing index.html.")

    built_csv = (
        build_dir / "output" / "analysis" / "ice_coverage_summary.csv"
    )

    if not built_csv.exists():
        issues.append("Build is missing the summary CSV.")

        return issues

    built_df = pd.read_csv(built_csv)

    columns = [
        "date",
        "region",
        "relative_coverage_percent",
        "absolute_coverage_percent",
    ]

    summary_sorted = (
        summary_df[columns]
        .sort_values(["date", "region"])
        .reset_index(drop=True)
    )

    built_sorted = (
        built_df[columns]
        .sort_values(["date", "region"])
        .reset_index(drop=True)
    )

    if not summary_sorted.equals(built_sorted):
        issues.append(
            "Built summary CSV differs from the analysis summary."
        )

    built_latest = build_dir / "output" / "analysis" / "latest.json"

    if not built_latest.exists():
        issues.append("Build is missing latest.json.")

    else:
        with open(built_latest, encoding="utf-8") as file:
            payload = json.load(file)

        if payload.get("date") != summary_df["date"].max():
            issues.append(
                "Built latest.json date does not match the"
                " newest observation."
            )

    return issues


def _load_frame(path: Path) -> pd.DataFrame:
    """Read a derived CSV product; empty means empty frame.

    A missing file and the empty product of a fresh dataset
    (0 bytes, F-031) both yield an empty frame; the callers
    decide whether that state is an issue.
    """

    try:
        return pd.read_csv(path)

    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse the QA validation options."""

    parser = argparse.ArgumentParser(
        description="Validate the daily pipeline output."
    )

    add_log_arguments(parser)

    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    summary_path: Path = ICE_COVERAGE_SUMMARY_CSV,
    latest_path: Path = LATEST_JSON,
    timeseries_path: Path = ICE_COVERAGE_TIMESERIES_CSV,
    yearly_path: Path = ICE_COVERAGE_YEARLY_CSV,
    events_path: Path = ICE_COVERAGE_EVENTS_CSV,
    plots_dir: Path = PLOTS_DIR,
    build_dir: Path = BUILD_DIR,
    reference_path: Path = REFERENCE_SUMMARY_JSON,
) -> int:
    """Validate the pipeline outputs; return the issue count.

    Returns 0 when no issue is found and the number of
    issues otherwise, so the script can gate a deployment
    through its exit code. All paths are injectable keyword
    arguments with the production defaults from
    ``src/config/paths.py`` (#73 pattern).
    """

    args = parse_args(argv)

    configure_logging(
        level=args.log_level,
        log_file=args.log_file,
    )

    issues: list[str] = []

    if not reference_path.exists():
        logger.error(
            "Missing reference summary: %s",
            reference_path,
        )

        return 1

    with open(reference_path, encoding="utf-8") as file:
        expected_regions = set(json.load(file))

    if not summary_path.exists():
        logger.error("Missing summary CSV: %s", summary_path)

        return 1

    summary_df = pd.read_csv(summary_path)

    issues += validate_summary_frame(
        summary_df,
        expected_regions,
    )

    if latest_path.exists():
        with open(latest_path, encoding="utf-8") as file:
            issues += validate_latest_json(
                json.load(file),
                summary_df,
            )

    else:
        issues.append("Missing latest.json.")

    timeseries_df = _load_frame(timeseries_path)

    if timeseries_df.empty:
        issues.append("Timeseries product is missing or empty.")

    else:
        issues += validate_timeseries_frame(
            summary_df,
            timeseries_df,
        )

    issues += validate_yearly_frame(
        _load_frame(yearly_path),
    )

    issues += validate_events_frame(
        _load_frame(events_path),
    )

    issues += validate_plots_inventory(
        plots_dir,
        expected_regions,
    )

    issues += validate_build_inventory(
        build_dir,
        summary_df,
    )

    for issue in issues:
        logger.error("QA issue: %s", issue)

    logger.info(
        "QA validation found %d issue(s).",
        len(issues),
    )

    return len(issues)


if __name__ == "__main__":
    sys.exit(main())
