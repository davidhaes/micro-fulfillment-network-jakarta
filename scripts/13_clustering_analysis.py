from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.analysis import run_kmeans
from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_csv, write_metadata
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe


N_CLUSTERS = 4


def assign_cluster_labels(summary: pd.DataFrame) -> dict[int, str]:
    """Assign interpretable cluster labels based on direct cluster-level rankings."""
    labels: dict[int, str] = {}
    ranked = summary.copy()

    ranked["demand_rank"] = ranked["mean_demand_index"].rank(ascending=False, method="dense")
    ranked["underserved_rank"] = ranked["mean_underserved_score"].rank(ascending=False, method="dense")
    ranked["accessibility_rank"] = ranked["road_accessibility_score"].rank(ascending=False, method="dense")

    for _, row in ranked.iterrows():
        cluster_id = int(row["cluster"])
        demand_rank = float(row["demand_rank"])
        underserved_rank = float(row["underserved_rank"])
        accessibility_rank = float(row["accessibility_rank"])

        if demand_rank <= 2 and underserved_rank <= 2:
            labels[cluster_id] = "High-demand underserved priority"
        elif demand_rank <= 2 and accessibility_rank <= 2:
            labels[cluster_id] = "High-demand accessible core"
        elif demand_rank >= 3 and underserved_rank >= 3:
            labels[cluster_id] = "Lower-demand peripheral"
        else:
            labels[cluster_id] = "Mixed urban opportunity"

    return labels



def main() -> None:
    """Run KMeans clustering on demand and service coverage features."""
    settings = get_settings()
    logger = get_logger("13_clustering_analysis")

    lisa_path = require_file(settings.processed_dir / "demand_underserved_lisa.gpkg")
    output_path = settings.processed_dir / "demand_clusters.gpkg"
    summary_path = settings.tables_dir / "demand_cluster_summary.csv"

    if output_path.exists() and summary_path.exists():
        logger.info(f"Using cached file from {output_path}")
        logger.info(f"Using cached file from {summary_path}")
        return

    grid = gpd.read_file(lisa_path, layer="lisa")
    validate_geodataframe(grid, required_columns=["demand_index", "underserved_score"])

    feature_columns = [
        "demand_index",
        "population_score",
        "nighttime_lights_score",
        "built_score",
        "road_accessibility_score",
        "poi_density_score",
        "underserved_score",
    ]

    grid["cluster"] = run_kmeans(
        frame=grid,
        feature_columns=feature_columns,
        n_clusters=N_CLUSTERS,
        random_seed=settings.random_seed,
    ).astype(int)

    summary = (
        grid.groupby("cluster", as_index=False)
        .agg(
            cell_count=("cell_id", "count"),
            mean_demand_index=("demand_index", "mean"),
            total_proxy_deliveries_per_100k=("proxy_deliveries_per_100k", "sum"),
            mean_underserved_score=("underserved_score", "mean"),
            high_high_demand_lisa_count=("demand_index_lisa_cluster", lambda s: int((s == "High-High").sum())),
            high_high_underserved_lisa_count=("underserved_score_lisa_cluster", lambda s: int((s == "High-High").sum())),
            demand_index=("demand_index", "mean"),
            underserved_score=("underserved_score", "mean"),
            road_accessibility_score=("road_accessibility_score", "mean"),
        )
        .copy()
    )

    labels = assign_cluster_labels(summary)
    grid["cluster_label"] = grid["cluster"].map(labels)
    summary["cluster_label"] = summary["cluster"].map(labels)

    grid.to_file(output_path, driver="GPKG", layer="demand_clusters")
    write_csv(summary, summary_path)

    write_metadata(
        data_path=output_path,
        dataset_name="Operational demand clusters for quick-commerce micro-fulfillment planning",
        source="Derived from demand index, service coverage, and LISA outputs",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m grid",
        temporal_coverage="Scenario-based clustering analysis",
        preprocessing_steps=[
            "Loaded LISA-enhanced demand and underserved grid",
            "Selected normalized demand, built-up, accessibility, POI, and underserved features",
            "Standardized features using scikit-learn StandardScaler",
            "Applied KMeans with four clusters and fixed random seed",
            "Assigned operational labels based on demand, underserved, and accessibility rankings",
        ],
        unit="Cluster ID and operational cluster label",
        citation_apa="MacQueen, J. (1967). Some methods for classification and analysis of multivariate observations.",
        citation_bibtex="@inproceedings{macqueen1967, title={Some methods for classification and analysis of multivariate observations}, author={MacQueen, J.}, year={1967}}",
        crs=settings.projected_crs,
    )

    logger.info("Clustering analysis completed.")
    print(f"Demand clusters completed: {output_path}")
    print(f"Cluster summary completed: {summary_path}")


if __name__ == "__main__":
    main()
