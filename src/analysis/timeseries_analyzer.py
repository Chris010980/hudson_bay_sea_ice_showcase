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

from curses import window
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

DEFAULT_YEARLY = ( 
    PROJECT_ROOT 
    / "output" 
    / "analysis" 
    / "ice_coverage_yearly.csv" 
)

class TimeSeriesAnalyzer:

    def __init__(
        self,
        csv_path: str | Path = DEFAULT_RESULTS,
        output_path: str | Path = DEFAULT_TIMESERIES,
        yearly_output_path: str | Path = DEFAULT_YEARLY,
    ):

        self.csv_path = Path(csv_path)
        self.output_path = Path(output_path)
        self.yearly_output_path = Path(yearly_output_path)

        self.df = pd.DataFrame()
        self.yearly_df = pd.DataFrame()

    # ---------------------------------------------------------
    # public API
    # ---------------------------------------------------------

    def analyze(self) -> tuple[pd.DataFrame, pd.DataFrame]:

        self.load()

        self.interpolate_calendar()

        self.calculate_moving_average(
            window=3,
        )

        self.calculate_climatology(
            start_year=1981,
            end_year=2010,
        )

        self.calculate_yearly_means()

        self.calculate_anomalies()

        return (
            self.df,
            self.yearly_df,
        )

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
                    limit=14,
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

    def filter_complete_years(self) -> pd.DataFrame:
        """
        Return only complete region-years.

        The original self.df is not modified.
        """

        logger.info(
            "Filtering incomplete years."
        )

        if self.df.empty:
            logger.warning(
                "Cannot filter incomplete years: dataframe is empty."
            )
            return self.df.iloc[0:0].copy()

        df = self.df.copy()

        df["year"] = df["date"].dt.year

        complete_groups = []

        for (region, year), group in df.groupby(
            ["region", "year"]
        ):

            expected_days = (
                366
                if pd.Timestamp(year=year, month=12, day=31).dayofyear == 366
                else 365
            )

            valid_days = (
                group["relative_coverage_percent"]
                .notna()
                .sum()
            )

            if valid_days == expected_days:

                complete_groups.append(
                    (region, year)
                )

            else:

                logger.debug(
                    "Incomplete year: %s / %d "
                    "(%d/%d valid days).",
                    region,
                    year,
                    valid_days,
                    expected_days,
                )

        if not complete_groups:

            logger.warning(
                "No complete region-years found."
            )

            return df.iloc[0:0].drop(
                columns="year"
            )

        complete_years = pd.DataFrame(
            complete_groups,
            columns=[
                "region",
                "year",
            ],
        )

        all_years = (
            df[
                [
                    "region",
                    "year",
                ]
            ]
            .drop_duplicates()
        )

        logger.info(
            "Found %d complete region-years "
            "out of %d region-years.",
            len(complete_years),
            len(all_years),
        )

        return (
            df
            .merge(
                complete_years,
                on=[
                    "region",
                    "year",
                ],
                how="inner",
            )
            .drop(columns="year")
            .sort_values(
                [
                    "region",
                    "date",
                ]
            )
            .reset_index(drop=True)
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

        window_size = 2 * window + 1 

        for column in columns: 
            new_column = f"{column}_ma" 
            self.df[new_column] = np.nan 

            for region, indices in self.df.groupby( "region" ).groups.items(): 
                region_df = self.df.loc[indices].sort_values( "date" ) 
                values = region_df[column] 
                valid = values.notna() 

                # Identify contiguous valid sections. 
                group = ( valid .ne(valid.shift()) .cumsum() ) 

                for _, segment in region_df[ valid ].groupby(group[valid]): 
                    if segment.empty: 
                        continue 

                    ma = ( segment[column] .rolling( window=window_size, center=True, min_periods=1, ) .mean() ) 

                    self.df.loc[ segment.index, new_column, ] = ma.values

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
            self.df["date"]
            .dt.year.between( start_year, end_year, ) 
            ].copy()

    # Month/day is used instead of dayofyear so that leap 
    # years do not shift all dates after February. 
     
        climatology["month_day"] = ( 
            climatology["date"].dt.strftime("%m-%d") 
        ) 

        climatology_mean = ( 
            climatology.groupby( [ "region", "month_day", ] )[ [ "relative_coverage_percent", "absolute_coverage_percent", ] ]
            .mean()
            .rename( 
                columns={ 
                    "relative_coverage_percent": "relative_climatology_percent", 
                    "absolute_coverage_percent": "absolute_climatology_percent", 
                } 
            ) 
            .reset_index() 
        ) 

        self.df["month_day"] = ( 
            self.df["date"].dt.strftime("%m-%d") 
        ) 

        self.df = self.df.merge( 
            climatology_mean, how="left", on=[ "region", "month_day", ], 
        )

    # ---------------------------------------------------------
    # anomalies
    # ---------------------------------------------------------

    def calculate_anomalies(self):

        logger.info( "Calculating relative and absolute anomalies." ) 

        self.df["relative_anomaly_percent"] = ( 
            self.df["relative_coverage_percent"] 
            - self.df["relative_climatology_percent"] 
        ) 

        self.df["absolute_anomaly_percent"] = ( 
            self.df["absolute_coverage_percent"] 
            - self.df["absolute_climatology_percent"] 
        )

    # ========================================================= 
    # yearly means 
    # ========================================================= 
    def calculate_yearly_means(self):
        """Calculate annual means using complete region-years only."""

        logger.info(
            "Calculating yearly mean sea-ice coverage."
        )

        if self.df.empty:
            logger.warning(
                "Cannot calculate yearly means: input dataframe is empty."
            )
            self.yearly_df = pd.DataFrame()
            return

        complete_df = self.filter_complete_years()

        if complete_df.empty:
            logger.warning(
                "No complete region-years available for yearly means."
            )
            self.yearly_df = pd.DataFrame()
            return

        df = complete_df.copy()

        df["year"] = df["date"].dt.year

        columns = [
            "relative_coverage_percent",
            "absolute_coverage_percent",
            "relative_ice_area_km2",
            "absolute_ice_area_km2",
        ]

        missing = [
            column
            for column in columns
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                "Missing columns required for yearly means: "
                + ", ".join(missing)
            )

        yearly = (
            df
            .groupby(
                [
                    "region",
                    "year",
                ],
                as_index=False,
            )[columns]
            .mean()
        )

        yearly.rename(
            columns={
                "relative_coverage_percent":
                    "relative_mean_coverage_percent",

                "absolute_coverage_percent":
                    "absolute_mean_coverage_percent",

                "relative_ice_area_km2":
                    "relative_mean_ice_area_km2",

                "absolute_ice_area_km2":
                    "absolute_mean_ice_area_km2",
            },
            inplace=True,
        )

        self.yearly_df = (
            yearly
            .sort_values(
                [
                    "region",
                    "year",
                ]
            )
            .reset_index(drop=True)
        )

        logger.info(
            "Calculated %d yearly mean records.",
            len(self.yearly_df),
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

        self.yearly_output_path.parent.mkdir( 
            parents=True, 
            exist_ok=True, 
        )

        self.df.to_csv( 
            self.output_path, 
            index=False, 
        ) 

        self.yearly_df.to_csv( 
            self.yearly_output_path, 
            index=False, 
        )

        logger.info( 
            "Saved derived time series to %s", 
            self.output_path, 
        ) 

        logger.info( 
            "Saved yearly means to %s", 
            self.yearly_output_path, 
        )

        return ( self.output_path, self.yearly_output_path, )