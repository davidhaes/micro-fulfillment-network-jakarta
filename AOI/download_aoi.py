from __future__ import annotations

import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely import make_valid
from shapely.geometry import MultiPolygon, Polygon
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import file_size_mb, write_metadata
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.validators import validate_geodataframe


GADM_LEVEL2_ZIP_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_IDN_2.json.zip"


TARGET_NAME2_PATTERNS = [
    r"jakarta barat",
    r"jakarta pusat",
    r"jakarta selatan",
    r"jakarta timur",
    r"jakarta utara",
    r"kota bogor",
    r"bogor",
    r"depok",
    r"kota depok",
    r"kota tangerang",
    r"tangerang selatan",
    r"kota tangerang selatan",
    r"tangerang",
    r"kota bekasi",
    r"bekasi",
]


EXCLUDE_NAME2_PATTERNS = [
    r"kepulauan seribu",
    r"seribu",
]


def normalize_name(value: object) -> str:
    """Normalize administrative names for robust matching, including camel-case names."""
    text = "" if pd.isna(value) else str(value)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def compact_name(value: object) -> str:
    """Normalize administrative names into compact strings without spaces."""
    return normalize_name(value).replace(" ", "")

def repair_geometry(geometry):
    """Repair invalid geometry using shapely.make_valid with buffer fallback."""
    if geometry is None:
        return geometry

    if geometry.is_empty:
        return geometry

    if geometry.is_valid:
        return geometry

    try:
        repaired = make_valid(geometry)
        if repaired is not None and not repaired.is_empty and repaired.is_valid:
            return repaired
    except Exception:
        pass

    try:
        repaired = geometry.buffer(0)
        if repaired is not None and not repaired.is_empty:
            return repaired
    except Exception:
        pass

    return geometry


