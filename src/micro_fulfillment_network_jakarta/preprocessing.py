from __future__ import annotations

import numpy as np
import pandas as pd
import rasterio
import rioxarray
import xarray as xr
from rasterio.enums import Resampling


def min_max_scale(values: np.ndarray | pd.Series, lower_percentile: float = 1.0, upper_percentile: float = 99.0) -> np.ndarray:
    """Scale values to the 0 to 1 range using percentile clipping for robustness."""
    array = np.asarray(values, dtype=float)
    result = np.zeros_like(array, dtype=float)

    valid = np.isfinite(array)
    if not valid.any():
        return result

    low = np.nanpercentile(array[valid], lower_percentile)
    high = np.nanpercentile(array[valid], upper_percentile)

    if np.isclose(high, low):
        result[valid] = 0.0
        return result

    clipped = np.clip(array, low, high)
    result[valid] = (clipped[valid] - low) / (high - low)
    result[~valid] = np.nan
    return result


def safe_log1p(values: np.ndarray | pd.Series) -> np.ndarray:
    """Apply log1p transformation after clipping negative values to zero."""
    array = np.asarray(values, dtype=float)
    array = np.where(np.isfinite(array), array, np.nan)
    array = np.where(array < 0, 0, array)
    return np.log1p(array)


def weighted_overlay(frame: pd.DataFrame, columns: list[str], weights: list[float], output_column: str) -> pd.DataFrame:
    """Compute a weighted overlay index from normalized columns."""
    if len(columns) != len(weights):
        raise ValueError("Columns and weights must have equal length.")
    if not np.isclose(sum(weights), 1.0):
        raise ValueError("Weights must sum to 1.0.")

    output = frame.copy()
    score = np.zeros(len(output), dtype=float)
    for column, weight in zip(columns, weights):
        if column not in output.columns:
            raise KeyError(f"Missing column for weighted overlay: {column}")
        score += output[column].astype(float).to_numpy() * float(weight)

    output[output_column] = score
    return output


def open_raster_as_xarray(path: str) -> xr.DataArray:
    """Open a raster file as an xarray DataArray using rioxarray."""
    return rioxarray.open_rasterio(path, masked=True)


def resample_raster_to_match(source_path: str, match_path: str, output_path: str, resampling: Resampling = Resampling.bilinear) -> str:
    """Resample a raster to match another raster grid."""
    with rasterio.open(match_path) as match:
        dst_crs = match.crs
        dst_transform = match.transform
        dst_height = match.height
        dst_width = match.width

    with rasterio.open(source_path) as src:
        data = src.read(
            out_shape=(src.count, dst_height, dst_width),
            resampling=resampling,
        )
        profile = src.profile.copy()
        profile.update(
            {
                "crs": dst_crs,
                "transform": dst_transform,
                "height": dst_height,
                "width": dst_width,
            }
        )

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(data)

    return output_path
