#!/usr/bin/env python3
"""EG.34 -- severity-adjusted refit of the env-SDOH links that survive FDR.

Project-head follow-up (2026-09-03, relayed via user: "run them both" on my
recommendation): EG.27 explicitly flagged that severity group was never
tested as a possible confounder of the environment-SDOH link itself --
every SDOH score with a Stage-1 hit also differs by severity group, so
part of the raw Spearman correlation could just be "both track severity"
rather than a direct environment-survey relationship.

For every env-SDOH pair that survives EG.33's FDR correction at q<0.05,
refit as OLS: sdoh_score ~ env_metric + age + site dummies + severity-group
dummies, and report whether the environment term is still significant once
severity is controlled for. OLS is an approximation for SDOH scores that
are counts/binary (matches this repo's existing convention of using OLS
for CES-D-10/PAID-5/similar scores elsewhere, e.g. EG.16/EG.19) -- not a
claim these are normally distributed, just a consistent, interpretable
way to compare the raw vs. severity-adjusted coefficient on the same
scale.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from aireadi import cohort, results

FDR_TABLE = Path(__file__).resolve().parent / "results" / "EG_33_fdr_corrected.csv"
ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
SDOH_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "sdoh_survey_scores.csv"

SDOH_ONLY_NEW = ["neighborhood_score", "food_insecurity_score", "diet_score", "substance_use_count", "current_smoker"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    sdoh = pd.read_csv(SDOH_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25", "mean_nox", "mean_voc", "mean_temp", "mean_hum", "mean_light"]],
                  on="person_id", how="left")
    df = df.merge(sdoh[["person_id"] + SDOH_ONLY_NEW], on="person_id", how="left")
    return df


def main() -> None:
    survivors = pd.read_csv(FDR_TABLE)
    survivors = survivors[survivors["fdr_significant_q0.05"]]
    print(f"\n{'='*90}\nEG.34 -- severity-adjusted refit of {len(survivors)} FDR-surviving env-SDOH pairs\n{'='*90}")

    df = build_table()
    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    sev_dummies = pd.get_dummies(df["study_group_label"], prefix="sev", drop_first=True, dtype=float)
    df = pd.concat([df, site_dummies, sev_dummies], axis=1)
    site_cols = list(site_dummies.columns)
    sev_cols = list(sev_dummies.columns)

    rows = []
    for _, r in survivors.iterrows():
        env_col, sdoh_col = r["env_metric"], r["sdoh_score"]
        if sdoh_col not in df.columns:
            continue
        for variant, extra in (("raw", []), ("age_site_adjusted", ["age"] + site_cols),
                                ("severity_adjusted", ["age"] + site_cols + sev_cols)):
            cols = [env_col, sdoh_col] + extra
            sub = df[cols].dropna()
            if len(sub) < 30:
                continue
            X = sm.add_constant(sub[[env_col] + extra]) if extra else sm.add_constant(sub[[env_col]])
            y = sub[sdoh_col]
            fit = sm.OLS(y, X).fit()
            rows.append({
                "env_metric": env_col, "sdoh_score": sdoh_col, "variant": variant, "n": len(sub),
                "env_coef": fit.params[env_col], "env_p": fit.pvalues[env_col],
                "eg27_or_eg32_rho": r["spearman_rho"], "eg33_q_value": r["q_value_at_0.05"],
            })
            flag = " *" if fit.pvalues[env_col] < 0.05 else ""
            print(f"  {env_col:10s}/{sdoh_col:22s} {variant:20s} N={len(sub):4d}  coef={fit.params[env_col]:+.4f}  p={fit.pvalues[env_col]:.4f}{flag}")

    summary = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parent / "results" / "EG_34_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nEG.34 summary written to {out_path}")

    # Which pairs stay significant once severity is controlled for?
    pivot_pairs = summary[["env_metric", "sdoh_score"]].drop_duplicates()
    survives, drops = [], []
    for _, pr in pivot_pairs.iterrows():
        sub = summary[(summary["env_metric"] == pr["env_metric"]) & (summary["sdoh_score"] == pr["sdoh_score"])]
        sev_row = sub[sub["variant"] == "severity_adjusted"]
        if sev_row.empty:
            continue
        label = f"{pr['env_metric']}/{pr['sdoh_score']}"
        if sev_row.iloc[0]["env_p"] < 0.05:
            survives.append(f"{label} (p={sev_row.iloc[0]['env_p']:.3g})")
        else:
            drops.append(f"{label} (p={sev_row.iloc[0]['env_p']:.3g})")

    result_summary = (
        f"Severity-adjusted OLS refit (sdoh_score ~ env_metric + age + site + severity-group dummies) "
        f"for all {len(pivot_pairs)} env-SDOH pairs that survived EG.33's FDR correction at q<0.05. "
        f"Still significant with severity controlled: {len(survives)}/{len(pivot_pairs)}"
        + (f": {', '.join(survives)}" if survives else "") + ". "
        f"Drop out once severity is controlled: {len(drops)}/{len(pivot_pairs)}"
        + (f": {', '.join(drops)}" if drops else "") + ". "
        + ("The pairs that survive are environment-SDOH links independent of severity group, not just "
           "both tracking severity in parallel -- the strongest candidates for a real finding."
           if survives else
           "None of the FDR-surviving pairs hold up once severity is controlled for -- consistent with "
           "EG.27's caveat that severity may explain the apparent environment-SDOH links rather than "
           "sitting downstream of them.")
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.34", summary, paper="p2",
        method="For every env-SDOH pair surviving EG.33's FDR correction (q<0.05), OLS refit of "
                "sdoh_score ~ env_metric under 3 covariate sets: raw (env_metric only), age+site "
                "adjusted, and severity-adjusted (age + site + severity-group dummies added). Answers "
                "EG.27's flagged gap -- whether severity group confounds the environment-SDOH link, "
                "not just co-occurs with it. Track: primary.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
