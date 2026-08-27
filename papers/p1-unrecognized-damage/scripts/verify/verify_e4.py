"""Independent verification of Phase 4 (Table 1, Figures 1-2, Table 2, supplement).

Phase 4 fits nothing; it assembles. So the checks are of two kinds: Table 1's
cells are re-derived from the raw CSVs (no `aireadi` import, as always), and
every Table 2 / supplement cell is traced back to the frozen artifact it was
copied from. Figures are checked to exist in every promised format.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

import _raw

print("=" * 78)
print("VERIFY E4 — Table 1 from raw; Table 2 and supplement against their sources")
print("=" * 78)

d = _raw.build()
R = _raw.REPO / "papers/p1-unrecognized-damage/results"
GROUPS = _raw.GROUPS

# ── Table 1 from raw ────────────────────────────────────────────────────
print("\nE4.1 — Table 1")
t1 = _raw.artifact("E4_1_table1.csv").set_index(["section", "variable"])


def cell(section, variable, col="Overall"):
    return str(t1.loc[(section, variable), col])


def mean_sd(s):
    return f"{s.mean():.1f} ({s.std():.1f})"


def n_pct(flag):
    s = pd.Series(flag).dropna()
    return f"{int((s > 0).sum()):,} ({100 * (s > 0).mean():.1f}%)"


def med_iqr(s, fmt="{:.1f}"):
    return (fmt + " [" + fmt + "–" + fmt + "]").format(s.median(), s.quantile(.25), s.quantile(.75))


_raw.check("Table 1 participants overall", cell("Cohort", "Participants"), f"{len(d):,}")
for g in GROUPS:
    _raw.check(f"Table 1 participants {g}", cell("Cohort", "Participants", g), f"{int((d.group == g).sum()):,}")
    _raw.check(f"Table 1 age {g}", cell("Cohort", "Age, years", g), mean_sd(d.loc[d.group == g, "age"]))
    _raw.check(f"Table 1 BMI {g}", cell("Body and glycaemia", "BMI, kg/m²", g), mean_sd(d.loc[d.group == g, "bmi"]))
    _raw.check(f"Table 1 HbA1c {g}", cell("Body and glycaemia", "HbA1c, %", g), med_iqr(d.loc[d.group == g, "hba1c"]))
    _raw.check(f"Table 1 ACR median {g}", cell("Kidney", "Urine ACR, mg/g", g), med_iqr(d.loc[d.group == g, "acr"]))
    _raw.check(f"Table 1 kidney abnormal {g}", cell("Kidney", "ACR ≥ 30 mg/g (abnormal)", g), n_pct(d.loc[d.group == g, "abn_kidney"]))
    _raw.check(f"Table 1 heart abnormal {g}", cell("Heart", "hs-cTnT ≥ 14 ng/L (abnormal)", g), n_pct(d.loc[d.group == g, "abn_heart"]))
    _raw.check(f"Table 1 nerve abnormal {g}", cell("Nerve", "≥ 2 insensate sites (abnormal)", g), n_pct(d.loc[d.group == g, "abn_nerve"]))
    _raw.check(f"Table 1 self-reported kidney {g}", cell("Kidney", "Self-reported kidney problems", g), n_pct(d.loc[d.group == g, "sr_kidney"]))
    _raw.check(f"Table 1 self-reported heart {g}", cell("Heart", "Self-reported heart attack or other heart condition", g), n_pct(d.loc[d.group == g, "sr_heart"]))
    _raw.check(f"Table 1 any organ {g}", cell("Multi-organ", "Any organ abnormal (of three)", g), n_pct(d.loc[d.group == g, "abn_any"]))
    two = np.where(d.n_abn.isna(), np.nan, (d.n_abn >= 2).astype(float))
    _raw.check(f"Table 1 two-or-more {g}", cell("Multi-organ", "Two or more organs abnormal", g), n_pct(pd.Series(two)[(d.group == g).to_numpy()]))
    burden = np.where(d.abn_kidney.isna() | d.sr_kidney.isna(), np.nan, (d.abn_kidney.eq(1) & d.sr_kidney.eq(0)).astype(float))
    _raw.check(f"Table 1 kidney burden {g}", cell("Kidney", "Abnormal and unrecognized (burden)", g), n_pct(pd.Series(burden)[(d.group == g).to_numpy()]))
    _raw.check(f"Table 1 either burden {g}", cell("Multi-organ", "Kidney or heart abnormal and unrecognized (burden)", g),
               n_pct(d.loc[d.group == g].pipe(lambda x: np.where(
                   x.abn_kidney.notna() & x.abn_heart.notna() & x.sr_kidney.notna() & x.sr_heart.notna(),
                   ((x.abn_kidney.eq(1) & x.sr_kidney.eq(0)) | (x.abn_heart.eq(1) & x.sr_heart.eq(0))).astype(float), np.nan))))
trop_bd = d.trop_bd.fillna(False).astype(bool) & d.trop.notna()
_raw.check("Table 1 troponin below detection overall", cell("Heart", "hs-cTnT below the 6 ng/L detection limit"),
           f"{int(trop_bd.sum()):,} ({100 * trop_bd.sum() / d.trop.notna().sum():.1f}%)")
_raw.check("Table 1 troponin median overall (all results)", cell("Heart", "hs-cTnT, ng/L (all results; below-detection at 6)"), med_iqr(d.trop))
obs = pd.read_csv(_raw.DS / "clinical_data/observation.csv", low_memory=False,
                  usecols=["person_id", "observation_source_value", "value_as_number"])
obs["k"] = _raw._key(obs.observation_source_value)
v = pd.to_numeric(obs.value_as_number, errors="coerce")
obs["v"] = v.mask(v.isin(_raw.SPECIAL))
cesd = obs[obs.k == "cestl"].groupby("person_id").v.first().reindex(d.index)
_raw.check("Table 1 CES-D screen-positive overall", cell("Psychosocial", "CES-D-10 screen-positive (≥ 10)"),
           n_pct(np.where(cesd.isna(), np.nan, (cesd >= 10).astype(float))))
_raw.check("Table 1 CES-D median overall", cell("Psychosocial", "CES-D-10 score (0–30)"), med_iqr(cesd, "{:.0f}"))
_raw.check("Table 1 markdown rendering exists", (R / "E4_1_table1.md").exists(), True)
_raw.check("Table 1 has no participant-level column", "person_id" not in open(R / "E4_1_table1.csv").read(), True)

# ── Figures ─────────────────────────────────────────────────────────────
print("\nE4.2 / E4.3 — figures")
for name in ["E4_2_figure1", "E4_3_figure2"]:
    for ext in ("png", "pdf", "svg"):
        _raw.check(f"{name}.{ext} exists", (R / f"{name}.{ext}").exists(), True)
    _raw.check(f"{name}_300dpi.png exists", (R / f"{name}_300dpi.png").exists(), True)

# ── Table 2 against its sources ─────────────────────────────────────────
print("\nE4.4 — Table 2")
t2 = _raw.artifact("E4_4_table2.csv")
aim2 = _raw.artifact("E3_3_aim2_confirmatory.csv").set_index(["exposure", "outcome"])
nerve = aim2.loc[("cesd_total", "abn_nerve")]
row = t2[(t2.analysis == "CES-D-10, per SD") & (t2.term == "Nerve abnormal")].iloc[0]
_raw.check("Table 2 Aim-2 nerve OR string", row.estimate, f"{nerve.estimate:.2f} ({nerve.ci_lo:.2f}–{nerve.ci_hi:.2f})")
_raw.check("Table 2 Aim-2 nerve q", row.q, f"{nerve.q:.2f}")
_raw.check("Table 2 Aim-2 nerve n", int(row.n), int(nerve.n))
p2 = _raw.artifact("E2C_1_sweep.csv"); p2 = p2[p2.adjustment == "damage"].set_index(["exposure", "outcome"])
e = p2.loc[("cesd_total", "abn_nerve")]
_raw.check("Table 2 Aim-2 nerve exploratory estimate carries the Phase-2 OR", f"{e.estimate:.2f}" in str(row.exploratory_estimate), True)
t1a = _raw.artifact("E3_3_track_undiagnosed.csv").set_index(["definition", "outcome"])
k = t1a.loc[("undiagnosed_range", "abn_kidney")]
row = t2[(t2.analysis.str.startswith("No diabetes label, HbA1c")) & (t2.term == "Kidney abnormal")].iloc[0]
_raw.check("Table 2 T1 kidney OR string", row.estimate.split(";")[0], f"{k.estimate:.2f} ({k.ci_lo:.2f}–{k.ci_hi:.2f})")
_raw.check("Table 2 T1 kidney bootstrap", f"bootstrap {k.boot_ci_lo:.2f}–{k.boot_ci_hi:.2f}" in row.estimate, True)
_raw.check("Table 2 T1 kidney exposed count", f"{int(k.events_exposed)}/{int(k.n_exposed)}" in str(row.exploratory_estimate), True)
e14 = _raw.artifact("E1_4_models.csv").set_index(["organ", "model", "term"])
row = t2[(t2.analysis == "Kidney — model C") & (t2.term == "log ACR, per unit")].iloc[0]
w = e14.loc[("kidney", "C: B + marker magnitude", "log_acr")]
_raw.check("Table 2 block A log ACR OR", row.estimate, f"{w.odds_ratio:.2f} ({w.ci_lo:.2f}–{w.ci_hi:.2f})")
row = t2[(t2.analysis == "Heart — model C") & (t2.term == "Insulin vs Healthy")].iloc[0]
w = e14.loc[("heart", "C: B + marker magnitude", "C(study_group_label)[T.Insulin]")]
_raw.check("Table 2 block A heart model C Insulin OR", row.estimate, f"{w.odds_ratio:.2f} ({w.ci_lo:.2f}–{w.ci_hi:.2f})")
_raw.check("Table 2 block A heart model C Insulin p is non-significant (suggestive wording)", bool(w.p > 0.05), True)
_raw.check("Table 2 row count", len(t2), 54)
_raw.check("Table 2 markdown exists", (R / "E4_4_table2.md").exists(), True)

# ── Supplement ──────────────────────────────────────────────────────────
print("\nE4.4 — supplement")
s1 = _raw.artifact("E4_4_S1_site_direction.csv")
by_site = _raw.artifact("E3_3_aim1_by_site.csv")
_raw.check("S1a row count = E3.3 by-site rows", int(s1.table.str.startswith("S1a").sum()), len(by_site))
_raw.check("S1a every row same direction", bool(s1[s1.table.str.startswith("S1a")].same_direction_as_pooled.astype(bool).all()), True)
s2 = _raw.artifact("E4_4_S2_cutoff_sweeps.csv")
e15 = _raw.artifact("E1_5_threshold_sweep.csv"); bsw = _raw.artifact("E3_3_burden_sweep.csv")
_raw.check("S2 row count = E1.5 rungs + either-organ rungs", len(s2), len(e15) + int(bsw.organ.str.startswith("either").sum()))
k30 = s2[(s2.organ == "kidney") & (s2.cutoff.astype(str) == "30.0")].iloc[0]
_raw.check("S2 kidney primary rung prevalence = E1.5", float(k30.prevalence_pct), float(e15[(e15.organ == "kidney") & (e15.cutoff.astype(str) == "30.0")].prevalence_pct.iloc[0]))
_raw.check("S2 kidney primary rung burden = E3.3", float(k30.burden_pct), float(bsw[(bsw.organ == "kidney") & (bsw.cutoff.astype(str) == "30.0")].burden_pct.iloc[0]))
s3 = _raw.artifact("E4_4_S3_experiment_log.csv")
log = (_raw.REPO / "papers/p1-unrecognized-damage/RESULTS_LOG.md").read_text()
status_ids = [m.group(1) for m in re.finditer(r"^\|\s*(E[0-9A-Z.]+)\s*\|\s*\w", log, re.M)]
_raw.check("S3 one row per status-table experiment", sorted(s3.experiment), sorted(status_ids))
_raw.check("S3 every experiment done or explicitly rescoped (E0.2 gate)",
           bool(s3.status.isin(["done", "rescope"]).all() or (s3[~s3.status.eq("done")].experiment == "E0.2").all()), True)
expected = 0
for name, adj in [("E2C_1_sweep.csv", "damage"), ("E2C_3_sweep.csv", "damage"), ("E2A_1_sweep.csv", "damage"), ("E2B_1_sweep.csv", "damage"),
                  ("E2D_1_sweep.csv", "damage"), ("E2E_2_sweep.csv", "damage"), ("E2F_1_models.csv", "full"), ("E2C_2.csv", "recognition+marker")]:
    t = _raw.artifact(name); t = t[t.adjustment == adj]; expected += int((t.q < 0.05).sum())
expected += int((_raw.artifact("E2A_2_models.csv").q < 0.05).sum())
_raw.check("S3 FDR-survivor total = source artifacts (= E3.1's 79)", int(s3.fdr_survivors.sum()), expected)
_raw.check("S3 labels Aim 2 as criterion not met", "criterion not met" in str(s3.set_index("experiment").loc["E2C.1", "label_in_paper"]), True)
_raw.check("S3 labels E2E.1 unadjudicated", "UNADJUDICATED" in str(s3.set_index("experiment").loc["E2E.1", "label_in_paper"]), True)
s4 = _raw.artifact("E4_4_S4_ecg.csv")
_raw.check("S4 has exactly the T2 rows plus the unadjudicated row(s)", len(s4), len(_raw.artifact("E3_3_track_ecg.csv")) + len(_raw.artifact("E2E_1_unrecognized.csv")))
_raw.check("S4 unadjudicated row is labelled", bool(s4.kind.str.contains("UNADJUDICATED").any()), True)
s5 = _raw.artifact("E4_4_S5_age_confounding.csv")
_raw.check("S5 carries the sign-test rows", int((s5.table == "S5a sign test").sum()), 2)
sup = (R / "E4_4_supplement.md").read_text()
_raw.check("supplement markdown labels the ECG row unadjudicated", "UNADJUDICATED" in sup, True)
_raw.check("supplement markdown calls the site check a sanity check", "sanity check" in sup, True)
# Column HEADERS only: the S3 experiment log legitimately quotes the E0.4 prose
# "no duplicate person_id", which is a sentence about the cohort, not a column.
_raw.check("no participant-level column in any E4 artifact",
           not any("person_id" in open(p).readline() for p in R.glob("E4_*.csv")), True)
_raw.check("no E4 artifact has 2,280-ish rows (would mean a per-person table)",
           not any(sum(1 for _ in open(p)) > 500 for p in R.glob("E4_*.csv")), True)

_raw.report("E4")
