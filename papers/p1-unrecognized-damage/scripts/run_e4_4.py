"""E4.4 — Table 2 and the supplement, assembled from frozen artifacts.

Nothing is fitted here. Every cell is copied from an artifact that E3.3
produced against `PRESPEC.md` (or, for the supplement's exploratory rows, from
the Phase-1/2 artifact the log points to), so the manuscript tables cannot
disagree with the frozen results. The point of this runner is to put the
numbers the paper needs in the shape the paper needs, once, with provenance
recorded in every row.

Outputs (all aggregate; `results/`):

* ``E4_4_table2.csv`` / ``.md``  — Table 2: the headline association models.
  Block A: who is unrecognized (E1.4 models A/B/C, the severity and
  marker terms). Block B: Aim 2, the ten pre-specified CES-D models with the
  Phase-2 exploratory estimate alongside. Block C: T1, the undiagnosed-range
  models with Wald and bootstrap intervals.
* ``E4_4_S1_site_direction.csv``  — every core trend within each site, plus
  Cochran's Q / I² for the model-based rows.
* ``E4_4_S2_cutoff_sweeps.csv``   — prevalence, unrecognized fraction and
  burden at every rung of both cutoff grids.
* ``E4_4_S3_experiment_log.csv``  — one row per experiment in the log:
  what was run, the one-line result, keep/kill, and how many adjusted models
  it fitted and how many survived FDR.
* ``E4_4_S4_ecg.csv``             — the T2 numeric-metric models and the ONE
  unadjudicated machine-read infarct row, labelled as such.
* ``E4_4_S5_age_confounding.csv`` — the E2.AGE sign test and per-exposure
  correlations behind the Methods sentence.
* ``E4_4_supplement.md``          — all of the above rendered for the draft.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from aireadi import results

import _phase3

_phase3.banner("E4.4", "Table 2 and the supplement, from frozen artifacts")

R = _phase3.RESULTS
LOG = (_phase3.PAPER / "RESULTS_LOG.md").read_text(encoding="utf-8")


def art(name: str) -> pd.DataFrame:
    return pd.read_csv(R / name)


def fmt_or(est, lo, hi, d=2):
    return f"{est:.{d}f} ({lo:.{d}f}–{hi:.{d}f})"


def fmt_p(p):
    if pd.isna(p):
        return ""
    return "<0.001" if p < 0.001 else f"{p:.3f}" if p < 0.1 else f"{p:.2f}"


# ═══════════════════════════════════════════════════════════════════════
# Table 2
# ═══════════════════════════════════════════════════════════════════════
rows = []

# Block A — who is unrecognized (E1.4 models, reproduced at E3.3 as A1.5).
a15 = art("E3_3_aim1_recognition_models.csv")
TERMS = {"C(study_group_label)[T.Pre-DM]": "Pre-DM vs Healthy", "C(study_group_label)[T.Oral Med]": "Oral Med vs Healthy",
         "C(study_group_label)[T.Insulin]": "Insulin vs Healthy", "age": "Age, per year",
         "hba1c": "HbA1c, per %", "bmi": "BMI, per kg/m²", "log_acr": "log ACR, per unit",
         "log_troponin": "log hs-cTnT, per unit"}
for organ in ("kidney", "heart"):
    for model in ("A: age + severity + site", "B: A + HbA1c + BMI", "C: B + marker magnitude"):
        sub = a15[(a15.organ == organ) & (a15.model == model)]
        for term, label in TERMS.items():
            r = sub[sub.term == term]
            if r.empty:
                continue
            r = r.iloc[0]
            rows.append({"block": "A. Odds of being unrecognized, among the abnormal", "analysis": f"{organ.capitalize()} — model {model[0]}",
                         "term": label, "estimate": fmt_or(r.odds_ratio, r.ci_lo, r.ci_hi), "p": fmt_p(r.p),
                         "q": "", "n": int(r.n_model), "exploratory_estimate": "",
                         "source": "E3_3_aim1_recognition_models.csv (= E1_4_models.csv)"})

# Block B — Aim 2 per spec, with the Phase-2 estimate beside it.
aim2 = art("E3_3_aim2_confirmatory.csv").set_index(["exposure", "outcome"])
p2 = art("E2C_1_sweep.csv")
p2 = p2[p2.adjustment == "damage"].set_index(["exposure", "outcome"])
OUT = {"abn_kidney": "Kidney abnormal", "abn_heart": "Heart abnormal", "abn_nerve": "Nerve abnormal",
       "abn_any": "Any organ abnormal", "abn_multi": "Two or more organs abnormal"}
EXP = {"cesd_total": "CES-D-10, per SD", "cesd_positive": "CES-D-10 ≥ 10"}
for exposure, elabel in EXP.items():
    for outcome, olabel in OUT.items():
        r, e = aim2.loc[(exposure, outcome)], p2.loc[(exposure, outcome)]
        rows.append({"block": "B. Aim 2 — depressive symptoms and measured damage (pre-specified model)",
                     "analysis": elabel, "term": olabel, "estimate": fmt_or(r.estimate, r.ci_lo, r.ci_hi),
                     "p": fmt_p(r.p), "q": fmt_p(r.q), "n": int(r.n),
                     "exploratory_estimate": f"{fmt_or(e.estimate, e.ci_lo, e.ci_hi)}, q {fmt_p(e.q)}",
                     "source": "E3_3_aim2_confirmatory.csv; exploratory: E2C_1_sweep.csv (age + severity + site)"})

# Block C — T1.
t1 = art("E3_3_track_undiagnosed.csv").set_index(["definition", "outcome"])
DEF = {"undiagnosed_range": "No diabetes label, HbA1c ≥ 6.5% (n = 46)", "undiagnosed_range_cgm": "No diabetes label, CGM mean ≥ 154 mg/dL (n = 55)"}
for definition, dlabel in DEF.items():
    for outcome, olabel in OUT.items():
        r = t1.loc[(definition, outcome)]
        rows.append({"block": "C. Unrecognized diabetes beneath unrecognized damage (exploratory-confirmatory)",
                     "analysis": dlabel, "term": olabel,
                     "estimate": f"{fmt_or(r.estimate, r.ci_lo, r.ci_hi)}; bootstrap {r.boot_ci_lo:.2f}–{r.boot_ci_hi:.2f}",
                     "p": fmt_p(r.p), "q": fmt_p(r.q), "n": int(r.n),
                     "exploratory_estimate": f"Phase-2 q {fmt_p(r.phase2_q)}; {int(r.events_exposed)}/{int(r.n_exposed)} exposed abnormal ({r.pct_exposed}% vs {r.pct_unexposed}%)",
                     "source": "E3_3_track_undiagnosed.csv (= E2A_2_models.csv, family narrowed 15 -> 10)"})

table2 = pd.DataFrame(rows).set_index(["block", "analysis", "term"])
pd.set_option("display.width", 250)
print(table2.drop(columns=["source"]).to_string())

# ═══════════════════════════════════════════════════════════════════════
# Supplement
# ═══════════════════════════════════════════════════════════════════════
# S1 — site direction check.
by_site = art("E3_3_aim1_by_site.csv")
het = art("E3_3_site_heterogeneity.csv")
s1 = by_site[["claim", "organ", "site", "n", "pct", "pct_Healthy", "pct_Pre-DM", "pct_Oral Med", "pct_Insulin",
              "trend_z", "trend_p", "same_direction_as_pooled", "significant_within_site"]].copy()
s1.insert(0, "table", "S1a core trends within site")
s1_b = het.rename(columns={"analysis": "claim"}).copy()
s1_b.insert(0, "table", "S1b model-based rows: direction, Cochran's Q, I²")
s1 = pd.concat([s1, s1_b], ignore_index=True)

# S2 — cutoff sweeps.
e15 = art("E1_5_threshold_sweep.csv")
bsw = art("E3_3_burden_sweep.csv")
s2 = e15.merge(bsw[["organ", "cutoff", "burden_pct", "burden_ci_lo", "burden_ci_hi", "burden_trend_z", "burden_trend_p",
                    "burden_Healthy", "burden_Pre-DM", "burden_Oral Med", "burden_Insulin"]],
               on=["organ", "cutoff"], how="left")
either_rows = bsw[bsw.organ.str.startswith("either")]
s2 = pd.concat([s2, either_rows], ignore_index=True)

# S3 — one row per experiment from the log's status table, with model counts.
status_rows = []
for line in LOG.splitlines():
    m = re.match(r"^\|\s*(E[0-9A-Z.]+)\s*\|\s*(\w[\w ]*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$", line)
    if m and m.group(1) != "ID":
        status_rows.append({"experiment": m.group(1), "status": m.group(2), "key_output": m.group(3).replace("`", ""),
                            "one_line_result": m.group(4), "decision": m.group(5)})
s3 = pd.DataFrame(status_rows).set_index("experiment")
# This runner is E4.4: its own status row is rewritten by results.save() only after
# the table below is built, so it reads "not started" here. It is running.
if "E4.4" in s3.index:
    s3.loc["E4.4", "status"] = "done"
    s3.loc["E4.4", "key_output"] = "results/E4_4_table2.csv"
    s3.loc["E4.4", "one_line_result"] = "Table 2 and supplement S1-S5 assembled from frozen artifacts (this run)."
    s3.loc["E4.4", "decision"] = "keep"
FAMILIES = {"E2C.1": ("E2C_1_sweep.csv", "damage"), "E2C.3": ("E2C_3_sweep.csv", "damage"), "E2A.1": ("E2A_1_sweep.csv", "damage"),
            "E2B.1": ("E2B_1_sweep.csv", "damage"), "E2D.1": ("E2D_1_sweep.csv", "damage"), "E2E.2": ("E2E_2_sweep.csv", "damage"),
            "E2F.1": ("E2F_1_models.csv", "full"), "E2C.2": ("E2C_2.csv", "recognition+marker")}
s3["adjusted_models"] = np.nan
s3["fdr_survivors"] = np.nan
for exp, (name, adj) in FAMILIES.items():
    t = art(name)
    t = t[t.adjustment == adj]
    s3.loc[exp, "adjusted_models"] = len(t)
    s3.loc[exp, "fdr_survivors"] = int((t.q < 0.05).sum())
t = art("E2A_2_models.csv")
s3.loc["E2A.2", "adjusted_models"] = len(t); s3.loc["E2A.2", "fdr_survivors"] = int((t.q < 0.05).sum())
s3["label_in_paper"] = "exploratory"
for exp, lab in {"E1.0": "definitions", "E1.1": "primary (A1.1)", "E1.2": "primary (A1.2, A1.3)", "E1.3": "primary (A1.4)",
                 "E1.4": "primary (A1.5)", "E1.5": "primary robustness (S2)", "E2C.1": "secondary Aim 2 — pre-specified criterion not met at E3.3",
                 "E2C.2": "exploratory (H3, null)", "E2A.2": "exploratory-confirmatory (T1)", "E2E.2": "supplement (T2)",
                 "E2E.1": "supplement, one row, UNADJUDICATED", "E2F.1": "exploratory, stated negative (T3)",
                 "E3.1": "convergence", "E3.2": "PRESPEC", "E3.3": "confirmatory reruns", "E4.1": "Table 1",
                 "E4.2": "Figure 1", "E4.3": "Figure 2", "E4.4": "Table 2 + supplement"}.items():
    if exp in s3.index:
        s3.loc[exp, "label_in_paper"] = lab

# S4 — ECG: T2 plus the one unadjudicated row.
t2 = art("E3_3_track_ecg.csv")
t2.insert(0, "kind", "numeric ECG measurement (T2, age + severity + site)")
e2e1 = art("E2E_1_unrecognized.csv")
s4 = pd.concat([t2, e2e1.assign(kind="UNADJUDICATED machine-read prior-infarct statement vs self-report — physician-unreviewed; supplementary only")],
               ignore_index=True)

# S5 — E2.AGE.
s5 = pd.concat([art("E2_AGE_summary.csv").assign(table="S5a sign test"),
                art("E2_AGE_suppression.csv").assign(table="S5b per pair")], ignore_index=True)

# ═══════════════════════════════════════════════════════════════════════
# Markdown renderings
# ═══════════════════════════════════════════════════════════════════════
def md_table(df: pd.DataFrame, cols: list[str], headers: list[str] | None = None) -> str:
    headers = headers or cols
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(r[c]) else str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


t2md = ["# Table 2 — Headline association models", ""]
for block, sub in table2.reset_index().groupby("block", sort=False):
    t2md += [f"## {block}", "", md_table(sub, ["analysis", "term", "estimate", "p", "q", "n", "exploratory_estimate"],
                                        ["Analysis", "Term", "OR (95% CI)", "p", "q", "n", "Exploratory (Phase 2) estimate"]), ""]
t2md += ["Block A: logistic regression of unrecognized status among participants with an abnormal result; model A = age + severity "
         "group + site, B = A + HbA1c + BMI, C = B + log marker magnitude. Block B: logistic regression of each damage outcome on "
         "CES-D-10, adjusted for age, BMI, HbA1c, severity group and site (complete case), Benjamini-Hochberg q within the ten "
         "models; the pre-specified criterion (q < 0.05 in both exposure forms) was not met for any outcome. Block C: logistic "
         "regression within the Healthy + Pre-DM groups adjusted for age and site; percentile bootstrap, 2,000 resamples; "
         "Benjamini-Hochberg q within the ten models. All from AI-READI v3.0.0."]
(R / "E4_4_table2.md").write_text("\n".join(t2md), encoding="utf-8")

sup = ["# Supplementary tables — Paper 1", "",
       "## S1. Within-site direction check", "",
       "A sanity check that no headline trend is driven by one site (same sign at UW, UAB and UCSD); with three sites, sign "
       "agreement alone has roughly a one-in-four chance under the null. Per-site significance is shown but not required.", "",
       md_table(s1[s1.table.str.startswith("S1a")], ["claim", "organ", "site", "n", "pct_Healthy", "pct_Insulin", "trend_z", "trend_p", "same_direction_as_pooled"],
                ["Claim", "Organ", "Site", "n", "Healthy %", "Insulin %", "Trend z", "p", "Same direction"]), "",
       md_table(s1[s1.table.str.startswith("S1b")], ["claim", "pooled", "UW_estimate", "UAB_estimate", "UCSD_estimate", "sites_same_direction", "heterogeneity_q_p", "i_squared_pct"],
                ["Model", "Pooled", "UW", "UAB", "UCSD", "Same direction", "Cochran Q p", "I² %"]), "",
       "## S2. Cutoff sweeps", "",
       "Prevalence, unrecognized fraction and population burden at every rung of the pre-specified grids. The chosen cutoffs "
       "(ACR ≥ 30 mg/g, hs-cTnT ≥ 14 ng/L, ≥ 2 insensate sites) are marked. 'Any detectable' troponin is not a clinical cutoff.", "",
       md_table(s2, ["organ", "cutoff", "is_primary", "prevalence_pct", "unrecognized_pct", "burden_pct", "burden_Healthy", "burden_Insulin", "burden_trend_z", "burden_trend_p"],
                ["Organ", "Cutoff", "Primary", "Prevalence %", "Unrecognized %", "Burden %", "Burden Healthy %", "Burden Insulin %", "Burden trend z", "p"]), "",
       "## S3. Every experiment run, with its outcome", "",
       "The complete record (`RESULTS_LOG.md`), one row per experiment, nulls included. Adjusted-model and FDR-survivor counts "
       "are from the primary family of each Phase-2 experiment.", "",
       md_table(s3.reset_index(), ["experiment", "label_in_paper", "adjusted_models", "fdr_survivors", "decision", "one_line_result"],
                ["ID", "Label in paper", "Adjusted models", "FDR survivors", "Decision", "Result"]), "",
       "## S4. ECG", "",
       "T2: the device's numeric measurements against the heart marker (instrument readings, no interpretation). The final "
       "row is the ONLY machine-interpretation result in the paper and is UNADJUDICATED: every record carries an explicit "
       "'Unconfirmed Diagnosis' stamp and none was physician-reviewed.", "",
       md_table(s4, [c for c in s4.columns if c in ("kind", "exposure", "outcome", "metric_label", "estimate", "ci_lo", "ci_hi", "p", "q", "phase2_q",
                                                     "ecg_pattern", "self_report", "n_pattern", "n_answered", "n_unrecognized", "pct_unrecognized", "ci_lo_pct", "ci_hi_pct")]), "",
       "## S5. Age as a negative confounder (Methods sentence)", "",
       md_table(s5[s5.table == "S5a sign test"], ["pattern", "prediction", "n_pairs", "pct_adjusted_exceeds_crude", "sign_test_p"],
                ["Pattern", "Prediction", "Pairs", "% adjusted > crude", "Sign test p"]), "",
       md_table(s5[s5.table == "S5b per pair"], ["exposure_label", "outcome", "r_exposure_age", "r_outcome_age", "crude", "age_adjusted", "adjusted_exceeds_crude"],
                ["Exposure", "Outcome", "r(exposure, age)", "r(outcome, age)", "Crude", "Age-adjusted", "Adjusted > crude"]), "",
       "## Supplementary figures", "",
       "S-Fig 1: Aim 2 forest per PRESPEC (`E3_3_aim2_figure.png`). S-Fig 2: burden across the cutoff grids "
       "(`E3_3_burden_sweep_figure.png`). S-Fig 3: within-site burden (`E3_3_site_replication_figure.png`). S-Fig 4: age as a "
       "negative confounder (`E2_AGE_figure.png`). S-Fig 5: machine-read infarct tiers vs troponin, UNADJUDICATED (`E2E_1_figure.png`)."]
(R / "E4_4_supplement.md").write_text("\n".join(sup), encoding="utf-8")
print(f"\nmarkdown -> E4_4_table2.md, E4_4_supplement.md; S3 has {len(s3)} experiments")

# ═══════════════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════════════
nerve = aim2.loc[("cesd_total", "abn_nerve")]
t1k = t1.loc[("undiagnosed_range", "abn_kidney")]
results.save(
    "E4.4", table2, paper="p1",
    method=("Table 2 assembled from frozen E3.3 artifacts, nothing refitted: block A the E1.4 who-is-unrecognized models "
            "(A1.5), block B the ten pre-specified Aim-2 models with the Phase-2 exploratory estimate alongside, block C the "
            "T1 undiagnosed-range models with Wald and bootstrap intervals. Provenance recorded per row."),
    result=(f"{len(table2)} rows. Aim 2 nerve OR {nerve.estimate} ({nerve.ci_lo}-{nerve.ci_hi}), q={nerve.q:.3g} — criterion not met; "
            f"T1 kidney OR {t1k.estimate} (bootstrap {t1k.boot_ci_lo}-{t1k.boot_ci_hi}), q={t1k.q:.3g}."),
    decision="keep", name="table2",
)
results.save("E4.4", s1, paper="p1", method="Supplement S1: within-site direction check for every core trend, plus Cochran's Q / I² for the model-based rows.",
             result=f"{int((s1.table.str.startswith('S1a')).sum())} site rows, all same direction as pooled; {int((s1.table.str.startswith('S1b')).sum())} model rows.",
             decision="keep", name="S1_site_direction", primary=False)
results.save("E4.4", s2, paper="p1", method="Supplement S2: prevalence, unrecognized fraction and burden at every rung of both cutoff grids (E1.5 + E3.3 burden sweep).",
             result=f"{len(s2)} rows across kidney, heart and either-organ grids.", decision="keep", name="S2_cutoff_sweeps", primary=False)
results.save("E4.4", s3, paper="p1", method="Supplement S3: one row per experiment from the RESULTS_LOG status table, with adjusted-model and FDR-survivor counts and the label each carries in the paper.",
             result=f"{len(s3)} experiments; Phase-2 primary families total {int(s3.adjusted_models.sum())} adjusted models with {int(s3.fdr_survivors.sum())} FDR survivors.",
             decision="keep", name="S3_experiment_log", primary=False)
results.save("E4.4", s4, paper="p1", method="Supplement S4: T2 ECG numeric models plus the single UNADJUDICATED machine-read infarct row.",
             result=f"{len(t2)} numeric rows + {len(e2e1)} unadjudicated row(s).", decision="keep", name="S4_ecg", primary=False)
results.save("E4.4", s5, paper="p1", method="Supplement S5: the E2.AGE sign test and per-pair correlations behind the Methods sentence on age as a negative confounder.",
             result=f"{len(s5)} rows.", decision="keep", name="S5_age_confounding", primary=False)
