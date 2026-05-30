from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio

from micro_fulfillment_network_jakarta.data_io import assert_storage_cap


def require_file(path: Path) -> Path:
    """Require that a file exists."""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def require_directory(path: Path) -> Path:
    """Require that a directory exists."""
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Required directory not found: {path}")
    return path


def require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    """Require DataFrame columns."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def validate_geodataframe(gdf: gpd.GeoDataFrame, required_columns: list[str] | None = None) -> None:
    """Validate GeoDataFrame CRS, geometry, and required columns."""
    if gdf.empty:
        raise ValueError("GeoDataFrame is empty.")
    if gdf.crs is None:
        raise ValueError("GeoDataFrame CRS is missing.")
    if "geometry" not in gdf.columns:
        raise ValueError("GeoDataFrame has no geometry column.")
    invalid_count = int((~gdf.geometry.is_valid).sum())
    if invalid_count > 0:
        raise ValueError(f"GeoDataFrame contains invalid geometries: {invalid_count}")
    if required_columns:
        require_columns(gdf, required_columns)


def validate_raster(path: Path, expected_crs: str | None = None) -> None:
    """Validate raster existence and optional CRS."""
    require_file(path)
    with rasterio.open(path) as dataset:
        if dataset.count < 1:
            raise ValueError(f"Raster has no bands: {path}")
        if expected_crs and dataset.crs and dataset.crs.to_string() != expected_crs:
            raise ValueError(f"Unexpected raster CRS for {path}: {dataset.crs} != {expected_crs}")


def validate_metadata_for_data_file(data_path: Path) -> Path:
    """Require metadata JSON next to a data file."""
    metadata_path = data_path.with_suffix(data_path.suffix + ".metadata.json")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found for {data_path}: {metadata_path}")
    return metadata_path


def validate_storage_cap() -> None:
    """Validate project storage cap."""
    assert_storage_cap()
