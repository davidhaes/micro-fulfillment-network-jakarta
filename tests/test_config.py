from __future__ import annotations

from micro_fulfillment_network_jakarta.config import get_settings


def test_projected_crs_default() -> None:
    """Projected CRS should default to Jakarta UTM zone 48S."""
    settings = get_settings()
    assert settings.projected_crs == "EPSG:32748"


def test_mfc_counts_are_positive() -> None:
    """MFC scenario counts should be positive integers."""
    settings = get_settings()
    assert len(settings.mfc_counts) > 0
    assert all(isinstance(value, int) for value in settings.mfc_counts)
    assert all(value > 0 for value in settings.mfc_counts)


def test_ev_adoption_scenarios_are_percentages() -> None:
    """EV adoption scenarios should be valid percentages."""
    settings = get_settings()
    assert len(settings.ev_adoption_scenarios) > 0
    assert all(0 <= value <= 100 for value in settings.ev_adoption_scenarios)


def test_service_level_is_positive() -> None:
    """Service-level threshold should be positive."""
    settings = get_settings()
    assert settings.service_level_minutes > 0


def test_grid_size_is_positive() -> None:
    """Analysis grid size should be positive."""
    settings = get_settings()
    assert settings.analysis_grid_size_meters > 0