def repair_geodataframe_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Repair invalid geometries and remove empty geometries."""
    output = gdf.copy()
    output["geometry"] = output.geometry.apply(repair_geometry)
    output = output[output.geometry.notna() & ~output.geometry.is_empty].copy()
    return output


def download_file(url: str, output_path: Path) -> Path:
    """Download a URL to a local file with a progress bar."""
    logger = get_logger("download_aoi")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logger.info(f"Using cached file from {output_path}")
        return output_path

    logger.info(f"Downloading and pre-processing fresh from {url}")
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    with output_path.open("wb") as file, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        desc="Downloading GADM",
    ) as progress:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file.write(chunk)
                progress.update(len(chunk))

    return output_path


def extract_geojson(zip_path: Path, extract_dir: Path) -> Path:
    """Extract the GADM GeoJSON file from a zip archive."""
    logger = get_logger("download_aoi")
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as archive:
        candidates = [name for name in archive.namelist() if name.lower().endswith(".json")]
        if not candidates:
            raise FileNotFoundError("No GeoJSON JSON file found inside GADM zip archive.")
        member = candidates[0]
        output_path = extract_dir / Path(member).name

        if output_path.exists():
            logger.info(f"Using cached file from {output_path}")
            return output_path

        logger.info(f"Extracting {member} to {output_path}")
        archive.extract(member, extract_dir)
        extracted_path = extract_dir / member
        if extracted_path != output_path:
            extracted_path.replace(output_path)

    return output_path


def select_greater_jakarta_units(gdf: gpd.GeoDataFrame, exclude_kepulauan_seribu: bool = True) -> gpd.GeoDataFrame:
    """Select Greater Jakarta administrative units from GADM level 2 with strict validation."""
    required_columns = ["NAME_1", "NAME_2", "geometry"]
    missing_columns = [column for column in required_columns if column not in gdf.columns]
    if missing_columns:
        raise KeyError(f"Missing required GADM columns: {missing_columns}")

    if gdf.empty:
        raise ValueError("GADM GeoDataFrame is empty.")

    if gdf.crs is None:
        raise ValueError("GADM GeoDataFrame CRS is missing.")

    output = repair_geodataframe_geometries(gdf)

    output["name1_norm"] = output["NAME_1"].map(normalize_name)
    output["name2_norm"] = output["NAME_2"].map(normalize_name)
    output["name1_compact"] = output["NAME_1"].map(compact_name)
    output["name2_compact"] = output["NAME_2"].map(compact_name)

    accepted_province_compact = {
        "jakarta",
        "jakartaraya",
        "dkijakarta",
        "banten",
        "jawabarat",
        "westjava",
    }

    province_mask = (
        output["name1_compact"].isin(accepted_province_compact)
        | output["name1_compact"].str.contains(r"jakarta|banten|jawabarat|westjava", regex=True, na=False)
    )

    target_units_compact = {
        "jakartabarat",
        "jakartapusat",
        "jakartaselatan",
        "jakartatimur",
        "jakartautara",
        "kotabogor",
        "bogor",
        "depok",
        "kotadepok",
        "kotatangerang",
        "tangerangselatan",
        "kotatangerangselatan",
        "tangerang",
        "kotabekasi",
        "bekasi",
    }

    target_mask = output["name2_compact"].isin(target_units_compact)

    broad_target_mask = output["name2_compact"].str.contains(
        r"jakartabarat|jakartapusat|jakartaselatan|jakartatimur|jakartautara|"
        r"kotabogor|bogor|kotadepok|depok|kotatangerangselatan|tangerangselatan|"
        r"kotatangerang|tangerang|kotabekasi|bekasi",
        regex=True,
        na=False,
    )

    selected = output[province_mask & (target_mask | broad_target_mask)].copy()

    if exclude_kepulauan_seribu:
        selected = selected[
            ~selected["name2_compact"].str.contains(r"kepulauanseribu|seribu", regex=True, na=False)
        ].copy()

    selected = selected.drop(columns=["name1_norm", "name2_norm", "name1_compact", "name2_compact"])
    selected = repair_geodataframe_geometries(selected)
    selected = selected.sort_values(["NAME_1", "NAME_2"]).reset_index(drop=True)

    if selected.empty:
        available = output[["NAME_1", "NAME_2"]].drop_duplicates().sort_values(["NAME_1", "NAME_2"])
        raise ValueError(
            "No Greater Jakarta units selected. "
            f"Available units sample: {available.head(150).to_dict('records')}"
        )

    if len(selected) < 10:
        available_context = output[
            output["name1_compact"].str.contains(r"jakarta|banten|jawabarat|westjava", regex=True, na=False)
        ][["NAME_1", "NAME_2"]].drop_duplicates().sort_values(["NAME_1", "NAME_2"])

        selected_preview = selected[["NAME_1", "NAME_2"]].to_dict("records")
        context_preview = available_context.head(250).to_dict("records")

        raise ValueError(
            "AOI selection returned fewer than 10 units, which is too small for the intended "
            "Greater Jakarta road-based logistics region. "
            f"Selected units: {selected_preview}. "
            f"Available province-context units sample: {context_preview}"
        )

    validate_geodataframe(selected, required_columns=["NAME_1", "NAME_2"])
    return selected


def dissolve_aoi(selected_units: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Dissolve selected administrative units into one metropolitan AOI."""
    selected_units = repair_geodataframe_geometries(selected_units)
    dissolved_geometry = selected_units.geometry.unary_union
    dissolved_geometry = repair_geometry(dissolved_geometry)

    if isinstance(dissolved_geometry, Polygon):
        dissolved_geometry = MultiPolygon([dissolved_geometry])

    dissolved = gpd.GeoDataFrame(
        {
            "aoi_name": ["Greater Jakarta road-based quick-commerce logistics region"],
            "included_units": [", ".join(selected_units["NAME_2"].astype(str).tolist())],
            "unit_count": [int(len(selected_units))],
        },
        geometry=[dissolved_geometry],
        crs=selected_units.crs,
    )

    dissolved = repair_geodataframe_geometries(dissolved)
    return dissolved


