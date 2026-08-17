#!/usr/bin/env python3
"""EG.4 -- second mediation link: does activity/BMI predict glycemic control?

Project-head mediation hypothesis (2026-08-15, see PRESPEC.md Section 8):
worse pollution -> less activity / higher BMI -> worse glycemic control.
EG.2/EG.3 tested the first link (pollution -> activity/BMI) and found a
mixed result: BMI moved as expected, but steps/active_calories moved
*opposite* to the hypothesized direction (more pollution, more activity).

EG.4 tests the second link on its own, independent of pollution: does
activity (steps, active_calories) or BMI predict glycemic control, once
age and severity group are controlled for? This is a necessary condition
for the mediation story to work at all -- if activity/BMI don't predict
glycemic control here, pollution's effect on them (EG.2/EG.3) can't be
mediating anything, regardless of direction.

Same 4 candidate glycemic-control outcomes as EG.1 (glucose_mean,
glucose_cv, tar_180, spikes_per_day_180), same severity + site covariate
structure, so this is directly comparable to EG.1's coefficient table.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables

CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"

PREDICTORS = ["steps", "active_calories", "bmi", "age"]
CANDIDATE_OUTCOMES = ["glucose_mean", "glucose_cv", "tar_180", "spikes_per_day_180"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    extra = activity[["person_id", "average_active_calories_kcal"]].rename(
        columns={"average_active_calories_kcal": "active_calories"}
    )
    df = df.merge(extra, on="person_id", how="left")

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", *CANDIDATE_OUTCOMES]], on="person_id", how="left")
    return df


def main() -> None:
    df = build_table()
    print(f"\n{'='*90}\nEG.4 -- second mediation link: glycemic control ~ activity + BMI + age + severity\n{'='*90}")

    rows = []
    for outcome in CANDIDATE_OUTCOMES:
        severity_dummies = pd.get_dummies(df["study_group_label"], prefix="sev", drop_first=True, dtype=float)
        site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
        model_df = pd.concat(
            [df[[outcome] + PREDICTORS], severity_dummies, site_dummies], axis=1
        ).dropna()
        n = len(model_df)

        X = sm.add_constant(model_df.drop(columns=outcome))
        y = model_df[outcome]
        fit = sm.OLS(y, X).fit()

        table = pd.DataFrame({"coefficient": fit.params, "p_value": fit.pvalues}).drop(index="const")
        table = table[table.index.isin(PREDICTORS)].sort_values("p_value")

        print(f"\n--- outcome = {outcome}  (N={n}, R2={fit.rsquared:.3f}) ---")
        print(table.round(4).to_string())

        steps_row = table.loc["steps"]
        cal_row = table.loc["active_calories"]
        bmi_row = table.loc["bmi"]
        rows.append({
            "outcome": outcome, "n": n, "r2": fit.rsquared,
            "steps_coef": steps_row["coefficient"], "steps_p": steps_row["p_value"],
            "active_calories_coef": cal_row["coefficient"], "active_calories_p": cal_row["p_value"],
            "bmi_coef": bmi_row["coefficient"], "bmi_p": bmi_row["p_value"],
        })

        env_table = table.reset_index().rename(columns={"index": "predictor"})
        env_table.insert(0, "outcome", outcome)
        env_table.insert(1, "n", n)
        results.save(
            f"EG.4_{outcome}", env_table, paper="p2",
            method=f"OLS: {outcome} ~ steps + active_calories + bmi + age + severity-group dummies "
                    f"+ site dummies",
            result=f"N={n}, R2={fit.rsquared:.3f}. steps p={steps_row['p_value']:.3g}, "
                    f"active_calories p={cal_row['p_value']:.3g}, bmi p={bmi_row['p_value']:.3g}.",
            decision="keep",
        )

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_4_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.4 cross-outcome summary written to {summary_path}")
    print(summary.round(4).to_string(index=False))

    n_steps_sig = int((summary["steps_p"] < 0.05).sum())
    n_cal_sig = int((summary["active_calories_p"] < 0.05).sum())
    n_bmi_sig = int((summary["bmi_p"] < 0.05).sum())
    top_summary = (
        f"Across {len(CANDIDATE_OUTCOMES)} candidate glycemic-control outcomes ({', '.join(CANDIDATE_OUTCOMES)}), "
        f"steps significant (p<0.05) in {n_steps_sig}/{len(CANDIDATE_OUTCOMES)}; "
        f"active_calories significant in {n_cal_sig}/{len(CANDIDATE_OUTCOMES)}; "
        f"bmi significant in {n_bmi_sig}/{len(CANDIDATE_OUTCOMES)}. See EG_4_summary.csv for per-outcome detail."
    )
    results.save(
        "EG.4", summary, paper="p2",
        method="Cross-outcome summary of the second mediation link (see EG.4_<outcome> rows for "
                "each individual fit): tests steps, active_calories, and BMI against 4 candidate "
                "CGM-derived glycemic-control outcomes, controlling for age and severity group.",
        result=top_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
