from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.crs import CRS

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.logger import get_logger


def utc_today() -> str:
    """Return the current UTC date as YYYY-MM-DD."""
    return datetime.now(timezone.utc).date().isoformat()


def file_size_mb(path: Path) -> float | None:
    """Return file size in megabytes if the file exists."""
    if not path.exists():
        return None
    return round(path.stat().st_size / (1024 * 1024), 3)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON file using UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file using UTF-8 encoding."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    """Write a UTF-8 text file with LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def append_text(path: Path, content: str) -> None:
    """Append UTF-8 text with LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(content)


def write_metadata(
    data_path: Path,
    dataset_name: str,
    source: str,
    source_url: str,
    license_name: str,
    spatial_resolution: str,
    temporal_coverage: str,
    preprocessing_steps: list[str],
    unit: str,
    citation_apa: str,
    citation_bibtex: str,
    crs: str,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write a metadata JSON file next to a dataset."""
    metadata_path = data_path.with_suffix(data_path.suffix + ".metadata.json")
    payload: dict[str, Any] = {
        "dataset_name": dataset_name,
        "source": source,
        "source_url": source_url,
        "license": license_name,
        "access_date": utc_today(),
        "spatial_resolution": spatial_resolution,
        "temporal_coverage": temporal_coverage,
        "preprocessing_steps": preprocessing_steps,
        "unit": unit,
        "citation_apa": citation_apa,
        "citation_bibtex": citation_bibtex,
        "file_size_mb": file_size_mb(data_path),
        "crs": crs,
    }
    if extra:
        payload.update(extra)
    write_json(metadata_path, payload)
    return metadata_path


def read_vector(path: Path) -> gpd.GeoDataFrame:
    """Read a vector dataset and validate existence."""
    if not path.exists():
        raise FileNotFoundError(f"Vector file not found: {path}")
    return gpd.read_file(path)


def write_vector(gdf: gpd.GeoDataFrame, path: Path, driver: str | None = None) -> Path:
    """Write a GeoDataFrame to disk."""
    logger = get_logger("data_io")
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing vector dataset to {path}")
    if driver:
        gdf.to_file(path, driver=driver)
    else:
        gdf.to_file(path)
    return path


def write_csv(frame: pd.DataFrame, path: Path) -> Path:
    """Write a DataFrame as CSV."""
    logger = get_logger("data_io")
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing CSV table to {path}")
    frame.to_csv(path, index=False, encoding="utf-8")
    return path


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV file with validation."""
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    return pd.read_csv(path)


def get_raster_crs(path: Path) -> str:
    """Return the CRS string for a raster file."""
    if not path.exists():
        raise FileNotFoundError(f"Raster file not found: {path}")
    with rasterio.open(path) as dataset:
        crs: CRS | None = dataset.crs
        return crs.to_string() if crs else "UNKNOWN"


def compute_data_folder_size_gb() -> float:
    """Compute total size of the data folder in gigabytes."""
    settings = get_settings()
    data_dir = settings.project_root / "data"
    if not data_dir.exists():
        return 0.0
    total_bytes = sum(path.stat().st_size for path in data_dir.rglob("*") if path.is_file())
    return round(total_bytes / (1024**3), 4)


def assert_storage_cap() -> None:
    """Raise an error when the data folder exceeds the project storage cap."""
    settings = get_settings()
    size_gb = compute_data_folder_size_gb()
    if size_gb > settings.storage_cap_gb:
        raise RuntimeError(
            f"Data folder exceeds storage cap: {size_gb} GB > {settings.storage_cap_gb} GB"
        )
