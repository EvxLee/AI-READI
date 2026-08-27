#!/usr/bin/env python3
"""EG.27 -- does environmental exposure relate to SDOH / survey measures?

Project head's follow-up (2026-08-26/27): "do a deep dive into how
environmental sensor data relates to survey data ... especially social
determinants of health including neighborhood security, CESD-10 for
depression, PAID-5 for problem areas in diabetes, dietary survey, and
substance use; if there are links, we can try connecting them to diabetic
severity."

Two-stage design:
  Stage 1: Spearman correlation, pooled across all participants, between
    each of 6 environmental exposure metrics (PM2.5, NOx, VOC, temp,
    humidity, light) and each of 6 SDOH/survey scores (neighborhood,
    CES-D-10, PAID-5, diet, substance-use count, current-smoker) built in
    `build_sdoh_table.py`. Spearman, not Pearson, since several of these
    scores are counts/composites of Likert items rather than continuous
    normal measures. 36 tests total.
  Stage 2 (only for pairs significant in Stage 1): does the SDOH score
    also differ by diabetes severity group (Kruskal-Wallis)? This is the
    "connect them to diabetic severity" follow-up -- only run where
    Stage 1 already found an environment link, to avoid a second blind
    36-test fishing expedition.

No FDR correction applied at this stage (36 tests, purely exploratory,
first pass) -- flagged explicitly in the result summary so it isn't
over-read the way EG.18's uncorrected results were.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kruskal, spearmanr

from aireadi import cohort, results

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
SDOH_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "sdoh_survey_scores.csv"

ENV_METRICS = ["mean_pm25", "mean_nox", "mean_voc", "mean_temp", "mean_hum", "mean_light"]
SDOH_SCORES = ["neighborhood_score", "cesd_total", "paid_total", "diet_score", "substance_use_count", "current_smoker"]
# cesd_total/paid_total already exist on cohort.build_core_table(); pull only the
# new columns from the SDOH build to avoid a _x/_y merge collision.
SDOH_ONLY_NEW = [c for c in SDOH_SCORES if c not in ("cesd_total", "paid_total")]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    sdoh = pd.read_csv(SDOH_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id"] + ENV_METRICS], on="person_id", how="left")
    df = df.merge(sdoh[["person_id"] + SDOH_ONLY_NEW], on="person_id", how="left")
    return df


def main() -> None:
    df = build_table()
    print(f"\n{'='*90}\nEG.27 -- environmental exposure vs SDOH/survey scores, pooled Spearman\n{'='*90}")

    rows = []
    for env_col in ENV_METRICS:
        for sdoh_col in SDOH_SCORES:
            pair = df[[env_col, sdoh_col]].dropna()
            n = len(pair)
            if n < 30:
                continue
            rho, p = spearmanr(pair[env_col], pair[sdoh_col])
            rows.append({"env_metric": env_col, "sdoh_score": sdoh_col, "n": n, "spearman_rho": rho, "p_value": p})

    stage1 = pd.DataFrame(rows).sort_values("p_value")
    print(stage1.round(5).to_string(index=False))

    sig1 = stage1[stage1["p_value"] < 0.05]
    print(f"\nStage 1 significant (p<0.05, uncorrected, 36 tests): {len(sig1)}/{len(stage1)}")

    # Stage 2: for each significant env-SDOH pair, does the SDOH score
    # differ by severity group?
    stage2_rows = []
    for _, r in sig1.iterrows():
        sdoh_col = r["sdoh_score"]
        groups = [g[sdoh_col].dropna().values for _, g in df.groupby("study_group_label") if g[sdoh_col].notna().sum() >= 10]
        if len(groups) < 2:
            continue
        stat, p2 = kruskal(*groups)
        stage2_rows.append({
            "env_metric": r["env_metric"], "sdoh_score": sdoh_col,
            "stage1_rho": r["spearman_rho"], "stage1_p": r["p_value"],
            "severity_kruskal_stat": stat, "severity_kruskal_p": p2,
        })
    stage2 = pd.DataFrame(stage2_rows).drop_duplicates(subset="sdoh_score").sort_values("severity_kruskal_p") if stage2_rows else pd.DataFrame()
    if not stage2.empty:
        print(f"\n--- Stage 2: SDOH scores with a Stage-1 environment link, checked against severity group ---")
        print(stage2.round(5).to_string(index=False))

    out_path = Path(__file__).resolve().parent / "results" / "EG_27_summary.csv"
    stage1.to_csv(out_path, index=False)
    stage2_path = Path(__file__).resolve().parent / "results" / "EG_27_stage2_severity.csv"
    if not stage2.empty:
        stage2.to_csv(stage2_path, index=False)
    print(f"\nEG.27 stage 1 written to {out_path}" + (f", stage 2 to {stage2_path}" if not stage2.empty else ""))

    sig1_list = ", ".join(
        f"{r.env_metric}/{r.sdoh_score} (rho={r.spearman_rho:.3f}, p={r.p_value:.3g})" for r in sig1.itertuples()
    )
    severity_list = ", ".join(
        f"{r.sdoh_score} (p={r.severity_kruskal_p:.3g})" for r in stage2.itertuples()
    ) if not stage2.empty else "none tested (no Stage-1 hits)"
    result_summary = (
        f"Stage 1 (pooled Spearman, 36 tests, uncorrected): {len(sig1)}/36 significant at p<0.05: "
        f"{sig1_list if sig1_list else 'none'}. Stage 2 (severity-group differences for SDOH scores "
        f"with a Stage-1 environment link, Kruskal-Wallis): {severity_list}. Exploratory first pass, "
        f"no multiple-comparison correction applied -- treat as hypothesis-generating, not confirmatory."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.27", stage1, paper="p2",
        method="Stage 1: Spearman correlation, pooled, between 6 environmental exposure metrics "
                "(PM2.5/NOx/VOC/temp/humidity/light) and 6 SDOH/survey scores (PhenX neighborhood "
                "battery z-score composite, CES-D-10 total, PAID-5 total, dietary survey score, "
                "substance-use current-use count, current-smoker flag) built in build_sdoh_table.py. "
                "Stage 2: for any Stage-1-significant pair, Kruskal-Wallis test of that SDOH score "
                "across the 4 severity groups.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
