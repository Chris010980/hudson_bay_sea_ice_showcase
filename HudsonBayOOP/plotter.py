# plotter.py

import os
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.dates import DateFormatter, MonthLocator
import matplotlib as mpl

mpl.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 200,

    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,

    "xtick.labelsize": 9,
    "ytick.labelsize": 9,

    "legend.fontsize": 9,
    "legend.frameon": False,

    "lines.linewidth": 1.3,
    "grid.alpha": 0.4,

    "savefig.bbox": "tight",
})

class Plotter:
    def __init__(self, data):
        if isinstance(data, str):
            self.df = pd.read_csv(data, parse_dates=["date"])
        elif isinstance(data, pd.DataFrame):
            self.df = data.copy()
        else:
            raise ValueError("Plotter erwartet Dateipfad (str) oder DataFrame!")

        self.show_decadal_mean = False  # später leicht aktivierbar

        # Immer sicherstellen:
        self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
        if self.df["date"].isna().any():
            print("[WARNUNG] Einige Datumswerte konnten nicht geparst werden!")

        self.df["Jahr"] = self.df["date"].dt.year
        self.df["Tag_im_Jahr"] = self.df["date"].dt.dayofyear
        self.df["Monat"] = self.df["date"].dt.month
        self.df["Tag"] = self.df["date"].dt.day

        # Dummy-Jahr für Plot-X-Achse
        self.df["PlotDatum"] = self.df["date"].apply(
            lambda d: datetime(2000, d.month, d.day)
        )

        self.unique_years = sorted(self.df["Jahr"].unique())
        self.norm = mcolors.Normalize(vmin=min(self.unique_years), vmax=max(self.unique_years))
        self.cmap = cm.get_cmap("plasma", len(self.unique_years))

        # 10-Jahres-Zeitfenster
        start_year = min(self.unique_years)
        end_year = max(self.unique_years)
        self.intervals = []
        for y in range(start_year, end_year + 1, 10):
            interval_start = y
            interval_end = min(y + 9, end_year)
            self.intervals.append((interval_start, interval_end))

        # X-Achse Formatierung
        self.month_locator = MonthLocator()
        self.month_formatter = DateFormatter("%b")

    def plot_timeseries_by_region(self, output_dir="results/plots_by_region"):
        os.makedirs(output_dir, exist_ok=True)
        regions = self.df["region"].unique()

        for region in regions:
            df_region = self.df[self.df["region"] == region]

            for col, label, suffix in [
                ("relative_coverage_percent_of_water", "relative ice coverage (%)", "relative"),
                ("absolute_coverage_percent_of_water", "absolute ice coverage (%)", "absolute")
            ]:
                fig, ax = plt.subplots(figsize=(9, 5))

                # Einzeljahre
                for year in self.unique_years:
                    df_year = df_region[df_region["Jahr"] == year].sort_values("PlotDatum")
                    ax.plot(
                        df_year["PlotDatum"],
                        df_year[col],
                        color=self.cmap(self.norm(year)),
                        linewidth=1.0,
                        alpha=0.9
                    )

                # 10-Jahres-Mittel
                for interval_start, interval_end in self.intervals:
                    df_interval = df_region[
                        (df_region["Jahr"] >= interval_start) &
                        (df_region["Jahr"] <= interval_end)
                    ]
                    if df_interval.empty:
                        continue

                    mean_curve = (
                        df_interval.groupby("Tag_im_Jahr")[col]
                        .mean()
                        .reset_index()
                    )
                    mean_curve["PlotDatum"] = mean_curve["Tag_im_Jahr"].apply(
                        lambda d: datetime(2000, 1, 1) + pd.to_timedelta(d - 1, unit="D")
                    )

                    if self.show_decadal_mean:
                        ax.plot(
                            mean_curve["PlotDatum"],
                            mean_curve[col],
                            color="black",
                            linewidth=2.0,
                            alpha=0.4
                        )

                #ax.set_title(f"{label} – {region}", fontsize=11)
                ax.set_ylabel(label)
                ax.set_xlabel("Month")
                ax.set_xlim(datetime(2000, 1, 1), datetime(2000, 12, 31))
                ax.xaxis.set_major_locator(self.month_locator)
                ax.xaxis.set_major_formatter(self.month_formatter)
                ax.grid(True)

                # Colorbar für Jahre
                sm = plt.cm.ScalarMappable(cmap=self.cmap, norm=self.norm)
                sm.set_array([])

                cbar = plt.colorbar(
                    sm,
                    ax=ax,
                    pad=0.02,
                    fraction=0.04
                )
                cbar.set_label("Year", fontsize=8)
                cbar.ax.tick_params(labelsize=7)

                filename = f"{region.replace(' ', '_')}_{suffix}.png"
                filepath = os.path.join(output_dir, filename)
                plt.tight_layout()
                plt.savefig(filepath)
                plt.close()

        print(f"✅ Zeitreihen gespeichert in '{output_dir}/'.")

    def plot_polar_by_region(self, output_dir="results/polarplots_by_region"):
        os.makedirs(output_dir, exist_ok=True)
        df = self.df.copy()
        theta_offset = np.deg2rad(15)
        df["theta"] = (2 * np.pi * (df["Tag_im_Jahr"] - 1) / 365.0 + theta_offset) % (2 * np.pi)

        base_cmap = plt.colormaps.get_cmap("plasma")
        colors = [base_cmap(i / (len(self.unique_years) )) for i in range(len(self.unique_years))]

        regions = df["region"].unique()
        for region in regions:
            df_region = df[df["region"] == region]

            for col, label, suffix in [
                ("relative_coverage_percent_of_water", "relative ice coverage (%)", "relative"),
                ("absolute_coverage_percent_of_water", "absolute ice coverage (%)", "absolute")
            ]:
                fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(7, 5))

                for i, year in enumerate(self.unique_years):
                    df_year = df_region[df_region["Jahr"] == year].sort_values("theta")
                    ax.plot(
                        df_year["theta"],
                        df_year[col],
                        color=self.cmap(self.norm(year)),
                        linewidth=1.1,
                        alpha=0.85
                    )

                ax.set_theta_zero_location("N")
                ax.set_theta_direction(-1)

                month_angles = np.deg2rad(np.arange(0, 360, 30))
                month_labels = ["Dez", "Jan", "Feb", "Mär", "Apr", "Mai",
                                "Jun", "Jul", "Aug", "Sep", "Okt", "Nov"]

                ax.set_xticks(month_angles)
                ax.set_xticklabels(month_labels, fontsize=7)
                ax.tick_params(labelsize=7)

                #ax.set_title(f"{label} – {region}", fontsize=11, pad=30)
                ax.set_rlabel_position(270)
                ax.grid(True)
                ax.set_ylabel("")

                sm = plt.cm.ScalarMappable(cmap=self.cmap, norm=self.norm)
                sm.set_array([])

                cbar = fig.colorbar(
                    sm,
                    ax=ax,
                    orientation="vertical",
                    pad=0.1,
                    fraction=0.05
                )
                cbar.set_label("Year", fontsize=8)
                cbar.ax.tick_params(labelsize=7)

                filename = f"{region.replace(' ', '_')}_polar_{suffix}.png"
                filepath = os.path.join(output_dir, filename)
                fig.savefig(filepath, bbox_inches="tight")
                plt.close()

        print(f"✅ Polarplots gespeichert in '{output_dir}/'.")
