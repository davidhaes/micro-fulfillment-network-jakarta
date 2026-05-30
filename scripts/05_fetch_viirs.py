from __future__ import annotations

import json
import sys
from pathlib import Path

import ee
import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_metadata
from micro_fulfillment_network_jakarta.gee_utils import download_ee_image, initialize_earth_engine
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import require_file, validate_raster


VIIRS_COLLECTION = "NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG"
TARGET_YEAR = 2024


def load_aoi_geometry() -> dict:
    """Load AOI geometry as GeoJSON geometry dictionary."""
    settings = get_settings()
    aoi_path = require_file(settings.aoi_dir / "aoi_default.geojson")
    aoi = gpd.read_file(aoi_path).to_crs(settings.default_crs)
    return json.loads(aoi.to_json())["features"][0]["geometry"]


def build_viirs_annual_mean(year: int) -> ee.Image:
    """Build a VIIRS annual mean nighttime lights image."""
    start = f"{year}-01-01"
    end = f"{year + 1}-01-01"
    collection = (
        ee.ImageCollection(VIIRS_COLLECTION)
        .filterDate(start, end)
        .select("avg_rad")
    )
    count = int(collection.size().getInfo())

    if count == 0:
        raise ValueError(f"No VIIRS monthly images found for year {year}.")

    image = (
        collection.mean()
        .max(ee.Image.constant(0))
        .rename("nighttime_lights_avg_rad")
    )

    return image


def main() -> None:
    """Fetch preprocessed VIIRS nighttime lights raster for the project AOI."""
    settings = get_settings()
    logger = get_logger("05_fetch_viirs")

    output_path = settings.raw_dir / "viirs_nighttime_lights" / f"viirs_nighttime_lights_{TARGET_YEAR}_mean_1km_utm48s.tif"

    if output_path.exists():
        logger.info(f"Using cached file from {output_path}")
        validate_raster(output_path, expected_crs=settings.projected_crs)
        return

    logger.info("Downloading and pre-processing fresh from VIIRS via Google Earth Engine.")
    initialize_earth_engine(settings=settings, allow_interactive=True)

    geometry = load_aoi_geometry()
    ee_geometry = ee.Geometry(geometry)

    viirs = (
        build_viirs_annual_mean(TARGET_YEAR)
        .clip(ee_geometry)  # clip dulu
    )

    download_ee_image(
        image=viirs,
        output_path=output_path,
        region=ee_geometry,
        scale=settings.analysis_grid_size_meters,  # resampling ke 1km terjadi di sini
        crs=settings.projected_crs,
        overwrite=False,
    )

    validate_raster(output_path, expected_crs=settings.projected_crs)

    write_metadata(
        data_path=output_path,
        dataset_name="VIIRS nighttime lights annual mean",
        source="NOAA VIIRS DNB monthly VCMCFG via Google Earth Engine",
        source_url="https://developers.google.com/earth-engine/datasets/catalog/NOAA_VIIRS_DNB_MONTHLY_V1_VCMCFG",
        license_name="Public domain, NOAA open data",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m analysis grid aggregated from approximately 500 m source",
        temporal_coverage=f"{TARGET_YEAR}-01-01 to {TARGET_YEAR}-12-31",
        preprocessing_steps=[
            "Filtered VIIRS monthly VCMCFG collection to target year",
            "Selected avg_rad band",
            "Computed annual mean composite",
            "Clipped raster to Greater Jakarta AOI",
            "Aggregated and reprojected raster to EPSG:32748 at 1 km analysis grid",
            "Clipped negative radiance values to zero",
        ],
        unit="nanoWatts per square centimeter per steradian",
        citation_apa="Elvidge, C. D., et al. (2017). VIIRS night-time lights. International Journal of Remote Sensing.",
        citation_bibtex="@article{elvidge2017viirs, title={VIIRS night-time lights}, author={Elvidge, Christopher D. and others}, journal={International Journal of Remote Sensing}, year={2017}}",
        crs=settings.projected_crs,
        extra={
            "gee_collection": VIIRS_COLLECTION,
            "target_year": TARGET_YEAR,
            "interpretation_limit": "Nighttime lights are used as an economic activity proxy and may show blooming or saturation in dense urban cores.",
        },
    )

    logger.info(f"VIIRS raster written to {output_path}")
    print(f"VIIRS completed: {output_path}")


if __name__ == "__main__":
    main()
