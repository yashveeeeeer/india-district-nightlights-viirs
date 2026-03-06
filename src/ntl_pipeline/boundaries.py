from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from .config import Config
from .io import download_file, unzip_to_bytes


def download_datameet_boundaries(cfg: Config, raw_dir: Path) -> Path:
    url = cfg.get("boundaries", "datameet_zip_url")
    rel = cfg.get("boundaries", "datameet_districts_relpath")
    zip_path = raw_dir / "boundaries" / "datameet_maps_master.zip"
    shp_out_dir = raw_dir / "boundaries" / "datameet_districts_2011"

    if not zip_path.exists():
        download_file(url, zip_path)

    # Extract all sidecar files for the shapefile (.shp/.shx/.dbf/.prj/.cpg)
    with unzip_to_bytes(zip_path) as z:
        base = rel[:-4]  # prefix up to .shp extension
        members = [m for m in z.namelist() if m.startswith(base)]
        if not members:
            raise FileNotFoundError(f"Could not find {rel} inside {zip_path}")
        for m in members:
            out_path = shp_out_dir / Path(m).name
            if not out_path.exists():
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with z.open(m) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())

    shp_path = shp_out_dir / Path(rel).name
    if not shp_path.exists():
        raise FileNotFoundError(f"Expected shapefile at {shp_path}")
    return shp_path


def load_districts(shp_path: Path, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(crs)
    else:
        gdf = gdf.to_crs(crs)

    # Normalize district ID
    id_candidates = ["censuscode", "DIST_CODE", "DT_CEN_CD"]
    for col in id_candidates:
        if col in gdf.columns:
            gdf["district_id"] = gdf[col].astype(str)
            break
    else:
        gdf["district_id"] = gdf.index.astype(str)

    # Normalize district name
    name_candidates = ["DISTRICT", "DIST_NAME", "NAME_2"]
    for col in name_candidates:
        if col in gdf.columns:
            gdf["district_name"] = gdf[col]
            break
    else:
        gdf["district_name"] = gdf["district_id"]

    # Normalize state name
    state_candidates = ["ST_NM", "STATE", "ST_NAME", "NAME_1"]
    for col in state_candidates:
        if col in gdf.columns:
            gdf["state_name"] = gdf[col]
            break
    else:
        gdf["state_name"] = None

    return gdf[["district_id", "district_name", "state_name", "geometry"]].copy()
