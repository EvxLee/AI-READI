#!/usr/bin/env python3
"""EP.1-EP.7 -- pairwise severity-group binary logistic models.

Project-head-directed near-term step (2026-08-11, see PLAN.md / PRESPEC.md
amendment): instead of one 4-group model, fit a separate binary logistic
regression for each pair of severity categories.

EP.1-EP.3 cover the three *adjacent* boundaries --

    Healthy vs Pre-DM
    Pre-DM  vs Oral Med
    Oral Med vs Insulin

EP.5-EP.7 (added 2026-08-12, same project-head note: "you might as well do
every pair of those four groups... it's kind of a sanity check") cover the
three *non-adjacent* pairs --

    Healthy  vs Oral Med
    Healthy  vs Insulin
    Pre-DM   vs Insulin

The point of the non-adjacent pairs is a sanity check on the gradient
assumption: if severity is a real continuum, predictors that separate
adjacent groups should show up at least as strongly (and in the same
direction) across the wider gaps, not disappear or flip.

All pairs use the same environmental / BMI / wearable predictor set as the
main Aim 1 model, adjusted for age and clinical site. For each pair this
reports which predictors are significant and their direction (does the
predictor go up or down crossing that specific severity boundary).

`mean_glucose` (CGM manifest mean) is included as a predictor here on
purpose, even though glycemic control is partly definitional of severity
group: the project head specifically wants to see whether the same
predictors that separate severity groups also line up with the richer
CGM-derived metrics from `build_cgm_table.py` (EG.1) -- that comparison is
the point, not a design flaw.

Not yet doing the VIF/multicollinearity diagnostics PRESPEC.md assigns to
E1.7 -- this is a first pass, flagged as such in the result summary.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables
from aireadi.constants import GROUP_ORDER

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"

PAIRS = [
    ("Healthy", "Pre-DM"),
    ("Pre-DM", "Oral Med"),
    ("Oral Med", "Insulin"),
]

# Non-adjacent pairs -- the remaining 3 of all C(4,2)=6 possible pairs,
# requested 2026-08-12 as a gradient/continuum sanity check.
NONADJACENT_PAIRS = [
    ("Healthy", "Oral Med"),
    ("Healthy", "Insulin"),
    ("Pre-DM", "Insulin"),
]

PREDICTORS = [
    "log_pm25", "mean_temp", "mean_hum", "mean_light", "mean_voc", "mean_nox",
    "bmi", "mean_glucose", "steps", "stress", "heart_rate", "sleep_hours",
    "active_calories", "age",
]


def build_table() -> pd.DataFrame:
    """Same merge as run_e1_1.py -- core table + extra wearables + environment."""
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    extra = activity[["person_id", "average_active_calories_kcal"]].rename(
        columns={"average_active_calories_kcal": "active_calories"}
    )
    df = df.merge(extra, on="person_id", how="left")

    if not ENV_TABLE.exists():
        raise FileNotFoundError(f"{ENV_TABLE} not found -- run build_env_table.py first.")
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(
        env[["person_id", "mean_temp", "mean_hum", "mean_light", "mean_pm25", "mean_voc", "mean_nox"]],
        on="person_id", how="left",
    )
    df["log_pm25"] = np.log1p(df["mean_pm25"])
    return df


def fit_pair(df: pd.DataFrame, group_a: str, group_b: str) -> tuple[pd.DataFrame, int]:
    """Binary logistic: 1 = group_b (more severe), 0 = group_a. Returns
    (coefficient table, N used)."""
    sub = df[df["study_group_label"].isin([group_a, group_b])].copy()
    sub["outcome"] = (sub["study_group_label"] == group_b).astype(int)

    # Site as dummy covariates -- drop_first to avoid the dummy trap.
    site_dummies = pd.get_dummies(sub["clinical_site"], prefix="site", drop_first=True, dtype=float)

    model_df = pd.concat([sub[["outcome"] + PREDICTORS], site_dummies], axis=1).dropna()
    n = len(model_df)
    if n < 30 or model_df["outcome"].nunique() < 2:
        return pd.DataFrame(), n

    X = sm.add_constant(model_df.drop(columns="outcome"))
    y = model_df["outcome"]
    try:
        fit = sm.Logit(y, X).fit(disp=0, maxiter=200)
    except Exception as exc:  # noqa: BLE001 -- e.g. perfect separation
        return pd.DataFrame({"error": [str(exc)]}), n

    out = pd.DataFrame({
        "coefficient": fit.params,
        "odds_ratio": np.exp(fit.params),
        "p_value": fit.pvalues,
        "direction": np.where(fit.params > 0, f"higher -> more {group_b}-like", f"higher -> more {group_a}-like"),
    })
    out = out.drop(index="const")
    out = out[out.index.isin(PREDICTORS)]  # drop site dummies from the reported table, keep them in the fit
    return out.sort_values("p_value"), n


def run_pair(df: pd.DataFrame, exp_id: str, group_a: str, group_b: str, all_results: list) -> None:
    table, n = fit_pair(df, group_a, group_b)
    print(f"\n{'='*80}\n{exp_id}: {group_a} vs {group_b}  (N={n})\n{'='*80}")
    if table.empty:
        print("  Could not fit (insufficient N or separation issue).")
        summary = f"N={n}, could not fit."
        results.log(exp_id, paper="p2",
                    method=f"Binary logistic ({group_a}=0 vs {group_b}=1), predictors: "
                            f"{', '.join(PREDICTORS)}, + clinical_site dummies",
                    result=summary, decision="rescope")
        return

    pd.set_option("display.width", 200)
    print(table.round(4).to_string())

    sig = table[table["p_value"] < 0.05]
    sig_list = ", ".join(f"{v} ({r.direction}, p={r.p_value:.3g})" for v, r in sig.iterrows())
    summary = f"N={n}. Significant (p<0.05): {sig_list if sig_list else 'none'}."

    table.insert(0, "pair", f"{group_a} vs {group_b}")
    table.insert(1, "n", n)
    table = table.reset_index().rename(columns={"index": "predictor"})
    all_results.append(table)

    results.save(
        exp_id, table, paper="p2",
        method=f"Binary logistic regression: outcome=1 if {group_b} else 0 (restricted to "
                f"{group_a}/{group_b}), predictors={', '.join(PREDICTORS)} + clinical_site dummies",
        result=summary,
        decision="keep",
    )


def main() -> None:
    df = build_table()
    adjacent_results: list = []
    nonadjacent_results: list = []

    for i, (group_a, group_b) in enumerate(PAIRS, start=1):
        run_pair(df, f"EP.{i}", group_a, group_b, adjacent_results)

    for i, (group_a, group_b) in enumerate(NONADJACENT_PAIRS, start=5):
        run_pair(df, f"EP.{i}", group_a, group_b, nonadjacent_results)

    all_results = adjacent_results + nonadjacent_results
    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        combined_path = Path(__file__).resolve().parent / "results" / "EP_combined.csv"
        combined.to_csv(combined_path, index=False)
        print(f"\nCombined table for all {len(all_results)} pairs written to {combined_path}")

    if adjacent_results:
        # EP.4: cross-pair synthesis -- which predictors are significant, and
        # in the same direction, across more than one adjacent-pair boundary.
        adjacent_combined = pd.concat(adjacent_results, ignore_index=True)
        sig_only = adjacent_combined[adjacent_combined["p_value"] < 0.05]
        counts = sig_only.groupby("predictor")["pair"].apply(list)
        print("\nEP.4 synthesis -- predictors significant in more than one adjacent-pair boundary:")
        recurring = counts[counts.apply(len) > 1]
        if len(recurring):
            print(recurring.to_string())
        else:
            print("  none -- no predictor was significant across more than one boundary in this first pass.")

        synth_summary = (
            f"{len(recurring)} predictor(s) significant across >1 adjacent-pair boundary: "
            f"{', '.join(recurring.index) if len(recurring) else 'none'}. "
            f"Full per-predictor breakdown in EP_combined.csv."
        )
        recurring_df = recurring.reset_index()
        recurring_df.columns = ["predictor", "significant_in_pairs"]
        recurring_df["significant_in_pairs"] = recurring_df["significant_in_pairs"].apply(str)
        results.save(
            "EP.4", recurring_df if len(recurring_df) else None, paper="p2",
            method="Cross-pair synthesis of EP.1-EP.3 (adjacent boundaries only): predictors "
                    "significant (p<0.05) in more than one adjacent-severity-boundary logistic model, "
                    "i.e. a consistent direction of effect as severity increases rather than a "
                    "one-boundary artifact.",
            result=synth_summary,
            decision="keep" if len(recurring) else "rescope",
        )

    if nonadjacent_results:
        # EP.8 (informal, not its own ID): sanity check -- does mean_glucose,
        # the one predictor significant at every adjacent boundary, also stay
        # significant and same-direction across the wider non-adjacent gaps?
        nonadj_combined = pd.concat(nonadjacent_results, ignore_index=True)
        glucose_rows = nonadj_combined[nonadj_combined["predictor"] == "mean_glucose"]
        print("\nGradient sanity check -- mean_glucose across non-adjacent pairs:")
        print(glucose_rows[["pair", "n", "p_value", "direction"]].to_string(index=False))


if __name__ == "__main__":
    main()
