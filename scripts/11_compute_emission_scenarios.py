from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_csv, write_metadata
from micro_fulfillment_network_jakarta.emissions import (
    DEFAULT_ELECTRIC_MOTORCYCLE_KWH_PER_KM,
    DEFAULT_GRID_GCO2E_PER_KWH,
    DEFAULT_ICE_MOTORCYCLE_GCO2E_PER_KM,
    build_emission_scenario_table,
)
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import require_file


def main() -> None:
    """Compute emission scenarios for optimized MFC networks and EV adoption levels."""
    settings = get_settings()
    logger = get_logger("11_compute_emission_scenarios")

    summary_path = require_file(settings.tables_dir / "optimized_network_summary.csv")
    output_path = settings.processed_dir / "emission_scenarios.csv"
    table_output_path = settings.tables_dir / "emission_scenarios.csv"

    if output_path.exists() and table_output_path.exists():
        logger.info(f"Using cached file from {output_path}")
        logger.info(f"Using cached file from {table_output_path}")
        return

    summary = pd.read_csv(summary_path)
    if summary.empty:
        raise ValueError("Optimized network summary is empty.")

    baseline_distance_km = float(summary["baseline_demand_weighted_distance_km"].iloc[0])

    scenario_distances = summary[
        [
            "mfc_count",
            "demand_weighted_distance_km",
            "distance_reduction_percent",
            "coverage_share",
            "mean_nearest_distance_km",
            "p90_nearest_distance_km",
        ]
    ].copy()

    emission_table = build_emission_scenario_table(
        scenario_distances=scenario_distances,
        baseline_distance_km=baseline_distance_km,
        ev_adoption_scenarios=settings.ev_adoption_scenarios,
    )

    emission_table = emission_table.merge(
        scenario_distances,
        on=["mfc_count", "demand_weighted_distance_km"],
        how="left",
    )

    emission_table["ice_motorcycle_gco2e_per_km"] = DEFAULT_ICE_MOTORCYCLE_GCO2E_PER_KM
    emission_table["electric_motorcycle_kwh_per_km"] = DEFAULT_ELECTRIC_MOTORCYCLE_KWH_PER_KM
    emission_table["grid_gco2e_per_kwh"] = DEFAULT_GRID_GCO2E_PER_KWH
    emission_table["accounting_basis"] = "per_100000_proxy_deliveries"

    write_csv(emission_table, output_path)
    write_csv(emission_table, table_output_path)

    write_metadata(
        data_path=output_path,
        dataset_name="Operational CO2e emission scenarios for quick-commerce MFC networks",
        source="Derived from optimized network distance outputs and literature-based emission factors",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution="Scenario table by MFC count and EV adoption level",
        temporal_coverage="Scenario analysis, not observed emissions",
        preprocessing_steps=[
            "Loaded demand-weighted distance per 100,000 proxy deliveries from optimized network summary",
            "Computed baseline centralized ICE motorcycle emissions",
            "Computed blended fleet emissions for EV adoption levels",
            "Calculated emission reduction percentage relative to centralized ICE baseline",
        ],
        unit="kg CO2e per 100,000 proxy deliveries",
        citation_apa="Emission calculation follows standard activity data multiplied by emission factor accounting.",
        citation_bibtex="@misc{emissionAccounting2025, title={Scenario-based last-mile delivery emission accounting}, author={Project pipeline}, year={2025}}",
        crs="Not applicable",
        extra={
            "ice_motorcycle_gco2e_per_km": DEFAULT_ICE_MOTORCYCLE_GCO2E_PER_KM,
            "electric_motorcycle_kwh_per_km": DEFAULT_ELECTRIC_MOTORCYCLE_KWH_PER_KM,
            "grid_gco2e_per_kwh": DEFAULT_GRID_GCO2E_PER_KWH,
            "interpretation_limit": "Results are scenario-based emissions per normalized proxy deliveries, not measured company emissions.",
        },
    )

    logger.info("Emission scenario computation completed.")
    print(f"Emission scenarios completed: {output_path}")


if __name__ == "__main__":
    main()
