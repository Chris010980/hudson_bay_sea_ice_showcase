"""
Analyse historical regional sea-ice time series.

This class operates on the complete
ice_coverage_summary.csv produced by the processing pipeline
and derives additional products such as interpolated calendars,
moving averages, climatologies and long-term statistics.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.config.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)


DEFAULT_RESULTS = (
    PROJECT_ROOT
    / "output"
    / "analysis"
    / "ice_coverage_summary.csv"
)


class TimeSeriesAnalyzer:
    """
    Analyse historical sea-ice time series.

    Notes
    -----
    The original CSV remains untouched.
    Every derived product is calculated from the historical
    observations and can be exported separately.
    """

    def __init__(
        self,
        csv_path: str | Path = DEFAULT_RESULTS,
    ):

        self.csv_path = Path(csv_path)

        self.df = pd.DataFrame()

        self.interpolated = pd.DataFrame()

    # ---------------------------------------------------------
    # public API
    # ---------------------------------------------------------

    def load(self) -> pd.DataFrame:
        """
        Load the historical CSV.
        """

        logger.info(
            "Loading %s",
            self.csv_path,
        )

        self.df = pd.read_csv(
            self.csv_path,
            parse_dates=["date"],
        )

        self.df.sort_values(
            [
                "region",
                "date",
            ],
            inplace=True,
        )

        return self.df

    def interpolate_calendar(
        self,
        max_gap_days: int = 14,
    ) -> pd.DataFrame:
        """
        Fill missing calendar days by linear interpolation.

        Only gaps up to max_gap_days are interpolated.

        Larger gaps remain missing and therefore produce
        visible breaks in later plots.
        """

        if self.df.empty:
            self.load()

        regions = []

        for region, group in self.df.groupby("region"):

            group = (
                group
                .set_index("date")
                .sort_index()
            )

            full = (
                group
                .asfreq("D")
            )

            full["region"] = region

            numeric = full.select_dtypes("number").columns

            full[numeric] = full[numeric].interpolate(
                method="time",
                limit=max_gap_days,
                limit_area="inside",
            )

            regions.append(full.reset_index())

        self.interpolated = pd.concat(
            regions,
            ignore_index=True,
        )

        logger.info(
            "Interpolated calendar created."
        )

        return self.interpolated

    def moving_average(
        self,
        column: str,
        window_days: int = 3,
    ) -> pd.DataFrame:
        """
        Calculate centred moving average.

        Parameters
        ----------
        column
            Column to smooth.

        window_days
            Number of days to either side.

            1 -> 3-day average

            2 -> 5-day average

            3 -> 7-day average
        """

        if self.interpolated.empty:
            self.interpolate_calendar()

        df = self.interpolated.copy()

        window = 2 * window_days + 1

        smoothed = []

        for _, group in df.groupby("region"):

            group = group.sort_values("date")

            group[f"{column}_smooth"] = (
                group[column]
                .rolling(
                    window=window,
                    center=True,
                    min_periods=1,
                )
                .mean()
            )

            smoothed.append(group)

        return pd.concat(
            smoothed,
            ignore_index=True,
        )

    def climatology(
        self,
        column: str,
        start_year: int = 1981,
        end_year: int = 2010,
    ) -> pd.DataFrame:
        """
        Compute daily climatology.

        Returns one mean value for every day-of-year.
        """

        if self.interpolated.empty:
            self.interpolate_calendar()

        df = self.interpolated.copy()

        years = (
            df.date.dt.year >= start_year
        ) & (
            df.date.dt.year <= end_year
        )

        df = df[years]

        df["dayofyear"] = (
            df.date.dt.dayofyear
        )

        climatology = (
            df.groupby(
                [
                    "region",
                    "dayofyear",
                ]
            )[column]
            .mean()
            .reset_index()
        )

        return climatology

    def available_regions(self):

        if self.df.empty:
            self.load()

        return sorted(
            self.df.region.unique()
        )

    def available_years(self):

        if self.df.empty:
            self.load()

        return sorted(
            self.df.date.dt.year.unique()
        )