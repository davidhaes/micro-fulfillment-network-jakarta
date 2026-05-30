from __future__ import annotations

import math
import sys
import textwrap
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch
from shapely import make_valid
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.viz_theme import (
    add_basemap,
    add_north_arrow,
    add_scale_bar,
    add_source_note,
    save_figure,
    set_publication_theme,
    validate_colormap,
)
from micro_fulfillment_network_jakarta.validators import require_file, validate_geodataframe


DEMAND_CMAP = "YlOrRd"
PRIORITY_CMAP = "YlOrRd"

MFC_COLOR = "#C62828"
MFC_EDGE_COLOR = "#FFFFFF"

ADMIN_BOUNDARY_COLOR = "#333333"
ADMIN_FILL = "#DCEEFF"

COVERED_COLOR = "#2E7D32"
UNCOVERED_COLOR = "#FDD49E"

LISA_COLORS = {
    "High-High": "#B2182B",
    "High-Low": "#EF8A62",
    "Low-High": "#67A9CF",
    "Low-Low": "#2166AC",
    "Not significant": "#E0E0E0",
    "Not evaluated": "#F5F5F5",
}

CLUSTER_COLORS = {
    "High-demand underserved priority": "#B2182B",
    "High-demand accessible core": "#1B9E77",
    "Lower-demand peripheral": "#6A51A3",
    "Mixed urban opportunity": "#E6AB02",
    "Unclassified": "#BDBDBD",
}


def repair_geometry(geometry):
    """Repair invalid geometry for visualization using make_valid with buffer fallback."""
    if geometry is None:
        return geometry
    if geometry.is_empty:
        return geometry
    if geometry.is_valid:
        return geometry

    try:
        repaired = make_valid(geometry)
        if repaired is not None and not repaired.is_empty and repaired.is_valid:
            return repaired
    except Exception:
        pass

    try:
        repaired = geometry.buffer(0)
        if repaired is not None and not repaired.is_empty:
            return repaired
    except Exception:
        pass

    return geometry


