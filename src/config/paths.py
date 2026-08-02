"""Project-level filesystem paths used by command line entry points."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
"""Absolute path to the project root directory, one level above the ``src`` package."""

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

def resolve_project_path(path: str | Path, base_dir: Path = PROJECT_ROOT) -> Path:
    """Return an absolute path, resolving relative inputs below ``base_dir``."""

    path = Path(path)
    if path.is_absolute():
        return path

    return base_dir / path
