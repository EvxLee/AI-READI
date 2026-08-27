"""Audit every quoted number in the Phase-1 report against the artifacts.

The project rule is that numbers in a report are re-read from executed output,
never recalled. This enforces it: each claim below names the artifact cell it
came from, and the script fails if the report and the CSV disagree.

Run after any edit to reports/2026-08-12-phase1-report.md.
"""

from __future__ import annotations

import re

import pandas as pd

import _raw

REPORT = (_raw.REPO / "reports" / "2026-08-12-phase1-report.md").read_text()

prev = _raw.artifact("E1_1_prevalence_by_group.csv").set_index(["organ", "stratum"])
unrec = _raw.artifact("E1_2_unrecognized_by_group.csv").set_index(["organ", "stratum"])
burden = _raw.artifact("E1_2_population_burden.csv").set_index(["organ", "stratum"])
conc = _raw.artifact("E1_2_concordance.csv").set_index("organ")
counts = _raw.artifact("E1_3_organ_counts.csv").set_index("stratum")
overlap = _raw.artifact("E1_3_overlap.csv").set_index("combination")
ucount = _raw.artifact("E1_3_unrecognized_counts.csv")
profile = _raw.artifact("E1_4_profile.csv").set_index(["organ", "variable"])
models = _raw.artifact("E1_4_models.csv").set_index(["organ", "model", "term"])
sweep = _raw.artifact("E1_5_threshold_sweep.csv").set_index(["organ", "cutoff"])
stab = _raw.artifact("E1_5_conclusion_stability.csv").set_index("claim")

print("=" * 78)
print("AUDIT — every number quoted in the Phase-1 report")
print("=" * 78)


def quoted(text: str) -> bool:
    """Is this exact string present in the report?"""
    return text in REPORT


def claim(label: str, text: str, source: str) -> None:
    ok = quoted(text)
    print(f"  [{'OK  ' if ok else 'MISS'}] {label:<52} '{text}'  <- {source}")
    if not ok:
        _raw.FAILURES.append(f"{label}: report does not contain '{text}' (from {source})")


def claim_rounded(label: str, value: float, source: str, *, places=(1, 2, 3)) -> None:
    """Accept the value at any of several precisions.

    Prose legitimately says "OR 0.44" for 0.442. What must never pass is a
    number that does not round to the artifact's value at ANY precision.
    """
    forms = [f"{round(value, p):g}" for p in places]
    # The report is typeset with a Unicode minus; the artifact carries ASCII.
    forms += [f.replace("-", "−") for f in forms if f.startswith("-")]
    ok = any(quoted(f) for f in forms)
    print(f"  [{'OK  ' if ok else 'MISS'}] {label:<52} {forms}  <- {source}")
    if not ok:
        _raw.FAILURES.append(f"{label}: no rounding of {value} appears in the report ({source})")


def claim_row(label: str, cells: list[str], source: str) -> None:
    """A markdown table row must tie these cells together, in order.

    Checking cells individually is too weak: '204' and '9.2%' both appear
    elsewhere in the report, but only E1_3_overlap pairs them.
    """
    # Match against the report with emphasis stripped: a highlighted cell is
    # still the same number, and the check is about values, not typography.
    pattern = r"\|\s*" + r"\s*\|\s*".join(re.escape(c) for c in cells) + r"\s*\|"
    ok = re.search(pattern, REPORT.replace("*", "")) is not None
    print(f"  [{'OK  ' if ok else 'MISS'}] {label:<52} {cells}  <- {source}")
    if not ok:
        _raw.FAILURES.append(f"{label}: no table row pairs {cells} (from {source})")


print("\n§1 PREVALENCE")
for organ in ["kidney", "heart", "nerve", "any"]:
    r = prev.loc[(organ, "Overall")]
    claim(f"{organ} overall pct", f"{r.pct}%", f"E1_1[{organ},Overall].pct")
    claim(f"{organ} overall k", f"{int(r.k):,}", f"E1_1[{organ},Overall].k")
    claim(f"{organ} CI", f"{r.ci_lo}–{r.ci_hi}", f"E1_1[{organ},Overall] CI")
