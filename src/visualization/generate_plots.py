"""Command line entry point for plot generation."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import matplotlib.pyplot as plt

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.config.logging_config import (
    DEFAULT_LOG_FILE,
    configure_logging,
)
from src.visualization.geotiff_plot import (
    DEFAULT_OUTPUT_PLOT_PATH,
    DEFAULT_REGION_BOUNDS,
    SeaIcePlotter,
)
from src.visualization.timeseries_plot import TimeSeriesPlotter

logger = logging.getLogger(__name__)

PLOT_TYPES = ("overview", "timeseries", "polar", "all")
"""Valid plot types (the parse_args choices and RUNNERS keys)."""

TimeSeriesFactory = Callable[[], TimeSeriesPlotter]
"""Constructor contract of the time-series plotter (issue #74)."""

MapPlotterFactory = Callable[..., SeaIcePlotter]
"""Constructor contract of the overview plotter (issue #74)."""

PlotRunner = Callable[
    [argparse.Namespace, TimeSeriesFactory, MapPlotterFactory],
    None,
]
"""Signature of a plot mode runner (issue #74)."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line options for the plot generation stage."""

    parser = argparse.ArgumentParser(description="Generate plots.")

    parser.add_argument(
        "plot_type",
        choices=PLOT_TYPES,
        help="Type of plot to generate.",
    )
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    parser.add_argument(
        "--input-tiff",
        default=None,
        help="Path to a GeoTIFF file for the preview plot.",
    )
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
    parser.add_argument(
        "--title",
        default=None,
        help="Optional title for the generated plot.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display the plot window after saving it.",
    )
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


def _generate_timeseries(
    args: argparse.Namespace,
    ts_factory: TimeSeriesFactory,
    map_plotter_factory: MapPlotterFactory,
) -> None:
    """Generate the time-series plots.

    Uniform runner signature for the RUNNERS table: the map
    plotter factory is not used by this mode.
    """

    plotter = ts_factory()

    plotter.plot_timeseries()

    logger.info("Time series plots generated.")


def _generate_polar(
    args: argparse.Namespace,
    ts_factory: TimeSeriesFactory,
    map_plotter_factory: MapPlotterFactory,
) -> None:
    """Generate the polar plots.

    Uniform runner signature for the RUNNERS table: the map
    plotter factory is not used by this mode.
    """

    plotter = ts_factory()

    plotter.plot_polar()

    logger.info("Polar plots generated.")


def _generate_all(
    args: argparse.Namespace,
    ts_factory: TimeSeriesFactory,
    map_plotter_factory: MapPlotterFactory,
) -> None:
    """Generate every plot product.

    Uniform runner signature for the RUNNERS table. When no
    GeoTIFF is available, only the time-series plots are
    regenerated (documented fallback, see Findings.md F-019).
    """

    try:
        map_plotter = map_plotter_factory(
            input_path=args.input_tiff,
            bounds=tuple(args.bounds),
        )

        map_plotter.load()

        # -------------------------------------------------
        # plain overview
        # -------------------------------------------------

        map_plotter.plot_overview()
        map_plotter.save()

        # -------------------------------------------------
        # overview with all regions
        # -------------------------------------------------

        map_plotter.plot_regions()
        map_plotter.save(suffix="regions")

        # -------------------------------------------------
        # one figure per region
        # -------------------------------------------------

        for region in map_plotter.regions:
            map_plotter.plot_single_region(region)

            map_plotter.save(suffix=region.lower().replace(" ", "_"))

    except FileNotFoundError:
        logger.warning("No GeoTIFF available. Skipping overview plots.")

        ts = ts_factory()

        ts.plot_all()

        logger.info("Only time series plots re-generated.")

        return

    ts = ts_factory()

    ts.plot_all()

    logger.info("All plots generated.")


def _generate_overview(
    args: argparse.Namespace,
    ts_factory: TimeSeriesFactory,
    map_plotter_factory: MapPlotterFactory,
) -> None:
    """Generate one overview plot.

    Uniform runner signature for the RUNNERS table: the time
    series factory is not used by this mode.
    """

    # ---------------------------------------------------------
    # Plotter
    # ---------------------------------------------------------

    plotter = map_plotter_factory(
        input_path=args.input_tiff,
        bounds=tuple(args.bounds),
    )

    plotter.load()

    # ---------------------------------------------------------
    # Generate one plot for every region
    # ---------------------------------------------------------

    if args.all_regions:
        for region_name in plotter.regions:
            plotter.plot_single_region(region_name)

            output = Path(args.output)

            region_slug = region_name.lower().replace(" ", "_")
            output_file = (
                output.parent
                / f"{output.stem}_{region_slug}{output.suffix}"
            )

            plotter.save(output_file)

            logger.info("Saved %s", output_file)

        return

    # ---------------------------------------------------------
    # Overview with all regions
    # ---------------------------------------------------------

    if args.regions:
        plotter.plot_regions()

    # ---------------------------------------------------------
    # Only selected regions
    # ---------------------------------------------------------

    elif args.region:
        plotter.plot_overview()

        plotter.draw_regions(selected=args.region)

    # ---------------------------------------------------------
    # Plain overview
    # ---------------------------------------------------------

    else:
        plotter.plot_overview()

    plotter.save(args.output)

    logger.info("Saved %s", args.output)

    if args.show:
        plt.show()


RUNNERS: Mapping[str, PlotRunner] = {
    "timeseries": _generate_timeseries,
    "polar": _generate_polar,
    "all": _generate_all,
    "overview": _generate_overview,
}


def main(
    argv: Sequence[str] | None = None,
    *,
    ts_factory: TimeSeriesFactory = TimeSeriesPlotter,
    map_plotter_factory: MapPlotterFactory = SeaIcePlotter,
) -> None:
    """Generate sea ice plots."""

    args = parse_args(argv)

    configure_logging(
        level=args.log_level,
        log_file=args.log_file,
    )

    RUNNERS[args.plot_type](args, ts_factory, map_plotter_factory)


if __name__ == "__main__":
    main()
