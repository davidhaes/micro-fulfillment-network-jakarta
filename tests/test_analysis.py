from __future__ import annotations

import pandas as pd

from micro_fulfillment_network_jakarta.analysis import compute_weighted_mean


def test_compute_weighted_mean() -> None:
    frame = pd.DataFrame({"value": [10.0, 20.0, 30.0], "weight": [1.0, 2.0, 1.0]})
    result = compute_weighted_mean(frame, "value", "weight")
    assert result == 20.0
