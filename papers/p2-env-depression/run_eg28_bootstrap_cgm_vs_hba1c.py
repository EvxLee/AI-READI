#!/usr/bin/env python3
"""EG.28 -- bootstrap significance test, CGM glucose variability vs HbA1c, predicting pollution.

Project head's follow-up (2026-08-26/27): "when comparing CGM vs. HbA1c
performance, make sure to include significance tests; even if you run the
model once with CGM and once with HbA1c, you can bootstrap the predictions
to get error bars; so please re-run with significance tests; i'm
particularly interested in blood glucose variability since that can be
measured [by] the CGM and not HbA1c."

EG.25 compared CGM-outcome models against the HbA1c-outcome model by eye,
using each fit's own p-value on the pollutant term -- exactly the flawed
comparison he's now correcting. This instead directly bootstraps the
DIFFERENCE between the two models' pollutant association strength, so the
"CGM beats HbA1c" (or doesn't) claim carries its own significance test.

Design: for each of PM2.5/NOx/VOC and each of 3 CGM variability metrics
that have no HbA1c equivalent (glucose_cv, intraday_glucose_variance,
glucose_overall_variance):
  1. Fit outcome ~ log(pollutant) + covariates via OLS, once with the CGM
     variability metric as outcome, once with hba1c as outcome, on the
     SAME rows (intersected non-null set) so the two models are directly
     comparable.
  2. Resample participants with replacement, B=1000 times. Each resample,
     refit both models on the identical resampled rows and record the
     |t-statistic| on the pollutant term for each -- |t| captures both
     effect size and precision in one number, more informative here than
     comparing R^2 or raw p-values across two different outcomes.
  3. The bootstrap distribution of (|t|_CGM - |t|_HbA1c) gives a 95%
     percentile CI and a two-sided bootstrap p-value on whether CGM's
     pollutant association is significantly stronger than HbA1c's.

Uses closed-form OLS (numpy) inside the bootstrap loop for speed --
statsmodels would be equivalent but ~50x slower over 1000 iterations x 9
pollutant/metric pairs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from aireadi import azure_io, cohort, results, wearables

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"
VAR_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "glucose_variability_metrics.csv"
RANGE_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_range_features.csv"

POLLUTANTS = [("PM2.5", "log_pm25"), ("NOx", "log_nox"), ("VOC", "log_voc")]
VARIABILITY_METRICS = ["glucose_cv", "intraday_glucose_variance", "glucose_overall_variance"]
OTHER_PREDICTORS = ["mean_temp", "mean_hum", "mean_light", "bmi", "steps", "stress",
                     "heart_rate", "sleep_hours", "active_calories", "age"]
N_BOOT = 1000
SEED = 20260827


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

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", "glucose_cv"]], on="person_id", how="left")
    var = pd.read_csv(VAR_TABLE, dtype={"person_id": str})
    df = df.merge(var[["person_id", "intraday_glucose_variance"]], on="person_id", how="left")
    rng = pd.read_csv(RANGE_TABLE, dtype={"person_id": str})
    df = df.merge(rng[["person_id", "glucose_overall_variance"]], on="person_id", how="left")

    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    return pd.concat([df, site_dummies], axis=1)


def ols_tstat(X: np.ndarray, y: np.ndarray, col_idx: int) -> float:
    """|t-statistic| on column `col_idx` of a closed-form OLS fit."""
    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    n, k = X.shape
    dof = max(n - k, 1)
    sigma2 = float(resid @ resid) / dof
    se = np.sqrt(sigma2 * XtX_inv[col_idx, col_idx])
    if se == 0 or np.isnan(se):
        return 0.0
    return abs(float(beta[col_idx]) / se)


def fit_pair(model_df: pd.DataFrame, log_col: str, cgm_col: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Return (X, y_cgm, y_hba1c, pollutant_col_idx) as plain numpy arrays."""
    site_cols = [c for c in model_df.columns if c.startswith("site_")]
    predictor_cols = [log_col] + OTHER_PREDICTORS + site_cols
    X = np.column_stack([np.ones(len(model_df))] + [model_df[c].values.astype(float) for c in predictor_cols])
    pollutant_col_idx = 1 + predictor_cols.index(log_col)
    y_cgm = model_df[cgm_col].values.astype(float)
    y_hba1c = model_df["hba1c"].values.astype(float)
    return X, y_cgm, y_hba1c, pollutant_col_idx


