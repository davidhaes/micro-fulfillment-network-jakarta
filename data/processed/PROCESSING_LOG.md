# Processing Log


Total data folder size: 0.4060 GB.

Processed outputs created by the pipeline:

* demand_grid.gpkg: latent quick-commerce demand proxy grid.
* demand_index.tif: rasterized demand index.
* mfc_candidates.gpkg: candidate micro-fulfillment center locations.
* optimized_mfc_networks.gpkg: selected MFC points by scenario.
* service_coverage.gpkg: nearest-MFC distance, coverage flags, and underserved score.
* emission_scenarios.csv: CO2e scenarios by MFC count and EV adoption.
* demand_underserved_lisa.gpkg: Local Moran's I cluster diagnostics.
* spatial_autocorrelation.csv: Global Moran's I diagnostics.
* demand_clusters.gpkg: operational KMeans segments.
* viirs_temporal_trend.csv: nighttime lights trend context.
* validation_crosscheck.csv: administrative-scale sanity checks.

Reference scenario:

* MFC count: 30.
* Coverage share: 0.7633.
* Distance reduction percent: 76.9645.

Best emission scenario:

* MFC count: 30.
* EV adoption percent: 100.
* Emission reduction percent: 92.7214.

Interpretation boundary:

* Demand metrics are open-data proxy outputs, not proprietary order volume.
* Emission metrics are scenario-based kg CO2e per 100,000 proxy deliveries, not measured company emissions.
