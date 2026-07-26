"""Utilities for creating a regional sea-ice map from a GeoTIFF file."""

from __future__ import annotations

from src.config.paths import DATA_DIR, PROJECT_ROOT, resolve_project_path

from pathlib import Path
from datetime import datetime

import json
import logging
import os
import re
import pyproj
import rasterio

import cartopy.crs as ccrs
import cartopy.feature as cfeature

import numpy as np

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.path as mpath
import matplotlib.pyplot as plt
matplotlib.use("Agg")


os.environ.setdefault("PROJ_LIB", pyproj.datadir.get_data_dir())
os.environ.setdefault("GDAL_DATA", pyproj.datadir.get_data_dir())

DEFAULT_REGION_BOUNDS = (260.0, 300.0, 50.0, 75.0)
DEFAULT_OUTPUT_PLOT_PATH = PROJECT_ROOT / "output" / "plots" / "sea_ice_geotiff_overview.png"
logger = logging.getLogger(__name__)

import matplotlib as mpl

mpl.rcParams.update(
    {
        "figure.dpi": 150,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "savefig.bbox": "tight",
    }
)
   
class SeaIcePlotter:

    # ---------------------------------------------------------
    # Construction
    # ---------------------------------------------------------

    def __init__(
        self,
        input_path: str | Path | None = None,
        bounds: tuple[float, float, float, float] = DEFAULT_REGION_BOUNDS,
    ):
        if input_path is None:
            input_path = self.find_concentration_geotiff()

        self.input_path = resolve_project_path(input_path)
        self.bounds = bounds

        # matplotlib
        self.fig = None
        self.ax = None

        # raster
        self.ice = None
        self.transform = None
        self.extent = None

        # projection
        self.source_crs = None
        self.projection = None
        self.globe = None

        # metadata
        self.date = None

        self._configure_style()

    def _configure_style(self):

        self.figure_size = (7.2, 6.2)

        self.left_margin = 0.07
        self.right_margin = 0.89

        self.bottom_margin = 0.10
        self.top_margin = 0.87

        self.title_y = 0.965
        self.subtitle_y = 0.93

        self.colorbar_pad = 0.05
        self.colorbar_shrink = 0.75

        self.title_fontsize = 16
        self.subtitle_fontsize = 11

        self.axis_fontsize = 10

        self.map_padding_south = 1.5

        self.colorbar_fontsize = 11
        self.colorbar_ticksize = 10

        self.grid_linewidth = 0.6

        self.border_color = "0.25"
        self.coast_color = "0.35"

        self.ocean_color = "#08306b"
        self.land_color = "#d9d9d9"

        self.region_color = "crimson"

        self.region_linewidth = 1.6

        self.region_fontsize = 8

        self.cmap = mcolors.LinearSegmentedColormap.from_list(
            "SeaIce",
            [
                self.ocean_color,
                "#2171b5",
                "#6baed6",
                "#c6dbef",
                "#ffffff",
            ],
        )

    @staticmethod
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

    def load_regions(
        self,
        region_file: str | Path | None = None,
    ):
        """Load region definitions from regions.json."""

        if region_file is None:
            region_file = PROJECT_ROOT / "src/config/regions.json"

        with open(region_file, encoding="utf-8") as f:
            data = json.load(f)

        self.regions = data["regions"]

    def load(self):

        self._load_raster()

        self._prepare_data()

        self._build_projection()

        self._extract_metadata()

        self.load_regions()

    def _create_figure(self):

        self.fig = plt.figure(figsize=self.figure_size)

        self.ax = plt.axes(projection=self.projection)
        self.ax.set_facecolor("white")

        lon_min, lon_max, lat_min, lat_max = self.bounds
        display_lat_min = lat_min - self.map_padding_south

        self.ax.set_extent(
            [lon_min, lon_max, display_lat_min, lat_max],
            crs=ccrs.PlateCarree(),
        )

        self.ax.spines["geo"].set_visible(False)

    def _load_raster(self):

        with rasterio.open(self.input_path) as src:

            self.ice = src.read(1).astype(np.float32)

            self.transform = src.transform

    def _prepare_data(self):

        mask = self.ice <= 1000

        self.ice[~mask] = np.nan

        self.ice /= 1000

        self.extent = (
            self.transform.c,
            self.transform.c + self.transform.a * self.ice.shape[1],
            self.transform.f + self.transform.e * self.ice.shape[0],
            self.transform.f,
        )

    def _build_projection(self):

        self.source_crs = ccrs.epsg(3411)

        self.globe = ccrs.Globe(
            semimajor_axis=6378273,
            semiminor_axis=6356889.449,
        )

        self.projection = ccrs.Stereographic(
            central_latitude=90,
            central_longitude=-80,
            true_scale_latitude=70,
            globe=self.globe,
        )

    def _draw_background(self):

        self._draw_boundary()

        self._draw_ocean()

        self._draw_land()

        self._draw_coastline()

    
    def _draw_boundary(self):
        
        lon_min, lon_max, lat_min, lat_max = self.bounds

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

        proj = self.projection.transform_points(
            ccrs.PlateCarree(),
            polygon_lon,
            polygon_lat,
        )

        boundary = mpath.Path(proj[:, :2])

        self.ax.set_boundary(
            boundary,
            transform=self.ax.transData,
        )

        self.ax.plot(
            polygon_lon,
            polygon_lat,
            transform=ccrs.PlateCarree(),
            color=self.border_color,
            linewidth=1.5,
            zorder=20
        )

    def _draw_ocean(self):

        self.ax.add_feature(
            cfeature.OCEAN,
            facecolor=self.ocean_color,
            edgecolor="none",
            zorder=1,
        )

    def _draw_land(self):

        self.ax.add_feature(
            cfeature.LAND,
            facecolor=self.land_color,
            edgecolor="none",
            zorder=2,
        )

    def _draw_coastline(self):
        self.ax.coastlines(color=self.coast_color, linewidth=0.7, zorder=4)

    def _draw_grid(self):

        self.gl = self.ax.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=False,
            color="0.6",
            alpha=0.35,
            linestyle="--",
            linewidth=0.6,
        )

        self.gl.xlocator = plt.FixedLocator(
            [-100, -90, -80, -70, -60]
        )

        self.gl.ylocator = plt.FixedLocator(
            [50, 55, 60, 65, 70, 75]
        )

    def _draw_axis_labels(self):
        
        lon_min, lon_max, lat_min, lat_max = self.bounds

        for lon in [-100, -90, -80, -70, -60]:

            self.ax.text(
                lon,
                lat_min - 0.6,
                f"{abs(lon)}°W",
                transform=ccrs.PlateCarree(),
                ha="center",
                va="top",
                fontsize=self.axis_fontsize,
                color="0.25",
                clip_on=False,
                zorder=50,
            )

        for lat in [50, 55, 60, 65, 70, 75]:

            self.ax.text(
                lon_min - 0.8,
                lat,
                f"{lat}°N",
                transform=ccrs.PlateCarree(),
                ha="right",
                va="center",
                fontsize=self.axis_fontsize,
                color="0.25",
                clip_on=False,
                zorder=50,
            )

    def _draw_sea_ice(self):

        self.image = self.ax.imshow(
            self.ice,
            origin="upper",
            extent=self.extent,
            transform=self.source_crs,
            cmap=self.cmap,
            vmin=0,
            vmax=1,
            interpolation="nearest",
            zorder=3,
        )

    def draw_regions(
        self,
        selected=None,
    ):

        """Draw one or more analysis regions."""

        for name, region in self.regions.items():

            if selected is not None and name not in selected:
                continue

            coords = np.asarray(region["polygon"], dtype=float)

            lon = coords[:, 0].copy()
            lat = coords[:, 1]

            # 0...360 -> -180...180
            lon = np.where(lon > 180.0, lon - 360.0, lon)

            # Polygon schließen
            lon = np.append(lon, lon[0])
            lat = np.append(lat, lat[0])

            self.ax.plot(
                lon,
                lat,
                transform=ccrs.PlateCarree(),
                color=self.region_color,
                linewidth=self.region_linewidth,
                zorder=30,
            )

            # Schwerpunkt für Text
            self.ax.text(
                lon.mean(),
                lat.mean(),
                name,
                transform=ccrs.PlateCarree(),
                fontsize=self.region_fontsize,
                ha="center",
                va="center",
                bbox=dict(
                    facecolor="white",
                    alpha=0.85,
                    edgecolor="0.8",
                    linewidth=0.5,
                    pad=1.5,
                ),
                zorder=31,
            )

    def _draw_colorbar(self):
        
        self.cbar = plt.colorbar(
            self.image,
            ax=self.ax,
            shrink=self.colorbar_shrink,
            pad=self.colorbar_pad,
        )

        self.cbar.outline.set_edgecolor("0.6")

        self.cbar.ax.tick_params(
            colors="0.3",
            labelsize=self.colorbar_ticksize,
        )

        self.cbar.set_label(
            "Sea ice concentration",
            fontsize=self.colorbar_fontsize,
            color="0.3",
        )

        self.cbar.set_ticks(np.linspace(0, 1, 6))

    def _extract_metadata(self):

        self.date = None

        match = re.search(r"(\d{8})", self.input_path.stem)

        if match:

            self.date = datetime.strptime(
                match.group(1),
                "%Y%m%d",
            )

    def _draw_title(
        self,
        title=None,
    ):

        title = title or "Hudson Bay Sea Ice Concentration"

        if self.date is not None:
            subtitle = self.date.strftime("%d %B %Y")
        else:
            subtitle = ""

        self.fig.text(
            0.5,
            0.975,
            title,
            ha="center",
            va="top",
            fontsize=self.title_fontsize,
            fontweight="bold",
        )

        if self.date is not None:
            self.fig.text(
                0.5,
                0.92,
                self.date.strftime("%d %B %Y"),
                ha="center",
                va="top",
                fontsize=self.subtitle_fontsize,
                color="0.35",
            )

    def save(
        self,
        output_path: str | Path | None = None,
        suffix: str | None = None,
    ):
        """
        Save the current figure.

        Parameters
        ----------
        output_path
            Destination file. If None, DEFAULT_OUTPUT_PLOT_PATH is used.

        suffix
            Optional suffix appended to the filename before the extension.

            Example:
                sea_ice_geotiff_preview.png
                -> sea_ice_geotiff_preview_regions.png
        """

        if output_path is None:
            output_path = DEFAULT_OUTPUT_PLOT_PATH

        output_path = resolve_project_path(output_path)

        if suffix:

            output_path = output_path.with_name(
                f"{output_path.stem}_{suffix}{output_path.suffix}"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.fig.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
        )

        logger.info("Saved plot to %s", output_path)

        return output_path

    def plot(
        self,
        title=None,
        regions=None,
    ):

        self._create_figure()

        self._draw_background()
        self._draw_grid()
        self._draw_axis_labels()

        self._draw_sea_ice()

        if regions is not None:
            self.draw_regions(selected=regions)

        self._draw_colorbar()

        self._draw_title(title)

        self._layout()

    def _layout(self):

        plt.subplots_adjust(
            left=self.left_margin,
            right=self.right_margin,
            bottom=self.bottom_margin,
            top=self.top_margin,
        )

    def plot_overview(self):

        self.plot()

    def plot_regions(self):

        self.plot(regions=list(self.regions))

    def plot_single_region(self, region):

        self.plot(
            title=region,
            regions=[region],
        )