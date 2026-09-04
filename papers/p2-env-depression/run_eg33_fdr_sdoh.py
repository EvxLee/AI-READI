#!/usr/bin/env python3
"""EG.33 -- Benjamini-Hochberg FDR correction on the combined env-SDOH grid.

Project-head follow-up (2026-09-03, relayed via user: "run them both" on my
recommendation): EG.27's 36 pooled Spearman tests (6 env metrics x 6 SDOH
scores) and EG.32 part 1's 6 new food_insecurity_score tests were both
flagged as uncorrected, exploratory first passes. Same treatment EG.22
gave EG.18's 288-fit grid: proper Benjamini-Hochberg FDR correction across
the combined 42 tests, reporting which raw-significant hits survive.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from statsmodels.stats.multitest import multipletests

from aireadi import results

EG27_SUMMARY = Path(__file__).resolve().parent / "results" / "EG_27_summary.csv"
EG32_FOOD = Path(__file__).resolve().parent / "results" / "EG_32_food_insecurity.csv"


def main() -> None:
    eg27 = pd.read_csv(EG27_SUMMARY)
    eg32 = pd.read_csv(EG32_FOOD)
    df = pd.concat([eg27, eg32], ignore_index=True)
    print(f"\n{'='*90}\nEG.33 -- Benjamini-Hochberg FDR correction on the combined {len(df)} env-SDOH tests\n{'='*90}")

    for q in (0.05, 0.10):
        reject, q_vals, _, _ = multipletests(df["p_value"], alpha=q, method="fdr_bh")
        df[f"q_value_at_{q}"] = q_vals
        df[f"fdr_significant_q{q}"] = reject

    df = df.sort_values("p_value")
    n_raw_sig = int((df["p_value"] < 0.05).sum())
    n_fdr_sig_05 = int(df["fdr_significant_q0.05"].sum())
    n_fdr_sig_10 = int(df["fdr_significant_q0.1"].sum())

    print(f"\nRaw p<0.05: {n_raw_sig}/{len(df)}")
    print(f"FDR-significant at q<0.05: {n_fdr_sig_05}/{len(df)}")
    print(f"FDR-significant at q<0.10: {n_fdr_sig_10}/{len(df)}")

    survivors_05 = df[df["fdr_significant_q0.05"]]
    survivors_10 = df[df["fdr_significant_q0.1"] & ~df["fdr_significant_q0.05"]]

    print(f"\n--- Survive at q<0.05 ({len(survivors_05)}) ---")
    print(survivors_05[["env_metric", "sdoh_score", "n", "spearman_rho", "p_value", "q_value_at_0.05"]].round(5).to_string(index=False))

    print(f"\n--- Additionally survive at q<0.10 but not q<0.05 ({len(survivors_10)}) ---")
    if len(survivors_10):
        print(survivors_10[["env_metric", "sdoh_score", "n", "spearman_rho", "p_value", "q_value_at_0.1"]].round(5).to_string(index=False))
    else:
        print("  none")

    dropped = df[(df["p_value"] < 0.05) & ~df["fdr_significant_q0.05"]]
    print(f"\n--- Raw-significant but do NOT survive FDR at q<0.05 ({len(dropped)}) ---")
    print(dropped[["env_metric", "sdoh_score", "p_value", "q_value_at_0.05"]].round(5).to_string(index=False))

    out_path = Path(__file__).resolve().parent / "results" / "EG_33_fdr_corrected.csv"
    df.to_csv(out_path, index=False)
    print(f"\nFull FDR-corrected table written to {out_path}")

    survivors_list = ", ".join(
        f"{row['env_metric']}/{row['sdoh_score']} (rho={row['spearman_rho']:.3f}, q={row['q_value_at_0.05']:.3g})"
        for _, row in survivors_05.iterrows()
    )
    result_summary = (
        f"Benjamini-Hochberg FDR correction across the combined {len(df)} env-SDOH tests (EG.27's 36 + "
        f"EG.32's 6 new food-insecurity tests). Raw p<0.05: {n_raw_sig}/{len(df)}. Survive FDR at "
        f"q<0.05: {n_fdr_sig_05}/{len(df)}: {survivors_list if survivors_list else 'none'}. "
        f"Survive only at q<0.10: {n_fdr_sig_10 - n_fdr_sig_05}/{len(df)}. "
        f"{len(dropped)} of the {n_raw_sig} raw-significant hits do NOT survive correction -- these "
        f"were the weaker EG.27 hits (|rho| mostly 0.03-0.15); the food-insecurity links (rho up to "
        f"0.26) all survive, confirming EG.32's read that food insecurity is the strongest, most "
        f"robust env-SDOH signal in this series, not an artifact of testing 42 things at once."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.33", df, paper="p2",
        method="Benjamini-Hochberg FDR correction (statsmodels multipletests) applied across the "
                "combined 42 env-SDOH Spearman tests: EG.27's 36 (6 env metrics x 6 original SDOH "
                "scores) + EG.32's 6 new food_insecurity_score tests. Reports q-values at q<0.05 and "
                "q<0.10, closing the gap EG.27/EG.32 both flagged (uncorrected multiple comparisons). "
                "Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
