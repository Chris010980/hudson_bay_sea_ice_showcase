"""Utilities for creating a regional sea-ice map from a GeoTIFF file."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import tifffile
from PIL import Image

from src.config.paths import DATA_DIR, PROJECT_ROOT, resolve_project_path

os.environ.setdefault("PROJ_LIB", pyproj.datadir.get_data_dir())
os.environ.setdefault("GDAL_DATA", pyproj.datadir.get_data_dir())

DEFAULT_REGION_BOUNDS = (260.0, 300.0, 50.0, 75.0)
DEFAULT_OUTPUT_PLOT_PATH = PROJECT_ROOT / "output" / "plots" / "sea_ice_geotiff_preview.png"


def find_concentration_geotiff(data_dir: str | Path | None = None) -> Path:
    """Return a representative concentration GeoTIFF from the local data tree."""

    base_dir = Path(data_dir) if data_dir is not None else DATA_DIR / "geotiff"
    if not base_dir.is_absolute():
        base_dir = PROJECT_ROOT / base_dir

    candidates = [
        path
        for path in base_dir.rglob("*.tif")
        if "concentration" in path.name.lower()
    ]
    if not candidates:
        raise FileNotFoundError(f"No concentration GeoTIFF found in {base_dir}.")

    return max(candidates, key=lambda path: (path.stat().st_mtime, path.as_posix()))


def _load_tiff_data(input_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read a GeoTIFF and build lon/lat coordinate arrays for plotting."""

    with tifffile.TiffFile(input_path) as tif:
        page = tif.pages[0]
        data = page.asarray()
        if data.ndim == 3:
            data = data[0]
        data = np.asarray(data, dtype=np.float32)

        tags = page.tags
        if "ModelPixelScaleTag" in tags and "ModelTiepointTag" in tags:
            pixel_scale = tags["ModelPixelScaleTag"].value
            tiepoint = tags["ModelTiepointTag"].value
            source_crs = "EPSG:3411"

            x = tiepoint[3] + (np.arange(data.shape[1]) + 0.5) * pixel_scale[0]
            y = tiepoint[4] - (np.arange(data.shape[0]) + 0.5) * pixel_scale[1]
            x_grid, y_grid = np.meshgrid(x, y)

            transformer = pyproj.Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
            lon_grid, lat_grid = transformer.transform(x_grid, y_grid)
            return data, lon_grid, lat_grid

    height, width = data.shape
    lon_min, lon_max, lat_min, lat_max = DEFAULT_REGION_BOUNDS
    x_values = np.linspace(lon_min, lon_max, width)
    y_values = np.linspace(lat_min, lat_max, height)
    lon_grid, lat_grid = np.meshgrid(x_values, y_values)
    return data, lon_grid, lat_grid


def _prepare_data_for_plot(
    input_path: str | Path,
    bounds: tuple[float, float, float, float] = DEFAULT_REGION_BOUNDS,
    width: int = 1200,
    height: int = 1200,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read and prepare a GeoTIFF for plotting."""

    resolved_path = resolve_project_path(input_path)
    data, lon_grid, lat_grid = _load_tiff_data(resolved_path)

    if data.shape[0] != height or data.shape[1] != width:
        data = np.array(Image.fromarray(data).resize((width, height), resample=Image.BILINEAR))
        lon_grid = np.array(Image.fromarray(lon_grid.astype(np.float32)).resize((width, height), resample=Image.BILINEAR))
        lat_grid = np.array(Image.fromarray(lat_grid.astype(np.float32)).resize((width, height), resample=Image.BILINEAR))

    if np.nanmax(data) > 1.5:
        data = data / 100.0

    data = np.ma.masked_invalid(data)
    data = np.ma.masked_where(data < 0, data)

    mask = (
        (lon_grid >= bounds[0])
        & (lon_grid <= bounds[1])
        & (lat_grid >= bounds[2])
        & (lat_grid <= bounds[3])
    )
    if mask.any():
        data = np.ma.masked_where(~mask, data)

    return data, lon_grid, lat_grid


def plot_geotiff_region(
    input_path: str | Path | None = None,
    output_path: str | Path | None = None,
    bounds: tuple[float, float, float, float] = DEFAULT_REGION_BOUNDS,
    title: str | None = None,
    show: bool = False,
) -> Path:
    """Create a regional sea-ice preview plot from a GeoTIFF and save it to disk."""

    if input_path is None:
        input_path = find_concentration_geotiff()

    resolved_input_path = resolve_project_path(input_path)
    if output_path is None:
        output_path = DEFAULT_OUTPUT_PLOT_PATH
    resolved_output_path = resolve_project_path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

    data, lon_grid, lat_grid = _prepare_data_for_plot(resolved_input_path, bounds=bounds)

    fig, ax = plt.subplots(figsize=(10, 8), dpi=180)

    mesh = ax.imshow(
        data,
        extent=[bounds[0], bounds[1], bounds[2], bounds[3]],
        cmap="Blues_r",
        vmin=0.0,
        vmax=1.0,
        origin="lower",
    )

    ax.set_xlim(bounds[0], bounds[1])
    ax.set_ylim(bounds[2], bounds[3])
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.3)

    cbar = plt.colorbar(mesh, ax=ax, orientation="vertical", pad=0.04)
    cbar.set_label("Sea ice concentration (0–1)")

    stem = resolved_input_path.stem if resolved_input_path.exists() else Path(str(input_path)).stem
    plot_title = title or f"Sea ice concentration preview – {stem}"
    ax.set_title(plot_title)

    plt.tight_layout()
    fig.savefig(resolved_output_path, dpi=200, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)
    return resolved_output_path