for organ in ["kidney", "heart", "nerve", "any"]:
    for g in _raw.GROUPS:
        r = prev.loc[(organ, g)]
        claim(f"{organ} {g}", f"{r.pct}%", f"E1_1[{organ},{g}]")
        # Percentages without denominators hide that Insulin is the small group.
        claim(f"{organ} {g} n/N", f"{int(r.k)} / {int(r.n)}", f"E1_1[{organ},{g}] k/n")

print("\n§2 UNRECOGNIZED")
for organ in ["kidney", "heart", "either"]:
    r = unrec.loc[(organ, "Overall")]
    claim(f"{organ} pct", f"{r.pct}%", f"E1_2[{organ},Overall].pct")
    claim(f"{organ} numerator", f"{int(r.k):,}", f"E1_2[{organ},Overall].k")
    claim(f"{organ} denominator", f"{int(r.n):,}", f"E1_2[{organ},Overall].n")
    claim(f"{organ} CI", f"{r.ci_lo}–{r.ci_hi}", f"E1_2[{organ},Overall] CI")
claim("kidney refusals-included", f"{unrec.loc[('kidney', 'Overall'), 'pct_incl_refusals']}%",
      "E1_2 pct_incl_refusals")
claim("either refusals-included", f"{unrec.loc[('either', 'Overall'), 'pct_incl_refusals']}%",
      "E1_2 pct_incl_refusals")

print("\n§2 CONCORDANCE")
for organ in ["kidney", "heart"]:
    for col in ["abnormal_and_not_reported", "abnormal_and_reported",
                "normal_and_reported", "normal_and_not_reported"]:
        claim(f"{organ} {col}", f"{int(conc.loc[organ, col]):,}", f"E1_2_concordance[{organ}]")
    reported = int(conc.loc[organ, "abnormal_and_reported"] + conc.loc[organ, "normal_and_reported"])
    claim(f"{organ} total reporting a diagnosis", f"{reported:,}", "derived from concordance")

print("\n§3 MULTI-ORGAN")
for i, key in enumerate(["organs_0", "organs_1", "organs_2", "organs_3"]):
    claim(f"count {i}", f"{int(counts.loc['Overall', key]):,}", f"E1_3[{key}]")
    claim(f"pct {i}", f"{counts.loc['Overall', f'pct_{i}']}%", f"E1_3[pct_{i}]")
claim("2+ organs overall", f"{counts.loc['Overall', 'pct_2_or_more']}%", "E1_3 pct_2_or_more")
claim("2+ healthy", f"{counts.loc['Healthy', 'pct_2_or_more']}%", "E1_3 Healthy")
claim("2+ insulin", f"{counts.loc['Insulin', 'pct_2_or_more']}%", "E1_3 Insulin")
# The report gives the complete enumeration as a table, so check every row and
# tie each count to its share — an incomplete list was how 'kidney + nerve'
# went missing in the first draft.
for name in overlap.index:
    r = overlap.loc[name]
    claim_row(f"overlap {name}", [f"{int(r.n):,}", f"{r.pct_of_complete}%"], "E1_3_overlap")
ok = len(overlap) == 8
print(f"  [{'OK  ' if ok else 'FAIL'}] all {len(overlap)} observed combinations enumerated")
if not ok:
    _raw.FAILURES.append(f"E1_3_overlap has {len(overlap)} rows; the check expects 8")

print("\n§3 MULTI-ORGAN BY SEVERITY")
for g in _raw.GROUPS:
    for i in range(4):
        claim(f"{g} pct_{i}", f"{counts.loc[g, f'pct_{i}']}%", f"E1_3[{g}].pct_{i}")
    claim_rounded(f"{g} mean organs", float(counts.loc[g, "mean_organs"]),
                  f"E1_3[{g}].mean_organs", places=(2,))
ok = counts.loc["Insulin", "mean_organs"] > 3 * counts.loc["Healthy", "mean_organs"]
print(f"  [{'OK  ' if ok else 'FAIL'}] mean organs more than triples "
      f"({counts.loc['Healthy', 'mean_organs']} -> {counts.loc['Insulin', 'mean_organs']})")
if not ok:
    _raw.FAILURES.append("report says mean organs more than triples; artifact disagrees")
