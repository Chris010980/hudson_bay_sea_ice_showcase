"""Utilities for creating a regional sea-ice map from a GeoTIFF file."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import tifffile
from cartopy.mpl.patch import geos_to_path
from PIL import Image
from shapely.geometry import Polygon

from src.config.paths import DATA_DIR, PROJECT_ROOT, resolve_project_path

os.environ.setdefault("PROJ_LIB", pyproj.datadir.get_data_dir())
os.environ.setdefault("GDAL_DATA", pyproj.datadir.get_data_dir())

DEFAULT_REGION_BOUNDS = (260.0, 300.0, 50.0, 75.0)
DEFAULT_OUTPUT_PLOT_PATH = PROJECT_ROOT / "output" / "plots" / "sea_ice_geotiff_preview.png"
logger = logging.getLogger(__name__)


def _normalize_longitudes(lon_grid: np.ndarray) -> np.ndarray:
    """Normalize longitudes from the [-180, 180] convention to [0, 360)."""

    lon = np.asarray(lon_grid, dtype=np.float32)
    return np.where(lon < 0.0, lon + 360.0, lon)


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

    logger.info("Loading GeoTIFF data from %s", input_path)
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
            logger.debug(
                "Using GeoTIFF georeferencing tags: pixel_scale=%s tiepoint=%s",
                pixel_scale,
                tiepoint,
            )

            x = tiepoint[3] + (np.arange(data.shape[1]) + 0.5) * pixel_scale[0]
            y = tiepoint[4] - (np.arange(data.shape[0]) + 0.5) * pixel_scale[1]
            x_grid, y_grid = np.meshgrid(x, y)

            transformer = pyproj.Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
            lon_grid, lat_grid = transformer.transform(x_grid, y_grid)
            lon_grid = _normalize_longitudes(lon_grid)
            logger.debug("Derived %dx%d raster coordinates", data.shape[0], data.shape[1])
            return data, lon_grid, lat_grid

    logger.warning("GeoTIFF georeferencing tags not found, falling back to synthetic bounds")
    height, width = data.shape
    lon_min, lon_max, lat_min, lat_max = DEFAULT_REGION_BOUNDS
    x_values = np.linspace(lon_min, lon_max, width)
    y_values = np.linspace(lat_min, lat_max, height)
    lon_grid, lat_grid = np.meshgrid(x_values, y_values)
    return data, lon_grid, lat_grid


def _prepare_plot_data(data: np.ndarray) -> np.ndarray:
    """Normalize raster values so invalid or negative entries render as 0% sea ice."""

    prepared = np.asarray(data, dtype=np.float32)
    if prepared.ndim == 3:
        prepared = prepared[0]
    prepared = np.where(np.isnan(prepared) | (prepared < 0.0), 0.0, prepared)

    if prepared.size:
        max_value = float(np.nanmax(prepared))
        if np.isfinite(max_value) and max_value > 1.0:
            logger.debug("Normalizing raster values to unit range with max %.3f", max_value)
            prepared = prepared / max_value

    return np.clip(prepared, 0.0, 1.0)


def _load_rendered_tiff(input_path: Path) -> np.ndarray:
    """Load a GeoTIFF as an image, preserving any palette color table."""

    with Image.open(input_path) as image:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        rendered = np.asarray(image)

    logger.debug("Rendered TIFF image with shape %s", rendered.shape)
    return rendered


def _build_boundary_path(
    projection: ccrs.Projection,
    bounds: tuple[float, float, float, float],
) -> object:
    """Create a simple regional boundary path for the overview plot."""

    lon_min, lon_max, lat_min, lat_max = bounds
    boundary_points = [
        (lon_min, lat_min),
        (lon_max, lat_min),
        (lon_max, lat_max),
        (lon_min, lat_max),
        (lon_min, lat_min),
    ]

    polygon = Polygon(boundary_points)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    projected = projection.project_geometry(polygon, ccrs.PlateCarree())
    return geos_to_path(projected)[0]


def _prepare_data_for_plot(
    input_path: str | Path,
    bounds: tuple[float, float, float, float] = DEFAULT_REGION_BOUNDS,
    width: int = 1200,
    height: int = 1200,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read and prepare a GeoTIFF for plotting."""

    resolved_path = resolve_project_path(input_path)
    logger.info("Preparing GeoTIFF image for plotting with bounds %s", bounds)
    _, lon_grid, lat_grid = _load_tiff_data(resolved_path)
    rendered = _load_rendered_tiff(resolved_path)

    if rendered.shape[0] != height or rendered.shape[1] != width:
        logger.debug("Resampling raster to %dx%d", width, height)
        rendered = np.array(Image.fromarray(rendered).resize((width, height), resample=Image.BILINEAR))
        lon_grid = np.array(Image.fromarray(lon_grid.astype(np.float32)).resize((width, height), resample=Image.BILINEAR))
        lat_grid = np.array(Image.fromarray(lat_grid.astype(np.float32)).resize((width, height), resample=Image.BILINEAR))

    mask = (
        (lon_grid >= bounds[0])
        & (lon_grid <= bounds[1])
        & (lat_grid >= bounds[2])
        & (lat_grid <= bounds[3])
    )
    if mask.any():
        logger.debug("Applied spatial mask to %d cells", int(mask.sum()))

    return rendered, lon_grid, lat_grid


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

    logger.info("Creating sea-ice preview plot for %s", resolved_input_path)
    logger.debug("Rendering bounds=%s title=%s", bounds, title)
    image_data, lon_grid, lat_grid = _prepare_data_for_plot(resolved_input_path, bounds=bounds)

    fig = plt.figure(figsize=(10, 8), dpi=180)
    ax = plt.axes(projection=ccrs.NorthPolarStereo(central_longitude=-80))
    ax.set_extent(list(bounds), crs=ccrs.PlateCarree())

    boundary_path = _build_boundary_path(ax.projection, bounds)
    ax.set_boundary(boundary_path, transform=ax.projection)

    image_extent = [
        float(np.nanmin(lon_grid)),
        float(np.nanmax(lon_grid)),
        float(np.nanmin(lat_grid)),
        float(np.nanmax(lat_grid)),
    ]
    ax.imshow(
        image_data,
        extent=image_extent,
        origin="upper",
        transform=ccrs.PlateCarree(),
        zorder=2,
    )

    ax.add_feature(cfeature.OCEAN, facecolor="lightblue", zorder=0)
    ax.add_feature(cfeature.LAND, facecolor="lightgray", edgecolor="black", linewidth=0.25, zorder=1)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5, zorder=2)
    ax.gridlines(draw_labels=False)

    stem = resolved_input_path.stem if resolved_input_path.exists() else Path(str(input_path)).stem
    plot_title = title or f"Sea ice concentration preview – {stem}"
    ax.set_title(plot_title)

    plt.tight_layout()
    fig.savefig(resolved_output_path, dpi=200, bbox_inches="tight")
    logger.info("Saved plot to %s", resolved_output_path)

    if show:
        plt.show()

    plt.close(fig)
    return resolved_output_path
