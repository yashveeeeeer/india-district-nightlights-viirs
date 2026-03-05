from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats


def compute_zonal_stats(
    districts: gpd.GeoDataFrame,
    raster_path: Path,
    year: int,
    metrics: List[str],
    nodata: float | int | None = None,
) -> pd.DataFrame:
    with rasterio.open(raster_path) as src:
        if nodata is None:
            nodata = src.nodata

    zs = zonal_stats(
        districts,
        raster_path,
        stats=metrics,
        nodata=nodata,
        geojson_out=False,
        all_touched=False,
    )

    out = pd.DataFrame(zs)
    out.insert(0, "year", year)
    out.insert(0, "district_id", districts["district_id"].astype(str).values)
    out.insert(1, "district_name", districts["district_name"].values)
    out.insert(2, "state_name", districts["state_name"].values)

    # Coverage diagnostic: proportion of pixels with valid data inside each polygon
    # rasterstats doesn't directly return pixel counts unless requested; request count + nodata count
    zs2 = zonal_stats(
        districts,
        raster_path,
        stats=["count"],
        nodata=nodata,
        geojson_out=False,
        all_touched=False,
    )
    counts = pd.DataFrame(zs2)["count"].astype(float)
    out["valid_pixel_count"] = counts

    # total_pixel_count isn't available without a second pass; approximate via all pixels with nodata excluded
    # If you need precise shares, compute a mask-based count with rasterio.features.geometry_mask.
    out["valid_pixel_share"] = np.nan

    # Interpretable transforms
    for col in ["mean", "median"]:
        if col in out.columns:
            out[f"log1p_{col}"] = np.log1p(out[col].astype(float))

    return out
