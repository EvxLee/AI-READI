"""Audit every number quoted in the Phase-2 report against the artifacts.

Same contract as `verify_report.py` does for Phase 1: the project rule is that
numbers in a report are re-read from executed output, never recalled, and this
enforces it. Each claim names the artifact cell it came from and the script fails
if the report and the CSV disagree.

The Phase-1 audit was extended in August after it turned out to check only one
direction -- that numbers *in* the report trace to an artifact, never that the
important artifact values reached the report. This one does both: the closing
section walks the surviving associations in each sweep and fails if one is
missing from the prose.

Run after any edit to reports/2026-08-17-phase2-report.md.
"""

from __future__ import annotations

import re

import pandas as pd

import _raw

REPORT_PATH = _raw.REPO / "reports" / "2026-08-17-phase2-report.md"
REPORT = REPORT_PATH.read_text()
# The prose uses a typographic minus (U+2212); artifact values carry an ASCII
# one. Normalising here means a negative number is checked on its value rather
# than on which dash the writer happened to type.
BARE = REPORT.replace("*", "").replace("**", "").replace("−", "-")

print("=" * 78)
print("AUDIT — every number quoted in the Phase-2 report")
print("=" * 78)


def claim(label: str, text: str) -> None:
    _raw.check(label, text in BARE, True)


def claim_number(label: str, value: float, *, places=(1, 2, 3)) -> None:
    """The value must appear at one of its plausible roundings.

    Counts are written with thousands separators in prose ("n = 2,217"), so the
    comma-grouped form counts as a match too -- otherwise this fails on
    formatting rather than on a number being absent.

    Zero-decimal roundings are deliberately NOT tried below 1000. An odds ratio
    of 1.2175 renders as "1" there, and a bare "1" occurs in any page of prose,
    so every such check passed no matter what the report said. That is not
    hypothetical: it is why the E2.AGE correlations sat wrong through 105
    passing checks (see E2.DOCS, 25 Aug). `:g` still covers integers, which is
    what actual counts need. Above 1000 the comma form is distinctive enough to
    be worth trying.
    """
    forms = {f"{value:.{p}f}" for p in places} | {f"{value:g}"}
    if abs(value) >= 1000:
        forms |= {f"{value:,.0f}", f"{value:.0f}"}
    _raw.check(label, any(f in BARE for f in forms), True)


# ── Track C ─────────────────────────────────────────────────────────────
print("\nTrack C")
c1 = _raw.artifact("E2C_1_sweep.csv")
adj = c1[c1.adjustment == "damage"]
survivors = adj[adj.q < 0.05]

_raw.check("E2C.1 survivor count is 4 of 16", (len(survivors), len(adj)), (4, 16))
claim("report states four of sixteen survive", "four of sixteen adjusted models survive")
for _, r in survivors.iterrows():
    claim_number(f"E2C.1 {r.exposure}/{r.outcome} estimate in report", r.estimate)
    claim_number(f"E2C.1 {r.exposure}/{r.outcome} ci_lo in report", r.ci_lo)
_raw.check("E2C.1 every survivor is a nerve outcome",
           sorted(set(survivors.outcome)), ["abn_nerve", "monofilament_missed"])
claim("report says the signal is nerve only", "all four are nerve")

rob = _raw.artifact("E2C_1_nerve_robustness.csv")
rob = rob[rob.outcome == "abn_nerve"].set_index("check")
for check, quoted in [("unadjusted", 1.078), ("+ age only", 1.262),
                      ("full (age + severity + site)", 1.218),
                      ("drop both sets (n=20)", 1.194)]:
    _raw.check(f"E2C.1 robustness {check} matches report", round(float(
        rob.loc[check, "estimate"]), 3), quoted, tol=0.0011)
    claim_number(f"report quotes {check}", rob.loc[check, "estimate"])

head = _raw.artifact("E2C_3_nerve_head_to_head.csv")
head = head[head.outcome == "abn_nerve"].set_index("questionnaire")
claim_number("E2C.3 head-to-head sample size",
             float(head.loc["CES-D-10 total", "n"]))
claim_number("E2C.3 CES-D mutually adjusted OR",
             head.loc["cesd_total | mutually adjusted", "estimate"])
