from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich import print

from .config import Config
from .boundaries import download_datameet_boundaries, load_districts
from .viirs_download import download_viirs
from .zonal import compute_zonal_stats
from .exporters import export_panel_csv, export_year_geojson

app = typer.Typer(add_completion=False)


@app.command("download-boundaries")
def download_boundaries(config: Path = typer.Option(..., "--config")):
    cfg = Config.load(config)
    raw_dir = Path("data/raw")
    shp = download_datameet_boundaries(cfg, raw_dir)
    print(f"[green]Boundaries ready:[/green] {shp}")


@app.command("download-viirs")
def download_viirs_cmd(config: Path = typer.Option(..., "--config")):
    """Download VIIRS annual nightlight rasters (Earth Engine or EOG)."""
    cfg = Config.load(config)
    start = int(cfg.get("nightlights", "years", "start"))
    end = int(cfg.get("nightlights", "years", "end"))
    years = list(range(start, end + 1))
    target = Path("data/raw/viirs")

    use_ee = cfg.get("nightlights", "viirs", "use_earth_engine", default=True)
    eog_url = cfg.get("nightlights", "viirs", "eog_base_url")
    band = cfg.get("nightlights", "viirs", "product_band", default="average")
    ee_scale = int(cfg.get("nightlights", "viirs", "ee_scale", default=500))
    ee_project = cfg.get("nightlights", "viirs", "ee_project", default=None)
    ee_sa_key = cfg.get("nightlights", "viirs", "ee_service_account_key", default=None)

    paths = download_viirs(
        years=years,
        out_dir=target,
        use_earth_engine=use_ee,
        eog_base_url=eog_url,
        product_band=band,
        ee_scale=ee_scale,
        ee_project=ee_project,
        ee_sa_key=ee_sa_key,
    )
    print(f"[green]Downloaded {len(paths)} raster(s) to {target}[/green]")


@app.command("prep-rasters")
def prep_rasters(
    config: Path = typer.Option(..., "--config"),
    source: str = typer.Option("viirs", "--source"),
):
    # For many EOG products CRS is already EPSG:4326. Keep as a hook.
    print(f"[green]prep-rasters[/green] no-op for source={source} (assumes EPSG:4326).")


@app.command("zonal-stats")
def zonal_stats_cmd(config: Path = typer.Option(..., "--config")):
    cfg = Config.load(config)
    start = int(cfg.get("nightlights", "years", "start"))
    end = int(cfg.get("nightlights", "years", "end"))
    metrics = list(cfg.get("processing", "metrics"))

    # boundaries
    shp_dir = Path("data/raw/boundaries/datameet_districts_2011")
    shp_files = list(shp_dir.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError("District shapefile not found. Run: make boundaries")
    districts = load_districts(shp_files[0])

    # rasters
    rows = []
    for year in range(start, end + 1):
        raster_path = Path(f"data/raw/viirs/VIIRS_{year}.tif")
        if not raster_path.exists():
            raise FileNotFoundError(f"Missing raster for {year}: {raster_path}")
        print(f"Computing zonal stats for {year}...")
        rows.append(compute_zonal_stats(districts, raster_path, year, metrics))

    panel = pd.concat(rows, ignore_index=True)
    out_csv = Path(cfg.get("outputs", "csv_path"))
    export_panel_csv(panel, out_csv)
    print(f"[green]Wrote[/green] {out_csv}")


@app.command("export-geojson")
def export_geojson(config: Path = typer.Option(..., "--config")):
    cfg = Config.load(config)
    csv_path = Path(cfg.get("outputs", "csv_path"))
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing panel CSV: {csv_path}. Run: make stats")

    shp_dir = Path("data/raw/boundaries/datameet_districts_2011")
    shp_files = list(shp_dir.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError("District shapefile not found. Run: make boundaries")
    districts = load_districts(shp_files[0])

    df = pd.read_csv(csv_path)
    out_dir = Path(cfg.get("outputs", "geojson_dir"))
    for year, ydf in df.groupby("year"):
        out_path = out_dir / f"nightlights_districts_{int(year)}.geojson"
        export_year_geojson(districts, ydf, out_path)
        print(f"[green]Wrote[/green] {out_path}")


@app.command("run-all")
def run_all(config: Path = typer.Option("configs/config.yaml", "--config")):
    """Run the full pipeline end-to-end: boundaries -> VIIRS -> zonal stats -> GeoJSON."""
    print("[bold]Step 1/4: Downloading district boundaries...[/bold]")
    download_boundaries(config)

    print("\n[bold]Step 2/4: Downloading VIIRS rasters...[/bold]")
    download_viirs_cmd(config)

    print("\n[bold]Step 3/4: Computing zonal statistics...[/bold]")
    zonal_stats_cmd(config)

    print("\n[bold]Step 4/4: Exporting GeoJSON files...[/bold]")
    export_geojson(config)

    cfg = Config.load(config)
    print(f"\n[bold green]Done![/bold green]")
    print(f"  CSV  : {cfg.get('outputs', 'csv_path')}")
    print(f"  JSON : {cfg.get('outputs', 'geojson_dir')}/")


def main():
    app()


if __name__ == "__main__":
    main()
