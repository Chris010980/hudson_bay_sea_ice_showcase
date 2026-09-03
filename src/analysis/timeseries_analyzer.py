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
        # Search for actual threshold crossings
        # ---------------------------------------------------------

        for start_idx in range(
            1,
            len(data),
        ):

            previous = data.iloc[start_idx - 1]
            current = data.iloc[start_idx]

            # -----------------------------------------------------
            # Crossing must occur between consecutive calendar days.
            # -----------------------------------------------------

            if (
                current["date"] - previous["date"]
                != pd.Timedelta(days=1)
            ):
                continue

            y0 = previous[column]
            y1 = current[column]

            # -----------------------------------------------------
            # Determine whether an actual crossing occurred.
            # -----------------------------------------------------

            if direction == "down":

                crossed = (
                    y0 > threshold
                    and y1 <= threshold
                )

            else:  # direction == "up"

                crossed = (
                    y0 < threshold
                    and y1 >= threshold
                )

            if not crossed:
                continue

            # -----------------------------------------------------
            # Check persistence.
            #
            # The crossing day itself counts as the first
            # persistence day.
            # -----------------------------------------------------

            end_idx = start_idx + persistence

            if end_idx > len(data):
                continue

            persistent_segment = data.iloc[
                start_idx:end_idx
            ]

            if len(persistent_segment) < persistence:
                continue

            # -----------------------------------------------------
            # All persistence observations must be consecutive
            # calendar days.
            # -----------------------------------------------------

            date_deltas = (
                persistent_segment["date"]
                .diff()
                .dropna()
            )

            if not date_deltas.eq(
                pd.Timedelta(days=1)
            ).all():
                continue

            # -----------------------------------------------------
            # Check persistence on the required side.
            # -----------------------------------------------------

            if direction == "down":

                persistent = (
                    persistent_segment[column]
                    <= threshold
                ).all()

            else:

                persistent = (
                    persistent_segment[column]
                    >= threshold
                ).all()

            if not persistent:
                continue

            # -----------------------------------------------------
            # Valid persistent crossing found.
            #
            # Interpolate between the observations immediately
            # surrounding the threshold.
            # -----------------------------------------------------

            if y0 == threshold:
                return previous["date"]

            if y1 == threshold:
                return current["date"]

            if y1 == y0:
                return current["date"]

            fraction = (
                threshold - y0
            ) / (
                y1 - y0
            )

            if not 0.0 <= fraction <= 1.0:
                continue

            delta = (
                current["date"]
                - previous["date"]
            )

            return (
                previous["date"]
                + fraction * delta
            )

        return None

    def _get_event_window(
        self,
        df_region: pd.DataFrame,
        event_year: int,
        event_type: str,
        start_date: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """
        Return the time window used for a threshold event search.

        Parameters
        ----------
        df_region:
            Regional daily time series.

        event_year:
            Calendar year of the event.

        event_type:
            ``"break-up"`` or ``"freeze-up"``.

        start_date:
            Optional dynamic start date. If supplied, it overrides
            the normal seasonal start date.

        Returns
        -------
        pd.DataFrame
            Data restricted to the requested event window.
        """

        if event_type == "break-up":

            default_start = pd.Timestamp(
                year=event_year,
                month=3,
                day=16,
            )

            end = pd.Timestamp(
                year=event_year,
                month=9,
                day=15,
            )

        elif event_type == "freeze-up":

            default_start = pd.Timestamp(
                year=event_year,
                month=9,
                day=16,
            )

            end = pd.Timestamp(
                year=event_year + 1,
                month=3,
                day=15,
            )

        else:
            raise ValueError(
                f"Unknown event type: {event_type}"
            )

        if start_date is None:
            start = default_start
        else:
            start = pd.Timestamp(start_date)

        if start > end:
            return df_region.iloc[0:0].copy()

        return df_region[
            df_region["date"].between(
                start,
                end,
            )
        ].copy()

    def calculate_threshold_events(
        self,
        thresholds: tuple[float, ...] = (
            10.0,
            50.0,
            90.0,
        ),
        persistence: int = 7,
        column: str = "relative_coverage_percent",
    ) -> pd.DataFrame:
        """
        Calculate break-up and freeze-up threshold events.

        Break-up events are searched between March 16 and September 15.

        Freeze-up events normally start on September 16 and extend
        through March 15 of the following year.

        If a threshold has a valid break-up event but the threshold is
        already reached or exceeded on September 16, the freeze-up
        search is extended backwards to the day after the corresponding
        break-up event. This allows an earlier freeze-up crossing in
        September to be detected.

        A freeze-up event is only considered meaningful if the
        corresponding threshold was crossed during the preceding
        break-up season.
        """

        logger.info(
            "Calculating threshold events "
            "(thresholds=%s, persistence=%d days).",
            thresholds,
            persistence,
        )

        if self.df.empty:
            logger.warning(
                "Cannot calculate threshold events: dataframe is empty."
            )

            self.events_df = pd.DataFrame(
                columns=[
                    "region",
                    "event_type",
                    "event_year",
                    "threshold_percent",
                    "event_date",
                ]
            )

            return self.events_df

        events = []

        # ---------------------------------------------------------
        # Process each region independently
        # ---------------------------------------------------------

        for region, df_region in self.df.groupby("region"):

            df_region = (
                df_region
                .sort_values("date")
                .reset_index(drop=True)
            )

            min_year = (
                df_region["date"]
                .dt.year
                .min()
            )

            max_year = (
                df_region["date"]
                .dt.year
                .max()
            )

            # -----------------------------------------------------
            # Process each event year
            # -----------------------------------------------------

            for event_year in range(
                min_year,
                max_year + 1,
            ):

                # =================================================
                # BREAK-UP WINDOW
                # =================================================

                breakup_window = self._get_event_window(
                    df_region=df_region,
                    event_year=event_year,
                    event_type="break-up",
                )

                # =================================================
                # FREEZE-UP DEFAULT WINDOW
                #
                # 16 September -> 15 March
                # =================================================

                default_freezeup_window = self._get_event_window(
                    df_region=df_region,
                    event_year=event_year,
                    event_type="freeze-up",
                )

                # -------------------------------------------------
                # Iterate over thresholds
                # -------------------------------------------------

                for threshold in thresholds:

                    # =============================================
                    # BREAK-UP
                    # =============================================

                    breakup_date = self._find_threshold_crossing(
                        df=breakup_window,
                        column=column,
                        threshold=threshold,
                        direction="down",
                        persistence=persistence,
                    )

                    events.append(
                        {
                            "region": region,
                            "event_type": "break-up",
                            "event_year": event_year,
                            "threshold_percent": threshold,
                            "event_date": breakup_date,
                        }
                    )

                    # =============================================
                    # FREEZE-UP
                    # =============================================

                    # No break-up means that the threshold was never
                    # reached from above during the melt season.
                    #
                    # Consequently, there is no meaningful freeze-up
                    # event for this threshold in the following season.

                    if breakup_date is None:

                        freezeup_date = None

                        logger.debug(
                            "No freeze-up for %s / %d / %.1f%%: "
                            "no corresponding break-up event.",
                            region,
                            event_year,
                            threshold,
                        )

                    else:

                        # -----------------------------------------
                        # Determine the state on September 16.
                        # -----------------------------------------

                        september_16 = pd.Timestamp(
                            year=event_year,
                            month=9,
                            day=16,
                        )

                        sep16_data = df_region[
                            df_region["date"]
                            == september_16
                        ]

                        # -----------------------------------------
                        # Default:
                        #
                        # Search from September 16 onward.
                        # -----------------------------------------

                        freezeup_start = september_16

                        # -----------------------------------------
                        # If the threshold has already been reached
                        # on September 16, the actual freeze-up may
                        # have happened before September 16.
                        #
                        # In this case extend the search window back
                        # to the day after the corresponding break-up.
                        # -----------------------------------------

                        if not sep16_data.empty:

                            sep16_value = pd.to_numeric(
                                sep16_data.iloc[0][column],
                                errors="coerce",
                            )

                            if (
                                pd.notna(sep16_value)
                                and sep16_value >= threshold
                            ):

                                freezeup_start = (
                                    pd.Timestamp(breakup_date)
                                    .normalize()
                                    + pd.Timedelta(days=1)
                                )

                                logger.debug(
                                    "Extending freeze-up window for "
                                    "%s / %d / %.1f%%: "
                                    "value on September 16 is %.2f%% "
                                    "(>= threshold). Start: %s.",
                                    region,
                                    event_year,
                                    threshold,
                                    sep16_value,
                                    freezeup_start.date(),
                                )

                        # -----------------------------------------
                        # Build the actual freeze-up search window.
                        # -----------------------------------------

                        freezeup_window = self._get_event_window(
                            df_region=df_region,
                            event_year=event_year,
                            event_type="freeze-up",
                            start_date=freezeup_start,
                        )

                        # -----------------------------------------
                        # Search for actual upward crossing.
                        # -----------------------------------------

                        freezeup_date = (
                            self._find_threshold_crossing(
                                df=freezeup_window,
                                column=column,
                                threshold=threshold,
                                direction="up",
                                persistence=persistence,
                            )
                        )

                    events.append(
                        {
                            "region": region,
                            "event_type": "freeze-up",
                            "event_year": event_year,
                            "threshold_percent": threshold,
                            "event_date": freezeup_date,
                        }
                    )

        # ---------------------------------------------------------
        # Create result dataframe
        # ---------------------------------------------------------

        self.events_df = (
            pd.DataFrame(events)
            .sort_values(
                [
                    "region",
                    "event_year",
                    "event_type",
                    "threshold_percent",
                ]
            )
            .reset_index(drop=True)
        )

        logger.info(
            "Calculated %d threshold event records.",
            len(self.events_df),
        )

        return self.events_df

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