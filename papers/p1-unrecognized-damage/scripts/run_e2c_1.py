"""E2C.1 — CES-D-10 depressive symptoms vs measured organ damage.

**This is Aim 2, the paper's planned secondary aim**, and the one Phase-2
experiment with a committed hypothesis: H2 says higher CES-D-10 associates with
greater measured damage after adjustment. The honest prior from our own
exploratory phase is that it will be small or null (CES-D was flat against
glycaemic outcomes, rho ~ 0.01). It gets reported either way, in one clearly
labelled paragraph, and a null here costs the paper nothing — Aim 1 stands on
its own.

What makes this version of the question worth asking is Aim 1's result. Every
prior study relating depression to diabetic complications asked participants
whether they had complications; E1.2 showed that 76.6% of the people with
kidney or heart damage in this cohort would have answered no. So those studies
were measuring awareness, not damage. Here the damage is measured the same day.

Exposure is taken two ways — the continuous score, and the validated >= 10
screen-positive cutoff — because a threshold effect and a dose-response are
different claims and the paper should not pick whichever looks better after the
fact. Both are reported for every outcome.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations, results

import _phase2

_phase2.banner("E2C.1", "CES-D-10 vs measured organ damage (Aim 2)")

df = _phase2.load()

EXPOSURES = {
    "cesd_total": "CES-D-10 total (0-30)",
    "cesd_positive": "CES-D-10 screen-positive (>= 10)",
}

print(f"CES-D-10 available for {int(df.cesd_total.notna().sum()):,} participants; "
      f"{int(df.cesd_positive.sum()):,} screen-positive (>= 10)")

# HbA1c joins the adjustment set here: it is the pre-registered covariate for
# Aim 2 (PLAN Part I, item 4) and CES-D is not a glycaemic measure, so there is
# no collinearity argument against it.
table = associations.sweep(
    df, EXPOSURES,
    adjustments=["unadjusted", "damage", "damage+hba1c"],
    fdr_within="damage",
)
_phase2.print_table(table, title="CES-D-10 vs damage — full sweep")

survivors = _phase2.headline(table)
raw_hits = _phase2.headline(table, use_q=False)

print(f"\nAdjusted family: {int((table.index.get_level_values('adjustment') == 'damage').sum())} "
      f"models, {len(raw_hits)} with p < 0.05, {len(survivors)} surviving FDR")

# Severity-stratified look. Not a subgroup hunt: E1.1 showed damage prevalence
# more than triples across these groups, so a pooled estimate can be carried
# entirely by group composition. `abn_any` is the pre-declared outcome here;
# `abn_nerve` is added because that is where the sweep's surviving associations
# landed, and it is labelled as the post-hoc follow-up it is.
strata = pd.concat({
    outcome: associations.stratified(df, "cesd_total", outcome)
    for outcome in ("abn_any", "abn_nerve")
}, names=["outcome"])
_phase2.print_table(strata, title="CES-D-10 (per SD) vs damage, within severity group")

# ── Nerve robustness, run because the sweep landed on nerve ─────────────
#
# Two questions a reviewer will ask, answered in the artifact rather than in
# prose. First: why does ADJUSTMENT STRENGTHEN this? An association that is
# absent unadjusted and appears on adjustment looks like fishing unless the
# mechanism is shown, so each covariate is added on its own. Second: CAVEATS.md
# requires that if a nerve result ever turns on the clinically odd monofilament
# rows -- 14 participants scoring 0 on both feet, 6 scoring 0 on one foot and 10
# on the other -- those rows get inspected before the result is interpreted.
robust_rows = []
for label, covariates in [
    ("unadjusted", []),
    ("+ age only", ["age"]),
    ("+ severity only", ["C(study_group_label)"]),
    ("+ site only", ["C(clinical_site)"]),
    ("+ age + severity", ["age", "C(study_group_label)"]),
    ("full (age + severity + site)", associations.ADJUSTMENTS["damage"]),
]:
    for outcome in ("abn_nerve", "monofilament_missed"):
        row = associations.fit(
            df, outcome, "cesd_total", covariates,
            family="gaussian" if outcome == "monofilament_missed" else "binomial")
        robust_rows.append({"check": label, "sample": "all", "outcome": outcome,
                            **{k: row[k] for k in ("n", "estimate", "ci_lo", "ci_hi", "p")}})

both_feet_zero = df["monofilament_left"].eq(0) & df["monofilament_right"].eq(0)
asymmetric = ((df["monofilament_left"].eq(0) & df["monofilament_right"].eq(10))
              | (df["monofilament_right"].eq(0) & df["monofilament_left"].eq(10)))
for label, keep in [
    (f"drop both-feet-zero (n={int(both_feet_zero.sum())})", ~both_feet_zero),
    (f"drop 0-vs-10 asymmetric (n={int(asymmetric.sum())})", ~asymmetric),
    (f"drop both sets (n={int((both_feet_zero | asymmetric).sum())})",
     ~(both_feet_zero | asymmetric)),
]:
    for outcome in ("abn_nerve", "monofilament_missed"):
        row = associations.fit(
            df[keep], outcome, "cesd_total", associations.ADJUSTMENTS["damage"],
            family="gaussian" if outcome == "monofilament_missed" else "binomial")
        robust_rows.append({"check": label, "sample": "restricted", "outcome": outcome,
                            **{k: row[k] for k in ("n", "estimate", "ci_lo", "ci_hi", "p")}})

robustness = pd.DataFrame(robust_rows).set_index(["check", "outcome"])
_phase2.print_table(robustness, title="Nerve association — covariate build-up and CAVEATS row checks")

# Read the log line's numbers back out of the table that was just written, so
# the prose and the artifact cannot disagree.
_drop_both_label = f"drop both sets (n={int((both_feet_zero | asymmetric).sum())})"


def _or(check: str) -> str:
    return f"{robustness.loc[(check, 'abn_nerve'), 'estimate']:.3f}"


def _p(check: str) -> str:
    return f"{robustness.loc[(check, 'abn_nerve'), 'p']:.3g}"

# The correlations behind the suppression, so the log line can state the reason
# rather than assert it.
corr_cesd_age = float(df[["cesd_total", "age"]].corr().iloc[0, 1])
corr_missed_age = float(df[["monofilament_missed", "age"]].corr().iloc[0, 1])
print(f"\nSuppression check: corr(CES-D, age) = {corr_cesd_age:.3f}, "
      f"corr(insensate sites, age) = {corr_missed_age:.3f}")

n_adjusted = int((table.index.get_level_values("adjustment") == "damage").sum())
verdict = ("AIM 2 IS NULL" if not len(survivors)
           else f"AIM 2 HAS {len(survivors)} SURVIVING ASSOCIATION(S)")

results.save(
    "E2C.1", table, paper="p1",
    method=("CES-D-10, continuous and at the >= 10 screen-positive cutoff, against each "
            "damage outcome (kidney/heart/nerve/any/multi-organ abnormal, and log marker "
            "magnitude): unadjusted, adjusted for age + severity + site, and + HbA1c. "
            "Odds ratios per 1 SD of score; Benjamini-Hochberg within the adjusted family."),
    result=(f"{verdict}. Of {n_adjusted} adjusted models, {len(raw_hits)} reach p < 0.05 "
            f"and {len(survivors)} survive FDR correction. Surviving: "
            f"{_phase2.summarise(survivors)}. CES-D-10 n="
            f"{int(df.cesd_total.notna().sum())}, "
            f"{int(df.cesd_positive.sum())} screen-positive."),
    decision="keep", name="sweep",
)
results.save(
    "E2C.1", strata, paper="p1",
    method=("CES-D-10 (per SD) vs any-organ damage (pre-declared) and vs nerve damage "
            "(post-hoc, following the sweep), fitted within each severity group, "
            "age + site adjusted, with bootstrap intervals where the smaller outcome "
            "cell falls under 50."),
    result=("Within-group estimates: "
            + "; ".join(f"{outcome}/{stratum} OR={r.estimate} ({r.ci_lo}-{r.ci_hi}), "
                        f"n={r.n}" for (outcome, stratum), r in strata.iterrows())),
    decision="keep", name="by_severity", primary=False,
)
results.save(
    "E2C.1", robustness, paper="p1",
    method=("Nerve-association robustness: each adjustment covariate added on its own to "
            "explain why the association appears only after adjustment, plus the "
            "CAVEATS-mandated re-fit excluding the clinically odd monofilament rows "
            "(both feet 0; one foot 0 with the other 10)."),
    result=(f"AGE IS THE SUPPRESSOR: OR per SD {_or('unadjusted')} unadjusted "
            f"(p={_p('unadjusted')}) -> {_or('+ age only')} with age alone "
            f"(p={_p('+ age only')}) -> {_or('full (age + severity + site)')} fully "
            f"adjusted. CES-D falls with age (r={corr_cesd_age:.3f}) while insensate sites "
            f"rise with it (r={corr_missed_age:.3f}), so the two cancel until age is held "
            f"constant; severity alone ({_or('+ severity only')}) and site alone "
            f"({_or('+ site only')}) do nothing. The result does NOT turn on the odd "
            f"monofilament rows: dropping all "
            f"{int((both_feet_zero | asymmetric).sum())} of them leaves OR "
            f"{_or(_drop_both_label)}, p={_p(_drop_both_label)}."),
    decision="keep", name="nerve_robustness", primary=False,
)
