#!/usr/bin/env python3
"""EG.22 -- Benjamini-Hochberg FDR correction on EG.18's 288-fit grid.

Project head's follow-up (2026-08-21): 44 of EG.18's 288 fits were
significant at raw p<0.05 -- about 3x the ~14 expected by chance, but that
"3x" comparison is not itself a correction, and was flagged as such when
first reported. This applies a proper Benjamini-Hochberg FDR correction
across all 288 p-values and reports which of the 44 survive at q<0.05 and
q<0.10.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from statsmodels.stats.multitest import multipletests

from aireadi import results

EG18_SUMMARY = Path(__file__).resolve().parent / "results" / "EG_18_summary.csv"


def main() -> None:
    df = pd.read_csv(EG18_SUMMARY)
    print(f"\n{'='*90}\nEG.22 -- Benjamini-Hochberg FDR correction on EG.18's {len(df)} fits\n{'='*90}")

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
    print(survivors_05[["pollutant", "scope", "site", "outcome", "n", "p_value", "q_value_at_0.05"]].round(5).to_string(index=False))

    print(f"\n--- Additionally survive at q<0.10 but not q<0.05 ({len(survivors_10)}) ---")
    if len(survivors_10):
        print(survivors_10[["pollutant", "scope", "site", "outcome", "n", "p_value", "q_value_at_0.1"]].round(5).to_string(index=False))
    else:
        print("  none")

    out_path = Path(__file__).resolve().parent / "results" / "EG_22_fdr_corrected.csv"
    df.to_csv(out_path, index=False)
    print(f"\nFull FDR-corrected table written to {out_path}")

    survivors_list = ", ".join(
        f"{row['pollutant']}/{row['scope']}" + (f"/{row['site']}" if row['scope'] == "per_site" else "")
        + f"/{row['outcome']} (q={row['q_value_at_0.05']:.3g})"
        for _, row in survivors_05.iterrows()
    )
    result_summary = (
        f"Of EG.18's 44 raw-significant (p<0.05) fits out of 288 total, {n_fdr_sig_05} survive "
        f"Benjamini-Hochberg FDR correction at q<0.05, and {n_fdr_sig_10} survive at the more "
        f"lenient q<0.10. Survivors at q<0.05: {survivors_list if survivors_list else 'none'}."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.22", df, paper="p2",
        method="Benjamini-Hochberg FDR correction (statsmodels multipletests, method='fdr_bh') "
                "applied to all 288 p-values from EG.18's pollutant x range-feature grid, at both "
                "q<0.05 and q<0.10 thresholds.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
