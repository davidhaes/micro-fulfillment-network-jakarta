from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import xy
from shapely.geometry import box
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import write_csv, write_metadata
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.preprocessing import min_max_scale, safe_log1p, weighted_overlay
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe, validate_raster


def read_single_band(path: Path) -> tuple[np.ndarray, rasterio.Affine, object, float | None]:
    """Read the first band of a raster as a float array."""
    with rasterio.open(path) as dataset:
        array = dataset.read(1).astype("float64")
        nodata = dataset.nodata
        transform = dataset.transform
        crs = dataset.crs
    if nodata is not None:
        array = np.where(array == nodata, np.nan, array)
    return array, transform, crs, nodata


def build_grid_from_reference(pop_path: Path, aoi_path: Path) -> gpd.GeoDataFrame:
    """Build 1 km grid polygons from the reference population raster."""
    logger = get_logger("09_build_demand_index")
    population, transform, crs, _ = read_single_band(pop_path)

    aoi = gpd.read_file(aoi_path).to_crs(crs)
    aoi_union = aoi.geometry.unary_union

    records: list[dict] = []
    height, width = population.shape

    logger.info("Building analysis grid from reference raster.")
    for row in tqdm(range(height), desc="Creating grid rows"):
        for col in range(width):
            value = population[row, col]
            if not np.isfinite(value):
                continue

            x_left, y_top = xy(transform, row, col, offset="ul")
            x_right, y_bottom = xy(transform, row, col, offset="lr")
            geom = box(x_left, y_bottom, x_right, y_top)

            if not geom.intersects(aoi_union):
                continue

            clipped = geom.intersection(aoi_union)
            if clipped.is_empty:
                continue

            records.append(
                {
                    "cell_id": f"cell_{row}_{col}",
                    "raster_row": int(row),
                    "raster_col": int(col),
                    "population_count": float(max(value, 0.0)),
                    "geometry": clipped,
                }
            )

    grid = gpd.GeoDataFrame(records, geometry="geometry", crs=crs)
    grid["area_m2"] = grid.geometry.area
    grid = grid[grid["area_m2"] > 0].reset_index(drop=True)
    return grid


def attach_raster_values(grid: gpd.GeoDataFrame, raster_path: Path, output_column: str) -> gpd.GeoDataFrame:
    """Attach raster values to grid cells by sampling raster values at grid centroids."""
    output = grid.copy()

    with rasterio.open(raster_path) as dataset:
        raster_crs = dataset.crs
        nodata = dataset.nodata

        sample_gdf = output.to_crs(raster_crs) if output.crs != raster_crs else output.copy()
        centroids = sample_gdf.geometry.centroid
        coordinates = [(float(point.x), float(point.y)) for point in centroids]

        sampled_values = []
        for sample in dataset.sample(coordinates):
            value = float(sample[0])
            if nodata is not None and np.isclose(value, nodata):
                sampled_values.append(np.nan)
            elif not np.isfinite(value):
                sampled_values.append(np.nan)
            else:
                sampled_values.append(value)

    output[output_column] = sampled_values
    return output




def compute_road_accessibility(grid: gpd.GeoDataFrame, roads_path: Path) -> pd.DataFrame:
    """Compute clipped road length per grid cell to avoid over-counting long road segments."""
    logger = get_logger("09_build_demand_index")
    roads = gpd.read_file(roads_path).to_crs(grid.crs)
    validate_geodataframe(roads)

    roads = roads[roads.geometry.notna() & roads.geometry.is_valid & ~roads.geometry.is_empty].copy()
    roads = roads.reset_index(drop=True)
    roads["road_id"] = [f"road_{i}" for i in range(len(roads))]

    grid_subset = grid[["cell_id", "geometry"]].copy()

    logger.info("Computing clipped road length by grid cell.")
    joined = gpd.sjoin(
        roads[["road_id", "geometry"]],
        grid_subset,
        how="inner",
        predicate="intersects",
    )

    if joined.empty:
        return pd.DataFrame(columns=["cell_id", "road_length_m_intersecting"])

    joined = joined.merge(
        grid_subset.rename(columns={"geometry": "cell_geometry"}),
        on="cell_id",
        how="left",
    )

    clipped_lengths = []
    for _, row in tqdm(joined.iterrows(), total=len(joined), desc="Clipping road segments"):
        road_geom = row.geometry
        cell_geom = row.cell_geometry
        if road_geom is None or cell_geom is None:
            clipped_lengths.append(0.0)
            continue
        intersection = road_geom.intersection(cell_geom)
        clipped_lengths.append(float(intersection.length) if not intersection.is_empty else 0.0)

    joined["road_length_m_intersecting"] = clipped_lengths

    road_summary = (
        joined.groupby("cell_id", as_index=False)["road_length_m_intersecting"]
        .sum()
    )
    return road_summary



