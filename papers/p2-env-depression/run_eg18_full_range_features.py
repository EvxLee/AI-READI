#!/usr/bin/env python3
"""EG.18 -- pollution vs. the full EG.17 range-feature set (24 outcomes).

Runs all 24 features from `build_cgm_range_features.py` (5 ranges x 4
features each, plus 4 overall summary metrics) against all 3 pollutants
(PM2.5, NOx, VOC), pooled + per-site, using the same no-severity design
that revealed real effects in EG.7a/EG.13/EG.14/EG.15 (severity group was
shown in EG.7 to overcontrol for pollution's effect).

24 outcomes x 3 pollutants x 4 (pooled + 3 sites) = up to 288 fits.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables
from aireadi.constants import SITES

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
RANGE_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_range_features.csv"

RANGES = ["severe_hypo", "moderate_hypo", "normal", "moderate_hyper", "severe_hyper"]
RANGE_FEATURES = ["minutes_per_day", "fraction", "mean_glucose", "windows_per_day"]
OUTCOMES = [f"{r}_{f}" for r in RANGES for f in RANGE_FEATURES] + [
    "glucose_mean", "glucose_overall_variance", "glucose_mean_daily_variance", "glucose_cv_ratio",
]

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

    range_table = pd.read_csv(RANGE_TABLE, dtype={"person_id": str})
    df = df.merge(range_table[["person_id", *OUTCOMES]], on="person_id", how="left")
    return df


def fit_one(model_df: pd.DataFrame, outcome: str, log_col: str) -> tuple[int, float, float, float] | None:
    n = len(model_df)
    if n < 30:
        return None
    X = sm.add_constant(model_df.drop(columns=outcome))
    y = model_df[outcome]
    fit = sm.OLS(y, X).fit()
    return n, fit.rsquared, fit.params[log_col], fit.pvalues[log_col]


def main() -> None:
    df = build_table()
    all_rows = []

    for pollutant_name, log_col, _raw_col in POLLUTANTS:
        predictors = [log_col] + OTHER_PREDICTORS
        print(f"\n{'='*90}\nEG.18 -- {pollutant_name} vs. all 24 EG.17 outcomes\n{'='*90}")

        for outcome in OUTCOMES:
            model_df = df[[outcome] + predictors].dropna()
            res = fit_one(model_df, outcome, log_col)
            if res is None:
                continue
            n, r2, coef, p = res
            all_rows.append({
                "pollutant": pollutant_name, "scope": "pooled", "site": "all",
                "outcome": outcome, "n": n, "r2": r2, "coef": coef, "p_value": p,
            })
            flag = " ***" if p < 0.05 else ""
            print(f"  pooled  {outcome:35s} N={n:5d}  coef={coef:12.5f}  p={p:.4g}{flag}")

            for site in SITES:
                sub = df[df["clinical_site"] == site]
                site_model_df = sub[[outcome] + predictors].dropna()
                sres = fit_one(site_model_df, outcome, log_col)
                if sres is None:
                    continue
                sn, sr2, scoef, sp = sres
                all_rows.append({
                    "pollutant": pollutant_name, "scope": "per_site", "site": site,
                    "outcome": outcome, "n": sn, "r2": sr2, "coef": scoef, "p_value": sp,
                })
                sflag = " ***" if sp < 0.05 else ""
                print(f"    {site:5s} {outcome:33s} N={sn:5d}  coef={scoef:12.5f}  p={sp:.4g}{sflag}")

    summary = pd.DataFrame(all_rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_18_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.18 summary written to {summary_path} ({len(summary)} fits)")

    sig = summary[summary["p_value"] < 0.05].sort_values("p_value")
    print(f"\n{'='*90}\nEG.18 -- all significant (p<0.05) results, sorted by p-value\n{'='*90}")
    print(sig.round(5).to_string(index=False))

    pooled_sig = sig[sig["scope"] == "pooled"]
    replicated = []
    for (pollutant, outcome), grp in sig[sig["scope"] == "per_site"].groupby(["pollutant", "outcome"]):
        if len(grp) >= 2:
            replicated.append((pollutant, outcome, grp["site"].tolist()))

    pooled_list = ", ".join(f"{r.pollutant}/{r.outcome} (p={r.p_value:.3g})" for r in pooled_sig.itertuples())
    replicated_list = "; ".join(f"{p}/{o} at {sites}" for p, o, sites in replicated)
    result_summary = (
        f"{len(summary)} total fits (24 outcomes x 3 pollutants x pooled+3 sites). "
        f"{len(sig)} significant at p<0.05. Pooled-significant: {pooled_list if pooled_list else 'none'}. "
        f"Outcomes significant at >=2 sites independently (real cross-site replication): "
        f"{replicated_list if replicated_list else 'none'}."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.18", summary, paper="p2",
        method="OLS, no severity-group dummies: each of EG.17's 24 range/overall glucose features "
                "~ log(pollutant) + other env vars + BMI + wearables + age (+ site dummies pooled, "
                "or refit per-site). Pollutant = PM2.5, NOx, or VOC. Full grid, 288 fits max.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
