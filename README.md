# Micro-Fulfillment Network Design for Reducing Last-Mile Delivery Emissions in Greater Jakarta Quick Commerce

This repository provides an open-data geospatial optimization framework for designing micro-fulfillment center networks and estimating last-mile delivery CO2e reduction pathways for quick-commerce operations in Greater Jakarta.

The project is built for Windows 11, Python 3.11, Google Earth Engine Python API, and pure Python scripts. No notebooks and no user-supplied shapefiles are required.

## Research Objective

The project asks whether an optimized micro-fulfillment network can reduce demand-weighted last-mile distance and operational CO2e while maintaining a 30-minute service-level target in Greater Jakarta.

## Important Interpretation Boundary

This project does not use actual quick-commerce order volume. It constructs a latent quick-commerce demand proxy from open geospatial data:

* WorldPop population.
* VIIRS nighttime lights.
* Dynamic World built probability.
* OpenStreetMap road accessibility.
* OpenStreetMap commercial POI density.

All emissions are scenario-based and expressed per 100,000 proxy deliveries.

## Study Area

The study area is the road-based Greater Jakarta logistics region, generated reproducibly from GADM 4.1 level 2 administrative boundaries. Kepulauan Seribu is excluded because the analysis focuses on road-based last-mile logistics.

## Main Methods

* Google Earth Engine raster preprocessing.
* AOI generation from GADM 4.1.
* Demand proxy weighted overlay.
* OSM road and POI processing with OSMnx.
* Candidate MFC generation.
* Demand-weighted p-median optimization.
* 30-minute service coverage analysis.
* CO2e scenario modeling for ICE and electric motorcycle adoption.
* Global Moran's I and LISA hotspot analysis.
* KMeans operational segmentation.
* Publication-grade static maps and charts.

## Environment

Recommended environment:

* Windows 11.
* Python 3.11.
* PyCharm or VS Code.
* Google Earth Engine project: `ee-davidproject`.

## Setup

Create and activate a virtual environment:

```powershell
Set-Location "E:\Project\micro-fulfillment-network-jakarta"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

## Key Results

* 30 optimized MFCs cover 76.3% of proxy demand within the 30-minute threshold.
* Extending the test to 60 MFCs only raises 30-minute coverage to 76.8%, indicating a structural coverage ceiling under the default 20 km/h and 30-minute assumptions.
* 30 MFCs reduce demand-weighted distance by 77.0% versus a centralized fulfillment baseline.
* 30 MFCs plus 50% EV adoption reduce scenario CO2e by 84.8% per 100,000 proxy deliveries.
* The best sensitivity scenario reaches 98.2% coverage at 25 km/h and a 60-minute service tier.
* Demand and underserved gaps are highly clustered, with Moran’s I of 0.944 and 0.870.
* The largest underserved bottlenecks are in Tangerang, Bekasi, and Bogor regencies.

## Strategic Interpretation

The project shows that quick-commerce decarbonization in Greater Jakarta is not simply an EV problem or an MFC-count problem. It is a spatial service-design problem. Dense urban cores are better suited for densification and electrification, while fringe regencies require selective MFC expansion, rider staging points, and 45–60 minute service tiers.

## Interpretation Boundary

Demand in this project is a latent open-data proxy, not actual platform order volume. Emissions are scenario-based per 100,000 proxy deliveries, not measured company emissions.

## Recommended Visuals

* `outputs/figures/maps/optimized_mfc_network_map.png`
* `outputs/figures/maps/thirty_minute_service_coverage_map.png`
* `outputs/figures/maps/underserved_hotspot_lisa_map.png`
* `outputs/figures/charts/enhanced_extended_mfc_coverage_curve.png`
* `outputs/figures/charts/enhanced_speed_service_sensitivity_heatmap.png`
* `outputs/figures/charts/enhanced_admin_action_typology.png`
