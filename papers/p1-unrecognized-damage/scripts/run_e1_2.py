"""E1.2 — Unrecognized fraction per organ. The paper's headline numbers.

"Unrecognized" = an abnormal result in a participant who reported no
corresponding diagnosis. Kidney and heart only: E0.GATE established that
v3.0.0 has no neuropathy self-report item, so nerve cannot carry this figure.

Three things are reported rather than one, because the single number is
ambiguous on its own:

1. the unrecognized fraction among the abnormal who ANSWERED the item (the
   headline, refusals excluded from the denominator),
2. the same fraction with refusals kept in the denominator (sensitivity — it
   can only pull the estimate down, and shows by how much),
3. the full 2x2 of test result against self-report, which is what a reader
   needs to judge the claim and what makes the reverse cell visible.
"""

from __future__ import annotations

import pandas as pd

from aireadi import results, stats, thresholds

import _phase1

_phase1.banner("E1.2", "Unrecognized fraction — the headline")

df = _phase1.load()

LABELS = {"kidney": "Kidney — ACR >= 30 mg/g vs 'kidney problems'",
          "heart": "Heart — hs-cTnT >= 14 ng/L vs 'heart attack / other heart issues'"}

# ── 1-2. Unrecognized fraction, by severity, both denominators ──────────
blocks, concordance = [], []
for organ in thresholds.UNRECOGNIZED_ORGANS:
    tab = stats.proportion_by_group(df, f"unrec_{organ}")
    tab.insert(0, "organ", organ)
    tab.insert(1, "definition", LABELS[organ])

    # Sensitivity denominator: all abnormal, refusals included. Same numerator.
    abn, sr = df[f"abn_{organ}"], df[f"sr_{organ}"]
    incl = (abn.eq(1) & sr.eq(0)).astype(float).mask(abn.ne(1))
    sens = stats.proportion_by_group(df.assign(_x=incl), "_x", trend=False)
    tab["n_incl_refusals"] = sens["n"]
    tab["pct_incl_refusals"] = sens["pct"]
    blocks.append(tab)

    # ── 3. The 2x2 ──────────────────────────────────────────────────────
    both = df[abn.notna() & sr.notna()]
    concordance.append({
        "organ": organ,
        "n_evaluable": len(both),
        "abnormal_and_not_reported": int((both[f"abn_{organ}"].eq(1) & both[f"sr_{organ}"].eq(0)).sum()),
        "abnormal_and_reported": int((both[f"abn_{organ}"].eq(1) & both[f"sr_{organ}"].eq(1)).sum()),
        "normal_and_reported": int((both[f"abn_{organ}"].eq(0) & both[f"sr_{organ}"].eq(1)).sum()),
        "normal_and_not_reported": int((both[f"abn_{organ}"].eq(0) & both[f"sr_{organ}"].eq(0)).sum()),
        "refused_the_item": int((abn.notna() & sr.isna()).sum()),
    })

table = pd.concat(blocks)
conc = pd.DataFrame(concordance).set_index("organ")
conc["pct_of_cohort_unrecognized"] = (
    100 * conc.abnormal_and_not_reported / conc.n_evaluable).round(1)

# "Either organ" — the abstract's summary figure. The evaluability rule lives
# in the package so a notebook cannot reimplement it differently; see
# thresholds.either_organ for why it is "both evaluable", not "either".
_either = thresholds.either_organ(df)
markers_ok = _either["markers_ok"]
answered = _either["answered"]
either_abn = _either["abnormal"]
either_unrec = _either["unrecognized"]

either = stats.proportion_by_group(
    df.assign(_x=either_unrec.where(answered & either_abn)), "_x")
either.insert(0, "organ", "either")
either.insert(1, "definition", "Kidney or heart — unrecognized among those abnormal on either")
# Same numerator, denominator widened to every abnormal participant including
# those who refused an item.
sens_either = stats.proportion_by_group(
    df.assign(_x=(either_unrec.eq(1)).astype(float).where(markers_ok & either_abn)),
    "_x", trend=False)
either["n_incl_refusals"] = sens_either["n"]
either["pct_incl_refusals"] = sens_either["pct"]
table = pd.concat([table, either])

pd.set_option("display.width", 220)


def overall(organ):
    return table[table.organ == organ].loc["Overall"]


print()
for organ in [*thresholds.UNRECOGNIZED_ORGANS, "either"]:
    sub = table[table.organ == organ]
    print(sub.definition.iloc[0])
    print(sub.drop(columns=["organ", "definition", "trend_p", "chi2_p"]).to_string())
    o = overall(organ)
    print(f"  UNRECOGNIZED {o.k:,.0f}/{o.n:,.0f} = {o.pct}% (95% CI {o.ci_lo}-{o.ci_hi})"
          f"   trend z={o.trend_z} p={o.trend_p:.2g}")
    if pd.notna(o.pct_incl_refusals):
        print(f"  with refusals kept in the denominator: "
              f"{o.k:,.0f}/{o.n_incl_refusals:,.0f} = {o.pct_incl_refusals}%")
    print()

