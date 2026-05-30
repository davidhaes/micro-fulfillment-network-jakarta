from __future__ import annotations

import json
import sys
from pathlib import Path

import folium
import geopandas as gpd
import h3
import pandas as pd
import plotly.express as px
import pydeck as pdk
from branca.colormap import linear

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe


def choose_reference_mfc_count(summary: pd.DataFrame) -> int:
    """Choose reference MFC count for interactive maps."""
    eligible = summary[summary["coverage_share"] >= 0.90].sort_values("mfc_count")
    if not eligible.empty:
        return int(eligible.iloc[0]["mfc_count"])
    return int(summary.sort_values(["coverage_share", "mfc_count"], ascending=[False, True]).iloc[0]["mfc_count"])


def add_h3_index(gdf: gpd.GeoDataFrame, resolution: int = 7) -> gpd.GeoDataFrame:
    """Add H3 cell index based on feature centroid for interactive inspection."""
    output = gdf.to_crs("EPSG:4326").copy()
    centroids = output.geometry.to_crs("EPSG:32748").centroid.to_crs(output.crs)
    output["h3_res7"] = [
        h3.geo_to_h3(float(point.y), float(point.x), resolution)
        for point in centroids
    ]
    return output


def create_interactive_demand_map(grid: gpd.GeoDataFrame, output_html: Path) -> None:
    """Create a Folium demand choropleth with tooltips."""
    web = add_h3_index(grid, resolution=7)

    _union = web.geometry.unary_union if hasattr(web.geometry, "union_all") else web.geometry.unary_union
    center = _union.centroid

    fmap = folium.Map(
        location=[center.y, center.x],
        zoom_start=10,
        tiles="CartoDB positron",
        control_scale=True,
    )

    values = web["demand_index"].fillna(0)
    colormap = linear.magma.scale(values.min(), values.max())
    colormap.caption = "Latent quick-commerce demand index"

    def style_function(feature):
        value = feature["properties"].get("demand_index")
        color = colormap(value if value is not None else 0)
        return {
            "fillColor": color,
            "color": "#333333",
            "weight": 0.15,
            "fillOpacity": 0.75,
        }

    fields = [
        "cell_id",
        "h3_res7",
        "demand_index",
        "population_count",
        "nighttime_lights",
        "built_probability",
        "commercial_poi_count",
        "cluster_label",
    ]
    fields = [field for field in fields if field in web.columns]

    folium.GeoJson(
        json.loads(web.to_json()),
        name="Demand index",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=fields, aliases=[field.replace("_", " ").title() for field in fields]),
    ).add_to(fmap)

    colormap.add_to(fmap)
    folium.LayerControl().add_to(fmap)

    output_html.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(output_html))


def create_interactive_mfc_map(
    grid: gpd.GeoDataFrame,
    selected_mfc: gpd.GeoDataFrame,
    p_value: int,
    output_html: Path,
) -> None:
    """Create a Folium map showing optimized MFC points and demand background."""
    web_grid = add_h3_index(grid, resolution=7)
    web_mfc = selected_mfc.to_crs("EPSG:4326").copy()
    center = web_grid.geometry.unary_union.centroid

    fmap = folium.Map(
        location=[center.y, center.x],
        zoom_start=10,
        tiles="CartoDB positron",
        control_scale=True,
    )

    demand_values = web_grid["demand_index"].fillna(0)
    colormap = linear.YlOrRd_09.scale(demand_values.min(), demand_values.max())
    colormap.caption = "Demand index"

    def style_function(feature):
        value = feature["properties"].get("demand_index")
        return {
            "fillColor": colormap(value if value is not None else 0),
            "color": "#333333",
            "weight": 0.12,
            "fillOpacity": 0.55,
        }

    folium.GeoJson(
        json.loads(web_grid.to_json()),
        name="Demand index",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["cell_id", "h3_res7", "demand_index", "cluster_label"],
            aliases=["Cell ID", "H3 Index", "Demand Index", "Cluster"],
        ),
    ).add_to(fmap)

    for _, row in web_mfc.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=6,
            color="#D32F2F",
            weight=2,
            fill=True,
            fill_color="#D32F2F",
            fill_opacity=0.95,
            popup=folium.Popup(
                html=(
                    f"<b>Scenario:</b> p={p_value}<br>"
                    f"<b>Selected order:</b> {int(row.get('selected_order', 0))}<br>"
                    f"<b>Candidate ID:</b> {row.get('candidate_id', 'unknown')}<br>"
                    f"<b>Demand index:</b> {float(row.get('demand_index', 0)):.3f}"
                ),
                max_width=280,
            ),
        ).add_to(fmap)

    colormap.add_to(fmap)
    folium.LayerControl().add_to(fmap)

    output_html.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(output_html))


