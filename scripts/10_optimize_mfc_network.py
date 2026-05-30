from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_csv, write_metadata
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.optimization import (
    compute_coverage,
    compute_euclidean_distance_matrix,
    greedy_p_median,
)
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe


DETOUR_FACTOR = 1.35
MAX_DEMAND_POINTS = 2500
MAX_CANDIDATES = 350
BASELINE_HUB_LON = 106.8272
BASELINE_HUB_LAT = -6.1754


def load_demand_grid(path: Path) -> gpd.GeoDataFrame:
    """Load demand grid and filter cells with positive demand."""
    grid = gpd.read_file(path, layer="demand_grid")
    validate_geodataframe(grid, required_columns=["cell_id", "demand_index", "proxy_deliveries_per_100k"])
    grid = grid[grid["demand_index"].fillna(0) > 0].copy()
    grid = grid.reset_index(drop=True)
    return grid


def drop_extra_geometry_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Drop non-active geometry-like columns before writing a GeoPackage."""
    output = gdf.copy()
    active_geometry_name = output.geometry.name
    drop_columns: list[str] = []

    for column in output.columns:
        if column == active_geometry_name:
            continue
        sample = output[column].dropna().head(10)
        if sample.empty:
            continue
        if any(hasattr(value, "geom_type") for value in sample):
            drop_columns.append(column)

    if drop_columns:
        output = output.drop(columns=drop_columns)

    return output


def build_candidate_points(grid: gpd.GeoDataFrame, pois_path: Path) -> gpd.GeoDataFrame:
    """Build candidate MFC points from high-demand cells and commercial POIs."""
    logger = get_logger("10_optimize_mfc_network")
    pois = gpd.read_file(pois_path).to_crs(grid.crs)
    validate_geodataframe(pois)

    high_demand = grid[
        (grid["demand_percentile"] >= 0.70)
        & (grid["built_probability"].fillna(0) >= 0.05)
    ].copy()

    if high_demand.empty:
        logger.info("No high-demand cells passed the candidate threshold. Falling back to top demand cells.")
        high_demand = grid.sort_values("demand_index", ascending=False).head(MAX_CANDIDATES).copy()

    poi_points = pois.copy()
    poi_points["geometry"] = poi_points.geometry.representative_point()

    joined = gpd.sjoin(
        poi_points[["geometry"]],
        high_demand[["cell_id", "demand_index", "geometry"]],
        how="inner",
        predicate="within",
    )

    if joined.empty:
        logger.info("No POI-based candidates found inside high-demand cells. Falling back to high-demand cell centroids.")
        fallback = high_demand.sort_values("demand_index", ascending=False).head(MAX_CANDIDATES).copy()
        non_geometry = fallback.drop(columns="geometry").copy()
        candidates = gpd.GeoDataFrame(
            non_geometry,
            geometry=fallback.geometry.centroid,
            crs=grid.crs,
        )
        candidates["candidate_source"] = "high_demand_cell_centroid"
    else:
        candidates = joined.merge(
            high_demand.drop(columns="geometry"),
            on="cell_id",
            how="left",
            suffixes=("", "_cell"),
        )
        candidates = gpd.GeoDataFrame(candidates, geometry="geometry", crs=grid.crs)
        candidates["candidate_source"] = "osm_commercial_poi_in_high_demand_cell"

    candidates = candidates.sort_values("demand_index", ascending=False).drop_duplicates(subset=["cell_id"])
    candidates = candidates.head(MAX_CANDIDATES).copy().reset_index(drop=True)
    candidates["candidate_id"] = [f"mfc_candidate_{i + 1:04d}" for i in range(len(candidates))]
    candidates["candidate_rank"] = np.arange(1, len(candidates) + 1)

    keep_columns = [
        "candidate_id",
        "candidate_rank",
        "candidate_source",
        "cell_id",
        "demand_index",
        "population_count",
        "nighttime_lights",
        "built_probability",
        "road_length_m_intersecting",
        "commercial_poi_count",
        "geometry",
    ]
    keep_columns = [column for column in keep_columns if column in candidates.columns]
    candidates = candidates[keep_columns].copy()
    candidates = drop_extra_geometry_columns(candidates)
    return candidates


def select_demand_points(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Select demand point centroids for optimization while preserving normalized demand weights."""
    selected = grid.sort_values("demand_index", ascending=False).head(MAX_DEMAND_POINTS).copy()
    selected = selected.reset_index(drop=True)

    geometry = selected.geometry.centroid
    non_geometry = selected.drop(columns="geometry").copy()

    demand_points = gpd.GeoDataFrame(
        non_geometry,
        geometry=geometry,
        crs=grid.crs,
    )

    total_selected_weight = float(demand_points["proxy_deliveries_per_100k"].sum())
    if total_selected_weight <= 0:
        total_selected_weight = float(demand_points["demand_index"].sum())
        demand_points["optimization_weight"] = demand_points["demand_index"] / total_selected_weight * 100000.0
    else:
        demand_points["optimization_weight"] = demand_points["proxy_deliveries_per_100k"] / total_selected_weight * 100000.0

    return demand_points


