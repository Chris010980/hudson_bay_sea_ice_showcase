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

DEFAULT_EVENTS = (
    PROJECT_ROOT
    / "output"
    / "analysis"
    / "ice_coverage_events.csv"
)

class TimeSeriesAnalyzer:

    def __init__(
        self,
        csv_path: str | Path = DEFAULT_RESULTS,
        output_path: str | Path = DEFAULT_TIMESERIES,
        yearly_output_path: str | Path = DEFAULT_YEARLY,
        events_output_path: str | Path = DEFAULT_EVENTS,
    ):

        self.csv_path = Path(csv_path)
        self.output_path = Path(output_path)
        self.yearly_output_path = Path(yearly_output_path)
        self.events_output_path = Path(events_output_path)

        self.df = pd.DataFrame()
        self.yearly_df = pd.DataFrame()
        self.events_df = pd.DataFrame()

        self.threshold_persistence = 3

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

        self.calculate_anomalies()

        self.calculate_yearly_means()

        self.calculate_threshold_events()

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

        climatology_stats = (
            climatology
            .groupby(
                [
                    "region",
                    "month_day",
                ]
            )[
                [
                    "relative_coverage_percent",
                    "absolute_coverage_percent",
                ]
            ]
            .agg(
                [
                    "mean",
                    "std",
                    "min",
                    "max",
                ]
            )
        )

        climatology_stats.columns = [
            "relative_climatology_percent",
            "relative_climatology_std_percent",
            "relative_climatology_min_percent",
            "relative_climatology_max_percent",
            "absolute_climatology_percent",
            "absolute_climatology_std_percent",
            "absolute_climatology_min_percent",
            "absolute_climatology_max_percent",
        ]

        climatology_stats = (
            climatology_stats
            .reset_index()
        )

        self.df["month_day"] = ( 
            self.df["date"].dt.strftime("%m-%d") 
        ) 

        self.df = self.df.merge( 
            climatology_stats, how="left", on=[ "region", "month_day", ], 
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
    # Freeze-up and break-up events
    # ---------------------------------------------------------
    def _find_threshold_crossing(
        self,
        df: pd.DataFrame,
        column: str,
        threshold: float,
        direction: str,
        persistence: int,
    ) -> pd.Timestamp | None:
        """
        Find the first persistent threshold crossing.

        Parameters
        ----------
        df:
            Dataframe containing a daily time series.

        column:
            Column containing the sea-ice coverage values.

        threshold:
            Threshold in percent.

        direction:
            ``"down"`` for a downward crossing (break-up),
            ``"up"`` for an upward crossing (freeze-up).

        persistence:
            Number of consecutive calendar days for which the
            value must remain on the target side of the threshold.

        Returns
        -------
        pd.Timestamp | None
            Linearly interpolated threshold-crossing date, or
            ``None`` if no persistent crossing is found.
        """

        if df.empty:
            return None

        if persistence < 1:
            raise ValueError(
                "persistence must be at least 1."
            )

        if direction not in {"down", "up"}:
            raise ValueError(
                f"Unknown threshold direction: {direction}"
            )

        # ---------------------------------------------------------
        # Prepare data
        # ---------------------------------------------------------

        data = (
            df[
                [
                    "date",
                    column,
                ]
            ]
            .copy()
        )

        data["date"] = pd.to_datetime(
            data["date"],
            errors="coerce",
        )

        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

        data.dropna(
            subset=[
                "date",
                column,
            ],
            inplace=True,
        )

        data.sort_values(
            "date",
            inplace=True,
        )

        data.reset_index(
            drop=True,
            inplace=True,
        )

        if data.empty:
            return None

        # ---------------------------------------------------------
        # Determine which side of the threshold is required
        # ---------------------------------------------------------

        if direction == "down":
            condition = (
                data[column] <= threshold
            )

        else:
            condition = (
                data[column] >= threshold
            )

        # ---------------------------------------------------------
        # Find persistent sections
        # ---------------------------------------------------------

        # A new section starts whenever the threshold condition
        # changes from True to False or vice versa.
        groups = (
            condition
            .ne(condition.shift())
            .cumsum()
        )

        for _, segment in data[
            condition
        ].groupby(groups[condition]):

            if segment.empty:
                continue

            # -----------------------------------------------------
            # Check actual calendar-day continuity
            # -----------------------------------------------------

            if len(segment) < persistence:
                continue

            segment_dates = segment["date"]

            consecutive_days = (
                segment_dates
                .diff()
                .dropna()
                .eq(pd.Timedelta(days=1))
            )

            # For N observations we need N-1 consecutive
            # one-day intervals.
            if (
                len(segment) > 1
                and not consecutive_days.all()
            ):
                continue

            # -----------------------------------------------------
            # First persistent observation
            # -----------------------------------------------------

            first_idx = segment.index[0]

            # If the first observation of the window is already
            # beyond the threshold, no interpolation from an
            # earlier observation inside this window is possible.
            if first_idx == 0:
                return segment.iloc[0]["date"]

            previous = data.iloc[
                first_idx - 1
            ]

            current = data.iloc[
                first_idx
            ]

            # -----------------------------------------------------
            # Make sure the preceding observation is the previous
            # calendar day.
            # -----------------------------------------------------

            if (
                current["date"]
                - previous["date"]
                != pd.Timedelta(days=1)
            ):
                # There is a data gap. We deliberately do not
                # interpolate across it.
                return current["date"]

            y0 = previous[column]
            y1 = current[column]

            # -----------------------------------------------------
            # Already exactly on the threshold
            # -----------------------------------------------------

            if y0 == threshold:
                return previous["date"]

            if y1 == threshold:
                return current["date"]

            # -----------------------------------------------------
            # Linear interpolation
            # -----------------------------------------------------

            if y1 == y0:
                return current["date"]

            fraction = (
                threshold - y0
            ) / (
                y1 - y0
            )

            # Numerical safety: only interpolate if the threshold
            # actually lies between the two observations.
            if not 0.0 <= fraction <= 1.0:
                return current["date"]

            delta = (
                current["date"]
                - previous["date"]
            )

            crossing = (
                previous["date"]
                + fraction * delta
            )

            return crossing

        return None

    def _get_event_window(
        self,
        df_region: pd.DataFrame,
        event_year: int,
        event_type: str,
    ) -> pd.DataFrame:
        if event_type == "freeze-up":
            start = pd.Timestamp(
                year=event_year,
                month=9,
                day=16,
            )

            end = pd.Timestamp(
                year=event_year + 1,
                month=3,
                day=15,
            )

        elif event_type == "break-up":
            start = pd.Timestamp(
                year=event_year,
                month=3,
                day=16,
            )

            end = pd.Timestamp(
                year=event_year,
                month=9,
                day=15,
            )

        else:
            raise ValueError(
                f"Unknown event type: {event_type}"
            )

        return df_region[
            df_region["date"].between(
                start,
                end,
            )
        ].copy()    

    def calculate_threshold_events(
        self,
        column: str = "relative_coverage_percent_ma",
        persistence: int | None = None,
    ):
        """
        Determine seasonal break-up and freeze-up threshold dates.

        Break-up is evaluated from March 16 through September 15.
        Freeze-up is evaluated from September 16 through March 15
        of the following year.

        Thresholds:
            Break-up: 90 %, 50 %, 10 % (downward crossings)
            Freeze-up: 10 %, 50 %, 90 % (upward crossings)

        A threshold crossing is only accepted if the sea-ice
        coverage remains on the respective side of the threshold
        for at least ``persistence`` consecutive days.

        The crossing date is linearly interpolated between the two
        daily observations surrounding the threshold.

        Results are stored in ``self.events_df``.
        """

        if persistence is None:
            persistence = self.threshold_persistence

        if persistence < 1:
            raise ValueError(
                "persistence must be at least 1."
            )

        if self.df.empty:
            logger.warning(
                "Cannot calculate threshold events: "
                "dataframe is empty."
            )

            self.events_df = pd.DataFrame()

            return

        if column not in self.df.columns:
            raise ValueError(
                f"Column '{column}' not found in dataframe."
            )

        logger.info(
            "Calculating threshold events using '%s' "
            "with %d-day persistence.",
            column,
            persistence,
        )

        thresholds = {
            "break-up": {
                90: "down",
                50: "down",
                10: "down",
            },
            "freeze-up": {
                10: "up",
                50: "up",
                90: "up",
            },
        }

        records = []

        for region, df_region in self.df.groupby("region"):

            df_region = (
                df_region
                .sort_values("date")
                .reset_index(drop=True)
            )

            # ---------------------------------------------------------
            # Break-up
            # ---------------------------------------------------------

            break_up_years = (
                df_region["date"]
                .dt.year
                .dropna()
                .unique()
            )

            for year in break_up_years:

                window = self._get_event_window(
                    df_region,
                    int(year),
                    "break-up",
                )

                if window.empty:
                    continue

                for threshold, direction in thresholds["break-up"].items():

                    date = self._find_threshold_crossing(
                        window,
                        column=column,
                        threshold=threshold,
                        direction=direction,
                        persistence=persistence,
                    )

                    records.append(
                        {
                            "region": region,
                            "event_type": "break-up",
                            "year": int(year),
                            "threshold_percent": threshold,
                            "date": date,
                        }
                    )

            # ---------------------------------------------------------
            # Freeze-up
            # ---------------------------------------------------------

            freeze_up_years = (
                df_region["date"]
                .dt.year
                .dropna()
                .unique()
            )

            for year in freeze_up_years:

                window = self._get_event_window(
                    df_region,
                    int(year),
                    "freeze-up",
                )

                if window.empty:
                    continue

                for threshold, direction in thresholds["freeze-up"].items():

                    date = self._find_threshold_crossing(
                        window,
                        column=column,
                        threshold=threshold,
                        direction=direction,
                        persistence=persistence,
                    )

                    records.append(
                        {
                            "region": region,
                            "event_type": "freeze-up",
                            "year": int(year),
                            "threshold_percent": threshold,
                            "date": date,
                        }
                    )

        # ---------------------------------------------------------
        # Create result dataframe
        # ---------------------------------------------------------

        self.events_df = pd.DataFrame(
            records,
            columns=[
                "region",
                "event_type",
                "year",
                "threshold_percent",
                "date",
            ],
        )

        if not self.events_df.empty:

            self.events_df["date"] = pd.to_datetime(
                self.events_df["date"],
            )

            self.events_df.sort_values(
                [
                    "region",
                    "year",
                    "event_type",
                    "threshold_percent",
                ],
                inplace=True,
            )

            self.events_df.reset_index(
                drop=True,
                inplace=True,
            )

        logger.info(
            "Calculated %d threshold-event records.",
            len(self.events_df),
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

        self.events_output_path.parent.mkdir(
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

        self.events_df.to_csv(
            self.events_output_path,
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

        logger.info(
            "Saved threshold events to %s",
            self.events_output_path,
        )

        return ( self.output_path, self.yearly_output_path, )