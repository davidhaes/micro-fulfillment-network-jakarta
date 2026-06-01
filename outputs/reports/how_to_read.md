# How to Read the Metrics

## Demand Index

* Unit: index from 0 to 1.
* Meaning: higher values indicate stronger open-data demand suitability.
* Inputs: population, nighttime lights, built-up probability, road accessibility, and commercial POI density.
* Important boundary: this is not actual order volume.

## Proxy Deliveries per 100,000

* Unit: normalized proxy demand weight.
* Meaning: allows scenario comparison without claiming actual delivery volume.
* Use: weighting p-median optimization and emissions scenarios.

## 30-Minute Coverage

* Unit: share of proxy demand covered within the modeled threshold.
* Current 30-MFC result: 76.3%.
* Extended 60-MFC result: 76.8%.
* Interpretation: the modeled network does not reach 90% coverage under the default 20 km/h and 30-minute assumption.

## Demand-Weighted Distance

* Unit: kilometers per 100,000 proxy deliveries.
* Baseline: 3,190,161.7 km.
* 30-MFC scenario: 734,869.6 km.
* Interpretation: the optimized network reduces distance by 77.0%.

## CO2e Reduction

* Unit: percent reduction relative to centralized internal-combustion motorcycle baseline.
* 30 MFC + 50% EV adoption: 84.8% reduction.
* 30 MFC + 100% EV adoption: 92.7% reduction.
* Interpretation: emissions fall when distance reduction and fleet electrification are combined.

## Moran’s I

* Demand index Moran’s I: 0.944.
* Underserved score Moran’s I: 0.870.
* Interpretation: values are strongly spatially clustered, not random.

## LISA Clusters

* High-High: high value surrounded by high-value neighbors.
* Low-Low: low value surrounded by low-value neighbors.
* High-Low: local high outlier.
* Low-High: local low outlier.
* Use: identify spatially contiguous priority zones.

## Action Typology

* Densify and electrify: high demand, low underserved score.
* Fringe MFC or staging priority: high underserved score and large proxy demand in fringe areas.
* Staging or tiered SLA: underserved but not dense enough for immediate full MFC expansion.
* Maintain and monitor: lower demand and lower underserved score.
