"""Audit every number quoted in the Phase-3 report against the artifacts.

Same contract as `verify_report.py` and `verify_phase2_report.py`: each claim
names the artifact cell it came from, and the script fails if the report and
the artifact disagree. It also checks the report in the other direction —
that the verdicts it states follow from the artifacts (the Aim-2 criterion,
the burden sweep, the site direction checks) and that every figure it embeds
exists.

Run after any edit to reports/2026-08-25-phase3-report.md.
"""

from __future__ import annotations

import re

import pandas as pd

import _raw

REPORT_PATH = _raw.REPO / "reports" / "2026-08-25-phase3-report.md"
REPORT = REPORT_PATH.read_text()
BARE = REPORT.replace("*", "").replace("`", "")
LOG = (_raw.REPO / "papers/p1-unrecognized-damage/RESULTS_LOG.md").read_text()

print("=" * 78)
print("AUDIT — every number quoted in the Phase-3 report")
print("=" * 78)


def quoted(text: str) -> bool:
    variants = {text, text.replace("-", "−"), text.replace(">= ", "≥ ").replace("-", "–")}
    return any(x in REPORT or x in BARE for x in variants)


def claim(label: str, text: str, source: str) -> None:
    ok = quoted(text)
    print(f"  [{'OK  ' if ok else 'MISS'}] {label:<58} '{text}'  <- {source}")
    if not ok:
        _raw.FAILURES.append(f"{label}: report does not contain '{text}' (from {source})")


def claim_rounded(label: str, value: float, source: str, *, places=(1, 2, 3, 4)) -> None:
    forms = [f"{round(value, p):g}" for p in places]
    forms += [f.replace("-", "−") for f in forms if f.startswith("-")]
    ok = any(quoted(f) for f in forms)
    print(f"  [{'OK  ' if ok else 'MISS'}] {label:<58} {forms[:2]}  <- {source}")
    if not ok:
        _raw.FAILURES.append(f"{label}: no rounding of {value} appears in the report ({source})")


def claim_row(label: str, cells: list[str], source: str) -> None:
    def norm(c):
        return c.replace(">= ", "≥ ").replace("-", "–") if re.match(r"^[0-9.<>= -]+%?$", c) else c
    pattern = r"\|\s*" + r"\s*\|\s*".join(re.escape(norm(c)) for c in cells) + r"\s*\|"
    ok = re.search(pattern, BARE) is not None or re.search(
        r"\|\s*" + r"\s*\|\s*".join(re.escape(c) for c in cells) + r"\s*\|", BARE) is not None
    print(f"  [{'OK  ' if ok else 'MISS'}] {label:<58} {cells}  <- {source}")
    if not ok:
        _raw.FAILURES.append(f"{label}: no table row pairs {cells} (from {source})")


R = _raw.REPO / "papers/p1-unrecognized-damage/results"
confirm = _raw.artifact("E3_3_aim1_confirmatory.csv")
by_site = _raw.artifact("E3_3_aim1_by_site.csv").set_index(["claim", "organ", "site"])
boot = _raw.artifact("E3_3_aim1_bootstrap.csv").set_index(["claim", "organ", "stratum"])
sweep = _raw.artifact("E3_3_burden_sweep.csv").set_index(["organ", "cutoff"])
aim2 = _raw.artifact("E3_3_aim2_confirmatory.csv").set_index(["exposure", "outcome"])
ladder = _raw.artifact("E3_3_aim2_ladder.csv").set_index(["sample", "step", "outcome"])
robust = _raw.artifact("E3_3_aim2_robustness.csv").set_index(["check", "detail", "exposure", "outcome"])
strata = _raw.artifact("E3_3_aim2_by_severity.csv").set_index("stratum")
imp = _raw.artifact("E3_3_aim2_missing_sensitivity.csv").set_index(["exposure", "outcome"])
h3 = _raw.artifact("E3_3_h3.csv").set_index(["exposure", "outcome"])
t1 = _raw.artifact("E3_3_track_undiagnosed.csv").set_index(["definition", "outcome"])
t1r = _raw.artifact("E3_3_track_undiagnosed_robustness.csv").set_index(["check", "detail", "outcome"])
bands = _raw.artifact("E3_3_track_undiagnosed_bands.csv").set_index("hba1c_band")
t2 = _raw.artifact("E3_3_track_ecg.csv").set_index(["exposure", "outcome"])
t2s = _raw.artifact("E3_3_track_ecg_by_site.csv").set_index(["metric", "outcome", "site"])
het = _raw.artifact("E3_3_site_heterogeneity.csv").set_index("analysis")
summary = _raw.artifact("E3_3_headline_summary.csv").set_index("claim")
rank = _raw.artifact("E3_1_ranking.csv")
core = _raw.artifact("E3_1_core_claims.csv")
a15 = _raw.artifact("E3_3_aim1_recognition_models.csv")
timing = _raw.artifact("E2_TIMING_survey_lag.csv").set_index("survey_item")
conc = _raw.artifact("E2_TIMING_marker_concurrence.csv").set_index("marker_item")


