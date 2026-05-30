from __future__ import annotations

import json
import sys
from pathlib import Path

import ee
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_csv, write_metadata
from micro_fulfillment_network_jakarta.gee_utils import initialize_earth_engine
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import require_file


VIIRS_COLLECTION = "NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG"
START_YEAR = 2020
END_YEAR = 2024


def load_aoi_geometry() -> dict:
    """Load AOI geometry as GeoJSON dictionary."""
    settings = get_settings()
    aoi_path = require_file(settings.aoi_dir / "aoi_default.geojson")
    aoi = gpd.read_file(aoi_path).to_crs(settings.default_crs)
    return json.loads(aoi.to_json())["features"][0]["geometry"]


def annual_viirs_mean(year: int, ee_geometry) -> float:
    """Compute AOI mean VIIRS radiance for one year in Earth Engine."""
    collection = (
        ee.ImageCollection(VIIRS_COLLECTION)
        .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
        .select("avg_rad")
    )

    count = int(collection.size().getInfo())
    if count == 0:
        return float("nan")

    raw_image = collection.mean().rename("avg_rad")
    image = raw_image.where(raw_image.lt(0), 0).rename("avg_rad")

    result = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=ee_geometry,
        scale=1000,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()

    return float(result.get("avg_rad", np.nan))


def main() -> None:
    """Compute annual VIIRS nighttime lights trend for Greater Jakarta AOI."""
    settings = get_settings()
    logger = get_logger("14_temporal_trend")

    output_path = settings.processed_dir / "viirs_temporal_trend.csv"
    table_output_path = settings.tables_dir / "viirs_temporal_trend.csv"

    if output_path.exists() and table_output_path.exists():
        logger.info(f"Using cached file from {output_path}")
        logger.info(f"Using cached file from {table_output_path}")
        return

    initialize_earth_engine(settings=settings, allow_interactive=True)
    geometry = load_aoi_geometry()
    ee_geometry = ee.Geometry(geometry)

    records = []
    for year in range(START_YEAR, END_YEAR + 1):
        logger.info(f"Computing VIIRS annual mean for {year}.")
        records.append(
            {
                "year": int(year),
                "mean_viirs_avg_rad": annual_viirs_mean(year, ee_geometry),
            }
        )

    frame = pd.DataFrame(records)
    clean = frame.dropna(subset=["mean_viirs_avg_rad"]).copy()

    if len(clean) >= 3:
        tau, p_value = stats.kendalltau(clean["year"], clean["mean_viirs_avg_rad"])
        slope, intercept, lower_slope, upper_slope = stats.theilslopes(
            clean["mean_viirs_avg_rad"],
            clean["year"],
            alpha=0.95,
        )
    else:
        tau, p_value, slope, intercept, lower_slope, upper_slope = [np.nan] * 6

    frame["kendall_tau"] = float(tau) if np.isfinite(tau) else np.nan
    frame["kendall_p_value"] = float(p_value) if np.isfinite(p_value) else np.nan
    frame["sen_slope_avg_rad_per_year"] = float(slope) if np.isfinite(slope) else np.nan
    frame["sen_slope_lower_95"] = float(lower_slope) if np.isfinite(lower_slope) else np.nan
    frame["sen_slope_upper_95"] = float(upper_slope) if np.isfinite(upper_slope) else np.nan

    write_csv(frame, output_path)
    write_csv(frame, table_output_path)

    write_metadata(
        data_path=output_path,
        dataset_name="Greater Jakarta VIIRS nighttime lights temporal trend",
        source="NOAA VIIRS DNB monthly VCMCFG via Google Earth Engine",
        source_url="https://developers.google.com/earth-engine/datasets/catalog/NOAA_VIIRS_DNB_MONTHLY_V1_VCMCFG",
        license_name="Public domain, NOAA open data",
        spatial_resolution="AOI-level annual mean at 1 km reduction scale",
        temporal_coverage=f"{START_YEAR} to {END_YEAR}",
        preprocessing_steps=[
            "Filtered VIIRS monthly collection for each year",
            "Computed annual mean radiance image",
            "Reduced annual image to Greater Jakarta AOI mean",
            "Computed Kendall tau trend test",
            "Computed Sen's slope using Theil-Sen estimator",
        ],
        unit="nanoWatts per square centimeter per steradian and annual slope",
        citation_apa="Elvidge, C. D., et al. (2017). VIIRS night-time lights. International Journal of Remote Sensing.",
        citation_bibtex="@article{elvidge2017viirs, title={VIIRS night-time lights}, author={Elvidge, Christopher D. and others}, journal={International Journal of Remote Sensing}, year={2017}}",
        crs="AOI statistic, source raster processed in Earth Engine",
        extra={
            "trend_method": "Kendall tau and Sen's slope",
            "interpretation_limit": "Trend reflects nighttime light intensity, not observed quick-commerce order volume.",
        },
    )

    logger.info("Temporal trend analysis completed.")
    print(f"VIIRS temporal trend completed: {output_path}")


if __name__ == "__main__":
    main()
