"""Audit every number quoted in the Phase-4 report against the artifacts.

Run after any edit to reports/2026-08-25-phase4-report.md.
"""

from __future__ import annotations

import re

import pandas as pd

import _raw

REPORT_PATH = _raw.REPO / "reports" / "2026-08-25-phase4-report.md"
REPORT = REPORT_PATH.read_text()
BARE = REPORT.replace("*", "").replace("`", "")
LOG = (_raw.REPO / "papers/p1-unrecognized-damage/RESULTS_LOG.md").read_text()

print("=" * 78)
print("AUDIT — every number quoted in the Phase-4 report")
print("=" * 78)


def quoted(text):
    variants = {text, text.replace("-", "−")}
    return any(x in REPORT or x in BARE for x in variants)


def claim(label, text, source):
    ok = quoted(text)
    print(f"  [{'OK  ' if ok else 'MISS'}] {label:<58} '{text}'  <- {source}")
    if not ok:
        _raw.FAILURES.append(f"{label}: report does not contain '{text}' (from {source})")


def claim_row(label, cells, source):
    pattern = r"\|\s*" + r"\s*\|\s*".join(re.escape(c) for c in cells) + r"\s*\|"
    ok = re.search(pattern, BARE) is not None
    print(f"  [{'OK  ' if ok else 'MISS'}] {label:<58} {cells}  <- {source}")
    if not ok:
        _raw.FAILURES.append(f"{label}: no table row pairs {cells} (from {source})")


R = _raw.REPO / "papers/p1-unrecognized-damage/results"
t1 = _raw.artifact("E4_1_table1.csv").set_index(["section", "variable"])
t2 = _raw.artifact("E4_4_table2.csv")
s1 = _raw.artifact("E4_4_S1_site_direction.csv")
s2 = _raw.artifact("E4_4_S2_cutoff_sweeps.csv")
s3 = _raw.artifact("E4_4_S3_experiment_log.csv")
s4 = _raw.artifact("E4_4_S4_ecg.csv")
s5 = _raw.artifact("E4_4_S5_age_confounding.csv")
burden = _raw.artifact("E1_2_population_burden.csv").set_index(["organ", "stratum"])
frac = _raw.artifact("E1_2_unrecognized_by_group.csv").set_index(["organ", "stratum"])
counts = _raw.artifact("E1_3_organ_counts.csv").set_index("stratum")
overlap = _raw.artifact("E1_3_overlap.csv").set_index("combination")
GROUPS = ["Healthy", "Pre-DM", "Oral Med", "Insulin"]

print("\n§1 TABLE 1")
claim("Table 1 row count", f"{len(t1)} rows", "E4_1_table1")
for section, variable, label in [("Cohort", "Participants", "Participants"), ("Cohort", "Age, years", "Age, years"),
                                 ("Body and glycaemia", "BMI, kg/m²", "BMI, kg/m²"), ("Body and glycaemia", "HbA1c, %", "HbA1c, %"),
                                 ("Psychosocial", "CES-D-10 screen-positive (≥ 10)", "CES-D-10 screen-positive (≥ 10)"),
                                 ("Kidney", "ACR ≥ 30 mg/g (abnormal)", "ACR ≥ 30 mg/g (abnormal)"),
                                 ("Heart", "hs-cTnT ≥ 14 ng/L (abnormal)", "hs-cTnT ≥ 14 ng/L (abnormal)"),
                                 ("Nerve", "≥ 2 insensate sites (abnormal)", "≥ 2 insensate sites (abnormal)"),
                                 ("Multi-organ", "Any organ abnormal (of three)", "Any organ abnormal"),
                                 ("Multi-organ", "Kidney or heart abnormal and unrecognized (burden)", "Kidney or heart abnormal and unrecognized")]:
    r = t1.loc[(section, variable)]
    claim_row(f"Table 1 {variable}", [label] + [str(r[g]) for g in GROUPS], "E4_1_table1")
for site, grp, key in [("UAB", "Insulin", "Clinical site — UAB"), ("UAB", "Healthy", "Clinical site — UAB"),
                       ("UW", "Healthy", "Clinical site — UW"), ("UW", "Insulin", "Clinical site — UW")]:
    pct = str(t1.loc[("Cohort", key), grp]).split("(")[1].rstrip(")")
    claim(f"site share {site} {grp}", pct, "E4_1_table1")
bd = str(t1.loc[("Heart", "hs-cTnT below the 6 ng/L detection limit"), "Overall"])
claim("troponin below detection overall", bd.replace(" (", ", ").rstrip(")"), "E4_1_table1")
for g in ("Healthy", "Insulin"):
    claim(f"troponin below detection {g}", str(t1.loc[("Heart", "hs-cTnT below the 6 ng/L detection limit"), g]).split("(")[1].rstrip(")"), "E4_1_table1")
