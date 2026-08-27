"""E4.1 — Table 1: cohort characteristics by severity group.

The paper's first table, built once from the same participant table every
analysis ran on, so a number in Table 1 can never disagree with a number in
a results table. Aggregates only: every cell is a count, a mean, a median or
a percentage over a group of at least 258 people.

Conventions, chosen once here and reported in the table footnote:

* continuous variables that are roughly symmetric (age, BMI) as mean (SD);
  skewed ones (HbA1c, ACR, troponin, CES-D-10, PAID-5, glucose) as
  median [IQR];
* categorical as n (%), with the denominator being participants with the
  variable measured, so a percentage is never deflated by missingness;
* an across-group test in the last column (Kruskal-Wallis for continuous,
  chi-square for categorical) — descriptive, not a hypothesis test, and the
  paper says so;
* the number missing per variable in its own column, because Table 1 is
  where a reader checks coverage.

Troponin is summarised over *all* measured results with below-detection rows
at the 6 ng/L limit, and the share below detection is its own row, so the
two denominators the E0.AUDIT caught are both visible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as _sps

from aireadi import results, thresholds

import _phase3

_phase3.banner("E4.1", "Table 1 — cohort characteristics by severity group")

df = _phase3.load_full()
GROUPS = ["Healthy", "Pre-DM", "Oral Med", "Insulin"]
COLS = ["Overall", *GROUPS]
either = thresholds.either_organ(df)
df["unrec_kidney_burden"] = (df.abn_kidney.eq(1) & df.sr_kidney.eq(0)).astype(float).mask(df.abn_kidney.isna() | df.sr_kidney.isna())
df["unrec_heart_burden"] = (df.abn_heart.eq(1) & df.sr_heart.eq(0)).astype(float).mask(df.abn_heart.isna() | df.sr_heart.isna())
df["unrec_either_burden"] = either["unrecognized"].where(either["answered"])
df["troponin_below_detection"] = df["troponin_t_below_detection"].astype("boolean").astype(float)
df["monofilament_missed_worse"] = 10 - df["monofilament_min"]

rows = []


def add(section, label, statistic, values, p, n_missing):
    rows.append({"section": section, "variable": label, "statistic": statistic,
                 **dict(zip(COLS, values)), "p_across_groups": p, "n_missing": n_missing})


def subsets(col):
    return [df[col]] + [df.loc[df.study_group_label == g, col] for g in GROUPS]


def mean_sd(section, label, col):
    vals = [f"{s.mean():.1f} ({s.std():.1f})" for s in subsets(col)]
    groups = [s.dropna() for s in subsets(col)[1:]]
    p = float(_sps.kruskal(*groups).pvalue)
    add(section, label, "mean (SD)", vals, p, int(df[col].isna().sum()))


def median_iqr(section, label, col, fmt="{:.1f}"):
    vals = [(fmt + " [" + fmt + "–" + fmt + "]").format(s.median(), s.quantile(.25), s.quantile(.75))
            for s in subsets(col)]
    groups = [s.dropna() for s in subsets(col)[1:]]
    p = float(_sps.kruskal(*groups).pvalue)
    add(section, label, "median [IQR]", vals, p, int(df[col].isna().sum()))


def n_pct(section, label, col):
    vals = []
    for s in subsets(col):
        s = s.dropna()
        vals.append(f"{int((s > 0).sum()):,} ({100 * (s > 0).mean():.1f}%)")
    tab = pd.crosstab(df.study_group_label, df[col] > 0)
    p = float(_sps.chi2_contingency(tab)[1]) if tab.shape == (4, 2) else np.nan
    add(section, label, "n (%)", vals, p, int(df[col].isna().sum()))


def categorical(section, label, col):
    tab = pd.crosstab(df[col], df.study_group_label)
    p = float(_sps.chi2_contingency(tab)[1])
    for level in tab.index:
        vals = [f"{int((df[col] == level).sum()):,} ({100 * (df[col] == level).mean():.1f}%)"]
        for g in GROUPS:
            sub = df.loc[df.study_group_label == g, col]
            vals.append(f"{int((sub == level).sum()):,} ({100 * (sub == level).mean():.1f}%)")
        add(section, f"{label} — {level}", "n (%)", vals, p, int(df[col].isna().sum()))


# ── Build ───────────────────────────────────────────────────────────────
add("Cohort", "Participants", "n", [f"{len(s):,}" for s in subsets("age")], np.nan, 0)
mean_sd("Cohort", "Age, years", "age")
categorical("Cohort", "Clinical site", "clinical_site")
mean_sd("Body and glycaemia", "BMI, kg/m²", "bmi")
n_pct("Body and glycaemia", "Obesity (BMI ≥ 30)", "bmi_obese")
median_iqr("Body and glycaemia", "HbA1c, %", "hba1c")
median_iqr("Body and glycaemia", "CGM mean glucose, mg/dL", "glucose_mean", fmt="{:.0f}")
median_iqr("Body and glycaemia", "CGM coefficient of variation, %", "glucose_cv")
median_iqr("Psychosocial", "CES-D-10 score (0–30)", "cesd_total", fmt="{:.0f}")
n_pct("Psychosocial", "CES-D-10 screen-positive (≥ 10)", "cesd_positive")
median_iqr("Psychosocial", "PAID-5 score (0–20)", "paid_total", fmt="{:.0f}")
median_iqr("Psychosocial", "Self-reported conditions, count", "comorbidity_count", fmt="{:.0f}")
median_iqr("Kidney", "Urine ACR, mg/g", "acr_mg_g")
n_pct("Kidney", "ACR ≥ 30 mg/g (abnormal)", "abn_kidney")
n_pct("Kidney", "Self-reported kidney problems", "sr_kidney")
n_pct("Kidney", "Abnormal and unrecognized (burden)", "unrec_kidney_burden")
median_iqr("Heart", "hs-cTnT, ng/L (all results; below-detection at 6)", "troponin_t")
n_pct("Heart", "hs-cTnT below the 6 ng/L detection limit", "troponin_below_detection")
n_pct("Heart", "hs-cTnT ≥ 14 ng/L (abnormal)", "abn_heart")
n_pct("Heart", "Self-reported heart attack or other heart condition", "sr_heart")
n_pct("Heart", "Abnormal and unrecognized (burden)", "unrec_heart_burden")
median_iqr("Nerve", "Insensate sites, worse foot (0–10)", "monofilament_missed_worse", fmt="{:.0f}")
n_pct("Nerve", "≥ 2 insensate sites (abnormal)", "abn_nerve")
n_pct("Multi-organ", "Any organ abnormal (of three)", "abn_any")
n_pct("Multi-organ", "Two or more organs abnormal", "abn_multi")
n_pct("Multi-organ", "Kidney or heart abnormal and unrecognized (burden)", "unrec_either_burden")

table1 = pd.DataFrame(rows).set_index(["section", "variable"])

pd.set_option("display.width", 250)
print(table1.drop(columns=["statistic"]).to_string())

# Markdown rendering for the manuscript draft.
lines = ["| Characteristic | Statistic | " + " | ".join(COLS) + " | p | n missing |",
         "|---|---|" + "---|" * len(COLS) + "---|---|"]
last = None
for (section, variable), r in table1.iterrows():
    if section != last:
        lines.append(f"| **{section}** | | " + " | ".join([""] * len(COLS)) + " | | |")
        last = section
    p = "" if pd.isna(r.p_across_groups) else ("<0.001" if r.p_across_groups < 0.001 else f"{r.p_across_groups:.3f}")
    lines.append(f"| {variable} | {r.statistic} | " + " | ".join(str(r[c]) for c in COLS)
                 + f" | {p} | {int(r.n_missing)} |")
lines.append("")
lines.append("Mean (SD) for roughly symmetric variables, median [IQR] for skewed ones; n (%) with the "
             "denominator being participants with the variable measured. p: Kruskal-Wallis across the "
             "four groups for continuous variables, chi-square for categorical — descriptive only. "
             "Abnormal = ACR ≥ 30 mg/g, hs-cTnT ≥ 14 ng/L, ≥ 2 insensate sites of 10 on the worse foot. "
             "Unrecognized = abnormal result with no corresponding self-reported diagnosis; burden is "
             "per 100 evaluable participants. Nerve has no self-report comparator in v3.0.0. "
            "Self-report survey precedes the clinic visit by a median of 35 days.")
md_path = _phase3.RESULTS / "E4_1_table1.md"
md_path.write_text("\n".join(lines), encoding="utf-8")
print(f"\nmarkdown rendering -> {md_path.name}")

results.save(
    "E4.1", table1, paper="p1",
    method=("Table 1 built from the master participant table: age, site, BMI, HbA1c, CGM glucose, "
            "CES-D-10, PAID-5, comorbidity count, each organ's marker distribution, abnormality "
            "prevalence, self-report and unrecognized burden, by severity group; mean (SD) / median "
            "[IQR] / n (%), Kruskal-Wallis or chi-square across groups, n missing per variable."),
    result=(f"{len(table1)} rows. Age {table1.loc[('Cohort', 'Age, years'), 'Overall']}; "
            f"any organ abnormal {table1.loc[('Multi-organ', 'Any organ abnormal (of three)'), 'Overall']}; "
            f"either-organ unrecognized burden {table1.loc[('Multi-organ', 'Kidney or heart abnormal and unrecognized (burden)'), 'Overall']} "
            f"overall, {table1.loc[('Multi-organ', 'Kidney or heart abnormal and unrecognized (burden)'), 'Insulin']} on insulin."),
    decision="keep", name="table1",
)
