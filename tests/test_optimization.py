from __future__ import annotations

import numpy as np

from micro_fulfillment_network_jakarta.optimization import assign_nearest_facility, greedy_p_median


def test_assign_nearest_facility() -> None:
    """Nearest assignment should choose the lowest-distance facility per demand point."""
    distance_matrix = np.array([[1.0, 5.0], [3.0, 2.0]])
    assignment = assign_nearest_facility(distance_matrix)
    assert assignment.tolist() == [0, 1]


def test_greedy_p_median_selects_requested_count() -> None:
    """Greedy p-median should select exactly p candidates when enough candidates exist."""
    distance_matrix = np.array(
        [
            [1.0, 4.0, 9.0],
            [2.0, 1.0, 8.0],
            [9.0, 6.0, 1.0],
        ]
    )
    weights = np.array([1.0, 1.0, 1.0])
    selected = greedy_p_median(distance_matrix, weights, p=2)
    assert len(selected) == 2
    assert len(set(selected)) == 2


def test_greedy_p_median_caps_at_candidate_count() -> None:
    """Greedy p-median should cap p at the number of candidates."""
    distance_matrix = np.array([[1.0, 2.0], [2.0, 1.0]])
    weights = np.array([1.0, 1.0])
    selected = greedy_p_median(distance_matrix, weights, p=5)
    assert len(selected) == 2
