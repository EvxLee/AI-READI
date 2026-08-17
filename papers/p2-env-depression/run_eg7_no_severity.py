#!/usr/bin/env python3
"""EG.7 -- sensitivity: does dropping severity group change EG.1 / EG.4?

Standing concern since EG.1 (see PRESPEC.md Section 7 and the EG.4/EG.5
discussion): severity group (Healthy/Pre-DM/Oral Med/Insulin) is largely
*defined* by glycemic control, so including it as a covariate may be
absorbing the true effect of pollution and activity/BMI rather than acting
as a neutral confounder. Evidence for this: EP.3/EP.6/EP.7 show pollution
significantly predicts severity-group membership, yet EG.1 (which controls
for severity group) finds pollution has no effect on the same underlying
glycemic-control metrics.

This reruns EG.1 (primary model) and EG.4 (second mediation link) with
severity-group dummies removed from the predictor set -- everything else
identical, same 4 candidate outcomes, same site dummies. If log(PM2.5) or
the activity/BMI terms become significant once severity group is dropped,
that confirms the overcontrol hypothesis. If they stay non-significant,
the null in EG.1/EG.4 is real, not an artifact of this covariate.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"

EG1_PREDICTORS = [
    "log_pm25", "mean_temp", "mean_hum", "mean_light", "mean_voc", "mean_nox",
    "bmi", "steps", "stress", "heart_rate", "sleep_hours", "active_calories",
    "age",
]
EG4_PREDICTORS = ["steps", "active_calories", "bmi", "age"]

CANDIDATE_OUTCOMES = ["glucose_mean", "glucose_cv", "tar_180", "spikes_per_day_180"]

# EG.1's original (with-severity) results, for the side-by-side comparison table.
EG1_WITH_SEVERITY = {
    "glucose_mean": 0.988, "glucose_cv": 0.114, "tar_180": 0.299, "spikes_per_day_180": 0.156,
}
EG4_WITH_SEVERITY_STEPS_P = {
    "glucose_mean": 0.5560, "glucose_cv": 0.8034, "tar_180": 0.4345, "spikes_per_day_180": 0.2386,
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


def run_eg7a_primary_no_severity(df: pd.DataFrame) -> pd.DataFrame:
    print(f"\n{'='*90}\nEG.7a -- EG.1 rerun WITHOUT severity-group dummies\n{'='*90}")

    rows = []
    for outcome in CANDIDATE_OUTCOMES:
        site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
        model_df = pd.concat([df[[outcome] + EG1_PREDICTORS], site_dummies], axis=1).dropna()
        n = len(model_df)

        X = sm.add_constant(model_df.drop(columns=outcome))
        y = model_df[outcome]
        fit = sm.OLS(y, X).fit()

        table = pd.DataFrame({"coefficient": fit.params, "p_value": fit.pvalues}).drop(index="const")
        table = table[table.index.isin(EG1_PREDICTORS)].sort_values("p_value")

        print(f"\n--- outcome = {outcome}  (N={n}, R2={fit.rsquared:.3f}) ---")
        print(table.round(4).to_string())

        env_row = table.loc["log_pm25"]
        bmi_row = table.loc["bmi"]
        rows.append({
            "outcome": outcome, "n": n, "r2": fit.rsquared,
            "log_pm25_coef": env_row["coefficient"], "log_pm25_p": env_row["p_value"],
            "log_pm25_p_with_severity": EG1_WITH_SEVERITY[outcome],
            "bmi_coef": bmi_row["coefficient"], "bmi_p": bmi_row["p_value"],
        })

        out_table = table.reset_index().rename(columns={"index": "predictor"})
        out_table.insert(0, "outcome", outcome)
        out_table.insert(1, "n", n)
        results.save(
            f"EG.7a_{outcome}", out_table, paper="p2",
            method=f"OLS: {outcome} ~ log1p(PM2.5) + env vars + BMI + wearables + age + site dummies "
                    f"(NO severity-group dummies -- EG.1 minus severity, to test overcontrol).",
            result=f"N={n}, R2={fit.rsquared:.3f}. log_pm25 p={env_row['p_value']:.3g} "
                    f"(was {EG1_WITH_SEVERITY[outcome]:.3g} with severity), bmi p={bmi_row['p_value']:.3g}.",
            decision="keep",
        )

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_7a_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.7a summary written to {summary_path}")
    print(summary.round(4).to_string(index=False))
    return summary


def run_eg7b_second_link_no_severity(df: pd.DataFrame) -> pd.DataFrame:
    print(f"\n{'='*90}\nEG.7b -- EG.4 rerun WITHOUT severity-group dummies\n{'='*90}")

    rows = []
    for outcome in CANDIDATE_OUTCOMES:
        site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
        model_df = pd.concat([df[[outcome] + EG4_PREDICTORS], site_dummies], axis=1).dropna()
        n = len(model_df)

        X = sm.add_constant(model_df.drop(columns=outcome))
        y = model_df[outcome]
        fit = sm.OLS(y, X).fit()

        table = pd.DataFrame({"coefficient": fit.params, "p_value": fit.pvalues}).drop(index="const")
        table = table[table.index.isin(EG4_PREDICTORS)].sort_values("p_value")

        print(f"\n--- outcome = {outcome}  (N={n}, R2={fit.rsquared:.3f}) ---")
        print(table.round(4).to_string())

        steps_row = table.loc["steps"]
        cal_row = table.loc["active_calories"]
        bmi_row = table.loc["bmi"]
        rows.append({
            "outcome": outcome, "n": n, "r2": fit.rsquared,
            "steps_coef": steps_row["coefficient"], "steps_p": steps_row["p_value"],
            "steps_p_with_severity": EG4_WITH_SEVERITY_STEPS_P[outcome],
            "active_calories_coef": cal_row["coefficient"], "active_calories_p": cal_row["p_value"],
            "bmi_coef": bmi_row["coefficient"], "bmi_p": bmi_row["p_value"],
        })

        out_table = table.reset_index().rename(columns={"index": "predictor"})
        out_table.insert(0, "outcome", outcome)
        out_table.insert(1, "n", n)
        results.save(
            f"EG.7b_{outcome}", out_table, paper="p2",
            method=f"OLS: {outcome} ~ steps + active_calories + bmi + age + site dummies "
                    f"(NO severity-group dummies -- EG.4 minus severity, to test overcontrol).",
            result=f"N={n}, R2={fit.rsquared:.3f}. steps p={steps_row['p_value']:.3g} "
                    f"(was {EG4_WITH_SEVERITY_STEPS_P[outcome]:.3g} with severity), "
                    f"active_calories p={cal_row['p_value']:.3g}, bmi p={bmi_row['p_value']:.3g}.",
            decision="keep",
        )

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_7b_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.7b summary written to {summary_path}")
    print(summary.round(4).to_string(index=False))
    return summary


def main() -> None:
    df = build_table()
    eg7a = run_eg7a_primary_no_severity(df)
    eg7b = run_eg7b_second_link_no_severity(df)

    print(f"\n{'='*90}\nEG.7 -- overcontrol verdict\n{'='*90}")
    n_pm25_flip = int(((eg7a["log_pm25_p"] < 0.05) & (eg7a["log_pm25_p_with_severity"] >= 0.05)).sum())
    n_steps_flip = int(((eg7b["steps_p"] < 0.05) & (eg7b["steps_p_with_severity"] >= 0.05)).sum())
    verdict = (
        f"log(PM2.5) flips from non-significant to significant (p<0.05) once severity is dropped, "
        f"in {n_pm25_flip}/{len(eg7a)} outcomes. steps flips the same way in {n_steps_flip}/{len(eg7b)} "
        f"outcomes. See EG_7a_summary.csv / EG_7b_summary.csv for full before/after detail."
    )
    print(verdict)

    combined = pd.DataFrame({
        "outcome": CANDIDATE_OUTCOMES,
        "log_pm25_p_no_severity": eg7a["log_pm25_p"].values,
        "log_pm25_p_with_severity": eg7a["log_pm25_p_with_severity"].values,
        "steps_p_no_severity": eg7b["steps_p"].values,
        "steps_p_with_severity": eg7b["steps_p_with_severity"].values,
    })
    results.save(
        "EG.7", combined, paper="p2",
        method="Overcontrol sensitivity check: EG.1 and EG.4 rerun with severity-group dummies "
                "removed from the predictor set, compared side by side against the original "
                "with-severity p-values.",
        result=verdict,
        decision="keep",
    )


if __name__ == "__main__":
    main()
