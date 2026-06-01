# Data Dictionary

## Demand Grid

* `cell_id`: unique 1 km grid cell identifier.
* `population_count`: WorldPop population count aggregated to the analysis grid.
* `nighttime_lights`: VIIRS annual mean nighttime radiance.
* `built_probability`: Dynamic World annual mean built-up probability.
* `road_length_m_intersecting`: clipped OSM road length inside the grid cell.
* `commercial_poi_count`: count of commercial OSM POIs inside the grid cell.
* `demand_index`: latent quick-commerce demand suitability index from 0 to 1.
* `proxy_deliveries_per_100k`: normalized proxy demand weight per 100,000 units.

## Optimization Outputs

* `mfc_count`: number of selected micro-fulfillment centers in the scenario.
* `coverage_share`: share of proxy demand covered within the modeled service threshold.
* `demand_weighted_distance_km`: demand-weighted route-distance proxy per 100,000 proxy deliveries.
* `distance_reduction_percent`: distance reduction relative to the centralized baseline.

## Emissions

* `ev_adoption_percent`: electric motorcycle adoption rate in the scenario.
* `scenario_emissions_kgco2e`: scenario emissions in kg CO2e per 100,000 proxy deliveries.
* `emission_reduction_percent`: emissions reduction relative to the centralized ICE baseline.

## Spatial Statistics

* `moran_i`: Global Moran’s I spatial autocorrelation statistic.
* `local_moran_i`: Local Moran’s I statistic.
* `lisa_cluster`: LISA cluster class.
* `underserved_score`: demand index multiplied by uncovered status under the reference scenario.

## Action Typology

* `action_typology`: recommended operational strategy for an administrative unit.
* `action_priority`: priority level.
* `action_rationale`: explanation for the recommended action.
