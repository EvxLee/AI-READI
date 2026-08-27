"""Chart styling and reusable figure builders.

Every figure in both papers is drawn through this module, so a colour or an
axis convention is defined once. Notebooks compose charts from these pieces
and add interpretation; they do not restate the palette.

Two colour jobs appear in this project and they are not interchangeable:

* **Severity group is ORDERED** (Healthy -> Pre-DM -> Oral Med -> Insulin), so
  it gets a one-hue ordinal ramp, light -> dark. Giving severity four unrelated
  hues would throw away the ordering that is the whole point of the paper.
* **Organ is IDENTITY** (kidney / heart / nerve), so it gets categorical hues.

Both palettes were checked with the data-viz validator against the light chart
surface (#fcfcfb): the organ trio passes CVD and normal-vision separation on
all pairs, and the severity ramp passes monotone lightness with visible step
gaps. Aqua sits below 3:1 contrast, which is why every chart here carries
direct labels rather than relying on the legend alone.
"""

from __future__ import annotations

import textwrap
from typing import Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

__all__ = [
    "SEVERITY", "SEVERITY_ORDER", "ORGAN", "ORGAN_LABEL", "SURFACE", "INK",
    "INK_SECONDARY", "MUTED", "GRID", "BASELINE", "EMPHASIS", "DEEMPHASIS",
    "style", "new_figure", "grouped_bars", "stacked_bars", "forest", "finish",
]

# ── Palette ────────────────────────────────────────────────────────────────
# Ordinal ramp for severity: one hue, light -> dark, light end clears 2:1.
SEVERITY = ["#86b6ef", "#3987e5", "#256abf", "#104281"]
SEVERITY_ORDER = ["Healthy", "Pre-DM", "Oral Med", "Insulin"]

# Categorical slots 1-3 for organ identity.
ORGAN = {"kidney": "#2a78d6", "heart": "#eb6834", "nerve": "#1baf7a"}
ORGAN_LABEL = {"kidney": "Kidney", "heart": "Heart", "nerve": "Nerve",
               "any": "Any organ", "either": "Either organ"}

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
EMPHASIS = "#2a78d6"
DEEMPHASIS = "#c3c2b7"

_SANS = ["DejaVu Sans", "Helvetica Neue", "Helvetica", "Arial", "sans-serif"]


def style() -> None:
    """Apply the project chart style. Call once per notebook."""
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": _SANS,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "axes.titlepad": 10,
        "axes.labelsize": 10,
        "axes.labelcolor": INK_SECONDARY,
        "axes.edgecolor": BASELINE,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.labelcolor": INK_SECONDARY,
        "lines.linewidth": 2.0,
        "lines.markersize": 8,
    })


def new_figure(width: float = 9.0, height: float = 5.0, **kwargs):
    """A styled figure/axes pair with the horizontal-only grid charts want."""
    fig, ax = plt.subplots(figsize=(width, height), **kwargs)
    for a in np.atleast_1d(ax).ravel():
        a.grid(axis="x", visible=False)
    return fig, ax


def _label_bars(ax, rects, values, fmt: str, *, threshold: float | None = None) -> None:
    """Direct-label bars. Labels ride outside so a dark fill never hides them."""
    for rect, value in zip(rects, values):
        if value is None or (isinstance(value, float) and np.isnan(value)):
            continue
        if threshold is not None and value < threshold:
            continue
        ax.annotate(fmt.format(value),
                    xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8, color=INK_SECONDARY)


def grouped_bars(ax, categories: Sequence[str], series: dict[str, Sequence[float]],
                 colors: Sequence[str], *, fmt: str = "{:.1f}",
                 label_values: bool = True, gap: float = 0.02):
    """Grouped bars with a 2px-equivalent surface gap between fills.

    `series` maps legend label -> one value per category.
    """
    n = len(series)
    slot = (1 - 0.25) / n
    width = slot - gap
    x = np.arange(len(categories), dtype=float)

    for i, ((label, values), color) in enumerate(zip(series.items(), colors)):
        offset = (i - (n - 1) / 2) * slot
        rects = ax.bar(x + offset, values, width, label=label, color=color,
                       edgecolor=SURFACE, linewidth=0.8)
        if label_values:
            _label_bars(ax, rects, values, fmt)

    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    return ax


