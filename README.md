# India District-Wise Nighttime Lights Database (VIIRS, 2012-2024)

**A ready-to-use, open-source Python pipeline that downloads and builds a complete district-level nighttime lights panel dataset for India using VIIRS satellite imagery (2012-2024).** One command gives you a clean CSV with 641 districts x 13 years of nightlight radiance statistics -- no manual downloads, no GIS expertise needed.

If you've been searching for *India night light data by district*, *VIIRS nighttime lights India download*, *district-wise luminosity data India*, or *satellite nightlight data for Indian states and districts* -- this is what you need.

---

## What I Built

I built a fully automated pipeline that:

1. **Downloads district boundaries** -- Census 2011 district shapefiles from [DataMeet](https://github.com/datameet/maps) (641 districts across 35 states/UTs)
2. **Pulls VIIRS satellite nightlight rasters** from Google Earth Engine (annual median radiance composites, 2012-2024)
3. **Computes district-level zonal statistics** -- mean, median, sum, std, min, max radiance per district per year
4. **Exports everything** as a flat CSV panel and year-wise GeoJSON files with district polygons

The whole thing runs end-to-end with a single command. The output is a clean, research-ready dataset you can directly use in Stata, R, Python, or Excel.

## Output

### CSV: `output/csv/nightlights_district_panel.csv`

**8,333 rows** (641 districts x 13 years) with these columns:

| Column | Description |
|--------|-------------|
| `district_id` | Census 2011 district code |
| `district_name` | District name |
| `state_name` | State / UT name |
| `year` | Year (2012-2024) |
| `mean` | Mean nightlight radiance (nW/cm²/sr) |
| `median` | Median nightlight radiance |
| `sum` | Total nightlight radiance (proxy for total economic activity) |
| `std` | Standard deviation of radiance |
| `min` / `max` | Min and max pixel radiance in the district |
| `valid_pixel_count` | Number of valid satellite pixels covering the district |
| `log1p_mean` | log(1 + mean) -- log-transformed mean for econometric use |
| `log1p_median` | log(1 + median) -- log-transformed median |

### GeoJSON: `output/geojson/nightlights_districts_<YEAR>.geojson`

One file per year with district polygons and all nightlight metrics attached -- ready for mapping in QGIS, kepler.gl, or any GIS tool.

## Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/yashveeeeeer/india-district-nightlights-viirs.git
cd india-district-nightlights-viirs
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

### 2. Set up Google Earth Engine (one-time)

The pipeline uses Google Earth Engine to download VIIRS rasters. You need:
- A free Google Earth Engine account -- [register here](https://code.earthengine.google.com/register)
- A Google Cloud project with the Earth Engine API enabled

```bash
earthengine authenticate
earthengine set_project YOUR_PROJECT_ID
```

If you have a **service account key** (recommended for automation), place it as `sa-key.json` in the project root and set the path in `configs/config.yaml`.

### 3. Run the full pipeline

```bash
python -m ntl_pipeline.cli run-all
```

This runs four steps automatically:
1. Downloads district boundaries from DataMeet
2. Downloads VIIRS annual nightlight rasters via Earth Engine (2012-2024)
3. Computes zonal statistics per district per year
4. Exports CSV panel and year-wise GeoJSON files

You can also run steps individually:

```bash
python -m ntl_pipeline.cli download-boundaries --config configs/config.yaml
python -m ntl_pipeline.cli download-viirs      --config configs/config.yaml
python -m ntl_pipeline.cli zonal-stats          --config configs/config.yaml
python -m ntl_pipeline.cli export-geojson       --config configs/config.yaml
```

## Configuration

Edit `configs/config.yaml` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `nightlights.years.start` | 2012 | First year |
| `nightlights.years.end` | 2024 | Last year |
| `nightlights.viirs.ee_scale` | 1000 | Resolution in metres (lower = finer but slower) |
| `nightlights.viirs.ee_project` | -- | Your Google Cloud project ID |
| `processing.metrics` | mean, median, sum, std, min, max | Zonal statistics to compute |

## Data Sources

| Source | What | Coverage |
|--------|------|----------|
| [NOAA VIIRS DNB](https://developers.google.com/earth-engine/datasets/catalog/NOAA_VIIRS_DNB_MONTHLY_V1_VCMCFG) | Monthly nighttime light composites (avg_rad band) | Global, 2012-present |
| [DataMeet Maps](https://github.com/datameet/maps) | India Census 2011 district boundaries | 641 districts, 35 states/UTs |

## Why Nighttime Lights?

Satellite-observed nighttime lights are one of the most widely used proxies for economic activity in development economics, urban studies, and policy research. They are especially valuable for:

- **Sub-national GDP estimation** where official statistics are unavailable or unreliable
- **Tracking electrification** and infrastructure development over time
- **Measuring urbanization** and urban sprawl at the district level
- **Disaster impact assessment** -- comparing pre/post nightlight levels
- **Inequality research** -- spatial distribution of economic activity

### Tips for researchers

- Use `log1p_mean` or `log1p_median` columns to handle the right-skewed distribution
- Prefer `median` radiance (less sensitive to outliers like gas flares) plus `sum` for total light output
- Check `valid_pixel_count` as a data quality diagnostic
- For panel regressions, the `district_id` (Census 2011 code) is a stable identifier across years

## Project Structure

```
india-district-nightlights-viirs/
├── configs/
│   └── config.yaml              # Pipeline configuration
├── src/ntl_pipeline/
│   ├── cli.py                   # CLI commands (run-all, download-viirs, etc.)
│   ├── viirs_download.py        # VIIRS download via Earth Engine
│   ├── boundaries.py            # District boundary download and loading
│   ├── zonal.py                 # Zonal statistics computation
│   ├── exporters.py             # CSV and GeoJSON export
│   ├── config.py                # YAML config loader
│   ├── io.py                    # File download utilities
│   └── rasters.py               # Raster reprojection utilities
├── output/
│   ├── csv/                     # Panel CSV (gitignored)
│   └── geojson/                 # Year-wise GeoJSON (gitignored)
├── data/                        # Raw data downloads (gitignored)
├── requirements.txt
├── pyproject.toml
└── Makefile
```

## Requirements

- Python 3.10+
- Google Earth Engine account (free)
- Google Cloud project with Earth Engine API enabled
- ~2 GB disk space for rasters and outputs

## Keywords

India nighttime lights, India night light data download, district-wise nightlight India, VIIRS India district, satellite nightlight data India, India luminosity data, India radiance data district level, night light GDP proxy India, DMSP OLS India, India economic activity satellite, nighttime lights panel data India, India district level data, VIIRS annual composite India, remote sensing India economics, geospatial India district data, night lights India 2024, India nightlight database

## License

Code is MIT licensed. Downloaded rasters and boundary files are governed by their respective data providers' terms (NOAA/EOG for VIIRS, DataMeet/Survey of India for boundaries).

## Citation

If you use this dataset or pipeline in your research, please consider linking back to this repository.
