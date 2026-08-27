"""E2F.1 — Access barriers and insecurity vs unrecognized status.

The most plausible mechanism the paper has for *why* damage goes unrecognized:
if you cannot get an appointment, cannot afford the prescription, or are not
listened to when you get there, nobody tells you your albumin is high. This is
the one Phase-2 track whose result would speak directly to Aim 1's explanation
rather than sitting beside it.

It is also the track with the most history attached. Three of four SDOH variables
in the deleted EDA notebooks were built by positionally slicing the racial
discrimination battery, and every result from that era — including the
"insecurity paradox" — is an artifact of that bug. It was never published, so
**this is not a correction of a field-level finding and must never be framed as
one.** It is a first look.

Scoring is deliberately not done here. `omop.phenx_scores` owns it, because the
traps are in the scoring rather than the modelling: two batteries are
non-monotonic in their coded values, three items are skip-gated, and two are
nominal. See CAVEATS.

Outcome is UNRECOGNIZED status, not damage, so the inherited Phase-1 constraints
bind: severity (the fraction falls across it), marker magnitude (the dominant
predictor), and age (the only term holding across all heart models). Reported
overall and within severity groups, since the plan requires insecurity to be
interpreted within groups only.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations, azure_io, omop, results, thresholds

import _phase2

_phase2.banner("E2F.1", "Access barriers and insecurity vs unrecognized status")

df = _phase2.load()

obs = omop.add_item_key(azure_io.load_table(
    "observation", usecols=["person_id", "observation_source_value", "value_as_number"]))
scores = omop.phenx_scores(obs).reset_index()
scores["person_id"] = scores["person_id"].astype(str)
df = df.merge(scores, on="person_id", how="left")

EXPOSURES = {
    "healthcare_access_barriers": "Healthcare access barriers (0-3)",
    "prescription_unaffordable": "Prescription unaffordability (0-4)",
    "food_insecurity": "Food insecurity, USDA count (0-5)",
    "food_insecure": "Food insecure (USDA >= 2)",
    "housing_insecure": "Housing insecure (no steady place or at risk)",
    "clinician_discrimination": "Clinician discrimination, mean (1-5)",
}

print("Score coverage and distribution:")
for column, label in EXPOSURES.items():
    s = df[column]
    print(f"  {label:<48} n={int(s.notna().sum()):>5}  mean {s.mean():.3f}  "
          f"max {s.max():.0f}")

# Unrecognized on either organ, defined exactly as E1.2 defines it.
either = thresholds.either_organ(df)
df["unrec_either"] = either["unrecognized"]
df.loc[~(either["abnormal"] & either["answered"]), "unrec_either"] = float("nan")
print(f"\nOutcome: {int(df.unrec_either.notna().sum())} participants abnormal on kidney or "
      f"heart with both items answered; {int(df.unrec_either.sum())} never told")

OUTCOMES = {f"unrec_{organ}": f"Unrecognized — {organ}"
            for organ in thresholds.UNRECOGNIZED_ORGANS}
OUTCOMES["unrec_either"] = "Unrecognized — either organ"
MARKER = {"unrec_kidney": ["log_acr"], "unrec_heart": ["log_troponin"],
          "unrec_either": ["log_acr", "log_troponin"]}

rows = []
for outcome, outcome_label in OUTCOMES.items():
    for exposure, exposure_label in EXPOSURES.items():
        for adjustment, covariates in [
            ("unadjusted", []),
            ("full", associations.ADJUSTMENTS["recognition"] + MARKER[outcome]),
        ]:
            row = associations.fit(df, outcome, exposure, covariates)
            row.update({"outcome_label": outcome_label,
                        "exposure_label": exposure_label,
                        "adjustment": adjustment})
            rows.append(row)

table = pd.DataFrame(rows)
primary = table["adjustment"] == "full"
table.loc[primary, "q"] = associations.fdr(table.loc[primary, "p"])
table = table.set_index(["outcome", "exposure", "adjustment"])[
    ["outcome_label", "exposure_label", "scale", "n", "estimate", "ci_lo", "ci_hi",
     "p", "q", "note"]]
_phase2.print_table(table, title="Access and insecurity vs unrecognized status")

survivors = table[table["q"] < 0.05]
raw_hits = table[primary.to_numpy() & (table["p"] < 0.05).to_numpy()]
n_primary = int(primary.sum())
print(f"\nPrimary family (fully adjusted): {n_primary} models, {len(raw_hits)} with "
      f"p < 0.05, {len(survivors)} surviving FDR")

# Within severity groups, as the plan requires for these variables. `unrec_either`
# is the pre-declared outcome; `unrec_heart` is added because that is where the
# surviving association landed, and a pooled effect that vanishes within every
# group is a statement about group composition rather than about barriers.
strata = pd.concat({
    "unrec_either": associations.stratified(
        df, "healthcare_access_barriers", "unrec_either",
        covariates=["age", "C(clinical_site)", "hba1c", "bmi",
                    "log_acr", "log_troponin"]),
    "unrec_heart": associations.stratified(
        df, "healthcare_access_barriers", "unrec_heart",
        covariates=["age", "C(clinical_site)", "hba1c", "bmi", "log_troponin"]),
}, names=["outcome"])
_phase2.print_table(strata, title="Access barriers vs unrecognized, within severity group")

# Sanity check on the scoring, reported so the artifact evidences it: barriers
# and insecurity should track each other and should be commoner at higher
# severity. If they do not, the scoring is wrong, not the world.
correlations = df[list(EXPOSURES)].corr().round(3)
_phase2.print_table(correlations, title="Do the SDOH scores cohere with each other?")
by_group = (df.groupby("study_group_label", observed=True)[list(EXPOSURES)]
              .mean().round(3))
_phase2.print_table(by_group, title="SDOH scores by severity group")

results.save(
    "E2F.1", table, paper="p1",
    method=("Healthcare access barriers, prescription unaffordability, food insecurity "
            "(USDA 5-item short form), housing insecurity and clinician discrimination "
            "against unrecognized status, per organ and either organ. Unadjusted and fully "
            "adjusted (age + severity + site + HbA1c + BMI + log marker magnitude), the "
            "latter being the primary family with FDR applied. Scores built by "
            "omop.phenx_scores, which handles the non-monotonic coding of pxhi1/pxfi1/pxfi2, "
            "excludes skip-gated items from sums, and drops nominal items."),
    result=(f"{len(survivors)} of {n_primary} fully-adjusted models survive FDR "
            f"({len(raw_hits)} reach p < 0.05 uncorrected). Surviving: "
            f"{_phase2.summarise(survivors) if len(survivors) else 'none'}. Coverage: "
            + ", ".join(f"{label} n={int(df[col].notna().sum())}"
                        for col, label in EXPOSURES.items())
            + ". NOT a correction of any published finding: the EDA-era 'insecurity "
              "paradox' was an artifact of the positional-slicing bug and existed only in "
              "this repo (CAVEATS)."),
    decision="keep", name="models",
)
results.save(
    "E2F.1", by_group, paper="p1",
    method=("Mean SDOH score by severity group, as a scoring sanity check — barriers should "
            "coexist and should not be flat across a cohort where severity tracks "
            "socioeconomic position."),
    result="; ".join(f"{g}: access {r.healthcare_access_barriers}, food "
                     f"{r.food_insecurity}, discrimination {r.clinician_discrimination}"
                     for g, r in by_group.iterrows()),
    decision="keep", name="by_group", primary=False,
)
results.save(
    "E2F.1", strata, paper="p1",
    method=("Access barriers vs unrecognized status within each severity group, fully "
            "adjusted, as the plan requires for insecurity variables. Both the pre-declared "
            "either-organ outcome and the heart outcome where the pooled association "
            "survived."),
    result="; ".join(f"{o}/{s} OR={r.estimate} ({r.ci_lo}-{r.ci_hi}), n={r.n}, p={r.p:.3g}"
                     for (o, s), r in strata.iterrows()),
    decision="keep", name="by_severity", primary=False,
)