print("Test result vs self-report (participants with both):")
print(conc.to_string())
print()
for organ in thresholds.UNRECOGNIZED_ORGANS:
    c = conc.loc[organ]
    reported = int(c.abnormal_and_reported + c.normal_and_reported)
    print(f"  {organ}: of {reported:,} who reported a diagnosis, "
          f"{int(c.normal_and_reported):,} ({100 * c.normal_and_reported / reported:.0f}%) "
          f"had a normal test today — a reminder this is a same-day snapshot, "
          f"not a lifetime history.")

# ── 4. Population burden ────────────────────────────────────────────────
# The conditional fraction above answers "of those with damage, how many did
# not know". It is NOT the same question as "how much unrecognized damage does
# this population carry", and the two move in opposite directions across
# severity. Reporting only the first would invert the finding.
burden_blocks = []
for organ in thresholds.UNRECOGNIZED_ORGANS:
    abn, sr = df[f"abn_{organ}"], df[f"sr_{organ}"]
    flag = (abn.eq(1) & sr.eq(0)).astype(float).mask(abn.isna() | sr.isna())
    b = stats.proportion_by_group(df.assign(_x=flag), "_x")
    b.insert(0, "organ", organ)
    burden_blocks.append(b)

b = stats.proportion_by_group(
    df.assign(_x=either_unrec.where(answered)), "_x")
b.insert(0, "organ", "either")
burden_blocks.append(b)
burden = pd.concat(burden_blocks)

print("\nPopulation burden — abnormal AND unrecognized, per 100 evaluable participants:")
for organ in [*thresholds.UNRECOGNIZED_ORGANS, "either"]:
    sub = burden[burden.organ == organ]
    o = sub.loc["Overall"]
    print(f"\n  {organ}: {o.k:,.0f}/{o.n:,.0f} = {o.pct}% of the cohort "
          f"(95% CI {o.ci_lo}-{o.ci_hi}), trend z={o.trend_z} p={o.trend_p:.2g}")
    print("   " + sub.drop(index="Overall")[["n", "k", "pct"]].to_string().replace("\n", "\n   "))

summary = "; ".join(
    f"{o} {overall(o).k:,.0f}/{overall(o).n:,.0f} = {overall(o).pct}% "
    f"(95% CI {overall(o).ci_lo}-{overall(o).ci_hi})"
    for o in [*thresholds.UNRECOGNIZED_ORGANS, "either"]
)
trends = "; ".join(
    f"{o} z={overall(o).trend_z} p={overall(o).trend_p:.1e}"
    for o in [*thresholds.UNRECOGNIZED_ORGANS, "either"]
)

results.save(
    "E1.2", table, paper="p1",
    method=("Unrecognized fraction (abnormal result AND no corresponding self-reported "
            "diagnosis) for kidney and heart, overall and by severity group, Wilson 95% "
            "CIs and Cochran-Armitage trend. Denominator = abnormal with the item "
            "answered; the refusals-included denominator is reported alongside."),
    result=f"Unrecognized: {summary}. Trend across severity: {trends}.",
    decision="keep", name="unrecognized_by_group",
)
results.save(
    "E1.2", conc, paper="p1",
    method="2x2 of measured result against same-day self-report, per organ.",
    result=("Concordance table: "
            + "; ".join(f"{o} abnormal-not-reported {conc.loc[o, 'abnormal_and_not_reported']:,}, "
                        f"abnormal-reported {conc.loc[o, 'abnormal_and_reported']:,}, "
                        f"normal-reported {conc.loc[o, 'normal_and_reported']:,}, "
                        f"normal-not-reported {conc.loc[o, 'normal_and_not_reported']:,}"
                        for o in thresholds.UNRECOGNIZED_ORGANS)),
    decision="keep", name="concordance", primary=False,
)


def bo(organ):
    return burden[burden.organ == organ].loc["Overall"]


results.save(
    "E1.2", burden, paper="p1",
    method=("Population burden: share of ALL evaluable participants who are both "
            "abnormal and unrecognized, by severity group. The conditional fraction "
            "and the population burden answer different questions and move in "
            "opposite directions across severity, so both are reported."),
    result=("Burden rises with severity even though the conditional fraction falls: "
            + "; ".join(f"{o} {bo(o).pct}% overall (trend z={bo(o).trend_z}, "
                        f"p={bo(o).trend_p:.1e})"
                        for o in [*thresholds.UNRECOGNIZED_ORGANS, "either"])),
    decision="keep", name="population_burden", primary=False,
)
