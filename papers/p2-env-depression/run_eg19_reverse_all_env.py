#!/usr/bin/env python3
"""EG.19 -- reverse direction, swapping the outcome across all environmental metrics.

Project head's follow-up (2026-08-19): "were you able to run the model
swapping the outcome to be different environmental metrics and the input
CGM features + covariates? I obviously don't mean the new CGM features I
just told you about" -- i.e. extend EG.16 (which only used PM2.5 as the
outcome) to also test NOx, VOC, temperature, humidity, and light as
outcomes, using EG.16's original (pre-EG.17) CGM predictor set:
glucose_mean, glucose_cv, intraday_glucose_variance,
interday_glucose_variance, hba1c -- NOT the EG.17 5-level range features.

Same exploratory/correlational framing as EG.16: environmental exposure
isn't plausibly caused by blood sugar, so this is read as "which glycemic
marker co-varies most with which exposure metric," not a mechanism test.
6 environmental outcomes x 5 glycemic predictors = 30 fits.
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

# (outcome column name, raw env column, whether to log1p-transform)
ENV_OUTCOMES = [
    ("log_pm25", "mean_pm25", True),
    ("log_nox", "mean_nox", True),
    ("log_voc", "mean_voc", True),
    ("mean_temp", "mean_temp", False),
    ("mean_hum", "mean_hum", False),
    ("mean_light", "mean_light", False),
]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(
        env[["person_id", "mean_pm25", "mean_nox", "mean_voc", "mean_temp", "mean_hum", "mean_light"]],
        on="person_id", how="left",
    )
    df["log_pm25"] = np.log1p(df["mean_pm25"])
    df["log_nox"] = np.log1p(df["mean_nox"])
    df["log_voc"] = np.log1p(df["mean_voc"])

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
    print(f"\n{'='*90}\nEG.19 -- reverse direction across all environmental outcomes\n{'='*90}")

    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    rows = []
    for env_col, _raw_col, _is_log in ENV_OUTCOMES:
        for predictor in GLYCEMIC_PREDICTORS:
            predictors = [predictor] + BASE_COVARIATES
            model_df = pd.concat([df[[env_col] + predictors], site_dummies], axis=1).dropna()
            n = len(model_df)

            X = sm.add_constant(model_df.drop(columns=env_col))
            y = model_df[env_col]
            fit = sm.OLS(y, X).fit()

            p, coef = fit.pvalues[predictor], fit.params[predictor]
            flag = " ***" if p < 0.05 else ""
            print(f"  outcome={env_col:12s} predictor={predictor:28s} N={n:5d}  coef={coef:12.6f}  p={p:.4g}{flag}")

            rows.append({
                "env_outcome": env_col, "glycemic_predictor": predictor, "n": n,
                "r2": fit.rsquared, "coef": coef, "p_value": p,
            })

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_19_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.19 summary written to {summary_path} ({len(summary)} fits)")

    sig = summary[summary["p_value"] < 0.05].sort_values("p_value")
    print(f"\n{'='*90}\nEG.19 -- significant (p<0.05) results\n{'='*90}")
    print(sig.round(6).to_string(index=False))

    sig_list = ", ".join(
        f"{r.env_outcome}~{r.glycemic_predictor} (p={r.p_value:.3g})" for r in sig.itertuples()
    )
    result_summary = (
        f"{len(summary)} fits (6 environmental outcomes x 5 glycemic predictors, EG.16's original "
        f"pre-EG.17 CGM feature set). {len(sig)} significant at p<0.05: "
        f"{sig_list if sig_list else 'none'}. Exploratory/correlational only, per EG.16's framing."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.19", summary, paper="p2",
        method="OLS, exploratory/correlational (not causal): environmental_metric ~ "
                "glycemic_predictor + bmi + age + site dummies, for each of 6 environmental "
                "outcomes (PM2.5, NOx, VOC, temp, humidity, light) x 5 glycemic predictors "
                "(glucose_mean, glucose_cv, intraday/interday variance, hba1c) -- extends EG.16 "
                "(which only tested PM2.5 as the outcome) across all environmental metrics, using "
                "the same pre-EG.17 CGM predictor set (not the new 5-level range features).",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