_med = str(t1.loc[("Heart", "hs-cTnT, ng/L (all results; below-detection at 6)"), "Overall"])
claim("troponin median", _med.split(" [")[0] + " ng/L [" + _med.split(" [")[1], "E4_1_table1")
claim("CES-D positive Healthy->Insulin", f"{str(t1.loc[('Psychosocial', 'CES-D-10 screen-positive (≥ 10)'), 'Healthy']).split('(')[1].rstrip(')')} → {str(t1.loc[('Psychosocial', 'CES-D-10 screen-positive (≥ 10)'), 'Insulin']).split('(')[1].rstrip(')')}", "E4_1_table1")

print("\n§2-3 FIGURES")
claim("either burden Healthy", f"{burden.loc[('either', 'Healthy'), 'pct']}", "E1_2_population_burden")
claim("either burden Insulin", f"{burden.loc[('either', 'Insulin'), 'pct']}", "E1_2_population_burden")
claim("burden trend z", f"z = {burden.loc[('either', 'Overall'), 'trend_z']:.2f}", "E1_2_population_burden")
claim("fraction Healthy->Insulin", f"{frac.loc[('either', 'Healthy'), 'pct']:.0f}% to {frac.loc[('either', 'Insulin'), 'pct']:.0f}%", "E1_2_unrecognized_by_group")
claim("fraction trend z", f"z = {frac.loc[('either', 'Overall'), 'trend_z']:.2f}", "E1_2_unrecognized_by_group")
claim("2+ overall", f"{counts.loc['Overall', 'pct_2_or_more']}%", "E1_3_organ_counts")
claim("2+ Healthy", f"{counts.loc['Healthy', 'pct_2_or_more']}%", "E1_3_organ_counts")
claim("2+ Insulin", f"{counts.loc['Insulin', 'pct_2_or_more']}%", "E1_3_organ_counts")
claim("n measured on all three", f"{int(counts.loc['Overall', 'n']):,}", "E1_3_organ_counts")
claim("heart alone", f"({int(overlap.loc['heart', 'n'])})", "E1_3_overlap")
claim("all three", f"{int(overlap.loc['kidney + heart + nerve', 'n'])} people", "E1_3_overlap")
for fig in re.findall(r"\]\((\.\./papers/[^)]+\.png)\)", REPORT):
    _raw.check(f"figure exists {fig.split('/')[-1]}", (REPORT_PATH.parent / fig).exists(), True)
_raw.check("log has two E4.2 entries (re-render recorded)", LOG.count("### E4.2 ") >= 2, True)

print("\n§4 TABLE 2 AND SUPPLEMENT")
claim("Table 2 row count", f"{len(t2)} rows", "E4_4_table2")
row = t2[(t2.analysis == "Kidney — model C") & (t2.term == "log ACR, per unit")].iloc[0]
claim("block A log ACR", f"OR {row.estimate}", "E4_4_table2")
row = t2[(t2.analysis == "Kidney — model C") & (t2.term == "Insulin vs Healthy")].iloc[0]
claim("block A kidney Insulin C", f"OR {row.estimate}", "E4_4_table2")
row = t2[(t2.analysis == "Heart — model C") & (t2.term == "Insulin vs Healthy")].iloc[0]
claim("block A heart Insulin C", f"OR {row.estimate}, p = {row.p}", "E4_4_table2")
row = t2[(t2.analysis == "CES-D-10, per SD") & (t2.term == "Nerve abnormal")].iloc[0]
claim("block B nerve", f"OR {row.estimate}, q = {row.q}", "E4_4_table2")
claim("block B nerve exploratory", row.exploratory_estimate.replace(", q ", ", q = "), "E4_4_table2")
row = t2[(t2.analysis.str.startswith("No diabetes label, HbA1c")) & (t2.term == "Kidney abnormal")].iloc[0]
claim("block C kidney", row.estimate.replace(";", ","), "E4_4_table2")
claim("block C kidney exposed", "13 of 46 exposed abnormal (28.3% vs 8.7%)", "E4_4_table2")
claim("S1 rows", f"{int(s1.table.str.startswith('S1a').sum())} + {int(s1.table.str.startswith('S1b').sum())}", "E4_4_S1")
claim("S2 rows", f"| {len(s2)} |", "E4_4_S2")
claim("S3 experiments", f"{len(s3)} experiments", "E4_4_S3")
claim("S3 models", f"{int(s3.adjusted_models.sum())} adjusted models", "E4_4_S3")
claim("S3 survivors", f"{int(s3.fdr_survivors.sum())} survivors", "E4_4_S3")
claim("S4 rows", f"{int((~s4.kind.str.contains('UNADJUDICATED')).sum())} + {int(s4.kind.str.contains('UNADJUDICATED').sum())}", "E4_4_S4")
claim("S5 rows", f"{int((s5.table == 'S5a sign test').sum())} + {int((s5.table != 'S5a sign test').sum())}", "E4_4_S5")
_raw.check("S3 survivors equal E3.1's 79", int(s3.fdr_survivors.sum()), 79)
_raw.check("report says nothing was fitted", "fits no models" in BARE, True)
_raw.check("report labels the unadjudicated row", "unadjudicated" in BARE.lower(), True)
_raw.check("log has two E4.4 entries (self-reference fix recorded)", LOG.count("### E4.4 ") >= 2, True)

_raw.report("PHASE-4 REPORT AUDIT")
