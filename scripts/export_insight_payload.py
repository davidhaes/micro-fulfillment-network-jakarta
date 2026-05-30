from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import compute_data_folder_size_gb
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import require_file


def safe_float(value: Any, digits: int = 6) -> float | None:
    """Convert a value to a rounded float or None."""
    try:
        output = float(value)
        if not np.isfinite(output):
            return None
        return round(output, digits)
    except Exception:
        return None


def safe_int(value: Any) -> int | None:
    """Convert a value to int or None."""
    try:
        if pd.isna(value):
            return None
        return int(value)
    except Exception:
        return None


def choose_reference_scenario(summary: pd.DataFrame) -> pd.Series:
    """Choose the smallest MFC count reaching 90 percent coverage, otherwise best coverage."""
    eligible = summary[summary["coverage_share"] >= 0.90].sort_values("mfc_count")
    if not eligible.empty:
        return eligible.iloc[0]
    return summary.sort_values(["coverage_share", "mfc_count"], ascending=[False, True]).iloc[0]


def compute_demand_concentration(clusters_path: Path) -> dict[str, Any]:
    """Compute demand concentration metrics from demand clusters."""
    grid = gpd.read_file(clusters_path, layer="demand_clusters")
    ordered = grid[["demand_index", "area_m2"]].copy()
    ordered = ordered.replace([np.inf, -np.inf], np.nan).dropna()
    ordered = ordered.sort_values("demand_index", ascending=False)

    total_demand = float(ordered["demand_index"].sum())
    total_area = float(ordered["area_m2"].sum())

    if total_demand <= 0 or total_area <= 0:
        return {
            "area_share_required_for_70_percent_demand": None,
            "top_10_percent_area_demand_share": None,
            "cell_count": int(len(ordered)),
        }

    ordered["cumulative_demand_share"] = ordered["demand_index"].cumsum() / total_demand
    ordered["cumulative_area_share"] = ordered["area_m2"].cumsum() / total_area

    threshold_positions = np.where(ordered["cumulative_demand_share"].to_numpy() >= 0.70)[0]
    if len(threshold_positions) == 0:
        area_share_70 = 1.0
    else:
        area_share_70 = float(ordered.iloc[int(threshold_positions[0])]["cumulative_area_share"])

    top10_cut = ordered["demand_index"].quantile(0.90)
    top10 = ordered[ordered["demand_index"] >= top10_cut]
    top10_demand_share = float(top10["demand_index"].sum() / total_demand)

    return {
        "area_share_required_for_70_percent_demand": safe_float(area_share_70),
        "top_10_percent_area_demand_share": safe_float(top10_demand_share),
        "cell_count": int(len(ordered)),
        "mean_demand_index": safe_float(ordered["demand_index"].mean()),
        "median_demand_index": safe_float(ordered["demand_index"].median()),
        "p90_demand_index": safe_float(ordered["demand_index"].quantile(0.90)),
    }


def get_top_records(frame: pd.DataFrame, sort_column: str, columns: list[str], n: int = 5) -> list[dict[str, Any]]:
    """Return top records as JSON-safe dictionaries."""
    top = frame.sort_values(sort_column, ascending=False).head(n)
    records = []
    for _, row in top.iterrows():
        record: dict[str, Any] = {}
        for column in columns:
            value = row.get(column)
            if isinstance(value, (np.integer, int)):
                record[column] = int(value)
            elif isinstance(value, (np.floating, float)):
                record[column] = safe_float(value)
            elif pd.isna(value):
                record[column] = None
            else:
                record[column] = str(value)
        records.append(record)
    return records


