from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.gee_utils import initialize_earth_engine
from micro_fulfillment_network_jakarta.logger import get_logger


def main() -> None:
    """Validate Google Earth Engine authentication and public dataset access."""
    logger = get_logger("setup_gee_auth")
    settings = get_settings()

    logger.info("Starting Google Earth Engine authentication validation.")
    logger.info(f"Project root: {settings.project_root}")
    logger.info(f"GEE project ID: {settings.gee_project_id}")
    logger.info(f"GEE key file path: {settings.gee_key_file}")

    ee = initialize_earth_engine(settings=settings, allow_interactive=True)

    image_collection = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG")
    collection_size = image_collection.limit(1).size().getInfo()

    if int(collection_size) >= 1:
        logger.info("Google Earth Engine authentication succeeded.")
        logger.info("Public dataset access test succeeded for NOAA VIIRS monthly VCMCFG.")
        print("GEE authentication succeeded.")
        print(f"Initialized project: {settings.gee_project_id}")
    else:
        raise RuntimeError("GEE initialized, but public dataset access returned no images.")


if __name__ == "__main__":
    main()
