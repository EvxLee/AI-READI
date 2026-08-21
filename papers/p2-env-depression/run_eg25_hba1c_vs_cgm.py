#!/usr/bin/env python3
"""EG.25 -- does CGM track pollution better than HbA1c?

Project head's follow-up (2026-08-21): "whatever models that have been
run, you can replace the cgm metrics with hemoglobin as some comparison,
ex: maybe cgm tracks with pollution better than hemoglobin does, would be
interesting because suggests based on someones cgm data we can tell this
person is in a more polluted environment... hopefully cgm is better."

Reruns the same no-severity design as EG.7a/EG.13/EG.14 (pollution ~
glycemic outcome + env vars + BMI + wearables + age), but with `hba1c` as
the single outcome instead of the 4 CGM-derived metrics, across all 3
pollutants, pooled + per-site. Result gets compared directly against the
existing CGM-based p-values for the same pollutant/scope combinations.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables
from aireadi.constants import SITES

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"

POLLUTANTS = [("PM2.5", "log_pm25", "mean_pm25"), ("NOx", "log_nox", "mean_nox"), ("VOC", "log_voc", "mean_voc")]
OTHER_PREDICTORS = ["mean_temp", "mean_hum", "mean_light", "bmi", "steps", "stress", "heart_rate", "sleep_hours", "active_calories", "age"]

# EG.7a/EG.13/EG.14's best (lowest) pooled CGM-outcome p-value per pollutant, for direct comparison.
BEST_CGM_POOLED_P = {"PM2.5": 0.0061, "NOx": 0.051, "VOC": 0.083}  # glucose_cv for PM2.5/NOx, spikes_per_day_180 for VOC


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
    return df


def main() -> None:
    df = build_table()
    print(f"\n{'='*90}\nEG.25 -- hba1c ~ pollutant + covariates, pooled + per-site, all 3 pollutants\n{'='*90}")

    rows = []
    for pollutant_name, log_col, _raw_col in POLLUTANTS:
        predictors = [log_col] + OTHER_PREDICTORS
        site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
        model_df = pd.concat([df[["hba1c"] + predictors], site_dummies], axis=1).dropna()
        n = len(model_df)
        X = sm.add_constant(model_df.drop(columns="hba1c"))
        y = model_df["hba1c"]
        fit = sm.OLS(y, X).fit()
        p, coef = fit.pvalues[log_col], fit.params[log_col]
        cgm_p = BEST_CGM_POOLED_P[pollutant_name]
        print(f"\n--- pooled: {pollutant_name}  (N={n}, R2={fit.rsquared:.3f}) ---")
        print(f"  {log_col}: coef={coef:.4f}, p={p:.4g}  (best CGM-outcome pooled p was {cgm_p:.3g})")
        rows.append({
            "pollutant": pollutant_name, "scope": "pooled", "site": "all", "n": n, "r2": fit.rsquared,
            "coef": coef, "p_value": p, "best_cgm_outcome_pooled_p": cgm_p,
        })

        for site in SITES:
            sub = df[df["clinical_site"] == site]
            site_model_df = sub[["hba1c"] + predictors].dropna()
            sn = len(site_model_df)
            if sn < 30:
                continue
            sX = sm.add_constant(site_model_df.drop(columns="hba1c"))
            sy = site_model_df["hba1c"]
            sfit = sm.OLS(sy, sX).fit()
            sp, scoef = sfit.pvalues[log_col], sfit.params[log_col]
            print(f"  site={site}: N={sn}, coef={scoef:.4f}, p={sp:.4g}")
            rows.append({
                "pollutant": pollutant_name, "scope": "per_site", "site": site, "n": sn, "r2": sfit.rsquared,
                "coef": scoef, "p_value": sp, "best_cgm_outcome_pooled_p": cgm_p,
            })

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_25_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.25 summary written to {summary_path}")
    print(summary.round(5).to_string(index=False))

    sig = summary[summary["p_value"] < 0.05]
    sig_list = ", ".join(
        f"{r.pollutant}/{r.scope}" + (f"/{r.site}" if r.scope == "per_site" else "") + f" (p={r.p_value:.3g})"
        for r in sig.itertuples()
    )
    pooled = summary[summary["scope"] == "pooled"]
    cgm_wins = int((pooled["p_value"] > pooled["best_cgm_outcome_pooled_p"]).sum())
    result_summary = (
        f"hba1c ~ pollutant, pooled + per-site, all 3 pollutants. Significant (p<0.05): "
        f"{sig_list if sig_list else 'none'}. Pooled comparison against best CGM-outcome p-value "
        f"(from EG.7a/EG.13/EG.14): CGM had the lower (better) p-value in {cgm_wins}/3 pollutants "
        f"-- {'CGM tracks pollution better than HbA1c, as hoped' if cgm_wins >= 2 else 'HbA1c is not clearly worse than CGM at tracking pollution'}."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.25", summary, paper="p2",
        method="OLS: hba1c ~ log(pollutant) + other env vars + BMI + wearables + age (+ site "
                "dummies pooled, or refit per-site), for PM2.5, NOx, VOC. Same no-severity design "
                "as EG.7a/EG.13/EG.14 (which used CGM-derived outcomes) -- direct comparison to "
                "test whether CGM data tracks pollution exposure better than the standard clinical "
                "HbA1c marker.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