def main() -> None:
    df = build_table()
    rng_state = np.random.default_rng(SEED)
    print(f"\n{'='*90}\nEG.28 -- bootstrap CGM-variability vs HbA1c, pollutant association strength\n{'='*90}")
    print(f"N bootstrap resamples per pair: {N_BOOT}")

    rows = []
    for pollutant_name, log_col in POLLUTANTS:
        for cgm_col in VARIABILITY_METRICS:
            needed = [log_col, cgm_col, "hba1c"] + OTHER_PREDICTORS + [c for c in df.columns if c.startswith("site_")]
            model_df = df[needed].dropna().reset_index(drop=True)
            n = len(model_df)
            if n < 50:
                continue
            X, y_cgm, y_hba1c, pidx = fit_pair(model_df, log_col, cgm_col)

            t_cgm_obs = ols_tstat(X, y_cgm, pidx)
            t_hba1c_obs = ols_tstat(X, y_hba1c, pidx)

            diffs = np.empty(N_BOOT)
            for b in range(N_BOOT):
                idx = rng_state.integers(0, n, size=n)
                Xb, yb_cgm, yb_hba1c = X[idx], y_cgm[idx], y_hba1c[idx]
                t_cgm = ols_tstat(Xb, yb_cgm, pidx)
                t_hba1c = ols_tstat(Xb, yb_hba1c, pidx)
                diffs[b] = t_cgm - t_hba1c

            ci_lo, ci_hi = np.percentile(diffs, [2.5, 97.5])
            boot_p = 2 * min((diffs >= 0).mean(), (diffs <= 0).mean())
            boot_p = min(boot_p, 1.0)
            verdict = "CGM significantly stronger" if ci_lo > 0 else ("HbA1c significantly stronger" if ci_hi < 0 else "no significant difference")

            print(f"\n--- {pollutant_name} / {cgm_col} (N={n}) ---")
            print(f"  observed |t|: CGM={t_cgm_obs:.3f}, HbA1c={t_hba1c_obs:.3f}, diff={t_cgm_obs - t_hba1c_obs:.3f}")
            print(f"  bootstrap diff 95% CI: [{ci_lo:.3f}, {ci_hi:.3f}], bootstrap p={boot_p:.4f} -> {verdict}")

            rows.append({
                "pollutant": pollutant_name, "cgm_metric": cgm_col, "n": n,
                "t_cgm_observed": t_cgm_obs, "t_hba1c_observed": t_hba1c_obs,
                "diff_observed": t_cgm_obs - t_hba1c_obs,
                "boot_diff_mean": diffs.mean(), "boot_ci_lo": ci_lo, "boot_ci_hi": ci_hi,
                "boot_p_value": boot_p, "verdict": verdict,
            })

    summary = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parent / "results" / "EG_28_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.28 summary written to {out_path}")

    cgm_wins = summary[summary["verdict"] == "CGM significantly stronger"]
    hba1c_wins = summary[summary["verdict"] == "HbA1c significantly stronger"]
    cgm_wins_list = ", ".join(f"{r.pollutant}/{r.cgm_metric} (p={r.boot_p_value:.3g})" for r in cgm_wins.itertuples())
    hba1c_wins_list = ", ".join(f"{r.pollutant}/{r.cgm_metric} (p={r.boot_p_value:.3g})" for r in hba1c_wins.itertuples())
    result_summary = (
        f"Bootstrap ({N_BOOT} resamples) comparison of |t-statistic| on the pollutant term, CGM "
        f"variability metric (glucose_cv, intraday_glucose_variance, glucose_overall_variance) vs "
        f"hba1c as outcome, same rows, all 3 pollutants (9 pairs total). CGM significantly stronger: "
        f"{cgm_wins_list if cgm_wins_list else 'none'}. HbA1c significantly stronger: "
        f"{hba1c_wins_list if hba1c_wins_list else 'none'}. Remaining pairs: no significant difference. "
        f"This is the formal significance test EG.25 was missing -- a direct bootstrap on the "
        f"CGM-vs-HbA1c difference itself, not a side-by-side read of two separate p-values."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.28", summary, paper="p2",
        method="Bootstrap (1000 resamples, participant-level with replacement) comparison of the "
                "|t-statistic| on the pollutant term between an OLS model with a CGM glucose-"
                "variability metric as outcome and an OLS model with hba1c as outcome (same rows, "
                "same covariates: other env vars + BMI + wearables + age + site dummies), for PM2.5, "
                "NOx, VOC x glucose_cv, intraday_glucose_variance, glucose_overall_variance. Gives a "
                "95% CI and bootstrap p-value on whether CGM's pollutant association is significantly "
                "stronger than HbA1c's, focused on variability metrics HbA1c cannot capture at all.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
