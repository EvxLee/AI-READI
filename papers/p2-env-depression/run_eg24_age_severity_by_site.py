#!/usr/bin/env python3
"""EG.24 -- age and severity-group distribution across sites.

Project head's follow-up (2026-08-21): "if we look at distribution of
pollutants across sites, maybe we could also look at distribution of age
and diabetic status across sites and see whether they're comparable, then
there's less of an objection of why we're pulling them together, if
they're comparable, even if one is more polluted, that shouldn't make too
much of a difference." Mirrors EG.11's per-site pollution descriptive, but
for age and severity-group composition -- checks whether the 3 sites are
similar populations, which determines how much weight to put on the
site-specific pollution/BMI/glycemic findings (EG.8, EG.13-15, EG.18,
EG.21).
"""

from __future__ import annotations

from pathlib import Path

from scipy.stats import chi2_contingency, kruskal
import pandas as pd

from aireadi import cohort, results


def main() -> None:
    df = cohort.build_core_table()
    print(f"\n{'='*90}\nEG.24 -- age and severity-group distribution by site\n{'='*90}")

    # Age: descriptive stats + Kruskal-Wallis across sites
    age_stats = df.groupby("clinical_site")["age"].agg(n="count", mean="mean", median="median", sd="std").reset_index()
    print("\n--- Age by site ---")
    print(age_stats.round(2).to_string(index=False))

    age_groups = [g["age"].dropna().values for _, g in df.groupby("clinical_site")]
    age_stat, age_p = kruskal(*age_groups)
    print(f"\nKruskal-Wallis (age across sites): H={age_stat:.3f}, p={age_p:.4g}")

    # Severity group: crosstab + chi-square test of independence
    severity_ct = pd.crosstab(df["clinical_site"], df["study_group_label"])
    severity_pct = pd.crosstab(df["clinical_site"], df["study_group_label"], normalize="index") * 100
    print("\n--- Severity group counts by site ---")
    print(severity_ct.to_string())
    print("\n--- Severity group % within site ---")
    print(severity_pct.round(1).to_string())

    chi2, chi_p, dof, _ = chi2_contingency(severity_ct)
    print(f"\nChi-square (severity group x site independence): chi2={chi2:.3f}, dof={dof}, p={chi_p:.4g}")

    out_path = Path(__file__).resolve().parent / "results" / "EG_24_age_severity_by_site.csv"
    combined = age_stats.copy()
    combined = combined.merge(severity_pct.reset_index(), on="clinical_site")
    combined.to_csv(out_path, index=False)
    print(f"\nEG.24 table written to {out_path}")

    age_verdict = "differs significantly" if age_p < 0.05 else "does NOT differ significantly"
    severity_verdict = "differs significantly" if chi_p < 0.05 else "does NOT differ significantly"
    result_summary = (
        f"Age {age_verdict} across the 3 sites (Kruskal-Wallis p={age_p:.3g}). "
        f"Severity-group composition {severity_verdict} across sites (chi-square p={chi_p:.3g}). "
        f"See EG_24_age_severity_by_site.csv for the full breakdown."
    )
    print(f"\n{result_summary}")
    results.save(
        "EG.24", combined, paper="p2",
        method="Descriptive + inferential: age (Kruskal-Wallis across sites) and severity-group "
                "composition (chi-square test of independence, site x severity-group) -- checks "
                "whether the 3 sites are comparable populations, mirroring EG.11's per-site "
                "pollution distribution check.",
        result=result_summary,
        decision="keep",
    )


if __name__ == "__main__":
    main()
