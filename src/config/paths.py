"""Project-level filesystem paths.

This module is the single source of truth for every path in the
project: modules import the named constants below instead of
constructing paths from local string fragments.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
"""Absolute path to the project root directory, one level above
the ``src`` package.
"""

# ---------------------------------------------------------- root dirs

DATA_DIR = PROJECT_ROOT / "data"
"""Default directory for downloaded or generated data files."""

LOG_DIR = PROJECT_ROOT / "logs"
"""Default directory for application log files."""

OUTPUT_DIR = PROJECT_ROOT / "output"
"""Default directory for generated plot and analysis outputs."""

DOCS_DIR = PROJECT_ROOT / "docs"
"""Default directory for static website files."""

BUILD_DIR = PROJECT_ROOT / "build"
"""Default directory for the built GitHub Pages website."""

CONFIG_DIR = PROJECT_ROOT / "src" / "config"
"""Directory with project configuration files."""

# -------------------------------------------------------- data subtree

GEOTIFF_DIR = DATA_DIR / "geotiff"
"""Directory for downloaded NSIDC GeoTIFF files."""

NATURAL_EARTH_DIR = DATA_DIR / "naturalearth"
"""Directory for Natural Earth background vector data."""

OCEAN_SHAPEFILE = NATURAL_EARTH_DIR / "ocean.shp"
"""Natural Earth ocean polygon shapefile."""

# ------------------------------------------------------ output subtree

ANALYSIS_DIR = OUTPUT_DIR / "analysis"
"""Directory for analysis result files."""

ICE_COVERAGE_SUMMARY_CSV = ANALYSIS_DIR / "ice_coverage_summary.csv"
"""Daily regional ice coverage summary of the process stage."""

ICE_COVERAGE_TIMESERIES_CSV = (
    ANALYSIS_DIR / "ice_coverage_timeseries.csv"
)
"""Derived continuous daily time series."""

ICE_COVERAGE_YEARLY_CSV = ANALYSIS_DIR / "ice_coverage_yearly.csv"
"""Derived yearly means per region."""

ICE_COVERAGE_EVENTS_CSV = ANALYSIS_DIR / "ice_coverage_events.csv"
"""Derived break-up/freeze-up threshold events."""

LATEST_JSON = ANALYSIS_DIR / "latest.json"
"""Marker with the latest processed date."""

PLOTS_DIR = OUTPUT_DIR / "plots"
"""Directory for generated figures."""

GEOTIFF_OVERVIEW_PLOT = PLOTS_DIR / "sea_ice_geotiff_overview.png"
"""Default output file of the GeoTIFF overview plot."""

REFERENCE_DIR = OUTPUT_DIR / "reference"
"""Directory for generated region reference data."""

REFERENCE_FILTERS_DIR = REFERENCE_DIR / "filters"
"""Directory for the per-region reference filter masks."""

REFERENCE_SUMMARY_JSON = REFERENCE_DIR / "reference_summary.json"
"""Region reference summary produced by the reference builder."""

# --------------------------------------------------- build/log/config

LOG_FILE = LOG_DIR / "hudson_bay_sea_ice.log"
"""Default application log file."""

REFERENCE_TIF = CONFIG_DIR / "reference.tif"
"""Generated reference water mask raster."""

REGIONS_FILE = CONFIG_DIR / "regions.json"
"""Analysis region definitions."""


def resolve_project_path(
    path: str | Path, base_dir: Path = PROJECT_ROOT
) -> Path:
    """Return an absolute path, resolving relative inputs below
    ``base_dir``.
    """

    path = Path(path)
    if path.is_absolute():
        return path

    return base_dir / path
