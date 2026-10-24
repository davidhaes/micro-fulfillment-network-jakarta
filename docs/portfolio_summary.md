# Portfolio Summary

## Project

Micro-Fulfillment Network Optimization for Quick-Commerce Decarbonization in Greater Jakarta.

## Problem

Quick commerce requires fast delivery, but Greater Jakarta’s metropolitan geography creates a trade-off between service coverage, last-mile distance, and emissions. The core question is whether micro-fulfillment center placement can reduce distance and CO2e while supporting a 30-minute service promise.

## Method

The project builds a reproducible Python pipeline using Google Earth Engine, WorldPop, VIIRS nighttime lights, Dynamic World, OpenStreetMap, GADM, p-median facility location, Moran’s I, LISA, clustering, and CO2e scenario modeling.

## Key Results

* 30 optimized MFCs cover 81.6% of proxy demand within 30 minutes at 20 km/h.
* 40 MFCs reach 91.9% and 60 MFCs 98.0%; coverage keeps rising with hub count.
* 30 MFCs reduce demand-weighted distance by 82.7%.
* 30 MFCs plus 50% EV adoption reduce scenario CO2e by 88.6%.
* With 30 MFCs, a 45-minute tier at 20 km/h reaches 98.4% coverage.
* Demand and uncovered demand are clustered, with Moran's I of 0.944 and 0.621.

## Strategic Insight

Near-full 30-minute coverage is reachable with about 40 hubs. The last tenth of demand sits in the Bogor, Bekasi and Tangerang regencies, where a 45-minute tier or rider staging points cost less than the hubs full coverage would need. Dense cores should be densified and electrified.

## Business Value

The framework helps operators decide where to expand fulfillment capacity, where to deploy EVs first, and where a longer service tier is cheaper than additional hubs.

## Limitations

Demand is an open-data proxy, not actual order volume. Distance is corrected Euclidean distance, not live routing time. Emissions are scenario-based per 100,000 proxy deliveries.