def cell(claim_, organ, stratum="Overall"):
    return confirm[(confirm.claim == claim_) & (confirm.organ == organ)].set_index("stratum").loc[stratum]


print("\nHEADLINE TABLE")
c = cell("prevalence", "any")
claim("any-organ prevalence", f"{c.pct}%", "E3_3_aim1_confirmatory prevalence/any"); claim("any-organ k/n", f"{int(c.k)} / {int(c.n):,}", "same")
c = cell("unrecognized_fraction", "either")
claim("either fraction", f"{c.pct}%", "E3_3_aim1_confirmatory fraction/either"); claim("either fraction k/n", f"{int(c.k)} / {int(c.n)}", "same")
claim("either fraction refusals incl.", f"{c.pct_incl_refusals}%", "same, pct_incl_refusals")
c = cell("population_burden", "either")
claim("either burden overall", f"{c.pct}%", "E3_3_aim1_confirmatory burden/either")
claim("either burden Insulin", f"{cell('population_burden', 'either', 'Insulin').pct}%", "same, Insulin")
c = cell("two_or_more_organs", "multi")
claim("two-or-more overall", f"{c.pct}%", "E3_3_aim1_confirmatory multi"); claim("two-or-more Insulin", f"{cell('two_or_more_organs', 'multi', 'Insulin').pct}%", "same, Insulin")
_raw.check("Aim 1 rows all reproduce Phase 1", bool(confirm.reproduces_phase1.all()), True)
claim("rows checked", f"{len(confirm)} rows", "E3_3_aim1_confirmatory row count")
claim("A1.5 term count", f"{len(a15)} terms", "E3_3_aim1_recognition_models row count")

print("\nE3.1")
claim("candidates", f"{len(rank)} associations", "E3_1_ranking"); claim("survivors", f"{int(rank.crit_survives_adjustment.sum())}", "E3_1_ranking")
claim("all-four", f"**{int((rank.criteria_met == 4).sum())}**", "E3_1_ranking")
claim("core all-four", f"**{int((core.criteria_met == 4).sum())} of {len(core)}**", "E3_1_core_claims")
four = rank[rank.criteria_met == 4]
for exp, n in four.experiment.value_counts().items():
    claim(f"all-four count {exp}", f"({exp}) {n}", "E3_1_ranking value_counts")
for exp, expo, out in [("E2A.2", "undiagnosed_range", "abn_kidney"), ("E2A.2", "undiagnosed_range_cgm", "abn_kidney"),
                       ("E2A.2", "undiagnosed_range", "abn_any"), ("E2F.1", "healthcare_access_barriers", "unrec_heart"),
                       ("E2E.2", "qrsd_ms", "abn_heart"), ("E2C.1", "cesd_total", "abn_nerve")]:
    r = rank[(rank.experiment == exp) & (rank.exposure == expo) & (rank.outcome == out)].iloc[0]
    claim(f"rank of {expo}->{out}", f"| {int(r['rank'])} |", "E3_1_ranking rank")
    claim_rounded(f"OR of {expo}->{out}", float(r.estimate), "E3_1_ranking estimate", places=(2,))

