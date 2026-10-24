from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
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
    greedy_max_coverage,
    solve_p_median,
)
from micro_fulfillment_network_jakarta.viz_theme import set_publication_theme
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe


DETOUR_FACTOR = 1.35
# All demand cells and every built-up candidate, as in 10_optimize_mfc_network.py.
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
    candidates = candidates.sort_values("demand_index", ascending=False).copy()
    candidates = candidates.reset_index(drop=True)
    return candidates


def select_demand_points(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """All demand cells, weights normalised to 100,000 proxy deliveries."""
    selected = grid.sort_values("demand_index", ascending=False).copy()
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
    """Extended MFC count scenarios: p-median for distance, and a greedy
    maximal-covering solution for the same p, so the coverage a network *could*
    reach is visible next to the coverage the distance-optimal network reaches."""
    records: list[dict] = []
    selected_by_p: dict[int, list[int]] = {}

    for p in tqdm(EXTENDED_MFC_COUNTS, desc="Extended MFC scenarios"):
        selected_indices = solve_p_median(route_distance, weights, p=p)
        selected_by_p[p] = selected_indices
        mclp = greedy_max_coverage(route_distance, weights, p, reachable_distance_m(20, 30))
        mclp_coverage = compute_coverage(route_distance, weights, mclp, reachable_distance_m(20, 30))

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
                "max_coverage_share": float(mclp_coverage["coverage_share"]),
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

    # Classification on two measured quantities per unit: mean demand index,
    # and the share of the unit's proxy demand that falls outside the 30-minute
    # reach of the 30-hub reference network. The earlier rule used the mean
    # cell underserved score, which large regencies dilute with empty land, so
    # the regencies holding most of the uncovered demand were labelled
    # "maintain and monitor".
    high_demand_threshold = 0.75
    uncovered_threshold = 0.20
    large_unit_deliveries = 10000.0

    action_labels = []
    action_priorities = []
    action_rationales = []

    for _, row in frame.iterrows():
        demand = float(row["mean_demand_index"])
        uncovered = float(row.get("uncovered_demand_share", 0.0) or 0.0)
        uncovered_volume = float(row.get("uncovered_proxy_deliveries_per_100k", 0.0) or 0.0)

        if demand >= high_demand_threshold and uncovered < uncovered_threshold:
            action_labels.append("Densify and electrify")
            action_priorities.append("High")
            action_rationales.append(
                "Dense demand already inside the 30-minute reach: electrify the fleet and densify inventory."
            )
        elif demand >= high_demand_threshold:
            action_labels.append("Add hubs in the core")
            action_priorities.append("High")
            action_rationales.append("Dense demand with a material share outside the 30-minute reach.")
        elif uncovered_volume >= 0.1 * large_unit_deliveries:
            # Ranked on the volume left outside the reach, not only its share:
            # a large regency just under the share threshold can strand more
            # orders than a small one above it (October 2026 audit).
            action_labels.append("Fringe hubs or staging points")
            action_priorities.append("High")
            action_rationales.append(
                "A large volume of demand outside the 30-minute reach: add fringe hubs or rider staging points, "
                "or offer a longer service tier."
            )
        elif uncovered >= uncovered_threshold:
            action_labels.append("Tiered service level")
            action_priorities.append("Medium")
            action_rationales.append("Low-volume demand outside the 30-minute reach: a 45 to 60 minute tier.")
        else:
            action_labels.append("Maintain and monitor")
            action_priorities.append("Low")
            action_rationales.append("Most demand is already inside the 30-minute reach.")

    frame["action_typology"] = action_labels
    frame["action_priority"] = action_priorities
    frame["action_rationale"] = action_rationales

    priority_order = {"High": 1, "Medium": 2, "Low": 3}
    frame["priority_rank"] = frame["action_priority"].map(priority_order)

    frame = frame.sort_values(
        ["priority_rank", "uncovered_proxy_deliveries_per_100k", "total_proxy_deliveries_per_100k"],
        ascending=[True, False, False],
    ).drop(columns=["priority_rank"]).reset_index(drop=True)

    return frame


def plot_extended_coverage_curve(frame: pd.DataFrame, output_path: Path, sensitivity: pd.DataFrame | None = None) -> None:
    """Coverage against hub count, with the slower-rider case when the sensitivity table is given.

    Distance reduction is left out: it is measured against one central hub,
    a network nobody runs, so it adds a large number without informing a choice.
    """
    set_publication_theme()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 6))
    plot_frame = frame.sort_values("mfc_count")
    ax.plot(plot_frame["mfc_count"], plot_frame["coverage_share"] * 100.0, color="#b63a1c", marker="o",
            linewidth=2.4, label="Distance-optimal network, 20 km/h")
    if "max_coverage_share" in plot_frame:
        ax.plot(plot_frame["mfc_count"], plot_frame["max_coverage_share"] * 100.0, color="#d98c6c", marker="o",
                linestyle="--", linewidth=1.6, label="Greedy coverage-maximising network, 20 km/h")
    if sensitivity is not None:
        slow = sensitivity[(sensitivity["speed_kmh"] == 15) & (sensitivity["service_minutes"] == 30)].sort_values("mfc_count")
        ax.plot(slow["mfc_count"], slow["coverage_share"] * 100.0, color="#15171a", marker="s", linewidth=2.0,
                label="Distance-optimal network, 15 km/h (or about 7 minutes lost to picking)")
    ax.axhline(90, color="#8c877c", linestyle=":", linewidth=1.0)
    ax.text(plot_frame["mfc_count"].max(), 90.8, "90%", fontsize=8.5, color="#6f7378", ha="right")
    ax.set_title("Share of demand within a 30-minute ride, by number of hubs", loc="left", pad=22)
    ax.text(0, 1.015, "Gains slow down once the core is covered; rider speed moves coverage as much as adding hubs",
            transform=ax.transAxes, ha="left", fontsize=9.5, color="#6f7378")
    ax.set_xlabel("Number of hubs")
    ax.set_ylabel("Proxy demand covered (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="y")
    ax.legend(loc="lower right")
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
        # Centred on the 90 percent target: rust below it, teal above it.
        cmap=LinearSegmentedColormap.from_list("site", ["#b63a1c", "#e7b8a7", "#f4f2ec", "#9fb8b5", "#3f6f73"]),
        norm=TwoSlopeNorm(vmin=20, vcenter=90, vmax=100),
        annot=True,
        annot_kws={"color": "#15171a"},
        fmt=".1f",
        linewidths=0.35,
        linecolor="white",
        cbar_kws={"label": "Coverage, percent"},
        ax=ax,
    )

    ax.set_title("Coverage by hub count, rider speed and service tier", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Share of proxy demand within reach; colour turns teal above the 90 percent target",
        transform=ax.transAxes,
        ha="left",
        fontsize=10.5,
    )
    ax.set_xlabel("Number of hubs")
    ax.set_ylabel("Speed and service-tier scenario")

    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_admin_typology(frame: pd.DataFrame, output_path: Path) -> None:
    """Plot action typology by administrative unit."""
    set_publication_theme()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plot_frame = frame.copy()
    # GADM writes "KotaBekasi"; regencies share names with their cities.
    plot_frame["admin_unit"] = (
        plot_frame["NAME_2"].astype(str).str.replace(r"(?<=[a-z])(?=[A-Z])", " ", regex=True)
        .replace({"Bogor": "Bogor regency", "Bekasi": "Bekasi regency", "Tangerang": "Tangerang regency"})
    )
    plot_frame["uncovered_percent"] = plot_frame["uncovered_demand_share"] * 100.0
    plot_frame = plot_frame.sort_values("uncovered_proxy_deliveries_per_100k", ascending=False).head(13)

    palette = {
        "Add hubs in the core": "#b63a1c",
        "Fringe hubs or staging points": "#d98c6c",
        "Densify and electrify": "#3f6f73",
        "Tiered service level": "#c9a227",
        "Maintain and monitor": "#8c877c",
    }

    fig, ax = plt.subplots(figsize=(11, 6.3))
    sns.barplot(
        data=plot_frame,
        x="uncovered_percent",
        y="admin_unit",
        hue="action_typology",
        dodge=False,
        palette=palette,
        ax=ax,
    )

    ax.set_title("Recommended action by regency and city", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Share of each unit's proxy demand outside 30 minutes of the 30-hub network",
        transform=ax.transAxes,
        ha="left",
        fontsize=10.5,
    )

    ax.set_xlabel("Proxy demand outside 30-minute reach, percent")
    ax.set_ylabel("")
    ax.grid(True, axis="x", alpha=0.3)
    ax.legend(title="Recommended action", loc="lower right", frameon=False)

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
            "uncovered_demand_share",
            "uncovered_proxy_deliveries_per_100k",
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
    plot_extended_coverage_curve(extended_summary, extended_chart_path, sensitivity)
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