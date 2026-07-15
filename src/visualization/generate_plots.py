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
    parser.add_argument(
        "--regions",
        action="store_true",
        help="Overlay analysis regions on the overview plot.",
    )

    parser.add_argument(
        "--region",
        nargs="+",
        metavar="REGION",
        help="Generate plots only for the selected region(s).",
    )

    parser.add_argument(
        "--all-regions",
        action="store_true",
        help="Generate one plot for every analysis region.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Generate sea ice plots."""

    args = parse_args(argv)

    configure_logging(
        level=args.log_level,
        log_file=args.log_file,
    )

    # -------------------------------------------------------------
    # Generate one plot for every region
    # -------------------------------------------------------------

    if args.all_regions:

        from src.visualization.geotiff_plot import load_regions

        regions = load_regions()

        for region_name in regions:

            output = Path(args.output)

            output_file = (
                output.parent /
                f"{output.stem}_{region_name.lower().replace(' ', '_')}{output.suffix}"
            )

            plot_geotiff_region(
                input_path=args.input_tiff,
                output_path=output_file,
                bounds=tuple(args.bounds),
                title=region_name,
                show=args.show,
                show_regions=True,
                region=[region_name],
            )

            logger.info("Saved %s", output_file)

        return

    # -------------------------------------------------------------
    # Normal plot
    # -------------------------------------------------------------

    show_regions = args.regions or args.region is not None

    output_path = plot_geotiff_region(
        input_path=args.input_tiff,
        output_path=args.output,
        bounds=tuple(args.bounds),
        title=args.title,
        show=args.show,
        show_regions=show_regions,
        region=args.region,
    )

    logger.info("Saved %s", output_path)


if __name__ == "__main__":
    main()
