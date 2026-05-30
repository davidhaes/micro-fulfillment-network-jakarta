from __future__ import annotations

import sys
from pathlib import Path

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.analysis import compute_concentration_share
from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.viz_theme import save_figure, set_publication_theme
from micro_fulfillment_network_jakarta.validators import require_file


def annotate_point(ax, x_value, y_value, label: str) -> None:
    """Annotate a chart point with readable formatting."""
    ax.annotate(
        label,
        xy=(x_value, y_value),
        xytext=(8, 8),
        textcoords="offset points",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75},
        arrowprops={"arrowstyle": "->", "color": "#333333", "lw": 0.8},
    )


def plot_distance_reduction(summary: pd.DataFrame, output_dir: Path) -> None:
    """Plot demand-weighted distance reduction by MFC count."""
    set_publication_theme()
    fig, ax = plt.subplots(figsize=(10, 6))

    sns.lineplot(
        data=summary,
        x="mfc_count",
        y="distance_reduction_percent",
        marker="o",
        linewidth=2.4,
        color="#D32F2F",
        ax=ax,
    )

    best = summary.sort_values("distance_reduction_percent", ascending=False).iloc[0]
    annotate_point(
        ax,
        best["mfc_count"],
        best["distance_reduction_percent"],
        f"Best tested: {best['distance_reduction_percent']:.1f}%",
    )

    ax.axhline(20, color="#333333", linestyle="--", linewidth=1, alpha=0.8)
    ax.text(
        summary["mfc_count"].min(),
        20.8,
        "H1 threshold: 20% distance reduction",
        fontsize=8,
        color="#333333",
    )

    ax.set_title("Distance Reduction from Distributed Micro-Fulfillment", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Demand-weighted route-distance proxy per 100,000 proxy deliveries",
        transform=ax.transAxes,
        ha="left",
        fontsize=11,
    )
    ax.set_xlabel("Number of MFCs")
    ax.set_ylabel("Distance reduction versus centralized baseline, percent")
    ax.grid(True, alpha=0.3)

    save_figure(
        fig,
        output_dir / "distance_reduction_by_mfc_count.png",
        output_dir / "distance_reduction_by_mfc_count.pdf",
    )
    plt.close(fig)


def plot_service_coverage(summary: pd.DataFrame, output_dir: Path) -> None:
    """Plot 30-minute service coverage curve."""
    set_publication_theme()
    fig, ax = plt.subplots(figsize=(10, 6))

    plot_frame = summary.copy()
    plot_frame["coverage_percent"] = plot_frame["coverage_share"] * 100.0

    sns.lineplot(
        data=plot_frame,
        x="mfc_count",
        y="coverage_percent",
        marker="o",
        linewidth=2.4,
        color="#2CA25F",
        ax=ax,
    )

    ax.axhline(90, color="#D32F2F", linestyle="--", linewidth=1.1)
    ax.text(
        plot_frame["mfc_count"].min(),
        91,
        "Target: 90% proxy demand covered",
        fontsize=8,
        color="#D32F2F",
    )

    eligible = plot_frame[plot_frame["coverage_percent"] >= 90].sort_values("mfc_count")
    if not eligible.empty:
        first = eligible.iloc[0]
        annotate_point(
            ax,
            first["mfc_count"],
            first["coverage_percent"],
            f"Minimum tested p={int(first['mfc_count'])}",
        )

    ax.set_title("Thirty-Minute Service Coverage Curve", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Coverage uses 20 km/h default speed, 30-minute SLA, and 1.35 detour factor",
        transform=ax.transAxes,
        ha="left",
        fontsize=11,
    )
    ax.set_xlabel("Number of MFCs")
    ax.set_ylabel("Covered proxy demand, percent")
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)

    save_figure(
        fig,
        output_dir / "service_coverage_curve.png",
        output_dir / "service_coverage_curve.pdf",
    )
    plt.close(fig)


def plot_emission_pathway(emissions: pd.DataFrame, output_dir: Path) -> None:
    """Plot emission reduction by MFC count and EV adoption."""
    set_publication_theme()
    fig, ax = plt.subplots(figsize=(10, 6))

    emissions = emissions.copy()
    emissions["ev_adoption_label"] = emissions["ev_adoption_percent"].astype(int).astype(str) + "% EV"

    sns.lineplot(
        data=emissions,
        x="mfc_count",
        y="emission_reduction_percent",
        hue="ev_adoption_label",
        marker="o",
        linewidth=2.2,
        ax=ax,
        palette="viridis",
    )

    ax.axhline(30, color="#333333", linestyle="--", linewidth=1)
    ax.text(
        emissions["mfc_count"].min(),
        30.8,
        "H3 benchmark: 30% CO2e reduction",
        fontsize=8,
        color="#333333",
    )

    best = emissions.sort_values("emission_reduction_percent", ascending=False).iloc[0]
    annotate_point(
        ax,
        best["mfc_count"],
        best["emission_reduction_percent"],
        f"Max: {best['emission_reduction_percent']:.1f}%",
    )

    ax.set_title("CO2e Reduction Pathway for Quick-Commerce Last-Mile Delivery", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Scenario emissions per 100,000 proxy deliveries, relative to centralized ICE motorcycle baseline",
        transform=ax.transAxes,
        ha="left",
        fontsize=11,
    )
    ax.set_xlabel("Number of MFCs")
    ax.set_ylabel("Emission reduction, percent")
    ax.grid(True, alpha=0.3)
    ax.legend(title="EV adoption", frameon=True)

    save_figure(
        fig,
        output_dir / "emission_scenario_pathway.png",
        output_dir / "emission_scenario_pathway.pdf",
    )
    plt.close(fig)


