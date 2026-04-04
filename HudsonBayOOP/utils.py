# utils.py
import re
from pathlib import Path

def extract_date_from_filename(filename):
    match = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
    if match:
        y, m, d = match.groups()
        return f"{y}-{m}-{d}"
    else:
        return None

def ensure_directories():
    """
    Erzeugt alle benötigten Ordner, falls sie nicht existieren.
    """
    required_dirs = [
        Path("results"),
        Path("results/plots_by_region"),
        Path("results/polarplots_by_region"),
        Path("GeoJson")
    ]

    for folder in required_dirs:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"[✔] Verzeichnis vorhanden: {folder.resolve()}")