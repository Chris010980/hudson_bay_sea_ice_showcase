# Hudson Bay Sea Ice Analysis

A reproducible Python workflow for the automated download, processing, analysis, and visualization of daily sea-ice concentration data for the Hudson Bay region.

The project automatically synchronizes the latest observations from the **National Snow and Ice Data Center (NSIDC)**, derives regional sea-ice statistics, and generates publication-quality maps and seasonal time-series visualizations. The complete workflow is designed to be reproducible and suitable for scientific analysis as well as portfolio presentation.

---

# Features

* Automated synchronization with the latest NSIDC GeoTIFF archive
* Incremental processing (only newly available observations are analysed)
* Regional analysis for five Hudson Bay subregions
* Daily sea-ice concentration statistics
* Publication-quality regional overview maps
* Seasonal Cartesian time-series
* Polar seasonal visualizations
* Automatic figure generation
* Reproducible scientific workflow
* GitHub Actions compatible for scheduled daily updates

---

# Workflow

```
            NSIDC Daily GeoTIFF Archive
                      │
                      ▼
            Download missing observations
                      │
                      ▼
            Process new GeoTIFF files
                      │
                      ▼
        Regional sea-ice concentration analysis
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
ice_coverage_summary.csv      latest.json
         │                         │
         └────────────┬────────────┘
                      ▼
          Generate publication-quality plots
                      │
                      ▼
              GitHub Pages Showcase
```

The update pipeline is fully incremental. Existing observations are not processed again, allowing daily updates to complete within only a few seconds if no new satellite products are available.

---

# Scientific Background

Hudson Bay is one of the world's largest seasonally ice-covered inland seas. Every year, sea ice begins to form during autumn, reaches its maximum extent during late winter, and melts again throughout spring and summer.

Monitoring this seasonal cycle provides valuable information for

* regional climate studies,
* marine ecosystems,
* navigation,
* Indigenous communities,
* operational ice forecasting.

Instead of analysing the Arctic Ocean as a whole, this project focuses on the Hudson Bay system and its individual subregions.

---

# Data Source

**Dataset**

NOAA / NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration

**Provider**

National Snow and Ice Data Center (NSIDC)

**Product**

Daily Northern Hemisphere Sea Ice Concentration GeoTIFF

**Projection**

Polar Stereographic (EPSG:3411)

**Temporal coverage**

1978 – present

**Spatial resolution**

25 km

The original GeoTIFF products remain unchanged. All derived quantities are generated reproducibly from the source data.

---

# Analysis Regions

The workflow computes daily statistics for

* Hudson Bay Area
* Hudson Bay
* Foxe Basin
* Gulf of Boothia
* Hudson Strait

Region definitions are stored separately as configurable polygons.

---

# Generated Outputs

## Analysis

```
output/
└── analysis/
    ├── ice_coverage_summary.csv
    └── latest.json
```

The CSV file contains the complete historical time series.

The JSON file contains the most recent observation and is intended for dashboards and the GitHub Pages showcase.

---

## Figures

The workflow automatically generates

* regional sea-ice overview maps
* region-highlight maps
* seasonal time-series
* polar seasonal diagrams

All figures are exported as publication-quality PNG files.

---

# Project Structure

```text
hudson_bay_sea_ice/
├── data/
│   ├── geotiff/
│   └── naturalearth/
│
├── logs/
│
├── output/
│   ├── analysis/
│   ├── plots/
│   └── reference/
│
├── src/
│   ├── analysis/
│   ├── config/
│   ├── data_download/
│   ├── update/
│   ├── visualization/
│   └── main.py
│
├── tests/
│
├── requirements.txt
└── README.md
```

---

# Installation

Clone the repository

```bash
git clone https://github.com/Chris010980/hudson_bay_sea_ice.git
cd hudson_bay_sea_ice
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate the environment

Linux / macOS

```bash
source .venv/bin/activate
```

Windows

```cmd
.venv\Scripts\activate
```

Install the required packages

```bash
pip install -r requirements.txt
```

---

# Usage

## Download the complete dataset

```bash
python src/main.py download
```

---

## Process all available observations

```bash
python src/main.py process
```

---

## Generate all visualizations

```bash
python src/main.py plots
```

---

## Run the complete daily update pipeline

```bash
python src/main.py update
```

The update pipeline performs

1. synchronization with the NSIDC archive,
2. download of missing GeoTIFF files,
3. regional analysis,
4. update of the CSV results,
5. generation of all figures,
6. optional cleanup of temporary data.

If no new observations are available, the workflow exits automatically after verifying that the local dataset is already up to date.

---

# Technologies

* Python
* NumPy
* Pandas
* Rasterio
* PyProj
* Cartopy
* Matplotlib
* Shapely
* GeoJSON
* GitHub Actions

---

# Reproducibility

Every generated figure can be reproduced directly from the original NSIDC dataset using the documented processing pipeline.

The project separates

* raw data,
* derived analysis,
* generated figures,
* configuration files,

to ensure transparent and reproducible results.

---

# Future Extensions

Possible future developments include

* climatological reference periods
* anomaly calculations
* freeze-up and break-up detection
* long-term trend analysis
* interactive web visualizations
* automated report generation
* integration of atmospheric and oceanographic datasets

---

# License

This project is released under the MIT License.

---

# Author

Christian Lurz

Software QA Engineer | Physicist

Scientific Data Analysis • Geospatial Visualization • Python Development
