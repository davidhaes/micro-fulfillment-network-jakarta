# Data Dictionary

* cell_id: ID unik grid cell 1 km.
* population_count: jumlah penduduk WorldPop hasil agregasi ke grid.
* nighttime_lights: annual mean VIIRS avg_rad.
* built_probability: annual mean Dynamic World built probability.
* road_length_m_intersecting: total panjang jalan OSM yang berinterseksi dengan cell.
* commercial_poi_count: jumlah POI komersial OSM dalam cell.
* population_score: skor populasi 0 sampai 1 setelah log1p dan scaling.
* nighttime_lights_score: skor VIIRS 0 sampai 1 setelah log1p dan scaling.
* built_score: skor built-up 0 sampai 1.
* road_accessibility_score: skor akses jalan 0 sampai 1.
* poi_density_score: skor POI 0 sampai 1.
* demand_index: latent quick-commerce demand proxy 0 sampai 1.
* proxy_deliveries_per_100k: bobot demand yang dinormalisasi ke 100.000 unit proxy.
* mfc_count: jumlah micro-fulfillment center dalam skenario.
* coverage_share: share proxy demand yang tercakup dalam SLA 30 menit.
* demand_weighted_distance_km: jarak demand-weighted per 100.000 proxy deliveries.
* distance_reduction_percent: penurunan jarak dibanding baseline centralized fulfillment.
* scenario_emissions_kgco2e: emisi skenario dalam kg CO2e per 100.000 proxy deliveries.
* emission_reduction_percent: penurunan emisi dibanding centralized ICE baseline.
* underserved_score: demand index dikalikan status tidak tercakup pada skenario referensi.
* local_moran_i: statistik Local Moran's I.
* local_moran_p: p-value Local Moran's I berbasis permutations.
* lisa_cluster: label cluster LISA.
* cluster_label: label segmentasi operasional KMeans.
