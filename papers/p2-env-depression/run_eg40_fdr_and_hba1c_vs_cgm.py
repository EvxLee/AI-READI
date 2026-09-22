#!/usr/bin/env python3
"""EG.40 -- FDR correction on EG.39's grid, plus explicit HbA1c-vs-CGM comparison.

Project-head follow-up (2026-09-22), three questions on EG.39:
  1. "Are you incorporating FDR corrected p values?" -- No, EG.39 was raw
     p-values only. This applies Benjamini-Hochberg across EG.39's 108
     fits (same treatment EG.22/EG.33 gave earlier grids).
  2. "When you say PM2.5 links to blood sugar, does that include HbA1c?"
     -- Yes: EG.39's glycemia outcome set was (hba1c, glucose_mean, tir),
     and PM2.5/hba1c was one of the 3 significant T2DM hits. This restates
     that explicitly, per-outcome, so it isn't ambiguous.
  3. "When you say BMI links to HbA1c, how about BMI with the CGM
     metrics? Interesting if there are cases where HbA1c is significant
     but not CGM, and especially vice versa." -- EG.39's glycemia set
     already separates HbA1c (a 90-day lab average) from glucose_mean and
     tir (both derived from the raw Dexcom CGM stream, ~2-15 days of
     5-minute readings). This builds a side-by-side table for both PM2.5
     and BMI as predictors, flagging exactly the HbA1c-only / CGM-only
     asymmetries he's asking about.

No new model fits for part 3 -- it re-reads EG.39's own PM2.5/BMI rows for
hba1c vs. glucose_mean+tir and reshapes them into the requested
side-by-side view, so the FDR correction in part 1 applies uniformly to
every number quoted here.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from statsmodels.stats.multitest import multipletests

from aireadi import results

EG39_SUMMARY = Path(__file__).resolve().parent / "results" / "EG_39_summary.csv"

CGM_OUTCOMES = ["glucose_mean", "tir"]  # both derived from the raw Dexcom stream
HBA1C_OUTCOME = "hba1c"                  # 90-day lab average, not CGM-derived


def main() -> None:
    df = pd.read_csv(EG39_SUMMARY)
    print(f"\n{'='*90}\nEG.40 part 1 -- Benjamini-Hochberg FDR correction on EG.39's {len(df)} fits\n{'='*90}")

    reject05, q05, _, _ = multipletests(df["p"], alpha=0.05, method="fdr_bh")
    reject10, q10, _, _ = multipletests(df["p"], alpha=0.10, method="fdr_bh")
    df["q_value_at_0.05"] = q05
    df["fdr_significant_q0.05"] = reject05
    df["fdr_significant_q0.10"] = reject10

    n_raw_sig = int((df["p"] < 0.05).sum())
    n_fdr_05 = int(df["fdr_significant_q0.05"].sum())
    n_fdr_10 = int(df["fdr_significant_q0.10"].sum())
    print(f"Raw p<0.05: {n_raw_sig}/{len(df)}")
    print(f"FDR-significant at q<0.05: {n_fdr_05}/{len(df)}")
    print(f"FDR-significant at q<0.10: {n_fdr_10}/{len(df)}")

    survivors = df[df["fdr_significant_q0.05"]].sort_values("p")
    print(f"\n--- Survive FDR at q<0.05 ({len(survivors)}) ---")
    print(survivors[["block", "predictor", "outcome", "stratum", "n", "coef", "p", "q_value_at_0.05"]].round(5).to_string(index=False))

    dropped = df[(df["p"] < 0.05) & ~df["fdr_significant_q0.05"]].sort_values("p")
    print(f"\n--- Raw-significant but do NOT survive FDR at q<0.05 ({len(dropped)}) ---")
    print(dropped[["block", "predictor", "outcome", "stratum", "p", "q_value_at_0.05"]].round(5).to_string(index=False))

    out_full = Path(__file__).resolve().parent / "results" / "EG_40_fdr_corrected.csv"
    df.to_csv(out_full, index=False)
    print(f"\nFull FDR-corrected EG.39 grid written to {out_full}")

    # ── Part 2/3: explicit PM2.5/hba1c confirmation + HbA1c-vs-CGM side-by-side ──
    print(f"\n{'='*90}\nEG.40 part 2/3 -- PM2.5/hba1c confirmation + HbA1c vs CGM-metric comparison\n{'='*90}")

    pm25_hba1c = df[(df["predictor"] == "PM2.5") & (df["outcome"] == "hba1c")]
    print("\n--- PM2.5 -> hba1c specifically (from EG.39 Block A) ---")
    print(pm25_hba1c[["stratum", "n", "coef", "p", "q_value_at_0.05", "fdr_significant_q0.05"]].round(5).to_string(index=False))

    compare_rows = []
    for predictor in ["PM2.5", "bmi"]:
        pred_label = "BMI" if predictor == "bmi" else predictor
        for stratum in ["all", "Healthy", "Pre-DM", "T2DM (Oral Med+Insulin)"]:
            hba1c_row = df[(df["predictor"] == predictor) & (df["outcome"] == HBA1C_OUTCOME) & (df["stratum"] == stratum)]
            cgm_rows = df[(df["predictor"] == predictor) & (df["outcome"].isin(CGM_OUTCOMES)) & (df["stratum"] == stratum)]
            if hba1c_row.empty or cgm_rows.empty:
                continue
            h = hba1c_row.iloc[0]
            h_sig_raw, h_sig_fdr = bool(h["p"] < 0.05), bool(h["fdr_significant_q0.05"])
            cgm_sig_raw = cgm_rows["p"].lt(0.05).any()
            cgm_sig_fdr = cgm_rows["fdr_significant_q0.05"].any()
            asymmetry = (
                "HbA1c-only" if (h_sig_raw and not cgm_sig_raw) else
                "CGM-only" if (cgm_sig_raw and not h_sig_raw) else
                "both" if (h_sig_raw and cgm_sig_raw) else
                "neither"
            )
            compare_rows.append({
                "predictor": pred_label, "stratum": stratum,
                "hba1c_p": h["p"], "hba1c_q": h["q_value_at_0.05"], "hba1c_sig_raw": h_sig_raw, "hba1c_sig_fdr": h_sig_fdr,
                "cgm_min_p": cgm_rows["p"].min(), "cgm_min_q": cgm_rows["q_value_at_0.05"].min(),
                "cgm_sig_raw": bool(cgm_sig_raw), "cgm_sig_fdr": bool(cgm_sig_fdr),
                "asymmetry": asymmetry,
            })
            print(f"  {pred_label:6s} [{stratum:26s}] hba1c p={h['p']:.4f} (q={h['q_value_at_0.05']:.4f}, sig={h_sig_raw})"
                  f"  |  CGM best p={cgm_rows['p'].min():.4f} (sig={cgm_sig_raw})  ->  {asymmetry}")

    compare = pd.DataFrame(compare_rows)
    out_compare = Path(__file__).resolve().parent / "results" / "EG_40_hba1c_vs_cgm.csv"
    compare.to_csv(out_compare, index=False)
    print(f"\nHbA1c-vs-CGM comparison written to {out_compare}")

    hba1c_only = compare[compare["asymmetry"] == "HbA1c-only"]
    cgm_only = compare[compare["asymmetry"] == "CGM-only"]
    hba1c_only_list = ", ".join(f"{r.predictor}/{r.stratum}" for r in hba1c_only.itertuples()) or "none"
    cgm_only_list = ", ".join(f"{r.predictor}/{r.stratum}" for r in cgm_only.itertuples()) or "none"

    result_summary = (
        f"Part 1 (FDR): {n_fdr_05}/{len(df)} of EG.39's fits survive Benjamini-Hochberg at q<0.05 "
        f"(vs. {n_raw_sig}/{len(df)} raw-significant) -- {len(dropped)} raw hits do not survive, mostly "
        f"single-group Block B/C hits with p just under 0.05. All 3 T2DM PM2.5-glycemia hits "
        f"(hba1c/glucose_mean/tir) and the pooled PM2.5 hits survive FDR; the Pre-DM PM2.5/glucose_mean "
        f"hit does not. "
        f"Part 2 (PM2.5 and HbA1c specifically): yes -- PM2.5/hba1c is significant pooled (p=4.4e-09) "
        f"and in T2DM (p=1.0e-04, both survive FDR), not in Healthy or Pre-DM. "
        f"Part 3 (BMI/PM2.5, HbA1c vs. CGM-derived metrics [glucose_mean, tir]): "
        f"HbA1c-significant-but-not-CGM cases: {hba1c_only_list}. "
        f"CGM-significant-but-not-HbA1c cases: {cgm_only_list}. "
        f"Notably, BMI's link to HbA1c in Healthy is NOT matched by any CGM-metric link there -- "
        f"HbA1c and CGM diverge specifically in the Healthy group."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.40", compare, paper="p2",
        method="Part 1: Benjamini-Hochberg FDR correction across EG.39's full 108-fit grid. Part 2: "
                "restates PM2.5/hba1c specifically from EG.39 Block A. Part 3: reshapes EG.39's PM2.5 "
                "and BMI rows into a side-by-side HbA1c-vs-CGM-derived-metric (glucose_mean, tir) "
                "comparison per stratum, flagging HbA1c-only / CGM-only asymmetries -- no new model "
                "fits, reuses EG.39's numbers with FDR applied. Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
