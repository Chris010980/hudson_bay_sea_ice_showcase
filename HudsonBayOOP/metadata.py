# metadata.py
import rasterio

class MetadataPrinter:
    @staticmethod
    def print_tif_metadata(tif_path):
        with rasterio.open(tif_path) as src:
            print("Dateiname:", tif_path)
            print("Breite:", src.width)
            print("Höhe:", src.height)
            print("Bands:", src.count)
            print("CRS:", src.crs)
            print("Transform:", src.transform)