print("\n§3 AIM 1 BY SITE, SWEEP, BOOTSTRAP")
for site in _raw.SITES if hasattr(_raw, "SITES") else ["UW", "UAB", "UCSD"]:
    r = by_site.loc[("population_burden", "either", site)]
    claim_row(f"burden by site {site}", [site, f"{r.pct_Healthy}%", f"{r.pct_Insulin}%", f"{r.trend_z:.2f}"], "E3_3_aim1_by_site")
kid = by_site.loc[("unrecognized_fraction", "kidney")]
claim_rounded("kidney fraction z UW", float(kid.loc["UW", "trend_z"]), "by_site", places=(2,))
claim_rounded("kidney fraction z UAB", float(kid.loc["UAB", "trend_z"]), "by_site", places=(2,))
claim_rounded("kidney fraction z UCSD", float(kid.loc["UCSD", "trend_z"]), "by_site", places=(2,))
claim("kidney fraction UCSD p", f"p = {kid.loc['UCSD', 'trend_p']:.3f}", "by_site")
n_sig3 = int(by_site.groupby(["claim", "organ"]).significant_within_site.sum().eq(3).sum())
claim("claims significant within all three sites", f"{n_sig3}", "by_site")
_raw.check("all 33 within-site trends keep their sign", bool(by_site.same_direction_as_pooled.all()), True)
for cut in ["20.0", "30.0", "50.0", "100.0", "300.0"]:
    r = sweep.loc[("either (kidney grid)", cut)]
    claim(f"either burden ACR {cut}", f"{r.burden_pct}%", "burden_sweep"); claim_rounded(f"either z ACR {cut}", float(r.burden_trend_z), "burden_sweep", places=(2,))
    claim(f"either burden ACR {cut} H->I", f"{r.burden_Healthy} → {r.burden_Insulin}", "burden_sweep")
for cut in ["detectable", "10.0", "14.0", "16.0", "19.0", "22.0"]:
    r = sweep.loc[("either (heart grid)", cut)]
    claim(f"either burden cTnT {cut}", f"{r.burden_pct}%", "burden_sweep"); claim_rounded(f"either z cTnT {cut}", float(r.burden_trend_z), "burden_sweep", places=(2,))
claim("heart detectable rung p", f"p = {sweep.loc[('heart', 'detectable'), 'burden_trend_p']:.3f}", "burden_sweep")
_raw.check("burden trend positive and significant at every rung", bool((sweep.burden_trend_z > 0).all() and (sweep.burden_trend_p < 0.05).all()), True)
for (claim_, organ, label) in [("unrecognized_fraction", "kidney", "Kidney unrecognized fraction"), ("unrecognized_fraction", "heart", "Heart unrecognized fraction"),
                               ("unrecognized_fraction", "either", "Either-organ unrecognized fraction"), ("population_burden", "either", "Either-organ burden")]:
    r = boot.loc[(claim_, organ, "Insulin")]
    claim_row(f"Insulin bootstrap {organ}", [label, str(int(r.n)), f"{r.pct}", f"{r.wilson_lo}–{r.wilson_hi}", f"{r.boot_lo}–{r.boot_hi}"], "aim1_bootstrap")

print("\n§4 AIM 2")
for outcome, lab in [("abn_kidney", "Kidney abnormal"), ("abn_heart", "Heart abnormal"), ("abn_nerve", "Nerve abnormal"),
                     ("abn_any", "Any organ"), ("abn_multi", "Two or more organs")]:
    a, b = aim2.loc[("cesd_total", outcome)], aim2.loc[("cesd_positive", outcome)]
    claim_row(f"aim2 {outcome}", [lab, f"{a.estimate:.2f} ({a.ci_lo:.2f}–{a.ci_hi:.2f})", f"{a.p:.2f}" if a.p >= 0.1 else f"{a.p:.3f}", f"{a.q:.2f}" if outcome != "abn_nerve" else f"{a.q:.3f}",
                                   f"{b.estimate:.2f} ({b.ci_lo:.2f}–{b.ci_hi:.2f})", f"{b.p:.2f}" if b.p >= 0.1 else f"{b.p:.3f}", f"{b.q:.2f}"], "aim2_confirmatory")
