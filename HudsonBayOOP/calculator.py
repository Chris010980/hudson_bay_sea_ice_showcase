# calculator.py

class IceCoverageCalculator:
    def __init__(self, pixel_area_km2=625):
        self.pixel_area_km2 = pixel_area_km2

    def compute_ice_coverage(self, region_gdf, water_area_km2):
        # Zähle Pixel mit raw == 2550
        num_nan = len(region_gdf[region_gdf["value"] == 2550])

        # Ungültige Werte maskieren
        invalid_values = [2510, 2530, 2540, 2550]
        valid_mask = region_gdf["value"] >= 0
        for val in invalid_values:
            valid_mask &= region_gdf["value"] != val

        region_gdf = region_gdf[valid_mask].copy()
        if region_gdf.empty:
            return None

        water_pixel_count = len(region_gdf)

        # Skaliere und maskiere Eis
        region_gdf["ice"] = region_gdf["value"] / 1000.0
        region_gdf = region_gdf[region_gdf["ice"] >= 0.15].copy()

        pixel_area = self.pixel_area_km2
        total_water_pixel_count = water_pixel_count + num_nan

        absolute_ice_area = len(region_gdf) * pixel_area
        relative_ice_area = region_gdf["ice"].sum() * pixel_area

        return {
            "total_water_pixel_count": total_water_pixel_count,
            "valid_water_pixel_count": water_pixel_count,
            "total_pixel_area_km2": total_water_pixel_count * pixel_area,
            "total_water_area_km2": water_area_km2,
            "valid_water_area_km2": water_pixel_count * pixel_area,
            "absolute_ice_area_km2": absolute_ice_area,
            "relative_ice_area_km2": relative_ice_area,
            "absolute_coverage_percent_of_water": (absolute_ice_area / (water_pixel_count * pixel_area)) * 100 if water_pixel_count > 0 else 0,
            "relative_coverage_percent_of_water": (relative_ice_area / (water_pixel_count * pixel_area)) * 100 if water_pixel_count > 0 else 0
        }
