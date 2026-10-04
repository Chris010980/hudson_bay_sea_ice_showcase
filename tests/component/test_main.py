"""Component tests for the pipeline dispatcher (issue #73).

The tests verify the CLI dispatcher in src/main.py
(tests/Findings.md, F-022):

* argument parsing of every pipeline stage,
* propagation of --log-level/--log-file to the stage modules,
* forwarding of the plots flags (--regions, --region,
  --all-regions, --show) and of --keep-data to the update
  stage,
* and the complete "all" sequence.

Test design:

* The stage modules are injected explicitly through the
  ``stages`` mapping parameter introduced in issue #73; no
  namespace patching is required.
* Every test passes an explicit --log-file below the pytest
  temporary directory so the dispatcher never writes to the
  production log file.

All tests are deterministic and require no network access.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.logging_config import DEFAULT_LOG_FILE
from src.main import build_stage_args, main, parse_args


def test_parse_args_stage_defaults() -> None:
    """Every plain stage parses with the common defaults."""

    for stage in ("download", "process", "build"):
        args = parse_args([stage])

        assert args.stage == stage
        assert args.log_level == "INFO"
        assert args.log_file == str(DEFAULT_LOG_FILE)


def test_parse_args_plots_flags() -> None:
    """The plots stage parses all stage-specific flags."""

    args = parse_args(
        [
            "plots",
            "timeseries",
            "--regions",
            "--region",
            "Region A",
            "Region B",
            "--all-regions",
            "--show",
        ]
    )

    assert args.stage == "plots"
    assert args.plot_type == "timeseries"
    assert args.regions is True
    assert args.region == ["Region A", "Region B"]
    assert args.all_regions is True
    assert args.show is True


def test_parse_args_update_keep_data() -> None:
    """The update stage parses the --keep-data flag."""

    args = parse_args(["update", "--keep-data"])

    assert args.stage == "update"
    assert args.keep_data is True


def test_build_stage_args_plain_stage() -> None:
    """A plain stage receives only the logging arguments."""

    args = parse_args(["build"])

    assert build_stage_args(args) == [
        "--log-level",
        "INFO",
        "--log-file",
        str(DEFAULT_LOG_FILE),
    ]


def test_build_stage_args_plots_flags() -> None:
    """The plots flags are forwarded in the documented order."""

    args = parse_args(
        [
            "plots",
            "overview",
            "--regions",
            "--region",
            "Region A",
            "--all-regions",
            "--show",
        ]
    )

    assert build_stage_args(args) == [
        "--log-level",
        "INFO",
        "--log-file",
        str(DEFAULT_LOG_FILE),
        "overview",
        "--regions",
        "--region",
        "Region A",
        "--all-regions",
        "--show",
    ]


def test_build_stage_args_update_keep_data() -> None:
    """--keep-data is forwarded to the update stage."""

    args = parse_args(["update", "--keep-data"])

    assert build_stage_args(args) == [
        "--log-level",
        "INFO",
        "--log-file",
        str(DEFAULT_LOG_FILE),
        "--keep-data",
    ]


def test_dispatcher_runs_selected_stage(tmp_path: Path) -> None:
    """The selected stage receives the forwarded arguments."""

    calls: list[list[str]] = []

    main(
        ["download", "--log-file", str(tmp_path / "dispatch.log")],
        stages={"download": calls.append},
    )

    assert calls == [
        [
            "--log-level",
            "INFO",
            "--log-file",
            str(tmp_path / "dispatch.log"),
        ]
    ]


def test_dispatcher_runs_all_stages_in_order(tmp_path: Path) -> None:
    """The "all" stage runs download, process, plots, build."""

    events: list[str] = []

    main(
        ["all", "--log-file", str(tmp_path / "dispatch.log")],
        stages={
            "download": lambda argv: events.append("download"),
            "process": lambda argv: events.append("process"),
            "plots": lambda argv: events.append("plots"),
            "build": lambda argv: events.append("build"),
        },
    )

    assert events == ["download", "process", "plots", "build"]


def test_parse_args_rejects_unknown_stage() -> None:
    """An unknown stage is rejected with argparse's exit."""

    with pytest.raises(SystemExit):
        parse_args(["inspect"])