def plot_top_underserved(admin_summary: pd.DataFrame, output_dir: Path) -> None:
    """Plot top underserved administrative units."""
    set_publication_theme()
    fig, ax = plt.subplots(figsize=(10, 6))

    frame = admin_summary.copy()
    frame["admin_unit"] = frame["NAME_2"].astype(str)
    frame = frame.sort_values("mean_underserved_score", ascending=False).head(10)

    sns.barplot(
        data=frame,
        x="mean_underserved_score",
        y="admin_unit",
        color="#D32F2F",
        ax=ax,
    )

    for idx, row in frame.reset_index(drop=True).iterrows():
        if idx < 3:
            ax.text(
                row["mean_underserved_score"],
                idx,
                f"  Top {idx + 1}",
                va="center",
                fontsize=8,
                color="black",
            )

    ax.set_title("Administrative Units with Highest Mean Underserved Score", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Underserved score combines demand proxy and lack of 30-minute MFC coverage",
        transform=ax.transAxes,
        ha="left",
        fontsize=11,
    )
    ax.set_xlabel("Mean underserved score")
    ax.set_ylabel("")
    ax.grid(True, axis="x", alpha=0.3)

    save_figure(
        fig,
        output_dir / "top_underserved_admin_units.png",
        output_dir / "top_underserved_admin_units.pdf",
    )
    plt.close(fig)


def plot_viirs_trend(trend: pd.DataFrame, output_dir: Path) -> None:
    """Plot VIIRS nighttime lights temporal trend."""
    set_publication_theme()
    fig, ax = plt.subplots(figsize=(10, 6))

    sns.lineplot(
        data=trend,
        x="year",
        y="mean_viirs_avg_rad",
        marker="o",
        linewidth=2.4,
        color="#54278F",
        ax=ax,
    )

    clean = trend.dropna(subset=["mean_viirs_avg_rad"]).copy()
    if len(clean) >= 3:
        slope = float(clean["sen_slope_avg_rad_per_year"].iloc[0])
        p_value = float(clean["kendall_p_value"].iloc[0])
        ax.text(
            0.02,
            0.92,
            f"Sen's slope: {slope:.3f} avg_rad/year\nKendall p-value: {p_value:.3f}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8},
        )

    ax.set_title("Nighttime Economic Activity Proxy Trend", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Greater Jakarta AOI annual mean VIIRS nighttime lights, 2020 to 2024",
        transform=ax.transAxes,
        ha="left",
        fontsize=11,
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("Mean VIIRS avg_rad")
    ax.grid(True, alpha=0.3)

    save_figure(
        fig,
        output_dir / "viirs_nighttime_lights_temporal_trend.png",
        output_dir / "viirs_nighttime_lights_temporal_trend.pdf",
    )
    plt.close(fig)


def plot_demand_concentration(clusters_path: Path, output_dir: Path) -> None:
    """Plot demand concentration curve from processed grid."""
    import geopandas as gpd

    grid = gpd.read_file(clusters_path, layer="demand_clusters")
    frame = grid[["demand_index", "area_m2"]].copy()
    frame = frame.sort_values("demand_index", ascending=False)
    frame["cumulative_demand_share"] = frame["demand_index"].cumsum() / frame["demand_index"].sum()
    frame["cumulative_area_share"] = frame["area_m2"].cumsum() / frame["area_m2"].sum()

    threshold_positions = np.where(frame["cumulative_demand_share"].to_numpy() >= 0.70)[0]
    if len(threshold_positions) == 0:
        area_share_percent = 100.0
    else:
        cutoff_position = int(threshold_positions[0])
        area_share_percent = float(frame.iloc[cutoff_position]["cumulative_area_share"] * 100.0)

    set_publication_theme()
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        frame["cumulative_area_share"] * 100.0,
        frame["cumulative_demand_share"] * 100.0,
        color="#D32F2F",
        linewidth=2.4,
    )
    ax.plot([0, 100], [0, 100], color="#777777", linestyle="--", linewidth=1)

    ax.axhline(70, color="#333333", linestyle=":", linewidth=1)
    ax.axvline(area_share_percent, color="#333333", linestyle=":", linewidth=1)
    ax.text(
        area_share_percent + 1,
        70,
        f"70% demand proxy within {area_share_percent:.1f}% of grid area",
        fontsize=8,
        va="bottom",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8},
    )

    ax.set_title("Spatial Concentration of Quick-Commerce Demand Proxy", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Cells sorted by demand index, cumulative demand share versus cumulative area share",
        transform=ax.transAxes,
        ha="left",
        fontsize=11,
    )
    ax.set_xlabel("Cumulative grid area, percent")
    ax.set_ylabel("Cumulative demand proxy, percent")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    save_figure(
        fig,
        output_dir / "demand_concentration_curve.png",
        output_dir / "demand_concentration_curve.pdf",
    )
    plt.close(fig)



