from pyhdf.SD import SD, SDC
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import shapely.geometry as sgeom
from cartopy.mpl.patch import geos_to_path
from shapely.geometry import Point, Polygon
import geopandas as gpd
import json
import os
import matplotlib as mpl

mpl.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 200,

    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,

    "xtick.labelsize": 9,
    "ytick.labelsize": 9,

    "legend.fontsize": 9,
    "legend.frameon": False,

    "lines.linewidth": 1.3,
    "grid.alpha": 0.4,

    "savefig.bbox": "tight",
})

def compute_ice_coverage(polygon, ice_data, lon, lat, threshold=0.2, cell_size_km=6.25):
    """
    Berechnet Gesamtfläche, rel./abs. Eisbedeckung für ein Shapely-Polygon.

    Args:
        polygon: Shapely Polygon-Objekt (in lon/lat).
        ice_data: 2D-MaskedArray mit Eiskonzentration (0–1).
        lon: 2D-Array der Längengrade.
        lat: 2D-Array der Breitengrade.
        threshold: Schwelle für absolute Bedeckung (default: 0.2).
        cell_size_km: Zellengröße (Standard: 6.25 km).

    Returns:
        Dictionary mit Flächen & Prozentwerten.
    """
    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    cell_area = cell_size_km ** 2

    valid_mask = ~ice_data.mask
    flat_lon = lon[valid_mask]
    flat_lat = lat[valid_mask]
    flat_ice = ice_data[valid_mask]

    points = [Point(lon_, lat_) for lon_, lat_ in zip(flat_lon, flat_lat)]
    inside = np.array([polygon.contains(p) for p in points])

    ice_inside = flat_ice[inside]
    total_cells = len(ice_inside)

    if total_cells == 0:
        return {
            'total_area_km2': 0.0,
            'relative_cover_km2': 0.0,
            'absolute_cover_km2': 0.0,
            'relative_percent': 0.0,
            'absolute_percent': 0.0
        }

    total_area_km2 = total_cells * cell_area
    relative_cover_km2 = np.sum(ice_inside * cell_area)
    absolute_cover_km2 = np.sum(ice_inside >= threshold) * cell_area

    return {
        'total_area_km2': total_area_km2,
        'relative_cover_km2': relative_cover_km2,
        'absolute_cover_km2': absolute_cover_km2,
        'relative_percent': 100 * relative_cover_km2 / total_area_km2,
        'absolute_percent': 100 * absolute_cover_km2 / total_area_km2
    }

# Krümmung entlang der Breitengrade
def create_geographic_boundary_polygon(lon_min, lon_max, lat_min, lat_max, resolution=0.05):
    lons_top = np.arange(lon_min, lon_max + resolution, resolution)
    lats_right = np.arange(lat_min, lat_max + resolution, resolution)
    lons_bottom = np.arange(lon_max, lon_min - resolution, -resolution)
    lats_left = np.arange(lat_max, lat_min - resolution, -resolution)

    # Ränder: oben, rechts, unten, links
    top = [(lon, lat_max) for lon in lons_top]
    right = [(lon_max, lat) for lat in lats_right]
    bottom = [(lon, lat_min) for lon in lons_bottom]
    left = [(lon_min, lat) for lat in lats_left]

    boundary_coords = top + right + bottom + left
    return sgeom.Polygon(boundary_coords)

# Pfade
json_path = "polygons/HudsonBayArea.json"
geojson_dir = "polygons_geojson"

# Sicherstellen, dass GeoJSON-Verzeichnis existiert
os.makedirs(geojson_dir, exist_ok=True)

# Lade Punktdaten
with open(json_path, "r") as f:
    polygon_point_dict = json.load(f)

# Erzeuge Polygonobjekte und speichere sie als GeoJSON
polygon_dict = {}
for name, points in polygon_point_dict.items():
    polygon = Polygon(points)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    polygon_dict[name] = polygon

    gdf = gpd.GeoDataFrame(index=[0], geometry=[polygon])
    gdf.to_file(os.path.join(geojson_dir, f"{name.replace(' ', '_')}.geojson"), driver="GeoJSON")

polygon_points =  [
    [262.0, 60.0],
    [265.0, 57.5],
    [270.0, 55.0],
    [275.0, 53.0],
    [280.0, 50.5],
    [285.0, 52.0],
    [285.0, 60.5],
    [281.7, 63.3],
    [277.6, 64.1],
    [270.0, 67.0],
    [262.0, 65.0]
  ]

# === 1. Pfade zu den Dateien ===
data_path = "/home/christian/Projekte/Meereis/HudsonBay/data/asi-AMSR2-n6250-20250601-v5.4.hdf"
grid_path = "/home/christian/Projekte/Meereis/HudsonBay/data/LongitudeLatitudeGrid-n6250-Arctic.hdf"

