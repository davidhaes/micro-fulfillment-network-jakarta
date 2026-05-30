from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import mapclassify
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from micro_fulfillment_network_jakarta.viz_theme import (
    BOUNDARY_COLOR,
    HIGHLIGHT_COLOR,
    add_basemap,
    add_north_arrow,
    add_scale_bar,
    add_source_note,
    save_figure,
    set_publication_theme,
    validate_colormap,
)


def plot_choropleth_map(
    gdf: gpd.GeoDataFrame,
    value_column: str,
    title: str,
    subtitle: str,
    source: str,
    output_png: Path,
    output_pdf: Path,
    cmap: str = "viridis",
    scheme: str = "Quantiles",
    k: int = 5,
) -> None:
    """Plot a publication-grade choropleth map."""
    validate_colormap(cmap)
    set_publication_theme()

    plot_gdf = gdf.copy()
    if plot_gdf.crs is None:
        raise ValueError("GeoDataFrame CRS is required for mapping.")

    fig, ax = plt.subplots(figsize=(11.69, 8.27))

    if scheme.lower() == "quantiles":
        classifier = mapclassify.Quantiles(plot_gdf[value_column].fillna(0), k=k)
    elif scheme.lower() == "naturalbreaks":
        classifier = mapclassify.NaturalBreaks(plot_gdf[value_column].fillna(0), k=k)
    else:
        classifier = None

    plot_gdf.plot(
        column=value_column,
        ax=ax,
        cmap=cmap,
        scheme=scheme if classifier is not None else None,
        k=k,
        legend=True,
        alpha=0.85,
        edgecolor=BOUNDARY_COLOR,
        linewidth=0.2,
    )

    add_basemap(ax, crs=plot_gdf.crs.to_string())
    add_north_arrow(ax)
    add_scale_bar(ax, length_km=10)
    add_source_note(ax, source)

    ax.set_title(title, loc="left", pad=20)
    ax.text(0.0, 1.01, subtitle, transform=ax.transAxes, ha="left", va="bottom", fontsize=11)
    ax.set_axis_off()

    save_figure(fig, output_png, output_pdf)
    plt.close(fig)


def plot_points_over_polygon(
    boundary: gpd.GeoDataFrame,
    points: gpd.GeoDataFrame,
    title: str,
    subtitle: str,
    source: str,
    output_png: Path,
    output_pdf: Path,
) -> None:
    """Plot point facilities over a polygon boundary."""
    set_publication_theme()

    if boundary.crs != points.crs:
        points = points.to_crs(boundary.crs)

    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    boundary.plot(ax=ax, facecolor="none", edgecolor=BOUNDARY_COLOR, linewidth=0.8)
    points.plot(ax=ax, color=HIGHLIGHT_COLOR, markersize=35, edgecolor="white", linewidth=0.7)

    add_basemap(ax, crs=boundary.crs.to_string())
    add_north_arrow(ax)
    add_scale_bar(ax, length_km=10)
    add_source_note(ax, source)

    ax.set_title(title, loc="left", pad=20)
    ax.text(0.0, 1.01, subtitle, transform=ax.transAxes, ha="left", va="bottom", fontsize=11)
    ax.set_axis_off()

    save_figure(fig, output_png, output_pdf)
    plt.close(fig)


def plot_line_chart(
    frame: pd.DataFrame,
    x: str,
    y: str,
    hue: str | None,
    title: str,
    subtitle: str,
    y_label: str,
    output_png: Path,
    output_pdf: Path,
) -> None:
    """Plot a publication-grade line chart."""
    set_publication_theme()

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(data=frame, x=x, y=y, hue=hue, marker="o", linewidth=2.2, ax=ax)

    ax.set_title(title, loc="left", pad=18)
    ax.text(0.0, 1.01, subtitle, transform=ax.transAxes, ha="left", va="bottom", fontsize=11)
    ax.set_xlabel(x.replace("_", " ").title())
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.3)

    save_figure(fig, output_png, output_pdf)
    plt.close(fig)


def plot_bar_ranking(
    frame: pd.DataFrame,
    category: str,
    value: str,
    title: str,
    subtitle: str,
    y_label: str,
    output_png: Path,
    output_pdf: Path,
    top_n: int = 10,
) -> None:
    """Plot a horizontal bar ranking chart."""
    set_publication_theme()

    plot_frame = frame.sort_values(value, ascending=False).head(top_n).copy()
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=plot_frame, x=value, y=category, color="#2C7FB8", ax=ax)

    ax.set_title(title, loc="left", pad=18)
    ax.text(0.0, 1.01, subtitle, transform=ax.transAxes, ha="left", va="bottom", fontsize=11)
    ax.set_xlabel(y_label)
    ax.set_ylabel("")
    ax.grid(True, axis="x", alpha=0.3)

    save_figure(fig, output_png, output_pdf)
    plt.close(fig)