def create_pydeck_mfc_map(selected_mfc: gpd.GeoDataFrame, output_html: Path) -> None:
    """Create a PyDeck point map for selected MFCs."""
    web = selected_mfc.to_crs("EPSG:4326").copy()
    web["lon"] = web.geometry.x
    web["lat"] = web.geometry.y
    web["radius_m"] = 350
    web["fill_color"] = [[211, 47, 47, 190] for _ in range(len(web))]


    _union = web.geometry.unary_union if hasattr(web.geometry, "union_all") else web.geometry.unary_union
    center = _union.centroid

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=web.drop(columns="geometry"),
        get_position="[lon, lat]",
        get_radius="radius_m",
        get_fill_color="fill_color",
        pickable=True,
        stroked=True,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
    )

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=center.y, longitude=center.x, zoom=10, pitch=0),
        tooltip={
            "html": "<b>Candidate:</b> {candidate_id}<br><b>Order:</b> {selected_order}<br><b>Demand index:</b> {demand_index}",
            "style": {"backgroundColor": "white", "color": "black"},
        },
        map_style="light",
    )

    output_html.parent.mkdir(parents=True, exist_ok=True)
    deck.to_html(str(output_html), open_browser=False)


def create_emission_dashboard(emissions: pd.DataFrame, output_html: Path) -> None:
    """Create interactive Plotly emission scenario chart."""
    frame = emissions.copy()
    frame["ev_adoption_label"] = frame["ev_adoption_percent"].astype(int).astype(str) + "% EV adoption"

    fig = px.line(
        frame,
        x="mfc_count",
        y="emission_reduction_percent",
        color="ev_adoption_label",
        markers=True,
        template="plotly_white",
        title="Interactive CO2e Reduction Pathway, MFC Count and EV Adoption Scenarios",
        labels={
            "mfc_count": "Number of MFCs",
            "emission_reduction_percent": "Emission reduction, percent",
            "ev_adoption_label": "EV adoption",
        },
        hover_data=[
            "coverage_share",
            "distance_reduction_percent",
            "scenario_emissions_kgco2e",
            "baseline_emissions_kgco2e",
        ],
    )
    fig.add_hline(y=30, line_dash="dash", line_color="#333333", annotation_text="30% benchmark")
    fig.update_layout(legend_title_text="Scenario", hovermode="x unified")

    output_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_html), include_plotlyjs="cdn")


def main() -> None:
    """Generate interactive maps and dashboards."""
    settings = get_settings()
    logger = get_logger("18_generate_interactive_maps")

    output_dir = settings.outputs_dir / "maps_interactive"
    output_dir.mkdir(parents=True, exist_ok=True)

    clusters_path = require_file(settings.processed_dir / "demand_clusters.gpkg")
    selected_path = require_file(settings.processed_dir / "optimized_mfc_networks.gpkg")
    summary_path = require_file(settings.tables_dir / "optimized_network_summary.csv")
    emissions_path = require_file(settings.tables_dir / "emission_scenarios.csv")

    grid = gpd.read_file(clusters_path, layer="demand_clusters")
    selected_all = gpd.read_file(selected_path, layer="optimized_mfc_networks")
    summary = pd.read_csv(summary_path)
    emissions = pd.read_csv(emissions_path)

    validate_geodataframe(grid, required_columns=["demand_index", "cluster_label"])
    validate_geodataframe(selected_all, required_columns=["mfc_count"])

    p_value = choose_reference_mfc_count(summary)
    selected_mfc = selected_all[selected_all["mfc_count"] == p_value].copy()

    logger.info("Creating interactive demand map.")
    create_interactive_demand_map(
        grid=grid,
        output_html=output_dir / "interactive_demand_index_map.html",
    )

    logger.info("Creating interactive MFC network map.")
    create_interactive_mfc_map(
        grid=grid,
        selected_mfc=selected_mfc,
        p_value=p_value,
        output_html=output_dir / "interactive_optimized_mfc_network_map.html",
    )

    logger.info("Creating PyDeck selected MFC map.")
    create_pydeck_mfc_map(
        selected_mfc=selected_mfc,
        output_html=output_dir / "pydeck_selected_mfc_map.html",
    )

    logger.info("Creating interactive emission dashboard.")
    create_emission_dashboard(
        emissions=emissions,
        output_html=output_dir / "interactive_emission_scenario_dashboard.html",
    )

    logger.info("Interactive outputs completed.")
    print(f"Interactive maps completed in: {output_dir}")


if __name__ == "__main__":
    main()
