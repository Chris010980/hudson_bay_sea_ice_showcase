"""
Build reference masks for all analysis regions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from pyproj import Transformer
from matplotlib.path import Path as MplPath
from src.config.paths import PROJECT_ROOT

import geopandas as gpd
from shapely.geometry import Polygon

logger = logging.getLogger(__name__)


REFERENCE_TIF = PROJECT_ROOT / "src" / "config" / "reference.tif"

FILTER_DIR = PROJECT_ROOT / "output" / "reference" / "filters"

REFERENCE_SUMMARY = PROJECT_ROOT / "output" / "reference" / "reference_summary.json"

class ReferenceBuilder:

    def __init__(
        self,
        reference_tif: str | Path = REFERENCE_TIF,
        region_file: str | Path | None = None,
    ):

        self.reference_tif = Path(reference_tif)

        if region_file is None:
            region_file = PROJECT_ROOT / "src/config/regions.json"

        self.region_file = Path(region_file)

        self.band = None
        self.transform = None

        self.regions = {}

        self.crs = "EPSG:3411"

        self.mask_dir = FILTER_DIR

        self.pixel_area_km2 = 625.0

        self.reference_summary = {}

    # ---------------------------------------------------------
    # public API
    # ---------------------------------------------------------

    def build(self):

        FILTER_DIR.mkdir(parents=True, exist_ok=True)

        self._load_reference()

        self._check_missing_values()

        self._load_regions()

        self._create_region_masks()

        self._calculate_reference_areas()

        self._save_summary()

    # ---------------------------------------------------------
    # reference
    # ---------------------------------------------------------

    def _load_reference(self):

        logger.info("Loading reference GeoTIFF")

        with rasterio.open(self.reference_tif) as src:

            self.band = src.read(1)

            self.transform = src.transform

    def _check_missing_values(self):

        missing = np.count_nonzero(self.band == 2550)

        if missing:

            raise RuntimeError(
                f"Reference contains {missing} missing pixels."
            )

        logger.info("Reference contains no missing values.")

    # ---------------------------------------------------------
    # regions
    # ---------------------------------------------------------

    def _load_regions(self):

        with open(self.region_file, encoding="utf-8") as f:
            data = json.load(f)

        self.regions = {}

        for name, region in data["regions"].items():

            coords = np.asarray(region["polygon"], dtype=float)

            coords[:, 0] = np.where(
                coords[:, 0] > 180,
                coords[:, 0] - 360,
                coords[:, 0],
            )

            self.regions[name] = {
                "coords": coords,
                "polygon": Polygon(coords),
            }

    # ---------------------------------------------------------
    # masks
    # ---------------------------------------------------------

    def _create_region_masks(self) -> None:
        """Create one boolean mask per analysis region."""

        with rasterio.open(self.reference_tif) as src:

            self.band = src.read(1)

            self.transform = src.transform

            rows, cols = np.indices(src.shape)

            xs, ys = rasterio.transform.xy(
                src.transform,
                rows,
                cols,
                offset="center",
            )

            xs = np.asarray(xs).ravel()
            ys = np.asarray(ys).ravel()

            transformer = Transformer.from_crs(
                self.crs,
                "EPSG:4326",
                always_xy=True,
            )

            lon, lat = transformer.transform(xs, ys)

        points = np.column_stack((lon, lat))

        for name, region in self.regions.items():

            coords = self.regions[name]["coords"]

            path = MplPath(coords)

            mask = path.contains_points(points)

            mask = mask.reshape(src.height, src.width)

            polygon_count = np.count_nonzero(mask)

            # -------------------------------------------------
            # Keep only valid ocean pixels
            # -------------------------------------------------

            water_mask = (
                (self.band >= 0)
                &
                (self.band <= 1000)
            )

            mask &= water_mask

            water_count = np.count_nonzero(mask)

            water_area_pixel_km2 = water_count * self.pixel_area_km2

            indices = np.flatnonzero(mask)

            self.reference_summary[name] = {
                "polygon_pixels": int(polygon_count),
                "water_pixels": int(water_count),
                "pixel_area_km2": int(self.pixel_area_km2),
                "water_area_pixel_km2": float(water_area_pixel_km2),
                "expected_water_pixels": int(water_count),
            }

            np.save(
                self.mask_dir / f"{name}_water.npy",
                indices,
            )

            logger.info(
                "Region %-20s : %5d polygon pixels -> %5d water pixels (%.1f%%) / water area %.1f km²",
                name,
                polygon_count,
                water_count,
                100 * water_count / polygon_count,
                water_area_pixel_km2,
            )

    # ---------------------------------------------------------
    # Naturalearth reference areas
    # ---------------------------------------------------------

    def _calculate_reference_areas(self):
        ocean = gpd.read_file(
            PROJECT_ROOT / "data" / "naturalearth" / "ocean.shp"
        )

        for name, region in self.regions.items():

            polygon = self.regions[name]["polygon"]

            region_gdf = gpd.GeoDataFrame(
                geometry=[polygon],
                crs="EPSG:4326",
            )

            intersection = gpd.overlay(
                region_gdf,
                ocean,
                how="intersection",
            )

            area = (
                intersection
                .to_crs(epsg=6933)
                .area
                .sum()
                / 1e6
            )

            self.reference_summary[name][
                "naturalearth_water_area_km2"
            ] = round(float(area),1)

            pixel_area = self.reference_summary[name]["water_area_pixel_km2"]

            difference = pixel_area - area

            difference_percent = (
                100 * difference / area
            )

            self.reference_summary[name]["difference_km2"] = round(float(difference),1)

            self.reference_summary[name]["difference_percent"] = round(float(difference_percent),2)

    # ---------------------------------------------------------
    # save json summary
    # ---------------------------------------------------------

    def _save_summary(self):

        with open(
            REFERENCE_SUMMARY,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                self.reference_summary,
                f,
                indent=4,
            )

        logger.info(
            "Saved reference summary to %s",
            REFERENCE_SUMMARY,
        )

    # ---------------------------------------------------------
    # check if instance already exists
    # ---------------------------------------------------------

    def ensure_reference(self) -> None:

        if not REFERENCE_SUMMARY.exists():
            logger.info("Reference metadata missing.")
            self.build()
            return

        self._load_regions()

        missing = []

        for region in self.regions:

            mask = self.mask_dir / f"{region}_water.npy"

            if not mask.exists():
                missing.append(region)

        if missing:

            logger.warning(
                "Missing reference masks for: %s",
                ", ".join(missing),
            )

            self.build()

            return

        logger.info("Reference already exists.")