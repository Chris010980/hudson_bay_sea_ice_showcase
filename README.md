# Arctic Sea Ice Coverage – Hudson Bay

A reproducible Python project for analysing and visualising the seasonal evolution of sea ice in Hudson Bay.

The project combines time-series analysis, spatial maps, and polar visualisations to examine how sea-ice coverage changes throughout the annual freeze-up and melt cycle. It is designed as a transparent analytical workflow: source data are processed into derived metrics and then transformed into publication-ready static figures and animations.

---

## Overview

Hudson Bay is a seasonally ice-covered marginal sea of the Arctic. Its ice cover typically grows during autumn and winter, reaches a late-winter maximum, and retreats during spring and summer.

This project focuses on the temporal and spatial structure of that cycle. Rather than treating sea ice as a single annual value, it examines how coverage evolves over time and across the Hudson Bay region.

The analysis includes:

- time series of sea-ice coverage or concentration
- seasonal comparisons between years
- spatial maps of sea-ice conditions
- polar map projections for regional context
- derived indicators for freeze-up, maximum coverage, and melt progression
- reproducible figure generation with Python

> **Note:** The exact interpretation of “coverage” depends on the source dataset. It may refer to sea-ice concentration, sea-ice extent, sea-ice area, or a regionally aggregated measure. The terminology in figures and documentation should match the selected data source precisely.

---

## Scientific Context

Sea ice is frozen seawater floating on the ocean surface. It follows a strong seasonal cycle: growth begins when autumn cooling reduces ocean heat and air temperatures fall below freezing; melting begins as solar input and temperatures rise in spring and summer.

Sea ice is relevant beyond its visible seasonal cycle. It affects exchanges of heat, moisture, and momentum between ocean and atmosphere, influences regional ecosystems and coastal conditions, and changes surface reflectivity. Open water absorbs substantially more solar radiation than ice-covered water, creating an ice–albedo feedback that can amplify warming.

Hudson Bay provides a useful regional case study because its sea ice is highly seasonal and its enclosed geography makes spatial changes in freeze-up and melt progression visually accessible.

