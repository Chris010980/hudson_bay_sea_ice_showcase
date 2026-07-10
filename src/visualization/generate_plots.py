"""Command line entry point for plot generation."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.config.logging_config import DEFAULT_LOG_FILE, configure_logging
from src.visualization.geotiff_plot import DEFAULT_OUTPUT_PLOT_PATH, DEFAULT_REGION_BOUNDS, plot_geotiff_region


logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line options for the plot generation stage."""

    parser = argparse.ArgumentParser(description="Generate sea ice plots.")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    parser.add_argument("--input-tiff", default=None, help="Path to a GeoTIFF file for the preview plot.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PLOT_PATH),
        help="Destination for the generated preview plot.",
    )
    parser.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        metavar=("LON_MIN", "LON_MAX", "LAT_MIN", "LAT_MAX"),
        default=list(DEFAULT_REGION_BOUNDS),
        help="Geographic bounds used for the preview map.",
    )
    parser.add_argument("--title", default=None, help="Optional title for the generated plot.")
    parser.add_argument("--show", action="store_true", help="Display the plot window after saving it.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Generate the initial GeoTIFF-based preview plot for the pipeline."""

    args = parse_args(argv)
    configure_logging(level=args.log_level, log_file=args.log_file)

    output_path = plot_geotiff_region(
        input_path=args.input_tiff,
        output_path=args.output,
        bounds=tuple(args.bounds),
        title=args.title,
        show=args.show,
    )
    logger.info("Saved sea ice preview plot to %s", output_path)


if __name__ == "__main__":
    main()
