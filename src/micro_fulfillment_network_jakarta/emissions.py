from __future__ import annotations

import pandas as pd


DEFAULT_ICE_MOTORCYCLE_GCO2E_PER_KM = 72.0
DEFAULT_ELECTRIC_MOTORCYCLE_KWH_PER_KM = 0.035
DEFAULT_GRID_GCO2E_PER_KWH = 650.0


def compute_ice_emissions_kg(distance_km: float, emission_factor_g_per_km: float = DEFAULT_ICE_MOTORCYCLE_GCO2E_PER_KM) -> float:
    """Compute internal combustion motorcycle emissions in kg CO2e."""
    return float(distance_km * emission_factor_g_per_km / 1000.0)


def compute_ev_emissions_kg(
    distance_km: float,
    kwh_per_km: float = DEFAULT_ELECTRIC_MOTORCYCLE_KWH_PER_KM,
    grid_g_per_kwh: float = DEFAULT_GRID_GCO2E_PER_KWH,
) -> float:
    """Compute electric motorcycle emissions in kg CO2e using grid electricity intensity."""
    return float(distance_km * kwh_per_km * grid_g_per_kwh / 1000.0)


def compute_fleet_emissions_kg(
    distance_km: float,
    ev_adoption_percent: float,
    ice_g_per_km: float = DEFAULT_ICE_MOTORCYCLE_GCO2E_PER_KM,
    ev_kwh_per_km: float = DEFAULT_ELECTRIC_MOTORCYCLE_KWH_PER_KM,
    grid_g_per_kwh: float = DEFAULT_GRID_GCO2E_PER_KWH,
) -> float:
    """Compute blended fleet emissions for an EV adoption scenario."""
    ev_share = ev_adoption_percent / 100.0
    ice_share = 1.0 - ev_share

    ice = compute_ice_emissions_kg(distance_km, ice_g_per_km)
    ev = compute_ev_emissions_kg(distance_km, ev_kwh_per_km, grid_g_per_kwh)

    return float((ice_share * ice) + (ev_share * ev))


def compute_emission_reduction_percent(baseline_kg: float, scenario_kg: float) -> float:
    """Compute emission reduction percentage relative to baseline emissions."""
    if baseline_kg <= 0:
        return float("nan")
    return float((baseline_kg - scenario_kg) / baseline_kg * 100.0)


def build_emission_scenario_table(
    scenario_distances: pd.DataFrame,
    baseline_distance_km: float,
    ev_adoption_scenarios: tuple[int, ...],
) -> pd.DataFrame:
    """Build emission scenario table for MFC count and EV adoption combinations."""
    baseline_emissions_kg = compute_fleet_emissions_kg(baseline_distance_km, ev_adoption_percent=0)

    records: list[dict[str, float]] = []
    for _, row in scenario_distances.iterrows():
        mfc_count = int(row["mfc_count"])
        distance_km = float(row["demand_weighted_distance_km"])

        for ev_adoption in ev_adoption_scenarios:
            emissions_kg = compute_fleet_emissions_kg(distance_km, ev_adoption)
            records.append(
                {
                    "mfc_count": mfc_count,
                    "ev_adoption_percent": int(ev_adoption),
                    "demand_weighted_distance_km": distance_km,
                    "scenario_emissions_kgco2e": emissions_kg,
                    "baseline_emissions_kgco2e": baseline_emissions_kg,
                    "emission_reduction_percent": compute_emission_reduction_percent(
                        baseline_emissions_kg,
                        emissions_kg,
                    ),
                }
            )

    return pd.DataFrame.from_records(records)
