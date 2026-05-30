from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

load_dotenv()


class Settings(BaseModel):
    """Runtime settings for the Greater Jakarta micro-fulfillment project."""

    project_root: Path = Field(
        default_factory=lambda: Path(os.getenv("PROJECT_ROOT", r"E:\Project\micro-fulfillment-network-jakarta"))
    )
    gee_project_id: str = Field(default_factory=lambda: os.getenv("GEE_PROJECT_ID", "ee-davidproject"))
    gee_service_account: str = Field(
        default_factory=lambda: os.getenv(
            "GEE_SERVICE_ACCOUNT",
            "gee-service@ee-davidproject.iam.gserviceaccount.com",
        )
    )
    gee_key_file: Path = Field(
        default_factory=lambda: Path(
            os.getenv("GEE_KEY_FILE", r"E:\Project\ee-davidproject-21f5e27cb4ee.json")
        )
    )

    default_crs: str = Field(default_factory=lambda: os.getenv("DEFAULT_CRS", "EPSG:4326"))
    projected_crs: str = Field(default_factory=lambda: os.getenv("PROJECTED_CRS", "EPSG:32748"))

    random_seed: int = Field(default_factory=lambda: int(os.getenv("RANDOM_SEED", "42")))
    storage_cap_gb: float = Field(default_factory=lambda: float(os.getenv("STORAGE_CAP_GB", "10")))
    analysis_grid_size_meters: int = Field(
        default_factory=lambda: int(os.getenv("ANALYSIS_GRID_SIZE_METERS", "1000"))
    )

    service_level_minutes: float = Field(default_factory=lambda: float(os.getenv("SERVICE_LEVEL_MINUTES", "30")))
    default_speed_kmh: float = Field(default_factory=lambda: float(os.getenv("DEFAULT_SPEED_KMH", "20")))

    aoi_gadm_country: str = Field(default_factory=lambda: os.getenv("AOI_GADM_COUNTRY", "IDN"))
    aoi_gadm_version: str = Field(default_factory=lambda: os.getenv("AOI_GADM_VERSION", "4.1"))
    aoi_exclude_kepulauan_seribu: bool = Field(
        default_factory=lambda: os.getenv("AOI_EXCLUDE_KEPULAUAN_SERIBU", "true").lower() == "true"
    )

    mfc_counts: tuple[int, ...] = Field(default_factory=lambda: _parse_int_tuple(os.getenv("MFC_COUNTS", "5,10,15,20,25,30")))
    ev_adoption_scenarios: tuple[int, ...] = Field(
        default_factory=lambda: _parse_int_tuple(os.getenv("EV_ADOPTION_SCENARIOS", "0,25,50,75,100"))
    )

    @field_validator("project_root", "gee_key_file")
    @classmethod
    def expand_path(cls, value: Path) -> Path:
        """Expand and resolve user-supplied paths without requiring existence."""
        return Path(value).expanduser()

    @property
    def aoi_dir(self) -> Path:
        """Return the AOI directory."""
        return self.project_root / "AOI"

    @property
    def raw_dir(self) -> Path:
        """Return the raw data directory."""
        return self.project_root / "data" / "raw"

    @property
    def processed_dir(self) -> Path:
        """Return the processed data directory."""
        return self.project_root / "data" / "processed"

    @property
    def outputs_dir(self) -> Path:
        """Return the outputs directory."""
        return self.project_root / "outputs"

    @property
    def reports_dir(self) -> Path:
        """Return the reports directory."""
        return self.outputs_dir / "reports"

    @property
    def maps_dir(self) -> Path:
        """Return the static maps output directory."""
        return self.outputs_dir / "figures" / "maps"

    @property
    def charts_dir(self) -> Path:
        """Return the charts output directory."""
        return self.outputs_dir / "figures" / "charts"

    @property
    def tables_dir(self) -> Path:
        """Return the tables output directory."""
        return self.outputs_dir / "tables"

    @property
    def geotiffs_dir(self) -> Path:
        """Return the GeoTIFF output directory."""
        return self.outputs_dir / "geotiffs"


def _parse_int_tuple(value: str) -> tuple[int, ...]:
    """Parse a comma-separated integer string into a tuple."""
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached project settings."""
    return Settings()
