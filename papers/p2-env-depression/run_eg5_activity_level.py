#!/usr/bin/env python3
"""EG.5 -- rebuild the mediation chain with activity-level minutes instead of steps.

`steps` failed both mediation links (EG.2/EG.3: significant but backwards
direction; EG.4: not significant at all). Project head asked (2026-08-17)
whether we're using the raw minutes-in-activity-level breakdown instead of
manifest steps -- we weren't. `build_activity_level_table.py` builds this
from the raw Garmin `physical_activity` stream's `sedentary`/`generic`/
`walking`/`running` interval labels, with two grouping variants:

  * v1 -- anything above sedentary counts as active (generic+walking+running)
  * v2 -- only walking+running counts as active (sedentary+generic = inactive)

This script reruns both mediation links with `active_minutes_v1_per_day`
and `active_minutes_v2_per_day` in place of `steps`, keeping
`active_calories` and `bmi` exactly as they were in EG.2-EG.4. `age` stays
a continuous covariate, not a stratification variable, matching every
other model in this chain.

Link 1 (pollution -> activity/BMI, pooled + per-site): EG.5a / EG.5b
Link 2 (activity/BMI -> glycemic control): EG.5c
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables
from aireadi.constants import SITES

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"
ACTIVITY_LEVEL_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "activity_level_minutes.csv"

ACTIVE_VARIANTS = ["active_minutes_v1_per_day", "active_minutes_v2_per_day"]
CANDIDATE_OUTCOMES = ["glucose_mean", "glucose_cv", "tar_180", "spikes_per_day_180"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    extra = activity[["person_id", "average_active_calories_kcal"]].rename(
        columns={"average_active_calories_kcal": "active_calories"}
    )
    df = df.merge(extra, on="person_id", how="left")

    level = pd.read_csv(ACTIVITY_LEVEL_TABLE, dtype={"person_id": str})
    df = df.merge(level[["person_id", *ACTIVE_VARIANTS]], on="person_id", how="left")

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", *CANDIDATE_OUTCOMES]], on="person_id", how="left")
    return df


def _fit_ols(model_df: pd.DataFrame, outcome: str) -> dict:
    X = sm.add_constant(model_df.drop(columns=outcome))
    y = model_df[outcome]
    fit = sm.OLS(y, X).fit()
    return {"n": len(model_df), "r2": fit.rsquared, "fit": fit}


def run_eg5a_pooled(df: pd.DataFrame) -> None:
    print(f"\n{'='*90}\nEG.5a -- link 1, pooled: active_minutes/BMI ~ log(PM2.5) + age + site\n{'='*90}")

    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    outcomes = ACTIVE_VARIANTS + ["active_calories", "bmi"]
    rows = []
    for outcome in outcomes:
        model_df = pd.concat([df[[outcome, "log_pm25", "age"]], site_dummies], axis=1).dropna()
        res = _fit_ols(model_df, outcome)
        fit = res["fit"]
        p, coef = fit.pvalues["log_pm25"], fit.params["log_pm25"]
        print(f"\n--- outcome = {outcome}  (N={res['n']}, R2={res['r2']:.3f}) ---")
        print(f"  log_pm25: coef={coef:.4f}, p={p:.4g}")
        rows.append({"outcome": outcome, "n": res["n"], "r2": res["r2"], "log_pm25_coef": coef, "log_pm25_p": p})

    summary = pd.DataFrame(rows)
    sig = summary[summary["log_pm25_p"] < 0.05]
    sig_list = ", ".join(
        f"{r.outcome} (p={r.log_pm25_p:.3g}, coef={'+ ' if r.log_pm25_coef > 0 else '- '}{abs(r.log_pm25_coef):.4f})"
        for r in sig.itertuples()
    )
    result_summary = f"Pooled across all 3 sites. log(PM2.5) significant (p<0.05) for: {sig_list if sig_list else 'none'}."
    print(f"\n{result_summary}")
    results.save(
        "EG.5a", summary, paper="p2",
        method="OLS, pooled across all 3 sites: active_minutes_v1_per_day / active_minutes_v2_per_day "
                "/ active_calories / bmi ~ log1p(PM2.5) + age + clinical_site dummies. EG.5 rework of "
                "EG.2, replacing steps with the raw activity-level-minutes measure.",
        result=result_summary,
        decision="keep",
    )


def run_eg5b_per_site(df: pd.DataFrame) -> None:
    print(f"\n{'='*90}\nEG.5b -- link 1, per-site: active_minutes/BMI ~ log(PM2.5) + age\n{'='*90}")

    outcomes = ACTIVE_VARIANTS + ["active_calories", "bmi"]
    rows = []
    for site in SITES:
        sub = df[df["clinical_site"] == site]
        for outcome in outcomes:
            model_df = sub[[outcome, "log_pm25", "age"]].dropna()
            if len(model_df) < 30:
                continue
            res = _fit_ols(model_df, outcome)
            fit = res["fit"]
            p, coef = fit.pvalues["log_pm25"], fit.params["log_pm25"]
            print(f"\n--- site={site}, outcome={outcome}  (N={res['n']}, R2={res['r2']:.3f}) ---")
            print(f"  log_pm25: coef={coef:.4f}, p={p:.4g}")
            rows.append({"site": site, "outcome": outcome, "n": res["n"], "r2": res["r2"],
                         "log_pm25_coef": coef, "log_pm25_p": p})

    summary = pd.DataFrame(rows)
    sig = summary[summary["log_pm25_p"] < 0.05]
    sig_list = ", ".join(
        f"{r.site}/{r.outcome} (p={r.log_pm25_p:.3g}, coef={'+ ' if r.log_pm25_coef > 0 else '- '}{abs(r.log_pm25_coef):.4f})"
        for r in sig.itertuples()
    )
    result_summary = f"Per-site (no pooling). log(PM2.5) significant (p<0.05) for: {sig_list if sig_list else 'none'}."
    print(f"\n{result_summary}")
    results.save(
        "EG.5b", summary, paper="p2",
        method="OLS, refit separately within each of the 3 sites: active_minutes_v1_per_day / "
                "active_minutes_v2_per_day / active_calories / bmi ~ log1p(PM2.5) + age. EG.5 rework "
                "of EG.3, replacing steps.",
        result=result_summary,
        decision="keep",
    )


def run_eg5c_second_link(df: pd.DataFrame) -> None:
    print(f"\n{'='*90}\nEG.5c -- link 2: glycemic control ~ active_minutes + active_calories + bmi + age + severity\n{'='*90}")

    predictors_base = ["active_calories", "bmi", "age"]
    rows = []
    for active_var in ACTIVE_VARIANTS:
        predictors = [active_var] + predictors_base
        for outcome in CANDIDATE_OUTCOMES:
            severity_dummies = pd.get_dummies(df["study_group_label"], prefix="sev", drop_first=True, dtype=float)
            site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
            model_df = pd.concat(
                [df[[outcome] + predictors], severity_dummies, site_dummies], axis=1
            ).dropna()
            n = len(model_df)

            X = sm.add_constant(model_df.drop(columns=outcome))
            y = model_df[outcome]
            fit = sm.OLS(y, X).fit()

            table = pd.DataFrame({"coefficient": fit.params, "p_value": fit.pvalues}).drop(index="const")
            table = table[table.index.isin(predictors)].sort_values("p_value")

            print(f"\n--- active_var={active_var}, outcome={outcome}  (N={n}, R2={fit.rsquared:.3f}) ---")
            print(table.round(4).to_string())

            active_row = table.loc[active_var]
            cal_row = table.loc["active_calories"]
            bmi_row = table.loc["bmi"]
            rows.append({
                "active_variant": active_var, "outcome": outcome, "n": n, "r2": fit.rsquared,
                "active_coef": active_row["coefficient"], "active_p": active_row["p_value"],
                "active_calories_coef": cal_row["coefficient"], "active_calories_p": cal_row["p_value"],
                "bmi_coef": bmi_row["coefficient"], "bmi_p": bmi_row["p_value"],
            })

            out_table = table.reset_index().rename(columns={"index": "predictor"})
            out_table.insert(0, "outcome", outcome)
            out_table.insert(0, "active_variant", active_var)
            out_table.insert(2, "n", n)
            results.save(
                f"EG.5c_{active_var}_{outcome}", out_table, paper="p2",
                method=f"OLS: {outcome} ~ {active_var} + active_calories + bmi + age + severity-group "
                        f"dummies + site dummies. EG.5 rework of EG.4, replacing steps with {active_var}.",
                result=f"N={n}, R2={fit.rsquared:.3f}. {active_var} p={active_row['p_value']:.3g}, "
                        f"active_calories p={cal_row['p_value']:.3g}, bmi p={bmi_row['p_value']:.3g}.",
                decision="keep",
            )

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_5c_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.5c cross-outcome summary written to {summary_path}")
    print(summary.round(4).to_string(index=False))

    n_active_sig = int((summary["active_p"] < 0.05).sum())
    top_summary = (
        f"Across {len(ACTIVE_VARIANTS)} active-minutes variants x {len(CANDIDATE_OUTCOMES)} outcomes "
        f"({len(summary)} fits), the active-minutes predictor significant (p<0.05) in {n_active_sig}/{len(summary)}. "
        f"See EG_5c_summary.csv for per-fit detail; compare against EG.4 where steps was significant in 0/4."
    )
    results.save(
        "EG.5c", summary, paper="p2",
        method="Cross-outcome summary of EG.5's second link (see EG.5c_<variant>_<outcome> rows for "
                "each individual fit): tests active_minutes_v1_per_day and active_minutes_v2_per_day "
                "(in place of steps) against 4 candidate glycemic-control outcomes, controlling for "
                "active_calories, bmi, age, and severity group.",
        result=top_summary,
        decision="keep",
    )


def main() -> None:
    df = build_table()
    run_eg5a_pooled(df)
    run_eg5b_per_site(df)
    run_eg5c_second_link(df)


if __name__ == "__main__":
    main()