def write_aoi_metadata(aoi_path: Path, selected_path: Path, selected_units: gpd.GeoDataFrame) -> None:
    """Write AOI metadata JSON files."""
    now = datetime.now(timezone.utc).date().isoformat()
    units = selected_units[["NAME_1", "NAME_2"]].to_dict("records")

    aoi_metadata = {
        "dataset_name": "Greater Jakarta dissolved AOI",
        "source": "GADM 4.1",
        "source_url": GADM_LEVEL2_ZIP_URL,
        "license": "GADM license for academic and non-commercial use",
        "access_date": now,
        "spatial_resolution": "Administrative boundary level 2 dissolved to metropolitan AOI",
        "temporal_coverage": "Static administrative boundary",
        "preprocessing_steps": [
            "Downloaded GADM Indonesia level 2 GeoJSON zip",
            "Filtered DKI Jakarta, Bogor, Depok, Tangerang, and Bekasi administrative units",
            "Excluded Kepulauan Seribu because the study focuses on road-based last-mile logistics",
            "Dissolved selected units into one functional metropolitan AOI",
        ],
        "unit": "Polygon geometry",
        "citation_apa": "GADM. (2022). Database of Global Administrative Areas, version 4.1.",
        "citation_bibtex": "@misc{gadm2022, title={Database of Global Administrative Areas, version 4.1}, author={{GADM}}, year={2022}, url={https://gadm.org/}}",
        "file_size_mb": file_size_mb(aoi_path),
        "crs": "EPSG:4326",
        "included_units": units,
    }
    (aoi_path.parent / "aoi_metadata.json").write_text(
        json.dumps(aoi_metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )

    write_metadata(
        data_path=selected_path,
        dataset_name="Greater Jakarta GADM level 2 selected units",
        source="GADM 4.1",
        source_url=GADM_LEVEL2_ZIP_URL,
        license_name="GADM license for academic and non-commercial use",
        spatial_resolution="Administrative boundary level 2",
        temporal_coverage="Static administrative boundary",
        preprocessing_steps=[
            "Downloaded GADM Indonesia level 2 GeoJSON zip",
            "Filtered Greater Jakarta road-based logistics administrative units",
            "Excluded Kepulauan Seribu from core logistics AOI",
            "Saved selected level 2 units as GeoJSON",
        ],
        unit="Polygon geometry",
        citation_apa="GADM. (2022). Database of Global Administrative Areas, version 4.1.",
        citation_bibtex="@misc{gadm2022, title={Database of Global Administrative Areas, version 4.1}, author={{GADM}}, year={2022}, url={https://gadm.org/}}",
        crs="EPSG:4326",
        extra={"included_units": units},
    )


def main() -> None:
    """Download and generate the Greater Jakarta AOI."""
    settings = get_settings()
    logger = get_logger("download_aoi")

    logger.info("Starting AOI generation from GADM 4.1.")
    temp_dir = settings.project_root / ".cache" / "gadm"
    zip_path = temp_dir / "gadm41_IDN_2.json.zip"
    extracted_geojson = extract_geojson(download_file(GADM_LEVEL2_ZIP_URL, zip_path), temp_dir)

    logger.info(f"Reading GADM level 2 file: {extracted_geojson}")
    gadm = gpd.read_file(extracted_geojson)
    if gadm.crs is None:
        gadm = gadm.set_crs(settings.default_crs)
    gadm = gadm.to_crs(settings.default_crs)
    gadm = repair_geodataframe_geometries(gadm)

    selected_units = select_greater_jakarta_units(
        gadm,
        exclude_kepulauan_seribu=settings.aoi_exclude_kepulauan_seribu,
    )
    validate_geodataframe(selected_units, required_columns=["NAME_1", "NAME_2"])

    dissolved = dissolve_aoi(selected_units)
    validate_geodataframe(dissolved, required_columns=["aoi_name", "unit_count"])

    aoi_path = settings.aoi_dir / "aoi_default.geojson"
    selected_path = settings.raw_dir / "gadm_aoi" / "greater_jakarta_gadm_level2.geojson"

    aoi_path.parent.mkdir(parents=True, exist_ok=True)
    selected_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Writing dissolved AOI to {aoi_path}")
    dissolved.to_file(aoi_path, driver="GeoJSON")

    logger.info(f"Writing selected GADM units to {selected_path}")
    selected_units.to_file(selected_path, driver="GeoJSON")

    write_aoi_metadata(aoi_path, selected_path, selected_units)

    logger.info(f"AOI generation completed with {len(selected_units)} administrative units.")
    print("AOI generation completed.")
    print(f"Dissolved AOI: {aoi_path}")
    print(f"Selected units: {selected_path}")


if __name__ == "__main__":
    main()
