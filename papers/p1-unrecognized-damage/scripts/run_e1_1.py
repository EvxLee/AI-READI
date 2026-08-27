"""E1.1 — Prevalence of an abnormal result per organ, overall and by severity.

Aim 1's first half: how much measured damage is there. Counting, not testing —
these numbers publish whatever they say. The trend test asks the ordered
question the paper actually claims ("does it rise with severity"), and a plain
chi-square rides along so "different across groups" is never mistaken for
"rises across groups".

Also produces the "at least one organ" row the abstract needs, restricted to
participants measured on all three so a partial row cannot look like a clean
negative.
"""

from __future__ import annotations

import pandas as pd

from aireadi import results, stats, thresholds

import _phase1

_phase1.banner("E1.1", "Prevalence of measured organ damage")

df = _phase1.load()

df["abn_any"] = df["n_organs_abnormal"].gt(0).astype(float).mask(
    df["n_organs_abnormal"].isna()
)

LABELS = {
    "kidney": "Kidney — ACR >= 30 mg/g",
    "heart": "Heart — hs-cTnT >= 14 ng/L",
    "nerve": "Nerve — >= 2 insensate sites of 10",
    "any": "Any of the three organs",
}

blocks = []
for organ in [*thresholds.ORGANS, "any"]:
    tab = stats.proportion_by_group(df, f"abn_{organ}")
    tab.insert(0, "organ", organ)
    tab.insert(1, "definition", LABELS[organ])
    blocks.append(tab)

table = pd.concat(blocks)

pd.set_option("display.width", 200)


def overall(organ: str) -> pd.Series:
    return table[table.organ == organ].loc["Overall"]


print()
for organ in [*thresholds.ORGANS, "any"]:
    sub = table[table.organ == organ]
    print(f"{LABELS[organ]}")
    print(sub.drop(columns=["organ", "definition", "trend_p", "chi2_p"]).to_string())
    o = overall(organ)
    print(f"  overall {o.k:,.0f}/{o.n:,.0f} = {o.pct}%  (95% CI {o.ci_lo}-{o.ci_hi})"
          f"   trend z={o.trend_z} p={o.trend_p:.2g}   chi2 p={o.chi2_p:.2g}\n")

summary = "; ".join(
    f"{organ} {overall(organ).k:,.0f}/{overall(organ).n:,.0f} ({overall(organ).pct}%)"
    for organ in [*thresholds.ORGANS, "any"]
)
trends = "; ".join(
    f"{organ} z={overall(organ).trend_z} p={overall(organ).trend_p:.1e}"
    for organ in [*thresholds.ORGANS, "any"]
)

results.save(
    "E1.1", table, paper="p1",
    method=("Prevalence of an abnormal result per organ and for any organ, overall "
            "and by severity group, with Wilson 95% CIs and a Cochran-Armitage "
            "trend test across the four ordered groups."),
    result=f"Overall prevalence {summary}. Trend across severity: {trends}.",
    decision="keep", name="prevalence_by_group",
)
