#!/usr/bin/env python3
"""EG.20 -- reverse direction, all CGM features together in one model per environmental outcome.

EG.16/EG.19 tested each glycemic predictor (glucose_mean, glucose_cv,
intraday/interday variance, hba1c) one at a time against each
environmental outcome -- 5 separate univariate models per outcome. The
project head's phrasing ("the input CGM features + covariates") means all
of them together as simultaneous predictors in a single model, not five
separate single-predictor models. This is the complete version of that
request: one multivariate model per environmental outcome, all 5 glycemic
features + bmi + age + site as predictors at once.

Same exploratory/correlational framing as EG.16/EG.19 -- environmental
exposure isn't plausibly caused by blood sugar, so this is read as "which
glycemic marker(s) independently co-vary with which exposure metric, once
the others are accounted for," not a mechanism test.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"
VARIABILITY_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "glucose_variability_metrics.csv"

GLYCEMIC_PREDICTORS = ["glucose_mean", "glucose_cv", "intraday_glucose_variance", "interday_glucose_variance", "hba1c"]
BASE_COVARIATES = ["bmi", "age"]

ENV_OUTCOMES = [
    ("log_pm25", "mean_pm25", True),
    ("log_nox", "mean_nox", True),
    ("log_voc", "mean_voc", True),
    ("mean_temp", "mean_temp", False),
    ("mean_hum", "mean_hum", False),
    ("mean_light", "mean_light", False),
]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(
        env[["person_id", "mean_pm25", "mean_nox", "mean_voc", "mean_temp", "mean_hum", "mean_light"]],
        on="person_id", how="left",
    )
    df["log_pm25"] = np.log1p(df["mean_pm25"])
    df["log_nox"] = np.log1p(df["mean_nox"])
    df["log_voc"] = np.log1p(df["mean_voc"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", "glucose_mean", "glucose_cv"]], on="person_id", how="left")

    var_table = pd.read_csv(VARIABILITY_TABLE, dtype={"person_id": str})
    df = df.merge(
        var_table[["person_id", "intraday_glucose_variance", "interday_glucose_variance"]],
        on="person_id", how="left",
    )
    return df


def main() -> None:
    df = build_table()
    print(f"\n{'='*90}\nEG.20 -- reverse direction, all 5 CGM features together per environmental outcome\n{'='*90}")

    predictors = GLYCEMIC_PREDICTORS + BASE_COVARIATES
    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)

    rows = []
    for env_col, _raw_col, _is_log in ENV_OUTCOMES:
        model_df = pd.concat([df[[env_col] + predictors], site_dummies], axis=1).dropna()
        n = len(model_df)

        X = sm.add_constant(model_df.drop(columns=env_col))
        y = model_df[env_col]
        fit = sm.OLS(y, X).fit()

        print(f"\n--- outcome = {env_col}  (N={n}, R2={fit.rsquared:.3f}) ---")
        table = pd.DataFrame({"coefficient": fit.params, "p_value": fit.pvalues}).drop(index="const")
        table = table[table.index.isin(GLYCEMIC_PREDICTORS)].sort_values("p_value")
        print(table.round(6).to_string())

        for predictor in GLYCEMIC_PREDICTORS:
            rows.append({
                "env_outcome": env_col, "glycemic_predictor": predictor, "n": n, "r2": fit.rsquared,
                "coef": table.loc[predictor, "coefficient"], "p_value": table.loc[predictor, "p_value"],
            })

        out_table = table.reset_index().rename(columns={"index": "predictor"})
        out_table.insert(0, "env_outcome", env_col)
        out_table.insert(1, "n", n)
        sig = table[table["p_value"] < 0.05]
        sig_list = ", ".join(f"{p} (p={r.p_value:.3g})" for p, r in sig.iterrows())
        results.save(
            f"EG.20_{env_col}", out_table, paper="p2",
            method=f"OLS, multivariate: {env_col} ~ all 5 glycemic features simultaneously "
                    f"(glucose_mean + glucose_cv + intraday_glucose_variance + "
                    f"interday_glucose_variance + hba1c) + bmi + age + site dummies.",
            result=f"N={n}, R2={fit.rsquared:.3f}. Significant (p<0.05): {sig_list if sig_list else 'none'}.",
            decision="keep",
        )

    summary = pd.DataFrame(rows)
    summary_path = Path(__file__).resolve().parent / "results" / "EG_20_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nEG.20 summary written to {summary_path}")

    sig = summary[summary["p_value"] < 0.05].sort_values("p_value")
    print(f"\n{'='*90}\nEG.20 -- significant (p<0.05) results across all 6 outcomes\n{'='*90}")
    print(sig.round(6).to_string(index=False))

    sig_list = ", ".join(f"{r.env_outcome}~{r.glycemic_predictor} (p={r.p_value:.3g})" for r in sig.itertuples())
    result_summary = (
        f"Multivariate version of EG.19 -- all 5 glycemic features together in one model per "
        f"environmental outcome, instead of 5 separate univariate models. {len(sig)}/30 "
        f"significant at p<0.05: {sig_list if sig_list else 'none'}. Compare against EG.19's "
        f"univariate results to see which predictors survive once the others are controlled for."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.20", summary, paper="p2",
        method="OLS, multivariate: environmental_metric ~ glucose_mean + glucose_cv + "
                "intraday_glucose_variance + interday_glucose_variance + hba1c (all 5 together) "
                "+ bmi + age + site dummies, for each of 6 environmental outcomes. Completes the "
                "project head's request for 'CGM features + covariates' as a single combined "
                "model, not 5 separate single-predictor models (EG.16/EG.19).",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
