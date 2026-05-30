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


WORLDPOP_COLLECTION = "WorldPop/GP/100m/pop"


def load_aoi_geometry() -> tuple[gpd.GeoDataFrame, dict]:
    """Load AOI GeoJSON and return GeoDataFrame plus GeoJSON geometry."""
    settings = get_settings()
    aoi_path = require_file(settings.aoi_dir / "aoi_default.geojson")
    aoi = gpd.read_file(aoi_path).to_crs(settings.default_crs)
    geometry = json.loads(aoi.to_json())["features"][0]["geometry"]
    return aoi, geometry


def get_latest_worldpop_image() -> tuple[ee.Image, int]:
    """Return the latest available WorldPop image for Indonesia."""
    collection = (
        ee.ImageCollection(WORLDPOP_COLLECTION)
        .filter(ee.Filter.eq("country", "IDN"))
        .sort("year", False)
    )
    image = ee.Image(collection.first())
    year = int(image.get("year").getInfo())
    return image.select("population").setDefaultProjection(crs="EPSG:4326", scale=92.77), year
#


def main() -> None:
    """Fetch preprocessed WorldPop population raster for the project AOI."""
    settings = get_settings()
    logger = get_logger("04_fetch_worldpop")

    output_path = settings.raw_dir / "worldpop_population" / "worldpop_population_1km_utm48s.tif"

    if output_path.exists():
        logger.info(f"Using cached file from {output_path}")
        validate_raster(output_path, expected_crs=settings.projected_crs)
        return

    logger.info("Downloading and pre-processing fresh from WorldPop via Google Earth Engine.")
    initialize_earth_engine(settings=settings, allow_interactive=True)

    _, geometry = load_aoi_geometry()
    ee_geometry = ee.Geometry(geometry)

    population_image, latest_year = get_latest_worldpop_image()

    aggregated = (
        population_image
        .clip(ee_geometry)
        .rename("population_count")
    )

    download_ee_image(
        image=aggregated,
        output_path=output_path,
        region=ee_geometry,
        scale=settings.analysis_grid_size_meters,
        crs=settings.projected_crs,
        overwrite=False,
    )

    validate_raster(output_path, expected_crs=settings.projected_crs)

    write_metadata(
        data_path=output_path,
        dataset_name="WorldPop population count aggregated to 1 km",
        source="WorldPop via Google Earth Engine",
        source_url="https://developers.google.com/earth-engine/datasets/catalog/WorldPop_GP_100m_pop",
        license_name="WorldPop open data license",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m analysis grid aggregated from approximately 100 m source",
        temporal_coverage=str(latest_year),
        preprocessing_steps=[
            "Filtered WorldPop collection to Indonesia",
            "Selected latest available year in the Earth Engine collection",
            "Aggregated population count to 1 km using sum reducer",
            "Clipped raster to Greater Jakarta AOI",
            "Reprojected raster to EPSG:32748",
        ],
        unit="persons per analysis cell",
        citation_apa="WorldPop. (2020). Global high resolution population denominators project. University of Southampton.",
        citation_bibtex="@misc{worldpop2020, title={Global high resolution population denominators project}, author={{WorldPop}}, year={2020}, url={https://www.worldpop.org/}}",
        crs=settings.projected_crs,
        extra={
            "gee_collection": WORLDPOP_COLLECTION,
            "latest_available_year_used": latest_year,
            "storage_cap_strategy": "Aggregated to 1 km to keep data folder below 10 GB and match facility location analysis scale.",
        },
    )

    logger.info(f"WorldPop raster written to {output_path}")
    print(f"WorldPop completed: {output_path}")


if __name__ == "__main__":
    main()
