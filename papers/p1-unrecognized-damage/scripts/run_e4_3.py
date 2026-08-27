"""E4.3 — Figure 2: multi-organ damage.

Panel A is the organ-count distribution by severity group (stacked); panel B
is the overlap of the three organs as an UpSet-style bar chart of every
observed combination. Both read from the E1.3 artifacts. The figure exists to
make one sentence visible: a third of insulin-treated participants carry
damage in two or more organs at once, and only a third are clear on all three.

A note on what this figure must not do: it shows *measured* damage on all
three organs including nerve. It says nothing about recognition, which nerve
cannot carry (`E0.GATE`). The caption states that.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from aireadi import figures, results

import _phase3

_phase3.banner("E4.3", "Figure 2 — multi-organ damage")

R = _phase3.RESULTS
counts = pd.read_csv(R / "E1_3_organ_counts.csv").set_index("stratum")
overlap = pd.read_csv(R / "E1_3_overlap.csv")
GROUPS = ["Healthy", "Pre-DM", "Oral Med", "Insulin"]

figures.style()
fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(12.5, 5.4), gridspec_kw={"width_ratios": [1, 1.25]})
for a in (ax_a, ax_b):
    a.grid(axis="x", visible=False)

# ── Panel A — organ-count distribution by severity ──────────────────────
series = {f"{k} organ{'s' if k != 1 else ''}": [float(counts.loc[g, f"pct_{k}"]) for g in GROUPS]
          for k in (0, 1, 2, 3)}
series = {("No organ" if k.startswith("0") else k): v for k, v in series.items()}
figures.stacked_bars(ax_a, [f"{g}\nn = {int(counts.loc[g, 'n']):,}" for g in GROUPS], series,
                     figures.SEVERITY, fmt="{:.0f}%", min_label=5.0)
ax_a.set_ylabel("% of participants measured on all three organs")
ax_a.set_ylim(0, 100)
ax_a.set_title("A  Number of organs with an abnormal result", loc="left")
ax_a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False)

# ── Panel B — every observed combination ────────────────────────────────
combo_col = "combination" if "combination" in overlap.columns else overlap.columns[0]
n_col = next(c for c in overlap.columns if c.startswith("n") and c != combo_col)
ov = overlap[overlap[combo_col].str.lower() != "none"].sort_values(n_col, ascending=False).reset_index(drop=True)
total = int(overlap[n_col].sum())
x = np.arange(len(ov))
colors = []
for name in ov[combo_col]:
    parts = [p.strip().lower() for p in str(name).replace("+", ",").split(",")]
    colors.append(figures.ORGAN[parts[0]] if len(parts) == 1 else figures.INK_SECONDARY)
bars = ax_b.bar(x, ov[n_col], 0.62, color=colors, edgecolor=figures.SURFACE)
for xi, n in zip(x, ov[n_col]):
    ax_b.annotate(f"{int(n)}\n({100 * n / total:.1f}%)", (xi, n), xytext=(0, 3), textcoords="offset points",
                  ha="center", va="bottom", fontsize=8, color=figures.INK_SECONDARY)
ax_b.set_xticks(x)
ax_b.set_xticklabels([str(c).replace(" + ", "\n+ ") for c in ov[combo_col]], fontsize=8.5)
ax_b.set_ylabel("participants")
ax_b.set_ylim(0, float(ov[n_col].max()) * 1.25)
none_n = int(overlap.loc[overlap[combo_col].str.lower() == "none", n_col].iloc[0])
ax_b.set_title(f"B  Which organs, in combination  (no organ: {none_n:,} of {total:,})", loc="left")

figures.finish(
    fig, "Figure 2 — Multi-organ damage: how many organs, and which together",
    "AI-READI v3.0.0; participants measured on all three organs (n = 2,216). Abnormal = ACR ≥ 30 mg/g, "
    "hs-cTnT ≥ 14 ng/L, ≥ 2 insensate sites of 10. This figure shows measured damage only; recognition "
    "is shown in Figure 1 for kidney and heart, and cannot be assessed for nerve.",
    source="Source: results/E1_3_organ_counts.csv, results/E1_3_overlap.csv")

for ext in ("pdf", "svg"):
    fig.savefig(R / f"E4_3_figure2.{ext}", bbox_inches="tight")
fig.savefig(R / "E4_3_figure2_300dpi.png", dpi=300, bbox_inches="tight")

results.save(
    "E4.3", fig, paper="p1",
    method=("Figure 2: panel A the distribution of abnormal-organ counts (0-3) by severity group, "
            "stacked; panel B every observed combination of kidney / heart / nerve damage. From the "
            "E1.3 artifacts; PNG 300 dpi, PDF and SVG written alongside."),
    result=(f"Two or more organs: {counts.loc['Healthy', 'pct_2_or_more']}% Healthy -> "
            f"{counts.loc['Insulin', 'pct_2_or_more']}% Insulin; most common single organ: "
            f"{ov.iloc[0][combo_col]} ({int(ov.iloc[0][n_col])}); all three in "
            f"{int(overlap.loc[overlap[combo_col].str.contains('kidney', case=False) & overlap[combo_col].str.contains('heart', case=False) & overlap[combo_col].str.contains('nerve', case=False), n_col].iloc[0])}."),
    decision="keep — re-rendered once after a visual check (group n moved into the tick labels, off the title)", name="figure2",
)
