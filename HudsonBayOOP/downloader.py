# downloader.py
import os
import requests
from bs4 import BeautifulSoup

class NSIDCDownloader:
    """
    Lädt NOAA NSIDC GeoTIFF concentration-Daten automatisch herunter.
    Erkennt automatisch alle Jahre & Monate.
    """
    def __init__(self, base_url, local_base):
        self.base_url = base_url.rstrip("/") + "/"
        self.local_base = local_base.rstrip("/") + "/"

    def get_remote_years(self):
        """
        Listet alle verfügbaren Jahre im NOAA-Verzeichnis.
        """
        resp = requests.get(self.base_url)
        if resp.status_code != 200:
            raise RuntimeError(f"[!] Fehler beim Abrufen: {self.base_url}")
        
        soup = BeautifulSoup(resp.text, "html.parser")
        years = [
            link.get("href").strip("/")
            for link in soup.find_all("a")
            if link.get("href").strip("/").isdigit()
        ]
        return sorted(years)

    def get_remote_months(self, year):
        """
        Listet alle verfügbaren Monate für ein Jahr.
        """
        year_url = f"{self.base_url}{year}/"
        resp = requests.get(year_url)
        if resp.status_code != 200:
            raise RuntimeError(f"[!] Fehler beim Abrufen: {year_url}")
        
        soup = BeautifulSoup(resp.text, "html.parser")
        months = [
            link.get("href").strip("/")
            for link in soup.find_all("a")
            if "_" in link.get("href") and link.get("href").endswith("/")
        ]
        return sorted(months)

    def get_remote_files(self, year, month):
        """
        Listet alle GeoTIFF concentration-Dateien für Jahr/Monat.
        """
        month_url = f"{self.base_url}{year}/{month}/"
        resp = requests.get(month_url)
        if resp.status_code != 200:
            print(f"[!] Fehler beim Abrufen: {month_url}")
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        files = [
            link.get("href")
            for link in soup.find_all("a")
            if "concentration" in link.get("href") and link.get("href").endswith(".tif")
        ]
        return sorted(files)

    def get_local_files(self, year, month):
        """
        Listet alle lokal vorhandenen GeoTIFFs für Jahr/Monat.
        """
        local_dir = os.path.join(self.local_base, year, month)
        if not os.path.exists(local_dir):
            return []
        return [
            f for f in os.listdir(local_dir)
            if f.endswith(".tif") and "concentration" in f
        ]

    def download_file(self, year, month, filename):
        """
        Lädt eine einzelne GeoTIFF-Datei herunter.
        """
        remote_url = f"{self.base_url}{year}/{month}/{filename}"
        local_dir = os.path.join(self.local_base, year, month)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)

        print(f"[↓] Lade {remote_url}")
        resp = requests.get(remote_url, stream=True)
        if resp.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[✔] Gespeichert: {local_path}")
        else:
            print(f"[!] Fehler {resp.status_code} beim Download: {remote_url}")

    def sync(self):
        """
        Synchronisiert alle verfügbaren Daten.
        """
        years = self.get_remote_years()
        for year in years:
            months = self.get_remote_months(year)
            for month in months:
                print(f"[i] Prüfe {year}/{month} ...")
                remote_files = self.get_remote_files(year, month)
                local_files = self.get_local_files(year, month)

                missing_files = set(remote_files) - set(local_files)
                if not missing_files:
                    print("[✔] Alles vorhanden.")
                else:
                    print(f"[!] Fehlen: {len(missing_files)} Dateien.")
                    for filename in missing_files:
                        self.download_file(year, month, filename)
