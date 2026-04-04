# processor.py
import rasterio
#from rasterio.transform import from_origin
import geopandas as gpd
from shapely.geometry import Point
import os
import numpy as np


class GeoTIFFProcessor:
    def __init__(self, pixel_area_km2=625):
        self.pixel_area_km2 = pixel_area_km2

    def geotiff_to_gdf_raw(self, tif_path):
        with rasterio.open(tif_path) as src:
            band = src.read(1)
            transform = src.transform
            mask = (band != src.nodata)
            rows, cols = mask.nonzero()
            xs, ys = rasterio.transform.xy(transform, rows, cols)
            values = band[rows, cols]

            points = [Point(x, y) for x, y in zip(xs, ys)]
            gdf = gpd.GeoDataFrame({'value': values}, geometry=points, crs=src.crs)
            gdf = gdf.to_crs(epsg=4326)
        return gdf

    def apply_region_filter(self, gdf, polygon, region_name, filter_dir):
        os.makedirs(filter_dir, exist_ok=True)
        gdf_length = len(gdf)

        pattern = os.path.join(filter_dir, f"{region_name.replace(' ', '_')}_filter_len{gdf_length}.npy")
        
        # Versuche Filter zu laden
        if os.path.exists(pattern):
            indices = np.load(pattern)
            if 0 < len(indices) < gdf_length:
                #print(f"[✔] Filter geladen: {pattern}")
                return gdf.iloc[indices].copy()

        # Filter neu berechnen
        mask = gdf.geometry.within(polygon)
        indices = mask[mask].index.to_numpy()
        np.save(pattern, indices)
        print(f"[+] Neuer Filter gespeichert: {pattern}")
        return gdf.iloc[indices].copy()
