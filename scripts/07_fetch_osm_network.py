from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
import networkx as nx
import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry.base import BaseGeometry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_metadata
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe


def sanitize_for_file(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Convert complex OSM attribute values to strings for stable GeoPackage writing."""
    output = gdf.copy()
    for column in output.columns:
        if column == "geometry":
            continue
        output[column] = output[column].map(
            lambda value: ", ".join(map(str, value)) if isinstance(value, list) else value
        )
        output[column] = output[column].map(
            lambda value: str(value) if isinstance(value, (dict, tuple, set)) else value
        )
    return output


def load_aoi_polygon() -> BaseGeometry:
    """Load AOI polygon in EPSG:4326 for OSMnx queries."""
    settings = get_settings()
    aoi_path = require_file(settings.aoi_dir / "aoi_default.geojson")
    aoi = gpd.read_file(aoi_path).to_crs(settings.default_crs)
    validate_geodataframe(aoi)
    return aoi.geometry.unary_union


def fetch_road_edges(polygon: BaseGeometry) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Fetch OSM drive road graph and return nodes and edges."""
    logger = get_logger("07_fetch_osm_network")
    logger.info("Requesting OSM drive road network through OSMnx.")

    graph: nx.MultiDiGraph = ox.graph_from_polygon(
        polygon,
        network_type="drive",
        simplify=True,
        retain_all=False,
        truncate_by_edge=True,
    )
    nodes, edges = ox.graph_to_gdfs(graph, nodes=True, edges=True)

    if nodes.empty or edges.empty:
        raise ValueError("OSMnx returned an empty road network.")

    logger.info(f"OSM graph downloaded with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
    return nodes, edges



def fetch_pois(polygon: BaseGeometry) -> gpd.GeoDataFrame:
    """Fetch commercial and logistics-relevant OSM POIs."""
    logger = get_logger("07_fetch_osm_network")

    tags: dict[str, Any] = {
        "shop": [
            "supermarket",
            "convenience",
            "department_store",
            "mall",
            "greengrocer",
            "general",
            "wholesale",
        ],
        "amenity": [
            "marketplace",
            "restaurant",
            "fast_food",
            "cafe",
        ],
        "building": [
            "retail",
            "commercial",
            "warehouse",
        ],
        "landuse": [
            "commercial",
            "retail",
            "industrial",
        ],
    }

    logger.info("Requesting OSM commercial and logistics-relevant POIs through OSMnx.")
    pois = ox.features_from_polygon(polygon, tags=tags)

    if pois.empty:
        raise ValueError("OSMnx returned no POIs for the selected tags.")

    pois = pois.reset_index()
    pois = pois[pois.geometry.notna()].copy()
    pois = pois[pois.geometry.is_valid].copy()

    return pois


def select_road_columns(edges: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep stable road columns needed for accessibility analysis."""
    keep_columns = [
        "osmid",
        "name",
        "highway",
        "oneway",
        "reversed",
        "length",
        "maxspeed",
        "geometry",
    ]
    available = [column for column in keep_columns if column in edges.columns]
    return edges[available].copy()


def select_node_columns(nodes: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep stable node columns needed for network diagnostics."""
    keep_columns = ["street_count", "highway", "geometry"]
    available = [column for column in keep_columns if column in nodes.columns]
    return nodes[available].copy()


def select_poi_columns(pois: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep stable POI columns needed for candidate screening."""
    keep_columns = [
        "osmid",
        "element_type",
        "name",
        "shop",
        "amenity",
        "building",
        "landuse",
        "geometry",
    ]
    available = [column for column in keep_columns if column in pois.columns]
    return pois[available].copy()


def main() -> None:
    """Fetch and cache OSM road network and POIs."""
    settings = get_settings()
    logger = get_logger("07_fetch_osm_network")

    output_dir = settings.raw_dir / "osm_network"
    roads_path = output_dir / "osm_roads_utm48s.gpkg"
    nodes_path = output_dir / "osm_road_nodes_utm48s.gpkg"
    pois_path = output_dir / "osm_commercial_pois_utm48s.gpkg"

    if roads_path.exists() and nodes_path.exists() and pois_path.exists():
        logger.info(f"Using cached file from {roads_path}")
        logger.info(f"Using cached file from {nodes_path}")
        logger.info(f"Using cached file from {pois_path}")
        return

    ox.settings.use_cache = True
    ox.settings.cache_folder = str(settings.project_root / "osmnx_cache")
    ox.settings.log_console = False
    ox.settings.timeout = 240
    ox.settings.overpass_rate_limit = True

    polygon = load_aoi_polygon()

    output_dir.mkdir(parents=True, exist_ok=True)

    nodes, edges = fetch_road_edges(polygon)
    pois = fetch_pois(polygon)

    roads = select_road_columns(edges).to_crs(settings.projected_crs)
    road_nodes = select_node_columns(nodes).to_crs(settings.projected_crs)
    commercial_pois = select_poi_columns(pois).to_crs(settings.projected_crs)

    roads = sanitize_for_file(roads)
    road_nodes = sanitize_for_file(road_nodes)
    commercial_pois = sanitize_for_file(commercial_pois)

    validate_geodataframe(roads)
    validate_geodataframe(road_nodes)
    validate_geodataframe(commercial_pois)

    logger.info(f"Writing OSM roads to {roads_path}")
    roads.to_file(roads_path, driver="GPKG", layer="roads")

    logger.info(f"Writing OSM road nodes to {nodes_path}")
    road_nodes.to_file(nodes_path, driver="GPKG", layer="nodes")

    logger.info(f"Writing OSM commercial POIs to {pois_path}")
    commercial_pois.to_file(pois_path, driver="GPKG", layer="pois")

    write_metadata(
        data_path=roads_path,
        dataset_name="OpenStreetMap drive road network",
        source="OpenStreetMap via OSMnx",
        source_url="https://www.openstreetmap.org/",
        license_name="Open Database License, ODbL",
        spatial_resolution="Vector road segments from OpenStreetMap clipped to Greater Jakarta AOI",
        temporal_coverage="Latest OpenStreetMap snapshot at access date",
        preprocessing_steps=[
            "Queried OSM drive road graph inside Greater Jakarta AOI",
            "Simplified graph topology using OSMnx",
            "Converted graph edges to GeoDataFrame",
            "Selected stable road attributes",
            "Reprojected road edges to EPSG:32748",
            "Saved to GeoPackage",
        ],
        unit="Road segment geometry with length in meters",
        citation_apa="OpenStreetMap contributors. (2025). OpenStreetMap geographic database.",
        citation_bibtex="@misc{osm2025, title={OpenStreetMap geographic database}, author={{OpenStreetMap contributors}}, year={2025}, url={https://www.openstreetmap.org/}}",
        crs=settings.projected_crs,
        extra={"download_tool": "OSMnx", "network_type": "drive"},
    )

    write_metadata(
        data_path=nodes_path,
        dataset_name="OpenStreetMap road network nodes",
        source="OpenStreetMap via OSMnx",
        source_url="https://www.openstreetmap.org/",
        license_name="Open Database License, ODbL",
        spatial_resolution="Vector road nodes from OpenStreetMap clipped to Greater Jakarta AOI",
        temporal_coverage="Latest OpenStreetMap snapshot at access date",
        preprocessing_steps=[
            "Queried OSM drive road graph inside Greater Jakarta AOI",
            "Converted graph nodes to GeoDataFrame",
            "Selected stable node attributes",
            "Reprojected nodes to EPSG:32748",
            "Saved to GeoPackage",
        ],
        unit="Road node geometry",
        citation_apa="OpenStreetMap contributors. (2025). OpenStreetMap geographic database.",
        citation_bibtex="@misc{osm2025, title={OpenStreetMap geographic database}, author={{OpenStreetMap contributors}}, year={2025}, url={https://www.openstreetmap.org/}}",
        crs=settings.projected_crs,
        extra={"download_tool": "OSMnx", "network_type": "drive"},
    )

    write_metadata(
        data_path=pois_path,
        dataset_name="OpenStreetMap commercial and logistics-relevant POIs",
        source="OpenStreetMap via OSMnx",
        source_url="https://www.openstreetmap.org/",
        license_name="Open Database License, ODbL",
        spatial_resolution="Vector POI geometries from OpenStreetMap clipped to Greater Jakarta AOI",
        temporal_coverage="Latest OpenStreetMap snapshot at access date",
        preprocessing_steps=[
            "Queried OSM features using commercial, retail, marketplace, food, warehouse, and landuse tags",
            "Removed missing and invalid geometries",
            "Selected stable POI attributes",
            "Reprojected POIs to EPSG:32748",
            "Saved to GeoPackage",
        ],
        unit="POI geometry",
        citation_apa="OpenStreetMap contributors. (2025). OpenStreetMap geographic database.",
        citation_bibtex="@misc{osm2025, title={OpenStreetMap geographic database}, author={{OpenStreetMap contributors}}, year={2025}, url={https://www.openstreetmap.org/}}",
        crs=settings.projected_crs,
        extra={
            "download_tool": "OSMnx",
            "poi_tags": {
                "shop": ["supermarket", "convenience", "department_store", "mall", "greengrocer", "general", "wholesale"],
                "amenity": ["marketplace", "restaurant", "fast_food", "cafe"],
                "building": ["retail", "commercial", "warehouse"],
                "landuse": ["commercial", "retail", "industrial"],
            },
            "interpretation_limit": "OSM POI completeness varies spatially and is treated as an accessibility and commercial intensity proxy.",
        },
    )

    logger.info("OSM network and POI download completed.")
    print(f"OSM roads completed: {roads_path}")
    print(f"OSM nodes completed: {nodes_path}")
    print(f"OSM POIs completed: {pois_path}")


if __name__ == "__main__":
    main()
