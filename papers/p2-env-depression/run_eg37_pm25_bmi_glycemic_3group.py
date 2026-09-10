#!/usr/bin/env python3
"""EG.37 -- PM2.5/BMI vs blood sugar, 3-group diabetic-status split.

Project-head follow-up (2026-09-10): EG.36's 2-group split (non-diabetic =
Healthy+Pre-DM vs. diabetic-treated = Oral Med+Insulin) showed PM2.5's
link to blood sugar is concentrated entirely in the diabetic-treated
group. He wants a 3-group version -- Healthy, Pre-DM, and (Oral+Insulin
combined) -- because "the oral and insulin combination is justifiable
since both are T2DM, but reviewers may object to combining healthy and
prediabetes."

Same design as EG.35/EG.36: PM2.5 and BMI each net of the other, + age +
site dummies, across hba1c/glucose_cv/tar_180/interday_glucose_variance.
Only the grouping changes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import cohort, results

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"
VAR_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "glucose_variability_metrics.csv"

OUTCOMES = ["hba1c", "glucose_cv", "tar_180", "interday_glucose_variance"]

STATUS_3GROUP_MAP = {
    "Healthy": "Healthy",
    "Pre-DM": "Pre-DM",
    "Oral Med": "T2DM (Oral Med+Insulin)",
    "Insulin": "T2DM (Oral Med+Insulin)",
}
GROUP3_ORDER = ["Healthy", "Pre-DM", "T2DM (Oral Med+Insulin)"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", "glucose_cv", "tar_180"]], on="person_id", how="left")
    var = pd.read_csv(VAR_TABLE, dtype={"person_id": str})
    df = df.merge(var[["person_id", "interday_glucose_variance"]], on="person_id", how="left")

    df["status_3group"] = df["study_group_label"].astype(str).map(STATUS_3GROUP_MAP)
    return df


def _fit_one(sub: pd.DataFrame, predictor: str, other_predictor: str, outcome: str, extra_cols: list[str]) -> dict | None:
    cols = [predictor, other_predictor, outcome] + extra_cols
    fit_df = sub[cols].dropna()
    if len(fit_df) < 30:
        return None
    X_cols = [predictor, other_predictor] + extra_cols
    X = fit_df[X_cols]
    X = X.loc[:, X.nunique() > 1]
    if predictor not in X.columns:
        return None
    X = sm.add_constant(X)
    fit = sm.OLS(fit_df[outcome], X).fit()
    return {"n": len(fit_df), "coef": fit.params[predictor], "p": fit.pvalues[predictor]}


def main() -> None:
    df = build_table()
    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    df = pd.concat([df, site_dummies], axis=1)
    site_cols = list(site_dummies.columns)
    predictors = [("log_pm25", "bmi"), ("bmi", "log_pm25")]

    print(f"\n{'='*90}\nEG.37 -- PM2.5 & BMI vs blood sugar, 3-group split\n{'='*90}")
    print("Group sizes:", df["status_3group"].value_counts().to_dict())

    rows = []
    print("\n--- Global (pooled, age + site) ---")
    for predictor, other in predictors:
        for outcome in OUTCOMES:
            r = _fit_one(df, predictor, other, outcome, ["age"] + site_cols)
            if r is None:
                continue
            rows.append({"stratum": "all", "predictor": predictor, "outcome": outcome, **r})
            flag = " *" if r["p"] < 0.05 else ""
            print(f"  {predictor:10s} -> {outcome:26s} N={r['n']:4d}  coef={r['coef']:+.4f}  p={r['p']:.4f}{flag}")

    print("\n--- By 3-group diabetic status ---")
    for group in GROUP3_ORDER:
        sub = df[df["status_3group"] == group]
        for predictor, other in predictors:
            for outcome in OUTCOMES:
                r = _fit_one(sub, predictor, other, outcome, ["age"] + site_cols)
                if r is None:
                    continue
                rows.append({"stratum": group, "predictor": predictor, "outcome": outcome, **r})
                flag = " *" if r["p"] < 0.05 else ""
                print(f"  {group:26s} {predictor:10s} -> {outcome:26s} N={r['n']:4d}  coef={r['coef']:+.4f}  p={r['p']:.4f}{flag}")

    summary = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parent / "results" / "EG_37_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.37 summary written to {out_path}")

    def _sig(sub_df):
        s = sub_df[sub_df["p"] < 0.05]
        return ", ".join(f"{r.stratum}/{r.predictor}/{r.outcome} (p={r.p:.3g})" for r in s.itertuples()) or "none"

    grp = summary[summary["stratum"] != "all"]
    pm25_t2dm = grp[(grp["stratum"].str.startswith("T2DM")) & (grp["predictor"] == "log_pm25")]
    pm25_healthy = grp[(grp["stratum"] == "Healthy") & (grp["predictor"] == "log_pm25")]
    pm25_predm = grp[(grp["stratum"] == "Pre-DM") & (grp["predictor"] == "log_pm25")]
    result_summary = (
        f"3-group split (Healthy N={int(df['status_3group'].eq('Healthy').sum())}, "
        f"Pre-DM N={int(df['status_3group'].eq('Pre-DM').sum())}, "
        f"T2DM=Oral+Insulin N={int(df['status_3group'].eq('T2DM (Oral Med+Insulin)').sum())}). "
        f"Significant: {_sig(grp)}. "
        f"PM2.5 -> blood sugar: {int((pm25_t2dm['p'] < 0.05).sum())}/4 outcomes in T2DM, "
        f"{int((pm25_predm['p'] < 0.05).sum())}/4 in Pre-DM, {int((pm25_healthy['p'] < 0.05).sum())}/4 in Healthy. "
        f"Keeping Healthy and Pre-DM separate (the reviewer-safe split) {'preserves' if int((pm25_t2dm['p'] < 0.05).sum()) >= 3 else 'weakens'} "
        f"EG.36's result -- the PM2.5 signal is still {'concentrated in the T2DM group' if int((pm25_t2dm['p'] < 0.05).sum()) >= 3 and int((pm25_healthy['p'] < 0.05).sum()) <= 1 else 'less cleanly separated than in the 2-group version'}."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.37", summary, paper="p2",
        method="Rerun of EG.35/EG.36's design (PM2.5 and BMI each net of the other + age + site, across "
                "hba1c/glucose_cv/tar_180/interday_glucose_variance) with a 3-group diabetic-status "
                "split: Healthy, Pre-DM, and T2DM (Oral Med + Insulin combined). Reviewer-safe version "
                "of EG.36 -- keeps Healthy and Pre-DM separate while still combining the two T2DM "
                "treatment arms. Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
