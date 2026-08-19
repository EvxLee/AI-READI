#!/usr/bin/env python3
"""EG.21 -- BMI vs. all three pollutants (PM2.5, NOx, VOC), pooled + per-site.

EG.2/EG.3 (2026-08-15) tested BMI as an outcome of pollution, but only for
PM2.5. Project head asked (2026-08-19) "did you also investigate BMI vs
pollution/air quality?" -- this completes that by extending the same test
to NOx and VOC, matching EG.13/EG.14's pattern (which did this same
extension for the glycemic-control outcomes, not BMI).

Same predictor set as EG.2/EG.3 (age + other env vars + wearables), minus
`bmi` itself since it's now the outcome. Pooled (with site dummies) +
per-site (no pooling), same as every other pollutant-comparison script in
this series.
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

OTHER_PREDICTORS = ["mean_temp", "mean_hum", "mean_light", "steps", "stress", "heart_rate", "sleep_hours", "active_calories", "age"]


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
    print(f"\n{'='*90}\nEG.21 -- BMI ~ pollutant + covariates, pooled + per-site, all 3 pollutants\n{'='*90}")

    rows = []
    for pollutant_name, log_col, _raw_col in POLLUTANTS:
        predictors = [log_col] + OTHER_PREDICTORS
        site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
        model_df = pd.concat([df[["bmi"] + predictors], site_dummies], axis=1).dropna()
        n = len(model_df)
        X = sm.add_constant(model_df.drop(columns="bmi"))
        y = model_df["bmi"]
        fit = sm.OLS(y, X).fit()
        p, coef = fit.pvalues[log_col], fit.params[log_col]
        print(f"\n--- pooled: {pollutant_name}  (N={n}, R2={fit.rsquared:.3f}) ---")
        print(f"  {log_col}: coef={coef:.4f}, p={p:.4g}")
        rows.append({"pollutant": pollutant_name, "scope": "pooled", "site": "all", "n": n, "r2": fit.rsquared, "coef": coef, "p_value": p})

        for site in SITES:
            sub = df[df["clinical_site"] == site]
            site_model_df = sub[["bmi"] + predictors].dropna()
            sn = len(site_model_df)
            if sn < 30:
                continue
            sX = sm.add_constant(site_model_df.drop(columns="bmi"))
            sy = site_model_df["bmi"]
            sfit = sm.OLS(sy, sX).fit()
            sp, scoef = sfit.pvalues[log_col], sfit.params[log_col]
            print(f"  site={site}: N={sn}, coef={scoef:.4f}, p={sp:.4g}")
            rows.append({"pollutant": pollutant_name, "scope": "per_site", "site": site, "n": sn, "r2": sfit.rsquared, "coef": scoef, "p_value": sp})

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_21_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.21 summary written to {summary_path}")
    print(summary.round(4).to_string(index=False))

    sig = summary[summary["p_value"] < 0.05]
    sig_list = ", ".join(
        f"{r.pollutant}/{r.scope}" + (f"/{r.site}" if r.scope == "per_site" else "") + f" (p={r.p_value:.3g})"
        for r in sig.itertuples()
    )
    result_summary = f"BMI ~ pollutant + covariates, all 3 pollutants, pooled + per-site. Significant (p<0.05): {sig_list if sig_list else 'none'}."
    print(f"\n{result_summary}")
    results.save(
        "EG.21", summary, paper="p2",
        method="OLS: bmi ~ log(pollutant) + other env vars + wearables + age (+ site dummies "
                "pooled, or refit per-site), for PM2.5, NOx, VOC. Completes EG.2/EG.3 (which only "
                "tested PM2.5) across all 3 pollutants -- direct answer to 'did you investigate "
                "BMI vs pollution/air quality?'",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
