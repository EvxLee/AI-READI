#!/usr/bin/env python3
"""EG.2 (pooled) and EG.3 (per-site) -- pollution -> activity/BMI mediation step.

Project-head direction, 2026-08-15 (see PLAN.md / PRESPEC.md amendment):
EG.1 found log(PM2.5) not significant for any of 4 glycemic-control outcomes
once severity group is a covariate. The project head's read: pollution
likely doesn't act on blood sugar directly -- it may instead discourage
physical activity and raise BMI, which then worsens glycemic control.
Hypothesis chain: worse pollution -> less activity / higher BMI -> worse
blood sugar control.

This script tests the first link only: does PM2.5 predict activity (steps,
active_calories) and BMI, controlling for age (the primary requested
confounder)? Two versions, both requested explicitly:

* EG.2 -- pooled across all three clinical sites (UW, UAB, UCSD), with site
  as a covariate (dummy-coded) so the pooled estimate isn't confounded by
  between-site differences in both pollution and activity.
* EG.3 -- the same model refit separately within each site, since a pooled
  fixed-effect for site can mask an effect that only holds (or reverses) at
  one location -- "these versions both provide different useful
  information potentially" (project head, verbatim).

Outcome is regressed on log1p(PM2.5) + age (+ site dummies in EG.2 only).
This does not yet chain into the second link (activity/BMI -> glycemic
control) -- that's a natural EG.4 once this first link is characterized.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables
from aireadi.constants import SITES

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"

OUTCOMES = ["steps", "active_calories", "bmi"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    extra = activity[["person_id", "average_active_calories_kcal"]].rename(
        columns={"average_active_calories_kcal": "active_calories"}
    )
    df = df.merge(extra, on="person_id", how="left")

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])
    return df


def _fit(model_df: pd.DataFrame, outcome: str) -> dict:
    X = sm.add_constant(model_df.drop(columns=outcome))
    y = model_df[outcome]
    fit = sm.OLS(y, X).fit()
    return {
        "n": len(model_df),
        "r2": fit.rsquared,
        "log_pm25_coef": fit.params["log_pm25"],
        "log_pm25_p": fit.pvalues["log_pm25"],
        "age_coef": fit.params["age"],
        "age_p": fit.pvalues["age"],
    }


def run_eg2_pooled(df: pd.DataFrame) -> None:
    print(f"\n{'='*90}\nEG.2 -- pooled: activity/BMI ~ log(PM2.5) + age + site  (all 3 sites together)\n{'='*90}")

    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    rows = []
    for outcome in OUTCOMES:
        model_df = pd.concat([df[[outcome, "log_pm25", "age"]], site_dummies], axis=1).dropna()
        fit = _fit(model_df, outcome)
        print(f"\n--- outcome = {outcome}  (N={fit['n']}, R2={fit['r2']:.3f}) ---")
        print(f"  log_pm25: coef={fit['log_pm25_coef']:.4f}, p={fit['log_pm25_p']:.4g}")
        print(f"  age:      coef={fit['age_coef']:.4f}, p={fit['age_p']:.4g}")
        rows.append({"outcome": outcome, **fit})

    summary = pd.DataFrame(rows)
    sig = summary[summary["log_pm25_p"] < 0.05]
    sig_list = ", ".join(
        f"{r.outcome} (p={r.log_pm25_p:.3g}, coef={'+ ' if r.log_pm25_coef > 0 else '- '}{abs(r.log_pm25_coef):.4f})"
        for r in sig.itertuples()
    )
    result_summary = (
        f"Pooled across all 3 sites (site as covariate). log(PM2.5) significant (p<0.05) "
        f"for: {sig_list if sig_list else 'none'}."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.2", summary, paper="p2",
        method="OLS, pooled across all 3 clinical sites: activity/BMI ~ log1p(PM2.5) + age + "
                "clinical_site dummies. Tests the first link in the project head's mediation "
                "hypothesis (pollution -> activity/BMI -> glycemic control), not the full chain.",
        result=result_summary,
        decision="keep",
    )


def run_eg3_per_site(df: pd.DataFrame) -> None:
    print(f"\n{'='*90}\nEG.3 -- per-site: activity/BMI ~ log(PM2.5) + age, fit separately at each site\n{'='*90}")

    rows = []
    for site in SITES:
        sub = df[df["clinical_site"] == site]
        for outcome in OUTCOMES:
            model_df = sub[[outcome, "log_pm25", "age"]].dropna()
            if len(model_df) < 30:
                print(f"\n--- site={site}, outcome={outcome}: N={len(model_df)}, too small to fit ---")
                continue
            fit = _fit(model_df, outcome)
            print(f"\n--- site={site}, outcome={outcome}  (N={fit['n']}, R2={fit['r2']:.3f}) ---")
            print(f"  log_pm25: coef={fit['log_pm25_coef']:.4f}, p={fit['log_pm25_p']:.4g}")
            rows.append({"site": site, "outcome": outcome, **fit})

    summary = pd.DataFrame(rows)
    sig = summary[summary["log_pm25_p"] < 0.05]
    sig_list = ", ".join(
        f"{r.site}/{r.outcome} (p={r.log_pm25_p:.3g}, coef={'+ ' if r.log_pm25_coef > 0 else '- '}{abs(r.log_pm25_coef):.4f})"
        for r in sig.itertuples()
    )
    result_summary = (
        f"Same model refit separately per site (no pooling, no site dummy). log(PM2.5) "
        f"significant (p<0.05) for: {sig_list if sig_list else 'none'}. Compare against EG.2's "
        f"pooled estimate -- a pooled-significant effect that disappears or reverses at one site "
        f"means the pooled estimate is being driven by between-site differences, not a "
        f"within-site pollution effect."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.3", summary, paper="p2",
        method="OLS, fit separately within each of the 3 clinical sites (UW, UAB, UCSD): "
                "activity/BMI ~ log1p(PM2.5) + age. Same first-link mediation test as EG.2, "
                "run without pooling to check whether the pooled effect holds at each site "
                "individually.",
        result=result_summary,
        decision="keep",
    )


def main() -> None:
    df = build_table()
    run_eg2_pooled(df)
    run_eg3_per_site(df)


if __name__ == "__main__":
    main()
