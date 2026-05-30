## Reproducibility

* The project can be run from a clean clone with Python 3.11.
* Environment dependencies are listed in `requirements.txt`.
* Local package installation is supported through `pyproject.toml`.
* The pipeline can be run with `python scripts\21_run_pipeline.py`.
* The pipeline supports `--continue-on-error`.
* The pipeline supports `--start-at`.

## Credential Safety

* `.env` is ignored by Git.
* Service account JSON files are ignored by Git.
* `.env.example` does not contain private keys.
* No credential is stored in notebooks or scripts.

## Data Authenticity

* AOI is generated from GADM 4.1.
* No user-supplied shapefile is required.
* Raw stored data are preprocessed derivatives, not unprocessed global source tiles.
* Every raw and processed data file has metadata JSON.
* `data/raw/MANIFEST.md` exists.
* `data/processed/PROCESSING_LOG.md` exists.

## Methodological Integrity

* Demand is explicitly described as a latent proxy, not actual order volume.
* CRS for distance analysis is EPSG:32748.
* Facility location uses demand-weighted p-median logic.
* Service coverage uses a stated 30-minute threshold.
* Distance approximation uses a documented detour factor.
* Emission modeling is scenario-based and normalized per 100,000 proxy deliveries.
* Spatial autocorrelation includes Global Moran's I and LISA.

## Visualization

* Static maps are exported as PNG and PDF.
* Maps use approved colormaps.
* Banned colormaps such as jet and rainbow are not used.
* Core maps include overview, thematic demand, optimized MFC network, service coverage, and LISA hotspot.
* Charts include distance reduction, service coverage, emissions, underserved ranking, trend, and demand concentration.
* Interactive maps are exported as HTML.

## Reporting

* `outputs/reports/executive_summary.md` exists.
* `outputs/reports/conclusions.md` exists.
* `outputs/reports/recommendations.md` exists.
* `outputs/reports/methodology.md` exists.
* `outputs/reports/how_to_read.md` exists.
* Reports contain numbers derived from CSV outputs.
* Limitations distinguish open data, derived proxies, and scenario assumptions.

## Portfolio Readiness

* `README.md` explains setup and execution.
* `LICENSE` exists.
* `CITATION.cff` exists.
* `CHANGELOG.md` exists.
* public-facing portfolio post, article, and upload guide exist.
* GitHub repository does not include large raw data or credentials.
