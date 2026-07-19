"""
Analyze one sea-ice GeoTIFF using the reference masks.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio

from src.config.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

REFERENCE_JSON = (
    PROJECT_ROOT / "output" / "reference" / "reference_summary.json"
)

FILTER_DIR = (
    PROJECT_ROOT / "output" / "reference" / "filters"
)


class RegionAnalyzer:

    def __init__(
        self,
        input_tif: str | Path,
        reference_json: str | Path = REFERENCE_JSON,
        filter_dir: str | Path = FILTER_DIR,
        pixel_area_km2: float = 625.0,
    ):

        self.input_tif = Path(input_tif)

        self.reference_json = Path(reference_json)
        self.filter_dir = Path(filter_dir)

        self.pixel_area_km2 = pixel_area_km2

        self.band = None
        self.reference = {}

        self.date = None

        self.results = {}

    # ---------------------------------------------------------
    # public API
    # ---------------------------------------------------------

    def analyze(self):

        self._load_reference()

        self._load_geotiff()

        if self.band is None:
            return {}

        self._extract_date()

        self._analyze_regions()

        return self.results

    # ---------------------------------------------------------
    # loading
    # ---------------------------------------------------------

    def _load_reference(self):

        with open(self.reference_json, encoding="utf-8") as f:
            self.reference = json.load(f)

    def _load_geotiff(self):

        logger.info("Loading %s", self.input_tif.name)

        try:

            with rasterio.open(self.input_tif) as src:

                self.band = src.read(1)

        except Exception as exc:

            logger.error(
                "Cannot read %s: %s",
                self.input_tif.name,
                exc,
            )

            self.band = None

    def _extract_date(self):

        match = re.search(r"(\d{8})", self.input_tif.stem)

        if match:
            self.date = datetime.strptime(
                match.group(1),
                "%Y%m%d",
            ).date()

    # ---------------------------------------------------------
    # analysis
    # ---------------------------------------------------------

    def _analyze_regions(self):

        for region_name, reference in self.reference.items():

            self._analyze_region(
                region_name,
                reference,
            )

    def _analyze_region(
        self,
        region_name,
        reference,
    ):

        indices = np.load(
            self.filter_dir / f"{region_name}_water.npy"
        )

        values = self.band.flat[indices]

        # -------------------------------------------------
        # Step 1: Missing values
        # -------------------------------------------------

        missing_pixels = np.count_nonzero(
            values == 2550
        )

        if missing_pixels > 0:

            logger.warning(
                "%s skipped (%d missing pixels)",
                region_name,
                missing_pixels,
            )

            return

        # -------------------------------------------------
        # Step 2: Keep only valid water pixels
        # -------------------------------------------------

        water = values[
            (values >= 0)
            &
            (values <= 1000)
        ]

        expected = reference["water_pixels"]

        if len(water) != expected:

            logger.warning(
                "%s: expected %d water pixels but found %d",
                region_name,
                expected,
                len(water),
            )

            return

        # -------------------------------------------------
        # Step 3: Sea ice
        # -------------------------------------------------

        ice = water >= 150

        absolute_ice_area = (
            ice.sum()
            * self.pixel_area_km2
        )

        relative_ice_area = (
            water[ice].sum()
            / 1000.0
            * self.pixel_area_km2
        )

        water_area = reference["water_area_pixel_km2"]

        self.results[region_name] = {

            "region": region_name,

            "date": self.date,

            "water_pixels": expected,

            "water_area_km2": water_area,

            "absolute_ice_area_km2": absolute_ice_area,

            "relative_ice_area_km2": relative_ice_area,

            "absolute_coverage_percent":
                100.0 * absolute_ice_area / water_area,

            "relative_coverage_percent":
                100.0 * relative_ice_area / water_area,

            "missing_pixels": 0,
        }

        logger.info(
            "%-20s : %6.1f %% (%8.0f km²)",
            region_name,
            100.0 * relative_ice_area / water_area,
            relative_ice_area,
        )