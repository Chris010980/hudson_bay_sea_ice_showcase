"""Debug tests for reference-region geometry."""

from pathlib import Path

import numpy as np
import rasterio
from matplotlib.path import Path as MplPath
from pyproj import Transformer

from src.analysis.reference_builder import ReferenceBuilder


def test_debug_region_pixel_membership(
    synthetic_reference_raster: Path,
    synthetic_region_file: Path,
) -> None:
    """Print pixel-center membership for the synthetic test regions."""

    builder = ReferenceBuilder(
        reference_tif=synthetic_reference_raster,
        region_file=synthetic_region_file,
    )

    builder._load_reference()
    builder._load_regions()

    with rasterio.open(synthetic_reference_raster) as src:
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
            "EPSG:3411",
            "EPSG:4326",
            always_xy=True,
        )

        lon, lat = transformer.transform(xs, ys)

    points = np.column_stack((lon, lat))

    for region_name, region in builder.regions.items():
        path = MplPath(region["coords"])

        inside = path.contains_points(points)

        print(f"\nRegion: {region_name}")
        print("-" * 60)

        for index, (row, col) in enumerate(
            zip(rows.ravel(), cols.ravel())
        ):
            print(
                f"pixel {index:2d} "
                f"(row={row}, col={col}) "
                f"lon={lon[index]:10.6f} "
                f"lat={lat[index]:10.6f} "
                f"inside={inside[index]}"
            )

        print(
            "\nSelected pixel indices:",
            np.flatnonzero(inside),
        )