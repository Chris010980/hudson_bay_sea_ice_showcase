from __future__ import annotations

import json
import logging
from src.config.paths import PROJECT_ROOT
from pathlib import Path

logger = logging.getLogger(__name__)

FILTER_DIR = PROJECT_ROOT / "output" / "reference" / "filters"

REFERENCE_JSON = PROJECT_ROOT / "output" / "reference" / "reference_summary.json"

class RegionAnalyzer:

    def __init__(
        self,
        input_tif,
        filter_dir=FILTER_DIR,
        reference_json=REFERENCE_JSON,
    ):
        self.input_tif = Path(input_tif)

        self.band = None
        self.transform = None

        self.reference = {}
        self.results = {}

    def analyze(self):

        self._load_reference()

        self._load_geotiff()

        self._analyze_regions()

        return self.results