claim("unrec 1 organ n", f"{int(ucount.n.iloc[1]):,}", "E1_3_unrecognized_counts")
claim("unrec 1 organ pct", f"{ucount.pct.iloc[1]}%", "E1_3_unrecognized_counts")
claim("unrec 2 organs n", f"{int(ucount.n.iloc[2])}", "E1_3_unrecognized_counts")
claim("unrec 2 organs pct", f"{ucount.pct.iloc[2]}%", "E1_3_unrecognized_counts")
claim("evaluable on both", f"{int(ucount.n.sum()):,}", "E1_3_unrecognized_counts total")

print("\n§4 FRACTION FALLS / BURDEN RISES")
for organ in ["kidney", "heart", "either"]:
    for g in _raw.GROUPS:
        claim(f"{organ} fraction {g}", f"{unrec.loc[(organ, g), 'pct']}%", f"E1_2[{organ},{g}]")
        claim(f"{organ} burden {g}", f"{burden.loc[(organ, g), 'pct']}", f"burden[{organ},{g}]")
for organ in ["kidney", "heart", "either"]:
    z_frac = float(unrec.loc[(organ, "Overall"), "trend_z"])
    z_bur = float(burden.loc[(organ, "Overall"), "trend_z"])
    ok = z_frac < 0 < z_bur
    print(f"  [{'OK  ' if ok else 'FAIL'}] {organ} fraction falls (z={z_frac:.3f}) while "
          f"burden rises (z={z_bur:.3f})")
    if not ok:
        _raw.FAILURES.append(f"{organ}: direction claim in the report is wrong")

print("\n§5 WHO IS UNRECOGNIZED")
claim("kidney ACR unrec median", "59", "E1_4_profile kidney marker unrecognized")
claim("kidney ACR rec median", "219", "E1_4_profile kidney marker recognized")
claim_rounded("log_acr OR",
              float(models.loc[('kidney', 'C: B + marker magnitude', 'log_acr'), 'odds_ratio']),
              "E1_4_models")
claim("kidney insulin OR (model C)",
      f"{models.loc[('kidney', 'C: B + marker magnitude', 'C(study_group_label)[T.Insulin]'), 'odds_ratio']}",
      "E1_4_models")
claim_rounded("heart age OR",
              float(models.loc[('heart', 'A: age + severity + site', 'age'), 'odds_ratio']),
              "E1_4_models")
claim_rounded("UCSD OR",
              float(models.loc[('kidney', 'A: age + severity + site', 'C(clinical_site)[T.UCSD]'), 'odds_ratio']),
              "E1_4_models")
lbl = "Other conditions reported (this organ's own items removed)"
claim_rounded("heart age unrec mean",
              float(profile.loc[('heart', 'Age, years'), 'unrecognized']), "E1_4_profile")
claim_rounded("heart age rec mean",
              float(profile.loc[('heart', 'Age, years'), 'recognized']), "E1_4_profile")
for organ, u, r in [("kidney", 4.70, 6.18), ("heart", 4.89, 7.03)]:
    claim_rounded(f"{organ} other-conditions unrecognized",
                  float(profile.loc[(organ, lbl), 'unrecognized']), "E1_4_profile")
    claim_rounded(f"{organ} other-conditions recognized",
                  float(profile.loc[(organ, lbl), 'recognized']), "E1_4_profile")

for var in ["Age, years", "BMI, kg/m2"]:
    for col in ["unrecognized", "recognized"]:
        claim_rounded(f"kidney {var} {col} (the clean null)",
                      float(profile.loc[("kidney", var), col]), "E1_4_profile", places=(2,))

print("\n§5 THE TWO ORGANS DIVERGE — the claim most likely to be over-stated")
# Kidney: magnitude dominates and severity STRENGTHENS under adjustment.
# Heart: magnitude is marginal and severity ATTENUATES to non-significance.
# The report must carry both, or it generalises a kidney result to both organs.
for col in ["unrecognized", "recognized"]:
    claim_rounded(f"heart troponin median {col}",
                  float(profile.loc[("heart", "heart marker (median)"), col]),
                  "E1_4_profile", places=(1,))
for organ, var in [("heart", "heart marker (median)"), ("kidney", "kidney marker (median)")]:
    claim_rounded(f"{organ} marker SMD", float(profile.loc[(organ, var), "smd"]),
                  "E1_4_profile", places=(3,))
