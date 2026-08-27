"""E4.2 — Figure 1: unrecognized damage by organ and severity group.

Two panels, one message, in the order `E2.DECIDE` fixed:

* **Panel A — population burden (primary).** Of every evaluable participant
  in each severity group, the share carrying kidney, heart, or either-organ
  damage that they reported never having been told about. This is the
  abstract's lead number and the screening argument: it rises steeply with
  severity.
* **Panel B — the conditional fraction (mechanism).** Of those with an
  abnormal result, the share never told. It *falls* with severity — a
  diabetes diagnosis buys monitoring, and monitoring is how things get found.

Both panels read straight from the E1.2 artifacts that E3.3 reproduced exactly,
so the figure cannot disagree with the tables. Wilson 95% intervals throughout.
Nerve is absent from both panels by design (`E0.GATE`): no self-report
comparator exists, so it carries no unrecognized figure.

Written at 300 dpi PNG for the manuscript, plus PDF and SVG for the journal.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from aireadi import figures, results

import _phase3

_phase3.banner("E4.2", "Figure 1 — unrecognized damage by organ and severity")

R = _phase3.RESULTS
burden = pd.read_csv(R / "E1_2_population_burden.csv").set_index(["organ", "stratum"])
frac = pd.read_csv(R / "E1_2_unrecognized_by_group.csv").set_index(["organ", "stratum"])
GROUPS = ["Healthy", "Pre-DM", "Oral Med", "Insulin"]
ORGANS = [("kidney", "Kidney (ACR ≥ 30 mg/g)"), ("heart", "Heart (hs-cTnT ≥ 14 ng/L)"),
          ("either", "Either organ")]

figures.style()
fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(12.5, 5.2))
for a in (ax_a, ax_b):
    a.grid(axis="x", visible=False)

# ── Panel A — burden ────────────────────────────────────────────────────
x = np.arange(len(GROUPS))
slot = 0.75 / len(ORGANS)
for i, (organ, label) in enumerate(ORGANS):
    vals = [float(burden.loc[(organ, g), "pct"]) for g in GROUPS]
    lo = [float(burden.loc[(organ, g), "ci_lo"]) for g in GROUPS]
    hi = [float(burden.loc[(organ, g), "ci_hi"]) for g in GROUPS]
    offs = (i - (len(ORGANS) - 1) / 2) * slot
    color = figures.ORGAN.get(organ, figures.INK)
    ax_a.bar(x + offs, vals, slot - 0.03, color=color, label=label, edgecolor=figures.SURFACE, linewidth=0.8)
    ax_a.errorbar(x + offs, vals, yerr=[np.array(vals) - np.array(lo), np.array(hi) - np.array(vals)],
                  fmt="none", ecolor=figures.INK_SECONDARY, elinewidth=1.0, capsize=2)
    # Labels ride above the upper interval, not on the bar top, so they never sit on a cap.
    for xi, v, h in zip(x + offs, vals, hi):
        ax_a.annotate(f"{v:.0f}", (xi, h), xytext=(0, 3), textcoords="offset points",
                      ha="center", va="bottom", fontsize=8, color=figures.INK_SECONDARY)
ax_a.set_xticks(x); ax_a.set_xticklabels(GROUPS)
ax_a.set_ylabel("% of evaluable participants")
ax_a.set_ylim(0, 58)
ax_a.set_title("A  Unrecognized damage per 100 participants", loc="left")
ax_a.legend(loc="upper left", frameon=False)
z_e = float(burden.loc[("either", "Overall"), "trend_z"])
ax_a.text(0.99, 0.97, f"trend across severity, either organ: z = {z_e:.2f}",
          transform=ax_a.transAxes, ha="right", va="top", fontsize=8.5, color=figures.INK_SECONDARY)

# ── Panel B — conditional fraction ──────────────────────────────────────
for organ, label in ORGANS:
    vals = [float(frac.loc[(organ, g), "pct"]) for g in GROUPS]
    lo = [float(frac.loc[(organ, g), "ci_lo"]) for g in GROUPS]
    hi = [float(frac.loc[(organ, g), "ci_hi"]) for g in GROUPS]
    color = figures.ORGAN.get(organ, figures.INK)
    ax_b.plot(x, vals, marker="o", color=color, label=label, linewidth=2.0, markersize=7)
    ax_b.fill_between(x, lo, hi, color=color, alpha=0.12, linewidth=0)
    # Endpoint labels only, offset by organ, so the three lines' labels cannot collide
    # where the lines cross in the middle groups; the table carries every value.
    # Offsets chosen per (organ, end) from the frozen values so no two labels share a slot:
    # Healthy runs kidney 89 > either 85 > heart 74; Insulin runs either 70 > heart 63 > kidney 57.
    offsets = {("kidney", 0): 9, ("kidney", -1): -13, ("heart", 0): -13, ("heart", -1): 9,
               ("either", 0): -13, ("either", -1): 9}
    for end, (xi, v) in zip((0, -1), [(x[0], vals[0]), (x[-1], vals[-1])]):
        dy = offsets[(organ, end)]
        ax_b.annotate(f"{v:.0f}", (xi, v), xytext=(0, dy), textcoords="offset points",
                      ha="center", va="bottom" if dy > 0 else "top", fontsize=8.5, color=color)
ax_b.set_xticks(x); ax_b.set_xticklabels(GROUPS)
ax_b.set_ylabel("% of those with an abnormal result")
ax_b.set_ylim(40, 100)
ax_b.set_title("B  Of those with damage, the share never told", loc="left")
ax_b.legend(loc="lower left", frameon=False)
z_f = float(frac.loc[("either", "Overall"), "trend_z"])
ax_b.text(0.99, 0.97, f"trend across severity, either organ: z = {z_f:.2f}",
          transform=ax_b.transAxes, ha="right", va="top", fontsize=8.5, color=figures.INK_SECONDARY)

figures.finish(
    fig, "Figure 1 — Unrecognized kidney and heart damage across the type 2 diabetes spectrum",
    "AI-READI v3.0.0, N = 2,280. Unrecognized = abnormal study-visit result with no corresponding "
    "self-reported diagnosis. Bars and bands: Wilson 95% CI. Burden rises with severity while the "
    "conditional fraction falls — sicker groups carry more damage, so even a smaller share missed is "
    "more people. Nerve carries no unrecognized figure: v3.0.0 has no neuropathy self-report item.",
    source="Source: results/E1_2_population_burden.csv, results/E1_2_unrecognized_by_group.csv "
           "(reproduced exactly by E3.3)")

for ext in ("pdf", "svg"):
    fig.savefig(R / f"E4_2_figure1.{ext}", bbox_inches="tight")
fig.savefig(R / "E4_2_figure1_300dpi.png", dpi=300, bbox_inches="tight")

results.save(
    "E4.2", fig, paper="p1",
    method=("Figure 1: panel A the population burden of unrecognized kidney / heart / either-organ "
            "damage per 100 evaluable participants by severity group (primary, per E2.DECIDE); panel B "
            "the conditional unrecognized fraction among the abnormal (mechanism). Wilson 95% CIs. "
            "Drawn from the E1.2 artifacts that E3.3 reproduced exactly; PNG 300 dpi, PDF and SVG "
            "written alongside."),
    result=(f"Either-organ burden {burden.loc[('either', 'Healthy'), 'pct']}% -> "
            f"{burden.loc[('either', 'Insulin'), 'pct']}% across severity (z={z_e:.2f}); either-organ "
            f"fraction {frac.loc[('either', 'Healthy'), 'pct']}% -> {frac.loc[('either', 'Insulin'), 'pct']}% "
            f"(z={z_f:.2f})."),
    decision="keep — re-rendered after visual checks (labels off the interval caps; panel B endpoint labels with per-organ offsets; headroom for the Insulin label)", name="figure1",
)
