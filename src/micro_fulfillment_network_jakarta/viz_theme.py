from __future__ import annotations

from pathlib import Path

import contextily as cx
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch
from pyproj import CRS


ALLOWED_SEQUENTIAL_CMAPS = ["viridis", "magma", "cividis", "YlOrRd", "YlGnBu"]
ALLOWED_DIVERGING_CMAPS = ["RdBu_r", "BrBG", "PuOr"]
ALLOWED_CATEGORICAL_CMAPS = ["tab10", "Set2"]
BANNED_CMAPS = ["jet", "rainbow", "hsv", "hot", "gist_rainbow", "prism"]

BOUNDARY_COLOR = "#15171a"
HIGHLIGHT_COLOR = "#b63a1c"
ANNOTATION_COLOR = "#000000"
BASEMAP_SOURCE = "Esri World Gray Canvas"


PORTFOLIO_INK = "#15171a"
PORTFOLIO_ACCENT = "#b63a1c"
PORTFOLIO_PALETTE = ["#b63a1c", "#15171a", "#8c877c", "#d98c6c", "#3f6f73", "#c9a227"]


def set_publication_theme() -> None:
    """Apply the figure style shared with the portfolio site: warm neutrals, one rust accent."""
    sns.set_theme(style="white", palette=PORTFOLIO_PALETTE)
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
            "text.color": PORTFOLIO_INK,
            "axes.titlesize": 12,
            "axes.titleweight": "semibold",
            "axes.titlelocation": "left",
            "axes.titlecolor": PORTFOLIO_INK,
            "axes.labelsize": 10,
            "axes.labelcolor": "#474b50",
            "axes.edgecolor": "#bcb7ab",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "grid.color": "#e2ded3",
            "legend.fontsize": 9,
            "legend.frameon": False,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "xtick.color": "#6f7378",
            "ytick.color": "#6f7378",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def validate_colormap(cmap: str) -> None:
    """Reject banned colormaps and allow approved high-contrast schemes."""
    if cmap in BANNED_CMAPS:
        raise ValueError(f"Colormap is banned for perceptual reasons: {cmap}")


def add_basemap(ax: Axes, crs: str) -> None:
    """Add a neutral gray basemap under the data. CARTO tiles now need an API key."""
    cx.add_basemap(ax, crs=crs, source=cx.providers.Esri.WorldGrayCanvas, attribution=False, zorder=0)


def add_north_arrow(ax: Axes, x: float = 0.94, y: float = 0.18) -> None:
    """Add a simple north arrow in axis coordinates."""
    arrow = FancyArrowPatch(
        (x, y - 0.08),
        (x, y),
        transform=ax.transAxes,
        arrowstyle="-|>",
        mutation_scale=16,
        linewidth=1.2,
        color="black",
    )
    ax.add_patch(arrow)
    ax.text(
        x,
        y + 0.015,
        "N",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
        color="black",
    )


def add_scale_bar(ax: Axes, length_km: float = 10.0, location: tuple[float, float] = (0.08, 0.08)) -> None:
    """Add a simple scale bar for projected CRS maps."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    x_start = xlim[0] + (xlim[1] - xlim[0]) * location[0]
    y_start = ylim[0] + (ylim[1] - ylim[0]) * location[1]
    length_m = length_km * 1000.0

    ax.plot([x_start, x_start + length_m], [y_start, y_start], color="black", linewidth=3)
    ax.text(
        x_start + length_m / 2,
        y_start + (ylim[1] - ylim[0]) * 0.015,
        f"{length_km:g} km",
        ha="center",
        va="bottom",
        fontsize=8,
        color="black",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8},
    )


def add_source_note(ax: Axes, source: str) -> None:
    """Add source attribution without generation timestamp."""
    note = f"Source: {source}. Basemap: {BASEMAP_SOURCE}."
    ax.text(
        0.01,
        0.01,
        note,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7,
        style="italic",
        color="black",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75},
    )


def save_figure(fig, output_png: Path, output_pdf: Path | None = None) -> None:
    """Save a figure as PNG only and remove any stale PDF counterpart."""
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, bbox_inches="tight", dpi=300)

    if output_pdf is not None and output_pdf.exists():
        output_pdf.unlink()


def describe_crs(crs_value: str) -> str:
    """Return a human-readable CRS name."""
    crs = CRS.from_user_input(crs_value)
    return crs.name


