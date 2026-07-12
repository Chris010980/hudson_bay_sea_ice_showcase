import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import rasterio

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from matplotlib.path import Path
from matplotlib.patches import PathPatch

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

    ice = src.read(1).astype(np.float32)

    transform = src.transform


# ---------------------------------------------------------------------
# NSIDC Werte
# ---------------------------------------------------------------------

land_mask = ice == 2540
coast_mask = ice == 2530

ice_mask = ice <= 1000

ice = ice.astype(np.float32)

ice[~ice_mask] = np.nan
ice /= 1000


# ---------------------------------------------------------------------
# Raster Extent EPSG:3411
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
fig.patch.set_facecolor("white")

ax = plt.axes(projection=projection)
ax.set_facecolor("white")

ax.set_extent(
    [lon_min, lon_max, lat_min, lat_max],
    crs=ccrs.PlateCarree()
)

ax.spines["geo"].set_visible(False)


# ---------------------------------------------------------------------
# Polygon des Kartenausschnitts
# ---------------------------------------------------------------------

n = 400

lon_bottom = np.linspace(lon_min, lon_max, n)
lon_top = np.linspace(lon_max, lon_min, n)

lat_bottom = np.full(n, lat_min)
lat_top = np.full(n, lat_max)

lon_right = np.full(n, lon_max)
lon_left = np.full(n, lon_min)

lat_right = np.linspace(lat_min, lat_max, n)
lat_left = np.linspace(lat_max, lat_min, n)

polygon_lon = np.concatenate([
    lon_bottom,
    lon_right,
    lon_top,
    lon_left,
    [lon_min]
])

polygon_lat = np.concatenate([
    lat_bottom,
    lat_right,
    lat_top,
    lat_left,
    [lat_min]
])

# ---------------------------------------------------------------------
# Boundary der GeoAxes auf den Kartenausschnitt setzen
# ---------------------------------------------------------------------

proj = projection.transform_points(
    ccrs.PlateCarree(),
    polygon_lon,
    polygon_lat
)

boundary = mpath.Path(proj[:, :2])

ax.set_boundary(
    boundary,
    transform=ax.transData
)

ax.plot(
    polygon_lon,
    polygon_lat,
    transform=ccrs.PlateCarree(),
    color="0.25",
    linewidth=1.0,
    zorder=20
)

# ---------------------------------------------------------------------
# Ozean innerhalb des Kartenausschnitts
# ---------------------------------------------------------------------

ax.fill(
    polygon_lon,
    polygon_lat,
    transform=ccrs.PlateCarree(),
    facecolor=ocean_color,
    edgecolor="none",
    zorder=0
)


# ---------------------------------------------------------------------
# Land
# ---------------------------------------------------------------------

land_artist = ax.add_feature(
    cfeature.LAND,
    facecolor=land_color,
    edgecolor="none",
    zorder=2
)

coast_artist = ax.coastlines(
    linewidth=0.7,
    color="0.35",
    zorder=4
)


# ---------------------------------------------------------------------
# Gitternetz
# ---------------------------------------------------------------------

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
        zorder=50
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
        zorder=50
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


# ---------------------------------------------------------------------
# Farbskala
# ---------------------------------------------------------------------

cbar = plt.colorbar(
    img,
    ax=ax,
    shrink=0.75,
    pad=0.05
)

cbar.ax.tick_params(labelsize=10)

cbar.set_label(
    "Sea ice concentration",
    fontsize=11
)


cbar.set_ticks(
    np.linspace(0, 1, 6)
)


# ---------------------------------------------------------------------
# Titel
# ---------------------------------------------------------------------

fig.suptitle(
    "Hudson Bay Sea Ice Concentration\nNSIDC Polar Stereographic",
    fontsize=16,
    y=0.98
)


plt.subplots_adjust(
    left=0.06,
    right=0.88,
    bottom=0.06,
    top=0.92
)


plt.savefig(
    "output/hudson_bay_sea_ice.png",
    dpi=300,
    bbox_inches="tight",
    facecolor="white"
)

plt.show()