def stacked_bars(ax, categories: Sequence[str], series: dict[str, Sequence[float]],
                 colors: Sequence[str], *, fmt: str = "{:.0f}%",
                 min_label: float = 6.0):
    """Stacked part-to-whole bars, hairline-separated, labelled where they fit."""
    x = np.arange(len(categories), dtype=float)
    bottom = np.zeros(len(categories))

    for (label, values), color in zip(series.items(), colors):
        values = np.asarray(values, dtype=float)
        ax.bar(x, values, 0.62, bottom=bottom, label=label, color=color,
               edgecolor=SURFACE, linewidth=1.2)
        for xi, (v, b) in enumerate(zip(values, bottom)):
            if v >= min_label:
                # White ink only on the darkest steps, where it is legible.
                dark = color in SEVERITY[2:] or color in (ORGAN["kidney"],)
                ax.text(xi, b + v / 2, fmt.format(v), ha="center", va="center",
                        fontsize=8, color=SURFACE if dark else INK)
        bottom += values

    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    return ax


def forest(ax, labels: Sequence[str], estimates: Sequence[float],
           ci_lo: Sequence[float], ci_hi: Sequence[float], *,
           colors: Sequence[str] | str = EMPHASIS, reference: float = 1.0,
           log: bool = True, significant: Sequence[bool] | None = None):
    """Dot-and-whisker plot of effect estimates.

    The natural form for odds ratios: the interval is the finding, and a
    reference line at 1.0 shows at a glance which intervals cross it.
    Non-significant rows are drawn hollow so "crosses 1" is visible without
    reading the numbers.
    """
    y = np.arange(len(labels))[::-1]
    if isinstance(colors, str):
        colors = [colors] * len(labels)
    if significant is None:
        significant = [lo > reference or hi < reference
                       for lo, hi in zip(ci_lo, ci_hi)]

    ax.axvline(reference, color=BASELINE, linewidth=1.0, zorder=1)
    for yi, est, lo, hi, color, sig in zip(y, estimates, ci_lo, ci_hi, colors,
                                           significant):
        ax.plot([lo, hi], [yi, yi], color=color, linewidth=2.0,
                solid_capstyle="round", zorder=2)
        ax.plot([est], [yi], marker="o", markersize=9, zorder=3,
                color=color if sig else SURFACE,
                markeredgecolor=color, markeredgewidth=2.0)

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    if log:
        ax.set_xscale("log")
        # Odds ratios cluster near 1, so a log axis usually spans well under a
        # decade and matplotlib labels it entirely from MINOR ticks -- which
        # default to scientific notation and render "1.1" as "1.1 x 10^0".
        # Both formatters have to be set, or a forest plot of plausible ORs
        # comes out unreadable.
        plain = mpl.ticker.FuncFormatter(lambda v, _: f"{v:g}")
        ax.xaxis.set_major_formatter(plain)
        ax.xaxis.set_minor_formatter(plain)
        # When the axis spans more than a decade the minor labels collide
        # (0.3 0.4 0.5 0.6 0.7 0.8 0.9 1 ... 20); keep a few round ones only.
        lo_v, hi_v = ax.get_xlim()
        if hi_v / max(lo_v, 1e-9) > 10:
            ticks = [t for t in (0.25, 0.5, 1, 2, 4, 8, 16, 32) if lo_v <= t <= hi_v]
            ax.set_xticks(ticks)
            ax.set_xticks([], minor=True)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_ylim(-0.7, len(labels) - 0.3)
    return ax


def finish(fig, title: str, subtitle: str = "", source: str = "") -> None:
    """Title block and provenance line.

    Every figure states the artifact it was drawn from, so a chart lifted into
    a slide deck still says where its numbers came from.

    Positions are computed in INCHES, not figure fractions: a fraction that
    leaves a clean gap on a 6-inch-tall figure overlaps on a 4-inch one, which
    is exactly how the title and subtitle first collided here.
    """
    w_in, h_in = fig.get_size_inches()

    # Wrap the subtitle to the figure's actual width (~13 chars per inch at 10pt).
    lines: list[str] = []
    if subtitle:
        lines = textwrap.wrap(subtitle, width=max(40, int(w_in * 13)))

    title_in = 0.26                       # baseline of the title
    gap_in = 0.24                         # title -> first subtitle line
    line_in = 0.19                        # between wrapped subtitle lines
    pad_in = 0.22                         # subtitle -> top of the axes

    fig.suptitle(title, x=0.008, y=1 - title_in / h_in, ha="left", va="top",
                 fontsize=13, fontweight="bold", color=INK)

    used = title_in + gap_in
    for i, line in enumerate(lines):
        fig.text(0.008, 1 - (used + i * line_in) / h_in, line, ha="left",
                 va="top", fontsize=9.5, color=INK_SECONDARY)
    if lines:
        used += (len(lines) - 1) * line_in + pad_in
    else:
        used += pad_in - gap_in

    bottom_in = 0.0
    if source:
        fig.text(0.008, 0.012, source, ha="left", va="bottom", fontsize=7.5,
                 color=MUTED)
        bottom_in = 0.22

    fig.tight_layout(rect=(0, bottom_in / h_in, 1, 1 - used / h_in))
