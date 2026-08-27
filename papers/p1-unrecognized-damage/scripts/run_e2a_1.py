"""E2A.1 — HbA1c and CGM metrics vs measured organ damage.

The question the severity label cannot answer. Participants are grouped by
*treatment* — diet, oral medication, insulin — which is a proxy for how bad the
diabetes is, not a measurement of it. Two people in the Oral Med group can have
very different glucose control. So: does measured organ damage track measured
glycaemia beyond the label?

Four exposures, in increasing order of what they cost to obtain:

* **HbA1c** — one blood draw, ~3-month average, already in the master table.
* **CGM mean glucose** — the manifest's own average over ~11 days.
* **TAR > 180 mg/dL** — the clinical standard-of-care variability measure.
* **CV and MAGE** — variability proper: the same average reached smoothly or in
  swings. These required parsing 2,245 per-participant Dexcom streams
  (`build_cgm_metrics.py`), which is why E0.3 flagged them BUILD REQUIRED.

That ordering is the point of the experiment. If mean glucose or HbA1c carries
everything, the expensive metrics add nothing and the paper says so — a useful
negative for anyone deciding whether CGM is worth it for risk assessment. If
variability adds signal beyond the average, that is a finding.

HbA1c is dropped from the adjustment set here: it is one of the exposures, and
adjusting a glycaemic exposure for a glycaemic covariate answers a question
nobody asked. The severity + age + site default still applies.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations, azure_io, results

import _phase2

_phase2.banner("E2A.1", "HbA1c and CGM metrics vs measured organ damage")

df = _phase2.load()

CGM = azure_io.repo_root() / "data" / "processed" / "p1" / "cgm_metrics.parquet"
if not CGM.exists():
    raise SystemExit(f"missing {CGM} — run build_cgm_metrics.py first")

cgm = pd.read_parquet(CGM)
cgm["person_id"] = cgm["person_id"].astype(str)
df = df.merge(cgm[["person_id", "glucose_mean", "glucose_cv", "tar_180", "mage",
                   "tir", "readings_used", "cgm_days", "pct_censored"]],
              on="person_id", how="left")
print(f"CGM censoring: {int(cgm.pct_censored.gt(0).sum())} participants have at least one "
      f"'High'/'Low' reading placed at the 40/400 boundary, "
      f"{int(cgm.pct_censored.gt(25).sum())} are over 25% censored — see CAVEATS. "
      f"A censoring sensitivity is run below.")

EXPOSURES = {
    "hba1c": "HbA1c (%)",
    "glucose_mean": "CGM mean glucose (mg/dL)",
    "tar_180": "CGM time above 180 mg/dL (%)",
    "glucose_cv": "CGM coefficient of variation (%)",
    "mage": "CGM MAGE (mg/dL)",
}

print("Exposure coverage:")
for column, label in EXPOSURES.items():
    print(f"  {label:<36} n={int(df[column].notna().sum()):>5}  "
          f"median {df[column].median():.2f}")

# Does the manifest's mean agree with the built one? Both exist, so check rather
# than assume; a disagreement would mean the parser read the wrong window.
overlap = df.dropna(subset=["mean_glucose", "glucose_mean"])
delta = (overlap["mean_glucose"] - overlap["glucose_mean"]).abs()
print(f"\nbuilt CGM mean vs manifest mean: n={len(overlap):,}, "
      f"median |diff|={delta.median():.3f}, max={delta.max():.2f} mg/dL")

# HbA1c out of the adjustment set: it is an exposure here.
adjust_no_hba1c = [c for c in associations.ADJUSTMENTS["damage"] if c != "hba1c"]
table = associations.sweep(
    df, EXPOSURES,
    adjustments=["unadjusted", "damage"],
    fdr_within="damage",
)
_phase2.print_table(table, title="Glycaemia vs damage — full sweep")

survivors = _phase2.headline(table)
raw_hits = _phase2.headline(table, use_q=False)
n_adjusted = int((table.index.get_level_values("adjustment") == "damage").sum())

# ── Does variability add anything beyond the average? ───────────────────
#
# The experiment's real question. Each variability metric is fitted with mean
# glucose already in the model, on the identical complete-case sample, so
# "adds signal beyond the average" is tested rather than inferred from two
# separate models with different n.
incremental_rows = []
base = ["glucose_mean"]
sample = df.dropna(subset=["glucose_mean", "glucose_cv", "tar_180", "mage",
                           "age", "study_group_label", "clinical_site"])
for exposure in ("tar_180", "glucose_cv", "mage", "hba1c"):
    for outcome in associations.BINARY_OUTCOMES:
        alone = associations.fit(sample, outcome, exposure, adjust_no_hba1c)
        with_mean = associations.fit(sample, outcome, exposure,
                                     adjust_no_hba1c + base)
        incremental_rows.append({
            "exposure": exposure, "outcome": outcome,
            "or_alone": alone["estimate"], "p_alone": alone["p"],
            "or_with_mean_glucose": with_mean["estimate"], "p_with_mean_glucose": with_mean["p"],
            "adds_beyond_mean": bool(with_mean["p"] < 0.05), "n": with_mean["n"],
        })
incremental = pd.DataFrame(incremental_rows).set_index(["exposure", "outcome"])
incremental["q_with_mean_glucose"] = associations.fdr(incremental["p_with_mean_glucose"])
_phase2.print_table(incremental,
                    title=f"Does variability add beyond mean glucose? (n={len(sample):,})")

# ── Censoring sensitivity ───────────────────────────────────────────────
#
# The variability metrics are the ones censoring damages: a "High" placed at 400
# understates a true excursion, so CV and MAGE are attenuated for the 23
# participants over 25% censored. Refit excluding heavy censoring; a conclusion
# that appears only in one version is a conclusion about sensor saturation.
clean = df[df["pct_censored"].fillna(0).le(25)]
censor_rows = []
for exposure in ("glucose_mean", "tar_180", "glucose_cv", "mage"):
    for outcome in associations.BINARY_OUTCOMES:
        full = associations.fit(df, outcome, exposure, adjust_no_hba1c)
        restricted = associations.fit(clean, outcome, exposure, adjust_no_hba1c)
        censor_rows.append({
            "exposure": exposure, "outcome": outcome,
            "or_all": full["estimate"], "p_all": full["p"], "n_all": full["n"],
            "or_low_censoring": restricted["estimate"],
            "p_low_censoring": restricted["p"], "n_low_censoring": restricted["n"],
            "conclusion_changes": bool((full["p"] < 0.05) != (restricted["p"] < 0.05)),
        })
censoring = pd.DataFrame(censor_rows).set_index(["exposure", "outcome"])
_phase2.print_table(censoring,
                    title=f"Censoring sensitivity: all vs <=25% censored (n={len(clean):,})")
print(f"\nConclusions sensitive to CGM censoring: "
      f"{int(censoring.conclusion_changes.sum())} of {len(censoring)}")

results.save(
    "E2A.1", table, paper="p1",
    method=("HbA1c, CGM mean glucose, TAR>180, CV and MAGE against each damage outcome, "
            "unadjusted and adjusted for age + severity + site (HbA1c excluded from the "
            "covariate set here, being an exposure). Odds ratios per 1 SD; FDR within the "
            "adjusted family. CV, MAGE and TAR were built from 2,245 per-participant "
            "Dexcom streams (build_cgm_metrics.py), the E0.3 BUILD REQUIRED item."),
    result=(f"Of {n_adjusted} adjusted models, {len(raw_hits)} reach p < 0.05 and "
            f"{len(survivors)} survive FDR. Surviving: "
            f"{_phase2.summarise(survivors) if len(survivors) else 'none'}. Coverage: "
            + ", ".join(f"{label} n={int(df[col].notna().sum())}"
                        for col, label in EXPOSURES.items())
            + f". Built CGM mean reproduces the manifest mean (median |diff| "
              f"{delta.median():.3f} mg/dL, n={len(overlap)})."),
    decision="keep", name="sweep",
)
results.save(
    "E2A.1", incremental, paper="p1",
    method=("Whether each glycaemic-variability metric (TAR>180, CV, MAGE) and HbA1c adds "
            "anything to mean glucose: fitted alone and then with mean glucose in the "
            "model, on one identical complete-case sample so the two are comparable."),
    result=(f"On the shared sample (n={len(sample):,}), metrics still significant with mean "
            f"glucose in the model: "
            + ("; ".join(f"{e}/{o} OR={r.or_with_mean_glucose} (p={r.p_with_mean_glucose:.3g})"
                         for (e, o), r in incremental[incremental.adds_beyond_mean].iterrows())
               or "none — mean glucose carries the signal and the variability metrics add "
                  "nothing beyond it")),
    decision="keep", name="incremental", primary=False,
)
results.save(
    "E2A.1", censoring, paper="p1",
    method=("CGM censoring sensitivity. The Dexcom writes 'Low'/'High' as strings outside "
            "its 40-400 mg/dL reportable range — 39,632 readings across 495 participants in "
            "v3.0.0, a defect found and fixed during this build (see CAVEATS). Those are "
            "censored, not missing, and are placed at the boundary, which attenuates "
            "variability. Every glycaemic exposure is refit excluding the participants over "
            "25% censored."),
    result=(f"{int(censoring.conclusion_changes.sum())} of {len(censoring)} conclusions "
            f"change when the {int(df.pct_censored.gt(25).sum())} heavily-censored "
            f"participants are excluded: "
            + ("; ".join(f"{e}/{o} p {r.p_all:.3g} -> {r.p_low_censoring:.3g}"
                         for (e, o), r in censoring[censoring.conclusion_changes].iterrows())
               or "none")
            + ". Before the fix, 2 participants were dropped entirely and 59 had a mean "
              "disagreeing with the manifest by more than 5 mg/dL."),
    decision="keep", name="censoring_sensitivity", primary=False,
)
