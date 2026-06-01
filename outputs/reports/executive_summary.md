# Executive Summary

This project evaluates whether an optimized micro-fulfillment center network can reduce last-mile delivery distance and CO2e emissions while supporting quick-commerce service coverage in Greater Jakarta. Demand is modeled as a latent open-data proxy using WorldPop population, VIIRS nighttime lights, Dynamic World built-up probability, OpenStreetMap accessibility, and commercial POI density. It is not actual platform order volume.

The workflow combines GADM-based AOI generation, Google Earth Engine raster preprocessing, a 1 km demand grid, candidate MFC screening, demand-weighted p-median optimization, 30-minute service coverage modeling, Moran’s I, LISA hotspot analysis, clustering, and CO2e scenario modeling.

Key findings:

* 30 optimized MFCs cover 76.3% of proxy demand within the modeled 30-minute threshold.
* Increasing the test range from 30 to 60 MFCs only raises 30-minute coverage to 76.8%, indicating a structural coverage ceiling under the default 20 km/h and 30-minute assumptions.
* 30 MFCs reduce demand-weighted distance by 77.0% compared with a centralized fulfillment baseline.
* 30 MFCs plus 50% electric motorcycle adoption reduce scenario CO2e by 84.8% per 100,000 proxy deliveries.
* The strongest sensitivity scenario reaches 98.2% coverage at 25 km/h and a 60-minute service tier.
* Demand and underserved gaps are strongly spatially clustered, with Moran’s I of 0.944 and 0.870.
* The largest underserved bottlenecks are located in Tangerang, Bekasi, and Bogor regencies.

Strategic conclusion: quick-commerce decarbonization in Greater Jakarta is not only an EV adoption problem or an MFC-count problem. It is a spatial service-design problem. Dense urban cores should be operationally densified and electrified, while fringe regencies require selective MFC expansion, rider staging points, and 45–60 minute service tiers.

The full pipeline is reproducible through Python scripts after Google Earth Engine credentials are configured.
