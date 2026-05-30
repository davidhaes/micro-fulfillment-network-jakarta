from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from pyproj import Transformer
from shapely.geometry import Point
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_csv, write_json, write_metadata
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.optimization import (
    compute_coverage,
    compute_euclidean_distance_matrix,
    greedy_p_median,
)
from micro_fulfillment_network_jakarta.viz_theme import set_publication_theme
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe


DETOUR_FACTOR = 1.35
MAX_DEMAND_POINTS = 2500
MAX_CANDIDATES = 350
BASELINE_HUB_LON = 106.8272
BASELINE_HUB_LAT = -6.1754

EXTENDED_MFC_COUNTS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60]
SPEED_SCENARIOS_KMH = [15, 20, 25]
SERVICE_TIERS_MINUTES = [30, 45, 60]


def load_demand_grid(path: Path) -> gpd.GeoDataFrame:
    """Load demand grid and keep positive demand cells."""
    grid = gpd.read_file(path, layer="demand_grid")
    validate_geodataframe(grid, required_columns=["cell_id", "demand_index", "proxy_deliveries_per_100k"])
    grid = grid[grid["demand_index"].fillna(0) > 0].copy().reset_index(drop=True)
    return grid


def load_candidates(path: Path) -> gpd.GeoDataFrame:
    """Load candidate MFC points."""
    candidates = gpd.read_file(path, layer="mfc_candidates")
    validate_geodataframe(candidates, required_columns=["candidate_id", "demand_index"])
    candidates = candidates.sort_values("demand_index", ascending=False).head(MAX_CANDIDATES).copy()
    candidates = candidates.reset_index(drop=True)
    return candidates


