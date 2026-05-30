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


DYNAMIC_WORLD_COLLECTION = "GOOGLE/DYNAMICWORLD/V1"
TARGET_YEAR = 2024


def load_aoi_geometry() -> dict:
    """Load AOI geometry as GeoJSON geometry dictionary."""
    settings = get_settings()
    aoi_path = require_file(settings.aoi_dir / "aoi_default.geojson")
    aoi = gpd.read_file(aoi_path).to_crs(settings.default_crs)
    return json.loads(aoi.to_json())["features"][0]["geometry"]


def build_dynamic_world_built_mean(year: int) -> ee.Image:
    """Build annual mean Dynamic World built probability."""
    start = f"{year}-01-01"
    end = f"{year + 1}-01-01"

    collection = (
        ee.ImageCollection(DYNAMIC_WORLD_COLLECTION)
        .filterDate(start, end)
        .select("built")
    )
    count = int(collection.size().getInfo())


    if count == 0:
        raise ValueError(f"No Dynamic World images found for year {year}.")

    return (  # ← mundurkan ke level fungsi (4 spasi, bukan 8)
        collection.mean()
        .rename("built_probability")
        .setDefaultProjection(crs="EPSG:4326", scale=10)
    )


def main() -> None:
    """Fetch preprocessed Dynamic World built probability raster."""
    settings = get_settings()
    logger = get_logger("06_fetch_dynamic_world")

    output_path = settings.raw_dir / "dynamic_world_built" / f"dynamic_world_built_probability_{TARGET_YEAR}_mean_1km_utm48s.tif"

    if output_path.exists():
        logger.info(f"Using cached file from {output_path}")
        validate_raster(output_path, expected_crs=settings.projected_crs)
        return

    logger.info("Downloading and pre-processing fresh from Dynamic World via Google Earth Engine.")
    initialize_earth_engine(settings=settings, allow_interactive=True)

    geometry = load_aoi_geometry()
    ee_geometry = ee.Geometry(geometry)

    built = (
        build_dynamic_world_built_mean(TARGET_YEAR)
        .clip(ee_geometry)
    )

    download_ee_image(
        image=built,
        output_path=output_path,
        region=ee_geometry,
        scale=settings.analysis_grid_size_meters,
        crs=settings.projected_crs,
        overwrite=False,
    )

    validate_raster(output_path, expected_crs=settings.projected_crs)

    write_metadata(
        data_path=output_path,
        dataset_name="Dynamic World built probability annual mean",
        source="Google Dynamic World V1 via Google Earth Engine",
        source_url="https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1",
        license_name="CC-BY 4.0",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m analysis grid aggregated from 10 m source",
        temporal_coverage=f"{TARGET_YEAR}-01-01 to {TARGET_YEAR}-12-31",
        preprocessing_steps=[
            "Filtered Dynamic World V1 image collection to target year",
            "Selected built probability band",
            "Computed annual mean composite",
            "Aggregated built probability to 1 km using mean reducer",
            "Clipped raster to Greater Jakarta AOI",
            "Reprojected raster to EPSG:32748",
        ],
        unit="probability from 0 to 1",
        citation_apa="Brown, C. F., et al. (2022). Dynamic World, near real-time global 10 m land use land cover mapping. Scientific Data.",
        citation_bibtex="@article{brown2022dynamic, title={Dynamic World, near real-time global 10 m land use land cover mapping}, author={Brown, Christopher F. and others}, journal={Scientific Data}, year={2022}}",
        crs=settings.projected_crs,
        extra={
            "gee_collection": DYNAMIC_WORLD_COLLECTION,
            "target_year": TARGET_YEAR,
            "interpretation_limit": "Built probability is used as an urban intensity proxy after annual averaging and 1 km aggregation.",
        },
    )

    logger.info(f"Dynamic World built raster written to {output_path}")
    print(f"Dynamic World completed: {output_path}")


if __name__ == "__main__":
    main()
