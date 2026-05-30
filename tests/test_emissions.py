from __future__ import annotations

import math

from micro_fulfillment_network_jakarta.emissions import (
    compute_emission_reduction_percent,
    compute_ev_emissions_kg,
    compute_fleet_emissions_kg,
    compute_ice_emissions_kg,
)


def test_compute_ice_emissions_kg() -> None:
    """ICE emissions should convert grams to kilograms correctly."""
    result = compute_ice_emissions_kg(distance_km=100.0, emission_factor_g_per_km=72.0)
    assert math.isclose(result, 7.2, rel_tol=1e-9)


def test_compute_ev_emissions_kg() -> None:
    """EV emissions should use distance, kWh per km, and grid factor."""
    result = compute_ev_emissions_kg(
        distance_km=100.0,
        kwh_per_km=0.035,
        grid_g_per_kwh=650.0,
    )
    assert math.isclose(result, 2.275, rel_tol=1e-9)


def test_compute_fleet_emissions_kg_half_ev() -> None:
    """A 50 percent EV fleet should be the average of ICE and EV emissions."""
    result = compute_fleet_emissions_kg(
        distance_km=100.0,
        ev_adoption_percent=50.0,
        ice_g_per_km=72.0,
        ev_kwh_per_km=0.035,
        grid_g_per_kwh=650.0,
    )
    expected = (7.2 + 2.275) / 2.0
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_compute_emission_reduction_percent() -> None:
    """Emission reduction should be computed relative to baseline."""
    result = compute_emission_reduction_percent(baseline_kg=100.0, scenario_kg=70.0)
    assert math.isclose(result, 30.0, rel_tol=1e-9)