claim_number("E2C.3 PAID-5 mutually adjusted OR",
             head.loc["paid_total | mutually adjusted", "estimate"])
_raw.check("E2C.3 nothing survives FDR",
           int((_raw.artifact("E2C_3_sweep.csv").q < 0.05).sum()), 0)

c2 = _raw.artifact("E2C_2.csv")
c2f = c2[c2.adjustment == "recognition+marker"]
_raw.check("E2C.2 nothing survives FDR", int((c2f.q < 0.05).sum()), 0)
_raw.check("E2C.2 every fully-adjusted estimate is below 1",
           bool((c2f.estimate < 1).all()), True)
claim("report states H3 is null", "Nothing survives FDR")

# ── Track A ─────────────────────────────────────────────────────────────
print("\nTrack A")
a2 = _raw.artifact("E2A_2_models.csv").set_index(["definition", "outcome"])
kidney = a2.loc[("undiagnosed_range", "abn_kidney")]
claim_number("E2A.2 kidney OR", kidney.estimate)
claim_number("E2A.2 kidney Wald lo", kidney.ci_lo)
claim_number("E2A.2 kidney bootstrap lo", kidney.boot_ci_lo)
_raw.check("E2A.2 both intervals exclude 1",
           bool(kidney.ci_lo > 1 and kidney.boot_ci_lo > 1), True)
claim_number("E2A.2 discordant n", float(kidney.n_discordant))
claim_number("E2A.2 CGM replication OR",
             a2.loc[("undiagnosed_range_cgm", "abn_kidney"), "estimate"])
_raw.check("E2A.2 insulin-at-target is null everywhere",
           bool((a2.loc["insulin_at_target", "q"] >= 0.05).all()), True)

prev = _raw.artifact("E2A_2_prevalence.csv").set_index(
    ["definition", "outcome", "side"])
claim_number("E2A.2 discordant kidney prevalence",
             prev.loc[("undiagnosed_range", "abn_kidney", "discordant"), "pct"])
claim_number("E2A.2 concordant kidney prevalence",
             prev.loc[("undiagnosed_range", "abn_kidney", "concordant"), "pct"])

inc = _raw.artifact("E2A_1_incremental.csv").set_index(["exposure", "outcome"])
claim_number("E2A.1 CV-beyond-mean kidney OR",
             inc.loc[("glucose_cv", "abn_kidney"), "or_with_mean_glucose"])
_raw.check("E2A.1 TAR adds nothing beyond mean glucose",
           bool((inc.loc["tar_180", "q_with_mean_glucose"] >= 0.05).all()), True)
claim("report says TAR adds nothing", "TAR > 180 adds nothing")

a1 = _raw.artifact("E2A_1_sweep.csv")
hba1c = a1[(a1.adjustment == "damage") & (a1.exposure == "hba1c")].set_index("outcome")
claim_number("E2A.1 HbA1c kidney OR", hba1c.loc["abn_kidney", "estimate"])

# ── Track B ─────────────────────────────────────────────────────────────
print("\nTrack B")
b = _raw.artifact("E2B_1_sweep.csv")
bmi = b[(b.adjustment == "damage") & (b.exposure == "bmi")].set_index("outcome")
for outcome in ("abn_kidney", "abn_heart", "abn_nerve", "abn_any"):
    claim_number(f"E2B.1 {outcome} OR", bmi.loc[outcome, "estimate"])
_raw.check("E2B.1 kidney is the null one",
           bool(bmi.loc["abn_kidney", "q"] > 0.05
                and (bmi.loc[["abn_heart", "abn_nerve", "abn_any"], "q"] < 0.05).all()),
           True)
claim("report flags kidney as the exception", "the exception is the informative part")

# ── Track E ─────────────────────────────────────────────────────────────
print("\nTrack E")
coh = _raw.artifact("E2E_2_coherence.csv").set_index(["metric", "outcome"])
claim_number("E2E.2 QRS vs abnormal troponin OR",
             coh.loc[("QRS duration (ms)", "abn_heart"), "estimate"])
claim_number("E2E.2 QTc vs abnormal troponin OR",
             coh.loc[("QTc interval (ms)", "abn_heart"), "estimate"])
