#!/usr/bin/env python3
"""EG.15 -- pollution vs. the new intraday/interday glucose variability metrics.

Project head's follow-up (2026-08-18): repeat the pollution tests using
EG.12's new within-day (intraday_glucose_variance) and between-day
(interday_glucose_variance) metrics as outcomes, alongside PM2.5, NOx, and
VOC as the environmental predictor. Same no-severity design as
EG.7a/EG.13/EG.14, pooled + per-site.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables
from aireadi.constants import SITES

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
VARIABILITY_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "glucose_variability_metrics.csv"

NEW_OUTCOMES = ["intraday_glucose_variance", "interday_glucose_variance"]
POLLUTANTS = [("PM2.5", "log_pm25", "mean_pm25"), ("NOx", "log_nox", "mean_nox"), ("VOC", "log_voc", "mean_voc")]

OTHER_PREDICTORS = [
    "mean_temp", "mean_hum", "mean_light", "bmi", "steps", "stress",
    "heart_rate", "sleep_hours", "active_calories", "age",
]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    extra = activity[["person_id", "average_active_calories_kcal"]].rename(
        columns={"average_active_calories_kcal": "active_calories"}
    )
    df = df.merge(extra, on="person_id", how="left")

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(
        env[["person_id", "mean_temp", "mean_hum", "mean_light", "mean_pm25", "mean_nox", "mean_voc"]],
        on="person_id", how="left",
    )
    df["log_pm25"] = np.log1p(df["mean_pm25"])
    df["log_nox"] = np.log1p(df["mean_nox"])
    df["log_voc"] = np.log1p(df["mean_voc"])

    var_table = pd.read_csv(VARIABILITY_TABLE, dtype={"person_id": str})
    df = df.merge(var_table[["person_id", *NEW_OUTCOMES]], on="person_id", how="left")
    return df


def main() -> None:
    df = build_table()
    all_rows = []

    for pollutant_name, log_col, _raw_col in POLLUTANTS:
        predictors = [log_col] + OTHER_PREDICTORS
        print(f"\n{'='*90}\nEG.15 -- {pollutant_name} vs. intraday/interday glucose variability\n{'='*90}")

        for outcome in NEW_OUTCOMES:
            model_df = df[[outcome] + predictors].dropna()
            n = len(model_df)
            X = sm.add_constant(model_df.drop(columns=outcome))
            y = model_df[outcome]
            fit = sm.OLS(y, X).fit()
            p, coef = fit.pvalues[log_col], fit.params[log_col]
            print(f"\n--- pooled: outcome={outcome}  (N={n}, R2={fit.rsquared:.3f}) ---")
            print(f"  {log_col}: coef={coef:.4f}, p={p:.4g}")
            all_rows.append({
                "pollutant": pollutant_name, "scope": "pooled", "site": "all",
                "outcome": outcome, "n": n, "r2": fit.rsquared, "coef": coef, "p_value": p,
            })

            for site in SITES:
                sub = df[df["clinical_site"] == site]
                site_model_df = sub[[outcome] + predictors].dropna()
                sn = len(site_model_df)
                if sn < 30:
                    continue
                sX = sm.add_constant(site_model_df.drop(columns=outcome))
                sy = site_model_df[outcome]
                sfit = sm.OLS(sy, sX).fit()
                sp, scoef = sfit.pvalues[log_col], sfit.params[log_col]
                print(f"  site={site}: N={sn}, coef={scoef:.4f}, p={sp:.4g}")
                all_rows.append({
                    "pollutant": pollutant_name, "scope": "per_site", "site": site,
                    "outcome": outcome, "n": sn, "r2": sfit.rsquared, "coef": scoef, "p_value": sp,
                })

    summary = pd.DataFrame(all_rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_15_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.15 summary written to {summary_path}")
    print(summary.round(4).to_string(index=False))

    sig = summary[summary["p_value"] < 0.05]
    sig_list = ", ".join(
        f"{r.pollutant}/{r.scope}"
        + (f"/{r.site}" if r.scope == "per_site" else "")
        + f"/{r.outcome} (p={r.p_value:.3g})"
        for r in sig.itertuples()
    )
    result_summary = (
        f"Across 3 pollutants x 2 new variability outcomes x (pooled + 3 sites), significant "
        f"(p<0.05) for: {sig_list if sig_list else 'none'}. See EG_15_summary.csv for full detail."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.15", summary, paper="p2",
        method="OLS, no severity-group dummies: intraday_glucose_variance / interday_glucose_variance "
                "~ log(pollutant) + other env vars + BMI + wearables + age (+ site dummies pooled, "
                "or refit per-site). Pollutant = PM2.5, NOx, or VOC.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
