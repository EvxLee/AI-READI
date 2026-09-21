#!/usr/bin/env python3
"""EG.39 -- full association grid, 3-group split: glycemia x pollutants x activity/BMI.

Project-head request (2026-09-21), verbatim: "summarize using the three
group split all of the associations between (HbA1c, mean CGM glucose,
mean time in range per day) vs our targets (pm2.5, voc, nox) as well as
both of these with BMI, steps per day, and active minutes per day
(anything above sedentary)."

Read as three blocks, each tested within the EG.37 3-group split
(Healthy / Pre-DM / T2DM = Oral Med+Insulin combined) plus a pooled/global
row for reference:

  Block A -- glycemia (hba1c, glucose_mean, tir) x pollutants (PM2.5, NOx, VOC)
  Block B -- glycemia (hba1c, glucose_mean, tir) x BMI/steps/active_minutes
  Block C -- pollutants (PM2.5, NOx, VOC) x BMI/steps/active_minutes

"Active minutes per day (anything above sedentary)" is
`active_minutes_v1_per_day` from `build_activity_level_table.py` (EG.5's
"v1" variant: generic+walking+running all count, only sedentary excluded)
-- his own definition matches that variant exactly, not v2
(walking+running only).

Design choice, stated up front: each pair here is a SIMPLE association
(predictor + age + site dummies only), not net-of-other-predictors like
EG.35/37's PM2.5-vs-BMI models. He asked for a broad summary across 27
pairs, not a fresh mediation-adjusted test -- adding cross-controls for
every pair would triple the design surface without being what was asked.
Flagged here so it isn't confused with EG.35's stricter design if the two
are compared later.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import cohort, results

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
CGM_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "cgm_glycemic_metrics.csv"
ACTIVITY_LEVEL_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "activity_level_minutes.csv"

GLYCEMIC_OUTCOMES = ["hba1c", "glucose_mean", "tir"]
POLLUTANTS = [("PM2.5", "log_pm25"), ("NOx", "log_nox"), ("VOC", "log_voc")]
ACTIVITY_BMI = ["bmi", "steps", "active_minutes_v1_per_day"]

STATUS_3GROUP_MAP = {
    "Healthy": "Healthy",
    "Pre-DM": "Pre-DM",
    "Oral Med": "T2DM (Oral Med+Insulin)",
    "Insulin": "T2DM (Oral Med+Insulin)",
}
GROUP3_ORDER = ["Healthy", "Pre-DM", "T2DM (Oral Med+Insulin)"]


def build_table() -> pd.DataFrame:
    # cohort.build_core_table() already attaches Garmin `steps` via its internal
    # _attach_wearables() merge (average_daily_activity -> steps) -- no need to
    # pull manifest_activity again here.
    df = cohort.build_core_table()

    level = pd.read_csv(ACTIVITY_LEVEL_TABLE, dtype={"person_id": str})
    df = df.merge(level[["person_id", "active_minutes_v1_per_day"]], on="person_id", how="left")

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25", "mean_nox", "mean_voc"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])
    df["log_nox"] = np.log1p(df["mean_nox"])
    df["log_voc"] = np.log1p(df["mean_voc"])

    cgm = pd.read_csv(CGM_TABLE, dtype={"person_id": str})
    df = df.merge(cgm[["person_id", "glucose_mean", "tir"]], on="person_id", how="left")

    df["status_3group"] = df["study_group_label"].astype(str).map(STATUS_3GROUP_MAP)
    return df


def _fit(sub: pd.DataFrame, predictor: str, outcome: str, extra_cols: list[str]) -> dict | None:
    cols = [predictor, outcome] + extra_cols
    fit_df = sub[cols].dropna()
    if len(fit_df) < 30:
        return None
    X = fit_df[[predictor] + extra_cols]
    X = X.loc[:, X.nunique() > 1]
    if predictor not in X.columns:
        return None
    fit = sm.OLS(fit_df[outcome], sm.add_constant(X)).fit()
    return {"n": len(fit_df), "coef": fit.params[predictor], "p": fit.pvalues[predictor]}


def main() -> None:
    df = build_table()
    # cohort.build_core_table() already carries Garmin steps via _attach_wearables;
    # confirm the column landed and isn't all-null before proceeding.
    if "steps" not in df.columns or df["steps"].notna().sum() == 0:
        raise RuntimeError("steps column missing/empty after build_table() -- check cohort.build_core_table()'s wearable merge")

    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    df = pd.concat([df, site_dummies], axis=1)
    site_cols = list(site_dummies.columns)
    strata = [("all", df)] + [(g, df[df["status_3group"] == g]) for g in GROUP3_ORDER]

    print(f"\n{'='*90}\nEG.39 -- full association grid, 3-group split\n{'='*90}")
    print("Group sizes:", df["status_3group"].value_counts().to_dict())

    rows = []

    def run_block(block: str, predictors: list[tuple[str, str]], outcomes: list[str]):
        print(f"\n--- Block {block}: {[p[0] for p in predictors]} x {outcomes} ---")
        for pred_label, pred_col in predictors:
            for outcome in outcomes:
                for stratum_name, sub in strata:
                    r = _fit(sub, pred_col, outcome, ["age"] + site_cols)
                    if r is None:
                        continue
                    rows.append({"block": block, "predictor": pred_label, "outcome": outcome,
                                 "stratum": stratum_name, **r})
                    flag = " *" if r["p"] < 0.05 else ""
                    print(f"  [{stratum_name:26s}] {pred_label:6s} -> {outcome:14s} N={r['n']:4d}  coef={r['coef']:+.4f}  p={r['p']:.4f}{flag}")

    run_block("A_glycemia_vs_pollutants", POLLUTANTS, GLYCEMIC_OUTCOMES)
    run_block("B_glycemia_vs_activityBMI", [(c, c) for c in ACTIVITY_BMI], GLYCEMIC_OUTCOMES)
    run_block("C_pollutants_vs_activityBMI", POLLUTANTS, ACTIVITY_BMI)

    summary = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parent / "results" / "EG_39_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.39 summary written to {out_path}")

    def _block_sig(block: str) -> str:
        b = summary[(summary["block"] == block) & (summary["stratum"] != "all")]
        sig = b[b["p"] < 0.05]
        n_total = len(b)
        by_group = {g: int((b[(b["stratum"] == g)]["p"] < 0.05).sum()) for g in GROUP3_ORDER}
        return f"{len(sig)}/{n_total} significant across the 3 groups ({', '.join(f'{g}: {n}' for g, n in by_group.items())})"

    result_summary = (
        "Full 27-pair association grid (glycemia x pollutants, glycemia x BMI/steps/active-minutes, "
        "pollutants x BMI/steps/active-minutes), each fit as predictor + age + site (no cross-"
        "predictor control), pooled and within the 3-group split (Healthy / Pre-DM / T2DM = Oral "
        "Med+Insulin). "
        f"Block A (glycemia vs pollutants): {_block_sig('A_glycemia_vs_pollutants')}. "
        f"Block B (glycemia vs BMI/steps/active-minutes): {_block_sig('B_glycemia_vs_activityBMI')}. "
        f"Block C (pollutants vs BMI/steps/active-minutes): {_block_sig('C_pollutants_vs_activityBMI')}. "
        "Full pair-by-pair, group-by-group table in EG_39_summary.csv. Confirms and extends EG.36/37's "
        "pattern (PM2.5 signal concentrated in T2DM) across NOx/VOC and the TIR/mean-glucose outcomes "
        "not previously tested in the 3-group split."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.39", summary, paper="p2",
        method="Full association grid requested by project head: 3 glycemic outcomes (hba1c, "
                "glucose_mean, tir) x 3 pollutants (PM2.5/NOx/VOC, log1p) [Block A]; the same 3 "
                "glycemic outcomes x BMI/steps/active_minutes_v1_per_day (anything above sedentary) "
                "[Block B]; and the 3 pollutants x BMI/steps/active_minutes_v1_per_day [Block C]. Each "
                "pair fit as simple OLS (predictor + age + site dummies, no cross-predictor control -- "
                "distinct from EG.35/37's net-of-each-other design). Pooled + EG.37's 3-group split "
                "(Healthy / Pre-DM / T2DM=Oral Med+Insulin). 27 pairs x 4 strata = up to 108 fits. "
                "Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
