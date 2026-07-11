import matplotlib.pyplot as plt
import numpy as np
import rasterio
import cartopy.crs as ccrs

# ---------------------------------------------------------------------
# Datei
# ---------------------------------------------------------------------

filename = "data/geotiff/2026/07_Jul/N_20260707_concentration_v4.0.tif"

# ---------------------------------------------------------------------
# TIFF lesen
# ---------------------------------------------------------------------

with rasterio.open(filename) as src:
    print(src.crs)
    print(src.crs.to_wkt())
    print(src.transform)
    print(src.tags())
    print(src.tags(ns="IMAGE_STRUCTURE"))
    print(src.tags(ns="TIFF"))
    print(src.profile)
    ice = src.read(1).astype(float)

    transform = src.transform

# ---------------------------------------------------------------------
# NSIDC-Werte maskieren
# ---------------------------------------------------------------------

ice[ice > 1000] = np.nan
ice /= 10.0

# ---------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------

globe = ccrs.Globe(
    semimajor_axis=6378273,
    semiminor_axis=6356889.449
)

projection = ccrs.Stereographic(
    central_latitude=90,
    central_longitude=-45,
    true_scale_latitude=70,
    globe=globe
)

#projection = ccrs.NorthPolarStereo(
#    central_longitude=-45
#)

fig = plt.figure(figsize=(10,10))

ax = plt.axes(projection=projection)

ax.set_extent([-180,180,30,90], crs=ccrs.PlateCarree())

ax.coastlines(linewidth=0.5)

ax.gridlines()

extent = (
    transform.c,
    transform.c + transform.a * ice.shape[1],
    transform.f + transform.e * ice.shape[0],
    transform.f
)

img = ax.imshow(
    ice,
    origin="upper",
    extent=extent,
    transform=projection,
    cmap="Blues",
    vmin=0,
    vmax=100,
)

plt.colorbar(
    img,
    ax=ax,
    shrink=0.7,
    label="Sea ice concentration [%]"
)

plt.title("NSIDC Sea Ice Concentration")

plt.show()