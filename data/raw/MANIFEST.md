# Raw Data Manifest

Total data folder size: 0.4060 GB

Raw data in this project means source-derived files after basic preprocessing. Satellite tiles, unprocessed global rasters, and manually supplied shapefiles are not stored.

Datasets:

1. Dynamic World built probability annual mean
   * Data path: `data\raw\dynamic_world_built\dynamic_world_built_probability_2024_mean_1km_utm48s.tif`
   * Metadata path: `data\raw\dynamic_world_built\dynamic_world_built_probability_2024_mean_1km_utm48s.tif.metadata.json`
   * Source: Google Dynamic World V1 via Google Earth Engine
   * Source URL: https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1
   * License: CC-BY 4.0
   * Access date: 2026-05-30
   * Spatial resolution: 1000 m analysis grid aggregated from 10 m source
   * Temporal coverage: 2024-01-01 to 2024-12-31
   * Unit: probability from 0 to 1
   * CRS: EPSG:32748
   * File size MB: 0.064
   * Preprocessing steps:
     * Filtered Dynamic World V1 image collection to target year
     * Selected built probability band
     * Computed annual mean composite
     * Aggregated built probability to 1 km using mean reducer
     * Clipped raster to Greater Jakarta AOI
     * Reprojected raster to EPSG:32748

2. Greater Jakarta GADM level 2 selected units
   * Data path: `data\raw\gadm_aoi\greater_jakarta_gadm_level2.geojson`
   * Metadata path: `data\raw\gadm_aoi\greater_jakarta_gadm_level2.geojson.metadata.json`
   * Source: GADM 4.1
   * Source URL: https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_IDN_2.json.zip
   * License: GADM license for academic and non-commercial use
   * Access date: 2026-05-30
   * Spatial resolution: Administrative boundary level 2
   * Temporal coverage: Static administrative boundary
   * Unit: Polygon geometry
   * CRS: EPSG:4326
   * File size MB: 0.069
   * Preprocessing steps:
     * Downloaded GADM Indonesia level 2 GeoJSON zip
     * Filtered Greater Jakarta road-based logistics administrative units
     * Excluded Kepulauan Seribu from core logistics AOI
     * Saved selected level 2 units as GeoJSON

3. OpenStreetMap commercial and logistics-relevant POIs
   * Data path: `data\raw\osm_network\osm_commercial_pois_utm48s.gpkg`
   * Metadata path: `data\raw\osm_network\osm_commercial_pois_utm48s.gpkg.metadata.json`
   * Source: OpenStreetMap via OSMnx
   * Source URL: https://www.openstreetmap.org/
   * License: Open Database License, ODbL
   * Access date: 2026-05-30
   * Spatial resolution: Vector POI geometries from OpenStreetMap clipped to Greater Jakarta AOI
   * Temporal coverage: Latest OpenStreetMap snapshot at access date
   * Unit: POI geometry
   * CRS: EPSG:32748
   * File size MB: 5.812
   * Preprocessing steps:
     * Queried OSM features using commercial, retail, marketplace, food, warehouse, and landuse tags
     * Removed missing and invalid geometries
     * Selected stable POI attributes
     * Reprojected POIs to EPSG:32748
     * Saved to GeoPackage

4. OpenStreetMap road network nodes
   * Data path: `data\raw\osm_network\osm_road_nodes_utm48s.gpkg`
   * Metadata path: `data\raw\osm_network\osm_road_nodes_utm48s.gpkg.metadata.json`
   * Source: OpenStreetMap via OSMnx
   * Source URL: https://www.openstreetmap.org/
   * License: Open Database License, ODbL
   * Access date: 2026-05-30
   * Spatial resolution: Vector road nodes from OpenStreetMap clipped to Greater Jakarta AOI
   * Temporal coverage: Latest OpenStreetMap snapshot at access date
   * Unit: Road node geometry
   * CRS: EPSG:32748
   * File size MB: 57.301
   * Preprocessing steps:
     * Queried OSM drive road graph inside Greater Jakarta AOI
     * Converted graph nodes to GeoDataFrame
     * Selected stable node attributes
     * Reprojected nodes to EPSG:32748
     * Saved to GeoPackage

5. OpenStreetMap drive road network
   * Data path: `data\raw\osm_network\osm_roads_utm48s.gpkg`
   * Metadata path: `data\raw\osm_network\osm_roads_utm48s.gpkg.metadata.json`
   * Source: OpenStreetMap via OSMnx
   * Source URL: https://www.openstreetmap.org/
   * License: Open Database License, ODbL
   * Access date: 2026-05-30
   * Spatial resolution: Vector road segments from OpenStreetMap clipped to Greater Jakarta AOI
   * Temporal coverage: Latest OpenStreetMap snapshot at access date
   * Unit: Road segment geometry with length in meters
   * CRS: EPSG:32748
   * File size MB: 339.242
   * Preprocessing steps:
     * Queried OSM drive road graph inside Greater Jakarta AOI
     * Simplified graph topology using OSMnx
     * Converted graph edges to GeoDataFrame
     * Selected stable road attributes
     * Reprojected road edges to EPSG:32748
     * Saved to GeoPackage

6. VIIRS nighttime lights annual mean
   * Data path: `data\raw\viirs_nighttime_lights\viirs_nighttime_lights_2024_mean_1km_utm48s.tif`
   * Metadata path: `data\raw\viirs_nighttime_lights\viirs_nighttime_lights_2024_mean_1km_utm48s.tif.metadata.json`
   * Source: NOAA VIIRS DNB monthly VCMCFG via Google Earth Engine
   * Source URL: https://developers.google.com/earth-engine/datasets/catalog/NOAA_VIIRS_DNB_MONTHLY_V1_VCMCFG
   * License: Public domain, NOAA open data
   * Access date: 2026-05-30
   * Spatial resolution: 1000 m analysis grid aggregated from approximately 500 m source
   * Temporal coverage: 2024-01-01 to 2024-12-31
   * Unit: nanoWatts per square centimeter per steradian
   * CRS: EPSG:32748
   * File size MB: 0.024
   * Preprocessing steps:
     * Filtered VIIRS monthly VCMCFG collection to target year
     * Selected avg_rad band
     * Computed annual mean composite
     * Clipped raster to Greater Jakarta AOI
     * Aggregated and reprojected raster to EPSG:32748 at 1 km analysis grid
     * Clipped negative radiance values to zero

7. WorldPop population count aggregated to 1 km
   * Data path: `data\raw\worldpop_population\worldpop_population_1km_utm48s.tif`
   * Metadata path: `data\raw\worldpop_population\worldpop_population_1km_utm48s.tif.metadata.json`
   * Source: WorldPop via Google Earth Engine
   * Source URL: https://developers.google.com/earth-engine/datasets/catalog/WorldPop_GP_100m_pop
   * License: WorldPop open data license
   * Access date: 2026-05-30
   * Spatial resolution: 1000 m analysis grid aggregated from approximately 100 m source
   * Temporal coverage: 2020
   * Unit: persons per analysis cell
   * CRS: EPSG:32748
   * File size MB: 0.033
   * Preprocessing steps:
     * Filtered WorldPop collection to Indonesia
     * Selected latest available year in the Earth Engine collection
     * Aggregated population count to 1 km using sum reducer
     * Clipped raster to Greater Jakarta AOI
     * Reprojected raster to EPSG:32748

