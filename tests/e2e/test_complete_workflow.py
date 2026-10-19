"""End-to-end test for the complete processing workflow
(issue #41, docs/testing/test-levels.md, section 5.2).

The test runs the representative E2E scenario against
isolated directories; every production stage is real:

    controlled observation GeoTIFFs
          |
          v
    ReferenceBuilder (injected paths, issue #104)
          |
          v
    RegionAnalyzer
          |
          v
    ResultsManager -> summary CSV + latest.json
          |
          v
    TimeSeriesAnalyzer -> timeseries/yearly/events CSV
          |
          v
    generate_plots CLI ("timeseries", F-018 seams)
          |
          v
    build_pages -> isolated build/ website

Only two external inputs are controlled (test-levels.md,
section 9): the naturalearth ocean dataset is replaced by a
controlled polygon, and the production directories are
snapshot-compared before and after the run.

The observations reuse the hand-calculated values of
tests/integration/test_spatial_processing_chain.py
(2026-03-01 and 2026-03-02). For the two-day dataset the
yearly product is empty; the F-031 guard keeps the plot
stage operable in that fresh-dataset state.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

import src.analysis.reference_builder as reference_builder_module
import src.update.build_pages as build_pages_module
import src.visualization.generate_plots as generate_plots_module
from src.analysis.reference_builder import ReferenceBuilder
from src.analysis.region_analyzer import RegionAnalyzer
from src.analysis.results_manager import ResultsManager
from src.analysis.timeseries_analyzer import TimeSeriesAnalyzer
from src.config.paths import PROJECT_ROOT
from src.visualization.timeseries_plot import TimeSeriesPlotter

# Persisted rows expected after the workflow (hand
# calculations, identical to the spatial chain integration
# tests):

_DAY_1_MIXED = {
    "region": "Test Region Mixed",
    "date": "2026-03-01",
    "water_pixels": 1,
    "water_area_km2": 625.0,
    "absolute_ice_area_km2": 625.0,
    "relative_ice_area_km2": 500.0,
    "absolute_coverage_percent": 100.0,
    "relative_coverage_percent": 80.0,
    "missing_pixels": 0,
}

_DAY_1_WATER = {
    "region": "Test Region Water",
    "date": "2026-03-01",
    "water_pixels": 4,
    "water_area_km2": 2500.0,
    "absolute_ice_area_km2": 1250.0,
    "relative_ice_area_km2": 625.0,
    "absolute_coverage_percent": 50.0,
    "relative_coverage_percent": 25.0,
    "missing_pixels": 0,
}

_DAY_2_MIXED = {
    "region": "Test Region Mixed",
    "date": "2026-03-02",
    "water_pixels": 1,
    "water_area_km2": 625.0,
    "absolute_ice_area_km2": 0.0,
    "relative_ice_area_km2": 0.0,
    "absolute_coverage_percent": 0.0,
    "relative_coverage_percent": 0.0,
    "missing_pixels": 0,
}

_DAY_2_WATER = {
    "region": "Test Region Water",
    "date": "2026-03-02",
    "water_pixels": 4,
    "water_area_km2": 2500.0,
    "absolute_ice_area_km2": 1875.0,
    "relative_ice_area_km2": 843.75,
    "absolute_coverage_percent": 75.0,
    "relative_coverage_percent": 33.75,
    "missing_pixels": 0,
}

_FLOAT_COLUMNS = {
    "water_area_km2",
    "absolute_ice_area_km2",
    "relative_ice_area_km2",
    "absolute_coverage_percent",
    "relative_coverage_percent",
}


class _StubGeopandas:
    """geopandas stand-in serving a controlled ocean dataset."""

    def __init__(self, ocean: gpd.GeoDataFrame) -> None:
        self._ocean = ocean

    def read_file(self, path) -> gpd.GeoDataFrame:
        return self._ocean

    def __getattr__(self, name):
        return getattr(gpd, name)


def _write_observation(
    data_dir: Path,
    filename: str,
    values: dict[int, int],
) -> Path:
    """Write a controlled daily observation GeoTIFF.

    The raster matches the geometry of the synthetic reference
    raster (5 x 5 pixels, EPSG:3411, 25 km pixels). ``values``
    maps flat pixel indices to concentration values on the
    0-1000 scale; all other pixels carry the land code 2510.
    """
    data = np.full((5, 5), 2510, dtype=np.uint16)

    for flat_index, value in values.items():
        data.flat[flat_index] = value

    transform = from_origin(
        west=0,
        north=125_000,
        xsize=25_000,
        ysize=25_000,
    )

    profile = {
        "driver": "GTiff",
        "height": 5,
        "width": 5,
        "count": 1,
        "dtype": data.dtype,
        "crs": "EPSG:3411",
        "transform": transform,
    }

    path = data_dir / filename

    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data, 1)

    return path


def _region_values(
    expected_reference_masks: dict[str, np.ndarray],
    water_values: list[int],
    mixed_values: list[int],
) -> dict[int, int]:
    """Map per-region concentration values to flat pixel indices."""
    return dict(
        zip(
            expected_reference_masks["Test Region Water"],
            water_values,
            strict=True,
        )
    ) | dict(
        zip(
            expected_reference_masks["Test Region Mixed"],
            mixed_values,
            strict=True,
        )
    )


def _assert_row(
    df: pd.DataFrame,
    position: int,
    expected: dict,
) -> None:
    """Assert one persisted CSV row against an expected record."""
    row = df.iloc[position]

    for column, value in expected.items():
        if column in _FLOAT_COLUMNS:
            assert row[column] == pytest.approx(value)
        else:
            assert row[column] == value


def _assert_png_product(path: Path) -> None:
    """Assert a persisted plot product is a non-empty readable PNG."""
    assert path.exists()

    content = path.read_bytes()

    assert len(content) > 0
    assert content.startswith(b"\x89PNG\r\n\x1a\n")

    image = plt.imread(path)

    assert image.size > 0


def _file_snapshot(path: Path) -> bytes | None:
    """Read a file's bytes for a before/after comparison."""
    if not path.exists():
        return None
    return path.read_bytes()


