## Why is demand modeled as a proxy?

Actual quick-commerce order data are proprietary and not available as open data. The project therefore models latent demand suitability using open geospatial proxies. The output should not be interpreted as observed order volume. It is a reproducible baseline that can later be calibrated with anonymized internal transaction data.

## Why use WorldPop?

WorldPop provides high-resolution population estimates and is widely used in public health, disaster exposure, accessibility, and urban analytics. In this project, it provides the residential demand base. It does not capture purchasing power alone, so it is combined with VIIRS, built-up intensity, road access, and POI density.

## Why use VIIRS nighttime lights?

Nighttime lights are frequently used as a proxy for economic activity and urban intensity. They help distinguish dense but low-activity areas from areas with stronger nighttime economic signals. The limitation is blooming and saturation, especially in dense urban cores.

## Why use Dynamic World built probability?

Dynamic World provides near real-time global land cover probabilities at 10 m resolution. The built probability band is used as an urban intensity proxy. It is aggregated to the project grid using a mean reducer, which approximates built-up share or intensity within each cell.

## Why use OpenStreetMap?

OpenStreetMap is the most practical open vector source for roads and POIs. It supports road accessibility, commercial density, and candidate MFC screening. The limitation is spatial variation in data completeness.

## Why EPSG:32748?

Distance, area, and buffer analysis should not be performed in EPSG:4326 because its units are degrees. Greater Jakarta lies in UTM zone 48S, so EPSG:32748 provides meter-based coordinates suitable for service coverage and distance-based optimization.

## Why p-median?

The p-median problem selects p facilities to minimize total demand-weighted distance. This fits the objective of reducing last-mile travel burden. For quick commerce, p-median is useful because shorter distance typically supports faster delivery and lower energy use.

## Why not full VRPTW?

Vehicle Routing Problem with Time Windows requires order timestamps, drop sequence, rider capacity, service time, time-dependent travel speed, fleet size, and batching rules. These data are not open. Facility location and coverage analysis are more appropriate for an open-data reproducible project.

## Why use a detour factor?

Euclidean distance underestimates real route distance. A detour factor adjusts straight-line distance to approximate road path distance. The project uses this as a transparent assumption. In production, it should be replaced with routing engine travel-time matrices.

## Why calculate emissions per 100,000 proxy deliveries?

The project does not know actual delivery volume. Normalizing to 100,000 proxy deliveries allows fair scenario comparison without claiming company-level totals. It is a scenario accounting unit.

## Why is EV not zero emission?

The project uses grid-based operational accounting. Electric motorcycles have no tailpipe emissions, but electricity generation still has carbon intensity. Therefore EV emissions are computed from kWh per km multiplied by grid emission factor.

## What does Moran's I add?

Moran's I tests whether high or low values cluster spatially. A significant Moran's I for demand index or underserved score means the pattern is not random. LISA then identifies where the local clusters are.

## What does LISA High-High mean?

High-High means a cell has a high value and is surrounded by neighbors with high values. For underserved score, this is more actionable than a single high cell because it indicates a contiguous intervention zone.

## What is the biggest limitation?

The largest limitation is the absence of actual order and travel-time data. The framework is a reproducible open-data baseline, not a replacement for internal operational optimization.

## What is the strongest contribution?

The strongest contribution is integrating open-data demand proxy, facility location optimization, service coverage, spatial autocorrelation, and CO2e scenario modeling into one reproducible Python pipeline for a real megacity logistics problem.
