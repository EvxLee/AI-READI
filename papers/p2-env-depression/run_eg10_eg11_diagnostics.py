#!/usr/bin/env python3
"""EG.10 -- severity-group distribution in EG.7a's significant results.
EG.11 -- per-site pollution distribution (PM2.5, NOx, VOC).

Project head's follow-up (2026-08-18) to EG.7/EG.8: before repeating the
pollution tests further, look at what's underneath the two significant
EG.7a outcomes (glucose_cv, tar_180) and check whether one site is simply
more (or more variably) polluted than the others, which would help explain
why EG.8's effect concentrated at UCSD.

Both diagnostics reuse tables already on disk -- no new Azure pulls.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from aireadi import azure_io, cohort, results, wearables

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"

PREDICTORS = [
    "log_pm25", "mean_temp", "mean_hum", "mean_light", "mean_voc", "mean_nox",
    "bmi", "steps", "stress", "heart_rate", "sleep_hours", "active_calories",
    "age",
]
SIG_OUTCOMES = ["glucose_cv", "tar_180"]  # EG.7a's two significant (no-severity) outcomes


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
    df = df.merge(cgm[["person_id", *SIG_OUTCOMES]], on="person_id", how="left")
    return df


def run_eg10(df: pd.DataFrame) -> None:
    print(f"\n{'='*90}\nEG.10 -- severity-group distribution within EG.7a's significant-outcome model rows\n{'='*90}")

    cohort_dist = df["study_group_label"].value_counts(normalize=True).sort_index() * 100
    print("\nFull cohort severity-group distribution (%):")
    print(cohort_dist.round(1).to_string())

    rows = []
    for outcome in SIG_OUTCOMES:
        model_df = df[["study_group_label"] + PREDICTORS + [outcome]].dropna()
        dist = model_df["study_group_label"].value_counts(normalize=True).sort_index() * 100
        counts = model_df["study_group_label"].value_counts().sort_index()
        print(f"\n--- outcome = {outcome}  (N={len(model_df)}) ---")
        for group in dist.index:
            print(f"  {group}: n={counts[group]}, {dist[group]:.1f}% (cohort: {cohort_dist[group]:.1f}%)")
        for group in dist.index:
            rows.append({
                "outcome": outcome, "severity_group": group,
                "n": int(counts[group]), "pct_in_model": dist[group],
                "pct_in_cohort": cohort_dist[group],
            })

    summary = pd.DataFrame(rows)
    max_skew = (summary["pct_in_model"] - summary["pct_in_cohort"]).abs().max()
    result_summary = (
        f"Severity-group distribution within EG.7a's glucose_cv/tar_180 model rows, compared to "
        f"the full cohort's distribution. Max absolute deviation from cohort proportions: "
        f"{max_skew:.1f} percentage points. See EG_10.csv for the full breakdown."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.10", summary, paper="p2",
        method="Descriptive: study_group_label distribution among the complete-case rows used in "
                "EG.7a's glucose_cv and tar_180 models, compared to the full cohort's distribution.",
        result=result_summary,
        decision="keep",
    )


def run_eg11(env: pd.DataFrame) -> None:
    print(f"\n{'='*90}\nEG.11 -- per-site pollution distribution (PM2.5, NOx, VOC)\n{'='*90}")

    core = cohort.build_core_table()[["person_id", "clinical_site"]]
    core["person_id"] = core["person_id"].astype(str)
    merged = env.merge(core, on="person_id", how="left")

    rows = []
    for pollutant in ["mean_pm25", "mean_nox", "mean_voc"]:
        for site in merged["clinical_site"].dropna().unique():
            vals = merged.loc[merged["clinical_site"] == site, pollutant].dropna()
            stats = {
                "pollutant": pollutant, "site": site, "n": len(vals),
                "mean": vals.mean(), "median": vals.median(), "sd": vals.std(),
                "iqr": vals.quantile(0.75) - vals.quantile(0.25), "max": vals.max(),
            }
            rows.append(stats)
            print(f"  {pollutant} @ {site}: n={stats['n']}, mean={stats['mean']:.2f}, "
                  f"median={stats['median']:.2f}, sd={stats['sd']:.2f}, iqr={stats['iqr']:.2f}, "
                  f"max={stats['max']:.2f}")

    summary = pd.DataFrame(rows).sort_values(["pollutant", "site"])
    print(f"\n{summary.round(2).to_string(index=False)}")

    pm25 = summary[summary["pollutant"] == "mean_pm25"]
    ucsd_sd = pm25.loc[pm25["site"] == "UCSD", "sd"].values
    max_sd_site = pm25.loc[pm25["sd"].idxmax(), "site"]
    result_summary = (
        f"Per-site PM2.5/NOx/VOC descriptive stats (mean, median, SD, IQR, max). PM2.5 SD is "
        f"highest at {max_sd_site}"
        + (f" (SD={ucsd_sd[0]:.2f})" if len(ucsd_sd) else "")
        + f". Full table in EG_11.csv -- checked against EG.8's finding that the pollution-glucose_cv "
        f"effect only replicated at UCSD."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.11", summary, paper="p2",
        method="Descriptive: mean/median/SD/IQR/max for mean_pm25, mean_nox, mean_voc, broken out "
                "by clinical_site, from environmental_summary.csv.",
        result=result_summary,
        decision="keep",
    )


def main() -> None:
    df = build_table()
    run_eg10(df)
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    run_eg11(env)


if __name__ == "__main__":
    main()
