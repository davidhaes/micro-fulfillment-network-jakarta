from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_text
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import require_file


def pct(value: float) -> str:
    """Format numeric percent."""
    if abs(value) <= 1.5:
        return f"{value * 100:.1f}%"
    return f"{value:.1f}%"


def choose_reference(summary: pd.DataFrame) -> pd.Series:
    """Choose smallest MFC count reaching 90 percent coverage, otherwise best coverage."""
    eligible = summary[summary["coverage_share"] >= 0.90].sort_values("mfc_count")
    if not eligible.empty:
        return eligible.iloc[0]
    return summary.sort_values(["coverage_share", "mfc_count"], ascending=[False, True]).iloc[0]


def build_public_brief(reference: pd.Series, best_distance: pd.Series, best_emission: pd.Series, top_admin: pd.Series) -> str:
    """Build concise public-facing project brief."""
    return f"""# Public Project Brief

## Headline

Thirty-minute quick commerce in Greater Jakarta cannot be solved by adding micro-fulfillment centers alone.

## Key Results

* 30 optimized MFCs cover {pct(float(reference["coverage_share"]))} of proxy demand within the 30-minute threshold.
* Demand-weighted distance falls by {pct(float(best_distance["distance_reduction_percent"]))} versus centralized fulfillment.
* The best tested CO2e scenario reduces emissions by {pct(float(best_emission["emission_reduction_percent"]))} per 100,000 proxy deliveries.
* The largest underserved bottleneck appears in {top_admin["NAME_2"]}.
* Demand is an open-data proxy, not actual platform order volume.

## Strategic Takeaway

Micro-fulfillment reduces distance and emissions, but uniform 30-minute coverage across Greater Jakarta requires a segmented service strategy. Dense urban cores should be densified and electrified, while fringe regencies need selective MFCs, staging points, and 45–60 minute service tiers.

## Suggested Short Caption

30 MFCs reduce last-mile distance dramatically, but they do not solve 30-minute coverage for Greater Jakarta. The remaining gap is spatially clustered in fringe regencies, especially Tangerang, Bekasi, and Bogor.

## Recommended Visuals

* `outputs/figures/maps/optimized_mfc_network_map.png`
* `outputs/figures/maps/thirty_minute_service_coverage_map.png`
* `outputs/figures/maps/underserved_hotspot_lisa_map.png`
* `outputs/figures/charts/emission_scenario_pathway.png`
* `outputs/figures/charts/enhanced_extended_mfc_coverage_curve.png`
"""


def build_public_article(reference: pd.Series, best_distance: pd.Series, best_emission: pd.Series, top_admin: pd.Series, moran_underserved: pd.Series) -> str:
    """Build longer public-facing article draft without platform-specific naming."""
    return f"""# Public Article Draft

## Why micro-fulfillment alone is not enough for Greater Jakarta quick commerce

Quick commerce depends on proximity. If inventory is too far from demand, every delivery becomes slower, more expensive, and more carbon-intensive. This project evaluates whether an optimized micro-fulfillment center network can improve 30-minute service coverage and reduce last-mile CO2e in Greater Jakarta.

The analysis uses only open data. Demand is modeled as a latent proxy from WorldPop population, VIIRS nighttime lights, Dynamic World built-up probability, OpenStreetMap accessibility, and commercial POI density. It is not actual platform order volume.

The result is clear: 30 optimized MFCs cover {pct(float(reference["coverage_share"]))} of proxy demand within the modeled 30-minute threshold. They reduce demand-weighted distance by {pct(float(best_distance["distance_reduction_percent"]))}, but they do not solve metropolitan-wide coverage.

The strongest emission scenario reduces CO2e by {pct(float(best_emission["emission_reduction_percent"]))} per 100,000 proxy deliveries. This shows that decarbonization is most effective when fulfillment proximity and EV adoption work together.

The spatial bottleneck is not the dense urban core. The largest underserved signal appears in {top_admin["NAME_2"]}, and underserved clustering is statistically strong with Moran’s I of {float(moran_underserved["moran_i"]):.3f}. This supports a cluster-based intervention strategy.

The practical implication is segmentation. Core urban areas are better suited for densification and electrification. Fringe regencies need selective MFCs, rider staging points, and realistic 45–60 minute service tiers.

## Key limitation

This is an open-data strategic planning framework. It should be calibrated with actual order density, delivery time, rider GPS, and facility cost before deployment.
"""


def build_publication_guide() -> str:
    """Build platform-neutral publication and portfolio guide."""
    return """# Publication Guide

## Repository Positioning

Use the repository as a reproducible geospatial optimization portfolio project. Emphasize methodology, reproducibility, and decision value.

## Recommended Portfolio Assets

* Executive summary.
* Optimized MFC network map.
* Service coverage map.
* Underserved hotspot map.
* Emission scenario chart.
* Enhanced MFC sensitivity chart.

## Recommended Short Project Description

Open-data geospatial optimization framework for quick-commerce micro-fulfillment network design, 30-minute service coverage, underserved hotspot detection, and last-mile CO2e scenario modeling in Greater Jakarta.

## Suggested Audience

* Urban logistics practitioners.
* E-commerce operations teams.
* ESG and sustainability analysts.
* Geospatial data science recruiters.
* Transport and city logistics researchers.

## Communication Guardrails

* Do not claim actual platform order volume.
* State that demand is an open-data proxy.
* State that emissions are scenario-based per 100,000 proxy deliveries.
* State that travel distance is corrected Euclidean, not live traffic routing.
"""


def main() -> None:
    """Generate public-facing communication drafts."""
    settings = get_settings()
    logger = get_logger("20_generate_public_brief")

    summary_path = require_file(settings.tables_dir / "optimized_network_summary.csv")
    emissions_path = require_file(settings.tables_dir / "emission_scenarios.csv")
    admin_path = require_file(settings.tables_dir / "admin_unit_demand_summary.csv")
    moran_path = require_file(settings.tables_dir / "spatial_autocorrelation.csv")

    summary = pd.read_csv(summary_path)
    emissions = pd.read_csv(emissions_path)
    admin = pd.read_csv(admin_path)
    moran = pd.read_csv(moran_path)

    reference = choose_reference(summary)
    best_distance = summary.sort_values("distance_reduction_percent", ascending=False).iloc[0]
    best_emission = emissions.sort_values("emission_reduction_percent", ascending=False).iloc[0]
    top_admin = admin.sort_values("mean_underserved_score", ascending=False).iloc[0]
    moran_underserved = moran[moran["metric"] == "underserved_score"].iloc[0]

    content_dir = settings.project_root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    write_text(content_dir / "public_brief.md", build_public_brief(reference, best_distance, best_emission, top_admin))
    write_text(content_dir / "public_article.md", build_public_article(reference, best_distance, best_emission, top_admin, moran_underserved))
    write_text(content_dir / "publication_guide.md", build_publication_guide())

    logger.info(f"Public brief saved to {content_dir / 'public_brief.md'}")
    logger.info(f"Public article saved to {content_dir / 'public_article.md'}")
    logger.info(f"Publication guide saved to {content_dir / 'publication_guide.md'}")
    print(f"Public-facing communication files completed in: {content_dir}")


if __name__ == "__main__":
    main()