def compute_poi_density(grid: gpd.GeoDataFrame, pois_path: Path) -> pd.DataFrame:
    """Compute commercial POI count per grid cell."""
    logger = get_logger("09_build_demand_index")
    pois = gpd.read_file(pois_path).to_crs(grid.crs)
    validate_geodataframe(pois)

    poi_points = pois.copy()
    poi_points["geometry"] = poi_points.geometry.representative_point()

    logger.info("Computing POI density with spatial join.")
    joined = gpd.sjoin(
        poi_points[["geometry"]],
        grid[["cell_id", "geometry"]],
        how="inner",
        predicate="within",
    )

    poi_summary = (
        joined.groupby("cell_id")
        .size()
        .reset_index(name="commercial_poi_count")
    )
    return poi_summary


def write_demand_raster(grid: gpd.GeoDataFrame, reference_raster: Path, output_path: Path) -> Path:
    """Rasterize demand index to the reference grid."""
    with rasterio.open(reference_raster) as source:
        profile = source.profile.copy()

    profile.update(
        {
            "dtype": "float32",
            "count": 1,
            "nodata": -9999.0,
            "compress": "lzw",
        }
    )

    shapes = [
        (geom, float(value))
        for geom, value in zip(grid.geometry, grid["demand_index"])
        if np.isfinite(value)
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        burned = rasterize(
            shapes=shapes,
            out_shape=(profile["height"], profile["width"]),
            transform=profile["transform"],
            fill=-9999.0,
            dtype="float32",
        )
        dst.write(burned, 1)

    return output_path


def main() -> None:
    """Build the latent quick-commerce demand proxy grid."""
    settings = get_settings()
    logger = get_logger("09_build_demand_index")

    aoi_path = require_file(settings.aoi_dir / "aoi_default.geojson")
    pop_path = require_file(settings.raw_dir / "worldpop_population" / "worldpop_population_1km_utm48s.tif")
    viirs_path = require_file(settings.raw_dir / "viirs_nighttime_lights" / "viirs_nighttime_lights_2024_mean_1km_utm48s.tif")
    built_path = require_file(settings.raw_dir / "dynamic_world_built" / "dynamic_world_built_probability_2024_mean_1km_utm48s.tif")
    roads_path = require_file(settings.raw_dir / "osm_network" / "osm_roads_utm48s.gpkg")
    pois_path = require_file(settings.raw_dir / "osm_network" / "osm_commercial_pois_utm48s.gpkg")

    output_grid_path = settings.processed_dir / "demand_grid.gpkg"
    output_raster_path = settings.processed_dir / "demand_index.tif"
    output_table_path = settings.tables_dir / "demand_grid_summary.csv"

    if output_grid_path.exists() and output_raster_path.exists():
        logger.info(f"Using cached file from {output_grid_path}")
        logger.info(f"Using cached file from {output_raster_path}")
        return

    validate_raster(pop_path, expected_crs=settings.projected_crs)
    validate_raster(viirs_path, expected_crs=settings.projected_crs)
    validate_raster(built_path, expected_crs=settings.projected_crs)

    grid = build_grid_from_reference(pop_path, aoi_path)
    grid = attach_raster_values(grid, viirs_path, "nighttime_lights")
    grid = attach_raster_values(grid, built_path, "built_probability")

    road_summary = compute_road_accessibility(grid, roads_path)
    poi_summary = compute_poi_density(grid, pois_path)

    grid = grid.merge(road_summary, on="cell_id", how="left")
    grid = grid.merge(poi_summary, on="cell_id", how="left")

    grid["road_length_m_intersecting"] = grid["road_length_m_intersecting"].fillna(0.0)
    grid["commercial_poi_count"] = grid["commercial_poi_count"].fillna(0.0)

    grid["population_score"] = min_max_scale(safe_log1p(grid["population_count"]))
    grid["nighttime_lights_score"] = min_max_scale(safe_log1p(grid["nighttime_lights"].fillna(0)))
    grid["built_score"] = min_max_scale(grid["built_probability"].fillna(0).clip(lower=0, upper=1))
    grid["road_accessibility_score"] = min_max_scale(safe_log1p(grid["road_length_m_intersecting"]))
    grid["poi_density_score"] = min_max_scale(safe_log1p(grid["commercial_poi_count"]))

    grid = weighted_overlay(
        frame=grid,
        columns=[
            "population_score",
            "nighttime_lights_score",
            "built_score",
            "road_accessibility_score",
            "poi_density_score",
        ],
        weights=[0.40, 0.25, 0.15, 0.10, 0.10],
        output_column="demand_index",
    )

    grid["demand_rank"] = grid["demand_index"].rank(ascending=False, method="dense").astype(int)
    grid["demand_percentile"] = grid["demand_index"].rank(pct=True)
    grid["proxy_delivery_weight"] = grid["demand_index"].clip(lower=0)
    total_weight = grid["proxy_delivery_weight"].sum()
    if total_weight > 0:
        grid["proxy_deliveries_per_100k"] = grid["proxy_delivery_weight"] / total_weight * 100000.0
    else:
        grid["proxy_deliveries_per_100k"] = 0.0

    validate_geodataframe(grid, required_columns=["cell_id", "demand_index"])

    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing demand grid to {output_grid_path}")
    grid.to_file(output_grid_path, driver="GPKG", layer="demand_grid")

    logger.info(f"Writing demand raster to {output_raster_path}")
    write_demand_raster(grid, pop_path, output_raster_path)

    summary = pd.DataFrame(
        [
            {
                "cell_count": int(len(grid)),
                "total_population_proxy": float(grid["population_count"].sum()),
                "mean_demand_index": float(grid["demand_index"].mean()),
                "median_demand_index": float(grid["demand_index"].median()),
                "p90_demand_index": float(grid["demand_index"].quantile(0.90)),
                "total_proxy_deliveries_per_100k": float(grid["proxy_deliveries_per_100k"].sum()),
            }
        ]
    )
    write_csv(summary, output_table_path)

    write_metadata(
        data_path=output_grid_path,
        dataset_name="Latent quick-commerce demand proxy grid",
        source="Derived from WorldPop, VIIRS, Dynamic World, and OpenStreetMap",
        source_url="https://www.worldpop.org/; https://www.noaa.gov/; https://dynamicworld.app/; https://www.openstreetmap.org/",
        license_name="Derived open data, see raw metadata for individual licenses",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m grid",
        temporal_coverage="WorldPop latest available year, VIIRS 2024, Dynamic World 2024, OSM latest snapshot",
        preprocessing_steps=[
            "Created 1 km analysis grid from WorldPop reference raster",
            "Attached VIIRS nighttime lights and Dynamic World built probability",
            "Computed OSM road length proxy by grid cell",
            "Computed OSM commercial POI count by grid cell",
            "Applied log1p transformation to skewed variables",
            "Scaled variables to 0 to 1 using percentile clipping",
            "Computed weighted overlay demand index",
            "Converted demand index to normalized proxy deliveries per 100,000 units",
        ],
        unit="Index from 0 to 1 and normalized proxy deliveries per 100,000",
        citation_apa="Derived open-data demand proxy based on WorldPop, VIIRS, Dynamic World, and OpenStreetMap.",
        citation_bibtex="@misc{derivedDemand2025, title={Latent quick-commerce demand proxy for Greater Jakarta}, author={Project pipeline}, year={2025}}",
        crs=settings.projected_crs,
        extra={
            "weights": {
                "population_score": 0.40,
                "nighttime_lights_score": 0.25,
                "built_score": 0.15,
                "road_accessibility_score": 0.10,
                "poi_density_score": 0.10,
            },
            "interpretation_limit": "This is not actual order volume. It is a latent demand suitability proxy derived from open data.",
        },
    )

    write_metadata(
        data_path=output_raster_path,
        dataset_name="Latent quick-commerce demand index raster",
        source="Derived from processed demand grid",
        source_url="Local pipeline output",
        license_name="Derived open data, see raw metadata for individual licenses",
        spatial_resolution=f"{settings.analysis_grid_size_meters} m",
        temporal_coverage="Composite proxy using latest available open datasets",
        preprocessing_steps=[
            "Rasterized demand index from processed demand grid",
            "Aligned output to WorldPop reference grid",
        ],
        unit="Demand index from 0 to 1",
        citation_apa="Derived open-data demand proxy based on WorldPop, VIIRS, Dynamic World, and OpenStreetMap.",
        citation_bibtex="@misc{derivedDemandRaster2025, title={Latent quick-commerce demand index raster for Greater Jakarta}, author={Project pipeline}, year={2025}}",
        crs=settings.projected_crs,
    )

    logger.info("Demand index construction completed.")
    print(f"Demand grid completed: {output_grid_path}")
    print(f"Demand raster completed: {output_raster_path}")


if __name__ == "__main__":
    main()