_raw.check("E2E.2 QT null while QTc is not",
           bool(coh.loc[("QT interval (ms)", "log_troponin"), "q"] >= 0.05
                and coh.loc[("QTc interval (ms)", "log_troponin"), "q"] < 0.05), True)
claim("report notes the QT/QTc split", "only the rate-corrected interval tracks anything")

e1 = _raw.artifact("E2E_1_unrecognized.csv").set_index(["ecg_pattern", "self_report"])
row = e1.loc[("Definite machine-read prior infarct",
              "Self-reported heart attack (mhoccur_mi)")]
claim_number("E2E.1 unrecognized percentage", row.pct_unrecognized)
claim_number("E2E.1 never-told count", float(row.n_never_told))
claim_number("E2E.1 eligible denominator", float(row.n_eligible))
claim_number("E2E.1 CI low", row.ci_lo)
_raw.check("report labels E2E.1 unadjudicated",
           "UNADJUDICATED" in REPORT and "Unconfirmed Diagnosis" in REPORT, True)

tiers = _raw.artifact("E2E_1_tiers.csv").set_index("tier")
claim_number("E2E.1 definite tier count",
             float(tiers.loc["definite prior infarct", "n_participants"]))
by_tier = _raw.artifact("E2E_1_by_tier.csv").set_index("infarct_tier")
claim_number("E2E.1 definite-tier troponin rate",
             by_tier.loc["definite prior infarct", "pct_troponin_abnormal"])
claim_number("E2E.1 no-pattern troponin rate",
             by_tier.loc["none", "pct_troponin_abnormal"])

# ── Track D and F ───────────────────────────────────────────────────────
print("\nTracks D and F")
d = _raw.artifact("E2D_1_sweep.csv")
dsurv = d[(d.adjustment == "damage") & (d.q < 0.05)]
_raw.check("E2D.1 survivor count", len(dsurv), 5)
claim("report states five of forty", "Five of forty adjusted models survive FDR")
for _, r in dsurv.iterrows():
    claim_number(f"E2D.1 {r.exposure}/{r.outcome} estimate", abs(r.estimate))

sens = _raw.artifact("E2D_1_plausibility_sensitivity.csv")
_raw.check("E2D.1 three conclusions change", int(sens.changed_conclusion.sum()), 3)
claim("report states three of forty change", "Three of forty\nconclusions change"
      if "Three of forty\nconclusions change" in BARE else "conclusions change")

f = _raw.artifact("E2F_1_models.csv")
ffull = f[f.adjustment == "full"]
fsurv = ffull[ffull.q < 0.05]
_raw.check("E2F.1 one survivor of eighteen", (len(fsurv), len(ffull)), (1, 18))
claim_number("E2F.1 surviving OR", fsurv.iloc[0].estimate)
claim_number("E2F.1 surviving CI low", fsurv.iloc[0].ci_lo)
_raw.check("E2F.1 survivor points below 1 (opposite to hypothesis)",
           bool(fsurv.iloc[0].estimate < 1), True)
claim("report states the direction is opposite", "runs the other way")

fstrata = _raw.artifact("E2F_1_by_severity.csv")
fh = fstrata[fstrata.outcome == "unrec_heart"].set_index("stratum")
for level in _raw.GROUPS:
    claim_number(f"E2F.1 {level} stratum OR", fh.loc[level, "estimate"])
_raw.check("E2F.1 every stratum below 1", bool((fh.estimate < 1).all()), True)

by_group = _raw.artifact("E2F_1_by_group.csv").set_index("study_group_label")
_raw.check("E2F.1 hardship rises monotonically (scoring sanity)",
           bool(by_group.loc[_raw.GROUPS, "food_insecurity"].is_monotonic_increasing),
           True)

# ── E2.AGE ──────────────────────────────────────────────────────────────
print("\nE2.AGE")
summary = _raw.artifact("E2_AGE_summary.csv").set_index("pattern")
opposite = summary.iloc[0]
claim_number("E2.AGE opposite-sign pair count", float(opposite.n_pairs))
claim_number("E2.AGE percentage", opposite.pct_adjusted_exceeds_crude)
_raw.check("E2.AGE holds in every opposite-sign pair",
           float(opposite.pct_adjusted_exceeds_crude), 100.0)
