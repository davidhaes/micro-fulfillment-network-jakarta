from __future__ import annotations

import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp
from scipy.spatial.distance import cdist


def compute_euclidean_distance_matrix(demand_xy: np.ndarray, candidate_xy: np.ndarray) -> np.ndarray:
    """Compute Euclidean distance matrix between demand points and candidate facilities."""
    return cdist(demand_xy.astype(float), candidate_xy.astype(float), metric="euclidean")


def assign_nearest_facility(distance_matrix: np.ndarray) -> np.ndarray:
    """Assign each demand point to the nearest facility column."""
    if distance_matrix.ndim != 2:
        raise ValueError("Distance matrix must be two-dimensional.")
    return np.argmin(distance_matrix, axis=1)


def compute_weighted_assignment_cost(distance_matrix: np.ndarray, weights: np.ndarray, selected_indices: list[int]) -> float:
    """Compute total demand-weighted distance for selected candidate indices."""
    if len(selected_indices) == 0:
        return float("inf")
    submatrix = distance_matrix[:, selected_indices]
    nearest_distance = np.min(submatrix, axis=1)
    return float(np.sum(nearest_distance * weights))


def greedy_p_median(distance_matrix: np.ndarray, weights: np.ndarray, p: int) -> list[int]:
    """Select p facilities using a deterministic vectorized greedy p-median heuristic."""
    if distance_matrix.ndim != 2:
        raise ValueError("Distance matrix must be two-dimensional.")
    if p <= 0:
        raise ValueError("p must be positive.")

    n_demand, n_candidates = distance_matrix.shape
    if n_demand == 0 or n_candidates == 0:
        raise ValueError("Distance matrix must have at least one demand point and one candidate.")

    weights = np.asarray(weights, dtype=float)
    if weights.shape[0] != n_demand:
        raise ValueError("Weights length must match the number of demand points.")
    if np.any(weights < 0):
        raise ValueError("Weights must be non-negative.")
    if np.isclose(weights.sum(), 0.0):
        raise ValueError("Weights must have positive total weight.")

    p = min(int(p), n_candidates)

    selected: list[int] = []
    remaining = np.arange(n_candidates, dtype=int)
    current_nearest = np.full(n_demand, np.inf, dtype=float)

    for _ in range(p):
        candidate_distances = distance_matrix[:, remaining]
        trial_nearest = np.minimum(current_nearest[:, None], candidate_distances)
        trial_costs = (trial_nearest * weights[:, None]).sum(axis=0)

        best_position = int(np.argmin(trial_costs))
        best_candidate = int(remaining[best_position])

        selected.append(best_candidate)
        current_nearest = np.minimum(current_nearest, distance_matrix[:, best_candidate])
        remaining = np.delete(remaining, best_position)

        if remaining.size == 0:
            break

    return selected


def solve_p_median_mip(distance_matrix: np.ndarray, weights: np.ndarray, p: int, time_limit_seconds: int = 120) -> list[int]:
    """Solve p-median as a mixed-integer program using OR-Tools CBC solver."""
    n_demand, n_candidates = distance_matrix.shape
    if p <= 0:
        raise ValueError("p must be positive.")
    p = min(p, n_candidates)

    solver = pywraplp.Solver.CreateSolver("CBC")
    if solver is None:
        return greedy_p_median(distance_matrix, weights, p)

    solver.SetTimeLimit(time_limit_seconds * 1000)

    open_vars = [solver.BoolVar(f"open_{j}") for j in range(n_candidates)]
    assign_vars = {
        (i, j): solver.BoolVar(f"assign_{i}_{j}")
        for i in range(n_demand)
        for j in range(n_candidates)
    }

    solver.Add(sum(open_vars) == p)

    for i in range(n_demand):
        solver.Add(sum(assign_vars[(i, j)] for j in range(n_candidates)) == 1)
        for j in range(n_candidates):
            solver.Add(assign_vars[(i, j)] <= open_vars[j])

    objective = solver.Objective()
    for i in range(n_demand):
        for j in range(n_candidates):
            objective.SetCoefficient(assign_vars[(i, j)], float(distance_matrix[i, j] * weights[i]))
    objective.SetMinimization()

    status = solver.Solve()

    if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        return greedy_p_median(distance_matrix, weights, p)

    selected = [j for j, var in enumerate(open_vars) if var.solution_value() > 0.5]
    if len(selected) != p:
        return greedy_p_median(distance_matrix, weights, p)

    return selected


def compute_coverage(distance_matrix: np.ndarray, weights: np.ndarray, selected_indices: list[int], threshold_meters: float) -> dict[str, float]:
    """Compute demand coverage within a distance threshold."""
    weights = np.asarray(weights, dtype=float)

    if len(selected_indices) == 0:
        return {
            "covered_weight": 0.0,
            "total_weight": float(weights.sum()),
            "coverage_share": 0.0,
            "mean_nearest_distance_m": float("nan"),
            "p90_nearest_distance_m": float("nan"),
            "max_nearest_distance_m": float("nan"),
        }

    nearest_distance = np.min(distance_matrix[:, selected_indices], axis=1)
    covered = nearest_distance <= threshold_meters
    covered_weight = float(weights[covered].sum())
    total_weight = float(weights.sum())
    coverage_share = covered_weight / total_weight if total_weight > 0 else 0.0

    return {
        "covered_weight": covered_weight,
        "total_weight": total_weight,
        "coverage_share": float(coverage_share),
        "mean_nearest_distance_m": float(np.average(nearest_distance, weights=weights)) if total_weight > 0 else float("nan"),
        "p90_nearest_distance_m": float(np.percentile(nearest_distance, 90)),
        "max_nearest_distance_m": float(nearest_distance.max()),
    }


def summarize_network_scenario(distance_matrix: np.ndarray, weights: np.ndarray, selected_indices: list[int], p: int, threshold_meters: float) -> pd.DataFrame:
    """Return one-row summary for an optimized network scenario."""
    coverage = compute_coverage(distance_matrix, weights, selected_indices, threshold_meters)
    coverage["mfc_count"] = int(p)
    coverage["selected_candidate_count"] = int(len(selected_indices))
    return pd.DataFrame([coverage])

