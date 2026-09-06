#!/usr/bin/env python3
"""EG.35 -- PM2.5 and BMI vs. blood sugar (CGM + HbA1c), global + age/severity-stratified.

Project-head follow-up (2026-09-06, relayed): "did PM2.5 and/or BMI also
link to blood sugar in any way, either through CGM-derived metrics or
HbA1c? Either globally or after stratifying by age/diabetic status?"

The "globally" half is already answered across EG.1/4/7/15/18/25/29 --
this restates that record rather than re-running it. The
age/diabetic-status-stratified half is a genuine gap: every stratified
result run so far (EG.8, EG.24, EG.26) stratified by clinical SITE, and
EG.24 showed site is confounded with age and severity composition -- it
was never stratified by age band or severity group directly. This closes
that gap.

Design: for PM2.5 and BMI each, as the predictor of interest, fit
outcome ~ predictor + age + site dummies (+ the other of PM2.5/BMI as a
covariate, so each predictor's link is checked net of the other) within
each of:
  * 3 age bands (40-54/55-69/70+, EG.23's existing convention)
  * 4 severity groups (Healthy/Pre-DM/Oral Med/Insulin)
across 4 outcomes: hba1c, glucose_cv, tar_180, interday_glucose_variance
(the strongest CGM-variability finding from EG.15). Age is dropped as a
covariate within severity-group strata only when the stratum is an age
band already (age band strata still include site dummies).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import cohort, results

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"
VAR_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "glucose_variability_metrics.csv"

OUTCOMES = ["hba1c", "glucose_cv", "tar_180", "interday_glucose_variance"]
AGE_BINS = [40, 55, 70, 200]
AGE_LABELS = ["40-54", "55-69", "70+"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", "glucose_cv", "tar_180"]], on="person_id", how="left")
    var = pd.read_csv(VAR_TABLE, dtype={"person_id": str})
    df = df.merge(var[["person_id", "interday_glucose_variance"]], on="person_id", how="left")

    df["age_band"] = pd.cut(df["age"], bins=AGE_BINS, labels=AGE_LABELS, right=False)
    return df


def _fit_one(sub: pd.DataFrame, predictor: str, other_predictor: str, outcome: str, extra_cols: list[str]) -> dict | None:
    cols = [predictor, other_predictor, outcome] + extra_cols
    fit_df = sub[cols].dropna()
    if len(fit_df) < 30:
        return None
    X_cols = [predictor, other_predictor] + extra_cols
    X = fit_df[X_cols]
    # Drop any covariate column that's constant within this stratum (e.g. a
    # single-site stratum after site dummies) -- would otherwise make X singular.
    X = X.loc[:, X.nunique() > 1]
    if predictor not in X.columns:
        return None
    X = sm.add_constant(X)
    y = fit_df[outcome]
    fit = sm.OLS(y, X).fit()
    return {"n": len(fit_df), "coef": fit.params[predictor], "p": fit.pvalues[predictor]}


def main() -> None:
    df = build_table()
    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    df = pd.concat([df, site_dummies], axis=1)
    site_cols = list(site_dummies.columns)

    print(f"\n{'='*90}\nEG.35 -- PM2.5 & BMI vs blood sugar, global + age/severity-stratified\n{'='*90}")

    rows = []
    predictors = [("log_pm25", "bmi"), ("bmi", "log_pm25")]

    # ── Global (pooled, all 2280) ──
    print("\n--- Global (pooled, age + site as covariates) ---")
    for predictor, other in predictors:
        for outcome in OUTCOMES:
            r = _fit_one(df, predictor, other, outcome, ["age"] + site_cols)
            if r is None:
                continue
            rows.append({"stratum_type": "global", "stratum": "all", "predictor": predictor, "outcome": outcome, **r})
            flag = " *" if r["p"] < 0.05 else ""
            print(f"  {predictor:10s} -> {outcome:26s} N={r['n']:4d}  coef={r['coef']:+.4f}  p={r['p']:.4f}{flag}")

    # ── Age-band stratified ──
    print("\n--- By age band ---")
    for band in AGE_LABELS:
        sub = df[df["age_band"] == band]
        for predictor, other in predictors:
            for outcome in OUTCOMES:
                r = _fit_one(sub, predictor, other, outcome, site_cols)
                if r is None:
                    continue
                rows.append({"stratum_type": "age_band", "stratum": band, "predictor": predictor, "outcome": outcome, **r})
                flag = " *" if r["p"] < 0.05 else ""
                print(f"  {band:6s} {predictor:10s} -> {outcome:26s} N={r['n']:4d}  coef={r['coef']:+.4f}  p={r['p']:.4f}{flag}")

    # ── Severity-group stratified ──
    print("\n--- By severity group ---")
    for group in df["study_group_label"].cat.categories:
        sub = df[df["study_group_label"] == group]
        for predictor, other in predictors:
            for outcome in OUTCOMES:
                r = _fit_one(sub, predictor, other, outcome, ["age"] + site_cols)
                if r is None:
                    continue
                rows.append({"stratum_type": "severity_group", "stratum": group, "predictor": predictor, "outcome": outcome, **r})
                flag = " *" if r["p"] < 0.05 else ""
                print(f"  {group:10s} {predictor:10s} -> {outcome:26s} N={r['n']:4d}  coef={r['coef']:+.4f}  p={r['p']:.4f}{flag}")

    summary = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parent / "results" / "EG_35_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.35 summary written to {out_path}")

    def _sig_list(sub_df: pd.DataFrame) -> str:
        sig = sub_df[sub_df["p"] < 0.05]
        return ", ".join(f"{r.stratum}/{r.predictor}/{r.outcome} (p={r.p:.3g})" for r in sig.itertuples()) or "none"

    glob = summary[summary["stratum_type"] == "global"]
    age_strat = summary[summary["stratum_type"] == "age_band"]
    sev_strat = summary[summary["stratum_type"] == "severity_group"]

    result_summary = (
        f"Global (pooled, net of the other predictor + age + site): "
        f"{int((glob['p'] < 0.05).sum())}/{len(glob)} significant: {_sig_list(glob)}. "
        f"Age-band-stratified (40-54/55-69/70+, site as covariate): "
        f"{int((age_strat['p'] < 0.05).sum())}/{len(age_strat)} significant: {_sig_list(age_strat)}. "
        f"Severity-group-stratified (age + site as covariates): "
        f"{int((sev_strat['p'] < 0.05).sum())}/{len(sev_strat)} significant: {_sig_list(sev_strat)}. "
        f"This is the first time either link has been stratified by age band or severity group "
        f"directly (all prior stratification was by clinical site, which EG.24 showed is confounded "
        f"with age/severity composition)."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.35", summary, paper="p2",
        method="For PM2.5 and BMI each (net of the other, + age + site dummies), OLS on 4 glycemic "
                "outcomes (hba1c, glucose_cv, tar_180, interday_glucose_variance -- EG.15's strongest "
                "CGM-variability finding): globally (pooled), stratified by 3 age bands (EG.23's "
                "40-54/55-69/70+ convention), and stratified by the 4 severity groups. First "
                "age/severity-direct stratification of this link -- prior stratification (EG.8/24/26) "
                "was by clinical site only, which EG.24 showed confounds age and severity composition. "
                "Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
