#!/usr/bin/env python3
"""EG.1 (primary model) and ECGM.2 (age-group CGM comparison).

EG.1 is the paper's central claim under the 2026-08-11 pivot (see PLAN.md /
PRESPEC.md Amendment): does an environmental term survive in a model of
glycemic control, once BMI, wearable behavior, age, and severity group are
controlled for? PRESPEC's amendment deliberately left the exact outcome
metric open pending inspection of `cgm_glycemic_metrics.csv`'s distribution
-- glucose_mean and tar_180 are both heavily right-skewed (skew 2.5, 2.4),
glucose_cv and spikes_per_day_180 much less so (skew 1.2, 1.1). Rather than
pick one now, this runs the same predictor set against four candidate
outcomes and reports all four, so the choice of headline metric can be made
from real numbers, not a guess.

ECGM.2 answers the project head's specific question: does glycemic control
differ between the insulin-dependent age<70 subgroup and the 70+ group, or
is it purely a severity effect (same for both ages once you're in the most
severe group)?
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from aireadi import azure_io, cohort, results, wearables

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"

PREDICTORS = [
    "log_pm25", "mean_temp", "mean_hum", "mean_light", "mean_voc", "mean_nox",
    "bmi", "steps", "stress", "heart_rate", "sleep_hours", "active_calories",
    "age",
]

CANDIDATE_OUTCOMES = ["glucose_mean", "glucose_cv", "tar_180", "spikes_per_day_180"]


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
    df = df.merge(
        cgm[["person_id", *CANDIDATE_OUTCOMES]],
        on="person_id", how="left",
    )
    return df


def run_eg1(df: pd.DataFrame) -> None:
    print(f"\n{'='*90}\nEG.1 -- primary model: glycemic control ~ environment + BMI + wearables + age + severity\n{'='*90}")

    rows = []
    for outcome in CANDIDATE_OUTCOMES:
        site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
        severity_dummies = pd.get_dummies(df["study_group_label"], prefix="sev", drop_first=True, dtype=float)
        model_df = pd.concat(
            [df[[outcome] + PREDICTORS], site_dummies, severity_dummies], axis=1
        ).dropna()
        n = len(model_df)

        X = sm.add_constant(model_df.drop(columns=outcome))
        y = model_df[outcome]
        fit = sm.OLS(y, X).fit()

        print(f"\n--- outcome = {outcome}  (N={n}, R2={fit.rsquared:.3f}) ---")
        table = pd.DataFrame({
            "coefficient": fit.params, "p_value": fit.pvalues,
        }).drop(index="const")
        table = table[table.index.isin(PREDICTORS)].sort_values("p_value")
        print(table.round(4).to_string())

        env_row = table.loc["log_pm25"]
        bmi_row = table.loc["bmi"]
        rows.append({
            "outcome": outcome, "n": n, "r2": fit.rsquared,
            "log_pm25_coef": env_row["coefficient"], "log_pm25_p": env_row["p_value"],
            "bmi_coef": bmi_row["coefficient"], "bmi_p": bmi_row["p_value"],
        })

        env_table = table.reset_index().rename(columns={"index": "predictor"})
        env_table.insert(0, "outcome", outcome)
        env_table.insert(1, "n", n)
        results.save(
            f"EG.1_{outcome}", env_table, paper="p2",
            method=f"OLS: {outcome} ~ log1p(PM2.5) + env vars + BMI + wearables + age + "
                    f"severity-group dummies + site dummies",
            result=f"N={n}, R2={fit.rsquared:.3f}. log_pm25 p={env_row['p_value']:.3g}, "
                    f"bmi p={bmi_row['p_value']:.3g}.",
            decision="keep",
        )

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_1_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.1 cross-outcome summary written to {summary_path}")
    print(summary.round(4).to_string(index=False))

    n_env_sig = int((summary["log_pm25_p"] < 0.05).sum())
    n_bmi_sig = int((summary["bmi_p"] < 0.05).sum())
    top_summary = (
        f"Across {len(CANDIDATE_OUTCOMES)} candidate glycemic-control outcomes ({', '.join(CANDIDATE_OUTCOMES)}), "
        f"log(PM2.5) significant (p<0.05) in {n_env_sig}/{len(CANDIDATE_OUTCOMES)}; "
        f"BMI significant in {n_bmi_sig}/{len(CANDIDATE_OUTCOMES)}. See EG_1_summary.csv for per-outcome detail."
    )
    results.save(
        "EG.1", summary, paper="p2",
        method="Cross-outcome summary of the primary model (see EG.1_<outcome> rows for each "
                "individual fit): tests log(PM2.5) and BMI against 4 candidate CGM-derived "
                "glycemic-control outcomes (glucose_mean, glucose_cv, tar_180, spikes_per_day_180).",
        result=top_summary,
        decision="keep",
    )


def run_ecgm2(df: pd.DataFrame) -> None:
    print(f"\n{'='*90}\nECGM.2 -- CGM metrics, insulin-dependent age<70 vs 70+\n{'='*90}")

    insulin = df[df["study_group_label"] == "Insulin"].copy()
    under70 = insulin[insulin["age"] < 70]
    over70 = insulin[insulin["age"] >= 70]
    print(f"N under-70 = {len(under70)}, N 70+ = {len(over70)}")

    rows = []
    for metric in CANDIDATE_OUTCOMES + ["tar_140", "tbr_70", "mage"]:
        a = under70[metric].dropna() if metric in under70.columns else pd.Series(dtype=float)
        # tar_140/tbr_70/mage aren't in `df` yet (only the 4 candidates were merged in build_table);
        # re-pull from the CGM table directly for these three.
        rows.append(metric)

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    insulin_ids = insulin[["person_id", "age"]].merge(cgm, on="person_id", how="left")
    under70_full = insulin_ids[insulin_ids["age"] < 70]
    over70_full = insulin_ids[insulin_ids["age"] >= 70]

    metrics = ["glucose_mean", "glucose_cv", "tar_140", "tar_180", "tbr_70",
               "spikes_per_day_180", "minutes_above_180_per_day", "mage"]
    comparison_rows = []
    for m in metrics:
        a = under70_full[m].dropna()
        b = over70_full[m].dropna()
        if len(a) > 3 and len(b) > 3:
            u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        else:
            p = float("nan")
        comparison_rows.append({
            "metric": m,
            "under70_n": len(a), "under70_mean": a.mean(), "under70_median": a.median(),
            "over70_n": len(b), "over70_mean": b.mean(), "over70_median": b.median(),
            "mannwhitney_p": p,
        })
    comparison = pd.DataFrame(comparison_rows).set_index("metric")
    print(comparison.round(3).to_string())

    sig = comparison[comparison["mannwhitney_p"] < 0.05]
    sig_list = ", ".join(sig.index) if len(sig) else "none"
    result_summary = (
        f"Insulin-dependent subgroup: N(<70)={len(under70_full)}, N(70+)={len(over70_full)}. "
        f"Metrics differing significantly by age (p<0.05, Mann-Whitney): {sig_list}."
    )
    results.save(
        "ECGM.2", comparison, paper="p2",
        method="Mann-Whitney U comparing 8 CGM-derived glycemic-control metrics between the "
                "insulin-dependent age<70 subgroup and the insulin-dependent 70+ group.",
        result=result_summary,
        decision="keep",
    )


def main() -> None:
    df = build_table()
    run_eg1(df)
    run_ecgm2(df)


if __name__ == "__main__":
    main()
