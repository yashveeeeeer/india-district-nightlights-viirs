"""Download VIIRS annual nighttime light composites for India.

Strategy A (default): Google Earth Engine  -- requires `earthengine-api` and
a one-time `earthengine authenticate`.  Uses the VIIRS monthly composites
(NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG), computes a per-year median, clips to
the India bounding box, and exports each year as a GeoTIFF.

Strategy B (fallback): Direct HTTP download from EOG / Payne Institute annual
VNL tiles.  No auth required, but the URL structure may change over time.
Downloads the global tile, then clips to India using rasterio.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

import numpy as np
from rich import print as rprint
from tqdm import tqdm


INDIA_BBOX = [68.0, 6.0, 97.5, 37.5]  # [west, south, east, north]


# ---------------------------------------------------------------------------
# Strategy A: Google Earth Engine
# ---------------------------------------------------------------------------

def _ee_init(project: str | None = None, sa_key_path: str | None = None):
    """Initialize the Earth Engine API.

    If *sa_key_path* is provided, authenticates with a service account key
    file (most reliable).  Otherwise falls back to user OAuth credentials.
    """
    import ee

    ee_kwargs: dict = {"opt_url": "https://earthengine-highvolume.googleapis.com"}
    if project:
        ee_kwargs["project"] = project

    if sa_key_path:
        import json
        with open(sa_key_path) as f:
            sa_info = json.load(f)
        sa_email = sa_info["client_email"]
        credentials = ee.ServiceAccountCredentials(sa_email, sa_key_path)
        ee.Initialize(credentials=credentials, **ee_kwargs)
        return

    try:
        ee.Initialize(**ee_kwargs)
        return
    except Exception:
        pass

    if not project:
        for fallback in ("earthengine-legacy", "earthengine-public"):
            try:
                ee.Initialize(**{**ee_kwargs, "project": fallback})
                return
            except Exception:
                pass

    ee.Authenticate()
    try:
        ee.Initialize(**ee_kwargs)
    except Exception:
        ee.Initialize(**{**ee_kwargs, "project": project or "earthengine-legacy"})


def _download_tile(url: str, dest: Path, chunk: int = 1 << 20):
    """Stream-download a URL to a local file."""
    import requests
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for part in r.iter_content(chunk_size=chunk):
                if part:
                    f.write(part)


def download_viirs_ee(
    years: List[int],
    out_dir: Path,
    band: str = "avg_rad",
    scale: int = 500,
    crs: str = "EPSG:4326",
    project: str | None = None,
    sa_key_path: str | None = None,
) -> List[Path]:
    """Download annual VIIRS composites via Earth Engine.

    For each year, takes the **median** of the 12 monthly avg_rad images,
    clips to India, and writes a GeoTIFF.
    """
    import ee

    _ee_init(project=project, sa_key_path=sa_key_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    west, south, east, north = INDIA_BBOX
    mid_lat = (south + north) / 2
    mid_lon = (west + east) / 2
    tiles = [
        ("NW", [west, mid_lat, mid_lon, north]),
        ("NE", [mid_lon, mid_lat, east, north]),
        ("SW", [west, south, mid_lon, mid_lat]),
        ("SE", [mid_lon, south, east, mid_lat]),
    ]

    downloaded: List[Path] = []

    for year in tqdm(years, desc="EE VIIRS download"):
        dest = out_dir / f"VIIRS_{year}.tif"
        if dest.exists():
            rprint(f"[dim]Skip (exists):[/dim] {dest}")
            downloaded.append(dest)
            continue

        start_date = f"{year}-01-01"
        end_date = f"{year + 1}-01-01"

        col = (
            ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG")
            .filterDate(start_date, end_date)
            .select(band)
        )
        annual = col.median()

        tile_paths: List[Path] = []
        for label, bbox in tiles:
            tile_rect = ee.Geometry.Rectangle(bbox)
            clipped = annual.clip(tile_rect)
            url = clipped.getDownloadURL({
                "scale": scale,
                "crs": crs,
                "region": tile_rect,
                "format": "GEO_TIFF",
                "filePerBand": False,
            })
            tile_path = out_dir / f"_tile_{year}_{label}.tif"
            rprint(f"[cyan]Downloading {year} tile {label}...[/cyan]")
            _download_tile(url, tile_path)
            tile_paths.append(tile_path)
            time.sleep(0.5)

        _merge_tiles(tile_paths, dest)
        for tp in tile_paths:
            tp.unlink(missing_ok=True)

        rprint(f"[green]Saved:[/green] {dest}")
        downloaded.append(dest)

    return downloaded


def _merge_tiles(tile_paths: List[Path], dest: Path):
    """Merge multiple GeoTIFF tiles into a single raster."""
    import rasterio
    from rasterio.merge import merge

    datasets = [rasterio.open(p) for p in tile_paths]
    try:
        mosaic, out_transform = merge(datasets)
        profile = datasets[0].profile.copy()
        profile.update({
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
        })
        dest.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(dest, "w", **profile) as dst:
            dst.write(mosaic)
    finally:
        for ds in datasets:
            ds.close()


# ---------------------------------------------------------------------------
# Strategy B: EOG direct download  (fallback)
# ---------------------------------------------------------------------------

def _clip_raster_to_india(src_path: Path, dst_path: Path):
    """Clip a global GeoTIFF to the India bounding box using rasterio."""
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.transform import from_bounds as transform_from_bounds

    with rasterio.open(src_path) as src:
        window = from_bounds(*INDIA_BBOX, transform=src.transform)
        data = src.read(1, window=window)
        win_transform = src.window_transform(window)

        profile = src.profile.copy()
        profile.update({
            "height": data.shape[0],
            "width": data.shape[1],
            "transform": win_transform,
        })

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(dst_path, "w", **profile) as dst:
            dst.write(data, 1)


def download_viirs_eog(
    years: List[int],
    out_dir: Path,
    eog_base_url: str,
    product_band: str = "average",
) -> List[Path]:
    """Download annual VNL composites from EOG and clip to India.

    The EOG file-naming convention changes between versions. This function
    tries the VNL v2.2 naming pattern. If it fails, the error message
    guides the user to check the EOG site for updated URLs.
    """
    import requests

    out_dir.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []

    for year in tqdm(years, desc="EOG VIIRS download"):
        dest = out_dir / f"VIIRS_{year}.tif"
        if dest.exists():
            rprint(f"[dim]Skip (exists):[/dim] {dest}")
            downloaded.append(dest)
            continue

        tile_url = (
            f"{eog_base_url.rstrip('/')}/{year}/"
            f"VNL_v22_npp_{year}0101-{year}1231_global_vcmslcfg_c202303062300."
            f"{product_band}_masked.dat.tif.gz"
        )

        rprint(f"[cyan]Trying EOG URL for {year}:[/cyan] {tile_url}")

        tmp_gz = out_dir / f"_tmp_vnl_{year}.tif.gz"
        tmp_raw = out_dir / f"_tmp_vnl_{year}_global.tif"
        try:
            _download_tile(tile_url, tmp_gz)
        except requests.HTTPError as exc:
            rprint(
                f"[red]EOG download failed for {year}:[/red] {exc}\n"
                "Check https://eogdata.mines.edu/products/vnl/ for the correct URL pattern."
            )
            continue

        import gzip
        import shutil
        with gzip.open(tmp_gz, "rb") as gz_in, open(tmp_raw, "wb") as raw_out:
            shutil.copyfileobj(gz_in, raw_out)
        tmp_gz.unlink(missing_ok=True)

        rprint(f"[cyan]Clipping to India...[/cyan]")
        _clip_raster_to_india(tmp_raw, dest)
        tmp_raw.unlink(missing_ok=True)

        rprint(f"[green]Saved:[/green] {dest}")
        downloaded.append(dest)

    return downloaded


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------

def download_viirs(
    years: List[int],
    out_dir: Path,
    use_earth_engine: bool = True,
    eog_base_url: Optional[str] = None,
    product_band: str = "average",
    ee_scale: int = 500,
    ee_project: Optional[str] = None,
    ee_sa_key: Optional[str] = None,
) -> List[Path]:
    """Download VIIRS annual rasters using the configured strategy."""
    if use_earth_engine:
        return download_viirs_ee(
            years, out_dir, scale=ee_scale,
            project=ee_project, sa_key_path=ee_sa_key,
        )

    if eog_base_url is None:
        raise ValueError(
            "eog_base_url must be set in config when use_earth_engine is false"
        )
    return download_viirs_eog(years, out_dir, eog_base_url, product_band)