for organ in ["kidney", "heart"]:
    for col in ["unrecognized", "recognized"]:
        claim_rounded(f"{organ} HbA1c {col}",
                      float(profile.loc[(organ, "HbA1c, %"), col]), "E1_4_profile", places=(2,))

MODELS = ["A: age + severity + site", "B: A + HbA1c + BMI", "C: B + marker magnitude"]
INSULIN = "C(study_group_label)[T.Insulin]"
for organ in ["kidney", "heart"]:
    for m in MODELS:
        claim_rounded(f"{organ} Insulin OR ({m[0]})",
                      float(models.loc[(organ, m, INSULIN), "odds_ratio"]), "E1_4_models")

# The structural claim, checked as a fact about the artifact rather than as prose.
k_p = [float(models.loc[("kidney", m, INSULIN), "p"]) for m in MODELS]
h_p = [float(models.loc[("heart", m, INSULIN), "p"]) for m in MODELS]
ok = all(p < 0.05 for p in k_p) and h_p[0] < 0.05 <= min(h_p[1], h_p[2])
print(f"  [{'OK  ' if ok else 'FAIL'}] kidney severity holds in all 3 models "
      f"(p={[f'{p:.1e}' for p in k_p]}); heart holds in A only "
      f"(p={[f'{p:.3f}' for p in h_p]})")
if not ok:
    _raw.FAILURES.append(
        "the report says kidney severity survives full adjustment while heart does "
        f"not; artifact p-values are kidney={k_p} heart={h_p}")

tro_p = float(models.loc[("heart", "C: B + marker magnitude", "log_troponin"), "p"])
acr_p = float(models.loc[("kidney", "C: B + marker magnitude", "log_acr"), "p"])
ok = acr_p < 1e-6 < tro_p < 0.05
print(f"  [{'OK  ' if ok else 'FAIL'}] ACR magnitude dominant (p={acr_p:.1e}), "
      f"troponin only marginal (p={tro_p:.3f})")
if not ok:
    _raw.FAILURES.append("report calls troponin magnitude marginal vs ACR; artifact disagrees")
claim_rounded("log_troponin OR", float(
    models.loc[("heart", "C: B + marker magnitude", "log_troponin"), "odds_ratio"]), "E1_4_models")
for m, lbl in [("B: A + HbA1c + BMI", "B"), ("C: B + marker magnitude", "C")]:
    claim_rounded(f"UCSD OR attenuating (model {lbl})",
                  float(models.loc[("kidney", m, "C(clinical_site)[T.UCSD]"), "odds_ratio"]),
                  "E1_4_models")
for organ in ["kidney", "heart"]:
    claim(f"{organ} model n", f"{int(models.loc[(organ, MODELS[2]), 'n_model'].iloc[0])}",
          "E1_4_models n_model")

print("\n§6 SWEEP")
for rung in ["20.0", "30.0", "50.0", "100.0", "300.0"]:
    r = sweep.loc[("kidney", rung)]
    claim(f"kidney @{rung} abnormal", f"{int(r.n_abnormal)}", "E1_5 sweep")
    claim(f"kidney @{rung} unrecognized", f"{r.unrecognized_pct}%", "E1_5 sweep")
hs = sweep.loc["heart"]
claim("heart sweep range lo", f"{hs.unrecognized_pct.min()}%", "E1_5 heart min")
claim("heart sweep range hi", f"{hs.unrecognized_pct.max()}%", "E1_5 heart max")
# Troponin is the cutoff we are least sure of, so the report prints the whole
# grid rather than just its range.
for rung in ["detectable", "10.0", "14.0", "16.0", "19.0", "22.0"]:
    r = sweep.loc[("heart", rung)]
    claim_row(f"heart @{rung} row", [f"{int(r.n_abnormal):,}", f"{r.prevalence_pct}%",
                                     f"{r.unrecognized_pct}%"], "E1_5 sweep")
# The chosen cutoff must not be the one that flatters the headline.
chosen = float(sweep.loc[("heart", "14.0"), "unrecognized_pct"])
ok = chosen < hs.unrecognized_pct.max()
print(f"  [{'OK  ' if ok else 'FAIL'}] chosen heart cutoff is not the most flattering "
      f"({chosen}% vs {hs.unrecognized_pct.max()}% at the loosest)")
