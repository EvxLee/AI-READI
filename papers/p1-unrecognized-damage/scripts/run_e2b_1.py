"""E2B.1 — BMI vs measured organ damage.

BMI already rides through this paper as a covariate and a Table 1 row (decision
4 in PROJECT_CONTEXT). This experiment asks whether it earns more than that:
does body mass track measured organ damage once age, severity and site are held
constant?

One property of this exposure deserves stating before any model runs. BMI is
entangled with severity by design — the severity groups are defined by
treatment, and treatment tracks weight — so the unadjusted-to-adjusted
comparison here is not a formality. It is the whole result. A raw BMI-damage
association in this cohort is close to guaranteed and means nothing on its own;
the question is what survives.

Because BMI is itself a member of the default recognition covariate set,
`associations` drops it from its own adjustment automatically rather than
entering the same column twice.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations, results

import _phase2

_phase2.banner("E2B.1", "BMI vs measured organ damage")

df = _phase2.load()

# The clinical bands, so the artifact can say something a clinician reads
# directly rather than only an odds ratio per SD.
df["bmi_obese"] = df["bmi"].ge(30).astype(float).mask(df["bmi"].isna())

EXPOSURES = {
    "bmi": "BMI (kg/m2)",
    "bmi_obese": "Obese (BMI >= 30)",
}

print(f"BMI available for {int(df.bmi.notna().sum()):,} participants; "
      f"median {df.bmi.median():.1f}, {int(df.bmi_obese.sum()):,} with BMI >= 30")

bands = (df.assign(band=pd.cut(df["bmi"], [0, 18.5, 25, 30, 35, 100],
                               labels=["<18.5", "18.5-25", "25-30", "30-35", ">=35"]))
           .groupby("band", observed=True)
           .agg(n=("bmi", "size"), pct_any=("abn_any", "mean"),
                pct_kidney=("abn_kidney", "mean"), pct_heart=("abn_heart", "mean"),
                pct_nerve=("abn_nerve", "mean")))
for col in [c for c in bands.columns if c.startswith("pct")]:
    bands[col] = (100 * bands[col]).round(1)
_phase2.print_table(bands, title="Damage prevalence by BMI band (unadjusted, descriptive)")

table = associations.sweep(
    df, EXPOSURES,
    adjustments=["unadjusted", "damage", "damage+hba1c"],
    fdr_within="damage",
)
_phase2.print_table(table, title="BMI vs damage — full sweep")

survivors = _phase2.headline(table)
raw_hits = _phase2.headline(table, use_q=False)
n_adjusted = int((table.index.get_level_values("adjustment") == "damage").sum())

# How much of the raw association is severity confounding? Reported explicitly,
# because "BMI predicts damage" is the claim a reader will assume was tested.
shift = []
for exposure in EXPOSURES:
    for outcome in associations.BINARY_OUTCOMES:
        u = table.loc[(exposure, outcome, "unadjusted")]
        a = table.loc[(exposure, outcome, "damage")]
        shift.append({"exposure": exposure, "outcome": outcome,
                      "unadjusted_or": u.estimate, "unadjusted_p": u.p,
                      "adjusted_or": a.estimate, "adjusted_p": a.p,
                      "survives_adjustment": bool(a.p < 0.05),
                      "lost_to_adjustment": bool(u.p < 0.05 and a.p >= 0.05)})
attenuation = pd.DataFrame(shift).set_index(["exposure", "outcome"])
_phase2.print_table(attenuation, title="What adjustment does to the raw BMI association")

strata = associations.stratified(df, "bmi", "abn_any")
_phase2.print_table(strata, title="BMI (per SD) vs any-organ damage, within severity group")

print(f"\nAdjusted family: {n_adjusted} models, {len(raw_hits)} with p < 0.05, "
      f"{len(survivors)} surviving FDR; "
      f"{int(attenuation.lost_to_adjustment.sum())} associations lost to adjustment")

results.save(
    "E2B.1", table, paper="p1",
    method=("BMI, continuous and at the >= 30 obesity cutoff, against each damage outcome: "
            "unadjusted, adjusted for age + severity + site, and + HbA1c. Odds ratios per "
            "1 SD; FDR within the adjusted family."),
    result=(f"Of {n_adjusted} adjusted models, {len(raw_hits)} reach p < 0.05 and "
            f"{len(survivors)} survive FDR. Surviving: "
            f"{_phase2.summarise(survivors) if len(survivors) else 'none'}. "
            f"{int(attenuation.lost_to_adjustment.sum())} of "
            f"{len(attenuation)} raw associations are lost once age + severity + site "
            f"enter, which is the expected direction: BMI is entangled with severity by "
            f"design."),
    decision="keep", name="sweep",
)
results.save(
    "E2B.1", attenuation, paper="p1",
    method=("Side-by-side unadjusted and adjusted BMI effects, flagging which raw "
            "associations do not survive age + severity + site."),
    result=("Lost to adjustment: "
            + (", ".join(f"{e}/{o}" for e, o in
                         attenuation[attenuation.lost_to_adjustment].index)
               or "none")
            + ". Surviving adjustment: "
            + (", ".join(f"{e}/{o}" for e, o in
                         attenuation[attenuation.survives_adjustment].index) or "none")),
    decision="keep", name="attenuation", primary=False,
)
results.save(
    "E2B.1", bands, paper="p1",
    method="Damage prevalence by clinical BMI band, descriptive and unadjusted.",
    result=("; ".join(f"{b}: n={int(r.n)}, any {r.pct_any}%" for b, r in bands.iterrows())),
    decision="keep", name="bands", primary=False,
)
results.save(
    "E2B.1", strata, paper="p1",
    method=("BMI (per SD) vs any-organ damage within each severity group, age + site "
            "adjusted, bootstrap intervals where the smaller cell is under 50."),
    result=("; ".join(f"{s} OR={r.estimate} ({r.ci_lo}-{r.ci_hi}), p={r.p:.3g}"
                      for s, r in strata.iterrows())),
    decision="keep", name="by_severity", primary=False,
)
