from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.analysis import pearson_correlation_with_pvalue
from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_csv, write_metadata
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe


def main() -> None:
    """Run cross-check validation of demand proxy against administrative population structure."""
    settings = get_settings()
    logger = get_logger("15_validation_crosscheck")

    clusters_path = require_file(settings.processed_dir / "demand_clusters.gpkg")
    admin_path = require_file(settings.raw_dir / "gadm_aoi" / "greater_jakarta_gadm_level2.geojson")

    output_path = settings.processed_dir / "validation_crosscheck.csv"
    table_output_path = settings.tables_dir / "validation_crosscheck.csv"
    admin_summary_path = settings.tables_dir / "admin_unit_demand_summary.csv"

    if output_path.exists() and admin_summary_path.exists():
        logger.info(f"Using cached file from {output_path}")
        logger.info(f"Using cached file from {admin_summary_path}")
        return

    grid = gpd.read_file(clusters_path, layer="demand_clusters").to_crs(settings.projected_crs)
    admin = gpd.read_file(admin_path).to_crs(settings.projected_crs)

    validate_geodataframe(grid, required_columns=["cell_id", "demand_index", "population_count"])
    validate_geodataframe(admin, required_columns=["NAME_1", "NAME_2"])

    grid_points = grid.copy()
    grid_points["geometry"] = grid_points.geometry.centroid

    joined = gpd.sjoin(
        grid_points,
        admin[["NAME_1", "NAME_2", "geometry"]],
        how="left",
        predicate="within",
    )

    admin_summary = (
        joined.dropna(subset=["NAME_1", "NAME_2"])
        .groupby(["NAME_1", "NAME_2"], as_index=False)
        .agg(
            cell_count=("cell_id", "count"),
            total_population_proxy=("population_count", "sum"),
            total_demand_index=("demand_index", "sum"),
            mean_demand_index=("demand_index", "mean"),
            total_proxy_deliveries_per_100k=("proxy_deliveries_per_100k", "sum"),
            mean_underserved_score=("underserved_score", "mean"),
            high_high_demand_lisa_count=("demand_index_lisa_cluster", lambda s: int((s == "High-High").sum())),
            high_high_underserved_lisa_count=(
            "underserved_score_lisa_cluster", lambda s: int((s == "High-High").sum())),
        )
        .copy()
    )

    admin_summary = admin_summary.dropna(subset=["NAME_1", "NAME_2"]).copy()

    admin_summary["demand_per_1000_population_proxy"] = np.where(
        admin_summary["total_population_proxy"] > 0,
        admin_summary["total_demand_index"] / admin_summary["total_population_proxy"] * 1000.0,
        np.nan,
    )

    corr_population_demand = pearson_correlation_with_pvalue(
        admin_summary["total_population_proxy"],
        admin_summary["total_demand_index"],
    )
    corr_population_proxy_delivery = pearson_correlation_with_pvalue(
        admin_summary["total_population_proxy"],
        admin_summary["total_proxy_deliveries_per_100k"],
    )

    validation = pd.DataFrame(
        [
            {
                "validation_check": "admin_population_vs_total_demand_index",
                "pearson_r": corr_population_demand["r"],
                "p_value": corr_population_demand["p_value"],
                "interpretation": "High positive correlation indicates the demand proxy remains broadly consistent with population structure while still allowing urban activity and accessibility variation.",
            },
            {
                "validation_check": "admin_population_vs_proxy_deliveries_per_100k",
                "pearson_r": corr_population_proxy_delivery["r"],
                "p_value": corr_population_proxy_delivery["p_value"],
                "interpretation": "This checks whether normalized proxy deliveries maintain plausible administrative-scale alignment with population distribution.",
            },
        ]
    )

    write_csv(validation, output_path)
    write_csv(validation, table_output_path)
    write_csv(admin_summary, admin_summary_path)

    write_metadata(
        data_path=output_path,
        dataset_name="Demand proxy validation cross-check",
        source="Derived from demand clusters and GADM administrative units",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution="Administrative unit level 2 summary",
        temporal_coverage="Composite validation using project demand proxy",
        preprocessing_steps=[
            "Converted demand grid to centroids",
            "Spatially joined grid centroids to GADM level 2 administrative units",
            "Aggregated population proxy, demand index, proxy deliveries, and hotspot counts",
            "Computed Pearson correlation between population proxy and demand metrics",
        ],
        unit="Correlation statistic and administrative summary",
        citation_apa="Validation cross-check derived from open geospatial data.",
        citation_bibtex="@misc{validationCrosscheck2025, title={Administrative validation cross-check for Greater Jakarta quick-commerce demand proxy}, author={Project pipeline}, year={2025}}",
        crs="Not applicable",
        extra={
            "interpretation_limit": "This is a sanity check against population structure, not validation against proprietary q-commerce orders.",
        },
    )

    logger.info("Validation cross-check completed.")
    print(f"Validation cross-check completed: {output_path}")
    print(f"Administrative demand summary completed: {admin_summary_path}")


if __name__ == "__main__":
    main()
