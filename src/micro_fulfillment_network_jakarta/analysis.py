from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm


def compute_weighted_mean(frame: pd.DataFrame, value_column: str, weight_column: str) -> float:
    """Compute a weighted mean from a DataFrame."""
    values = frame[value_column].astype(float).to_numpy()
    weights = frame[weight_column].astype(float).to_numpy()

    valid = np.isfinite(values) & np.isfinite(weights) & (weights >= 0)
    if not valid.any():
        return float("nan")

    total_weight = weights[valid].sum()
    if np.isclose(total_weight, 0.0):
        return float("nan")

    return float(np.average(values[valid], weights=weights[valid]))


def compute_concentration_share(frame: pd.DataFrame, value_column: str, area_column: str, value_share: float = 0.7) -> dict[str, float]:
    """Compute the area share required to accumulate a target value share."""
    ordered = frame.sort_values(value_column, ascending=False).copy()
    total_value = float(ordered[value_column].sum())
    total_area = float(ordered[area_column].sum())

    if np.isclose(total_value, 0.0) or np.isclose(total_area, 0.0):
        return {"value_share": value_share, "area_share": float("nan")}

    ordered["cumulative_value_share"] = ordered[value_column].cumsum() / total_value
    selected = ordered[ordered["cumulative_value_share"] <= value_share].copy()

    if selected.empty:
        selected = ordered.head(1)

    area_share = float(selected[area_column].sum() / total_area)
    return {"value_share": value_share, "area_share": area_share}


def run_kmeans(frame: pd.DataFrame, feature_columns: list[str], n_clusters: int, random_seed: int = 42) -> pd.Series:
    """Run KMeans clustering on selected feature columns."""
    features = frame[feature_columns].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    scaled = StandardScaler().fit_transform(features)
    model = KMeans(n_clusters=n_clusters, random_state=random_seed, n_init=20)
    labels = model.fit_predict(scaled)
    return pd.Series(labels, index=frame.index, name="cluster")


def simple_ols_summary(frame: pd.DataFrame, dependent: str, independents: list[str]) -> dict[str, float]:
    """Fit an OLS regression and return core diagnostics."""
    clean = frame[[dependent] + independents].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) <= len(independents) + 2:
        return {"r_squared": float("nan"), "adj_r_squared": float("nan"), "f_pvalue": float("nan")}

    y = clean[dependent]
    x = sm.add_constant(clean[independents])
    model = sm.OLS(y, x).fit()
    return {
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "f_pvalue": float(model.f_pvalue) if model.f_pvalue is not None else float("nan"),
    }


def pearson_correlation_with_pvalue(x: pd.Series, y: pd.Series) -> dict[str, float]:
    """Compute Pearson correlation and p-value."""
    clean = pd.DataFrame({"x": x, "y": y}).astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < 3:
        return {"r": float("nan"), "p_value": float("nan")}
    r_value, p_value = stats.pearsonr(clean["x"], clean["y"])
    return {"r": float(r_value), "p_value": float(p_value)}
