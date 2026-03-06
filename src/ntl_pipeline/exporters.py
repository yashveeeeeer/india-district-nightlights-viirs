from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from rich import print as rprint


def export_panel_csv(df: pd.DataFrame, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path


def export_year_geojson(districts: gpd.GeoDataFrame, year_df: pd.DataFrame, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    districts = districts.copy()
    districts["district_id"] = districts["district_id"].astype(str)
    year_df = year_df.copy()
    year_df["district_id"] = year_df["district_id"].astype(str)
    merged = districts.merge(year_df, on=["district_id"], how="left", suffixes=("", "_stats"))
    merged["year"] = year_df["year"].iloc[0] if len(year_df) else None

    # Warn if districts didn't match
    unmatched = merged["mean"].isna().sum() if "mean" in merged.columns else 0
    if unmatched > 0:
        year_val = year_df["year"].iloc[0] if len(year_df) else "unknown"
        rprint(
            f"[yellow]Warning: {unmatched}/{len(merged)} districts had no stats "
            f"match for year {year_val}[/yellow]"
        )

    merged.to_file(out_path, driver="GeoJSON")
    return out_path
