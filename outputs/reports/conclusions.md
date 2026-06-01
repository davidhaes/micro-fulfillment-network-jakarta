# Conclusions

## Answers to the Research Questions

1. No tested scenario from 5 to 60 MFCs reaches 90% coverage within the modeled 30-minute threshold at 20 km/h. The 30-MFC scenario covers 76.3% of proxy demand, and the 60-MFC scenario only increases coverage to 76.8%. This indicates a structural coverage ceiling.

2. The largest underserved bottlenecks are located in Tangerang, Bekasi, and Bogor regencies. Tangerang has a mean underserved score of 0.401, Bekasi 0.350, and Bogor 0.276.

3. The optimized 30-MFC network reduces demand-weighted last-mile distance by 77.0% compared with the centralized baseline. Baseline distance is 3,190,161.7 km per 100,000 proxy deliveries, while the 30-MFC scenario reduces it to 734,869.6 km.

4. The 30-MFC network plus 50% electric motorcycle adoption reduces scenario CO2e by 84.8% per 100,000 proxy deliveries. With 100% EV adoption, the reduction increases to 92.7%.

5. Demand and underserved gaps are strongly spatially clustered. Demand index Moran’s I is 0.944, and underserved score Moran’s I is 0.870, both significant at p = 0.001.

## Top Findings

* Micro-fulfillment significantly reduces last-mile distance, but it does not automatically solve 30-minute metropolitan-wide coverage.
* Increasing MFC count from 30 to 60 yields almost no coverage gain, raising coverage only from 76.3% to 76.8%.
* The largest gains occur between 5 and 15 MFCs, after which coverage improvement shows strong diminishing returns.
* A 60-minute service tier at 25 km/h reaches 98.2% coverage, showing that tiered service design is more effective than uniform 30-minute coverage.
* Fringe regencies are the structural bottleneck. Dense urban cores are relatively serviceable, while Tangerang, Bekasi, and Bogor require different operational strategies.
* EV adoption is most effective after fulfillment distance is reduced. Network design and fleet electrification should be implemented together.

## Hypothesis Evaluation

* H1 is strongly supported. Distributed MFCs reduce demand-weighted distance by more than 20%, with a 77.0% reduction in the 30-MFC scenario.
* H2 is not supported. Seventy percent of proxy demand requires 48.3% of the grid area, not less than 40%. Demand is more spatially distributed than expected.
* H3 is strongly supported. The 30-MFC network plus 50% EV adoption reduces scenario CO2e by 84.8%, exceeding the 30% benchmark.

## Spatial Pattern Summary

Demand is not randomly distributed. It is strongly clustered across the metropolitan region. The same is true for underserved demand. Core urban areas such as Jakarta, Kota Tangerang, Depok, Kota Bekasi, and Kota Bogor show high demand but relatively low underserved scores. In contrast, Tangerang, Bekasi, and Bogor regencies contain large underserved clusters.

## Temporal Pattern Summary

VIIRS nighttime lights show a positive Sen’s slope of 0.531 avg_rad per year from 2020 to 2024, but the Kendall p-value is 0.817. This trend should not be interpreted as statistically significant growth. VIIRS is used as an economic activity proxy, not as evidence of actual quick-commerce order growth.

## Counter-Intuitive Findings

* High-demand areas are not always the areas with the largest service gaps.
* Adding more MFCs beyond 30 does not materially improve 30-minute coverage.
* A uniform 30-minute promise is less realistic than a segmented service-tier strategy.
* The urban core is not the main bottleneck. Fringe regencies drive the remaining coverage gap.

## Limitations

* Demand is an open-data proxy, not actual order volume.
* Distance is corrected Euclidean distance, not time-dependent routing.
* CO2e estimates are scenario-based per 100,000 proxy deliveries.
* The model does not include facility rent, capacity constraints, inventory duplication, live traffic, rider scheduling, or actual order density.
