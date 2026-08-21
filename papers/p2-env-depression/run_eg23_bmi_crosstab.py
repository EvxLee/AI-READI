#!/usr/bin/env python3
"""EG.23 -- average BMI for every age-band x severity-group cell.

Project head's follow-up (2026-08-21): "compute bmi for each of the age
and diabetic groups together, ex the average bmi of someone whos
prediabetic and above 70, keep age as a continuous covariate" -- a
descriptive crosstab, not a model. Age bands mirror EDA_FINDINGS.md's
existing convention (40-54, 55-69, 70+) for continuity with the earlier
EDA; age itself stays continuous in every actual regression model
elsewhere in this paper, per his explicit note.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aireadi import cohort, results

AGE_BINS = [40, 55, 70, 200]
AGE_LABELS = ["40-54", "55-69", "70+"]


def main() -> None:
    df = cohort.build_core_table()
    df["age_band"] = pd.cut(df["age"], bins=AGE_BINS, labels=AGE_LABELS, right=False)

    print(f"\n{'='*90}\nEG.23 -- average BMI by age band x severity group\n{'='*90}")

    grouped = df.groupby(["age_band", "study_group_label"], observed=True)["bmi"]
    summary = grouped.agg(n="count", mean_bmi="mean", median_bmi="median", sd_bmi="std").reset_index()
    summary = summary.sort_values(["age_band", "study_group_label"])

    print(summary.round(2).to_string(index=False))

    pivot = summary.pivot(index="age_band", columns="study_group_label", values="mean_bmi")
    print("\n--- Pivoted (mean BMI) ---")
    print(pivot.round(2).to_string())

    out_path = Path(__file__).resolve().parent / "results" / "EG_23_bmi_crosstab.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.23 crosstab written to {out_path}")

    max_row = summary.loc[summary["mean_bmi"].idxmax()]
    min_row = summary.loc[summary["mean_bmi"].idxmin()]
    result_summary = (
        f"Average BMI computed for all {len(summary)} age-band x severity-group cells "
        f"(3 age bands x 4 severity groups). Highest mean BMI: {max_row['age_band']}/"
        f"{max_row['study_group_label']} ({max_row['mean_bmi']:.1f}, n={max_row['n']}). "
        f"Lowest: {min_row['age_band']}/{min_row['study_group_label']} ({min_row['mean_bmi']:.1f}, "
        f"n={min_row['n']}). Full table in EG_23_bmi_crosstab.csv."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.23", summary, paper="p2",
        method="Descriptive: mean/median/SD of BMI for each of the 12 age-band (40-54/55-69/70+) "
                "x severity-group (Healthy/Pre-DM/Oral Med/Insulin) cells. Not a model -- age stays "
                "continuous in every regression elsewhere in this paper.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