def build_payload() -> dict[str, Any]:
    """Build the final insight payload from project outputs."""
    settings = get_settings()

    summary_path = require_file(settings.tables_dir / "optimized_network_summary.csv")
    emissions_path = require_file(settings.tables_dir / "emission_scenarios.csv")
    moran_path = require_file(settings.tables_dir / "spatial_autocorrelation.csv")
    admin_summary_path = require_file(settings.tables_dir / "admin_unit_demand_summary.csv")
    validation_path = require_file(settings.tables_dir / "validation_crosscheck.csv")
    trend_path = require_file(settings.tables_dir / "viirs_temporal_trend.csv")
    cluster_summary_path = require_file(settings.tables_dir / "demand_cluster_summary.csv")
    clusters_path = require_file(settings.processed_dir / "demand_clusters.gpkg")

    summary = pd.read_csv(summary_path)
    emissions = pd.read_csv(emissions_path)
    moran = pd.read_csv(moran_path)
    admin = pd.read_csv(admin_summary_path)
    validation = pd.read_csv(validation_path)
    trend = pd.read_csv(trend_path)
    cluster_summary = pd.read_csv(cluster_summary_path)

    reference = choose_reference_scenario(summary)
    best_distance = summary.sort_values("distance_reduction_percent", ascending=False).iloc[0]
    best_emission = emissions.sort_values("emission_reduction_percent", ascending=False).iloc[0]

    ev50_reference = emissions[
        (emissions["mfc_count"] == int(reference["mfc_count"]))
        & (emissions["ev_adoption_percent"] == 50)
    ]

    moran_records = {}
    for _, row in moran.iterrows():
        metric = str(row["metric"])
        moran_records[metric] = {
            "moran_i": safe_float(row.get("moran_i")),
            "expected_i": safe_float(row.get("expected_i")),
            "p_value": safe_float(row.get("p_value")),
            "z_score": safe_float(row.get("z_score")),
            "weight_type": str(row.get("weight_type")),
            "observation_count": safe_int(row.get("observation_count")),
        }

    trend_row = trend.iloc[0].to_dict()

    payload = {
        "project": {
            "name": "micro-fulfillment-network-jakarta",
            "title": "Micro-Fulfillment Network Design for Reducing Last-Mile Delivery Emissions in Greater Jakarta Quick Commerce",

            "project_root": str(settings.project_root),
            "data_folder_size_gb": safe_float(compute_data_folder_size_gb()),
            "analysis_grid_size_meters": settings.analysis_grid_size_meters,
            "projected_crs": settings.projected_crs,
            "service_level_minutes": settings.service_level_minutes,
            "default_speed_kmh": settings.default_speed_kmh,
            "interpretation_boundary": "Demand is a latent open-data proxy, not actual quick-commerce order volume. Emissions are scenario-based per 100,000 proxy deliveries.",
        },
        "reference_network_scenario": {
            "mfc_count": safe_int(reference.get("mfc_count")),
            "coverage_share": safe_float(reference.get("coverage_share")),
            "distance_reduction_percent": safe_float(reference.get("distance_reduction_percent")),
            "demand_weighted_distance_km": safe_float(reference.get("demand_weighted_distance_km")),
            "baseline_demand_weighted_distance_km": safe_float(reference.get("baseline_demand_weighted_distance_km")),
            "mean_nearest_distance_km": safe_float(reference.get("mean_nearest_distance_km")),
            "p90_nearest_distance_km": safe_float(reference.get("p90_nearest_distance_km")),
            "max_nearest_distance_km": safe_float(reference.get("max_nearest_distance_km")),
            "total_proxy_deliveries_per_100k": safe_float(reference.get("total_proxy_deliveries_per_100k")),
        },
        "best_distance_scenario": {
            "mfc_count": safe_int(best_distance.get("mfc_count")),
            "distance_reduction_percent": safe_float(best_distance.get("distance_reduction_percent")),
            "coverage_share": safe_float(best_distance.get("coverage_share")),
            "demand_weighted_distance_km": safe_float(best_distance.get("demand_weighted_distance_km")),
        },
        "best_emission_scenario": {
            "mfc_count": safe_int(best_emission.get("mfc_count")),
            "ev_adoption_percent": safe_int(best_emission.get("ev_adoption_percent")),
            "emission_reduction_percent": safe_float(best_emission.get("emission_reduction_percent")),
            "scenario_emissions_kgco2e": safe_float(best_emission.get("scenario_emissions_kgco2e")),
            "baseline_emissions_kgco2e": safe_float(best_emission.get("baseline_emissions_kgco2e")),
        },
        "ev50_reference_scenario": None if ev50_reference.empty else {
            "mfc_count": safe_int(ev50_reference.iloc[0].get("mfc_count")),
            "ev_adoption_percent": 50,
            "emission_reduction_percent": safe_float(ev50_reference.iloc[0].get("emission_reduction_percent")),
            "scenario_emissions_kgco2e": safe_float(ev50_reference.iloc[0].get("scenario_emissions_kgco2e")),
        },
        "mfc_scenario_curve": [
            {
                "mfc_count": safe_int(row.get("mfc_count")),
                "coverage_share": safe_float(row.get("coverage_share")),
                "distance_reduction_percent": safe_float(row.get("distance_reduction_percent")),
                "mean_nearest_distance_km": safe_float(row.get("mean_nearest_distance_km")),
                "p90_nearest_distance_km": safe_float(row.get("p90_nearest_distance_km")),
            }
            for _, row in summary.sort_values("mfc_count").iterrows()
        ],
        "spatial_autocorrelation": moran_records,
        "demand_concentration": compute_demand_concentration(clusters_path),
        "top_underserved_admin_units": get_top_records(
            admin,
            sort_column="mean_underserved_score",
            columns=[
                "NAME_1",
                "NAME_2",
                "cell_count",
                "total_population_proxy",
                "total_proxy_deliveries_per_100k",
                "mean_demand_index",
                "mean_underserved_score",
                "high_high_demand_lisa_count",
                "high_high_underserved_lisa_count",
            ],
            n=10,
        ),
        "cluster_summary": get_top_records(
            cluster_summary,
            sort_column="total_proxy_deliveries_per_100k",
            columns=[
                "cluster",
                "cluster_label",
                "cell_count",
                "mean_demand_index",
                "total_proxy_deliveries_per_100k",
                "mean_underserved_score",
                "high_high_demand_lisa_count",
                "high_high_underserved_lisa_count",
            ],
            n=10,
        ),
        "validation_crosscheck": [
            {
                "validation_check": str(row.get("validation_check")),
                "pearson_r": safe_float(row.get("pearson_r")),
                "p_value": safe_float(row.get("p_value")),
                "interpretation": str(row.get("interpretation")),
            }
            for _, row in validation.iterrows()
        ],
        "viirs_temporal_trend": {
            "start_year": safe_int(trend["year"].min()),
            "end_year": safe_int(trend["year"].max()),
            "kendall_tau": safe_float(trend_row.get("kendall_tau")),
            "kendall_p_value": safe_float(trend_row.get("kendall_p_value")),
            "sen_slope_avg_rad_per_year": safe_float(trend_row.get("sen_slope_avg_rad_per_year")),
            "annual_values": [
                {
                    "year": safe_int(row.get("year")),
                    "mean_viirs_avg_rad": safe_float(row.get("mean_viirs_avg_rad")),
                }
                for _, row in trend.sort_values("year").iterrows()
            ],
        },
        "recommended_files_to_review": {
            "executive_summary": "outputs/reports/executive_summary.md",
            "conclusions": "outputs/reports/conclusions.md",
            "recommendations": "outputs/reports/recommendations.md",
            "main_demand_map": "outputs/figures/maps/quick_commerce_demand_index_map.png",
            "mfc_network_map": "outputs/figures/maps/optimized_mfc_network_map.png",
            "emission_chart": "outputs/figures/charts/emission_scenario_pathway.png",
        },
    }

    return payload


def main() -> None:
    """Export compact JSON payload for external interpretation."""
    settings = get_settings()
    logger = get_logger("export_insight_payload")

    output_path = settings.tables_dir / "insight_payload.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_payload()
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )

    logger.info(f"Insight payload written to {output_path}")
    print(f"Insight payload completed: {output_path}")


if __name__ == "__main__":
    main()
