"""Unit tests for the pipeline dispatcher (issues #73, #97).

The tests verify the CLI dispatcher in src/main.py
(tests/Findings.md, F-022):

* argument parsing of every pipeline stage,
* propagation of --log-level/--log-file to the stage modules,
* full option forwarding per stage (CLI parity, issue #106:
  download/process/plots options and --keep-data),
* the parity of the dispatcher sub-parsers with the stage
  module parsers,
* and the complete "all" sequence including the plot type.

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

from src.analysis.process_data import (
    parse_args as parse_process_args,
)
from src.config.logging_config import DEFAULT_LOG_FILE
from src.config.settings import DEFAULT_PRODUCT
from src.data_download.download_data import (
    parse_args as parse_download_args,
)
from src.data_download.downloader import (
    DEFAULT_GEOTIFF_DIR,
    DEFAULT_NSIDC_GEOTIFF_URL,
)
from src.main import build_stage_args, main, parse_args
from src.update.update_pipeline import (
    parse_args as parse_update_args,
)
from src.visualization.generate_plots import (
    parse_args as parse_plots_args,
)
from src.visualization.geotiff_plot import (
    DEFAULT_OUTPUT_PLOT_PATH,
    DEFAULT_REGION_BOUNDS,
)


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
    """The plots options are forwarded in the documented order."""

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

    expected = [
        "--log-level",
        "INFO",
        "--log-file",
        str(DEFAULT_LOG_FILE),
        "overview",
        "--output",
        str(DEFAULT_OUTPUT_PLOT_PATH),
        "--bounds",
    ]

    expected.extend(str(bound) for bound in DEFAULT_REGION_BOUNDS)

    expected.extend(
        [
            "--regions",
            "--region",
            "Region A",
            "--all-regions",
            "--show",
        ]
    )

    assert build_stage_args(args) == expected


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
    """The selected stage receives the forwarded arguments.

    Since issue #106 the download stage receives every live
    option with its value (CLI parity).
    """

    calls: list[list[str]] = []

    main(
        ["download", "--log-file", str(tmp_path / "dispatch.log")],
        stages={"download": calls.append},
    )

    expected = [
        "--log-level",
        "INFO",
        "--log-file",
        str(tmp_path / "dispatch.log"),
        "--base-url",
        str(DEFAULT_NSIDC_GEOTIFF_URL),
        "--output-dir",
        str(DEFAULT_GEOTIFF_DIR),
        "--product",
        DEFAULT_PRODUCT,
    ]

    assert calls == [expected]


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


def test_build_stage_args_download_filters() -> None:
    """The download stage options are forwarded with values."""

    args = parse_args(
        [
            "download",
            "--base-url",
            "https://example.test/archive/",
            "--output-dir",
            "data/custom",
            "--product",
            "test-product",
            "--year",
            "2024",
            "--year",
            "2025",
            "--month",
            "3",
            "--dry-run",
        ]
    )

    assert build_stage_args(args) == [
        "--log-level",
        "INFO",
        "--log-file",
        str(DEFAULT_LOG_FILE),
        "--base-url",
        "https://example.test/archive/",
        "--output-dir",
        "data/custom",
        "--product",
        "test-product",
        "--year",
        "2024",
        "--year",
        "2025",
        "--month",
        "3",
        "--dry-run",
    ]


def test_build_stage_args_process_dates() -> None:
    """The process stage date filters are forwarded."""

    args = parse_args(
        [
            "process",
            "--start-date",
            "2026-03-01",
            "--end-date",
            "2026-03-31",
        ]
    )

    assert build_stage_args(args) == [
        "--log-level",
        "INFO",
        "--log-file",
        str(DEFAULT_LOG_FILE),
        "--start-date",
        "2026-03-01",
        "--end-date",
        "2026-03-31",
    ]


def test_dispatcher_subparsers_match_stage_modules() -> None:
    """Every stage sub-parser mirrors its module parser (#106)."""

    download = parse_args(["download"])
    module_download = parse_download_args([])

    assert download.base_url == module_download.base_url
    assert download.output_dir == module_download.output_dir
    assert download.product == module_download.product
    assert download.years == module_download.years
    assert download.months == module_download.months
    assert download.dry_run == module_download.dry_run

    process = parse_args(["process"])
    module_process = parse_process_args([])

    assert process.start_date == module_process.start_date
    assert process.end_date == module_process.end_date

    plots = parse_args(["plots", "all"])
    module_plots = parse_plots_args(["all"])

    assert plots.input_tiff == module_plots.input_tiff
    assert plots.output == module_plots.output
    assert plots.bounds == module_plots.bounds
    assert plots.regions == module_plots.regions
    assert plots.region == module_plots.region
    assert plots.all_regions == module_plots.all_regions
    assert plots.show == module_plots.show

    update = parse_args(["update"])
    module_update = parse_update_args([])

    assert update.keep_data == module_update.keep_data


def test_dispatcher_all_mode_passes_plot_type_all(
    tmp_path: Path,
) -> None:
    """The "all" pipeline forwards the plot type "all" (#106).

    The plots stage requires its positional plot type; without
    it every real "all" run would exit in the argument parser
    (the unit tests previously masked this with fake stages).
    """

    calls: dict[str, list[str]] = {}

    def recorder(stage: str):
        def stage_main(argv):
            calls[stage] = list(argv or [])

        return stage_main

    main(
        ["all", "--log-file", str(tmp_path / "dispatch.log")],
        stages={
            "download": recorder("download"),
            "process": recorder("process"),
            "plots": recorder("plots"),
            "build": recorder("build"),
        },
    )

    assert calls["plots"] == [
        "--log-level",
        "INFO",
        "--log-file",
        str(tmp_path / "dispatch.log"),
        "all",
    ]

    assert calls["download"] == calls["process"]
    assert calls["process"] == calls["build"]