def select_demand_points(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Select top demand cells for optimization and normalize weights to 100,000 proxy deliveries."""
    selected = grid.sort_values("demand_index", ascending=False).head(MAX_DEMAND_POINTS).copy()
    selected = selected.reset_index(drop=True)

    non_geometry = selected.drop(columns="geometry").copy()
    demand_points = gpd.GeoDataFrame(
        non_geometry,
        geometry=selected.geometry.centroid,
        crs=grid.crs,
    )

    total_weight = float(demand_points["proxy_deliveries_per_100k"].sum())
    if total_weight <= 0:
        total_weight = float(demand_points["demand_index"].sum())
        demand_points["optimization_weight"] = demand_points["demand_index"] / total_weight * 100000.0
    else:
        demand_points["optimization_weight"] = demand_points["proxy_deliveries_per_100k"] / total_weight * 100000.0

    return demand_points


def coordinates_array(gdf: gpd.GeoDataFrame) -> np.ndarray:
    """Return Nx2 coordinate array from point geometries."""
    return np.column_stack([gdf.geometry.x.to_numpy(), gdf.geometry.y.to_numpy()])


def baseline_hub_point(projected_crs: str) -> Point:
    """Return representative centralized baseline hub near central Jakarta."""
    transformer = Transformer.from_crs("EPSG:4326", projected_crs, always_xy=True)
    x, y = transformer.transform(BASELINE_HUB_LON, BASELINE_HUB_LAT)
    return Point(x, y)


def compute_baseline_distance_km(demand_points: gpd.GeoDataFrame, weights: np.ndarray, projected_crs: str) -> float:
    """Compute baseline demand-weighted distance from a central hub."""
    hub = baseline_hub_point(projected_crs)
    baseline_distances_m = np.array(
        [geom.distance(hub) * DETOUR_FACTOR for geom in demand_points.geometry],
        dtype=float,
    )
    return float(np.sum((baseline_distances_m / 1000.0) * weights))


def reachable_distance_m(speed_kmh: float, service_minutes: float) -> float:
    """Compute reachable route distance in meters for a speed and service-tier scenario."""
    return float(speed_kmh * 1000.0 * (service_minutes / 60.0))


def build_extended_scenarios(
    route_distance: np.ndarray,
    weights: np.ndarray,
    baseline_distance_km: float,
) -> tuple[pd.DataFrame, dict[int, list[int]]]:
    """Build extended MFC count scenarios using greedy p-median."""
    records: list[dict] = []
    selected_by_p: dict[int, list[int]] = {}

    for p in tqdm(EXTENDED_MFC_COUNTS, desc="Extended MFC scenarios"):
        selected_indices = greedy_p_median(route_distance, weights, p=p)
        selected_by_p[p] = selected_indices

        nearest_distance_m = np.min(route_distance[:, selected_indices], axis=1)
        demand_weighted_distance_km = float(np.sum((nearest_distance_m / 1000.0) * weights))
        distance_reduction_percent = (
            (baseline_distance_km - demand_weighted_distance_km) / baseline_distance_km * 100.0
            if baseline_distance_km > 0
            else np.nan
        )

        base_coverage = compute_coverage(
            distance_matrix=route_distance,
            weights=weights,
            selected_indices=selected_indices,
            threshold_meters=reachable_distance_m(20, 30),
        )

        records.append(
            {
                "mfc_count": int(p),
                "service_minutes": 30,
                "speed_kmh": 20,
                "coverage_share": float(base_coverage["coverage_share"]),
                "covered_proxy_deliveries_per_100k": float(base_coverage["covered_weight"]),
                "mean_nearest_distance_km": float(base_coverage["mean_nearest_distance_m"] / 1000.0),
                "p90_nearest_distance_km": float(base_coverage["p90_nearest_distance_m"] / 1000.0),
                "max_nearest_distance_km": float(base_coverage["max_nearest_distance_m"] / 1000.0),
                "demand_weighted_distance_km": demand_weighted_distance_km,
                "baseline_demand_weighted_distance_km": baseline_distance_km,
                "distance_reduction_percent": float(distance_reduction_percent),
            }
        )

    return pd.DataFrame.from_records(records), selected_by_p


def build_speed_service_sensitivity(
    route_distance: np.ndarray,
    weights: np.ndarray,
    selected_by_p: dict[int, list[int]],
) -> pd.DataFrame:
    """Build sensitivity table across MFC counts, speeds, and service tiers."""
    records: list[dict] = []

    for p, selected_indices in selected_by_p.items():
        for speed in SPEED_SCENARIOS_KMH:
            for service_minutes in SERVICE_TIERS_MINUTES:
                threshold_m = reachable_distance_m(speed, service_minutes)
                coverage = compute_coverage(
                    distance_matrix=route_distance,
                    weights=weights,
                    selected_indices=selected_indices,
                    threshold_meters=threshold_m,
                )
                records.append(
                    {
                        "mfc_count": int(p),
                        "speed_kmh": int(speed),
                        "service_minutes": int(service_minutes),
                        "reachable_route_distance_km": float(threshold_m / 1000.0),
                        "coverage_share": float(coverage["coverage_share"]),
                        "covered_proxy_deliveries_per_100k": float(coverage["covered_weight"]),
                        "mean_nearest_distance_km": float(coverage["mean_nearest_distance_m"] / 1000.0),
                        "p90_nearest_distance_km": float(coverage["p90_nearest_distance_m"] / 1000.0),
                    }
                )

    return pd.DataFrame.from_records(records)


def build_admin_action_typology(admin_summary: pd.DataFrame) -> pd.DataFrame:
    """Classify administrative units into action-oriented operational typologies."""
    frame = admin_summary.dropna(subset=["NAME_1", "NAME_2"]).copy()

    high_demand_threshold = 0.75
    high_underserved_threshold = 0.20
    critical_underserved_threshold = 0.30

    action_labels = []
    action_priorities = []
    action_rationales = []

    for _, row in frame.iterrows():
        demand = float(row["mean_demand_index"])
        underserved = float(row["mean_underserved_score"])
        proxy_deliveries = float(row["total_proxy_deliveries_per_100k"])

        high_demand = demand >= high_demand_threshold
        high_underserved = underserved >= high_underserved_threshold
        critical_underserved = underserved >= critical_underserved_threshold

        if high_demand and high_underserved:
            action_labels.append("New MFC priority")
            action_priorities.append("High")
            action_rationales.append(
                "High demand and high underserved score indicate need for additional local fulfillment capacity."
            )
        elif high_demand and not high_underserved:
            action_labels.append("Densify and electrify")
            action_priorities.append("High")
            action_rationales.append(
                "High demand with low underserved score fits EV deployment, inventory densification, and operational productivity improvements."
            )
        elif not high_demand and critical_underserved and proxy_deliveries >= 10000:
            action_labels.append("Fringe MFC or staging priority")
            action_priorities.append("High")
            action_rationales.append(
                "Large proxy demand and critical underserved score indicate a fringe coverage bottleneck requiring MFC expansion or staging points."
            )
        elif not high_demand and high_underserved:
            action_labels.append("Staging or tiered SLA")
            action_priorities.append("Medium")
            action_rationales.append(
                "Moderate demand with high underserved score suggests rider staging, partner pickup, or 45–60 minute service tier."
            )
        else:
            action_labels.append("Maintain and monitor")
            action_priorities.append("Low")
            action_rationales.append(
                "Lower underserved score does not justify immediate MFC expansion."
            )

    frame["action_typology"] = action_labels
    frame["action_priority"] = action_priorities
    frame["action_rationale"] = action_rationales

    priority_order = {"High": 1, "Medium": 2, "Low": 3}
    frame["priority_rank"] = frame["action_priority"].map(priority_order)

    frame = frame.sort_values(
        ["priority_rank", "mean_underserved_score", "total_proxy_deliveries_per_100k"],
        ascending=[True, False, False],
    ).drop(columns=["priority_rank"]).reset_index(drop=True)

    return frame


def plot_extended_coverage_curve(frame: pd.DataFrame, output_path: Path) -> None:
    """Plot coverage and distance reduction across extended MFC scenarios."""
    set_publication_theme()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax1 = plt.subplots(figsize=(11, 6.2))
    ax2 = ax1.twinx()

    plot_frame = frame.sort_values("mfc_count").copy()
    plot_frame["coverage_percent"] = plot_frame["coverage_share"] * 100.0

    ax1.plot(
        plot_frame["mfc_count"],
        plot_frame["coverage_percent"],
        color="#2E7D32",
        marker="o",
        linewidth=2.4,
        label="30-minute coverage",
    )
    ax2.plot(
        plot_frame["mfc_count"],
        plot_frame["distance_reduction_percent"],
        color="#C62828",
        marker="s",
        linewidth=2.1,
        label="Distance reduction",
    )

    ax1.axhline(90, color="#333333", linestyle="--", linewidth=1.0)
    ax1.text(
        plot_frame["mfc_count"].min(),
        91,
        "90% coverage target",
        fontsize=8.5,
        color="#333333",
    )

    ax1.set_title("Extended MFC Count Sensitivity", loc="left", pad=18)
    ax1.text(
        0,
        1.01,
        "Coverage and distance reduction under 20 km/h and 30-minute service threshold",
        transform=ax1.transAxes,
        ha="left",
        fontsize=10.5,
    )

    ax1.set_xlabel("Number of MFCs")
    ax1.set_ylabel("Covered proxy demand, percent")
    ax2.set_ylabel("Distance reduction, percent")

    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="lower right", frameon=True)

    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_speed_service_heatmap(frame: pd.DataFrame, output_path: Path) -> None:
    """Plot heatmap of coverage across MFC count, speed, and service tier."""
    set_publication_theme()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plot_frame = frame.copy()
    plot_frame["scenario"] = (
        plot_frame["speed_kmh"].astype(str)
        + " km/h, "
        + plot_frame["service_minutes"].astype(str)
        + " min"
    )
    plot_frame["coverage_percent"] = plot_frame["coverage_share"] * 100.0

    pivot = plot_frame.pivot_table(
        index="scenario",
        columns="mfc_count",
        values="coverage_percent",
        aggfunc="mean",
    )

    scenario_order = [
        f"{speed} km/h, {minutes} min"
        for speed in SPEED_SCENARIOS_KMH
        for minutes in SERVICE_TIERS_MINUTES
    ]
    pivot = pivot.reindex(scenario_order)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    sns.heatmap(
        pivot,
        cmap="YlGnBu",
        annot=True,
        fmt=".1f",
        linewidths=0.35,
        linecolor="white",
        cbar_kws={"label": "Coverage, percent"},
        ax=ax,
    )

    ax.set_title("Speed and Service-Tier Coverage Sensitivity", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Coverage share by MFC count, rider speed assumption, and service-level threshold",
        transform=ax.transAxes,
        ha="left",
        fontsize=10.5,
    )
    ax.set_xlabel("Number of MFCs")
    ax.set_ylabel("Speed and service-tier scenario")

    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_admin_typology(frame: pd.DataFrame, output_path: Path) -> None:
    """Plot action typology by administrative unit."""
    set_publication_theme()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plot_frame = frame.copy()
    plot_frame["admin_unit"] = plot_frame["NAME_2"].astype(str)
    plot_frame = plot_frame.sort_values("mean_underserved_score", ascending=False).head(13)

    palette = {
        "New MFC priority": "#B2182B",
        "Fringe MFC or staging priority": "#D6604D",
        "Densify and electrify": "#1B9E77",
        "Staging or tiered SLA": "#E6AB02",
        "Maintain and monitor": "#9E9E9E",
    }

    fig, ax = plt.subplots(figsize=(11, 6.3))
    sns.barplot(
        data=plot_frame,
        x="mean_underserved_score",
        y="admin_unit",
        hue="action_typology",
        dodge=False,
        palette=palette,
        ax=ax,
    )

    ax.set_title("Administrative Action Typology", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Priority classes derived from demand intensity and underserved score",
        transform=ax.transAxes,
        ha="left",
        fontsize=10.5,
    )

    ax.set_xlabel("Mean underserved score")
    ax.set_ylabel("")
    ax.grid(True, axis="x", alpha=0.3)
    ax.legend(title="Recommended action", loc="lower right", frameon=True)

    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_enhanced_payload(
    extended_summary: pd.DataFrame,
    sensitivity: pd.DataFrame,
    typology: pd.DataFrame,
) -> dict:
    """Build compact enhanced-analysis JSON payload."""
    best_30 = extended_summary.sort_values(["coverage_share", "mfc_count"], ascending=[False, True]).iloc[0]

    coverage_90 = extended_summary[extended_summary["coverage_share"] >= 0.90].sort_values("mfc_count")
    if coverage_90.empty:
        mfc_for_90 = None
    else:
        mfc_for_90 = int(coverage_90.iloc[0]["mfc_count"])

    best_tier = sensitivity.sort_values(["coverage_share", "mfc_count"], ascending=[False, True]).iloc[0]

    top_actions = typology[
        [
            "NAME_1",
            "NAME_2",
            "mean_demand_index",
            "mean_underserved_score",
            "total_proxy_deliveries_per_100k",
            "action_typology",
            "action_priority",
        ]
    ].head(10).to_dict("records")

    return {
        "enhanced_analysis": {
            "extended_mfc_counts_tested": EXTENDED_MFC_COUNTS,
            "speed_scenarios_kmh": SPEED_SCENARIOS_KMH,
            "service_tiers_minutes": SERVICE_TIERS_MINUTES,
            "mfc_count_reaching_90_percent_coverage_at_20kmh_30min": mfc_for_90,
            "best_extended_30min_scenario": {
                "mfc_count": int(best_30["mfc_count"]),
                "coverage_share": float(best_30["coverage_share"]),
                "distance_reduction_percent": float(best_30["distance_reduction_percent"]),
                "p90_nearest_distance_km": float(best_30["p90_nearest_distance_km"]),
            },
            "best_speed_service_scenario": {
                "mfc_count": int(best_tier["mfc_count"]),
                "speed_kmh": int(best_tier["speed_kmh"]),
                "service_minutes": int(best_tier["service_minutes"]),
                "coverage_share": float(best_tier["coverage_share"]),
            },
            "top_admin_action_recommendations": top_actions,
        }
    }


def main() -> None:
    """Run enhanced sensitivity and action-typology analysis."""
    settings = get_settings()
    logger = get_logger("run_enhanced_analysis")

    demand_path = require_file(settings.processed_dir / "demand_grid.gpkg")
    candidates_path = require_file(settings.processed_dir / "mfc_candidates.gpkg")
    admin_summary_path = require_file(settings.tables_dir / "admin_unit_demand_summary.csv")

    processed_extended_path = settings.processed_dir / "enhanced_extended_mfc_summary.csv"
    processed_sensitivity_path = settings.processed_dir / "enhanced_speed_service_sensitivity.csv"
    processed_typology_path = settings.processed_dir / "admin_action_typology.csv"

    output_extended_path = settings.tables_dir / "enhanced_extended_mfc_summary.csv"
    output_sensitivity_path = settings.tables_dir / "enhanced_speed_service_sensitivity.csv"
    output_typology_path = settings.tables_dir / "admin_action_typology.csv"
    output_payload_path = settings.tables_dir / "enhanced_analysis_payload.json"

    charts_dir = settings.charts_dir
    extended_chart_path = charts_dir / "enhanced_extended_mfc_coverage_curve.png"
    heatmap_path = charts_dir / "enhanced_speed_service_sensitivity_heatmap.png"
    typology_chart_path = charts_dir / "enhanced_admin_action_typology.png"

    logger.info("Loading demand grid and MFC candidates.")
    grid = load_demand_grid(demand_path)
    candidates = load_candidates(candidates_path)
    demand_points = select_demand_points(grid)

    demand_xy = coordinates_array(demand_points)
    candidate_xy = coordinates_array(candidates)

    logger.info(f"Computing route-distance matrix for {len(demand_points)} demand points and {len(candidates)} candidates.")
    euclidean_distance = compute_euclidean_distance_matrix(demand_xy, candidate_xy)
    route_distance = euclidean_distance * DETOUR_FACTOR

    weights = demand_points["optimization_weight"].astype(float).to_numpy()
    baseline_distance_km = compute_baseline_distance_km(demand_points, weights, settings.projected_crs)

    logger.info("Building extended MFC count scenarios.")
    extended_summary, selected_by_p = build_extended_scenarios(route_distance, weights, baseline_distance_km)

    logger.info("Building speed and service-tier sensitivity scenarios.")
    sensitivity = build_speed_service_sensitivity(route_distance, weights, selected_by_p)

    logger.info("Building administrative action typology.")
    admin_summary = pd.read_csv(admin_summary_path)
    typology = build_admin_action_typology(admin_summary)

    logger.info("Writing enhanced analysis tables.")
    write_csv(extended_summary, processed_extended_path)
    write_csv(extended_summary, output_extended_path)
    write_csv(sensitivity, processed_sensitivity_path)
    write_csv(sensitivity, output_sensitivity_path)
    write_csv(typology, processed_typology_path)
    write_csv(typology, output_typology_path)

    write_metadata(
        data_path=processed_extended_path,
        dataset_name="Enhanced extended MFC count sensitivity summary",
        source="Derived from demand grid and MFC candidates",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m demand grid",
        temporal_coverage="Scenario analysis",
        preprocessing_steps=[
            "Loaded processed demand grid and MFC candidates",
            "Selected top demand cells for computational stability",
            "Normalized optimization weights to 100,000 proxy deliveries",
            "Computed corrected Euclidean route-distance matrix",
            "Ran greedy p-median for extended MFC counts",
            "Computed 30-minute coverage and distance reduction",
        ],
        unit="Scenario metrics by MFC count",
        citation_apa="Derived enhanced MFC sensitivity analysis from project pipeline.",
        citation_bibtex="@misc{enhancedMfcSensitivity2025, title={Enhanced MFC count sensitivity analysis}, author={Project pipeline}, year={2025}}",
        crs="Not applicable",
        extra={"detour_factor": DETOUR_FACTOR},
    )

    write_metadata(
        data_path=processed_sensitivity_path,
        dataset_name="Enhanced speed and service-tier coverage sensitivity",
        source="Derived from extended MFC scenarios",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m demand grid",
        temporal_coverage="Scenario analysis",
        preprocessing_steps=[
            "Loaded extended selected MFC scenarios",
            "Evaluated coverage for multiple rider speed assumptions",
            "Evaluated coverage for 30, 45, and 60 minute service tiers",
        ],
        unit="Coverage share by MFC count, speed, and service tier",
        citation_apa="Derived speed and service-tier sensitivity analysis from project pipeline.",
        citation_bibtex="@misc{speedServiceSensitivity2025, title={Speed and service-tier coverage sensitivity}, author={Project pipeline}, year={2025}}",
        crs="Not applicable",
        extra={"speed_scenarios_kmh": SPEED_SCENARIOS_KMH, "service_tiers_minutes": SERVICE_TIERS_MINUTES},
    )

    write_metadata(
        data_path=processed_typology_path,
        dataset_name="Administrative action typology for quick-commerce logistics",
        source="Derived from administrative demand summary",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution="Administrative unit level 2",
        temporal_coverage="Scenario analysis",
        preprocessing_steps=[
            "Loaded administrative unit demand summary",
            "Dropped unmatched administrative records",
            "Classified units by demand and underserved score thresholds",
            "Assigned action-oriented operational typology",
        ],
        unit="Administrative unit action class",
        citation_apa="Derived administrative action typology from project pipeline.",
        citation_bibtex="@misc{adminActionTypology2025, title={Administrative action typology for quick-commerce logistics}, author={Project pipeline}, year={2025}}",
        crs="Not applicable",
    )

    logger.info("Generating enhanced charts.")
    plot_extended_coverage_curve(extended_summary, extended_chart_path)
    plot_speed_service_heatmap(sensitivity, heatmap_path)
    plot_admin_typology(typology, typology_chart_path)

    payload = build_enhanced_payload(extended_summary, sensitivity, typology)
    write_json(output_payload_path, payload)

    logger.info("Enhanced analysis completed.")
    print(f"Enhanced extended MFC summary: {output_extended_path}")
    print(f"Enhanced speed-service sensitivity: {output_sensitivity_path}")
    print(f"Admin action typology: {output_typology_path}")
    print(f"Enhanced analysis payload: {output_payload_path}")
    print(f"Enhanced charts saved in: {charts_dir}")


if __name__ == "__main__":
    main()