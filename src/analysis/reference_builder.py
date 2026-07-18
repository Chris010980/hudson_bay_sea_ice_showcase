"""
Build reference masks for all analysis regions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from matplotlib.path import Path as MplPath
from src.config.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)


REFERENCE_TIF = PROJECT_ROOT / "src" / "config" / "reference.tif"

FILTER_DIR = PROJECT_ROOT / "output" / "reference" / "filters"


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

    # ---------------------------------------------------------
    # public API
    # ---------------------------------------------------------

    def build(self):

        FILTER_DIR.mkdir(parents=True, exist_ok=True)

        self._load_reference()

        self._check_missing_values()

        self._load_regions()

        self._create_region_masks()

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

        self.regions = data["regions"]

    # ---------------------------------------------------------
    # masks
    # ---------------------------------------------------------

    def _create_region_masks(self) -> None:
        """Create one boolean mask per analysis region."""

        with rasterio.open(self.reference_tiff) as src:

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
                src.crs,
                "EPSG:4326",
                always_xy=True,
            )

            lon, lat = transformer.transform(xs, ys)

        points = np.column_stack((lon, lat))

        for name, region in self.regions.items():

            polygon = np.asarray(region["polygon"], dtype=float)

            polygon[:, 0] = np.where(
                polygon[:, 0] > 180,
                polygon[:, 0] - 360,
                polygon[:, 0],
            )

            path = MplPath(polygon)

            mask = path.contains_points(points)

            mask = mask.reshape(src.height, src.width)

            np.save(
                self.mask_dir / f"{name}.npy",
                mask,
            )

            logger.info(
                "Created mask for %s (%d pixels)",
                name,
                mask.sum(),
            )