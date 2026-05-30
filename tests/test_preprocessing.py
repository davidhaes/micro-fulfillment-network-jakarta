from __future__ import annotations

import numpy as np

from micro_fulfillment_network_jakarta.preprocessing import min_max_scale


def test_min_max_scale_range() -> None:
    """Scaled values should stay within the 0 to 1 range."""
    values = np.array([1.0, 2.0, 3.0])
    scaled = min_max_scale(values)
    assert np.nanmin(scaled) >= 0.0
    assert np.nanmax(scaled) <= 1.0


def test_min_max_scale_constant_values() -> None:
    """Constant values should not produce division-by-zero errors."""
    values = np.array([5.0, 5.0, 5.0])
    scaled = min_max_scale(values)
    assert np.allclose(scaled, np.zeros_like(values))


def test_min_max_scale_nan_values() -> None:
    """NaN values should remain NaN while finite values are scaled."""
    values = np.array([1.0, np.nan, 3.0])
    scaled = min_max_scale(values)
    assert np.isnan(scaled[1])
    assert np.nanmin(scaled) >= 0.0
    assert np.nanmax(scaled) <= 1.0
