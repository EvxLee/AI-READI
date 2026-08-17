#!/usr/bin/env python3
"""EG.8 -- per-site replication of EG.7a (the no-severity primary model).

EG.7 found that dropping severity-group dummies from the primary model
makes log(PM2.5) significant for 2 of 4 glycemic-control outcomes
(glucose_cv, tar_180), where it was null with severity included. Before
treating that as a real, generalizable finding, this checks whether it
holds at each of the 3 clinical sites individually, or is driven by one
site the way the EG.2/EG.3 mediation-link effect was (strongest at UW,
weak or absent elsewhere).

Same predictor set as EG.7a (log1p(PM2.5) + env vars + BMI + wearables +
age -- no severity, no site dummies since each site is fit separately),
refit within UW / UAB / UCSD.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables
from aireadi.constants import SITES

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"

PREDICTORS = [
    "log_pm25", "mean_temp", "mean_hum", "mean_light", "mean_voc", "mean_nox",
    "bmi", "steps", "stress", "heart_rate", "sleep_hours", "active_calories",
    "age",
]
CANDIDATE_OUTCOMES = ["glucose_mean", "glucose_cv", "tar_180", "spikes_per_day_180"]

# EG.7a's pooled (no-severity) p-values, for the side-by-side comparison.
EG7A_POOLED_PM25_P = {
    "glucose_mean": 0.1591, "glucose_cv": 0.0061, "tar_180": 0.0168, "spikes_per_day_180": 0.7881,
}


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
        env[["person_id", "mean_temp", "mean_hum", "mean_light", "mean_pm25", "mean_voc", "mean_nox"]],
        on="person_id", how="left",
    )
    df["log_pm25"] = np.log1p(df["mean_pm25"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", *CANDIDATE_OUTCOMES]], on="person_id", how="left")
    return df


def main() -> None:
    df = build_table()
    print(f"\n{'='*90}\nEG.8 -- per-site replication of EG.7a (no-severity primary model)\n{'='*90}")

    rows = []
    for site in SITES:
        sub = df[df["clinical_site"] == site]
        for outcome in CANDIDATE_OUTCOMES:
            model_df = sub[[outcome] + PREDICTORS].dropna()
            n = len(model_df)
            if n < 30:
                print(f"\n--- site={site}, outcome={outcome}: N={n}, too small to fit ---")
                continue

            X = sm.add_constant(model_df.drop(columns=outcome))
            y = model_df[outcome]
            fit = sm.OLS(y, X).fit()

            env_p = fit.pvalues["log_pm25"]
            env_coef = fit.params["log_pm25"]
            print(f"\n--- site={site}, outcome={outcome}  (N={n}, R2={fit.rsquared:.3f}) ---")
            print(f"  log_pm25: coef={env_coef:.4f}, p={env_p:.4g}")

            rows.append({
                "site": site, "outcome": outcome, "n": n, "r2": fit.rsquared,
                "log_pm25_coef": env_coef, "log_pm25_p": env_p,
                "log_pm25_p_pooled": EG7A_POOLED_PM25_P[outcome],
            })

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_8_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.8 summary written to {summary_path}")
    print(summary.round(4).to_string(index=False))

    sig = summary[summary["log_pm25_p"] < 0.05]
    sig_list = ", ".join(
        f"{r.site}/{r.outcome} (p={r.log_pm25_p:.3g}, coef={'+ ' if r.log_pm25_coef > 0 else '- '}{abs(r.log_pm25_coef):.4f})"
        for r in sig.itertuples()
    )
    result_summary = (
        f"log(PM2.5) significant (p<0.05) per-site for: {sig_list if sig_list else 'none'}. "
        f"Compare against EG.7a's pooled result (significant for glucose_cv p=0.0061, tar_180 "
        f"p=0.0168) -- a pooled-significant effect that doesn't replicate at any single site "
        f"means it is likely driven by between-site differences, not a real within-site effect."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.8", summary, paper="p2",
        method="OLS, EG.7a's no-severity predictor set refit separately within each of the 3 "
                "clinical sites (UW, UAB, UCSD). Checks whether EG.7a's pooled pollution effect "
                "on glycemic control replicates at each site or is driven by one site.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
