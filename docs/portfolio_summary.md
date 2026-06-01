# Portfolio Summary

## Project

Micro-Fulfillment Network Optimization for Quick-Commerce Decarbonization in Greater Jakarta.

## Problem

Quick commerce requires fast delivery, but Greater Jakarta’s metropolitan geography creates a trade-off between service coverage, last-mile distance, and emissions. The core question is whether micro-fulfillment center placement can reduce distance and CO2e while supporting a 30-minute service promise.

## Method

The project builds a reproducible Python pipeline using Google Earth Engine, WorldPop, VIIRS nighttime lights, Dynamic World, OpenStreetMap, GADM, p-median facility location, Moran’s I, LISA, clustering, and CO2e scenario modeling.

## Key Results

* 30 optimized MFCs cover 76.3% of proxy demand within the 30-minute threshold.
* 60 MFCs only raise 30-minute coverage to 76.8%.
* 30 MFCs reduce demand-weighted distance by 77.0%.
* 30 MFCs plus 50% EV adoption reduce scenario CO2e by 84.8%.
* 30 MFCs, 25 km/h, and a 60-minute service tier reach 98.2% coverage.
* Demand and underserved gaps are highly clustered, with Moran’s I of 0.944 and 0.870.

## Strategic Insight

Quick-commerce decarbonization is not simply an EV problem or an MFC-count problem. It is a spatial service-design problem. Dense urban cores should be densified and electrified, while fringe regencies require selective MFCs, staging points, and 45–60 minute service tiers.

## Business Value

The framework helps operators decide where to expand fulfillment capacity, where to deploy EVs first, and where a uniform 30-minute delivery promise may be operationally unrealistic.

## Limitations

Demand is an open-data proxy, not actual order volume. Distance is corrected Euclidean distance, not live routing time. Emissions are scenario-based per 100,000 proxy deliveries.
