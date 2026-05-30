from __future__ import annotations

from micro_fulfillment_network_jakarta.reporting import (
    interpret_emission_reduction,
    interpret_moran_i,
    interpret_service_coverage,
)


def assert_interpretation_schema(payload: dict[str, str]) -> None:
    """Validate the standard interpretation dictionary schema."""
    required_keys = {"level", "description", "recommendation", "reference"}
    assert required_keys.issubset(payload.keys())
    for key in required_keys:
        assert isinstance(payload[key], str)
        assert len(payload[key]) > 0


def test_interpret_service_coverage_schema() -> None:
    """Service coverage interpretation should return the standard schema."""
    assert_interpretation_schema(interpret_service_coverage(0.92))


def test_interpret_emission_reduction_schema() -> None:
    """Emission reduction interpretation should return the standard schema."""
    assert_interpretation_schema(interpret_emission_reduction(35.0))


def test_interpret_moran_i_schema() -> None:
    """Moran's I interpretation should return the standard schema."""
    assert_interpretation_schema(interpret_moran_i(0.25))


def test_service_coverage_high_threshold() -> None:
    """Coverage above 90 percent should be labeled High."""
    payload = interpret_service_coverage(0.95)
    assert payload["level"] == "High"


def test_emission_reduction_high_threshold() -> None:
    """Emission reduction above 30 percent should be labeled High or better."""
    payload = interpret_emission_reduction(35.0)
    assert payload["level"] in {"High", "Transformational"}