def _directory_snapshot(directory: Path) -> list[str]:
    """List a directory's entries for a before/after comparison."""
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.iterdir())


@pytest.fixture
def e2e_workflow_environment(
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Isolate the complete workflow in the test environment.

    Provides the isolated stage paths (reference products,
    analysis products, plots, website source and build) and
    replaces the naturalearth ocean dataset with a controlled
    ocean polygon, so that no production data is read or
    written (test-levels.md, sections 8 and 9).
    """
    output_dir = test_environment["output"]

    reference_dir = output_dir / "reference"
    mask_dir = reference_dir / "filters"
    reference_json = reference_dir / "reference_summary.json"

    analysis_dir = output_dir / "analysis"
    plots_dir = output_dir / "plots"

    html_dir = test_environment["root"] / "html"
    build_dir = test_environment["build"]

    ocean = gpd.GeoDataFrame(
        geometry=[
            Polygon(
                [(-180, 80), (180, 80), (180, 90), (-180, 90)],
            )
        ],
        crs="EPSG:4326",
    )
    monkeypatch.setattr(
        reference_builder_module,
        "gpd",
        _StubGeopandas(ocean),
    )

    html_dir.mkdir()
    (html_dir / "index.html").write_text(
        "<html><body>site</body></html>",
        encoding="utf-8",
    )

    return {
        "mask_dir": mask_dir,
        "reference_json": reference_json,
        "csv": analysis_dir / "ice_coverage_summary.csv",
        "latest": analysis_dir / "latest.json",
        "timeseries": analysis_dir / "ice_coverage_timeseries.csv",
        "yearly": analysis_dir / "ice_coverage_yearly.csv",
        "events": analysis_dir / "ice_coverage_events.csv",
        "plots_dir": plots_dir,
        "html_dir": html_dir,
        "build_dir": build_dir,
        "log_file": test_environment["root"] / "e2e.log",
        "ts_factory": functools.partial(
            TimeSeriesPlotter,
            csv_file=analysis_dir / "ice_coverage_timeseries.csv",
            yearly_csv_file=analysis_dir / "ice_coverage_yearly.csv",
            events_csv_file=analysis_dir / "ice_coverage_events.csv",
            output_dir=plots_dir,
        ),
    }


def test_complete_workflow_produces_all_artifacts(
    e2e_workflow_environment: dict,
    test_environment: dict[str, Path],
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
    expected_reference_masks: dict[str, np.ndarray],
) -> None:
    """The complete workflow creates every intended artifact.

    Controlled inputs: the synthetic reference raster and region
    definitions plus two observation GeoTIFFs (2026-03-01 and
    2026-03-02, hand values of the spatial chain tests).

    Verified (test-levels.md, section 5.2):

    * the workflow succeeds end to end,
    * the intermediate reference products are created,
    * the persisted results and the derived analytical
      products match the hand calculations,
    * the expected classical plots exist as readable PNGs,
    * the website build is complete,
    * and no production file is modified.
    """
    env = e2e_workflow_environment

    production_filters = (
        PROJECT_ROOT / "output" / "reference" / "filters"
    )
    production_summary = (
        PROJECT_ROOT / "output" / "reference" / "reference_summary.json"
    )
    production_csv = (
        PROJECT_ROOT
        / "output"
        / "analysis"
        / "ice_coverage_summary.csv"
    )
    production_latest = (
        PROJECT_ROOT / "output" / "analysis" / "latest.json"
    )

    before = {
        "filters": _directory_snapshot(production_filters),
        "summary": _file_snapshot(production_summary),
        "csv": _file_snapshot(production_csv),
        "latest": _file_snapshot(production_latest),
    }

    # Stage 1: reference products (real ReferenceBuilder).
    ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
        mask_dir=env["mask_dir"],
        summary_path=env["reference_json"],
    ).build()

    # Stages 2 and 3: observations through the real
    # RegionAnalyzer into the real ResultsManager.
    observations = [
        _write_observation(
            test_environment["data"],
            "N_20260301_concentration_v1.0.tif",
            _region_values(
                expected_reference_masks,
                water_values=[400, 600, 100, 0],
                mixed_values=[800],
            ),
        ),
        _write_observation(
            test_environment["data"],
            "N_20260302_concentration_v1.0.tif",
            _region_values(
                expected_reference_masks,
                water_values=[150, 1000, 0, 200],
                mixed_values=[0],
            ),
        ),
    ]

    manager = ResultsManager(
        csv_path=env["csv"],
        latest_json_path=env["latest"],
    )

    for observation in observations:
        analyzer = RegionAnalyzer(
            input_tif=observation,
            reference_json=env["reference_json"],
            filter_dir=env["mask_dir"],
        )
        manager.add_results(analyzer.analyze())

    manager.save()

    # Stage 4: temporal analysis (real TimeSeriesAnalyzer).
    timeseries = TimeSeriesAnalyzer(
        csv_path=env["csv"],
        output_path=env["timeseries"],
        yearly_output_path=env["yearly"],
        events_output_path=env["events"],
    )

    timeseries.analyze()
    timeseries.save()

    # Stage 5: plots (real generate_plots CLI via the seams).
    generate_plots_module.main(
        [
            "timeseries",
            "--log-file",
            str(env["log_file"]),
        ],
        ts_factory=env["ts_factory"],
    )

    # Stage 6: website build (real build_pages).
    build_pages_module.main(
        [
            "--log-file",
            str(env["log_file"]),
        ],
        html_dir=env["html_dir"],
        output_dir=test_environment["output"],
        build_dir=env["build_dir"],
    )

    # Intermediate reference products exist.
    for region in expected_reference_masks:
        assert (env["mask_dir"] / f"{region}_water.npy").exists()

    assert env["reference_json"].exists()

    # Persisted results match the hand calculations.
    df = pd.read_csv(env["csv"])

    assert len(df) == 4

    expected_rows = [
        _DAY_1_MIXED,
        _DAY_1_WATER,
        _DAY_2_MIXED,
        _DAY_2_WATER,
    ]

    for position, expected in enumerate(expected_rows):
        _assert_row(df, position, expected)

    with open(env["latest"], encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["date"] == "2026-03-02"
    assert payload["observations"] == 4

    # Derived analytical products exist and stay consistent.
    timeseries_df = pd.read_csv(env["timeseries"])

    assert len(timeseries_df) == 4

    assert env["yearly"].exists()
    assert env["events"].exists()

    # Expected plots exist as readable PNGs.
    classical_dir = (
        env["plots_dir"] / "daily_timeseries" / "classical_timeseries"
    )

    expected_plots = {
        "Test_Region_Water_relative.png",
        "Test_Region_Water_absolute.png",
        "Test_Region_Mixed_relative.png",
        "Test_Region_Mixed_absolute.png",
    }

    actual_plots = {path.name for path in classical_dir.glob("*/*.png")}

    assert actual_plots == expected_plots

    for path in classical_dir.glob("*/*.png"):
        _assert_png_product(path)

    # The website build is complete.
    assert (env["build_dir"] / "index.html").exists()

    built_latest = (
        env["build_dir"] / "output" / "analysis" / "latest.json"
    )

    with open(built_latest, encoding="utf-8") as file:
        built_payload = json.load(file)

    assert built_payload["date"] == "2026-03-02"

    built_csv = pd.read_csv(
        env["build_dir"]
        / "output"
        / "analysis"
        / "ice_coverage_summary.csv",
    )

    assert len(built_csv) == 4

    # No production file was modified.
    assert (
        _directory_snapshot(production_filters) == (before["filters"])
    )
    assert _file_snapshot(production_summary) == before["summary"]
    assert _file_snapshot(production_csv) == before["csv"]
    assert _file_snapshot(production_latest) == before["latest"]
