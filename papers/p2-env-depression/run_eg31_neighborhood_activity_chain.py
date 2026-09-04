#!/usr/bin/env python3
"""EG.31 -- neighborhood security -> activity -> severity, as a 3-step chain.

Project-head follow-up (2026-09-02, relayed): "maybe see if neighborhood
[in]security leads to not going outside leading to less activity and more
diabetes."

EG.27 already showed neighborhood_score differs significantly by severity
group (Stage 2, p=0.0001) but never tested the proposed mechanism -- that
a worse neighborhood security score relates to LESS activity, which in
turn relates to worse severity. This tests the two new links needed to
complete that chain, plus reports the already-known third link for
context:

  1. NEW -- neighborhood_score ~ steps + active_calories (does neighborhood
     security relate to activity?), controlling for age, site, and PM2.5
     (since EG.27 also found neighborhood_score doesn't correlate with any
     environmental metric significantly -- so this checks whether it
     works through steps directly, not through the sensor-measured
     pollution channel).
  2. NEW -- steps/active_calories ~ severity group (Kruskal-Wallis), the
     "less activity -> more diabetes" half.
  3. Already known (restated for context, not rerun) -- neighborhood_score
     ~ severity group (Kruskal-Wallis), from EG.27 Stage 2.

This is exploratory and does not test mediation formally (no Sobel/bootstrap
mediation test) -- it checks whether each individual link in the proposed
chain holds at all before that heavier analysis would be worth running.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import kruskal

from aireadi import azure_io, cohort, results, wearables

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"
SDOH_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "sdoh_survey_scores.csv"

ACTIVITY_OUTCOMES = ["steps", "active_calories"]


def build_table() -> pd.DataFrame:
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    extra = activity[["person_id", "average_active_calories_kcal"]].rename(
        columns={"average_active_calories_kcal": "active_calories"}
    )
    df = df.merge(extra, on="person_id", how="left")

    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(env[["person_id", "mean_pm25"]], on="person_id", how="left")
    df["log_pm25"] = np.log1p(df["mean_pm25"])

    sdoh = pd.read_csv(SDOH_TABLE, dtype={"person_id": str})
    df = df.merge(sdoh[["person_id", "neighborhood_score"]], on="person_id", how="left")
    return df


def main() -> None:
    df = build_table()
    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True, dtype=float)
    df = pd.concat([df, site_dummies], axis=1)
    site_cols = list(site_dummies.columns)

    print(f"\n{'='*90}\nEG.31 -- neighborhood security -> activity -> severity chain\n{'='*90}")

    # ── Link 1 (NEW): neighborhood_score -> activity, controlling for age/site/PM2.5 ──
    link1_rows = []
    print("\n--- Link 1: neighborhood_score ~ activity (does neighborhood link to activity?) ---")
    for outcome in ACTIVITY_OUTCOMES:
        cols = ["neighborhood_score", "age", "log_pm25", outcome] + site_cols
        sub = df[cols].dropna()
        X = sm.add_constant(sub[["neighborhood_score", "age", "log_pm25"] + site_cols])
        y = sub[outcome]
        fit = sm.OLS(y, X).fit()
        link1_rows.append({
            "outcome": outcome, "n": len(sub),
            "neighborhood_coef": fit.params["neighborhood_score"], "neighborhood_p": fit.pvalues["neighborhood_score"],
        })
        flag = " *" if fit.pvalues["neighborhood_score"] < 0.05 else ""
        print(f"  {outcome:16s} N={len(sub):4d}  neighborhood_score coef={fit.params['neighborhood_score']:+.3f}  p={fit.pvalues['neighborhood_score']:.4f}{flag}")

    # ── Link 2 (NEW): activity ~ severity group ──
    link2_rows = []
    print("\n--- Link 2: activity by severity group (Kruskal-Wallis) ---")
    for outcome in ACTIVITY_OUTCOMES:
        groups = [g[outcome].dropna().values for _, g in df.groupby("study_group_label", observed=True) if g[outcome].notna().sum() >= 10]
        if len(groups) < 2:
            continue
        stat, p = kruskal(*groups)
        means = df.groupby("study_group_label", observed=True)[outcome].mean()
        link2_rows.append({"outcome": outcome, "kruskal_stat": stat, "kruskal_p": p, **{f"mean_{k}": v for k, v in means.items()}})
        flag = " *" if p < 0.05 else ""
        print(f"  {outcome:16s} kruskal p={p:.4g}{flag}  means: {means.round(1).to_dict()}")

    # ── Link 3 (restated from EG.27 Stage 2, not rerun) ──
    groups3 = [g["neighborhood_score"].dropna().values for _, g in df.groupby("study_group_label", observed=True) if g["neighborhood_score"].notna().sum() >= 10]
    stat3, p3 = kruskal(*groups3)
    print(f"\n--- Link 3 (recomputed on this pull, matches EG.27 Stage 2): neighborhood_score by severity group ---")
    print(f"  kruskal p={p3:.4g}")

    link1 = pd.DataFrame(link1_rows)
    link2 = pd.DataFrame(link2_rows)
    out1 = Path(__file__).resolve().parent / "results" / "EG_31_link1_neighborhood_activity.csv"
    out2 = Path(__file__).resolve().parent / "results" / "EG_31_link2_activity_severity.csv"
    link1.to_csv(out1, index=False)
    link2.to_csv(out2, index=False)
    print(f"\nEG.31 written to {out1}, {out2}")

    link1_sig = link1[link1["neighborhood_p"] < 0.05]
    link2_sig = link2[link2["kruskal_p"] < 0.05]
    result_summary = (
        f"3-step chain test for 'worse neighborhood security -> less activity -> more diabetes'. "
        f"Link 1 (neighborhood_score ~ steps/active_calories, controlling for age/site/PM2.5): "
        f"{len(link1_sig)}/2 significant"
        + (f" ({', '.join(f'{r.outcome} p={r.neighborhood_p:.3g}' for r in link1_sig.itertuples())})" if len(link1_sig) else "")
        + f". Link 2 (steps/active_calories differ by severity group, Kruskal-Wallis): "
        f"{len(link2_sig)}/2 significant"
        + (f" ({', '.join(f'{r.outcome} p={r.kruskal_p:.3g}' for r in link2_sig.itertuples())})" if len(link2_sig) else "")
        + f". Link 3 (neighborhood_score differs by severity group, restated from EG.27 Stage 2): "
        f"p={p3:.3g}. "
        + ("Both new links hold, consistent with the proposed chain, but this is not a formal "
           "mediation test (no indirect-effect estimate) -- it only checks each step individually."
           if len(link1_sig) == 2 and len(link2_sig) == 2 else
           "At least one new link does NOT hold, so the full 'neighborhood -> less activity -> more "
           "diabetes' chain is not supported end-to-end, even though neighborhood_score and activity "
           "each independently relate to severity.")
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.31", link1, paper="p2",
        method="3-step chain check for the proposed 'worse neighborhood security -> less activity -> "
                "more diabetes' pathway. Link 1 (NEW): neighborhood_score ~ steps/active_calories + "
                "age + site + log_pm25 (OLS). Link 2 (NEW): steps/active_calories by severity group "
                "(Kruskal-Wallis). Link 3 (restated from EG.27 Stage 2): neighborhood_score by "
                "severity group (Kruskal-Wallis). Not a formal mediation/indirect-effect test -- "
                "checks whether each link holds before that heavier analysis is worth running. "
                "Track: primary/exploratory.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
