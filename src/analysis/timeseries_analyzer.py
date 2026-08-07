"""
Post-process historical regional sea-ice time series.

The analyzer enriches the daily statistics stored in
ice_coverage_summary.csv with derived quantities such as

- continuous daily calendar
- interpolated gaps
- moving averages
- climatological mean
- anomalies

Additional products (freeze-up, break-up, trends, etc.)
can be added without changing the processing pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from src.config.paths import PROJECT_ROOT

DEFAULT_RESULTS = (
    PROJECT_ROOT
    / "output"
    / "analysis"
    / "ice_coverage_summary.csv"
)

DEFAULT_TIMESERIES = ( 
    PROJECT_ROOT 
    / "output" 
    / "analysis" 
    / "ice_coverage_timeseries.csv" 
)

class TimeSeriesAnalyzer:

    def __init__(
        self,
        csv_path: str | Path = DEFAULT_RESULTS,
        output_path: str | Path = DEFAULT_TIMESERIES,
    ):

        self.csv_path = Path(csv_path)
        self.output_path = Path(output_path)

        self.df = pd.DataFrame()

    # ---------------------------------------------------------
    # public API
    # ---------------------------------------------------------

    def analyze(self) -> pd.DataFrame:

        self.load()

        self.interpolate_calendar()

        self.calculate_moving_average(window=3)

        self.calculate_climatology(
            start_year=1981,
            end_year=2010,
        )

        self.calculate_anomalies()

        return self.df

    # ---------------------------------------------------------
    # loading
    # ---------------------------------------------------------

    def load(self):

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

    # ---------------------------------------------------------
    # interpolation
    # ---------------------------------------------------------

    def interpolate_calendar(self):

        logger.info(
            "Interpolating missing calendar days."
        )

        groups = []

        for region, df_region in self.df.groupby("region"):

            df_region = (
                df_region
                .set_index("date")
                .sort_index()
            )

            full_index = pd.date_range(
                df_region.index.min(),
                df_region.index.max(),
                freq="D",
            )

            df_region = df_region.reindex(full_index)

            df_region["region"] = region

            numeric = df_region.select_dtypes(
                include="number"
            ).columns

            df_region[numeric] = (
                df_region[numeric]
                .interpolate(
                    method="time",
                    limit_direction="both",
                )
            )

            df_region.index.name = "date"

            groups.append(
                df_region.reset_index()
            )

        self.df = pd.concat(
            groups,
            ignore_index=True,
        )

    # ---------------------------------------------------------
    # moving average
    # ---------------------------------------------------------

    def calculate_moving_average(
        self,
        window: int = 3,
    ):

        logger.info(
            "Calculating ±%d day moving averages.",
            window,
        )

        columns = [
            "relative_coverage_percent",
            "absolute_coverage_percent",
            "relative_ice_area_km2",
            "absolute_ice_area_km2",
        ]

        for column in columns:

            new_column = f"{column}_ma"

            self.df[new_column] = (
                self.df
                .groupby("region")[column]
                .transform(
                    lambda s:
                    s.rolling(
                        window=2 * window + 1,
                        center=True,
                        min_periods=1,
                    ).mean()
                )
            )

    # ---------------------------------------------------------
    # climatology
    # ---------------------------------------------------------

    def calculate_climatology(
        self,
        start_year: int,
        end_year: int,
    ):

        logger.info(
            "Calculating %d-%d climatology.",
            start_year,
            end_year,
        )

        climatology = self.df[
            (
                self.df["date"].dt.year >= start_year
            )
            &
            (
                self.df["date"].dt.year <= end_year
            )
        ].copy()

        climatology["dayofyear"] = (
            climatology["date"]
            .dt.dayofyear
        )

        mean = (

            climatology

            .groupby(
                [
                    "region",
                    "dayofyear",
                ]
            )[
                "relative_coverage_percent"
            ]

            .mean()

            .rename("climatology")

            .reset_index()

        )

        self.df["dayofyear"] = (
            self.df["date"]
            .dt.dayofyear
        )

        self.df = self.df.merge(
            mean,
            how="left",
            on=[
                "region",
                "dayofyear",
            ],
        )

    # ---------------------------------------------------------
    # anomalies
    # ---------------------------------------------------------

    def calculate_anomalies(self):

        logger.info(
            "Calculating anomalies."
        )

        self.df["anomaly"] = (

            self.df["relative_coverage_percent"]

            -

            self.df["climatology"]

        )

    # ---------------------------------------------------------
    # saving
    # ---------------------------------------------------------

    def save(self) -> Path: 
        """ 
        Save the derived time-series dataset. The original 
        ice_coverage_summary.csv is never modified. 
        """ 

        self.output_path.parent.mkdir( 
            parents=True, 
            exist_ok=True, 
        ) 

        self.df.to_csv( 
            self.output_path, 
            index=False, 
        ) 

        logger.info( 
            "Saved derived time series to %s", 
            self.output_path, 
        ) 

        return self.output_path