from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.logger import get_logger


def write_text_if_missing(path: Path, content: str) -> None:
    """Write a UTF-8 text file if it does not already exist."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json_if_missing(path: Path, payload: dict) -> None:
    """Write a UTF-8 JSON file if it does not already exist."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )


def ensure_directories(paths: Iterable[Path]) -> None:
    """Create directories if they do not exist."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Bootstrap all required project directories and functional starter files."""
    settings = get_settings()
    logger = get_logger("bootstrap_folders")
    now = datetime.now(timezone.utc).isoformat()

    logger.info("Starting folder bootstrap.")
    logger.info(f"Resolved project root: {settings.project_root}")

    directories = [
        settings.project_root / "AOI",
        settings.project_root / "data" / "raw" / "gadm_aoi",
        settings.project_root / "data" / "raw" / "worldpop_population",
        settings.project_root / "data" / "raw" / "viirs_nighttime_lights",
        settings.project_root / "data" / "raw" / "dynamic_world_built",
        settings.project_root / "data" / "raw" / "osm_network",
        settings.project_root / "data" / "processed",
        settings.project_root / "data" / "external" / "references",
        settings.project_root / "scripts",
        settings.project_root / "src" / "micro_fulfillment_network_jakarta",
        settings.project_root / "outputs" / "figures" / "maps",
        settings.project_root / "outputs" / "figures" / "charts",
        settings.project_root / "outputs" / "maps_interactive",
        settings.project_root / "outputs" / "tables",
        settings.project_root / "outputs" / "geotiffs",
        settings.project_root / "outputs" / "reports",
        settings.project_root / "content",
        settings.project_root / "docs",
        settings.project_root / "tests",
    ]
    ensure_directories(directories)

    write_text_if_missing(
        settings.project_root / "AOI" / "README.md",
        "# AOI\n\nThis folder stores reproducible administrative boundary outputs generated from GADM 4.1.\n",
    )

    write_json_if_missing(
        settings.project_root / "AOI" / "aoi_metadata.json",
        {
            "dataset_name": "Greater Jakarta AOI",
            "source": "GADM 4.1",
            "source_url": "https://gadm.org/",
            "license": "GADM license for academic and non-commercial use",
            "access_date": now[:10],
            "spatial_resolution": "Administrative boundary level 2",
            "temporal_coverage": "Static administrative boundary",
            "preprocessing_steps": [
                "Downloaded GADM administrative boundaries",
                "Filtered Greater Jakarta level 2 administrative units",
                "Excluded Kepulauan Seribu for road-based logistics analysis",
                "Dissolved selected units into one metropolitan AOI",
            ],
            "unit": "Polygon geometry",
            "citation_apa": "GADM. (2022). Database of Global Administrative Areas, version 4.1.",
            "citation_bibtex": "@misc{gadm2022, title={Database of Global Administrative Areas, version 4.1}, author={{GADM}}, year={2022}, url={https://gadm.org/}}",
            "file_size_mb": None,
            "crs": "EPSG:4326",
            "created_at_utc": now,
        },
    )

    write_text_if_missing(
        settings.project_root / "data" / "raw" / "MANIFEST.md",
        "# Raw Data Manifest\n\nRaw data in this project refers to source-derived files after basic preprocessing such as clipping, cleaning, reprojection, and compositing. Raw satellite tiles are not stored.\n",
    )

    write_text_if_missing(
        settings.project_root / "data" / "processed" / "PROCESSING_LOG.md",
        "# Processing Log\n\nThis file records derived analytical outputs such as demand index grids, candidate MFC locations, optimization results, emission scenarios, and spatial statistics.\n",
    )

    write_text_if_missing(
        settings.project_root / "data" / "external" / "references" / "README.md",
        "# External References\n\nThis folder stores open bibliographic references and citation material used by the methodology.\n",
    )

    write_text_if_missing(
        settings.project_root / "data" / "external" / "references" / "key_studies.bib",
        """@article{weber2020nighttime,
  title={Using nighttime lights to proxy economic activity},
  author={Weber, N. and others},
  journal={Remote Sensing},
  year={2020}
}

@misc{gadm2022,
  title={Database of Global Administrative Areas, version 4.1},
  author={{GADM}},
  year={2022},
  url={https://gadm.org/}
}
""",
    )

    for folder, title in [
        ("outputs/figures/maps", "Static Maps"),
        ("outputs/figures/charts", "Charts"),
        ("outputs/maps_interactive", "Interactive Maps"),
        ("outputs/tables", "Output Tables"),
        ("outputs/geotiffs", "Output GeoTIFFs"),
        ("outputs/reports", "Reports"),
    ]:
        write_text_if_missing(
            settings.project_root / folder / "README.md",
            f"# {title}\n\nThis folder is populated by the reproducible project pipeline.\n",
        )

    write_text_if_missing(
        settings.project_root / "outputs" / "run_log.md",
        "# Run Log\n\nProject execution log entries are appended below.\n",
    )

    write_text_if_missing(
        settings.project_root / "content" / "public-facing portfolio_post.md",
        "# public-facing portfolio Post\n\nThis file is generated by the publication pipeline.\n",
    )

    write_text_if_missing(
        settings.project_root / "content" / "public-facing portfolio_article.md",
        "# public-facing portfolio Article\n\nThis file is generated by the publication pipeline.\n",
    )

    write_text_if_missing(
        settings.project_root / "content" / "public-facing portfolio_upload_guide.md",
        "# public-facing portfolio Upload Guide\n\nThis file is generated by the publication pipeline.\n",
    )

    write_text_if_missing(
        settings.project_root / "docs" / "methodology_detail.md",
        "# Methodology Detail\n\nDetailed methodological documentation is generated and updated by the reporting pipeline.\n",
    )

    write_text_if_missing(
        settings.project_root / "docs" / "data_dictionary.md",
        "# Data Dictionary\n\nThis file documents fields, units, thresholds, and interpretation rules for analytical outputs.\n",
    )

    write_text_if_missing(
        settings.project_root / "docs" / "references.bib",
        """@misc{gadm2022,
  title={Database of Global Administrative Areas, version 4.1},
  author={{GADM}},
  year={2022},
  url={https://gadm.org/}
}
""",
    )

    write_text_if_missing(
        settings.project_root / "docs" / "figures_index.md",
        "# Figures Index\n\nThis file indexes generated maps and charts with file names, intended audience, and analytical purpose.\n",
    )

    write_text_if_missing(
        settings.project_root / "tests" / "__init__.py",
        '"""Test package for the micro-fulfillment network project."""\n',
    )

    write_text_if_missing(
        settings.project_root / "tests" / "conftest.py",
        """from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
""",
    )

    write_text_if_missing(
        settings.project_root / "tests" / "test_preprocessing.py",
        """from __future__ import annotations

import numpy as np

from micro_fulfillment_network_jakarta.preprocessing import min_max_scale


def test_min_max_scale_range() -> None:
    values = np.array([1.0, 2.0, 3.0])
    scaled = min_max_scale(values)
    assert float(scaled.min()) == 0.0
    assert float(scaled.max()) == 1.0
""",
    )

    write_text_if_missing(
        settings.project_root / "tests" / "test_analysis.py",
        """from __future__ import annotations

import pandas as pd

from micro_fulfillment_network_jakarta.analysis import compute_weighted_mean


def test_compute_weighted_mean() -> None:
    frame = pd.DataFrame({"value": [10.0, 20.0, 30.0], "weight": [1.0, 2.0, 1.0]})
    result = compute_weighted_mean(frame, "value", "weight")
    assert result == 20.0
""",
    )

    write_text_if_missing(
        settings.project_root / "tests" / "test_optimization.py",
        """from __future__ import annotations

import numpy as np

from micro_fulfillment_network_jakarta.optimization import assign_nearest_facility


def test_assign_nearest_facility() -> None:
    distance_matrix = np.array([[1.0, 5.0], [3.0, 2.0]])
    assignment = assign_nearest_facility(distance_matrix)
    assert assignment.tolist() == [0, 1]
""",
    )

    logger.info("Folder bootstrap completed successfully.")
    print("Bootstrap completed successfully.")
    print(f"Project root: {settings.project_root}")


if __name__ == "__main__":
    main()
