# GEE utilities
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import ee
import geemap
from tqdm import tqdm

from micro_fulfillment_network_jakarta.config import Settings, get_settings
from micro_fulfillment_network_jakarta.logger import get_logger


def initialize_earth_engine(settings: Settings | None = None, allow_interactive: bool = False):
    """Initialize Google Earth Engine using service account credentials with optional interactive fallback."""
    logger = get_logger("gee_utils")
    settings = settings or get_settings()

    key_file = Path(settings.gee_key_file)

    try:
        if key_file.exists():
            logger.info("Initializing Earth Engine with service account credentials.")
            credentials = ee.ServiceAccountCredentials(settings.gee_service_account, str(key_file))
            ee.Initialize(credentials, project=settings.gee_project_id)
        else:
            if not allow_interactive:
                raise FileNotFoundError(f"GEE key file not found: {key_file}")
            logger.warning(f"GEE key file not found at {key_file}. Falling back to interactive authentication.")

            ee.Authenticate()
            ee.Initialize(project=settings.gee_project_id)

        ee.Number(1).getInfo()
        logger.info("Earth Engine initialized successfully.")
        return ee
    except Exception as exc:
        logger.exception(f"Failed to initialize Earth Engine: {exc}")
        raise


def wait_for_task(task: Any, description: str, poll_seconds: int = 20) -> None:
    """Wait for an Earth Engine export task to complete."""
    logger = get_logger("gee_utils")
    logger.info(f"Monitoring Earth Engine task: {description}")

    with tqdm(desc=description, unit="poll") as progress:
        while task.active():
            time.sleep(poll_seconds)
            progress.update(1)

    status = task.status()
    state = status.get("state", "UNKNOWN")
    logger.info(f"Earth Engine task finished with state: {state}")

    if state != "COMPLETED":
        raise RuntimeError(f"Earth Engine task failed: {status}")


def download_ee_image(
    image: Any,
    output_path: Path,
    region: Any,
    scale: float,
    crs: str,
    overwrite: bool = False,
) -> Path:
    """Download an Earth Engine image as GeoTIFF using geemap."""
    logger = get_logger("gee_utils")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not overwrite:
        logger.info(f"Using cached file from {output_path}")
        return output_path

    logger.info(f"Downloading and pre-processing fresh from Google Earth Engine to {output_path}")
    geemap.ee_export_image(
        image,
        filename=str(output_path),
        scale=scale,
        crs=crs,
        region=region,
        file_per_band=False,
    )
    return output_path


def geojson_geometry_to_ee(geojson_geometry: dict) -> Any:
    """Convert a GeoJSON geometry dictionary to an Earth Engine geometry."""
    return ee.Geometry(geojson_geometry)


def get_ee_image_collection_size(collection_id: str) -> int:
    """Return the size of a public Earth Engine image collection."""
    collection = ee.ImageCollection(collection_id)
    return int(collection.size().getInfo())
