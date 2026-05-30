from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_csv, write_metadata
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.spatial_stats import (
    compute_global_moran,
    compute_lisa_clusters,
    moran_results_to_frame,
)
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe


GENERIC_LISA_COLUMNS = ["local_moran_i", "local_moran_p", "lisa_quadrant", "lisa_cluster"]


def drop_generic_lisa_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Drop generic LISA columns before computing another metric."""
    drop_cols = [column for column in GENERIC_LISA_COLUMNS if column in gdf.columns]
    if drop_cols:
        return gdf.drop(columns=drop_cols)
    return gdf


def main() -> None:
    """Compute spatial autocorrelation diagnostics for demand and underserved scores."""
    settings = get_settings()
    logger = get_logger("12_spatial_autocorrelation")

    service_path = require_file(settings.processed_dir / "service_coverage.gpkg")
    lisa_path = settings.processed_dir / "demand_underserved_lisa.gpkg"
    moran_path = settings.processed_dir / "spatial_autocorrelation.csv"
    moran_table_path = settings.tables_dir / "spatial_autocorrelation.csv"

    if lisa_path.exists() and moran_path.exists():
        logger.info(f"Using cached file from {lisa_path}")
        logger.info(f"Using cached file from {moran_path}")
        return

    grid = gpd.read_file(service_path, layer="service_coverage")
    validate_geodataframe(grid, required_columns=["demand_index", "underserved_score"])

    metrics = ["demand_index", "underserved_score"]
    moran_results = []
    lisa_grid = grid.copy()

    for metric in metrics:
        logger.info(f"Computing Global Moran's I for {metric}.")
        moran_results.append(compute_global_moran(lisa_grid, metric, k=8, permutations=999))

        logger.info(f"Computing LISA clusters for {metric}.")
        base_for_lisa = drop_generic_lisa_columns(lisa_grid)
        lisa_result = compute_lisa_clusters(base_for_lisa, metric, k=8, permutations=999, alpha=0.05)

        lisa_grid[f"{metric}_local_moran_i"] = lisa_result["local_moran_i"]
        lisa_grid[f"{metric}_local_moran_p"] = lisa_result["local_moran_p"]
        lisa_grid[f"{metric}_lisa_quadrant"] = lisa_result["lisa_quadrant"]
        lisa_grid[f"{metric}_lisa_cluster"] = lisa_result["lisa_cluster"]

    lisa_grid = drop_generic_lisa_columns(lisa_grid)
    moran_frame = moran_results_to_frame(moran_results)

    lisa_grid.to_file(lisa_path, driver="GPKG", layer="lisa")
    write_csv(moran_frame, moran_path)
    write_csv(moran_frame, moran_table_path)

    write_metadata(
        data_path=lisa_path,
        dataset_name="LISA clusters for demand and underserved quick-commerce proxy",
        source="Derived from service coverage grid",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m grid",
        temporal_coverage="Scenario-based spatial statistics",
        preprocessing_steps=[
            "Loaded service coverage grid",
            "Computed KNN spatial weights with k=8",
            "Computed Local Moran's I with 999 permutations",
            "Classified LISA clusters into High-High, Low-Low, High-Low, Low-High, and Not significant",
        ],
        unit="Local Moran's I and cluster label",
        citation_apa="Anselin, L. (1995). Local indicators of spatial association, LISA. Geographical Analysis.",
        citation_bibtex="@article{anselin1995lisa, title={Local indicators of spatial association, LISA}, author={Anselin, Luc}, journal={Geographical Analysis}, year={1995}}",
        crs=settings.projected_crs,
    )

    write_metadata(
        data_path=moran_path,
        dataset_name="Global Moran's I spatial autocorrelation diagnostics",
        source="Derived from service coverage grid",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m grid",
        temporal_coverage="Scenario-based spatial statistics",
        preprocessing_steps=[
            "Loaded demand index and underserved score",
            "Built KNN spatial weights with k=8",
            "Computed Global Moran's I with 999 permutations",
        ],
        unit="Moran's I statistic, z-score, and p-value",
        citation_apa="Moran, P. A. P. (1950). Notes on continuous stochastic phenomena. Biometrika.",
        citation_bibtex="@article{moran1950, title={Notes on continuous stochastic phenomena}, author={Moran, P. A. P.}, journal={Biometrika}, year={1950}}",
        crs="Not applicable",
    )

    logger.info("Spatial autocorrelation analysis completed.")
    print(f"LISA output completed: {lisa_path}")
    print(f"Moran table completed: {moran_path}")


if __name__ == "__main__":
    main()