def coordinates_array(gdf: gpd.GeoDataFrame) -> np.ndarray:
    """Return Nx2 coordinate array from point geometries."""
    return np.column_stack([gdf.geometry.x.to_numpy(), gdf.geometry.y.to_numpy()])


def baseline_hub_point(projected_crs: str) -> Point:
    """Return representative centralized fulfillment baseline hub near central Jakarta."""
    transformer = Transformer.from_crs("EPSG:4326", projected_crs, always_xy=True)
    x, y = transformer.transform(BASELINE_HUB_LON, BASELINE_HUB_LAT)
    return Point(x, y)


def main() -> None:
    """Optimize MFC network scenarios."""
    settings = get_settings()
    logger = get_logger("10_optimize_mfc_network")

    demand_path = require_file(settings.processed_dir / "demand_grid.gpkg")
    pois_path = require_file(settings.raw_dir / "osm_network" / "osm_commercial_pois_utm48s.gpkg")

    candidates_path = settings.processed_dir / "mfc_candidates.gpkg"
    selected_path = settings.processed_dir / "optimized_mfc_networks.gpkg"
    coverage_path = settings.processed_dir / "service_coverage.gpkg"
    summary_path = settings.tables_dir / "optimized_network_summary.csv"
    candidate_ranking_path = settings.tables_dir / "mfc_candidate_ranking.csv"

    if selected_path.exists() and summary_path.exists() and coverage_path.exists():
        logger.info(f"Using cached file from {selected_path}")
        logger.info(f"Using cached file from {coverage_path}")
        logger.info(f"Using cached file from {summary_path}")
        return

    graph_type_hint = nx.MultiDiGraph
    logger.info(f"NetworkX available for future routing extension: {graph_type_hint.__name__}")

    grid = load_demand_grid(demand_path)
    candidates = build_candidate_points(grid, pois_path)
    demand_points = select_demand_points(grid)

    if candidates.empty:
        raise ValueError("No MFC candidates generated.")

    demand_xy = coordinates_array(demand_points)
    candidate_xy = coordinates_array(candidates)

    logger.info(f"Computing distance matrix for {len(demand_points)} demand cells and {len(candidates)} candidates.")
    euclidean_distance = compute_euclidean_distance_matrix(demand_xy, candidate_xy)
    route_distance = euclidean_distance * DETOUR_FACTOR

    weights = demand_points["optimization_weight"].astype(float).to_numpy()
    if np.isclose(weights.sum(), 0.0):
        raise ValueError("Optimization weights sum to zero.")

    reachable_route_distance_m = settings.default_speed_kmh * 1000.0 * (settings.service_level_minutes / 60.0)
    threshold_meters = reachable_route_distance_m

    selected_records: list[gpd.GeoDataFrame] = []
    summary_records: list[dict] = []

    baseline_point = baseline_hub_point(settings.projected_crs)
    baseline_distances_m = np.array([geom.distance(baseline_point) * DETOUR_FACTOR for geom in demand_points.geometry])
    baseline_total_distance_km = float(np.sum((baseline_distances_m / 1000.0) * weights))
    baseline_mean_distance_km = float(np.average(baseline_distances_m / 1000.0, weights=weights))

    logger.info(f"Baseline proxy total distance per 100k normalized proxy deliveries: {baseline_total_distance_km:.2f} km")

    coverage_grid = grid.copy()

    for p in settings.mfc_counts:
        logger.info(f"Running greedy p-median optimization for p={p}.")
        selected_indices = greedy_p_median(route_distance, weights, p=p)

        coverage = compute_coverage(
            distance_matrix=route_distance,
            weights=weights,
            selected_indices=selected_indices,
            threshold_meters=threshold_meters,
        )

        nearest_distance_m = np.min(route_distance[:, selected_indices], axis=1)
        total_distance_km = float(np.sum((nearest_distance_m / 1000.0) * weights))
        mean_distance_km = float(np.average(nearest_distance_m / 1000.0, weights=weights))

        distance_reduction_percent = (
            (baseline_total_distance_km - total_distance_km) / baseline_total_distance_km * 100.0
            if baseline_total_distance_km > 0
            else np.nan
        )

        selected_candidates = candidates.iloc[selected_indices].copy()
        selected_candidates["mfc_count"] = int(p)
        selected_candidates["scenario_id"] = f"p_{p}"
        selected_candidates["selected_order"] = np.arange(1, len(selected_candidates) + 1)
        selected_records.append(selected_candidates)

        summary_records.append(
            {
                "scenario_id": f"p_{p}",
                "mfc_count": int(p),
                "selected_candidate_count": int(len(selected_indices)),
                "service_level_minutes": float(settings.service_level_minutes),
                "default_speed_kmh": float(settings.default_speed_kmh),
                "detour_factor": float(DETOUR_FACTOR),
                "coverage_share": float(coverage["coverage_share"]),
                "covered_proxy_deliveries_per_100k": float(coverage["covered_weight"]),
                "total_proxy_deliveries_per_100k": float(coverage["total_weight"]),
                "mean_nearest_distance_km": mean_distance_km,
                "p90_nearest_distance_km": float(coverage["p90_nearest_distance_m"] / 1000.0),
                "max_nearest_distance_km": float(coverage["max_nearest_distance_m"] / 1000.0),
                "demand_weighted_distance_km": total_distance_km,
                "baseline_demand_weighted_distance_km": baseline_total_distance_km,
                "baseline_mean_distance_km": baseline_mean_distance_km,
                "distance_reduction_percent": float(distance_reduction_percent),
                "demand_point_count_used": int(len(demand_points)),
                "candidate_count_used": int(len(candidates)),
            }
        )

        selected_xy = candidate_xy[selected_indices]
        nearest_all_grid = []
        for geom in grid.geometry.centroid:
            distances = np.sqrt((selected_xy[:, 0] - geom.x) ** 2 + (selected_xy[:, 1] - geom.y) ** 2) * DETOUR_FACTOR
            nearest_all_grid.append(float(distances.min()))

        coverage_grid[f"nearest_mfc_distance_km_p{p}"] = np.array(nearest_all_grid) / 1000.0
        coverage_grid[f"covered_30min_p{p}"] = coverage_grid[f"nearest_mfc_distance_km_p{p}"] <= (threshold_meters / 1000.0)

    selected_all = pd.concat(selected_records, ignore_index=True)
    selected_all = gpd.GeoDataFrame(selected_all, geometry="geometry", crs=grid.crs)
    selected_all = drop_extra_geometry_columns(selected_all)

    summary = pd.DataFrame(summary_records)

    best_coverage = summary.sort_values(["coverage_share", "mfc_count"], ascending=[False, True]).iloc[0]
    p_for_underserved = int(best_coverage["mfc_count"])
    coverage_grid["underserved_score"] = (
        coverage_grid["demand_index"].astype(float)
        * (~coverage_grid[f"covered_30min_p{p_for_underserved}"].astype(bool)).astype(float)
    )
    coverage_grid["reference_mfc_count_for_underserved"] = p_for_underserved

    candidates_to_write = drop_extra_geometry_columns(candidates)
    coverage_grid_to_write = drop_extra_geometry_columns(coverage_grid)

    logger.info(f"Writing MFC candidates to {candidates_path}")
    candidates_to_write.to_file(candidates_path, driver="GPKG", layer="mfc_candidates")

    logger.info(f"Writing optimized MFC networks to {selected_path}")
    selected_all.to_file(selected_path, driver="GPKG", layer="optimized_mfc_networks")

    logger.info(f"Writing service coverage grid to {coverage_path}")
    coverage_grid_to_write.to_file(coverage_path, driver="GPKG", layer="service_coverage")

    write_csv(summary, summary_path)
    write_csv(candidates.drop(columns="geometry"), candidate_ranking_path)

    write_metadata(
        data_path=candidates_path,
        dataset_name="Candidate micro-fulfillment center locations",
        source="Derived from demand grid and OpenStreetMap commercial POIs",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m demand grid with candidate points",
        temporal_coverage="Composite proxy using latest available open datasets",
        preprocessing_steps=[
            "Selected high-demand grid cells above 70th percentile",
            "Filtered cells with built probability at least 0.05",
            "Selected commercial OSM POIs inside high-demand cells",
            "Fell back to high-demand cell centroids if POI candidates were unavailable",
            f"Limited candidates to top {MAX_CANDIDATES} for computational stability",
        ],
        unit="Candidate point",
        citation_apa="Derived candidate MFC locations from open geospatial data.",
        citation_bibtex="@misc{mfcCandidates2025, title={Candidate micro-fulfillment center locations for Greater Jakarta}, author={Project pipeline}, year={2025}}",
        crs=settings.projected_crs,
    )

    write_metadata(
        data_path=selected_path,
        dataset_name="Optimized MFC network scenarios",
        source="Derived p-median optimization output",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution="Point facilities selected from candidate set",
        temporal_coverage="Scenario-based facility location analysis",
        preprocessing_steps=[
            "Selected demand-weighted p-median locations using vectorized greedy deterministic heuristic",
            "Applied corrected Euclidean distance with detour factor 1.35",
            "Evaluated MFC count scenarios from project configuration",
            "Computed 30-minute coverage using default speed assumption",
            "Normalized selected demand subset to 100,000 proxy deliveries for comparable scenario accounting",
        ],
        unit="Selected facility point by scenario",
        citation_apa="Hakimi, S. L. (1964). Optimum locations of switching centers and the absolute centers and medians of a graph. Operations Research.",
        citation_bibtex="@article{hakimi1964, title={Optimum locations of switching centers and the absolute centers and medians of a graph}, author={Hakimi, S. L.}, journal={Operations Research}, year={1964}}",
        crs=settings.projected_crs,
        extra={
            "detour_factor": DETOUR_FACTOR,
            "baseline_hub": {"longitude": BASELINE_HUB_LON, "latitude": BASELINE_HUB_LAT},
            "max_demand_points": MAX_DEMAND_POINTS,
            "max_candidates": MAX_CANDIDATES,
        },
    )

    write_metadata(
        data_path=coverage_path,
        dataset_name="Service coverage and underserved demand grid",
        source="Derived from optimized MFC network scenarios",
        source_url="Local pipeline output",
        license_name="Derived open data",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m grid",
        temporal_coverage="Scenario-based service coverage analysis",
        preprocessing_steps=[
            "Computed nearest selected MFC distance for each grid cell",
            "Applied corrected Euclidean distance with detour factor 1.35",
            "Classified 30-minute service coverage for each MFC count scenario",
            "Computed underserved score as demand index multiplied by uncovered status under reference scenario",
        ],
        unit="Grid cell with distance, coverage status, and underserved score",
        citation_apa="Derived service coverage analysis from open geospatial data.",
        citation_bibtex="@misc{serviceCoverage2025, title={Thirty-minute service coverage for Greater Jakarta quick-commerce MFC scenarios}, author={Project pipeline}, year={2025}}",
        crs=settings.projected_crs,
    )

    logger.info("MFC optimization completed.")
    print(f"MFC candidates completed: {candidates_path}")
    print(f"Optimized networks completed: {selected_path}")
    print(f"Network summary completed: {summary_path}")


if __name__ == "__main__":
    main()
