"""Fleet electrification against the same network, under two grid factors.

The scenario table in 11_compute_emission_scenarios.py measures every
reduction against one central hub serving the whole region with petrol
motorcycles. No operator runs that network, so the large percentages it
produces say more about the baseline than about any decision. This script
answers the two questions an operator can act on:

* for a fixed network, how much does electrifying the fleet cut CO2e;
* how sensitive is that cut to the grid factor. 650 gCO2e/kWh is the
  project default; 870 gCO2e/kWh is close to the operating margin of the
  coal-heavy Java-Bali grid and is the cautious case for charging load.

Writes outputs/tables/emission_grid_sensitivity.csv and
outputs/figures/charts/emission_per_delivery.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from micro_fulfillment_network_jakarta.emissions import (  # noqa: E402
    DEFAULT_ELECTRIC_MOTORCYCLE_KWH_PER_KM,
    DEFAULT_ICE_MOTORCYCLE_GCO2E_PER_KM,
    compute_fleet_emissions_kg,
)

GRID_FACTORS = (650.0, 870.0)
EV_SHARES = (0, 50, 100)


def main() -> None:
    tables = PROJECT_ROOT / "outputs" / "tables"
    summary = pd.read_csv(tables / "optimized_network_summary.csv")
    rows = []
    for _, r in summary.iterrows():
        km = float(r["demand_weighted_distance_km"])
        for grid in GRID_FACTORS:
            ice_only = compute_fleet_emissions_kg(km, 0, grid_g_per_kwh=grid)
            for ev in EV_SHARES:
                kg = compute_fleet_emissions_kg(km, ev, grid_g_per_kwh=grid)
                rows.append({
                    "mfc_count": int(r["mfc_count"]),
                    "grid_gco2e_per_kwh": int(grid),
                    "ev_adoption_percent": ev,
                    "km_per_100k_deliveries": round(km, 1),
                    "km_per_delivery": round(km / 100_000, 2),
                    "kgco2e_per_100k_deliveries": round(kg, 1),
                    "gco2e_per_delivery": round(kg * 1000 / 100_000, 1),
                    "reduction_vs_same_network_ice_pct": round((ice_only - kg) / ice_only * 100, 1),
                    "ice_gco2e_per_km": DEFAULT_ICE_MOTORCYCLE_GCO2E_PER_KM,
                    "ev_kwh_per_km": DEFAULT_ELECTRIC_MOTORCYCLE_KWH_PER_KM,
                })
    out = pd.DataFrame(rows)
    out.to_csv(tables / "emission_grid_sensitivity.csv", index=False)
    print(out[out["mfc_count"].isin([20, 30, 40])].to_string(index=False))
    plot(out, PROJECT_ROOT / "outputs" / "figures" / "charts" / "emission_per_delivery.png")


def plot(out: pd.DataFrame, path: Path) -> None:
    import matplotlib.pyplot as plt
    from micro_fulfillment_network_jakarta.viz_theme import set_publication_theme

    set_publication_theme()
    fig, ax = plt.subplots(figsize=(10, 5.6))
    styles = {0: ("#15171a", "Petrol fleet"), 50: ("#d98c6c", "Half electric"), 100: ("#b63a1c", "Fully electric")}
    for ev, (colour, label) in styles.items():
        for grid, ls in ((650, "-"), (870, "--")):
            d = out[(out["ev_adoption_percent"] == ev) & (out["grid_gco2e_per_kwh"] == grid)].sort_values("mfc_count")
            if ev == 0 and grid == 870:
                continue  # a petrol fleet does not depend on the grid
            ax.plot(d["mfc_count"], d["gco2e_per_delivery"], color=colour, ls=ls, lw=2,
                    label=label if ev == 0 else f"{label}, grid {grid} g/kWh")
    ax.set_xlabel("Number of hubs")
    ax.set_ylabel("g CO2e per delivery, one way")
    ax.set_title("CO2e per delivery by network size and fleet", pad=22)
    ax.text(0, 1.015, "Scenario factors: petrol motorcycle 72 g/km, electric 0.035 kWh/km; one-way demand-weighted distance",
            transform=ax.transAxes, fontsize=9, color="#6f7378", va="bottom")
    ax.set_ylim(0, None)
    ax.grid(axis="y")
    ax.legend(loc="upper right")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
