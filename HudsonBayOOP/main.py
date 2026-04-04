# main.py
import os
from region import RegionManager
from processor import GeoTIFFProcessor
from calculator import IceCoverageCalculator
from results import ResultsManager
from plotter import Plotter
from metadata import MetadataPrinter
from utils import extract_date_from_filename, ensure_directories
from region_filter_manager import RegionFilterManager
from downloader import NSIDCDownloader
import pandas as pd

class MainPipeline:
    def __init__(self, base_dir, polygon_json, natural_earth_path, geojson_dir):
        ensure_directories()
        self.region_mgr = RegionManager(polygon_json, natural_earth_path, geojson_dir)
        self.processor = GeoTIFFProcessor()
        self.calculator = IceCoverageCalculator()
        self.results_mgr = ResultsManager()
        self.base_dir = base_dir
        self.filter_mgr = RegionFilterManager(filter_dir="filters/")

    def run(self):
        '''
        for root, _, files in os.walk(self.base_dir):
            for filename in files:
                if "concentration" not in filename or not filename.endswith(".tif"):
                    continue

                tif_path = os.path.join(root, filename)
                print(f"[i] Verarbeite: {tif_path}")

                date = extract_date_from_filename(filename)
                csv_path = "results/ice_coverage_summary.csv"
                if self.results_mgr.is_date_already_processed(date, csv_path):
                    print(f"[i] Überspringe {filename}, Datum {date} bereits verarbeitet.")
                    # Bestehende Zeilen für dieses Datum in results aufnehmen
                    existing_rows = self.results_mgr.load_existing_rows_for_date(date)
                    for _, row in existing_rows.iterrows():
                        self.results_mgr.add_result(row.to_dict())
                    continue

                gdf = self.processor.geotiff_to_gdf_raw(tif_path)

                for region_name, polygon in self.region_mgr.polygons.items():
                    indices = self.filter_mgr.get_or_create_filter(region_name, polygon, gdf)
                    region_gdf = gdf.iloc[indices].copy()

                    if region_gdf.empty:
                        continue

                    stats = self.calculator.compute_ice_coverage(
                        region_gdf, self.region_mgr.water_areas.get(region_name, 0)
                    )
                    if stats is None:
                        continue
                    stats.update({"region": region_name, "date": date})
                    self.results_mgr.add_result(stats)

        df = self.results_mgr.save_to_csv("results/ice_coverage_summary.csv")
        '''
        df = pd.read_csv("results/ice_coverage_summary.csv")
        Plotter(df).plot_timeseries_by_region()
        Plotter(df).plot_polar_by_region()


if __name__ == "__main__":
    '''
    downloader = NSIDCDownloader(
        base_url="https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/geotiff",
        local_base="data/geotiff"
    )
    downloader.sync()
    '''
    pipeline = MainPipeline(
        base_dir="data",
        polygon_json="polygons/HudsonBayArea.json",
        natural_earth_path="naturalearth/ne_110m_ocean.shp",
        geojson_dir = "GeoJson/"
    )
    pipeline.run()
