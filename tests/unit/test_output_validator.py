"""Unit tests for the QA output validator (issue #41).

``src/qa/validate_output.py`` implements the QA validation
of the daily pipeline output (docs/testing/
qa-validation.md; regression case "malformed output
files", test-levels.md section 6.3). Every check is a pure
function; the inventory and ``main()`` tests use only
pytest's temporary directories. No network access, no
production paths.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.qa.validate_output import (
    EVENTS_COLUMNS,
    TIMESERIES_REQUIRED_COLUMNS,
    YEARLY_COLUMNS,
    main,
    validate_build_inventory,
    validate_events_frame,
    validate_latest_json,
    validate_plots_inventory,
    validate_summary_frame,
    validate_timeseries_frame,
    validate_yearly_frame,
)

_REGIONS = {"Test Region Water", "Test Region Mixed"}

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _summary_frame() -> pd.DataFrame:
    """A minimal valid summary state (two regions, one day)."""

    return pd.DataFrame(
        {
            "region": [
                "Test Region Mixed",
                "Test Region Water",
            ],
            "date": ["2026-03-01", "2026-03-01"],
            "water_pixels": [1, 4],
            "water_area_km2": [625.0, 2500.0],
            "absolute_ice_area_km2": [625.0, 1250.0],
            "relative_ice_area_km2": [500.0, 625.0],
            "absolute_coverage_percent": [100.0, 50.0],
            "relative_coverage_percent": [80.0, 25.0],
            "missing_pixels": [0, 0],
        }
    )


def _latest_payload(summary_df: pd.DataFrame) -> dict:
    """A latest.json payload consistent with the summary."""

    latest_date = summary_df["date"].max()

    regions = sorted(
        summary_df[summary_df["date"] == latest_date]["region"]
    )

    return {
        "dataset": "NSIDC G02135",
        "date": latest_date,
        "generated": "2026-03-01T12:00:00Z",
        "observations": len(summary_df),
        "regions": [{"region": region} for region in regions],
    }


def _timeseries_frame(summary_df: pd.DataFrame) -> pd.DataFrame:
    """A timeseries product containing every observation."""

    df = summary_df[
        [
            "region",
            "date",
            "relative_coverage_percent",
            "absolute_coverage_percent",
        ]
    ].copy()

    df["relative_anomaly_percent"] = 0.0
    df["absolute_anomaly_percent"] = 0.0

    return df


def _write_png(path: Path) -> None:
    """Write a minimal PNG-magic product file."""

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_bytes(_PNG_MAGIC + b"payload")


def _write_valid_state(root: Path) -> dict[str, Path]:
    """Write a complete valid pipeline output state."""

    analysis_dir = root / "output" / "analysis"
    plots_dir = root / "output" / "plots"
    build_dir = root / "build"
    reference_path = (
        root / "output" / "reference" / ("reference_summary.json")
    )

    analysis_dir.mkdir(parents=True, exist_ok=True)

    summary_df = _summary_frame()

    summary_path = analysis_dir / "ice_coverage_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    latest_path = analysis_dir / "latest.json"
    latest_path.write_text(
        json.dumps(_latest_payload(summary_df)),
        encoding="utf-8",
    )

    timeseries_path = analysis_dir / "ice_coverage_timeseries.csv"
    _timeseries_frame(summary_df).to_csv(
        timeseries_path,
        index=False,
    )

    yearly_path = analysis_dir / "ice_coverage_yearly.csv"
    pd.DataFrame(columns=YEARLY_COLUMNS).to_csv(
        yearly_path,
        index=False,
    )

    events_path = analysis_dir / "ice_coverage_events.csv"
    pd.DataFrame(columns=EVENTS_COLUMNS).to_csv(
        events_path,
        index=False,
    )

    reference_path.parent.mkdir(parents=True, exist_ok=True)
    reference_path.write_text(
        json.dumps(
            {
                "Test Region Water": {"water_pixels": 4},
                "Test Region Mixed": {"water_pixels": 1},
            }
        ),
        encoding="utf-8",
    )

    for region in _REGIONS:
        safe = region.replace(" ", "_")

        _write_png(
            plots_dir
            / "daily_timeseries"
            / "classical_timeseries"
            / "relative"
            / f"{safe}_relative.png"
        )
        _write_png(
            plots_dir
            / "daily_timeseries"
            / "classical_timeseries"
            / "absolute"
            / f"{safe}_absolute.png"
        )
        _write_png(
            plots_dir
            / "daily_timeseries"
            / "anomalies"
            / "relative"
            / f"{safe}_relative_anomaly.png"
        )
        _write_png(
            plots_dir
            / "daily_timeseries"
            / "anomalies"
            / "absolute"
            / f"{safe}_absolute_anomaly.png"
        )
        _write_png(
            plots_dir
            / "daily_timeseries"
            / "polar"
            / "relative"
            / f"{safe}_polar_relative.png"
        )
        _write_png(
            plots_dir
            / "daily_timeseries"
            / "polar"
            / "absolute"
            / f"{safe}_polar_absolute.png"
        )

    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "index.html").write_text(
        "<html><body>site</body></html>",
        encoding="utf-8",
    )

    built_analysis = build_dir / "output" / "analysis"
    built_analysis.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(
        built_analysis / "ice_coverage_summary.csv",
        index=False,
    )
    (built_analysis / "latest.json").write_text(
        json.dumps(_latest_payload(summary_df)),
        encoding="utf-8",
    )

    return {
        "summary_path": summary_path,
        "latest_path": latest_path,
        "timeseries_path": timeseries_path,
        "yearly_path": yearly_path,
        "events_path": events_path,
        "plots_dir": plots_dir,
        "build_dir": build_dir,
        "reference_path": reference_path,
        "log_file": root / "qa.log",
    }


def test_valid_summary_passes() -> None:
    """A valid summary state yields no issue."""

    assert (
        validate_summary_frame(
            _summary_frame(),
            _REGIONS,
        )
        == []
    )


def test_summary_schema_violation_is_reported() -> None:
    """A missing column is reported as a schema issue."""

    df = _summary_frame().drop(columns=["missing_pixels"])

    issues = validate_summary_frame(df, _REGIONS)

    assert len(issues) == 1
    assert "columns" in issues[0]


def test_summary_duplicates_and_bad_dates_are_reported() -> None:
    """Duplicate rows and non-ISO dates are reported."""

    df = pd.concat(
        [_summary_frame(), _summary_frame()],
        ignore_index=True,
    )
    df.loc[0, "date"] = "20260301"

    issues = validate_summary_frame(df, _REGIONS)

    assert len(issues) == 3
    assert any("malformed" in issue for issue in issues)
    assert any("duplicate" in issue for issue in issues)


def test_summary_region_and_coverage_bounds_are_reported() -> None:
    """Unknown regions and out-of-range coverage are reported."""

    df = _summary_frame()
    df.loc[0, "region"] = "AAA Unknown Region"
    df.loc[1, "relative_coverage_percent"] = 150.0

    issues = validate_summary_frame(df, _REGIONS)

    assert len(issues) == 2
    assert any("unknown regions" in issue for issue in issues)
    assert any("outside" in issue for issue in issues)


def test_latest_json_consistency_is_checked() -> None:
    """A consistent payload passes; mismatches are reported."""

    summary_df = _summary_frame()

    assert (
        validate_latest_json(
            _latest_payload(summary_df),
            summary_df,
        )
        == []
    )

    payload = _latest_payload(summary_df)
    payload["date"] = "2020-01-01"
    payload["observations"] = 99

    issues = validate_latest_json(payload, summary_df)

    assert len(issues) == 2
    assert all("match" in issue for issue in issues)


def test_timeseries_consistency_is_checked() -> None:
    """Missing observations and duplicates are reported."""

    summary_df = _summary_frame()

    assert (
        validate_timeseries_frame(
            summary_df,
            _timeseries_frame(summary_df),
        )
        == []
    )

    incomplete = _timeseries_frame(summary_df).iloc[:-1]

    missing = validate_timeseries_frame(
        summary_df,
        incomplete,
    )

    assert len(missing) == 1
    assert "missing summary" in missing[0]

    duplicated = pd.concat(
        [
            _timeseries_frame(summary_df),
            _timeseries_frame(summary_df),
        ],
        ignore_index=True,
    )

    dupes = validate_timeseries_frame(summary_df, duplicated)

    assert any("duplicate" in issue for issue in dupes)


def test_timeseries_schema_is_checked() -> None:
    """Missing required columns are reported."""

    summary_df = _summary_frame()

    broken = _timeseries_frame(summary_df).drop(
        columns=["relative_anomaly_percent"]
    )

    issues = validate_timeseries_frame(summary_df, broken)

    assert len(issues) == 1
    assert "missing columns" in issues[0]
    assert "relative_anomaly_percent" in issues[0]

    assert TIMESERIES_REQUIRED_COLUMNS


def test_yearly_and_events_schemas_are_checked() -> None:
    """Empty products pass; schema deviations are reported."""

    assert validate_yearly_frame(pd.DataFrame()) == []

    bad_yearly = pd.DataFrame(columns=["region", "year", "unexpected"])
    bad_yearly.loc[0] = ["Region A", 2026, 1.0]

    issues = validate_yearly_frame(bad_yearly)

    assert len(issues) == 1
    assert "columns" in issues[0]

    assert validate_events_frame(pd.DataFrame()) == []

    bad_events = pd.DataFrame(
        columns=EVENTS_COLUMNS[:-1] + ["wrong_type"]
    )
    bad_events.loc[0] = [
        "Region A",
        "break-up",
        2026,
        50.0,
        "2026-07-01",
    ]

    issues = validate_events_frame(bad_events)

    assert len(issues) == 1
    assert "columns" in issues[0]


def test_plots_inventory_reports_missing_and_invalid_products(
    tmp_path: Path,
) -> None:
    """Missing and non-PNG products are reported per region."""

    for region in _REGIONS:
        safe = region.replace(" ", "_")

        _write_png(
            tmp_path
            / "daily_timeseries"
            / "classical_timeseries"
            / "relative"
            / f"{safe}_relative.png"
        )

    issues = validate_plots_inventory(tmp_path, _REGIONS)

    # Five of six daily products are missing per region.
    assert len(issues) == 10
    assert all("Missing plot" in issue for issue in issues)

    valid = tmp_path / "plots_valid"
    for region in _REGIONS:
        safe = region.replace(" ", "_")

        _write_png(
            valid
            / "daily_timeseries"
            / "classical_timeseries"
            / "relative"
            / f"{safe}_relative.png"
        )
        absolute_png = (
            valid
            / "daily_timeseries"
            / "classical_timeseries"
            / "absolute"
            / f"{safe}_absolute.png"
        )
        absolute_png.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        absolute_png.write_text(
            "not a png",
            encoding="utf-8",
        )

    issues = validate_plots_inventory(valid, _REGIONS)

    # Four missing + one invalid per region.
    assert len(issues) == 10
    assert any("not a PNG" in issue for issue in issues)


def test_build_inventory_reports_missing_and_mismatched_products(
    tmp_path: Path,
) -> None:
    """A missing index.html and a mismatched CSV are reported."""

    summary_df = _summary_frame()

    empty_build = tmp_path / "empty"

    issues = validate_build_inventory(empty_build, summary_df)

    assert len(issues) == 2
    assert any("index.html" in issue for issue in issues)
    assert any("summary CSV" in issue for issue in issues)

    build = tmp_path / "build"
    analysis = build / "output" / "analysis"
    analysis.mkdir(parents=True)

    (build / "index.html").write_text(
        "<html></html>",
        encoding="utf-8",
    )

    stale = summary_df.copy()
    stale.loc[0, "relative_coverage_percent"] = 42.0
    stale.to_csv(
        analysis / "ice_coverage_summary.csv",
        index=False,
    )
    (analysis / "latest.json").write_text(
        json.dumps({"date": "2020-01-01"}),
        encoding="utf-8",
    )

    issues = validate_build_inventory(build, summary_df)

    assert len(issues) == 2
    assert any("differs" in issue for issue in issues)
    assert any("latest.json" in issue for issue in issues)


def test_main_passes_a_valid_output_state(tmp_path: Path) -> None:
    """A complete valid output state yields the exit code 0."""

    paths = _write_valid_state(tmp_path)

    assert (
        main(
            [
                "--log-file",
                str(paths["log_file"]),
            ],
            summary_path=paths["summary_path"],
            latest_path=paths["latest_path"],
            timeseries_path=paths["timeseries_path"],
            yearly_path=paths["yearly_path"],
            events_path=paths["events_path"],
            plots_dir=paths["plots_dir"],
            build_dir=paths["build_dir"],
            reference_path=paths["reference_path"],
        )
        == 0
    )


def test_main_counts_issues_of_a_corrupted_state(
    tmp_path: Path,
) -> None:
    """A corrupted latest.json is reported and counted."""

    paths = _write_valid_state(tmp_path)

    payload = json.loads(
        paths["latest_path"].read_text(encoding="utf-8")
    )
    payload["date"] = "2020-01-01"
    paths["latest_path"].write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--log-file",
                str(paths["log_file"]),
            ],
            summary_path=paths["summary_path"],
            latest_path=paths["latest_path"],
            timeseries_path=paths["timeseries_path"],
            yearly_path=paths["yearly_path"],
            events_path=paths["events_path"],
            plots_dir=paths["plots_dir"],
            build_dir=paths["build_dir"],
            reference_path=paths["reference_path"],
        )
        == 1
    )
