from __future__ import annotations

from pathlib import Path


def interpret_service_coverage(value: float) -> dict[str, str]:
    """Interpret 30-minute service coverage share."""
    if value >= 0.90:
        level = "High"
        description = "At least 90 percent of demand proxy is covered within the 30-minute service threshold."
        recommendation = "Use this configuration as a minimum service-level candidate and compare marginal cost against higher MFC counts."
    elif value >= 0.75:
        level = "Moderate"
        description = "Coverage is operationally meaningful but below the 90 percent target."
        recommendation = "Add MFCs in underserved high-demand clusters before scaling fleet electrification."
    else:
        level = "Low"
        description = "A large share of demand proxy remains outside the 30-minute service threshold."
        recommendation = "Do not use this network as the main quick-commerce configuration without additional fulfillment nodes."
    return {
        "level": level,
        "description": description,
        "recommendation": recommendation,
        "reference": "Quick commerce service-level convention is represented by a 30-minute delivery threshold; threshold is treated as an operational scenario assumption.",
    }


def interpret_emission_reduction(value: float) -> dict[str, str]:
    """Interpret emission reduction percentage."""
    if value >= 50:
        level = "Transformational"
        description = "The scenario reduces operational CO2e by at least half relative to the centralized ICE baseline."
        recommendation = "Prioritize implementation if investment cost and inventory complexity remain acceptable."
    elif value >= 30:
        level = "High"
        description = "The scenario reaches a high decarbonization effect and is consistent with combined logistics optimization and EV adoption."
        recommendation = "Use this scenario as the practical decarbonization benchmark for phased implementation."
    elif value >= 10:
        level = "Moderate"
        description = "The scenario produces measurable CO2e savings but may be insufficient for aggressive decarbonization targets."
        recommendation = "Increase MFC coverage or accelerate EV adoption."
    else:
        level = "Low"
        description = "The scenario yields limited CO2e reduction relative to baseline."
        recommendation = "Reassess facility placement, delivery density, or fleet technology assumptions."
    return {
        "level": level,
        "description": description,
        "recommendation": recommendation,
        "reference": "Emission reduction follows scenario-based CO2e accounting using distance multiplied by vehicle emission factors.",
    }


def interpret_moran_i(value: float) -> dict[str, str]:
    """Interpret Global Moran's I."""
    if value >= 0.30:
        level = "Strong positive spatial autocorrelation"
        description = "High and low values are spatially clustered rather than randomly distributed."
        recommendation = "Use LISA clusters to target spatially contiguous intervention zones."
    elif value >= 0.10:
        level = "Moderate positive spatial autocorrelation"
        description = "The metric shows meaningful spatial clustering."
        recommendation = "Prioritize clusters but verify local robustness with permutation p-values."
    elif value > -0.10:
        level = "Weak or near-random spatial pattern"
        description = "The metric does not show strong global clustering."
        recommendation = "Use local diagnostics and operational constraints instead of relying on broad hotspot assumptions."
    else:
        level = "Negative spatial autocorrelation"
        description = "High and low values tend to be spatially dispersed."
        recommendation = "Investigate outliers and edge effects before drawing operational conclusions."
    return {
        "level": level,
        "description": description,
        "recommendation": recommendation,
        "reference": "Moran's I interpretation follows spatial autocorrelation theory with permutation-based significance testing.",
    }


def write_markdown(path: Path, content: str) -> Path:
    """Write a Markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def bullet_list(items: list[str]) -> str:
    """Convert a list of strings to Markdown bullet list."""
    return "\n".join(f"* {item}" for item in items)
