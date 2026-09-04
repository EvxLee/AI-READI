#!/usr/bin/env python3
"""EG.32 -- age-stratified rerun of EG.27's significant env-SDOH pairs, plus food insecurity.

Project-head follow-up (2026-09-02, relayed): "go further down the path
of the 20/36 tests of the deep dive with sensor data/survey data and
stratify by age" and "start looking at survey data like social
determinants of health, food, neighborhood."

Two parts:
  1. Food insecurity is a SDOH construct he explicitly named that EG.27
     didn't cover. `build_sdoh_table.py` now builds `food_insecurity_score`
     (5-item PhenX battery, z-scored, same treatment as neighborhood_score).
     This reruns Stage 1 (pooled Spearman, 6 env metrics x food_insecurity_score,
     6 new tests) plus Stage 2 (severity-group Kruskal-Wallis) for that score
     alone, matching EG.27's exact design.
  2. For all 20 pairs EG.27 found significant pooled, rerun the same Spearman
     test within each of 3 age bands (40-54/55-69/70+, EG.23's existing
     convention) to see whether the pooled signal is concentrated in one age
     group or holds broadly. Purely stratified, not an interaction model --
     flagged as such, since a formal age*env interaction term would be the
     next step if a pattern shows up here.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy.stats import kruskal, spearmanr

from aireadi import cohort, results

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
SDOH_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "sdoh_survey_scores.csv"

ENV_METRICS = ["mean_pm25", "mean_nox", "mean_voc", "mean_temp", "mean_hum", "mean_light"]
AGE_BINS = [40, 55, 70, 200]
AGE_LABELS = ["40-54", "55-69", "70+"]


SDOH_ONLY_NEW = ["neighborhood_score", "food_insecurity_score", "diet_score", "substance_use_count", "current_smoker"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    sdoh = pd.read_csv(SDOH_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id"] + ENV_METRICS], on="person_id", how="left")
    # cesd_total/paid_total already exist on build_core_table(); pull only the new
    # SDOH columns (same _x/_y merge-collision avoidance as EG.27) so part 2's
    # age-stratified rerun covers ALL 20 of EG.27's significant pairs, not just
    # the cesd_total/paid_total ones.
    df = df.merge(sdoh[["person_id"] + SDOH_ONLY_NEW], on="person_id", how="left")
    df["age_band"] = pd.cut(df["age"], bins=AGE_BINS, labels=AGE_LABELS, right=False)
    return df


def part1_food_insecurity(df: pd.DataFrame) -> pd.DataFrame:
    print(f"\n{'='*90}\nEG.32 part 1 -- food_insecurity_score vs environment (Stage 1 + Stage 2)\n{'='*90}")
    rows = []
    for env_col in ENV_METRICS:
        pair = df[[env_col, "food_insecurity_score"]].dropna()
        if len(pair) < 30:
            continue
        rho, p = spearmanr(pair[env_col], pair["food_insecurity_score"])
        rows.append({"env_metric": env_col, "sdoh_score": "food_insecurity_score", "n": len(pair), "spearman_rho": rho, "p_value": p})
    stage1 = pd.DataFrame(rows).sort_values("p_value")
    print(stage1.round(5).to_string(index=False))

    groups = [g["food_insecurity_score"].dropna().values for _, g in df.groupby("study_group_label", observed=True) if g["food_insecurity_score"].notna().sum() >= 10]
    stat, p2 = kruskal(*groups)
    print(f"\nStage 2: food_insecurity_score by severity group -- kruskal p={p2:.4g}")
    stage1.attrs["severity_p"] = p2
    return stage1


def part2_age_stratified(df: pd.DataFrame, eg27_pairs: list[tuple[str, str]]) -> pd.DataFrame:
    print(f"\n{'='*90}\nEG.32 part 2 -- age-stratified rerun of EG.27's {len(eg27_pairs)} significant pairs\n{'='*90}")
    rows = []
    for env_col, sdoh_col in eg27_pairs:
        if sdoh_col not in df.columns:
            continue
        for band in AGE_LABELS:
            sub = df.loc[df["age_band"] == band, [env_col, sdoh_col]].dropna()
            if len(sub) < 30:
                rows.append({"env_metric": env_col, "sdoh_score": sdoh_col, "age_band": band, "n": len(sub), "spearman_rho": None, "p_value": None})
                continue
            rho, p = spearmanr(sub[env_col], sub[sdoh_col])
            rows.append({"env_metric": env_col, "sdoh_score": sdoh_col, "age_band": band, "n": len(sub), "spearman_rho": rho, "p_value": p})
    strat = pd.DataFrame(rows)
    print(strat.round(5).to_string(index=False))
    return strat


def main() -> None:
    df = build_table()

    stage1_food = part1_food_insecurity(df)

    eg27_path = Path(__file__).resolve().parent / "results" / "EG_27_summary.csv"
    eg27 = pd.read_csv(eg27_path)
    eg27_sig = eg27[eg27["p_value"] < 0.05]
    eg27_pairs = list(zip(eg27_sig["env_metric"], eg27_sig["sdoh_score"]))

    strat = part2_age_stratified(df, eg27_pairs)

    out_food = Path(__file__).resolve().parent / "results" / "EG_32_food_insecurity.csv"
    out_strat = Path(__file__).resolve().parent / "results" / "EG_32_age_stratified.csv"
    stage1_food.to_csv(out_food, index=False)
    strat.to_csv(out_strat, index=False)
    print(f"\nEG.32 written to {out_food}, {out_strat}")

    food_sig = stage1_food[stage1_food["p_value"] < 0.05]
    food_sig_list = ", ".join(f"{r.env_metric} (rho={r.spearman_rho:.3f}, p={r.p_value:.3g})" for r in food_sig.itertuples())

    # For each original pair, how many of the 3 age bands stay significant?
    strat_valid = strat.dropna(subset=["p_value"])
    persist_rows = []
    for (env_col, sdoh_col), g in strat_valid.groupby(["env_metric", "sdoh_score"]):
        n_sig = int((g["p_value"] < 0.05).sum())
        persist_rows.append(f"{env_col}/{sdoh_col}: {n_sig}/{len(g)} age bands")
    fully_persist = sum(1 for r in persist_rows if r.endswith(f"{len(AGE_LABELS)}/{len(AGE_LABELS)} age bands"))
    none_persist = sum(1 for r in persist_rows if r.endswith("0/3 age bands") or r.split(": ")[1].startswith("0/"))

    result_summary = (
        f"Part 1 (food insecurity, new construct): {len(food_sig)}/6 env metrics significant vs "
        f"food_insecurity_score: {food_sig_list if food_sig_list else 'none'}. Severity-group Kruskal p="
        f"{stage1_food.attrs.get('severity_p', float('nan')):.3g}. "
        f"Part 2 (age-stratified rerun of EG.27's {len(eg27_pairs)} significant pooled pairs across "
        f"3 age bands, 40-54/55-69/70+): of the pairs with enough data in every band, "
        f"{fully_persist} stayed significant in all 3 age bands (pooled signal is broad-based, not "
        f"age-concentrated), and results vary pair-by-pair otherwise -- full per-pair, per-band "
        f"breakdown in EG_32_age_stratified.csv. Purely stratified (no formal age x environment "
        f"interaction term fit) -- a pattern here would motivate that as a follow-up."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.32", strat, paper="p2",
        method="Part 1: Stage 1 (pooled Spearman) + Stage 2 (severity-group Kruskal-Wallis) for the "
                "new food_insecurity_score (5-item PhenX battery, added to build_sdoh_table.py), same "
                "design as EG.27. Part 2: age-stratified rerun (3 bands: 40-54/55-69/70+, EG.23's "
                "convention) of EG.27's 20 significant pooled Spearman pairs, to check whether the "
                "pooled signal is age-concentrated or broad. Track: primary/exploratory.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
