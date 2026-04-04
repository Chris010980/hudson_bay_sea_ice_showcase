# results.py
import os
import pandas as pd

class ResultsManager:
    def __init__(self, csv_path="results/ice_coverage_summary.csv"):
        self.results = []  # Neue Ergebnisse
        self.csv_path = csv_path
        if os.path.exists(self.csv_path):
            self.df_existing = pd.read_csv(self.csv_path)
        else:
            self.df_existing = pd.DataFrame(columns=["date", "region", "ice_coverage"])

    def add_result(self, result):
        self.results.append(result)

    def save_to_csv(self, path=None):
        if path is None:
            path = self.csv_path
    
        df_new = pd.DataFrame(self.results)
        df_combined = pd.concat([self.df_existing, df_new], ignore_index=True)
    
        # Doppelte Zeilen (Datum+Region) raus
        df_combined.drop_duplicates(subset=["date", "region"], inplace=True)
    
        df_combined.to_csv(path, index=False)
        return df_combined

    def is_date_already_processed(self, date, csv_path):
        """
        Prüft, ob das Datum bereits in der Ergebnis-CSV vorhanden ist.
        """
        if not os.path.exists(csv_path):
            return False  # Keine Datei, also kein Datum enthalten

        df = pd.read_csv(csv_path, usecols=["date"])
        return (df["date"] == date).any()
    
    def load_existing_rows_for_date(self, date):
        """
        Gibt alle Zeilen aus der bestehenden CSV für ein bestimmtes Datum zurück.
        """
        if self.df_existing.empty:
            return pd.DataFrame(columns=self.df_existing.columns)
        return self.df_existing[self.df_existing["date"] == date].copy()