def plot_validation_correlation(admin_summary: pd.DataFrame, output_dir: Path) -> None:
    """Plot validation cross-check scatter between population proxy and demand proxy."""
    set_publication_theme()
    fig, ax = plt.subplots(figsize=(10, 6))

    sns.regplot(
        data=admin_summary,
        x="total_population_proxy",
        y="total_demand_index",
        scatter_kws={"s": 55, "alpha": 0.85, "color": "#2C7FB8"},
        line_kws={"color": "#D32F2F", "linewidth": 2},
        ax=ax,
    )

    clean = admin_summary[["total_population_proxy", "total_demand_index"]].dropna()
    if len(clean) >= 3:
        r_value, p_value = stats.pearsonr(clean["total_population_proxy"], clean["total_demand_index"])
        ax.text(
            0.02,
            0.92,
            f"Pearson r: {r_value:.2f}\np-value: {p_value:.3f}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8},
        )

    ax.set_title("Validation Cross-Check: Population Proxy versus Demand Index", loc="left", pad=18)
    ax.text(
        0,
        1.01,
        "Administrative aggregation checks whether demand proxy remains plausible at city and regency scale",
        transform=ax.transAxes,
        ha="left",
        fontsize=11,
    )
    ax.set_xlabel("Total population proxy")
    ax.set_ylabel("Total demand index")
    ax.grid(True, alpha=0.3)

    save_figure(
        fig,
        output_dir / "validation_population_vs_demand_scatter.png",
        output_dir / "validation_population_vs_demand_scatter.pdf",
    )
    plt.close(fig)


def build_portfolio_contact_sheet(chart_dir: Path, map_dir: Path, output_path: Path) -> None:
    """Build a simple contact sheet for portfolio visual review using imageio."""
    image_paths = [
        map_dir / "quick_commerce_demand_index_compact.png",
        map_dir / "optimized_mfc_network_compact.png",
        chart_dir / "emission_scenario_pathway.png",
        chart_dir / "service_coverage_curve.png",
    ]
    available = [path for path in image_paths if path.exists()]
    if not available:
        return

    images = []
    for path in available:
        img = imageio.imread(path)
        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        images.append(img[:, :, :3])

    min_height = min(image.shape[0] for image in images)
    resized = []
    for image in images:
        scale = min_height / image.shape[0]
        new_width = max(1, int(image.shape[1] * scale))
        x_idx = np.linspace(0, image.shape[1] - 1, new_width).astype(int)
        y_idx = np.linspace(0, image.shape[0] - 1, min_height).astype(int)
        resized.append(image[np.ix_(y_idx, x_idx)])

    contact = np.concatenate(resized, axis=1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    imageio.imwrite(output_path, contact)


def main() -> None:
    """Generate analytical charts."""
    settings = get_settings()
    logger = get_logger("17_generate_charts")

    output_dir = settings.charts_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = require_file(settings.tables_dir / "optimized_network_summary.csv")
    emissions_path = require_file(settings.tables_dir / "emission_scenarios.csv")
    admin_summary_path = require_file(settings.tables_dir / "admin_unit_demand_summary.csv")
    trend_path = require_file(settings.tables_dir / "viirs_temporal_trend.csv")
    #demand_summary_path = require_file(settings.tables_dir / "demand_grid_summary.csv")
    clusters_path = require_file(settings.processed_dir / "demand_clusters.gpkg")

    summary = pd.read_csv(summary_path)
    emissions = pd.read_csv(emissions_path)
    admin_summary = pd.read_csv(admin_summary_path)
    trend = pd.read_csv(trend_path)

    chart_jobs = [
        ("distance_reduction", lambda: plot_distance_reduction(summary, output_dir)),
        ("service_coverage", lambda: plot_service_coverage(summary, output_dir)),
        ("emission_pathway", lambda: plot_emission_pathway(emissions, output_dir)),
        ("top_underserved", lambda: plot_top_underserved(admin_summary, output_dir)),
        ("viirs_trend", lambda: plot_viirs_trend(trend, output_dir)),
        ("demand_concentration", lambda: plot_demand_concentration(clusters_path, output_dir)),
        ("validation_scatter", lambda: plot_validation_correlation(admin_summary, output_dir)),
    ]

    for name, job in tqdm(chart_jobs, desc="Generating charts"):
        logger.info(f"Generating chart: {name}")
        job()

    build_portfolio_contact_sheet(
        chart_dir=output_dir,
        map_dir=settings.maps_dir,
        output_path=output_dir / "portfolio_visual_contact_sheet.png",
    )

    logger.info("Chart generation completed.")
    print(f"Charts completed in: {output_dir}")


if __name__ == "__main__":
    main()
