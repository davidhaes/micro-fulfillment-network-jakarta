from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from esda.moran import Moran, Moran_Local
from libpysal.weights import KNN, Queen


def build_knn_weights(gdf: gpd.GeoDataFrame, k: int = 8):
    """Build K-nearest-neighbor spatial weights."""
    weights = KNN.from_dataframe(gdf, k=k)
    weights.transform = "r"
    return weights


def build_queen_weights(gdf: gpd.GeoDataFrame):
    """Build Queen contiguity spatial weights."""
    weights = Queen.from_dataframe(gdf)
    weights.transform = "r"
    return weights


def clean_spatial_metric_frame(gdf: gpd.GeoDataFrame, value_column: str) -> gpd.GeoDataFrame:
    """Return a clean GeoDataFrame containing finite metric values and valid geometries."""
    if value_column not in gdf.columns:
        raise KeyError(f"Missing value column: {value_column}")
    if gdf.crs is None:
        raise ValueError("GeoDataFrame CRS is required for spatial statistics.")

    clean = gdf[[value_column, "geometry"]].copy()
    clean[value_column] = pd.to_numeric(clean[value_column], errors="coerce")
    clean = clean[np.isfinite(clean[value_column].to_numpy())].copy()
    clean = clean[clean.geometry.notna() & clean.geometry.is_valid & ~clean.geometry.is_empty].copy()

    if clean.empty:
        raise ValueError(f"No valid observations available for metric: {value_column}")

    return clean


def compute_global_moran(
    gdf: gpd.GeoDataFrame,
    value_column: str,
    k: int = 8,
    permutations: int = 999,
) -> dict[str, float | str | int]:
    """Compute Global Moran's I using KNN weights."""
    clean = clean_spatial_metric_frame(gdf, value_column)

    if len(clean) <= k:
        raise ValueError(f"Not enough observations for KNN Moran analysis: n={len(clean)}, k={k}")

    weights = build_knn_weights(clean, k=k)
    values = clean[value_column].astype(float).to_numpy()
    moran = Moran(values, weights, permutations=permutations)

    return {
        "metric": value_column,
        "moran_i": float(moran.I),
        "expected_i": float(moran.EI),
        "p_value": float(moran.p_sim),
        "z_score": float(moran.z_sim),
        "permutations": int(permutations),
        "weight_type": f"KNN k={k}",
        "observation_count": int(len(clean)),
    }


def lisa_label(quadrant: int, p_value: float, alpha: float = 0.05) -> str:
    """Convert Local Moran quadrant and p-value into a readable LISA label."""
    if not np.isfinite(p_value) or p_value > alpha:
        return "Not significant"
    if quadrant == 1:
        return "High-High"
    if quadrant == 2:
        return "Low-High"
    if quadrant == 3:
        return "Low-Low"
    if quadrant == 4:
        return "High-Low"
    return "Not significant"


def compute_lisa_clusters(
    gdf: gpd.GeoDataFrame,
    value_column: str,
    k: int = 8,
    permutations: int = 999,
    alpha: float = 0.05,
) -> gpd.GeoDataFrame:
    """Compute Local Moran's I and classify LISA clusters."""
    output = gdf.copy()
    clean = clean_spatial_metric_frame(output, value_column)

    if len(clean) <= k:
        raise ValueError(f"Not enough observations for KNN LISA analysis: n={len(clean)}, k={k}")

    weights = build_knn_weights(clean, k=k)
    values = clean[value_column].astype(float).to_numpy()
    lisa = Moran_Local(values, weights, permutations=permutations)

    clean["local_moran_i"] = lisa.Is
    clean["local_moran_p"] = lisa.p_sim
    clean["lisa_quadrant"] = lisa.q
    clean["lisa_cluster"] = [
        lisa_label(int(q), float(p), alpha=alpha)
        for q, p in zip(lisa.q, lisa.p_sim)
    ]

    output = output.join(
        clean[["local_moran_i", "local_moran_p", "lisa_quadrant", "lisa_cluster"]],
        how="left",
    )
    output["lisa_cluster"] = output["lisa_cluster"].fillna("Not evaluated")
    return output


def moran_results_to_frame(results: list[dict[str, float | str | int]]) -> pd.DataFrame:
    """Convert Moran result dictionaries to a DataFrame."""
    return pd.DataFrame(results)
