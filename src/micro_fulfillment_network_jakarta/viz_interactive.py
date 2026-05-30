from __future__ import annotations

from pathlib import Path

import folium
import geopandas as gpd
import plotly.express as px
import pydeck as pdk


def make_folium_choropleth(
    gdf: gpd.GeoDataFrame,
    value_column: str,
    tooltip_columns: list[str],
    output_html: Path,
    title: str,
) -> Path:
    """Create an interactive Folium choropleth map using direct GeoJson styling."""
    if value_column not in gdf.columns:
        raise KeyError(f"Missing value column: {value_column}")

    web_gdf = gdf.to_crs("EPSG:4326").copy()
    centroid = web_gdf.geometry.unary_union.centroid

    vmin = float(web_gdf[value_column].min())
    vmax = float(web_gdf[value_column].max())

    fmap = folium.Map(location=[centroid.y, centroid.x], zoom_start=10, tiles="CartoDB positron")

    def normalize(value: float) -> float:
        if vmax <= vmin:
            return 0.0
        return max(0.0, min(1.0, (float(value) - vmin) / (vmax - vmin)))

    def color(value: float) -> str:
        ratio = normalize(value)
        if ratio < 0.2:
            return "#FFFFCC"
        if ratio < 0.4:
            return "#A1DAB4"
        if ratio < 0.6:
            return "#41B6C4"
        if ratio < 0.8:
            return "#2C7FB8"
        return "#253494"

    def style_function(feature):
        value = feature["properties"].get(value_column, 0.0)
        return {
            "fillColor": color(value),
            "color": "#333333",
            "weight": 0.3,
            "fillOpacity": 0.75,
        }

    fields = [field for field in tooltip_columns if field in web_gdf.columns]

    folium.GeoJson(
        web_gdf,
        name=title,
        tooltip=folium.GeoJsonTooltip(fields=fields),
        style_function=style_function,
    ).add_to(fmap)

    folium.LayerControl().add_to(fmap)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(output_html))
    return output_html


def make_plotly_scenario_chart(frame, x: str, y: str, color: str, output_html: Path, title: str) -> Path:
    """Create an interactive Plotly scenario line chart."""
    fig = px.line(frame, x=x, y=y, color=color, markers=True, title=title)
    fig.update_layout(template="plotly_white")
    output_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_html), include_plotlyjs="cdn")
    return output_html


def make_pydeck_point_map(points: gpd.GeoDataFrame, output_html: Path, title: str) -> Path:
    """Create an interactive PyDeck point map for MFC candidates."""
    web_points = points.to_crs("EPSG:4326").copy()
    web_points["lon"] = web_points.geometry.x
    web_points["lat"] = web_points.geometry.y

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=web_points.drop(columns="geometry"),
        get_position="[lon, lat]",
        get_radius=250,
        get_fill_color=[211, 47, 47, 180],
        pickable=True,
    )

    center = web_points.geometry.unary_union.centroid
    view_state = pdk.ViewState(latitude=center.y, longitude=center.x, zoom=10, pitch=0)

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": title},
        map_style="light",
    )

    output_html.parent.mkdir(parents=True, exist_ok=True)
    deck.to_html(str(output_html), open_browser=False)
    return output_html
