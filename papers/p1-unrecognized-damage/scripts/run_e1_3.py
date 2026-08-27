"""E1.3 — Multi-organ view: how many organs at once, and which combinations.

Restricted throughout to the 2,216 participants measured on all three organs.
A participant missing one marker cannot contribute a count of "2 organs" —
they might be a 3 — so partial rows are excluded rather than imputed.

Outputs a counts table, an intersection table, and an UpSet-style figure.
The figure carries one series (intersection size), so it uses a single hue and
direct labels rather than a legend.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from aireadi import results, stats, thresholds

import _phase1

_phase1.banner("E1.3", "Multi-organ damage: counts and overlap")

df = _phase1.load()
complete = df[df["n_organs_abnormal"].notna()].copy()
print(f"\nComplete on all three organs: {len(complete):,} of {len(df):,}")

# ── Distribution of the per-person count ────────────────────────────────
rows = []
for label, sub in [("Overall", complete),
                   *[(g, complete[complete.study_group_label == g])
                     for g in complete.study_group_label.cat.categories]]:
    counts = sub["n_organs_abnormal"].value_counts().reindex([0, 1, 2, 3], fill_value=0)
    rows.append({
        "stratum": label, "n": len(sub),
        **{f"organs_{int(i)}": int(counts[i]) for i in [0, 1, 2, 3]},
        **{f"pct_{int(i)}": round(100 * counts[i] / len(sub), 1) for i in [0, 1, 2, 3]},
        "mean_organs": round(float(sub["n_organs_abnormal"].mean()), 3),
        "pct_2_or_more": round(100 * (sub["n_organs_abnormal"] >= 2).mean(), 1),
    })
counts_table = pd.DataFrame(rows).set_index("stratum")

# Trend on "two or more organs" — the multi-organ claim in one testable number.
multi = stats.proportion_by_group(
    complete.assign(_x=complete["n_organs_abnormal"].ge(2).astype(float)), "_x")
counts_table["trend_z_2plus"] = float(multi.loc["Overall", "trend_z"])
counts_table["trend_p_2plus"] = float(multi.loc["Overall", "trend_p"])

print("\nNumber of organs with an abnormal result, per participant:")
print(counts_table.to_string())

# ── Intersections ───────────────────────────────────────────────────────
flags = complete[[f"abn_{o}" for o in thresholds.ORGANS]].astype(int)
combo = flags.apply(
    lambda r: " + ".join(o for o, v in zip(thresholds.ORGANS, r) if v) or "none", axis=1)
overlap = (combo.value_counts().rename("n").to_frame()
           .assign(pct_of_complete=lambda t: (100 * t.n / len(complete)).round(1)))
overlap.index.name = "combination"
overlap["n_organs"] = [0 if i == "none" else i.count("+") + 1 for i in overlap.index]
print(f"\nCombinations among the {len(complete):,} complete participants:")
print(overlap.to_string())

# ── Unrecognized organ counts (kidney + heart only) ─────────────────────
unrec_ok = df[df["n_organs_unrecognized"].notna()]
unrec_counts = (unrec_ok["n_organs_unrecognized"].value_counts()
                .reindex([0, 1, 2], fill_value=0).rename("n").to_frame())
unrec_counts["pct"] = (100 * unrec_counts.n / len(unrec_ok)).round(1)
unrec_counts.index = [f"{int(i)} organ{'' if i == 1 else 's'} unrecognized"
                      for i in unrec_counts.index]
print(f"\nUnrecognized organ count (kidney+heart, {len(unrec_ok):,} evaluable):")
print(unrec_counts.to_string())

# ── UpSet-style figure ──────────────────────────────────────────────────
BLUE, INK, MUTED = "#2a78d6", "#0b0b0b", "#8f8e88"
inter = overlap[overlap.index != "none"].sort_values("n", ascending=False)
members = [set(i.split(" + ")) for i in inter.index]

fig = plt.figure(figsize=(8.4, 5.6))
gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.06)
ax, mat = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

x = np.arange(len(inter))
ax.bar(x, inter.n, width=0.62, color=BLUE, zorder=3)
for xi, v in zip(x, inter.n):
    ax.text(xi, v + max(inter.n) * 0.02, f"{v:,}", ha="center", va="bottom",
            fontsize=10, color=INK)
ax.set_ylabel("Participants", fontsize=10, color=INK)
ax.set_ylim(0, max(inter.n) * 1.16)
ax.set_xlim(-0.7, len(inter) - 0.3)
ax.grid(axis="y", color="#e6e5e0", lw=0.8, zorder=0)
ax.set_axisbelow(True)
for side in ("top", "right", "bottom"):
    ax.spines[side].set_visible(False)
ax.spines["left"].set_color(MUTED)
ax.tick_params(axis="x", length=0, labelbottom=False)
ax.tick_params(axis="y", colors=MUTED, labelsize=9)
ax.set_title(
    f"Which organs are abnormal together (n = {len(complete):,} measured on all three)",
    fontsize=12, color=INK, pad=12, loc="left")

for row, organ in enumerate(thresholds.ORGANS):
    y = len(thresholds.ORGANS) - 1 - row
    mat.axhspan(y - 0.5, y + 0.5, color="#f5f4f0" if row % 2 == 0 else "white", zorder=0)
    for xi, m in enumerate(members):
        on = organ in m
        mat.scatter(xi, y, s=110, color=BLUE if on else "#dcdbd5", zorder=2)
    on_x = [xi for xi, m in enumerate(members) if organ in m]
    if len(on_x) > 1:
        mat.plot([min(on_x), max(on_x)], [y, y], color=BLUE, lw=0, zorder=1)
for xi, m in enumerate(members):
    ys = [len(thresholds.ORGANS) - 1 - thresholds.ORGANS.index(o) for o in m]
    if len(ys) > 1:
        mat.plot([xi, xi], [min(ys), max(ys)], color=BLUE, lw=2, zorder=1)

mat.set_yticks(range(len(thresholds.ORGANS)))
mat.set_yticklabels([o.capitalize() for o in reversed(thresholds.ORGANS)],
                    fontsize=10, color=INK)
mat.set_xticks(x)
mat.set_xticklabels([])
mat.set_xlim(-0.7, len(inter) - 0.3)
mat.set_ylim(-0.5, len(thresholds.ORGANS) - 0.5)
for side in ("top", "right", "bottom", "left"):
    mat.spines[side].set_visible(False)
mat.tick_params(length=0)
mat.set_xlabel(
    "Kidney ACR ≥ 30 mg/g · Heart hs-cTnT ≥ 14 ng/L · Nerve ≥ 2 insensate sites of 10",
    fontsize=8.5, color=MUTED, labelpad=10)
fig.subplots_adjust(left=0.11, right=0.98, top=0.9, bottom=0.12)

results.save("E1.3", counts_table, paper="p1",
             method=("Per-participant count of organs with an abnormal result, overall "
                     "and by severity, restricted to participants measured on all three."),
             result=(f"Among {len(complete):,} measured on all three: "
                     f"{counts_table.loc['Overall', 'pct_0']}% none, "
                     f"{counts_table.loc['Overall', 'pct_1']}% one, "
                     f"{counts_table.loc['Overall', 'pct_2']}% two, "
                     f"{counts_table.loc['Overall', 'pct_3']}% all three. "
                     f">=2 organs rises {counts_table.loc['Healthy', 'pct_2_or_more']}% -> "
                     f"{counts_table.loc['Insulin', 'pct_2_or_more']}% across severity "
                     f"(trend z={counts_table.loc['Overall', 'trend_z_2plus']}, "
                     f"p={counts_table.loc['Overall', 'trend_p_2plus']:.1e})."),
             decision="keep", name="organ_counts")

results.save("E1.3", overlap, paper="p1",
             method="Counts for every observed combination of abnormal organs.",
             result=("Most common single organ: "
                     f"{inter.index[0]} ({inter.n.iloc[0]:,}); "
                     f"all three organs abnormal in "
                     f"{int(overlap.loc['kidney + heart + nerve', 'n']) if 'kidney + heart + nerve' in overlap.index else 0}."),
             decision="keep", name="overlap", primary=False)

results.save("E1.3", unrec_counts, paper="p1",
             method="Per-participant count of organs abnormal AND unrecognized (kidney+heart).",
             result=(f"Of {len(unrec_ok):,} evaluable on both organs, "
                     f"{unrec_counts.iloc[1]['pct']}% carry one unrecognized organ and "
                     f"{unrec_counts.iloc[2]['pct']}% carry two."),
             decision="keep", name="unrecognized_counts", primary=False)

path = results.save("E1.3", fig, paper="p1",
                    method="UpSet-style figure of abnormal-organ intersections.",
                    result="Figure written; see E1_3_overlap.csv for the counts.",
                    decision="keep", name="overlap_figure", primary=False)
print(f"\nFigure: {path}")