nerve = aim2.loc[("cesd_total", "abn_nerve")]
claim("nerve OR per SD", f"1.16 (95% CI {nerve.ci_lo:.2f}–{nerve.ci_hi:.2f})", "aim2_confirmatory"); claim("nerve q", f"q = {nerve.q:.3f}", "aim2_confirmatory")
claim("nerve p", f"p = {nerve.p:.3f}", "aim2_confirmatory")
_raw.check("verdict follows from the artifact (both forms q<0.05 required)", bool(nerve.q < 0.05 and aim2.loc[("cesd_positive", "abn_nerve"), "q"] < 0.05), False)
_raw.check("summary verdict says not claimed", "NOT claimed" in str(summary.loc["A2.1 CES-D-10 -> nerve abnormal (spec covariates)", "verdict"]), True)
claim("screen-positive raw p", f"p = {aim2.loc[('cesd_positive', 'abn_nerve'), 'p']:.3f}", "aim2_confirmatory")
P2 = "Phase-2 sample (each step's own complete cases)"
FX = [s for s in ladder.index.get_level_values("sample").unique() if s.startswith("fixed")][0]
for step, p2v, fxv in [("+ age + severity + site", "1.218", "1.194"), ("+ age + severity + site + HbA1c", "1.185", "1.184"),
                       ("+ age + severity + site + BMI", "1.193", "1.167"), ("full spec (+ BMI + HbA1c)", "1.161", "1.161")]:
    claim_rounded(f"ladder P2 {step}", float(ladder.loc[(P2, step, "abn_nerve"), "estimate"]), "aim2_ladder", places=(3,))
    claim_rounded(f"ladder fixed {step}", float(ladder.loc[(FX, step, "abn_nerve"), "estimate"]), "aim2_ladder", places=(3,))
    claim(f"ladder P2 n {step}", f"n = {int(ladder.loc[(P2, step, 'abn_nerve'), 'n']):,}", "aim2_ladder")
import numpy as np
drop_total = np.log(ladder.loc[(P2, "+ age + severity + site", "abn_nerve"), "estimate"]) - np.log(ladder.loc[(FX, "full spec (+ BMI + HbA1c)", "abn_nerve"), "estimate"])
drop_sample = np.log(ladder.loc[(P2, "+ age + severity + site", "abn_nerve"), "estimate"]) - np.log(ladder.loc[(FX, "+ age + severity + site", "abn_nerve"), "estimate"])
claim("sample share of attenuation", f"{100 * drop_sample / drop_total:.0f}%", "aim2_ladder (log-OR arithmetic)")
claim("participants lost", f"68 participants", "aim2_ladder n difference"); _raw.check("lost count from ladder", int(ladder.loc[(P2, '+ age + severity + site', 'abn_nerve'), 'n'] - ladder.loc[(FX, 'full spec (+ BMI + HbA1c)', 'abn_nerve'), 'n']), 68)
claim("lost enriched nerve %", "23.5% of them are nerve-abnormal against 14.3%", "E3.3 log line"); _raw.check("log carries the 23.5/14.3 figures", "23.5% nerve-abnormal vs 14.3%" in LOG, True)
im = imp.loc[("cesd_total", "abn_nerve")]; imp_pos = imp.loc[("cesd_positive", "abn_nerve")]
claim("imputed OR", f"OR {im.estimate:.2f} ({im.ci_lo:.2f}–{im.ci_hi:.2f}), q = {im.q:.3f}", "aim2_missing_sensitivity")
claim("imputed screen OR", f"OR {imp_pos.estimate:.2f}, q = {imp_pos.q:.2f}", "aim2_missing_sensitivity")
for site in ["UW", "UAB", "UCSD"]:
    claim_rounded(f"nerve within {site}", float(robust.loc[("within site", site, "cesd_total", "abn_nerve"), "estimate"]), "aim2_robustness", places=(2,))
