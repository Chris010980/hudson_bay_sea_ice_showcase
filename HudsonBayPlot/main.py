import json
import os
import numpy as np
import matplotlib.pyplot as plt
from pyhdf.SD import SD, SDC
from shapely.geometry import Polygon
import geopandas as gpd

from ice_analysis import compute_ice_coverage_from_gdf, hdf_to_geodataframe, get_polygon_mask
from plotting import plot_ice_map
import cartopy.crs as ccrs

from pathlib import Path



# === Parameter ===
polygon_json = "polygons/HudsonBayArea.json"
geojson_dir = "polygons"
data_path = "data/asi-AMSR2-n6250-20250601-v5.4.hdf"
grid_path = "data/LongitudeLatitudeGrid-n6250-Arctic.hdf"
region_bounds = (260, 300, 50, 75)  # lon_min, lon_max, lat_min, lat_max
filter_dir = Path("polygon_filters")
filter_dir.mkdir(exist_ok=True)

# === Polygon laden und in GeoJSON konvertieren ===
with open(polygon_json, "r") as f:
    polygon_dict_raw = json.load(f)

polygon_dict = {}
for name, points in polygon_dict_raw.items():
    polygon = Polygon(points).buffer(0)
    polygon_dict[name] = polygon

    gdf = gpd.GeoDataFrame(index=[0], geometry=[polygon], crs="EPSG:4326")
    gdf.to_file(os.path.join(geojson_dir, f"{name.replace(' ', '_')}.geojson"), driver="GeoJSON")

# === Daten laden ===
sd = SD(data_path, SDC.READ)
ice_data = np.ma.masked_where((ice := sd.select('ASI Ice Concentration')[:]) == 0, ice / 100.0)

grid_sd = SD(grid_path, SDC.READ)
lat = grid_sd.select('Latitudes')[:]
lon = grid_sd.select('Longitudes')[:]

# === Maske auf Region ===
lon_min, lon_max, lat_min, lat_max = region_bounds
mask = (lat >= lat_min) & (lat <= lat_max) & (lon >= lon_min) & (lon <= lon_max)
ice_data_masked = np.ma.masked_where(~mask, ice_data)
lat_masked = np.ma.masked_where(~mask, lat)
lon_masked = np.ma.masked_where(~mask, lon)


# Erzeuge GeoDataFrame einmalig
gdf = hdf_to_geodataframe(ice_data, lon, lat)
results = {}

for name, polygon in polygon_dict.items():
    mask = get_polygon_mask(gdf, polygon, name, filter_dir)
    gdf_region = gdf[mask]
    
    result = compute_ice_coverage_from_gdf(gdf_region, polygon)
    results[name] = result


# === Plot ===
fig = plt.figure(figsize=(10, 8))
proj = ccrs.NorthPolarStereo(central_longitude=-80)
ax = plt.axes(projection=proj)
plot_ice_map(ax, lon_masked, lat_masked, ice_data_masked, proj, region_bounds,
             title="Sea Ice Concentration – Hudson Bay (2025-06-01)")
plt.tight_layout()
plt.show()

# === Ausgabe ===
for name, r in results.items():
    print(f"\n🧭 {name}")
    print(f"  Gesamtfläche:          {r['total_area_km2']:,.2f} km²")
    print(f"  Relative Bedeckung:    {r['relative_cover_km2']:,.2f} km² ({r['relative_percent']:.2f}%)")
    print(f"  Absolute Bedeckung ≥20%: {r['absolute_cover_km2']:,.2f} km² ({r['absolute_percent']:.2f}%)")