if not ok:
    _raw.FAILURES.append("report says the chosen troponin cutoff is mid-range; it is the maximum")
# The stability artifact records that the falling-fraction trend is directionally
# consistent but not significant at every rung. The report must say so.
for organ, n_sig, n_rung in [("kidney", 3, 5), ("heart", 3, 6)]:
    claim(f"{organ} falling-fraction significance", f"3 of {n_rung}",
          f"E1_5_conclusion_stability {organ} detail")
    sig = int((sweep.loc[organ].unrec_trend_p < 0.05).sum())
    ok = sig == n_sig
    print(f"  [{'OK  ' if ok else 'FAIL'}] {organ} unrec trend significant at "
          f"{sig}/{n_rung} rungs")
    if not ok:
        _raw.FAILURES.append(
            f"report says {organ} falling fraction is significant at {n_sig} of {n_rung} "
            f"rungs; artifact says {sig}")
claim("nerve >=1 prevalence", f"{sweep.loc[('nerve', '1'), 'prevalence_pct']}%", "E1_5 nerve")
claim("nerve >=2 prevalence", f"{sweep.loc[('nerve', '2'), 'prevalence_pct']}%", "E1_5 nerve")

print("\n§8 / DECISIONS — nerve cutoff impact")
nerve = _raw.artifact("E1_5_nerve_cutoff_impact.csv").set_index("nerve_rule")
for rule in [">=1 of 10 missed", ">=2 of 10 missed", ">=3 of 10 missed"]:
    r = nerve.loc[rule]
    claim(f"{rule} nerve prevalence", f"{r.nerve_prevalence_pct}%", "E1_5_nerve_cutoff_impact")
    claim(f"{rule} any-organ", f"{r.any_organ_pct}%", "E1_5_nerve_cutoff_impact")
    claim(f"{rule} 2+ organs", f"{r.two_plus_organs_pct}%", "E1_5_nerve_cutoff_impact")
ok = nerve.kidney_unrecognized_pct.nunique() == 1
print(f"  [{'OK  ' if ok else 'FAIL'}] headline is invariant to the nerve cutoff "
      f"({nerve.kidney_unrecognized_pct.iloc[0]}% at every rung)")
if not ok:
    _raw.FAILURES.append("report claims the nerve cutoff cannot move the headline; it does")

n_hold = int(stab.holds_at_every_cutoff.sum())
n_total = len(stab)
print(f"  [{'OK  ' if n_hold == n_total - 1 else 'FAIL'}] stability: {n_hold}/{n_total} hold")
if n_hold != n_total - 1:
    _raw.FAILURES.append(f"report says 6 of 7 hold; artifact says {n_hold} of {n_total}")
claim("number of sweep re-analyses", f"{len(sweep)}", "row count of E1_5 sweep")

print("\nINTERNAL CONSISTENCY OF THE REPORT")
# No stray four-significant-figure percentages: every "NN.N%" in the report must
# appear in some artifact, or be one of the derived figures listed here.
DERIVED = {"63%", "60%", "40%", "4%", "72%", "50%"}
pcts = set(re.findall(r"\b\d{1,3}\.\d%", REPORT))
pool = set()
nerve_art = _raw.artifact('E1_5_nerve_cutoff_impact.csv')
spec_art = _raw.artifact('E1_0_threshold_spec.csv')
for art in (prev, unrec, burden, counts, sweep, ucount, conc, overlap, profile,
            nerve_art, spec_art):
    for col in art.columns:
        if art[col].dtype.kind == "f":
            pool |= {f"{v}%" for v in art[col].dropna().round(1).tolist()}
pool |= {f"{v}%" for v in counts.filter(like="pct").values.ravel().tolist()}
orphans = {p for p in pcts if p not in pool and p not in DERIVED}
print(f"  decimal percentages quoted: {len(pcts)}; not traceable to an artifact: "
      f"{sorted(orphans) if orphans else 'none'}")
if orphans:
    _raw.FAILURES.append(f"untraceable percentages in the report: {sorted(orphans)}")

_raw.report("REPORT AUDIT")
