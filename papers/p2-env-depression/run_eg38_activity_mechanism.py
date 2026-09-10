#!/usr/bin/env python3
"""EG.38 -- does the PM2.5 / BMI -> blood sugar link run through reduced activity?

Project-head follow-up (2026-09-10), verbatim: "next would be to answer
whether the oral + insulin group with higher pollution tend to exercise
less (measured by activity, steps, and/or calories) and similarly for BMI
in the healthy + prediabetes group."

EG.36 found:
  * T2DM group (Oral Med + Insulin): PM2.5 links to all 4 blood sugar measures.
  * non-diabetic group (Healthy + Pre-DM): BMI links to blood sugar (hba1c, tar_180).

This tests the obvious candidate mechanism for each -- reduced physical
activity:
  * T2DM group: activity ~ log_pm25 (+ bmi + age + site). If higher
    pollution predicts less activity here, that's a plausible pathway for
    the PM2.5 -> blood sugar link EG.36 found in this same group.
  * non-diabetic group: activity ~ bmi (+ log_pm25 + age + site). If
    higher BMI predicts less activity here, that's the parallel pathway
    for the BMI -> blood sugar link.

Both predictors are run in BOTH groups (not just the one where EG.36
flagged them) so the group-specificity of any activity link is visible,
not assumed. Activity measured 4 ways: steps, active_calories,
active_minutes_v1_per_day (any non-sedentary), active_minutes_v2_per_day
(walking+running only). This is a single-link check, not a formal
mediation model -- if a link shows up, a bootstrap indirect-effect test
is the next step.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
ACTIVITY_LEVEL_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "activity_level_minutes.csv"

ACTIVITY_OUTCOMES = ["steps", "active_calories", "active_minutes_v1_per_day", "active_minutes_v2_per_day"]

STATUS_2GROUP_MAP = {
    "Healthy": "non-diabetic (Healthy+Pre-DM)",
    "Pre-DM": "non-diabetic (Healthy+Pre-DM)",
    "Oral Med": "T2DM (Oral Med+Insulin)",
    "Insulin": "T2DM (Oral Med+Insulin)",
}
GROUP2_ORDER = ["non-diabetic (Healthy+Pre-DM)", "T2DM (Oral Med+Insulin)"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    df = df.merge(
        activity[["person_id", "average_active_calories_kcal"]].rename(
            columns={"average_active_calories_kcal": "active_calories"}),
        on="person_id", how="left",
    )

    level = pd.read_csv(ACTIVITY_LEVEL_TABLE, dtype={"person_id": str})
    df = df.merge(level[["person_id", "active_minutes_v1_per_day", "active_minutes_v2_per_day"]],
                  on="person_id", how="left")

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])

    df["status_2group"] = df["study_group_label"].astype(str).map(STATUS_2GROUP_MAP)
    return df


def _fit_one(sub: pd.DataFrame, predictor: str, other_predictor: str, outcome: str, extra_cols: list[str]) -> dict | None:
    cols = [predictor, other_predictor, outcome] + extra_cols
    fit_df = sub[cols].dropna()
    if len(fit_df) < 30:
        return None
    X = fit_df[[predictor, other_predictor] + extra_cols]
    X = X.loc[:, X.nunique() > 1]
    if predictor not in X.columns:
        return None
    fit = sm.OLS(fit_df[outcome], sm.add_constant(X)).fit()
    return {"n": len(fit_df), "coef": fit.params[predictor], "p": fit.pvalues[predictor]}


def main() -> None:
    df = build_table()
    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    df = pd.concat([df, site_dummies], axis=1)
    site_cols = list(site_dummies.columns)
    predictors = [("log_pm25", "bmi"), ("bmi", "log_pm25")]

    print(f"\n{'='*90}\nEG.38 -- activity ~ PM2.5 / BMI, within each diabetic-status group\n{'='*90}")
    print("Group sizes:", df["status_2group"].value_counts().to_dict())

    rows = []
    for group in GROUP2_ORDER:
        sub = df[df["status_2group"] == group]
        print(f"\n--- {group} ---")
        for predictor, other in predictors:
            for outcome in ACTIVITY_OUTCOMES:
                r = _fit_one(sub, predictor, other, outcome, ["age"] + site_cols)
                if r is None:
                    continue
                rows.append({"group": group, "predictor": predictor, "activity_outcome": outcome, **r})
                flag = " *" if r["p"] < 0.05 else ""
                direction = "less" if r["coef"] < 0 else "more"
                print(f"  {predictor:10s} -> {outcome:26s} N={r['n']:4d}  coef={r['coef']:+.4f} ({direction} activity)  p={r['p']:.4f}{flag}")

    summary = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parent / "results" / "EG_38_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.38 summary written to {out_path}")

    # The two links the project head specifically asked about:
    t2dm_pm25 = summary[(summary["group"] == "T2DM (Oral Med+Insulin)") & (summary["predictor"] == "log_pm25")]
    nondiab_bmi = summary[(summary["group"] == "non-diabetic (Healthy+Pre-DM)") & (summary["predictor"] == "bmi")]

    def _describe(sub_df, label):
        sig = sub_df[sub_df["p"] < 0.05]
        if sig.empty:
            return f"{label}: NO significant link to any of the 4 activity measures (all p>0.05) -- reduced activity does not look like the mechanism"
        parts = ", ".join(
            f"{r.activity_outcome} (coef={r.coef:+.3g}, {'less' if r.coef < 0 else 'MORE'} activity, p={r.p:.3g})"
            for r in sig.itertuples()
        )
        return f"{label}: {len(sig)}/4 significant -- {parts}"

    result_summary = (
        "Single-link check for the reduced-activity mechanism, within each diabetic-status group "
        "(activity ~ predictor + other predictor + age + site). "
        + _describe(t2dm_pm25, "T2DM group, PM2.5 -> activity") + ". "
        + _describe(nondiab_bmi, "Non-diabetic group, BMI -> activity") + ". "
        "Both predictors were run in both groups (see EG_38_summary.csv) to show group-specificity. "
        "Not a formal mediation test -- a bootstrap indirect-effect model is the next step for any link that shows up."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.38", summary, paper="p2",
        method="Within each of the 2 diabetic-status groups (non-diabetic = Healthy+Pre-DM; T2DM = "
                "Oral Med+Insulin), OLS of 4 activity measures (steps, active_calories, "
                "active_minutes_v1_per_day, active_minutes_v2_per_day) on log_pm25 and on bmi, each "
                "net of the other + age + site. Tests the reduced-activity mechanism for EG.36's two "
                "group-specific blood-sugar findings (PM2.5->glycemia in T2DM; BMI->glycemia in "
                "non-diabetic). Single-link check, not a formal mediation model. Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
