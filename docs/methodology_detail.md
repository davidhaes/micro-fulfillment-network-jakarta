# Methodology Detail

## Study Area

The study area is the road-based Greater Jakarta metropolitan logistics region. The AOI is generated from GADM 4.1 level 2 administrative boundaries and includes DKI Jakarta and adjacent urban jurisdictions in Tangerang, Bekasi, Bogor, and Depok. Kepulauan Seribu is excluded because the analysis focuses on road-based last-mile logistics.

## Data Sources

The project uses only open data: WorldPop population, VIIRS nighttime lights, Dynamic World built-up probability, OpenStreetMap roads and POIs, and GADM administrative boundaries.

## Demand Proxy

Quick-commerce demand is modeled as a latent open-data proxy. The demand index combines population, nighttime lights, built-up intensity, road accessibility, and commercial POI density. It is not actual platform order volume.

## Optimization

Candidate MFCs are generated from high-demand areas and OSM commercial POIs. A deterministic greedy p-median heuristic selects MFC locations to reduce demand-weighted distance.

## Coverage

Coverage is evaluated using a 30-minute threshold, a default speed of 20 km/h, and a detour factor of 1.35. Enhanced sensitivity analysis tests MFC counts up to 60, speeds of 15, 20, and 25 km/h, and service tiers of 30, 45, and 60 minutes.

## Emissions

CO2e scenarios are calculated per 100,000 proxy deliveries using distance-based activity data, internal-combustion motorcycle emission factors, electric motorcycle energy consumption, and grid emission intensity.

## Spatial Statistics

Global Moran’s I measures overall spatial clustering. LISA identifies local clusters such as High-High underserved hotspots.

## Limitations

The project does not use actual order data, live traffic, facility rent, capacity constraints, or rider scheduling. It is a strategic open-data decision-support framework.