For background on sea-ice processes and terminology, see the National Snow and Ice Data Center (NSIDC) and NASA Earth Observatory resources.  
- [NSIDC: Sea Ice](https://nsidc.org/learn/parts-cryosphere/sea-ice)  
- [NSIDC: Science of Sea Ice](https://nsidc.org/learn/parts-cryosphere/sea-ice/science-sea-ice)  
- [NASA Earth Observatory: Sea Ice](https://science.nasa.gov/earth/earth-observatory/sea-ice/)

---

## Questions Addressed

The project is intended to support questions such as:

- How does sea-ice coverage in Hudson Bay evolve over the annual cycle?
- When do freeze-up, peak coverage, and melt onset occur?
- How do individual years differ from a reference period or long-term average?
- Which parts of Hudson Bay retain ice longest during the melt season?
- How can time series and spatial maps be combined to make seasonal changes easier to interpret?

The project is exploratory and visual-analytical. It does not attempt to attribute individual events or trends to a specific physical cause.

---

## Data

**Primary dataset:** `[INSERT DATASET NAME]`  
**Provider:** `[INSERT PROVIDER]`  
**Temporal coverage:** `[INSERT START YEAR]–[INSERT END YEAR]`  
**Spatial resolution:** `[INSERT RESOLUTION]`  
**Variable used:** `[e.g. sea-ice concentration / sea-ice extent / sea-ice area]`

The source data are retained separately from generated outputs where licensing, file size, or download requirements make this appropriate.

### Data provenance

All visualisations should be reproducible from the documented source data and processing scripts. If raw data are not included in the repository, this README should state:

1. where the data can be obtained,
2. which files are required,
3. how they must be placed locally, and
4. whether preprocessing is needed before running the analysis.

---

## Methodology

The workflow consists of the following stages:

1. **Data acquisition**  
   Download or load gridded sea-ice data for the Hudson Bay region.

2. **Validation and preprocessing**  
   Inspect dimensions, timestamps, missing values, coordinate conventions, and physical units.

3. **Regional subsetting**  
   Restrict the data to Hudson Bay using a geographic bounding box or region mask.

4. **Temporal analysis**  
   Aggregate the selected variable into time series and compare seasonal evolution across years.

5. **Spatial analysis**  
   Produce maps for selected dates, seasonal stages, or year-to-year comparisons.

6. **Visualisation**  
   Generate line plots, regional maps, polar projections, and optional animations.

7. **Export**  
   Save figures and derived outputs in a structured output directory for use in the portfolio showcase.

---

## Project Structure

```text
project_root/
│
├── src/
│   ├── main.py
│   ├── data/
│   │   ├── download_data.py
│   │   └── downloader.py
│   ├── logging_config.py
│   └── paths.py
│
├── data/
│   └── geotiff/          # Downloaded NSIDC GeoTIFF files, excluded from Git
│
├── logs/                 # Runtime logs, excluded from Git
├── requirements.txt
└── README.md
```

## Installation

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/Chris010980/[REPOSITORY_NAME].git
cd [REPOSITORY_NAME]

python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

## Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Show the available pipeline stages:

```bash
python src/main.py -h
```

Run the download stage:

```bash
python src/main.py download
```

By default, downloads are stored below `data/geotiff/` and logs are written to
`logs/hudson_bay_sea_ice.log`.

The downloader compares the remote NSIDC directory listing with the files that
already exist locally. Files already present in `data/geotiff/<year>/<month>/`
are skipped, so rerunning the command only downloads missing files.

Preview what would be downloaded without writing files:

```bash
python src/main.py download --dry-run
```

Limit the check to a year or month:

```bash
python src/main.py download --year 2026 --dry-run
python src/main.py download --year 2026 --month 06_Jun --dry-run
```

Download only missing concentration files for a selected year:

```bash
python src/main.py download --year 2026
```

Download missing extent files instead of concentration files:

```bash
python src/main.py download --year 2026 --product extent
```

Both `--year` and `--month` can be repeated:

```bash
python src/main.py download --year 2025 --year 2026 --month 05_May --month 06_Jun
```

## Typical workflow:

### 1. Download or update source data in data/geotiff/

```bash
python src/main.py download
```

### 2. Run preprocessing

```bash
python src/main.py process
```

### 3. Generate plots

```bash
python src/main.py plots
```

### 4. Run all migrated stages

```bash
python src/main.py all
```

## Outputs

## Generated outputs may include:

seasonal time-series plots
annual or multi-year comparisons
Hudson Bay sea-ice concentration maps
polar-projection maps
freeze-up and melt-season visualisations
animations showing the progression of sea-ice conditions

The portfolio presentation is available at:

Data Visualization & Analysis Showcase

## Reproducibility

The project aims to make the full path from source data to final figure inspectable:

source data
→ validation and preprocessing
→ regional subsetting
→ analysis
→ visualisation
→ exported figure

Generated files in output/ can be regenerated from the scripts and documented inputs. Large raw datasets, temporary files, logs, and machine-specific configuration should generally be excluded through .gitignore.

## Limitations

Results depend on the temporal and spatial resolution of the source dataset.
Sea-ice concentration, extent, and area are different measures and should not be used interchangeably.
A regional analysis does not by itself establish causality or climate attribution.
Satellite-derived products can contain uncertainty, gaps, changing sensors, and algorithm-specific characteristics.

## Possible Extensions

Automated download and periodic update of source data
Long-term trend analysis and anomaly calculation
Comparison with air temperature, ocean temperature, wind, or atmospheric indices
Detection of freeze-up and break-up dates
Interactive web visualisations
Automated reporting pipeline
Integration with broader climate-data projects

## Technologies

Python
NumPy
Pandas
Xarray
Matplotlib
Cartopy
NetCDF / gridded climate-data tooling
Git and GitHub for version control and reproducibility

## License

[INSERT LICENSE]

Author

Christian Lurz
GitHub
