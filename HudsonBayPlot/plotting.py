import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.patch import geos_to_path

from ice_analysis import create_geographic_boundary_polygon

def plot_ice_map(ax, lon, lat, ice_data, projection, region_bounds, title=""):
    lon_min, lon_max, lat_min, lat_max = region_bounds

    # Setze Kartenrahmen
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
    ax.set_boundary(
        geos_to_path(projection.project_geometry(
            create_geographic_boundary_polygon(lon_min, lon_max, lat_min, lat_max),
            ccrs.PlateCarree()))[0],
        transform=projection
    )
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)

    mesh = ax.pcolormesh(
        lon, lat, ice_data,
        transform=ccrs.PlateCarree(),
        cmap='Blues_r',
        shading='auto'
    )
    plt.colorbar(mesh, ax=ax, orientation='vertical', label='Sea Ice Concentration (0–1)')
    ax.set_title(title)