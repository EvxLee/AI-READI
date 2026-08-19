#!/usr/bin/env python3
"""EG.13 -- NOx in place of PM2.5. EG.14 -- VOC in place of PM2.5.

Project head's follow-up (2026-08-18) to EG.7/EG.8: repeat the no-severity
primary model and per-site check, but with NOx and VOC as the
environmental term instead of PM2.5. Same predictor set, same 4 candidate
outcomes, same "no severity" design as EG.7a, same per-site refit as EG.8.
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

CANDIDATE_OUTCOMES = ["glucose_mean", "glucose_cv", "tar_180", "spikes_per_day_180"]

# (experiment ID, raw column, log-transformed column name)
POLLUTANTS = [
    ("EG.13", "mean_nox", "log_nox"),
    ("EG.14", "mean_voc", "log_voc"),
]

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
        env[["person_id", "mean_temp", "mean_hum", "mean_light", "mean_nox", "mean_voc"]],
        on="person_id", how="left",
    )
    df["log_nox"] = np.log1p(df["mean_nox"])
    df["log_voc"] = np.log1p(df["mean_voc"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", *CANDIDATE_OUTCOMES]], on="person_id", how="left")
    return df


def run_pollutant(df: pd.DataFrame, exp_id: str, pollutant_col: str) -> None:
    predictors = [pollutant_col] + OTHER_PREDICTORS
    print(f"\n{'='*90}\n{exp_id} -- pooled: glycemic control ~ {pollutant_col} + other predictors, no severity\n{'='*90}")

    pooled_p: dict[str, float] = {}
    pooled_rows = []
    for outcome in CANDIDATE_OUTCOMES:
        model_df = df[[outcome] + predictors].dropna()
        n = len(model_df)
        X = sm.add_constant(model_df.drop(columns=outcome))
        y = model_df[outcome]
        fit = sm.OLS(y, X).fit()
        p, coef = fit.pvalues[pollutant_col], fit.params[pollutant_col]
        pooled_p[outcome] = p
        print(f"\n--- outcome = {outcome}  (N={n}, R2={fit.rsquared:.3f}) ---")
        print(f"  {pollutant_col}: coef={coef:.4f}, p={p:.4g}")
        pooled_rows.append({"outcome": outcome, "n": n, "r2": fit.rsquared, "coef": coef, "p_value": p})

    pooled_summary = pd.DataFrame(pooled_rows)
    pooled_sig = pooled_summary[pooled_summary["p_value"] < 0.05]
    pooled_sig_list = ", ".join(f"{r.outcome} (p={r.p_value:.3g})" for r in pooled_sig.itertuples())
    results.save(
        f"{exp_id}a", pooled_summary, paper="p2",
        method=f"OLS, pooled, no severity-group dummies: glycemic control ~ {pollutant_col} + "
                f"other env vars + BMI + wearables + age + site dummies.",
        result=f"{pollutant_col} significant (p<0.05) for: {pooled_sig_list if pooled_sig_list else 'none'}.",
        decision="keep",
    )

    print(f"\n{'='*90}\n{exp_id}b -- per-site refit\n{'='*90}")
    site_rows = []
    for site in SITES:
        sub = df[df["clinical_site"] == site]
        for outcome in CANDIDATE_OUTCOMES:
            model_df = sub[[outcome] + predictors].dropna()
            n = len(model_df)
            if n < 30:
                continue
            X = sm.add_constant(model_df.drop(columns=outcome))
            y = model_df[outcome]
            fit = sm.OLS(y, X).fit()
            p, coef = fit.pvalues[pollutant_col], fit.params[pollutant_col]
            print(f"  site={site}, outcome={outcome} (N={n}): {pollutant_col} coef={coef:.4f}, p={p:.4g}")
            site_rows.append({
                "site": site, "outcome": outcome, "n": n, "r2": fit.rsquared,
                "coef": coef, "p_value": p, "p_value_pooled": pooled_p[outcome],
            })

    site_summary = pd.DataFrame(site_rows)
    site_sig = site_summary[site_summary["p_value"] < 0.05]
    site_sig_list = ", ".join(f"{r.site}/{r.outcome} (p={r.p_value:.3g})" for r in site_sig.itertuples())
    result_summary = (
        f"Pooled: {pollutant_col} significant for {pooled_sig_list if pooled_sig_list else 'none'}. "
        f"Per-site: significant for {site_sig_list if site_sig_list else 'none'}."
    )
    print(f"\n{result_summary}")
    results.save(
        f"{exp_id}b", site_summary, paper="p2",
        method=f"OLS, per-site (no pooling), no severity-group dummies: glycemic control ~ "
                f"{pollutant_col} + other env vars + BMI + wearables + age, refit within each site.",
        result=result_summary,
        decision="keep",
    )

    results.save(
        exp_id, pd.concat([pooled_summary.assign(scope="pooled"), site_summary.assign(scope="per_site")], ignore_index=True),
        paper="p2",
        method=f"Combined pooled + per-site test of {pollutant_col} (in place of PM2.5) against "
                f"the same no-severity primary-model design as EG.7a/EG.8.",
        result=result_summary,
        decision="keep",
    )


def main() -> None:
    df = build_table()
    for exp_id, _raw_col, log_col in POLLUTANTS:
        run_pollutant(df, exp_id, log_col)


if __name__ == "__main__":
    main()
