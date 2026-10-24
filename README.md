# Micro-Fulfillment Network Optimization for Quick-Commerce Decarbonization in Greater Jakarta

Open-data geospatial optimization framework for evaluating micro-fulfillment center (MFC) network design, 30-minute service coverage, underserved spatial clusters, and last-mile CO2e reduction scenarios for quick-commerce operations in Greater Jakarta.

The pipeline combines Google Earth Engine, WorldPop, VIIRS nighttime lights, Dynamic World, OpenStreetMap, p-median and maximal-covering facility location, Moran's I, LISA hotspot analysis, and CO2e scenario modeling in a reproducible Python pipeline.

## Executive Takeaway

A 30 minute promise across Greater Jakarta needs about 25 hubs, not 60, as long as riders keep moving.

With demand anchored to population, 25 hubs put 90.6 percent of proxy demand within a 30 minute ride at 20 km/h and 30 hubs 92.5 percent; doubling to 60 hubs only reaches 97.2 percent. Rider speed matters as much as hub count: at 15 km/h, or with about 7 minutes of each 30 lost to picking and handover, 30 hubs cover 81.2 percent. Almost all uncovered demand (99 percent) sits in the Bogor, Bekasi and Tangerang regencies, where a 45 minute tier or rider staging points are cheaper than more stores. On the same network, a fully electric fleet cuts CO2e per delivery by 58 to 68 percent depending on the grid factor.

## Key Results

* 30 optimized MFCs cover 92.5% of proxy demand within 30 minutes at 20 km/h; 25 MFCs reach 90.6% and 15 reach 80.9%.
* 40 MFCs reach 95.2% and 60 MFCs 97.2%. A greedy coverage-maximising network reaches 95.7% at 30 hubs.
* At 15 km/h the 30-hub network covers 81.2%; 45 hubs are needed to reach 90%.
* With 30 MFCs, a 45-minute tier at 20 km/h reaches 97.6% coverage.
* On the 30-hub network an average delivery is 5.7 km one way (6.9 km with 20 hubs). A petrol fleet emits about 410 gCO2e per delivery; 50% electric adoption cuts this by 29 to 34% and 100% by 58 to 68%, at grid factors of 870 and 650 gCO2e/kWh (`outputs/tables/emission_grid_sensitivity.csv`).
* Uncovered demand: Bogor regency 25% of its demand, Bekasi regency 23%, Tangerang regency 19%; together 99% of all uncovered demand.

## Correction, October 2026

A second audit found that demand had been weighted by the composite index alone. A 1 km cell's index runs from about 0.3 in sparse fringe land to 0.9 in the dense core, while population density differs by a factor of twenty or more, so the fringe regencies received more demand than all of DKI Jakarta. `scripts/09_build_demand_index.py` now weights each cell's population by the index, which puts 34% of demand in DKI Jakarta, close to its share of the region's population. All optimisation outputs were regenerated.

The same audit replaced the emission headline. Reductions of up to 94.5% were measured against one central hub serving the whole region, a network no operator runs. `scripts/11b_grid_sensitivity.py` reports electrification against a petrol fleet on the same network under two grid factors. The action typology now ranks regencies by the volume of uncovered demand rather than a share threshold alone, which moves the Tangerang regency into the fringe class.

Version 2 (September 2026) reported 81.6% coverage with 30 hubs, a 98.0% figure for 60 hubs and uncovered shares of 30% (Bogor) and 27% (Bekasi). Those figures are superseded.

## Correction, September 2026

An earlier version of this README reported 76.3% coverage with 30 hubs, a "coverage ceiling" of 76.8% at 60 hubs, and concluded that adding MFCs cannot solve 30-minute coverage. That conclusion was an artifact of the setup, not a property of Greater Jakarta:

* only the 2,500 highest-demand cells (57% of proxy demand) entered the optimization, and coverage was reported as a share of that subset;
* candidate sites were limited to 350 points in the top 30% of demand, and 76.8% was exactly the coverage reached with all 350 open.

The optimization now uses all 7,096 demand cells, all 3,792 built-up cells as candidates, greedy construction improved by vertex substitution, and a maximal-covering comparison. The previous outputs are archived outside the repository.

## Study Area

