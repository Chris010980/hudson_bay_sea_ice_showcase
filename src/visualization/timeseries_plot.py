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

RESULTS_CSV = PROJECT_ROOT / "output" / "analysis" / "ice_coverage_timeseries.csv"
OUTPUT_DIR = PROJECT_ROOT / "output" / "plots"
YEARLY_CSV = PROJECT_ROOT / "output" / "analysis" / "ice_coverage_yearly.csv" 

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
        yearly_csv_file: str | Path = YEARLY_CSV,
    ):

        self.csv_file = Path(csv_file)
        self.yearly_csv_file = Path(yearly_csv_file)

        self.df = None
        self.yearly_df = None

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

        # ------------------------------------------------------------- 
        # Climatology 
        # ------------------------------------------------------------- 
        self.climatology_color = "0.25" 
        self.climatology_linewidth = 2.2 
        self.climatology_alpha = 0.95 

        # ------------------------------------------------------------- 
        # Current observation 
        # ------------------------------------------------------------- 
        self.current_marker_size = 45

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

        self.yearly_df = pd.read_csv(
            self.yearly_csv_file,
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

    # ================================================================
    #  Gap handling 
    # ================================================================ 
    def _prepare_year( self, df_year: pd.DataFrame, ) -> pd.DataFrame: 
        """ 
        Prepare one year's data for plotting. NaN values are 
        deliberately retained. Matplotlib does not draw line segments 
        across NaN values, which provides the desired behaviour for 
        data gaps that were not interpolated by the TimeSeriesAnalyzer. 
        """ 
        return ( df_year .sort_values("date") .copy() )


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
                "relative_coverage_percent_ma",
                "Relative ice coverage (%)",
                "relative",
            )

            self._plot_region(
                region,
                "absolute_coverage_percent_ma",
                "Absolute ice coverage (%)",
                "absolute",
            )

    def _plot_region(
        self,
        region,
        column,
        ylabel,
        suffix,
    ):
        """Plot one quantity for one analysis region."""

        df_region = (
            self.df[self.df.region == region]
            .sort_values("date")
            .copy()
        )

        if df_region.empty:
            logger.warning(
                "No data available for region %s.",
                region,
            )
            return

        # ---------------------------------------------------------
        # Select matching climatology
        # ---------------------------------------------------------

        climatology_column = {
            "relative": "relative_climatology_percent",
            "absolute": "absolute_climatology_percent",
        }.get(suffix)

        if climatology_column is None:
            logger.warning(
                "No climatology defined for suffix '%s'.",
                suffix,
            )
            return

        # ---------------------------------------------------------
        # Figure
        # ---------------------------------------------------------

        fig, ax = plt.subplots(
            figsize=self.figure_size,
        )

        for spine in ax.spines.values():
            spine.set_color("0.4")
            spine.set_linewidth(0.8)

        # ---------------------------------------------------------
        # Individual years
        # ---------------------------------------------------------

        for year in self.unique_years:

            df_year = (
                df_region[
                    df_region["year"] == year
                ]
                .sort_values("date")
                .copy()
            )

            if df_year.empty:
                continue

            df_year = self._prepare_year(df_year)

            ax.plot(
                df_year["plot_date"],
                df_year[column],
                color=self.cmap(self.norm(year)),
                linewidth=1.3,
                alpha=0.85,
            )

        # ---------------------------------------------------------
        # 1981–2010 climatology
        # ---------------------------------------------------------

        climatology = (
            df_region[
                [
                    "plot_date",
                    climatology_column,
                ]
            ]
            .dropna(
                subset=[climatology_column]
            )
            .sort_values("plot_date")
        )

        if not climatology.empty:

            ax.plot(
                climatology["plot_date"],
                climatology[climatology_column],
                color=self.climatology_color,
                linewidth=self.climatology_linewidth,
                alpha=self.climatology_alpha,
                zorder=8,
                label="1981–2010 climatology",
            )

        # ---------------------------------------------------------
        # Current observation
        # ---------------------------------------------------------

        current = (
            df_region
            .dropna(subset=[column])
            .sort_values("date")
        )

        if not current.empty:

            latest = current.iloc[-1]

            ax.scatter(
                latest["plot_date"],
                latest[column],
                s=self.current_marker_size,
                color="red",
                edgecolor="black",
                linewidth=0.8,
                zorder=10,
            )

        # ---------------------------------------------------------
        # Axes
        # ---------------------------------------------------------

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

        ax.set_xlim(
            datetime(2000, 1, 1),
            datetime(2000, 12, 31),
        )

        ax.xaxis.set_major_locator(
            self.month_locator
        )

        ax.xaxis.set_major_formatter(
            self.month_formatter
        )

        ax.grid(
            True,
            linestyle="--",
            linewidth=0.7,
            color="0.6",
            alpha=0.3,
        )

        # ---------------------------------------------------------
        # Climatology legend
        # ---------------------------------------------------------

        if not climatology.empty:

            ax.legend(
                loc="upper right",
                frameon=False,
                fontsize=self.legend_fontsize,
            )

        # ---------------------------------------------------------
        # Year colorbar
        # ---------------------------------------------------------

        self._create_colorbar(
            fig,
            ax,
        )

        # ---------------------------------------------------------
        # Save
        # ---------------------------------------------------------

        filepath = (
            self.output_dir
            / f"{region.replace(' ', '_')}_{suffix}.png"
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
            filepath,
        )


    def plot_polar(self):
        """Create polar plots for every region."""

        if self.df is None:
            self.load()

        for region in self.df.region.unique():

            self._plot_polar_region(
                region,
                "relative_coverage_percent_ma",
                "Relative ice coverage (%)",
                "relative",
            )

            self._plot_polar_region(
                region,
                "absolute_coverage_percent_ma",
                "Absolute ice coverage (%)",
                "absolute",
            )

    def _prepare_polar_year(
        self,
        df_year: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Prepare one year for polar plotting.

        Data are kept in chronological order. The cyclic connection
        between December and January is only allowed for complete years.
        """

        df_year = (
            df_year
            .sort_values("date")
            .copy()
        )

        if df_year.empty:
            return df_year

        dates = df_year["date"].dt.normalize()

        expected_days = (
            366
            if dates.iloc[0].is_leap_year
            else 365
        )

        is_complete = (
            dates.nunique() >= expected_days
            and dates.min().month == 1
            and dates.min().day == 1
            and dates.max().month == 12
            and dates.max().day == 31
        )

        if not is_complete:
            return df_year

        # Explicitly add the first day once more at the end
        # so that the polar curve closes at the year boundary.
        first = df_year.iloc[[0]].copy()

        first["theta"] = (
            2 * np.pi
            + first["theta"]
        )

        return pd.concat(
            [df_year, first],
            ignore_index=True,
        )

    def _plot_polar_region(self, region, column, ylabel, suffix):
        """Plot one quantity for one analysis region."""

        if self.df is None: 
            return 

        if column not in self.df.columns: 
            logger.warning( "Column %s not found. Skipping %s.", column, region, ) 
            return

        df_region = self.df[self.df.region == region].copy()

        df_region["theta"] = (2*np.pi * (df_region.day_of_year-1) / 365 + self.theta_offset) % (2*np.pi)

        fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=self.polar_figure_size)

        ax.spines["polar"].set_color("0.4")
        ax.spines["polar"].set_linewidth(0.8)

        for year in self.unique_years:

            df_year = df_region[
                df_region["year"] == year
            ].copy()

            if df_year.empty:
                continue

            df_year = self._prepare_polar_year(df_year)

            ax.plot(
                df_year["theta"],
                df_year[column],
                color=self.cmap(self.norm(year)),
                linewidth=1.3,
                alpha=0.85,
            )

        # ---------------------------------------------------------
        # Climatology
        # ---------------------------------------------------------

        climatology_column = {
            "relative": "relative_climatology_percent",
            "absolute": "absolute_climatology_percent",
        }.get(suffix)

        climatology = pd.DataFrame()

        if climatology_column is not None:

            climatology = (
                df_region[
                    [
                        "theta",
                        climatology_column,
                        "day_of_year",
                    ]
                ]
                .dropna(
                    subset=[climatology_column]
                )
                .sort_values("day_of_year")
            )

        if not climatology.empty:

            ax.plot(
                climatology["theta"],
                climatology[climatology_column],
                color=self.climatology_color,
                linewidth=self.climatology_linewidth,
                alpha=self.climatology_alpha,
                zorder=8,
                label="1981–2010 climatology",
            )

        # ------------------------------------------------------------- 
        # Current observation 
        # ------------------------------------------------------------- 
        current = (
            df_region
            .dropna(subset=["date", column])
            .sort_values("date")
        )

        if not current.empty:

            latest = current.iloc[-1]

            ax.scatter(
                latest["plot_date"],
                latest[column],
                s=self.current_marker_size,
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

        # ------------------------------------------------------------- 
        # Climatology legend 
        # ------------------------------------------------------------- 
        if not climatology.empty: 
            ax.legend( 
                loc="upper right", 
                bbox_to_anchor=(1.15, 1.10), 
                frameon=False, 
                fontsize=self.legend_fontsize, 
            )

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

    def plot_yearly_means(self):
        """Plot annual mean relative sea-ice coverage with linear trend."""

        if self.yearly_df is None: 
            self.load() 
            
        df = self.yearly_df.copy()

        required_columns = {
            "year",
            "region",
            "relative_mean_coverage_percent",
        }

        missing = required_columns - set(df.columns)

        if missing:

            logger.error(
                "Yearly mean file is missing columns: %s",
                ", ".join(sorted(missing)),
            )

            return

        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce",
        )

        df["relative_mean_coverage_percent"] = pd.to_numeric(
            df["relative_mean_coverage_percent"],
            errors="coerce",
        )

        df.dropna(
            subset=[
                "year",
                "relative_mean_coverage_percent",
            ],
            inplace=True,
        )

        if df.empty:

            logger.warning(
                "Yearly mean file contains no valid data."
            )

            return

        for region in sorted(df["region"].unique()):

            df_region = (
                df[df["region"] == region]
                .sort_values("year")
                .copy()
            )

            if len(df_region) < 2:

                logger.warning(
                    "Not enough yearly data for trend in %s.",
                    region,
                )

                continue

            x = df_region["year"].to_numpy(
                dtype=float,
            )

            y = df_region[
                "relative_mean_coverage_percent"
            ].to_numpy(
                dtype=float,
            )

            # ---------------------------------------------------------
            # Linear trend
            # ---------------------------------------------------------

            slope, intercept = np.polyfit(
                x,
                y,
                1,
            )

            y_trend = (
                slope * x
                + intercept
            )

            # Coefficient of determination R²
            residuals = y - y_trend

            ss_res = np.sum(
                residuals ** 2
            )

            ss_tot = np.sum(
                (y - np.mean(y)) ** 2
            )

            if ss_tot > 0:

                r_squared = (
                    1.0
                    - ss_res / ss_tot
                )

            else:

                r_squared = np.nan

            # ---------------------------------------------------------
            # Figure
            # ---------------------------------------------------------

            fig, ax = plt.subplots(
                figsize=self.figure_size,
            )

            for spine in ax.spines.values():

                spine.set_color("0.4")
                spine.set_linewidth(0.8)

            # ---------------------------------------------------------
            # Annual means
            # ---------------------------------------------------------

            ax.plot(
                x,
                y,
                marker="o",
                markersize=3.5,
                linewidth=1.3,
                color=mpl.colormaps["plasma"](0.55),
                alpha=0.85,
                label="Annual mean",
            )

            # ---------------------------------------------------------
            # Trend line
            # ---------------------------------------------------------

            ax.plot(
                x,
                y_trend,
                linestyle="--",
                linewidth=1.8,
                color="0.2",
                alpha=0.9,
                label="Linear trend",
            )

            # ---------------------------------------------------------
            # Trend equation
            # ---------------------------------------------------------

            reference_year = 2000

            slope, intercept = np.polyfit(
                x,
                y,
                1,
            )

            reference_value = (
                slope * reference_year
                + intercept
            )

            if slope >= 0:

                equation = (
                    rf"$y = {slope:.3f}(x-{reference_year})"
                    rf" + {reference_value:.1f}$"
                )

            else:

                equation = (
                    rf"$y = {slope:.3f}(x-{reference_year})"
                    rf" + {reference_value:.1f}$"
                )

            if np.isfinite(r_squared):

                trend_text = (
                    f"{equation}\n"
                    rf"$R^2 = {r_squared:.3f}$"
                )

            else:

                trend_text = equation

            ax.text(
                0.02,
                0.97,
                trend_text,
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=self.legend_fontsize,
                color="0.25",
                bbox={
                    "boxstyle": "round,pad=0.35",
                    "facecolor": "white",
                    "edgecolor": "0.75",
                    "alpha": 0.85,
                },
            )

            # ---------------------------------------------------------
            # Axes
            # ---------------------------------------------------------

            ax.set_xlabel(
                "Year",
                fontsize=self.axis_fontsize,
                color="0.25",
            )

            ax.set_ylabel(
                "Mean relative ice coverage (%)",
                fontsize=self.axis_fontsize,
                color="0.25",
            )

            ax.set_title(
                f"Annual mean sea-ice coverage – {region}",
                fontsize=self.title_fontsize,
            )

            ax.grid(
                True,
                linestyle="--",
                linewidth=0.7,
                color="0.6",
                alpha=0.3,
            )

            # ---------------------------------------------------------
            # X axis
            # ---------------------------------------------------------

            x_min = x.min()
            x_max = x.max()

            margin = max(
                1.0,
                0.03 * (x_max - x_min),
            )

            ax.set_xlim(
                x_min - margin,
                x_max + margin,
            )

            # ---------------------------------------------------------
            # Legend
            # ---------------------------------------------------------

            ax.legend(
                loc="upper right",
                frameon=False,
                fontsize=self.legend_fontsize,
            )

            # ---------------------------------------------------------
            # Save
            # ---------------------------------------------------------

            filepath = (
                self.output_dir
                / f"{region.replace(' ', '_')}_yearly_mean_relative.png"
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
                filepath,
            )


    def plot_all(self):
        """Create all available time-series plots."""

        if self.df is None:
            self.load()

        self.plot_timeseries()

        self.plot_polar()

        self.plot_yearly_means()

    def _plot_decadal_mean(self):
        pass

    def _plot_climatology(self):
        pass