# === 2. Lade Sea Ice Konzentration ===
sd = SD(data_path, SDC.READ)
#print("Datensätze:", sd.datasets().keys())

ice_data = sd.select('ASI Ice Concentration')[:]  # ggf. anpassen
ice_data = np.ma.masked_where(ice_data == 0, ice_data)
ice_data = ice_data / 100.0

# === 3. Lade das Grid ===
grid_sd = SD(grid_path, SDC.READ)
lat = grid_sd.select('Latitudes')[:]
lon = grid_sd.select('Longitudes')[:]

#print("lon min/max:", lon.min(), lon.max())
#print("lat min/max:", lat.min(), lat.max())

# === 4. ROI: Begrenzung auf Hudson Bay / Baffin Island ===
lat_min, lat_max = 50, 75
#lon_min, lon_max = -100, -60
lon_min, lon_max = 260, 300

mask = (lat >= lat_min) & (lat <= lat_max) & (lon >= lon_min) & (lon <= lon_max)

# Maske auf alle Arrays anwenden
ice_data_masked = np.ma.masked_where(~mask, ice_data)
lat_masked = np.ma.masked_where(~mask, lat)
lon_masked = np.ma.masked_where(~mask, lon)

# === 5. Plot mit angepasster Projektion ===
fig = plt.figure(figsize=(7, 5))

# Zentraler Längengrad um Hudson Bay besser zu zentrieren
proj = ccrs.NorthPolarStereo(central_longitude=-80)


# Erzeuge Rechteck als Shapely-Polygon (in lat/lon)
# roi_box = sgeom.box(lon_min, lat_min, lon_max, lat_max)




# Ergebnisse berechnen
results = {}
for name, polygon in polygon_dict.items():
    result = compute_ice_coverage(polygon, ice_data, lon, lat)
    results[name] = result


# Erzeuge Shapely-Polygon für Analyse
manual_polygon = Polygon(polygon_points)
if not manual_polygon.is_valid:
    manual_polygon = manual_polygon.buffer(0)  # einfache Topologie-Korrektur
# Projizieren
manual_proj = proj.project_geometry(manual_polygon, ccrs.PlateCarree())
manual_path = geos_to_path(manual_proj)[0]


# Erzeuge Krümmung als Shapely-Polygon (in lat/lon)
roi_polygon = create_geographic_boundary_polygon(lon_min, lon_max, lat_min, lat_max)

# Projiziere auf Kartenprojektion
roi_proj = proj.project_geometry(roi_polygon, ccrs.PlateCarree())

# Konvertiere in matplotlib Path
roi_path = geos_to_path(roi_proj)[0]

# Setze Kartenrahmen
ax = plt.axes(projection=proj)
ax.set_boundary(roi_path, transform=proj)


# Nur Region um Hudson Bay
ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
ax.add_feature(cfeature.LAND, facecolor='lightgray')
gl = ax.gridlines(
    draw_labels=True,
    linewidth=0.5,
    color='gray',
    alpha=0.5,
    linestyle='--',
    dms=True,
    x_inline=False,
    y_inline=False
)

# ALLES explizit setzen
#gl.top_labels = False
#gl.bottom_labels = True
#gl.left_labels = False
#gl.right_labels = True

gl.xlabel_style = {'size': 7}
gl.ylabel_style = {'size': 7}

# wichtig bei Polprojektionen
gl.rotate_labels = True


# Zeichnen
ax.add_patch(plt.Polygon(
    manual_path.vertices,
    closed=True,
    edgecolor='red',
    facecolor='none',
    linewidth=2,
    transform=proj
))


# Plotten
mesh = ax.pcolormesh(
    lon_masked, lat_masked, ice_data_masked,
    transform=ccrs.PlateCarree(),
    cmap='Blues_r',
    shading='auto'
)



cbar = fig.colorbar(
    mesh,
    ax=ax,
    orientation='vertical',
    fraction=0.045,
    pad=0.1
)
cbar.set_label("Sea ice concentration", fontsize=8)
cbar.ax.tick_params(labelsize=7)
'''
ax.set_title(
    "Sea Ice Concentration – Hudson Bay Region\n6 January 2025",
    fontsize=11,
    pad=10
)
'''
plt.tight_layout()
plt.savefig("HudsonBayArea_HudsonBay_Web.png")
plt.close()


# Ausgabe
for name, r in results.items():
    print(f"\n🧭 {name}")
    print(f"  Gesamtfläche:          {r['total_area_km2']:,.2f} km²")
    print(f"  Relative Bedeckung:    {r['relative_cover_km2']:,.2f} km² ({r['relative_percent']:.2f}%)")
    print(f"  Absolute Bedeckung ≥20%: {r['absolute_cover_km2']:,.2f} km² ({r['absolute_percent']:.2f}%)")
