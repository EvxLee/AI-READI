#!/usr/bin/env python3
"""EG.36 -- PM2.5/BMI vs blood sugar, re-stratified into 2 diabetic-status groups.

Project-head follow-up (2026-09-06): EG.35's 4-way severity-group split
(Healthy/Pre-DM/Oral Med/Insulin) was underpowered -- only 5/32 fits
significant, plausibly because splitting 2280 people 4 ways left too few
per group. His ask: rerun with 2 groups instead -- non-diabetic (Healthy
+ Pre-DM) vs. diabetic-on-treatment (Oral Med + Insulin) -- to see whether
the signal comes back once each group has roughly double the N.

Same design as EG.35 otherwise: PM2.5 and BMI each net of the other,
+ age + site dummies, across hba1c/glucose_cv/tar_180/interday_glucose_variance.
Global and age-band results are unchanged from EG.35 (not rerun here --
only the severity split changes); this script reruns the global fits too,
for a single self-contained comparison table.
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

# The 2-group collapse the project head asked for.
DIABETIC_STATUS_MAP = {
    "Healthy": "non-diabetic (Healthy+Pre-DM)",
    "Pre-DM": "non-diabetic (Healthy+Pre-DM)",
    "Oral Med": "diabetic-treated (Oral Med+Insulin)",
    "Insulin": "diabetic-treated (Oral Med+Insulin)",
}
GROUP2_ORDER = ["non-diabetic (Healthy+Pre-DM)", "diabetic-treated (Oral Med+Insulin)"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", "glucose_cv", "tar_180"]], on="person_id", how="left")
    var = pd.read_csv(VAR_TABLE, dtype={"person_id": str})
    df = df.merge(var[["person_id", "interday_glucose_variance"]], on="person_id", how="left")

    df["diabetic_status_2group"] = df["study_group_label"].astype(str).map(DIABETIC_STATUS_MAP)
    return df


def _fit_one(sub: pd.DataFrame, predictor: str, other_predictor: str, outcome: str, extra_cols: list[str]) -> dict | None:
    cols = [predictor, other_predictor, outcome] + extra_cols
    fit_df = sub[cols].dropna()
    if len(fit_df) < 30:
        return None
    X_cols = [predictor, other_predictor] + extra_cols
    X = fit_df[X_cols]
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
    predictors = [("log_pm25", "bmi"), ("bmi", "log_pm25")]

    print(f"\n{'='*90}\nEG.36 -- PM2.5 & BMI vs blood sugar, 2-group diabetic-status split\n{'='*90}")
    print("Group sizes:", df["diabetic_status_2group"].value_counts().to_dict())

    rows = []
    print("\n--- Global (pooled, age + site as covariates) ---")
    for predictor, other in predictors:
        for outcome in OUTCOMES:
            r = _fit_one(df, predictor, other, outcome, ["age"] + site_cols)
            if r is None:
                continue
            rows.append({"stratum_type": "global", "stratum": "all", "predictor": predictor, "outcome": outcome, **r})
            flag = " *" if r["p"] < 0.05 else ""
            print(f"  {predictor:10s} -> {outcome:26s} N={r['n']:4d}  coef={r['coef']:+.4f}  p={r['p']:.4f}{flag}")

    print("\n--- By 2-group diabetic status ---")
    for group in GROUP2_ORDER:
        sub = df[df["diabetic_status_2group"] == group]
        for predictor, other in predictors:
            for outcome in OUTCOMES:
                r = _fit_one(sub, predictor, other, outcome, ["age"] + site_cols)
                if r is None:
                    continue
                rows.append({"stratum_type": "diabetic_status_2group", "stratum": group, "predictor": predictor, "outcome": outcome, **r})
                flag = " *" if r["p"] < 0.05 else ""
                print(f"  {group:38s} {predictor:10s} -> {outcome:26s} N={r['n']:4d}  coef={r['coef']:+.4f}  p={r['p']:.4f}{flag}")

    summary = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parent / "results" / "EG_36_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.36 summary written to {out_path}")

    def _sig_list(sub_df: pd.DataFrame) -> str:
        sig = sub_df[sub_df["p"] < 0.05]
        return ", ".join(f"{r.stratum}/{r.predictor}/{r.outcome} (p={r.p:.3g})" for r in sig.itertuples()) or "none"

    glob = summary[summary["stratum_type"] == "global"]
    grp2 = summary[summary["stratum_type"] == "diabetic_status_2group"]
    eg35_path = Path(__file__).resolve().parent / "results" / "EG_35_summary.csv"
    eg35 = pd.read_csv(eg35_path)
    eg35_sev = eg35[eg35["stratum_type"] == "severity_group"]
    n_sig_4group = int((eg35_sev["p"] < 0.05).sum())

    result_summary = (
        f"Global (unchanged from EG.35, rerun for a self-contained table): {int((glob['p'] < 0.05).sum())}/8 "
        f"significant. 2-group diabetic-status split (non-diabetic = Healthy+Pre-DM, N="
        f"{int(df['diabetic_status_2group'].eq(GROUP2_ORDER[0]).sum())}; diabetic-treated = Oral Med+Insulin, "
        f"N={int(df['diabetic_status_2group'].eq(GROUP2_ORDER[1]).sum())}): "
        f"{int((grp2['p'] < 0.05).sum())}/{len(grp2)} significant: {_sig_list(grp2)}. "
        f"Compares to EG.35's 4-way severity split, which found {n_sig_4group}/32 significant. "
        f"{'The 2-group split recovers more signal, confirming the 4-way split was underpowered.' if int((grp2['p'] < 0.05).sum()) > n_sig_4group else 'The 2-group split does NOT recover materially more signal than the 4-way split -- the weak 4-way result was not primarily a sample-size artifact.'}"
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.36", summary, paper="p2",
        method="Rerun of EG.35's design (PM2.5 and BMI, each net of the other + age + site, across "
                "hba1c/glucose_cv/tar_180/interday_glucose_variance), with the severity-group split "
                "collapsed from 4 groups to 2 (non-diabetic = Healthy+Pre-DM; diabetic-treated = Oral "
                "Med+Insulin), per project-head request to test whether EG.35's weak 4-way severity "
                "split was a sample-size artifact. Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
