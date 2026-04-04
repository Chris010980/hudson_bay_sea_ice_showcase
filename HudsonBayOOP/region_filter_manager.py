# region_filter_manager.py
import os
import re
import numpy as np
from glob import glob

class RegionFilterManager:
    def __init__(self, filter_dir):
        self.filter_dir = filter_dir
        os.makedirs(filter_dir, exist_ok=True)
        # Struktur: {(region_name, gdf_length): np.ndarray}
        self._cache = {}

    def get_or_create_filter(self, region_name, polygon, gdf):
        gdf_length = len(gdf)
        key = (region_name, gdf_length)

        # 1️⃣ Schauen, ob Filter im RAM-Cache
        if key in self._cache:
            return self._cache[key]

        # 2️⃣ Falls nicht im RAM, suche Datei
        pattern = os.path.join(self.filter_dir, f"{region_name.replace(' ', '_')}_filter_len*.npy")
        existing_filters = glob(pattern)

        for fpath in existing_filters:
            match = re.search(r"len(\d+)\.npy", fpath)
            if match and int(match.group(1)) == gdf_length:
                try:
                    indices = np.load(fpath)
                    if 0 < len(indices) < gdf_length:
                        self._cache[key] = indices
                        return indices
                except Exception as e:
                    print(f"[!] Fehler beim Laden des Filters: {e}")

        # 3️⃣ Falls kein gültiger Filter, neu berechnen
        mask = gdf.geometry.within(polygon)
        indices = np.where(mask)[0]

        path = os.path.join(self.filter_dir, f"{region_name.replace(' ', '_')}_filter_len{gdf_length}.npy")
        np.save(path, indices)

        self._cache[key] = indices
        return indices
