"""Project-wide scientific and data-format constants.

These values describe the NSIDC G02135 sea-ice data products and
the scientific conventions of the analysis. They are shared by
at least two modules or define project-level domain settings;
purely module-specific tuning stays near its use in the
responsible module.
"""

from __future__ import annotations

# NSIDC G02135 daily GeoTIFF product. Concentrations are encoded
# in tenths of a percent (valid range 0..1000); 2550 marks
# missing pixels.
DEFAULT_PRODUCT = "concentration"
CONCENTRATION_SCALE = 1000
MISSING_PIXEL_VALUE = 2550

# A pixel counts as sea ice from this concentration upwards
# (15 percent, encoded in tenths of a percent).
ICE_CONCENTRATION_THRESHOLD_TENTHS = 150

# NSIDC sea-ice polar stereographic grid with 25 km pixels.
PIXEL_AREA_KM2 = 625.0

# Coordinate reference systems: the NSIDC data grid, geographic
# coordinates, and the equal-area CRS used for area computation.
DATA_EPSG = 3411
DATA_CRS = "EPSG:3411"
WGS84_CRS = "EPSG:4326"
AREA_EPSG = 6933

# WMO 1981-2010 climate normal used for climatology and
# anomalies.
CLIMATOLOGY_START_YEAR = 1981
CLIMATOLOGY_END_YEAR = 2010

# Threshold levels (percent coverage) for break-up/freeze-up
# event detection.
EVENT_THRESHOLDS_PERCENT = (10.0, 50.0, 90.0)

# Geographic bounds (lon_min, lon_max, lat_min, lat_max) of the
# Hudson Bay showcase region.
HUDSON_BAY_BOUNDS = (260.0, 300.0, 50.0, 75.0)

# Resolution (dpi) for saved publication figures.
FIGURE_SAVE_DPI = 300
