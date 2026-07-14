"""Utilities for creating a regional sea-ice map from a GeoTIFF file."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.path as mpath

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import rasterio

from src.config.paths import DATA_DIR, PROJECT_ROOT, resolve_project_path

os.environ.setdefault("PROJ_LIB", pyproj.datadir.get_data_dir())
os.environ.setdefault("GDAL_DATA", pyproj.datadir.get_data_dir())

DEFAULT_REGION_BOUNDS = (260.0, 300.0, 50.0, 75.0)
DEFAULT_OUTPUT_PLOT_PATH = PROJECT_ROOT / "output" / "plots" / "sea_ice_geotiff_preview.png"
logger = logging.getLogger(__name__)


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

def plot_geotiff_region(
    input_path: str | Path | None = None,
    output_path: str | Path | None = None,
    bounds: tuple[float, float, float, float] = DEFAULT_REGION_BOUNDS,
    title: str | None = None,
    show: bool = False,
    draw_regions=False,
    region_file=None,
    selected_regions=None,
) -> Path:
    """
    Generate the Hudson Bay sea-ice overview plot.
    """

    if input_path is None:
        input_path = find_concentration_geotiff()

    input_path = resolve_project_path(input_path)

    if output_path is None:
        output_path = DEFAULT_OUTPUT_PLOT_PATH

    output_path = resolve_project_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lon_min, lon_max, lat_min, lat_max = bounds

    logger.info("Reading %s", input_path)

    with rasterio.open(input_path) as src:

        ice = src.read(1).astype(np.float32)
        transform = src.transform

    # -------------------------------------------------------------
    # NSIDC values
    # -------------------------------------------------------------

    ice_mask = ice <= 1000

    ice = ice.astype(np.float32)
    ice[~ice_mask] = np.nan
    ice /= 1000.0

    extent = (
        transform.c,
        transform.c + transform.a * ice.shape[1],
        transform.f + transform.e * ice.shape[0],
        transform.f,
    )

    source_crs = ccrs.epsg(3411)

    globe = ccrs.Globe(
        semimajor_axis=6378273,
        semiminor_axis=6356889.449,
    )

    projection = ccrs.Stereographic(
        central_latitude=90,
        central_longitude=-80,
        true_scale_latitude=70,
        globe=globe,
    )

    ocean_color = "#08306b"
    land_color = "#d9d9d9"

    ice_cmap = mcolors.LinearSegmentedColormap.from_list(
        "SeaIce",
        [
            ocean_color,
            "#2171b5",
            "#6baed6",
            "#c6dbef",
            "#ffffff",
        ],
    )

    fig = plt.figure(figsize=(8, 8))
    fig.patch.set_facecolor("white")

    ax = plt.axes(projection=projection)
    ax.set_facecolor("white")

    ax.set_extent(
        [lon_min, lon_max, lat_min, lat_max],
        crs=ccrs.PlateCarree(),
    )

    ax.spines["geo"].set_visible(False)

    # -------------------------------------------------------------
    # Boundary polygon
    # -------------------------------------------------------------

    n = 400

    lon_bottom = np.linspace(lon_min, lon_max, n)
    lon_top = np.linspace(lon_max, lon_min, n)

    lat_bottom = np.full(n, lat_min)
    lat_top = np.full(n, lat_max)

    lon_right = np.full(n, lon_max)
    lon_left = np.full(n, lon_min)

    lat_right = np.linspace(lat_min, lat_max, n)
    lat_left = np.linspace(lat_max, lat_min, n)

    polygon_lon = np.concatenate(
        [
            lon_bottom,
            lon_right,
            lon_top,
            lon_left,
            [lon_min],
        ]
    )

    polygon_lat = np.concatenate(
        [
            lat_bottom,
            lat_right,
            lat_top,
            lat_left,
            [lat_min],
        ]
    )

    proj = projection.transform_points(
        ccrs.PlateCarree(),
        polygon_lon,
        polygon_lat,
    )

    boundary = mpath.Path(proj[:, :2])

    ax.set_boundary(
        boundary,
        transform=ax.transData,
    )

    # border

    ax.plot(
        polygon_lon,
        polygon_lat,
        transform=ccrs.PlateCarree(),
        color="0.25",
        linewidth=1.0,
        zorder=20,
    )

    # ocean

    ax.fill(
        polygon_lon,
        polygon_lat,
        transform=ccrs.PlateCarree(),
        facecolor=ocean_color,
        edgecolor="none",
        zorder=0,
    )

    # land / coast

    ax.add_feature(
        cfeature.LAND,
        facecolor=land_color,
        edgecolor="none",
        zorder=2,
    )

    ax.coastlines(
        linewidth=0.7,
        color="0.35",
        zorder=4,
    )

    # grid

    gl = ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=False,
        linewidth=0.6,
        color="gray",
        alpha=0.5,
        linestyle=":",
    )

    gl.xlocator = plt.FixedLocator(
        [-100, -90, -80, -70, -60]
    )

    gl.ylocator = plt.FixedLocator(
        [50, 55, 60, 65, 70, 75]
    )

    # labels

    for lon in [-100, -90, -80, -70, -60]:

        ax.text(
            lon,
            lat_min - 0.6,
            f"{abs(lon)}°W",
            transform=ccrs.PlateCarree(),
            ha="center",
            va="top",
            fontsize=10,
            clip_on=False,
            zorder=50,
        )

    for lat in [50, 55, 60, 65, 70, 75]:

        ax.text(
            lon_min - 0.8,
            lat,
            f"{lat}°N",
            transform=ccrs.PlateCarree(),
            ha="right",
            va="center",
            fontsize=10,
            clip_on=False,
            zorder=50,
        )

    img = ax.imshow(
        ice,
        origin="upper",
        extent=extent,
        transform=source_crs,
        cmap=ice_cmap,
        vmin=0,
        vmax=1,
        interpolation="nearest",
        zorder=3,
    )

    cbar = plt.colorbar(
        img,
        ax=ax,
        shrink=0.75,
        pad=0.05,
    )

    cbar.ax.tick_params(labelsize=10)

    cbar.set_label(
        "Sea ice concentration",
        fontsize=11,
    )

    cbar.set_ticks(np.linspace(0, 1, 6))

    fig.suptitle(
        title or "Hudson Bay Sea Ice Concentration",
        fontsize=16,
        y=0.98,
    )

    plt.subplots_adjust(
        left=0.06,
        right=0.88,
        bottom=0.06,
        top=0.92,
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )

    logger.info("Saved plot to %s", output_path)

    if show:
        plt.show()

    plt.close(fig)

    return output_path

def load_regions(
    region_file: str | Path | None = None,
) -> dict:

    if region_file is None:
        region_file = PROJECT_ROOT / "src/config/regions.json"

    with open(region_file, encoding="utf-8") as f:
        return json.load(f)
    
def draw_regions(
    ax,
    regions,
    selected=None,
):
    for region in regions:

        if selected is not None:
            if region["name"] not in selected:
                continue

        coords = np.asarray(region["coordinates"])

        lon = coords[:,0]
        lat = coords[:,1]

        ax.plot(
            lon,
            lat,
            transform=ccrs.PlateCarree(),
            linewidth=2,
            color="red",
            zorder=30,
        )
