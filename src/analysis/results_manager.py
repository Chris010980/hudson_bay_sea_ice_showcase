"""
Collect and store analysis results.
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


class ResultsManager:

    def __init__(
        self,
        csv_path: str | Path = DEFAULT_RESULTS,
    ):

        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.results: list[dict] = []

        if self.csv_path.exists():

            self.df_existing = pd.read_csv(
                self.csv_path,
            )

        else:

            self.df_existing = pd.DataFrame()

    # ---------------------------------------------------------
    # public API
    # ---------------------------------------------------------

    def add_results(
        self,
        results: dict,
    ):

        self.results.extend(results.values())

    def is_date_processed(
        self,
        date,
    ) -> bool:

        if self.df_existing.empty:
            return False

        return (
            self.df_existing["date"]
            == str(date)
        ).any()

    def save(self):

        df_new = pd.DataFrame(self.results)

        if df_new.empty:

            logger.info("No new results.")

            return self.df_existing

        df = pd.concat(
            [
                self.df_existing,
                df_new,
            ],
            ignore_index=True,
        )

        df.drop_duplicates(
            subset=["date", "region"],
            keep="last",
            inplace=True,
        )

        df.sort_values(
            [
                "date",
                "region",
            ],
            inplace=True,
        )

        df.to_csv(
            self.csv_path,
            index=False,
        )

        logger.info(
            "Saved %d rows.",
            len(df),
        )

        return df