import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import rasterio

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from rasterio.windows import from_bounds
from pyproj import CRS, Transformer
import matplotlib.path as mpath

# ---------------------------------------------------------------------
# Datei
# ---------------------------------------------------------------------

filename = (
    "data/geotiff/2026/07_Jul/"
    "N_20260707_concentration_v4.0.tif"
)


# ---------------------------------------------------------------------
# Bounding Box Hudson Bay
# ---------------------------------------------------------------------

lon_min = -100
lon_max = -60

lat_min = 50
lat_max = 75


# ---------------------------------------------------------------------
# Raster lesen
# ---------------------------------------------------------------------

with rasterio.open(filename) as src:

    raster_crs = CRS.from_epsg(3411)

    transformer = Transformer.from_crs(
        CRS.from_epsg(4326),
        raster_crs,
        always_xy=True
    )

    x1, y1 = transformer.transform(
        lon_min,
        lat_min
    )

    x2, y2 = transformer.transform(
        lon_max,
        lat_max
    )

    window = from_bounds(
        x1,
        y1,
        x2,
        y2,
        transform=src.transform
    )

    ice = src.read(
        1,
        window=window
    ).astype(np.float32)

    transform = src.window_transform(window)


# ---------------------------------------------------------------------
# NSIDC Werte
# ---------------------------------------------------------------------

# ungültige Werte
ice[ice > 1000] = np.nan

# 0 ... 1000 -> 0 ... 1
ice /= 1000.0


# ---------------------------------------------------------------------
# Raster Extent in EPSG:3411
# ---------------------------------------------------------------------

extent = (
    transform.c,
    transform.c + transform.a * ice.shape[1],
    transform.f + transform.e * ice.shape[0],
    transform.f
)

source_crs = ccrs.epsg(3411)


# ---------------------------------------------------------------------
# Projektion
# ---------------------------------------------------------------------

globe = ccrs.Globe(
    semimajor_axis=6378273,
    semiminor_axis=6356889.449
)


projection = ccrs.Stereographic(
    central_latitude=90,
    central_longitude=-80,
    true_scale_latitude=70,
    globe=globe
)


# ---------------------------------------------------------------------
# Farben
# ---------------------------------------------------------------------

ocean_color = "#08306b"
land_color = "#d9d9d9"


ice_cmap = mcolors.LinearSegmentedColormap.from_list(
    "SeaIce",
    [
        ocean_color,
        "#2171b5",
        "#6baed6",
        "#c6dbef",
        "#ffffff"
    ]
)


# ---------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------

fig = plt.figure(figsize=(8, 8))

ax = plt.axes(
    projection=projection
)

ax.set_extent(
    [
        lon_min,
        lon_max,
        lat_min,
        lat_max
    ],
    crs=ccrs.PlateCarree()
)



ax.spines["geo"].set_visible(False)


# Hintergrund

ax.set_facecolor(ocean_color)


# Land

ax.add_feature(
    cfeature.LAND,
    facecolor=land_color,
    edgecolor="0.45",
    linewidth=0.4,
    zorder=1
)


ax.coastlines(
    linewidth=0.5,
    color="0.5",
    zorder=4
)


# Gitternetz

gl = ax.gridlines(
    crs=ccrs.PlateCarree(),
    draw_labels=False,
    linewidth=0.6,
    color="gray",
    alpha=0.5,
    linestyle=":"
)


gl.xlocator = plt.FixedLocator(
    [-100, -90, -80, -70, -60]
)

gl.ylocator = plt.FixedLocator(
    [50, 55, 60, 65, 70, 75]
)

# ---------------------------------------------------------------------
# Meereis
# ---------------------------------------------------------------------

img = ax.imshow(
    ice,
    origin="upper",
    extent=extent,
    transform=source_crs,
    cmap=ice_cmap,
    vmin=0,
    vmax=1,
    interpolation="nearest",
    zorder=3
)


# Farbskala

cbar = plt.colorbar(
    img,
    ax=ax,
    shrink=0.75,
    pad=0.04
)

cbar.set_label(
    "Sea ice concentration"
)

cbar.set_ticks(
    np.linspace(0, 1, 6)
)


plt.title(
    "Hudson Bay Sea Ice Concentration\nNSIDC Polar Stereographic"
)


plt.subplots_adjust(
    left=0.05,
    right=0.95,
    bottom=0.05,
    top=0.95
)

plt.show()