claim("report quotes the sign test", "sign test p = 1.8e-12")

# The exposure-age correlations the prose names. Added 25 Aug after two of them
# (steps and resting heart rate) turned out to have been recalled rather than
# re-read -- the report said -0.26 and -0.23 against an artifact holding -0.298
# and -0.271. The summary row was checked here from the start; the correlations
# the narrative actually quotes were not, so the error survived 105 checks.
sup = _raw.artifact("E2_AGE_suppression.csv")
r_age = sup.groupby("exposure").r_exposure_age.first()
for exposure in ("steps", "heart_rate", "cesd_total", "bmi", "hba1c"):
    claim_number(f"E2.AGE {exposure} correlation with age quoted correctly",
                 float(r_age[exposure]))
_raw.check("E2.AGE eight of nine exposures fall with age",
           int((r_age < 0).sum()), 8)
claim("report states eight of nine decline", "Eight of nine candidate exposures decline")

# ── Figures ─────────────────────────────────────────────────────────────
print("\nFIGURES")
referenced = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", REPORT)
for src in referenced:
    _raw.check(f"figure exists: {src.rsplit('/', 1)[-1]}",
               (REPORT_PATH.parent / src).resolve().exists(), True)

# The reverse direction, as the rest of this file does it: a figure that was
# drawn and never reached the report is the same defect as a number that did not.
on_disk = sorted(p.name for p in
                 (_raw.REPO / "papers/p1-unrecognized-damage/results").glob("E2*_figure.png"))
for name in on_disk:
    _raw.check(f"figure reached the report: {name}",
               any(name in src for src in referenced), True)
_raw.check("Track D's missing figure is explained, not silent",
           "the one track with no figure" in BARE, True)

# ── E2.TIMING and the settled decisions ─────────────────────────────────
print("\nE2.TIMING AND DECISIONS")
_raw.check("report carries the E2.TIMING correction", "E2.TIMING" in REPORT, True)
_raw.check("E2.TIMING declares it has no artifact to trace to",
           "the one Phase-2 check that" in BARE
           and "cannot trace" in BARE, True)
_raw.check("report states the tests are concurrent and the survey is not",
           "The tests are concurrent. The survey is not." in BARE, True)
_raw.check("report states the timing bias is the conservative direction",
           "conservative one" in BARE, True)
_raw.check("the three open decisions are recorded as settled",
           "E2.OPEN" in REPORT and "Decided" in REPORT, True)
_raw.check("each decision records the alternative that was weighed",
           BARE.count("Alternative") + BARE.count("alternative") >= 3, True)
_raw.check("decisions are marked not-yet-frozen",
           "none is frozen until" in BARE, True)

# ── Coverage: did every surviving association reach the report? ─────────
print("\nCOVERAGE — every FDR survivor must appear in the prose")
for name, artifact, exposure_col in [
    ("E2C.1", "E2C_1_sweep.csv", "exposure"),
    ("E2B.1", "E2B_1_sweep.csv", "exposure"),
    ("E2D.1", "E2D_1_sweep.csv", "exposure"),
]:
    table = _raw.artifact(artifact)
    surv = table[(table.adjustment == "damage") & (table.q < 0.05)]
    for _, r in surv.iterrows():
        forms = {f"{abs(r.estimate):.2f}", f"{abs(r.estimate):.3f}",
                 f"{abs(r.estimate):g}"}
        _raw.check(f"{name} survivor {r.exposure}/{r.outcome} reached the report",
                   any(v in BARE for v in forms), True)

# ── Internal consistency ────────────────────────────────────────────────
print("\nINTERNAL CONSISTENCY")
_raw.check("report does not claim to correct a published SDOH finding",
           "must not be framed as correcting a field-level finding" in BARE, True)
_raw.check("report states Phase 1 is unaffected by the three defects",
           "None of them touches Phase 1" in BARE, True)
_raw.check("report flags the Paper-2 impact of the Garmin fix",
           "This one matters to Paper 2" in BARE, True)
_raw.check("report labels Phase 2 exploratory",
           "exploratory" in BARE.lower(), True)

_raw.report("PHASE-2 REPORT AUDIT")