def repair_geodataframe_for_plotting(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Repair invalid geometries before validation and plotting."""
    output = gdf.copy()
    output["geometry"] = output.geometry.apply(repair_geometry)
    output = output[output.geometry.notna() & ~output.geometry.is_empty].copy()
    return output


def choose_reference_mfc_count(summary: pd.DataFrame) -> int:
    """Choose the smallest MFC count reaching 90 percent coverage, otherwise best available coverage."""
    eligible = summary[summary["coverage_share"] >= 0.90].sort_values("mfc_count")
    if not eligible.empty:
        return int(eligible.iloc[0]["mfc_count"])

    fallback = summary.sort_values(["coverage_share", "mfc_count"], ascending=[False, True]).iloc[0]
    return int(fallback["mfc_count"])


def compact_admin_name(value: object) -> str:
    """Convert administrative names to compact lowercase keys."""
    text = "" if pd.isna(value) else str(value)
    text = text.replace(" ", "").replace("-", "").replace("_", "")
    return text.lower()


def pretty_admin_label(value: object) -> str:
    """Create compact multi-line administrative labels from GADM names."""
    text = "" if pd.isna(value) else str(value)

    replacements = {
        "KotaTangerang": "Kota\nTangerang",
        "TangerangSelatan": "Tangerang\nSelatan",
        "KotaBekasi": "Kota\nBekasi",
        "KotaBogor": "Kota\nBogor",
        "JakartaBarat": "Jakarta\nBarat",
        "JakartaPusat": "Jakarta\nPusat",
        "JakartaSelatan": "Jakarta\nSelatan",
        "JakartaTimur": "Jakarta\nTimur",
        "JakartaUtara": "Jakarta\nUtara",
    }

    if text in replacements:
        return replacements[text]

    output = ""
    for index, char in enumerate(text):
        if index > 0 and char.isupper() and text[index - 1].islower():
            output += " "
        output += char

    words = output.strip().split()
    if len(words) == 2:
        return f"{words[0]}\n{words[1]}"
    if len(words) == 3:
        return f"{words[0]}\n{' '.join(words[1:])}"

    return output.strip()


def label_font_size(name: object) -> float:
    """Use small but readable font size for dense metropolitan labels."""
    key = compact_admin_name(name)

    if key.startswith("jakarta"):
        return 5.1
    if key in {"kotabogor", "kotabekasi", "kotatangerang", "tangerangselatan"}:
        return 5.2
    if key in {"depok", "kotabogor"}:
        return 5.3
    return 5.5


def candidate_label_offsets_px() -> list[tuple[float, float]]:
    """Generate compact pixel offsets for automatic label collision avoidance."""
    offsets: list[tuple[float, float]] = [(0.0, 0.0)]

    for radius in [7, 12, 18, 25, 34, 45, 58]:
        for angle in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            offsets.append((radius * math.cos(angle), radius * math.sin(angle)))

    return offsets


def set_map_extent(ax, admin: gpd.GeoDataFrame, pad_ratio: float = 0.045) -> None:
    """Set consistent map extent with padding."""
    minx, miny, maxx, maxy = admin.total_bounds
    dx = maxx - minx
    dy = maxy - miny
    ax.set_xlim(minx - dx * pad_ratio, maxx + dx * pad_ratio)
    ax.set_ylim(miny - dy * pad_ratio, maxy + dy * pad_ratio)


def add_admin_labels(ax, admin: gpd.GeoDataFrame) -> None:
    """Add all administrative labels near representative points with automatic collision reduction."""
    fig = ax.figure
    labels = []

    admin_for_labels = admin.copy()
    admin_for_labels["plot_area"] = admin_for_labels.geometry.area
    admin_for_labels = admin_for_labels.sort_values("plot_area", ascending=False)

    for _, row in admin_for_labels.iterrows():
        name = row.get("NAME_2", "")
        point = row.geometry.representative_point()

        text = ax.text(
            point.x,
            point.y,
            pretty_admin_label(name),
            fontsize=label_font_size(name),
            ha="center",
            va="center",
            linespacing=0.88,
            color="#111111",
            zorder=80,
            bbox={
                "facecolor": (1.0, 1.0, 1.0, 0.72),
                "edgecolor": "none",
                "boxstyle": "round,pad=0.09",
            },
            path_effects=[pe.withStroke(linewidth=1.8, foreground="white")],
        )
        labels.append((text, point.x, point.y))

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    placed_bboxes = []
    offsets = candidate_label_offsets_px()

    for text, original_x, original_y in labels:
        original_display = ax.transData.transform((original_x, original_y))
        chosen_bbox = None

        for dx, dy in offsets:
            candidate_display = original_display + np.array([dx, dy])
            candidate_data = ax.transData.inverted().transform(candidate_display)

            text.set_position((candidate_data[0], candidate_data[1]))
            fig.canvas.draw()

            bbox = text.get_window_extent(renderer=renderer).expanded(1.03, 1.08)
            has_overlap = any(bbox.overlaps(existing) for existing in placed_bboxes)

            if not has_overlap:
                chosen_bbox = bbox
                break

        if chosen_bbox is None:
            text.set_fontsize(max(4.4, text.get_fontsize() - 0.8))
            text.set_position((original_x, original_y))
            fig.canvas.draw()
            chosen_bbox = text.get_window_extent(renderer=renderer).expanded(1.02, 1.06)

        placed_bboxes.append(chosen_bbox)


def create_map_figure(title: str, subtitle: str, figsize: tuple[float, float] = (16.0, 9.0)):
    """Create a clean 16:9 map figure with improved title spacing."""
    set_publication_theme()

    fig, ax = plt.subplots(figsize=figsize)
    fig.subplots_adjust(left=0.035, right=0.985, top=0.875, bottom=0.060)

    ax.set_title(title, loc="left", pad=32, fontsize=15.5, fontweight="bold")
    ax.text(
        0.0,
        1.020,
        subtitle,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10.7,
        color="#222222",
    )

    return fig, ax


def wrap_label(text: str, width: int = 28) -> str:
    """Wrap legend labels."""
    return "\n".join(textwrap.wrap(str(text), width=width))


def format_tick(value: float) -> str:
    """Format colorbar ticks without crowding."""
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def add_floating_card(ax, x: float, y: float, width: float, height: float) -> None:
    """Add a semi-transparent white legend card behind solid legend content."""
    card = FancyBboxPatch(
        (x, y),
        width,
        height,
        transform=ax.transAxes,
        boxstyle="round,pad=0.012,rounding_size=0.012",
        facecolor=(1.0, 1.0, 1.0, 0.90),
        edgecolor=(0.55, 0.55, 0.55, 1.0),
        linewidth=0.9,
        zorder=60,
    )
    ax.add_patch(card)


def add_discrete_legend_card(
    ax,
    title: str,
    handles: list,
    x: float = 0.700,
    y: float = 0.050,
    width: float = 0.280,
    height: float = 0.220,
    ncol: int = 1,
) -> None:
    """Add compact floating discrete legend with solid text and symbols in one column."""
    add_floating_card(ax, x, y, width, height)

    ax.text(
        x + 0.014,
        y + height - 0.030,
        title,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.0,
        fontweight="bold",
        color="#111111",
        zorder=120,
    )

    wrapped_handles = []
    for handle in handles:
        handle.set_label(wrap_label(handle.get_label(), width=28))
        wrapped_handles.append(handle)

    legend = ax.legend(
        handles=wrapped_handles,
        loc="upper left",
        bbox_to_anchor=(x + 0.012, y + height - 0.058),
        bbox_transform=ax.transAxes,
        frameon=False,
        fontsize=8.8,
        ncol=1,
        labelspacing=0.48,
        handlelength=1.25,
        handletextpad=0.50,
        borderaxespad=0.0,
        columnspacing=0.85,
    )
    legend.set_zorder(130)

    for text in legend.get_texts():
        text.set_color("#111111")

    for legend_handle in legend.legend_handles:
        try:
            legend_handle.set_alpha(1.0)
        except Exception:
            pass


def add_continuous_legend_card(
    fig,
    ax,
    title: str,
    cmap: str,
    vmin: float,
    vmax: float,
    x: float = 0.735,
    y: float = 0.055,
    width: float = 0.245,
    height: float = 0.145,
) -> None:
    """Add compact floating continuous legend with clear numeric tick values."""
    add_floating_card(ax, x, y, width, height)

    ax.text(
        x + 0.014,
        y + height - 0.030,
        title,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.0,
        fontweight="bold",
        color="#111111",
        zorder=120,
    )

    cax = ax.inset_axes(
        [x + 0.020, y + 0.050, width - 0.040, 0.032],
        transform=ax.transAxes,
    )
    cax.set_zorder(125)

    norm = Normalize(vmin=vmin, vmax=vmax)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])

    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    midpoint = (vmin + vmax) / 2.0
    cbar.set_ticks([vmin, midpoint, vmax])
    cbar.set_ticklabels([format_tick(vmin), format_tick(midpoint), format_tick(vmax)])
    cbar.ax.tick_params(labelsize=8.8, pad=2, colors="#111111")
    cbar.outline.set_linewidth(0.7)

    for label in cbar.ax.get_xticklabels():
        label.set_color("#111111")
        label.set_alpha(1.0)


def add_combined_continuous_symbol_card(
    fig,
    ax,
    title: str,
    cmap: str,
    vmin: float,
    vmax: float,
    symbol_handles: list,
    x: float = 0.705,
    y: float = 0.045,
    width: float = 0.275,
    height: float = 0.245,
) -> None:
    """Add compact card with clear continuous colorbar and one-column symbol legend."""
    add_floating_card(ax, x, y, width, height)

    ax.text(
        x + 0.014,
        y + height - 0.028,
        title,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.0,
        fontweight="bold",
        color="#111111",
        zorder=120,
    )

    cax = ax.inset_axes(
        [x + 0.020, y + height - 0.086, width - 0.040, 0.032],
        transform=ax.transAxes,
    )
    cax.set_zorder(125)

    norm = Normalize(vmin=vmin, vmax=vmax)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")

    midpoint = (vmin + vmax) / 2.0
    cbar.set_ticks([vmin, midpoint, vmax])
    cbar.set_ticklabels([format_tick(vmin), format_tick(midpoint), format_tick(vmax)])
    cbar.ax.tick_params(labelsize=8.4, pad=2, colors="#111111")
    cbar.outline.set_linewidth(0.7)

    for label in cbar.ax.get_xticklabels():
        label.set_color("#111111")
        label.set_alpha(1.0)

    wrapped_handles = []
    for handle in symbol_handles:
        handle.set_label(wrap_label(handle.get_label(), width=27))
        wrapped_handles.append(handle)

    legend = ax.legend(
        handles=wrapped_handles,
        loc="upper left",
        bbox_to_anchor=(x + 0.012, y + height - 0.142),
        bbox_transform=ax.transAxes,
        frameon=False,
        fontsize=8.8,
        ncol=1,
        labelspacing=0.46,
        handlelength=1.30,
        handletextpad=0.55,
        borderaxespad=0.0,
    )
    legend.set_zorder(130)

    for text in legend.get_texts():
        text.set_color("#111111")

    for legend_handle in legend.legend_handles:
        try:
            legend_handle.set_alpha(1.0)
        except Exception:
            pass


def finalize_projected_map(ax, crs: str, source: str, scale_km: float = 10.0) -> None:
    """Add cartographic elements to a projected map."""
    try:
        add_basemap(ax, crs=crs)
    except Exception:
        pass

    add_north_arrow(ax, x=0.955, y=0.905)
    add_scale_bar(ax, length_km=scale_km)
    add_source_note(ax, source)
    ax.set_axis_off()


def plot_overview_map(aoi: gpd.GeoDataFrame, admin: gpd.GeoDataFrame, output_dir: Path) -> None:
    """Plot AOI overview map."""
    fig, ax = create_map_figure(
        title="Greater Jakarta Quick-Commerce Logistics Study Area",
        subtitle="Road-based metropolitan AOI from GADM 4.1 administrative units",
    )

    set_map_extent(ax, admin)
    admin.plot(ax=ax, facecolor=ADMIN_FILL, edgecolor=ADMIN_BOUNDARY_COLOR, linewidth=0.65, alpha=0.84, zorder=2)
    aoi.boundary.plot(ax=ax, color=MFC_COLOR, linewidth=1.8, zorder=6)
    add_admin_labels(ax, admin)

    handles = [
        Patch(facecolor=ADMIN_FILL, edgecolor=ADMIN_BOUNDARY_COLOR, label="Included city or regency"),
        Line2D([0], [0], color=MFC_COLOR, linewidth=1.8, label="Dissolved study-area boundary"),
    ]
    add_discrete_legend_card(ax, "Map legend", handles, x=0.730, y=0.045, width=0.250, height=0.155, ncol=1)

    finalize_projected_map(
        ax=ax,
        crs=admin.crs.to_string(),
        source="GADM 4.1, OpenStreetMap basemap",
        scale_km=20,
    )

    save_figure(fig, output_dir / "overview_aoi_map.png", None)
    plt.close(fig)


def plot_demand_index_map(grid: gpd.GeoDataFrame, admin: gpd.GeoDataFrame, output_dir: Path) -> None:
    """Plot demand index map."""
    validate_colormap(DEMAND_CMAP)

    fig, ax = create_map_figure(
        title="Quick-Commerce Demand Suitability",
        subtitle="Open-data latent demand proxy from population, nighttime lights, built-up intensity, road access, and POI density",
    )

    set_map_extent(ax, admin)

    vmin = float(grid["demand_index"].min())
    vmax = float(grid["demand_index"].max())

    grid.plot(
        column="demand_index",
        ax=ax,
        cmap=DEMAND_CMAP,
        vmin=vmin,
        vmax=vmax,
        alpha=0.88,
        linewidth=0,
        zorder=2,
    )
    admin.boundary.plot(ax=ax, color=ADMIN_BOUNDARY_COLOR, linewidth=0.55, zorder=5)

    top = grid.sort_values("demand_index", ascending=False).head(10)
    top.boundary.plot(ax=ax, color=MFC_COLOR, linewidth=1.1, zorder=6)

    add_admin_labels(ax, admin)

    symbol_handles = [
        Patch(facecolor="none", edgecolor=MFC_COLOR, linewidth=1.1, label="Top 10 demand grid cells"),
        Line2D([0], [0], color=ADMIN_BOUNDARY_COLOR, linewidth=0.65, label="Administrative boundary"),
    ]
    add_combined_continuous_symbol_card(
        fig,
        ax,
        "Demand index",
        DEMAND_CMAP,
        vmin,
        vmax,
        symbol_handles,
        x=0.705,
        y=0.045,
        width=0.275,
        height=0.220,
    )

    finalize_projected_map(
        ax=ax,
        crs=grid.crs.to_string(),
        source="WorldPop, VIIRS, Dynamic World, OpenStreetMap, GADM",
        scale_km=10,
    )

    save_figure(fig, output_dir / "quick_commerce_demand_index_map.png", None)
    plt.close(fig)

    fig_sq, ax_sq = create_map_figure(
        title="Quick-Commerce Demand Suitability",
        subtitle="Greater Jakarta, open-data latent demand proxy",
    )

    set_map_extent(ax_sq, admin)

    grid.plot(
        column="demand_index",
        ax=ax_sq,
        cmap=DEMAND_CMAP,
        vmin=vmin,
        vmax=vmax,
        alpha=0.88,
        linewidth=0,
        zorder=2,
    )
    admin.boundary.plot(ax=ax_sq, color=ADMIN_BOUNDARY_COLOR, linewidth=0.55, zorder=5)
    add_admin_labels(ax_sq, admin)
    add_continuous_legend_card(fig_sq, ax_sq, "Demand index", DEMAND_CMAP, vmin, vmax, x=0.735, y=0.055)

    finalize_projected_map(
        ax=ax_sq,
        crs=grid.crs.to_string(),
        source="WorldPop, VIIRS, Dynamic World, OSM",
        scale_km=10,
    )

    save_figure(fig_sq, output_dir / "quick_commerce_demand_index_public-facing portfolio_square.png", None)
    plt.close(fig_sq)


def plot_optimized_mfc_network(
    grid: gpd.GeoDataFrame,
    admin: gpd.GeoDataFrame,
    selected_mfc: gpd.GeoDataFrame,
    p_value: int,
    coverage_share: float,
    output_dir: Path,
) -> None:
    """Plot selected MFC network over demand background."""
    fig, ax = create_map_figure(
        title=f"Optimized Micro-Fulfillment Network, p={p_value}",
        subtitle=f"Demand-weighted p-median network, 30-minute modeled coverage={coverage_share:.1%}",
    )

    set_map_extent(ax, admin)

    vmin = float(grid["demand_index"].min())
    vmax = float(grid["demand_index"].max())

    grid.plot(
        column="demand_index",
        ax=ax,
        cmap=DEMAND_CMAP,
        vmin=vmin,
        vmax=vmax,
        alpha=0.58,
        linewidth=0,
        zorder=2,
    )

    admin.boundary.plot(ax=ax, color=ADMIN_BOUNDARY_COLOR, linewidth=0.55, zorder=5)

    selected_mfc.plot(
        ax=ax,
        color=MFC_COLOR,
        markersize=34,
        edgecolor=MFC_EDGE_COLOR,
        linewidth=0.8,
        zorder=10,
    )

    add_admin_labels(ax, admin)

    symbol_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="white",
            markerfacecolor=MFC_COLOR,
            markeredgecolor=MFC_EDGE_COLOR,
            markersize=7.5,
            linestyle="None",
            label="Selected Micro-Fulfillment Center",
        ),
        Line2D([0], [0], color=ADMIN_BOUNDARY_COLOR, linewidth=0.65, label="Administrative boundary"),
    ]

    add_combined_continuous_symbol_card(
        fig,
        ax,
        "Demand and network",
        DEMAND_CMAP,
        vmin,
        vmax,
        symbol_handles,
        x=0.705,
        y=0.045,
        width=0.275,
        height=0.225,
    )

    finalize_projected_map(
        ax=ax,
        crs=grid.crs.to_string(),
        source="Derived p-median optimization from open geospatial data",
        scale_km=10,
    )

    save_figure(fig, output_dir / "optimized_mfc_network_map.png", None)
    plt.close(fig)

    fig_sq, ax_sq = create_map_figure(
        title=f"Optimized Micro-Fulfillment Network, p={p_value}",
        subtitle=f"Demand-weighted p-median network, 30-minute modeled coverage={coverage_share:.1%}",
    )

    set_map_extent(ax_sq, admin)

    grid.plot(
        column="demand_index",
        ax=ax_sq,
        cmap=DEMAND_CMAP,
        vmin=vmin,
        vmax=vmax,
        alpha=0.58,
        linewidth=0,
        zorder=2,
    )

    admin.boundary.plot(ax=ax_sq, color=ADMIN_BOUNDARY_COLOR, linewidth=0.55, zorder=5)

    selected_mfc.plot(
        ax=ax_sq,
        color=MFC_COLOR,
        markersize=34,
        edgecolor=MFC_EDGE_COLOR,
        linewidth=0.8,
        zorder=10,
    )

    add_admin_labels(ax_sq, admin)

    add_combined_continuous_symbol_card(
        fig_sq,
        ax_sq,
        "Demand and network",
        DEMAND_CMAP,
        vmin,
        vmax,
        symbol_handles,
        x=0.705,
        y=0.045,
        width=0.275,
        height=0.225,
    )

    finalize_projected_map(
        ax=ax_sq,
        crs=grid.crs.to_string(),
        source="Open-data optimization output",
        scale_km=10,
    )

    save_figure(fig_sq, output_dir / "optimized_mfc_network_public-facing portfolio_square.png", None)
    plt.close(fig_sq)


def plot_service_coverage_map(
    coverage: gpd.GeoDataFrame,
    admin: gpd.GeoDataFrame,
    selected_mfc: gpd.GeoDataFrame,
    p_value: int,
    output_dir: Path,
) -> None:
    """Plot 30-minute service coverage map."""
    column = f"covered_30min_p{p_value}"

    fig, ax = create_map_figure(
        title=f"Thirty-Minute Service Coverage, p={p_value}",
        subtitle="Covered cells are within the modeled 30-minute route-distance threshold",
    )

    set_map_extent(ax, admin)

    covered = coverage[coverage[column].astype(bool)].copy()
    uncovered = coverage[~coverage[column].astype(bool)].copy()

    uncovered.plot(ax=ax, color=UNCOVERED_COLOR, edgecolor="none", alpha=0.90, zorder=2)
    covered.plot(ax=ax, color=COVERED_COLOR, edgecolor="none", alpha=0.82, zorder=3)

    admin.boundary.plot(ax=ax, color=ADMIN_BOUNDARY_COLOR, linewidth=0.55, zorder=5)

    selected_mfc.plot(
        ax=ax,
        color=MFC_COLOR,
        markersize=32,
        edgecolor=MFC_EDGE_COLOR,
        linewidth=0.75,
        zorder=10,
    )

    add_admin_labels(ax, admin)

    handles = [
        Patch(facecolor=COVERED_COLOR, edgecolor="none", label="Covered within 30 minutes"),
        Patch(facecolor=UNCOVERED_COLOR, edgecolor="none", label="Outside 30-minute threshold"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="white",
            markerfacecolor=MFC_COLOR,
            markeredgecolor=MFC_EDGE_COLOR,
            markersize=7.5,
            linestyle="None",
            label="Selected Micro-Fulfillment Center",
        ),
        Line2D([0], [0], color=ADMIN_BOUNDARY_COLOR, linewidth=0.65, label="Administrative boundary"),
    ]

    add_discrete_legend_card(ax, "Coverage legend", handles, x=0.700, y=0.045, width=0.280, height=0.245, ncol=1)

    finalize_projected_map(
        ax=ax,
        crs=coverage.crs.to_string(),
        source="Derived service coverage model, OSM-based accessibility proxy",
        scale_km=10,
    )

    save_figure(fig, output_dir / "thirty_minute_service_coverage_map.png", None)
    plt.close(fig)


def plot_lisa_hotspot_map(lisa: gpd.GeoDataFrame, admin: gpd.GeoDataFrame, output_dir: Path) -> None:
    """Plot LISA hotspot map for underserved score."""
    cluster_column = "underserved_score_lisa_cluster"
    categories = ["High-High", "High-Low", "Low-High", "Low-Low", "Not significant", "Not evaluated"]

    fig, ax = create_map_figure(
        title="Underserved Demand Hotspots",
        subtitle="Local Moran's I clusters for demand cells outside the 30-minute coverage threshold",
    )

    set_map_extent(ax, admin)

    for category in categories:
        subset = lisa[lisa[cluster_column] == category]
        if subset.empty:
            continue

        subset.plot(
            ax=ax,
            color=LISA_COLORS[category],
            edgecolor="none",
            alpha=0.88 if category == "High-High" else 0.74,
            zorder=4 if category == "High-High" else 2,
        )

    admin.boundary.plot(ax=ax, color=ADMIN_BOUNDARY_COLOR, linewidth=0.55, zorder=5)

    high_high = lisa[lisa[cluster_column] == "High-High"]
    if not high_high.empty:
        high_high.boundary.plot(ax=ax, color="#7F0000", linewidth=0.95, zorder=6)

    add_admin_labels(ax, admin)

    handles = [
        Patch(facecolor=LISA_COLORS["High-High"], edgecolor="none", label="High-High hotspot"),
        Patch(facecolor=LISA_COLORS["High-Low"], edgecolor="none", label="High-Low outlier"),
        Patch(facecolor=LISA_COLORS["Low-High"], edgecolor="none", label="Low-High outlier"),
        Patch(facecolor=LISA_COLORS["Low-Low"], edgecolor="none", label="Low-Low cluster"),
        Patch(facecolor=LISA_COLORS["Not significant"], edgecolor="none", label="Not significant"),
    ]

    add_discrete_legend_card(ax, "LISA legend", handles, x=0.700, y=0.045, width=0.280, height=0.300, ncol=1)

    finalize_projected_map(
        ax=ax,
        crs=lisa.crs.to_string(),
        source="Local Moran's I, 999 permutations, KNN k=8",
        scale_km=10,
    )

    save_figure(fig, output_dir / "underserved_hotspot_lisa_map.png", None)
    plt.close(fig)


def plot_emission_priority_map(
    coverage: gpd.GeoDataFrame,
    admin: gpd.GeoDataFrame,
    p_value: int,
    output_dir: Path,
) -> None:
    """Plot priority score for service and decarbonization intervention."""
    distance_column = f"nearest_mfc_distance_km_p{p_value}"
    output = coverage.copy()

    demand_scaled = output["demand_index"].fillna(0)
    distance_scaled = output[distance_column].fillna(0)

    if distance_scaled.max() > distance_scaled.min():
        distance_scaled = (distance_scaled - distance_scaled.min()) / (distance_scaled.max() - distance_scaled.min())
    else:
        distance_scaled = distance_scaled * 0

    output["decarbonization_priority_score"] = 0.65 * demand_scaled + 0.35 * distance_scaled
    output["decarbonization_priority_score"] = np.where(
        output[f"covered_30min_p{p_value}"].astype(bool),
        output["decarbonization_priority_score"] * 0.55,
        output["decarbonization_priority_score"],
    )

    fig, ax = create_map_figure(
        title="Decarbonization Priority Surface",
        subtitle="High demand and longer nearest-MFC distance define priority intervention areas",
    )

    set_map_extent(ax, admin)
    validate_colormap(PRIORITY_CMAP)

    vmin = float(output["decarbonization_priority_score"].min())
    vmax = float(output["decarbonization_priority_score"].max())

    output.plot(
        column="decarbonization_priority_score",
        ax=ax,
        cmap=PRIORITY_CMAP,
        vmin=vmin,
        vmax=vmax,
        alpha=0.88,
        linewidth=0,
        zorder=2,
    )

    admin.boundary.plot(ax=ax, color=ADMIN_BOUNDARY_COLOR, linewidth=0.55, zorder=5)

    top_priority = output.sort_values("decarbonization_priority_score", ascending=False).head(12)
    top_priority.boundary.plot(ax=ax, color="#000000", linewidth=1.25, zorder=8)

    add_admin_labels(ax, admin)

    symbol_handles = [
        Patch(facecolor="none", edgecolor="#000000", linewidth=1.25, label="Top 12 priority grid cells"),
        Line2D([0], [0], color=ADMIN_BOUNDARY_COLOR, linewidth=0.65, label="Administrative boundary"),
    ]

    add_combined_continuous_symbol_card(
        fig,
        ax,
        "Priority score",
        PRIORITY_CMAP,
        vmin,
        vmax,
        symbol_handles,
        x=0.705,
        y=0.045,
        width=0.275,
        height=0.245,
    )

    finalize_projected_map(
        ax=ax,
        crs=coverage.crs.to_string(),
        source="Demand index, nearest-MFC distance, and service coverage",
        scale_km=10,
    )

    save_figure(fig, output_dir / "emission_reduction_priority_map.png", None)
    plt.close(fig)


def plot_cluster_map(clusters: gpd.GeoDataFrame, admin: gpd.GeoDataFrame, output_dir: Path) -> None:
    """Plot operational demand cluster map."""
    plot_clusters = clusters.copy()
    plot_clusters["cluster_label"] = plot_clusters["cluster_label"].fillna("Unclassified")

    label_order = [
        "High-demand underserved priority",
        "High-demand accessible core",
        "Mixed urban opportunity",
        "Lower-demand peripheral",
        "Unclassified",
    ]

    labels = [label for label in label_order if label in set(plot_clusters["cluster_label"])]

    fig, ax = create_map_figure(
        title="Operational Demand Segments",
        subtitle="KMeans segmentation of demand, accessibility, POI density, built-up intensity, and underserved score",
    )

    set_map_extent(ax, admin)

    for label in labels:
        subset = plot_clusters[plot_clusters["cluster_label"] == label]
        subset.plot(
            ax=ax,
            color=CLUSTER_COLORS.get(label, "#BDBDBD"),
            edgecolor="none",
            alpha=0.86,
            zorder=2,
        )

    admin.boundary.plot(ax=ax, color=ADMIN_BOUNDARY_COLOR, linewidth=0.55, zorder=5)
    add_admin_labels(ax, admin)

    handles = [
        Patch(facecolor=CLUSTER_COLORS.get(label, "#BDBDBD"), edgecolor="none", label=label)
        for label in labels
    ]

    add_discrete_legend_card(ax, "Cluster legend", handles, x=0.700, y=0.045, width=0.280, height=0.270, ncol=1)

    finalize_projected_map(
        ax=ax,
        crs=clusters.crs.to_string(),
        source="KMeans clustering from demand and service coverage features",
        scale_km=10,
    )

    save_figure(fig, output_dir / "operational_demand_cluster_map.png", None)
    plt.close(fig)


def main() -> None:
    """Generate all static maps."""
    settings = get_settings()
    logger = get_logger("16_generate_static_maps")

    output_dir = settings.maps_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    admin_path = require_file(settings.raw_dir / "gadm_aoi" / "greater_jakarta_gadm_level2.geojson")
    aoi_path = require_file(settings.aoi_dir / "aoi_default.geojson")
    clusters_path = require_file(settings.processed_dir / "demand_clusters.gpkg")
    coverage_path = require_file(settings.processed_dir / "service_coverage.gpkg")
    selected_path = require_file(settings.processed_dir / "optimized_mfc_networks.gpkg")
    lisa_path = require_file(settings.processed_dir / "demand_underserved_lisa.gpkg")
    summary_path = require_file(settings.tables_dir / "optimized_network_summary.csv")

    admin = repair_geodataframe_for_plotting(gpd.read_file(admin_path).to_crs(settings.projected_crs))
    aoi = repair_geodataframe_for_plotting(gpd.read_file(aoi_path).to_crs(settings.projected_crs))
    clusters = repair_geodataframe_for_plotting(gpd.read_file(clusters_path, layer="demand_clusters").to_crs(settings.projected_crs))
    coverage = repair_geodataframe_for_plotting(gpd.read_file(coverage_path, layer="service_coverage").to_crs(settings.projected_crs))
    selected_all = repair_geodataframe_for_plotting(gpd.read_file(selected_path, layer="optimized_mfc_networks").to_crs(settings.projected_crs))
    lisa = repair_geodataframe_for_plotting(gpd.read_file(lisa_path, layer="lisa").to_crs(settings.projected_crs))
    summary = pd.read_csv(summary_path)

    validate_geodataframe(admin)
    validate_geodataframe(aoi)
    validate_geodataframe(clusters, required_columns=["demand_index", "cluster_label"])
    validate_geodataframe(coverage, required_columns=["demand_index", "underserved_score"])
    validate_geodataframe(selected_all, required_columns=["mfc_count", "selected_order"])
    validate_geodataframe(lisa)

    p_value = choose_reference_mfc_count(summary)
    coverage_share = float(summary.loc[summary["mfc_count"] == p_value, "coverage_share"].iloc[0])
    selected_mfc = selected_all[selected_all["mfc_count"] == p_value].copy()

    map_jobs = [
        ("overview", lambda: plot_overview_map(aoi, admin, output_dir)),
        ("demand", lambda: plot_demand_index_map(clusters, admin, output_dir)),
        ("optimized_mfc", lambda: plot_optimized_mfc_network(clusters, admin, selected_mfc, p_value, coverage_share, output_dir)),
        ("coverage", lambda: plot_service_coverage_map(coverage, admin, selected_mfc, p_value, output_dir)),
        ("lisa", lambda: plot_lisa_hotspot_map(lisa, admin, output_dir)),
        ("emission_priority", lambda: plot_emission_priority_map(coverage, admin, p_value, output_dir)),
        ("clusters", lambda: plot_cluster_map(clusters, admin, output_dir)),
    ]

    for name, job in tqdm(map_jobs, desc="Generating static maps"):
        logger.info(f"Generating static map: {name}")
        job()

    logger.info("Static map generation completed.")
    print(f"Static maps completed in: {output_dir}")


if __name__ == "__main__":
    main()
