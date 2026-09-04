#!/usr/bin/env python3
"""EG.30 -- does pollution link to stress and sleep, not just steps/BMI?

Project-head follow-up (2026-09-02, relayed): "also try linking pollution
to any other wearable activities like stress and sleep, that could be an
interesting pathway to go down."

Mirrors EG.2/EG.3's exact design (pollution -> activity/BMI, pooled with
site dummies + per-site), swapping in `stress` and `sleep_hours` as the
outcomes, for all 3 pollutants (PM2.5/NOx/VOC) rather than PM2.5 only, to
match the breadth of EG.13/EG.14's later extension of EG.2/EG.3.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import azure_io, cohort, results, wearables
from aireadi.constants import SITES

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"

OUTCOMES = ["stress", "sleep_hours"]
POLLUTANTS = [("PM2.5", "log_pm25", "mean_pm25"), ("NOx", "log_nox", "mean_nox"), ("VOC", "log_voc", "mean_voc")]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25", "mean_nox", "mean_voc"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])
    df["log_nox"] = np.log1p(df["mean_nox"])
    df["log_voc"] = np.log1p(df["mean_voc"])
    return df


def main() -> None:
    df = build_table()
    print(f"\n{'='*90}\nEG.30 -- pollution vs stress/sleep, pooled + per-site\n{'='*90}")

    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    pooled_df_base = pd.concat([df, site_dummies], axis=1)

    rows = []
    for pollutant_name, log_col, raw_col in POLLUTANTS:
        for outcome in OUTCOMES:
            cols = [log_col, "age", outcome] + list(site_dummies.columns)
            sub = pooled_df_base[cols].dropna()
            if len(sub) < 30:
                continue
            model_cols = [log_col, "age"] + list(site_dummies.columns)
            X = sm.add_constant(sub[model_cols])
            y = sub[outcome]
            fit = sm.OLS(y, X).fit()
            rows.append({
                "scope": "pooled", "pollutant": pollutant_name, "outcome": outcome,
                "site": "all", "n": len(sub), "r2": fit.rsquared,
                "coef": fit.params[log_col], "p": fit.pvalues[log_col],
            })
            flag = " *" if fit.pvalues[log_col] < 0.05 else ""
            print(f"  pooled  {pollutant_name:6s} / {outcome:12s} N={len(sub):4d}  coef={fit.params[log_col]:+.4f}  p={fit.pvalues[log_col]:.4f}{flag}")

            for site in SITES:
                site_sub = df.loc[df["clinical_site"] == site, [log_col, "age", outcome]].dropna()
                if len(site_sub) < 30:
                    continue
                Xs = sm.add_constant(site_sub[[log_col, "age"]])
                ys = site_sub[outcome]
                sfit = sm.OLS(ys, Xs).fit()
                rows.append({
                    "scope": "per_site", "pollutant": pollutant_name, "outcome": outcome,
                    "site": site, "n": len(site_sub), "r2": sfit.rsquared,
                    "coef": sfit.params[log_col], "p": sfit.pvalues[log_col],
                })
                sflag = " *" if sfit.pvalues[log_col] < 0.05 else ""
                print(f"    {site:6s} {pollutant_name:6s} / {outcome:12s} N={len(site_sub):4d}  coef={sfit.params[log_col]:+.4f}  p={sfit.pvalues[log_col]:.4f}{sflag}")

    summary = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parent / "results" / "EG_30_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.30 summary written to {out_path}")

    sig = summary[summary["p"] < 0.05]
    sig_list = ", ".join(
        f"{r.pollutant}/{r.outcome}/{r.scope}{'(' + r.site + ')' if r.scope == 'per_site' else ''} "
        f"(coef={r.coef:+.3f}, p={r.p:.3g})" for r in sig.itertuples()
    )
    result_summary = (
        f"Pollution (PM2.5/NOx/VOC, log1p) vs stress and sleep_hours (Garmin), pooled with site "
        f"dummies + age, and per-site with age only. {len(sig)}/{len(summary)} fits significant "
        f"(p<0.05): {sig_list if sig_list else 'none'}."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.30", summary, paper="p2",
        method="Extends EG.2/EG.3's pollution-vs-activity/BMI design to stress and sleep_hours as "
                "outcomes, for all 3 pollutants (PM2.5/NOx/VOC), pooled (log(pollutant) + age + site "
                "dummies) and per-site (log(pollutant) + age). Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