claim("nerve >=1 OR", f"**{robust.loc[('nerve cutoff', '>= 1 insensate sites', 'cesd_total', 'abn_nerve'), 'estimate']:.2f}**", "aim2_robustness")
claim("nerve >=1 p", f"**{robust.loc[('nerve cutoff', '>= 1 insensate sites', 'cesd_total', 'abn_nerve'), 'p']:.2f}**", "aim2_robustness")
claim_rounded("nerve >=3 OR", float(robust.loc[("nerve cutoff", ">= 3 insensate sites", "cesd_total", "abn_nerve"), "estimate"]), "aim2_robustness", places=(2,))
claim("odd rows p", f"{robust.loc[('drop odd monofilament rows', 'n dropped = 20', 'cesd_total', 'abn_nerve'), 'p']:.3f}", "aim2_robustness")
claim_rounded("PAID mutual CES-D OR", float(robust.loc[("PAID-5 head-to-head (identical sample)", "mutually adjusted for PAID-5", "cesd_total", "abn_nerve"), "estimate"]), "aim2_robustness", places=(2,))
nonsig = int(((robust.index.get_level_values("outcome") == "abn_nerve") & (robust.p >= 0.05)).sum())
claim("non-significant robustness rows", {12: "Twelve", 11: "Eleven", 13: "Thirteen"}.get(nonsig, str(nonsig)) + " of the sixteen", "aim2_robustness")
claim_row("within severity", ["Within Healthy / Pre-DM / Oral Med / Insulin", " / ".join(f"{strata.loc[g, 'estimate']:.2f}" for g in ["Healthy", "Pre-DM", "Oral Med", "Insulin"]), "none significant"], "aim2_by_severity")
a2h = het.loc["A2.1 CES-D per SD -> nerve"]
claim("aim2 heterogeneity", f"Q p = {a2h.heterogeneity_q_p:.2f}, I² = {a2h.i_squared_pct:.0f}%", "site_heterogeneity")
claim("H3 heart", f"heart OR {h3.loc[('cesd_total', 'unrec_heart'), 'estimate']:.2f}, p = {h3.loc[('cesd_total', 'unrec_heart'), 'p']:.3f}, q = {h3.loc[('cesd_total', 'unrec_heart'), 'q']:.2f}", "h3")
_raw.check("H3 no survivor", int((h3.q < 0.05).sum()), 0)

print("\n§5 T1")
for outcome, lab in [("abn_kidney", "Kidney abnormal"), ("abn_any", "Any organ"), ("abn_heart", "Heart"), ("abn_nerve", "Nerve")]:
    r = t1.loc[("undiagnosed_range", outcome)]
    claim_row(f"T1 {outcome}", [lab if outcome != "abn_kidney" else "Kidney abnormal", f"{int(r.events_exposed)} / {int(r.n_exposed)} ({r.pct_exposed}% vs {r.pct_unexposed}%)",
                               f"{r.estimate:.2f}", f"{r.ci_lo:.2f}–{r.ci_hi:.2f}", f"{r.boot_ci_lo:.2f}–{r.boot_ci_hi:.2f}",
                               f"{r.q:.4f}" if r.q < 0.001 else (f"{r.q:.3f}" if r.q < 0.1 else f"{r.q:.2f}")], "track_undiagnosed")
cg = t1.loc[("undiagnosed_range_cgm", "abn_kidney")]
claim("CGM def OR", f"{cg.estimate:.2f}", "track_undiagnosed"); claim("CGM def events", f"{int(cg.events_exposed)} / {int(cg.n_exposed)}", "track_undiagnosed")
prim = t1.loc[("undiagnosed_range", "abn_kidney")]
claim("T1 phase2 q", f"{prim.phase2_q:.4f} → {prim.q:.4f}", "track_undiagnosed phase2_q/q")
for site in ["UW", "UAB", "UCSD"]:
    r = t1r.loc[("within site", site, "abn_kidney")]
    claim_rounded(f"T1 {site} OR", float(r.estimate), "track_undiagnosed_robustness", places=(2,))
    claim(f"T1 {site} bootstrap", f"{r.boot_ci_lo:.2f}–{r.boot_ci_hi:.1f}" if site == "UCSD" else f"{r.boot_ci_lo:.2f}–{r.boot_ci_hi:.2f}", "track_undiagnosed_robustness")
