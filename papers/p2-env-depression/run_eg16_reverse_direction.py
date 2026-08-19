#!/usr/bin/env python3
"""EG.16 -- reverse direction: does glycemic control predict pollution exposure?

Project head's follow-up (2026-08-18): "what if you also went the reverse
direction and used CGM to predict pollution, covariate BMI, just so we can
compare that to use hemoglobin [A1c]... even if it's not the best link,
it's still some kind of finding if good."

This is explicitly exploratory/correlational, not a causal claim --
pollution exposure isn't plausibly caused by someone's blood sugar. Read
as "which glycemic marker co-varies most with exposure," not a mechanism
test. Two variants of the glycemic predictor, same log1p(PM2.5) outcome,
same BMI + age + site covariates:

  (a) CGM-derived metrics: glucose_mean, glucose_cv,
      intraday_glucose_variance, interday_glucose_variance
  (b) HbA1c (cohort.build_core_table()'s `hba1c`), for comparison against
      (a) -- does the standard clinical marker do better or worse than the
      richer CGM metrics at "explaining" pollution exposure?
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"
VARIABILITY_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "glucose_variability_metrics.csv"

GLYCEMIC_PREDICTORS = ["glucose_mean", "glucose_cv", "intraday_glucose_variance", "interday_glucose_variance", "hba1c"]
BASE_COVARIATES = ["bmi", "age"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", "glucose_mean", "glucose_cv"]], on="person_id", how="left")

    var_table = pd.read_csv(VARIABILITY_TABLE, dtype={"person_id": str})
    df = df.merge(
        var_table[["person_id", "intraday_glucose_variance", "interday_glucose_variance"]],
        on="person_id", how="left",
    )
    return df


def main() -> None:
    df = build_table()
    print(f"\n{'='*90}\nEG.16 -- reverse direction: log(PM2.5) ~ glycemic marker + bmi + age + site\n{'='*90}")

    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    rows = []
    for predictor in GLYCEMIC_PREDICTORS:
        predictors = [predictor] + BASE_COVARIATES
        model_df = pd.concat([df[["log_pm25"] + predictors], site_dummies], axis=1).dropna()
        n = len(model_df)

        X = sm.add_constant(model_df.drop(columns="log_pm25"))
        y = model_df["log_pm25"]
        fit = sm.OLS(y, X).fit()

        p, coef = fit.pvalues[predictor], fit.params[predictor]
        print(f"\n--- glycemic predictor = {predictor}  (N={n}, R2={fit.rsquared:.3f}) ---")
        print(f"  {predictor}: coef={coef:.6f}, p={p:.4g}")

        rows.append({
            "glycemic_predictor": predictor, "n": n, "r2": fit.rsquared,
            "coef": coef, "p_value": p,
        })

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_16_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.16 summary written to {summary_path}")
    print(summary.round(6).to_string(index=False))

    sig = summary[summary["p_value"] < 0.05]
    sig_list = ", ".join(f"{r.glycemic_predictor} (p={r.p_value:.3g})" for r in sig.itertuples())
    result_summary = (
        f"Reverse-direction (log(PM2.5) ~ glycemic marker + bmi + age + site), exploratory/"
        f"correlational only. Significant (p<0.05): {sig_list if sig_list else 'none'}. "
        f"hba1c p={summary.loc[summary['glycemic_predictor']=='hba1c','p_value'].values[0]:.3g}, "
        f"for comparison against the CGM-derived metrics."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.16", summary, paper="p2",
        method="OLS, exploratory/correlational (not causal): log1p(PM2.5) ~ glycemic_predictor + "
                "bmi + age + site dummies, run separately for each glycemic_predictor in "
                "{glucose_mean, glucose_cv, intraday_glucose_variance, interday_glucose_variance, "
                "hba1c}. Tests which glycemic marker co-varies most with pollution exposure, per "
                "project head's request; pollution is not plausibly caused by blood sugar, so this "
                "is read as a correlational comparison, not a mechanism test.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
