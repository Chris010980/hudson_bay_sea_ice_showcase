"""
Time series plots for Hudson Bay sea ice analysis.
"""

from __future__ import annotations

import logging

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.colors as mcolors

import numpy as np
import pandas as pd

from datetime import datetime
from matplotlib.dates import DateFormatter, MonthLocator

from src.config.paths import PROJECT_ROOT

RESULTS_CSV = PROJECT_ROOT / "output" / "analysis" / "ice_coverage_summary.csv"
OUTPUT_DIR = PROJECT_ROOT / "output" / "plots"

logger = logging.getLogger(__name__)

mpl.rcParams.update({
    "figure.dpi": 150,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "legend.frameon": False,
    "lines.linewidth": 1.8,
    "grid.linestyle": "--",
    "grid.alpha": 0.3,
    "grid.color": "0.6",
    "savefig.bbox": "tight",
})


class TimeSeriesPlotter:

    def __init__(
        self,
        csv_file: str | Path = RESULTS_CSV,
    ):

        self.csv_file = Path(csv_file)

        self.df = None

        self.unique_years = None
        self.norm = None
        self.cmap = None

        self.month_locator = None
        self.month_formatter = None

        self.show_decadal_mean = False

        self.max_gap_days = 21

        self._configure_style()

    def _configure_style(self):

        self.figure_size = (9,6)

        self.polar_figure_size = (6.5, 6)

        self.linewidth = 1.2

        self.grid_alpha = 0.4

        self.title_fontsize = 15

        self.axis_fontsize = 11

        self.tick_fontsize = 9

        self.legend_fontsize = 9

        self.colorbar_fontsize = 10
        self.colorbar_ticksize = 8

        # Polar layout
        self.polar_left = 0.1
        self.polar_right = 0.86
        self.polar_bottom = 0.08
        self.polar_top = 0.94

        self.polar_colorbar_pad = 0.12
        self.polar_colorbar_fraction = 0.045

        self.month_locator = MonthLocator()
        self.month_formatter = DateFormatter("%b")

        self.theta_offset = np.deg2rad(15)

        self.output_dir = OUTPUT_DIR / "timeseries"

        self.polar_output_dir = OUTPUT_DIR / "polar"

        self.relative_series = (
            "relative_coverage_percent_of_water",
            "Relative ice coverage (%)",
            "relative",
        )

        self.absolute_series = (
            "absolute_coverage_percent_of_water",
            "Absolute ice coverage (%)",
            "absolute",
        )


    def load(self):
        """Load the processed sea-ice statistics."""
        self.df = pd.read_csv(
            self.csv_file,
            parse_dates=["date"],
        )

        self._prepare_dataframe()

    def _prepare_dataframe(self):
        """Prepare additional columns required for plotting."""
        df = self.df

        df["year"] = df.date.dt.year

        df["month"] = df.date.dt.month

        df["day"] = df.date.dt.day

        df["day_of_year"] = df.date.dt.dayofyear

        df["plot_date"] = df.date.apply(
            lambda d: datetime(
                2000,
                d.month,
                d.day,
            )
        )

        self.unique_years = sorted(df.year.unique())

        self.norm = mcolors.Normalize(
            min(self.unique_years),
            max(self.unique_years),
        )

        self.cmap = mpl.colormaps["plasma"]

    def _insert_gaps(
        self,
        df,
    ):
        """Insert NaN rows to prevent long gaps being connected."""

        df = df.sort_values("date").copy()

        delta = df.date.diff().dt.days

        breaks = delta > self.max_gap_days

        if not breaks.any():

            return df

        rows = []

        for i, row in df.iterrows():

            rows.append(row)

            if breaks.loc[i]:

                nan = row.copy()

                nan.iloc[:] = np.nan

                nan["plot_date"] = row["plot_date"]

                rows.append(nan)

        return pd.DataFrame(rows)

    def _create_colorbar(
        self,
        fig,
        ax,
        *,
        pad=0.02,
        fraction=0.04,
    ):
        """Add the common year colorbar."""

        sm = plt.cm.ScalarMappable(
            cmap=self.cmap,
            norm=self.norm,
        )

        sm.set_array([])

        cbar = fig.colorbar(
            sm,
            ax=ax,
            pad=pad,
            fraction=fraction,
        )

        cbar.outline.set_edgecolor("0.6")

        cbar.ax.tick_params(
            colors="0.3",
            labelsize=self.colorbar_ticksize,
        )

        cbar.set_label(
            "Year",
            fontsize=self.colorbar_fontsize,
            color="0.3",
        )

    def plot_timeseries(self):
        """Create Cartesian time-series plots for every region."""

        if self.df is None:
            self.load()

        for region in self.df.region.unique():

            self._plot_region(
                region,
                "relative_coverage_percent",
                "Relative ice coverage (%)",
                "relative",
            )

            self._plot_region(
                region,
                "absolute_coverage_percent",
                "Absolute ice coverage (%)",
                "absolute",
            )

    def _plot_region(self, region, column, ylabel, suffix,):
        """Plot one quantity for one analysis region."""
        df_region = self.df[self.df.region == region]

        fig, ax = plt.subplots(figsize=self.figure_size,)

        for spine in ax.spines.values():
            spine.set_color("0.4")
            spine.set_linewidth(0.8)

        # Einzeljahre
        for year in self.unique_years:
            df_year = df_region[df_region["year"] == year].sort_values("plot_date")
            df_year = self._insert_gaps(df_year)
            ax.plot(
                df_year["plot_date"],
                df_year[column],
                color=self.cmap(self.norm(year)),
                linewidth=1.3,
                alpha=0.85
            )

        ax.scatter(
            df_year["plot_date"].iloc[-1],
            df_year[column].iloc[-1],
            s=45,
            color="red",
            edgecolor="black",
            linewidth=0.8,
            zorder=10,
        )

        #ax.set_title(f"{label} – {region}", fontsize=11)
        ax.set_xlabel(
            "Month",
            fontsize=self.axis_fontsize,
            color="0.25",
        )

        ax.set_ylabel(
            ylabel,
            fontsize=self.axis_fontsize,
            color="0.25",
        )

        ax.set_xlim(datetime(2000, 1, 1), datetime(2000, 12, 31))
        ax.xaxis.set_major_locator(self.month_locator)
        ax.xaxis.set_major_formatter(self.month_formatter)
        ax.grid(
            True,
            linestyle="--",
            linewidth=0.7,
            color="0.6",
            alpha=0.3,
        )

        # Colorbar für Jahre
        self._create_colorbar(fig, ax,)

        filepath = (
            self.output_dir
            / f"{region.replace(' ','_')}_{suffix}.png"
        )

        filepath.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fig.savefig(
            filepath,
            dpi=300,
        )

        plt.close(fig)

        logger.info(
            "Saved %s",
            filepath.name,
        )


    def plot_polar(self):
        """Create polar plots for every region."""

        if self.df is None:
            self.load()

        for region in self.df.region.unique():

            self._plot_polar_region(
                region,
                "relative_coverage_percent",
                "Relative ice coverage (%)",
                "relative",
            )

            self._plot_polar_region(
                region,
                "absolute_coverage_percent",
                "Absolute ice coverage (%)",
                "absolute",
            )

    def _plot_polar_region(self, region, column, ylabel, suffix):
        """Plot one quantity for one analysis region."""

        df_region = self.df[self.df.region == region].copy()

        df_region["theta"] = (2*np.pi * (df_region.day_of_year-1) / 365 + self.theta_offset) % (2*np.pi)

        fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=self.polar_figure_size)

        ax.spines["polar"].set_color("0.4")
        ax.spines["polar"].set_linewidth(0.8)

        for i, year in enumerate(self.unique_years):
            df_year = df_region[df_region["year"] == year].sort_values("theta")
            ax.plot(
                df_year["theta"],
                df_year[column],
                color=self.cmap(self.norm(year)),
                linewidth=1.3,
                alpha=0.85
            )

        ax.scatter(
            df_year["theta"].iloc[-1],
            df_year[column].iloc[-1],
            s=45,
            color="red",
            edgecolor="black",
            linewidth=0.8,
            zorder=10,
        )

        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)

        month_angles = np.deg2rad(np.arange(0, 360, 30))
        month_labels = ["Dec", "Jan", "Feb", "Mar", "Apr", "May",
                        "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]

        ax.set_xticks(month_angles)
        ax.set_xticklabels(month_labels, fontsize=self.tick_fontsize)
        ax.tick_params(
            labelsize=self.tick_fontsize,
            colors="0.3",
        )

        #ax.set_title(f"{label} – {region}", fontsize=11, pad=30)
        ax.set_rlabel_position(270)
        ax.grid(
            True,
            linestyle="--",
            linewidth=0.7,
            color="0.6",
            alpha=0.3,
        )
        ax.set_ylabel("")

        self._create_colorbar(
            fig,
            ax,
            pad=self.polar_colorbar_pad,
            fraction=self.polar_colorbar_fraction,
        )

        fig.subplots_adjust(
            left=self.polar_left,
            right=self.polar_right,
            bottom=self.polar_bottom,
            top=self.polar_top,
        )

        filepath = (
            self.output_dir
            / f"{region.replace(' ','_')}_polar_{suffix}.png"
        )

        filepath.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fig.savefig(
            filepath,
            dpi=300,
        )

        plt.close(fig)

        logger.info(
            "Saved %s",
            filepath.name,
        )

    def plot_all(self):
        """Create all available time-series plots."""

        if self.df is None:
            self.load()

        self.plot_timeseries()

        self.plot_polar()

    def _plot_decadal_mean(self):
        pass

    def _plot_climatology(self):
        pass