for band in bands.index:
    r = bands.loc[band]
    claim_row(f"band {band}", [band, f"{int(r.n):,}", f"{int(r.kidney_abnormal)} ({r.pct}%)"], "track_undiagnosed_bands")
t1h = het.loc["T1 undiagnosed-range -> kidney"]
claim("T1 heterogeneity", f"Q p = {t1h.heterogeneity_q_p:.2f}, I² = {t1h.i_squared_pct:.0f}%", "site_heterogeneity")
claim("double-unrecognized", "16 of the 19", "E3.3 log"); _raw.check("log carries double-unrecognized 16 of 19", "double-unrecognized 16 of 19" in LOG, True)

print("\n§6 T2")
for metric, lab in [("qrsd_ms", "QRS duration"), ("qtc_ms", "QTc"), ("rate_bpm", "Heart rate"), ("pr_ms", "PR interval"), ("qt_ms", "QT (uncorrected)")]:
    a, b = t2.loc[(metric, "abn_heart")], t2.loc[(metric, "log_troponin")]
    claim_rounded(f"T2 {metric} OR", float(a.estimate), "track_ecg", places=(2,)); claim_rounded(f"T2 {metric} beta", float(b.estimate), "track_ecg", places=(3,))
for site in ["UW", "UAB", "UCSD"]:
    claim_rounded(f"QRS beta {site}", float(t2s.loc[("qrsd_ms", "log_troponin", site), "estimate"]), "track_ecg_by_site", places=(3,))
q = het.loc["T2 qrsd_ms -> abn_heart"]
claim("QRS abn_heart heterogeneity", f"Q p = {q.heterogeneity_q_p:.3f}, I² = {q.i_squared_pct:.0f}%", "site_heterogeneity")

print("\n§7 TIMING")
claim("timing median", f"{timing.loc['mhoccur_rnl', 'median_days_before_visit']:.0f} days (IQR {timing.loc['mhoccur_rnl', 'iqr_lo']:.0f}–{timing.loc['mhoccur_rnl', 'iqr_hi']:.0f})", "E2_TIMING_survey_lag")
claim("timing same-day", f"{timing.loc['mhoccur_rnl', 'pct_same_day']}% of {int(timing.loc['mhoccur_rnl', 'n_paired']):,}", "E2_TIMING_survey_lag")
claim("albumin same-day", f"{conc.loc['import_urine_albumin', 'pct_same_day_as_troponin']}% of", "E2_TIMING_marker_concurrence")
claim("timing min lag", f"{int(timing.loc['mhoccur_rnl', 'min_days'])} days", "E2_TIMING_survey_lag")

print("\nPROVENANCE AND FIGURES")
for h in ["c6bbb2ec", "c9f2acb6"]:
    claim(f"hash {h} in report", h, "RESULTS_LOG E3.2 / E3.2.AMEND.1"); _raw.check(f"hash {h} in log", h in LOG, True)
for fig in re.findall(r"\]\((\.\./papers/[^)]+\.png)\)", REPORT):
    _raw.check(f"figure exists {fig.split('/')[-1]}", (REPORT_PATH.parent / fig).exists(), True)
_raw.check("report states the criterion is not met", "criterion is not met" in BARE, True)
_raw.check("report states PRESPEC parameters unchanged", "byte-identical" in BARE, True)
_raw.check("report labels the site check a sanity check", "sanity check, not a replication" in BARE, True)
_raw.check("report says PRESPEC was written by Claude", "written by Claude, not with Evan" in BARE, True)
_raw.check("log has E3.1.RUN1, E3.REVIEW, E3.2.AMEND.1 and two E3.FREEZE entries",
           all(k in LOG for k in ["### E3.1.RUN1", "### E3.REVIEW", "### E3.2.AMEND.1"]) and LOG.count("### E3.FREEZE") == 2, True)

_raw.report("PHASE-3 REPORT AUDIT")