The study area is the road-based Greater Jakarta metropolitan logistics region generated from GADM 4.1 administrative boundaries. It includes DKI Jakarta and adjacent urban jurisdictions in Tangerang, Bekasi, Bogor, and Depok. Kepulauan Seribu is excluded because the analysis focuses on road-based last-mile logistics.

## Important Interpretation Boundary

Demand in this project is a latent open-data proxy, not actual platform order volume. The demand proxy is derived from WorldPop population, VIIRS nighttime lights, Dynamic World built-up probability, OpenStreetMap road accessibility and OpenStreetMap commercial POI density.

Emissions are scenario-based per 100,000 proxy deliveries, not measured company emissions. The grid emission factor is an assumption; results are given at 650 and at 870 gCO2e/kWh, the latter closer to published Java-Bali grid values. Distance is corrected Euclidean distance (detour factor 1.35), not live time-dependent routing.

## Method Overview

1. Generate the Greater Jakarta AOI from GADM 4.1.
2. Preprocess raster data in Google Earth Engine.
3. Build a 1 km open-data quick-commerce demand proxy.
4. Take every built-up cell (Dynamic World built-up probability at least 0.20) as a candidate MFC site.
5. Optimize MFC networks with a demand-weighted p-median (greedy construction plus vertex substitution) over all demand cells, and compare with a greedy maximal-covering solution.
6. Evaluate 30-minute service coverage, CO2e scenarios, and spatial clustering of uncovered demand.
7. Run sensitivity analysis for MFC count, speed, and service tier.

## Visual Evidence and Interpretation

### 1. Optimized Micro-Fulfillment Network

![Optimized MFC Network](docs/assets/01_optimized_mfc_network.png)

Hubs follow the population: the core cities hold most of them, with a ring of hubs in the inner suburbs.

### 2. Thirty-Minute Service Coverage

![Thirty-Minute Service Coverage](docs/assets/02_thirty_minute_service_coverage.png)

92.5% of proxy demand sits within 30 minutes of the 30-hub network at 20 km/h. The uncovered remainder is on the fringes.

### 3. Underserved Demand Hotspots

![Underserved Hotspot LISA](docs/assets/03_underserved_hotspot_lisa.png)

Uncovered demand clusters spatially (Moran's I = 0.621, p = 0.001), mostly in the Bogor, Bekasi and Tangerang regencies.

### 4. MFC Count Sensitivity

![Extended MFC Coverage Curve](docs/assets/04_extended_mfc_coverage_curve.png)

Coverage rises from 37.8% with 5 hubs to 90.6% with 25 and 92.5% with 30, then flattens: 95.2% with 40 and 97.2% with 60. At 15 km/h every count covers far less.

### 5. Speed and Service-Tier Sensitivity

![Speed Service Sensitivity](docs/assets/05_speed_service_sensitivity_heatmap.png)

A 45-minute tier lifts the 30-hub network from 92.5% to 97.6% coverage at 20 km/h, which is the cheaper route to near-full coverage than doubling the network.

### 6. CO2e per Delivery

![CO2e per delivery](docs/assets/06_emission_scenario_pathway.png)

Per delivery CO2e by network size and fleet electrification, under grid factors of 650 and 870 gCO2e/kWh, is in `outputs/figures/charts/emission_per_delivery.png`.

### 7. Administrative Action Typology

![Administrative Action Typology](docs/assets/07_admin_action_typology.png)

Units are classed by demand intensity and by the share of their demand outside the 30-minute reach of the 30-hub network.

## Strategic Recommendations

### Core urban areas

Demand in Jakarta, Kota Tangerang, Tangerang Selatan, Depok, Kota Bekasi and Kota Bogor is inside the 30-minute reach. Densify inventory, cut picking time, electrify the fleet and improve charging access.

### Fringe regencies

The Bogor, Bekasi and Tangerang regencies hold 99% of the uncovered volume. Use rider staging points at the edge of the covered area and offer a 45-minute tier where hubs are not justified.

## Reproducing

```bash
python scripts/21_run_pipeline.py --skip-gee-auth
python scripts/run_enhanced_analysis.py
```

Steps 01 to 08 need Earth Engine credentials; from step 09 onward the pipeline runs on data already on disk.
