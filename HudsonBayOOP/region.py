# region.py (angepasst)
import geopandas as gpd
from shapely.geometry import Polygon
import json
import os

class RegionManager:
    def __init__(self, polygon_json, natural_earth_path, geojson_dir):
        self.polygon_json = polygon_json
        self.geojson_dir = geojson_dir
        self.natural_earth_path = natural_earth_path
        self.polygons = self.load_region_polygons()
        self.water_areas = self.calculate_water_areas()

    def load_region_polygons(self):
        with open(self.polygon_json) as f:
            data = json.load(f)

        polygons = {}
        for name, coords in data.items():
            # Transformiere Längengrade 0–360 → -180–180
            transformed_coords = [
                (((lon + 180) % 360) - 180, lat)
                for lon, lat in coords
            ]
            polygon = Polygon(transformed_coords)
            self.save_geojson(name, polygon)
            polygons[name] = polygon

        print(f"[✔] Regionen geladen: {list(polygons.keys())}")
        return polygons

    def calculate_water_areas(self):
        ocean = gpd.read_file(self.natural_earth_path)
        water_areas = {}
        for name, polygon in self.polygons.items():
            region_gdf = gpd.GeoDataFrame(geometry=[polygon], crs="EPSG:4326")
            region_gdf = region_gdf.to_crs(ocean.crs)
            clipped = gpd.overlay(region_gdf, ocean, how="intersection")
            water_area_km2 = clipped.to_crs(epsg=6931).area.sum() / 1e6  # m² → km²
            water_areas[name] = water_area_km2
            print(f"[i] Region {name}: Wasserfläche ~ {water_area_km2:.2f} km²")
        return water_areas

    def save_geojson(self, region_name, polygon):
        geojson_path = os.path.join(self.geojson_dir, f"{region_name.replace(' ', '_')}_polygon.geojson")
        if not os.path.exists(geojson_path):
            gpd.GeoDataFrame({"region": [region_name]}, geometry=[polygon], crs="EPSG:4326").to_file(geojson_path, driver="GeoJSON")
            print(f"[✔] Polygon gespeichert: {geojson_path}")
        return geojson_path
