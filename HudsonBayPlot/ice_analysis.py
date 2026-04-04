import numpy as np
from shapely.geometry import Point, Polygon
import pandas as pd
import geopandas as gpd

def hdf_to_geodataframe(ice_data, lon, lat):
    """
    Wandelt HDF-Daten in ein GeoDataFrame um (nur gültige Datenpunkte).
    """
    valid_mask = ~ice_data.mask
    flat_lon = lon[valid_mask].flatten()
    flat_lat = lat[valid_mask].flatten()
    flat_ice = ice_data[valid_mask].flatten()

    df = pd.DataFrame({
        'lon': flat_lon,
        'lat': flat_lat,
        'ice': flat_ice
    })
    geometry = [Point(xy) for xy in zip(flat_lon, flat_lat)]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")  # WGS84
    return gdf


def compute_ice_coverage_from_gdf(gdf, polygon, threshold=0.2, cell_size_km=6.25):
    """
    Berechnet Eisbedeckung innerhalb eines Polygons auf Basis eines GeoDataFrames.
    """
    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    gdf_poly = gdf[gdf.geometry.within(polygon)]

    total_cells = len(gdf_poly)
    cell_area = cell_size_km ** 2

    if total_cells == 0:
        return {
            'total_area_km2': 0.0,
            'relative_cover_km2': 0.0,
            'absolute_cover_km2': 0.0,
            'relative_percent': 0.0,
            'absolute_percent': 0.0
        }

    total_area = total_cells * cell_area
    relative_cover = gdf_poly['ice'].sum() * cell_area
    absolute_cover = (gdf_poly['ice'] >= threshold).sum() * cell_area

    return {
        'total_area_km2': total_area,
        'relative_cover_km2': relative_cover,
        'absolute_cover_km2': absolute_cover,
        'relative_percent': 100 * relative_cover / total_area,
        'absolute_percent': 100 * absolute_cover / total_area
    }


def get_polygon_mask(gdf, polygon, name, filter_dir):
    """
    Gibt eine Bool-Maske für Punkte im GDF zurück. Verwendet Cache, wenn vorhanden.
    """
    mask_file = filter_dir / f"{name}_mask.npz"

    if mask_file.exists():
        mask = np.load(mask_file)['mask']
        print(f"✅ Maske für {name} geladen ({mask.sum()} Punkte innerhalb)")
    else:
        if not polygon.is_valid:
            polygon = polygon.buffer(0)

        mask = gdf.geometry.within(polygon).values
        np.savez_compressed(mask_file, mask=mask)
        print(f"💾 Maske für {name} gespeichert ({mask.sum()} Punkte innerhalb)")

    return mask


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
    #if np.ma.isMaskedArray(ice_inside):
    #    ice_inside = ice_inside.filled(0)
    print(f"  ➤ Masked Array? {np.ma.isMaskedArray(ice_inside)}")
    print(f"  ➤ Masked Count: {np.ma.count_masked(ice_inside) if np.ma.isMaskedArray(ice_inside) else 0}")
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
    return Polygon(boundary_coords)