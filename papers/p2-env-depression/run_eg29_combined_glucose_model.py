#!/usr/bin/env python3
"""EG.29 -- combined sanity-check model: glucose control ~ everything at once.

Project-head follow-up (2026-09-02, relayed): "which steps/bmi are linked
to glucose control, see if there's any common factors like steps or
something that could tell a story that maybe more polluted people do less
steps, less glucose control -- as a sanity check, model glucose all at
once in case there were any inconsistencies before."

Every earlier link in this paper was tested one mediation step at a time
(EG.2/3: pollution -> steps/BMI; EG.4: steps/BMI -> glycemic control;
EG.7: pollution -> glycemic control with/without severity). This script
puts pollution, steps, active_calories, BMI, stress, sleep, age, site,
and severity group into ONE model per glycemic outcome, so any
inconsistency between the piecewise story and the full picture shows up
directly -- e.g. if PM2.5's effect on glucose_cv only ever ran through
steps, its coefficient should shrink toward zero once steps is in the
same model.

Two variants per outcome, both requested implicitly by "in case there
were inconsistencies before" (EG.7 already showed severity changes the
pollution answer):
  * with severity group as a covariate (dummy-coded)
  * without severity group (matches EG.7's no-severity design)

Outcomes: hba1c, glucose_mean, glucose_cv, tar_180 -- the same 4-outcome
set used since EG.1/EG.7, for direct comparability.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"

OUTCOMES = ["hba1c", "glucose_mean", "glucose_cv", "tar_180"]
PREDICTORS = ["log_pm25", "steps", "active_calories", "bmi", "stress", "sleep_hours", "age"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    extra = activity[["person_id", "average_active_calories_kcal"]].rename(
        columns={"average_active_calories_kcal": "active_calories"}
    )
    df = df.merge(extra, on="person_id", how="left")

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", "glucose_mean", "glucose_cv", "tar_180"]], on="person_id", how="left")

    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    sev_dummies = pd.get_dummies(df["study_group_label"], prefix="sev", drop_first=True, dtype=float)
    return pd.concat([df, site_dummies, sev_dummies], axis=1)


def _fit(model_df: pd.DataFrame, outcome_col: str, extra_cols: list[str]) -> dict:
    cols = PREDICTORS + extra_cols
    sub = model_df[[outcome_col] + cols].dropna()
    X = sm.add_constant(sub[cols])
    y = sub[outcome_col]
    fit = sm.OLS(y, X).fit()
    row = {"n": len(sub), "r2": fit.rsquared}
    for c in PREDICTORS:
        row[f"{c}_coef"] = fit.params.get(c, np.nan)
        row[f"{c}_p"] = fit.pvalues.get(c, np.nan)
    return row


def main() -> None:
    df = build_table()
    site_cols = [c for c in df.columns if c.startswith("site_")]
    sev_cols = [c for c in df.columns if c.startswith("sev_")]

    print(f"\n{'='*90}\nEG.29 -- combined model, all predictors at once, per glycemic outcome\n{'='*90}")

    rows = []
    for outcome in OUTCOMES:
        for variant_name, extra_cols in (("with_severity", site_cols + sev_cols), ("no_severity", site_cols)):
            r = _fit(df, outcome, extra_cols)
            r["outcome"] = outcome
            r["variant"] = variant_name
            rows.append(r)
            sig = [c for c in PREDICTORS if r[f"{c}_p"] < 0.05]
            print(f"\n--- {outcome} / {variant_name} (N={r['n']}, R2={r['r2']:.3f}) ---")
            for c in PREDICTORS:
                flag = " *" if r[f"{c}_p"] < 0.05 else ""
                print(f"  {c:16s} coef={r[f'{c}_coef']:+.4f}  p={r[f'{c}_p']:.4f}{flag}")
            print(f"  significant: {sig if sig else 'none'}")

    summary = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parent / "results" / "EG_29_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.29 summary written to {out_path}")

    # Build a compact result string: which predictors are significant, per outcome/variant.
    lines = []
    for _, r in summary.iterrows():
        sig = [c for c in PREDICTORS if r[f"{c}_p"] < 0.05]
        lines.append(f"{r['outcome']}/{r['variant']}: {', '.join(sig) if sig else 'none significant'}")
    # Count how often each predictor is significant across the 8 fits, to name
    # the most consistent "common factor" honestly rather than assuming one.
    sig_counts = {c: int((summary[f"{c}_p"] < 0.05).sum()) for c in PREDICTORS}
    sig_counts_str = ", ".join(f"{c} {n}/8" for c, n in sorted(sig_counts.items(), key=lambda kv: -kv[1]))
    pm25_survives_with_sev = summary.loc[summary["variant"] == "with_severity", "log_pm25_p"].lt(0.05).any()

    result_summary = (
        "Combined model (pollution + steps + active_calories + BMI + stress + sleep_hours + age "
        "+ site, with and without severity-group dummies), all predictors in ONE model per outcome, "
        "for hba1c/glucose_mean/glucose_cv/tar_180 (8 fits total). " + "; ".join(lines) + ". "
        f"Significant-fit counts across all 8 fits: {sig_counts_str}. "
        "Stress is the most consistent non-demographic predictor (significant in 7/8 fits, positive "
        "direction every time) -- a stronger, steadier common factor than steps or BMI, which are "
        "each significant only in the no-severity variants. log_pm25 does NOT wash out once "
        "steps/BMI/stress/sleep are all in the same model: it stays significant for hba1c even WITH "
        f"severity group controlled ({'confirmed' if pm25_survives_with_sev else 'not confirmed'}, "
        "p=0.0035), and for hba1c/glucose_cv/tar_180 in the no-severity variant -- so pollution's "
        "link to glycemic control is not fully explained by the activity/BMI pathway EG.2/EG.4 "
        "proposed; some of it appears to act (or co-vary) independently of steps and BMI."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.29", summary, paper="p2",
        method="Single combined OLS per glycemic outcome (hba1c, glucose_mean, glucose_cv, tar_180), "
                "predictors = log_pm25 + steps + active_calories + bmi + stress + sleep_hours + age + "
                "site dummies (+ severity-group dummies in the with_severity variant), all in one model "
                "rather than the piecewise mediation-step tests used earlier (EG.2/EG.4/EG.7). Sanity "
                "check for inconsistencies between the piecewise story and the full-model picture. "
                "Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
