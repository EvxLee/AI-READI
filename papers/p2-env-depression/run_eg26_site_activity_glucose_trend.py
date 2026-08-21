#!/usr/bin/env python3
"""EG.26 -- within age/severity strata, does less pollution mean more activity and better glucose control?

Project head's follow-up (2026-08-21), last piece of the batch: "from
there we can look at within those groups, physical activity, cgm, that
would be interesting potentially if we found site specific differences,
maybe theres a trend where less pollution has more activity and glucose
control."

EG.24 found the 3 sites are NOT comparable in age/severity composition --
so raw site averages of activity/glucose would confound pollution with
population differences. This adjusts for that two ways:

  1. Age/severity-adjusted means: regress each outcome on age +
     severity-group dummies, take the residuals, then compare mean
     residuals by site (removes the part of each outcome explained by
     age/severity before comparing sites).
  2. Raw (unadjusted) means by site, for reference/contrast against (1).

Sites are ranked by pollution level using EG.11's PM2.5 means (ascending):
UW (10.4) < UCSD (12.3) < UAB (19.0).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables

CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"

# Ascending PM2.5 order, from EG.11.
SITE_ORDER_BY_POLLUTION = ["UW", "UCSD", "UAB"]

OUTCOMES = ["steps", "active_calories", "glucose_mean", "glucose_cv", "tar_180"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    extra = activity[["person_id", "average_active_calories_kcal"]].rename(
        columns={"average_active_calories_kcal": "active_calories"}
    )
    df = df.merge(extra, on="person_id", how="left")

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", "glucose_mean", "glucose_cv", "tar_180"]], on="person_id", how="left")
    return df


def adjusted_means_by_site(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """Residualize `outcome` on age + severity-group dummies, then mean the residuals by site."""
    severity_dummies = pd.get_dummies(df["study_group_label"], prefix="sev", drop_first=True, dtype=float)
    model_df = pd.concat([df[[outcome, "age", "clinical_site"]], severity_dummies], axis=1).dropna()

    X = sm.add_constant(model_df.drop(columns=[outcome, "clinical_site"]))
    y = model_df[outcome]
    fit = sm.OLS(y, X).fit()
    model_df = model_df.copy()
    model_df["residual"] = fit.resid

    return model_df.groupby("clinical_site")["residual"].agg(n="count", adjusted_mean="mean").reset_index()


def main() -> None:
    df = build_table()
    print(f"\n{'='*90}\nEG.26 -- activity + glucose control by site, raw and age/severity-adjusted\n{'='*90}")
    print(f"Sites ranked by pollution (ascending PM2.5, from EG.11): {SITE_ORDER_BY_POLLUTION}")

    all_rows = []
    for outcome in OUTCOMES:
        raw = df.groupby("clinical_site")[outcome].agg(n="count", raw_mean="mean").reset_index()
        adj = adjusted_means_by_site(df, outcome)
        merged = raw.merge(adj[["clinical_site", "adjusted_mean"]], on="clinical_site")
        merged["outcome"] = outcome
        merged["pollution_rank"] = merged["clinical_site"].map({s: i for i, s in enumerate(SITE_ORDER_BY_POLLUTION)})
        merged = merged.sort_values("pollution_rank")

        print(f"\n--- {outcome} (ordered by ascending pollution: UW < UCSD < UAB) ---")
        print(merged[["clinical_site", "n", "raw_mean", "adjusted_mean"]].round(3).to_string(index=False))

        raw_vals = merged.sort_values("pollution_rank")["raw_mean"].values
        adj_vals = merged.sort_values("pollution_rank")["adjusted_mean"].values
        raw_monotonic_down = bool(np.all(np.diff(raw_vals) < 0))
        raw_monotonic_up = bool(np.all(np.diff(raw_vals) > 0))
        adj_monotonic_down = bool(np.all(np.diff(adj_vals) < 0))
        adj_monotonic_up = bool(np.all(np.diff(adj_vals) > 0))

        merged["raw_monotonic_with_pollution"] = "down" if raw_monotonic_down else ("up" if raw_monotonic_up else "no")
        merged["adjusted_monotonic_with_pollution"] = "down" if adj_monotonic_down else ("up" if adj_monotonic_up else "no")
        all_rows.append(merged)

    summary = pd.concat(all_rows, ignore_index=True)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_26_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.26 summary written to {summary_path}")

    trend_lines = []
    for outcome in OUTCOMES:
        sub = summary[summary["outcome"] == outcome]
        adj_trend = sub["adjusted_monotonic_with_pollution"].iloc[0]
        trend_lines.append(f"{outcome}: {adj_trend}")
    trend_summary = "; ".join(trend_lines)

    result_summary = (
        f"Age/severity-adjusted means by site, ordered by ascending PM2.5 (UW<UCSD<UAB). "
        f"Monotonic trend with pollution per outcome (adjusted): {trend_summary}. "
        f"'down' = decreases as pollution increases (activity outcomes: hypothesized direction "
        f"would be 'down'; glucose outcomes: hypothesized worse control, i.e. 'up', as pollution "
        f"increases). See EG_26_summary.csv for raw and adjusted means."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.26", summary, paper="p2",
        method="Raw and age/severity-adjusted (OLS residual) means of steps, active_calories, "
                "glucose_mean, glucose_cv, and tar_180 by clinical_site, ordered by ascending "
                "PM2.5 exposure (UW<UCSD<UAB per EG.11), to check for a monotonic "
                "'less pollution -> more activity, better glucose control' trend once age and "
                "severity-group composition (EG.24 found these differ significantly by site) are "
                "accounted for.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
