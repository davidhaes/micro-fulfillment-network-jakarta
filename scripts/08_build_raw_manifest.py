from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import compute_data_folder_size_gb, write_csv, write_text
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import validate_storage_cap


def collect_raw_metadata(raw_dir: Path) -> list[dict]:
    """Collect metadata JSON records from the raw data directory."""
    records: list[dict] = []
    for metadata_path in sorted(raw_dir.rglob("*.metadata.json")):
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        data_file_name = metadata_path.name.replace(".metadata.json", "")
        data_path = metadata_path.with_name(data_file_name)
        payload["metadata_path"] = str(metadata_path.relative_to(raw_dir.parent.parent))
        payload["data_path"] = str(data_path.relative_to(raw_dir.parent.parent))
        records.append(payload)
    return records


def build_manifest_markdown(records: list[dict], data_size_gb: float) -> str:
    """Build raw data manifest Markdown without using Markdown tables."""

    lines = [
        "# Raw Data Manifest",
        "",
        f"Total data folder size: {data_size_gb:.4f} GB",
        "",
        "Raw data in this project means source-derived files after basic preprocessing. Satellite tiles, unprocessed global rasters, and manually supplied shapefiles are not stored.",
        "",
        "Datasets:",
        "",
    ]

    if not records:
        lines.append("* No raw dataset metadata found yet.")
        return "\n".join(lines) + "\n"

    for index, record in enumerate(records, start=1):
        lines.extend(
            [
                f"{index}. {record.get('dataset_name', 'Unnamed dataset')}",
                f"   * Data path: `{record.get('data_path', 'unknown')}`",
                f"   * Metadata path: `{record.get('metadata_path', 'unknown')}`",
                f"   * Source: {record.get('source', 'unknown')}",
                f"   * Source URL: {record.get('source_url', 'unknown')}",
                f"   * License: {record.get('license', 'unknown')}",
                f"   * Access date: {record.get('access_date', 'unknown')}",
                f"   * Spatial resolution: {record.get('spatial_resolution', 'unknown')}",
                f"   * Temporal coverage: {record.get('temporal_coverage', 'unknown')}",
                f"   * Unit: {record.get('unit', 'unknown')}",
                f"   * CRS: {record.get('crs', 'unknown')}",
                f"   * File size MB: {record.get('file_size_mb', 'unknown')}",
                "   * Preprocessing steps:",
            ]
        )
        for step in record.get("preprocessing_steps", []):
            lines.append(f"     * {step}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    """Build raw data manifest and metadata index table."""
    settings = get_settings()
    logger = get_logger("08_build_raw_manifest")

    logger.info("Building raw data manifest.")
    records = collect_raw_metadata(settings.raw_dir)

    data_size_gb = compute_data_folder_size_gb()
    validate_storage_cap()

    manifest = build_manifest_markdown(records, data_size_gb)
    manifest_path = settings.raw_dir / "MANIFEST.md"
    write_text(manifest_path, manifest)

    if records:
        index_frame = pd.DataFrame(records)
    else:
        index_frame = pd.DataFrame(
            columns=[
                "dataset_name",
                "source",
                "source_url",
                "license",
                "access_date",
                "spatial_resolution",
                "temporal_coverage",
                "unit",
                "crs",
                "file_size_mb",
                "data_path",
                "metadata_path",
            ]
        )

    index_path = settings.tables_dir / "raw_data_inventory.csv"
    write_csv(index_frame, index_path)

    logger.info(f"Raw manifest written to {manifest_path}")
    logger.info(f"Raw inventory table written to {index_path}")
    print(f"Raw manifest completed: {manifest_path}")
    print(f"Raw inventory completed: {index_path}")


if __name__ == "__main__":
    main()
