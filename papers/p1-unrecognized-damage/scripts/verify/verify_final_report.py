"""Audit the numbers quoted in the final overnight report against the artifacts."""
from __future__ import annotations
import re
import _raw

REPORT = (_raw.REPO / "reports" / "2026-08-25-final-report.md").read_text()
BARE = " ".join(REPORT.replace("*", "").replace("`", "").split())
LOG = (_raw.REPO / "papers/p1-unrecognized-damage/RESULTS_LOG.md").read_text()
print("=" * 78); print("AUDIT — final report"); print("=" * 78)


def claim(label, text, source):
    ok = any(x in BARE for x in {text, text.replace("-", "−")})
    print(f"  [{'OK  ' if ok else 'MISS'}] {label:<50} '{text}'  <- {source}")
    if not ok:
        _raw.FAILURES.append(f"{label}: '{text}' not in final report ({source})")


confirm = _raw.artifact("E3_3_aim1_confirmatory.csv")
def cell(c, o, s="Overall"):
    return confirm[(confirm.claim == c) & (confirm.organ == o)].set_index("stratum").loc[s]
claim("any prevalence", f"{cell('prevalence','any').pct}% ({int(cell('prevalence','any').k)} / {int(cell('prevalence','any').n):,})", "E3_3_aim1_confirmatory")
claim("healthy any", f"{cell('prevalence','any','Healthy').pct}%", "E3_3"); claim("insulin any", f"{cell('prevalence','any','Insulin').pct}%", "E3_3")
claim("either fraction", f"{cell('unrecognized_fraction','either').pct}% ({int(cell('unrecognized_fraction','either').k)} / {int(cell('unrecognized_fraction','either').n)})", "E3_3")
claim("kidney fraction", f"kidney {cell('unrecognized_fraction','kidney').pct}%", "E3_3"); claim("heart fraction", f"heart {cell('unrecognized_fraction','heart').pct}%", "E3_3")
claim("either burden", f"{cell('population_burden','either').pct}% overall", "E3_3"); claim("insulin burden", f"{cell('population_burden','either','Insulin').pct}%", "E3_3")
claim("healthy burden", f"{cell('population_burden','either','Healthy').pct}%", "E3_3")
claim("burden z", f"z = {cell('population_burden','either').trend_z:.2f}", "E3_3"); claim("fraction z", f"z = {cell('unrecognized_fraction','either').trend_z:.2f}", "E3_3")
claim("fraction H->I", f"{cell('unrecognized_fraction','either','Healthy').pct:.0f}% (Healthy) → {cell('unrecognized_fraction','either','Insulin').pct:.0f}% (Insulin)", "E3_3")
claim("kidney fraction H->I", f"kidney {cell('unrecognized_fraction','kidney','Healthy').pct:.0f}% → {cell('unrecognized_fraction','kidney','Insulin').pct:.0f}%", "E3_3")
a15 = _raw.artifact("E3_3_aim1_recognition_models.csv").set_index(["organ", "model", "term"])
w = a15.loc[("kidney", "C: B + marker magnitude", "log_acr")]
claim("log ACR OR", f"OR {w.odds_ratio:.2f} ({w.ci_lo:.2f}–{w.ci_hi:.2f})", "E3_3_aim1_recognition_models")
t1 = _raw.artifact("E3_3_track_undiagnosed.csv").set_index(["definition", "outcome"]); k = t1.loc[("undiagnosed_range", "abn_kidney")]
claim("T1 OR", f"OR {k.estimate:.2f} (Wald {k.ci_lo:.2f}–{k.ci_hi:.2f}; bootstrap {k.boot_ci_lo:.2f}–{k.boot_ci_hi:.2f})", "E3_3_track_undiagnosed")
claim("T1 abstract", f"OR {k.estimate:.2f}, bootstrap 95% CI {k.boot_ci_lo:.2f}–{k.boot_ci_hi:.2f}", "E3_3_track_undiagnosed")
claim("T1 exposed n", f"{int(k.n_exposed)} participants with no diabetes label", "E3_3_track_undiagnosed")
cg = t1.loc[("undiagnosed_range_cgm", "abn_kidney")]; claim("CGM OR", f"OR {cg.estimate:.2f}", "E3_3_track_undiagnosed")
claim("double-unrecognized", "16 of the 19", "E3.3 log"); _raw.check("log double-unrecognized", "double-unrecognized 16 of 19" in LOG, True)
aim2 = _raw.artifact("E3_3_aim2_confirmatory.csv").set_index(["exposure", "outcome"]); n = aim2.loc[("cesd_total", "abn_nerve")]
claim("aim2 OR", f"OR {n.estimate:.2f} ({n.ci_lo:.2f}–{n.ci_hi:.2f}), q = {n.q:.2f}", "E3_3_aim2_confirmatory")
claim("aim2 abstract", f"OR {n.estimate:.2f} per SD, 95% CI {n.ci_lo:.2f}–{n.ci_hi:.2f}, q = {n.q:.2f}", "E3_3_aim2_confirmatory")
p2 = _raw.artifact("E2C_1_sweep.csv"); p2 = p2[p2.adjustment == "damage"].set_index(["exposure", "outcome"]); e = p2.loc[("cesd_total", "abn_nerve")]
claim("phase-2 nerve", f"OR {e.estimate:.2f}, q = {e.q:.3f}", "E2C_1_sweep")
imp = _raw.artifact("E3_3_aim2_missing_sensitivity.csv").set_index(["exposure", "outcome"])
claim("imputation q", f"q = {imp.loc[('cesd_total','abn_nerve'),'q']:.3f}", "E3_3_aim2_missing_sensitivity")
ladder = _raw.artifact("E3_3_aim2_ladder.csv").set_index(["sample", "step", "outcome"])
P2 = "Phase-2 sample (each step's own complete cases)"; FX = [s for s in ladder.index.get_level_values("sample").unique() if s.startswith("fixed")][0]
import numpy as np
tot = np.log(ladder.loc[(P2, "+ age + severity + site", "abn_nerve"), "estimate"]) - np.log(ladder.loc[(FX, "full spec (+ BMI + HbA1c)", "abn_nerve"), "estimate"])
smp = np.log(ladder.loc[(P2, "+ age + severity + site", "abn_nerve"), "estimate"]) - np.log(ladder.loc[(FX, "+ age + severity + site", "abn_nerve"), "estimate"])
claim("sample share", f"{100 * smp / tot:.0f}% of the attenuation", "E3_3_aim2_ladder"); claim("lost 68", "68 participants", "E3_3_aim2_ladder")
f1 = _raw.artifact("E2F_1_models.csv"); f1 = f1[(f1.adjustment == "full") & (f1.exposure == "healthcare_access_barriers") & (f1.outcome == "unrec_heart")].iloc[0]
claim("access OR", f"OR {f1.estimate:.2f} ({f1.ci_lo:.2f}–{f1.ci_hi:.2f})", "E2F_1_models")
t2 = _raw.artifact("E3_3_track_ecg.csv").set_index(["exposure", "outcome"]); claim("QRS q", f"q = {t2.loc[('qrsd_ms','log_troponin'),'q']:.0e}".replace("e-", "×10⁻").replace("5×10⁻24", "5×10⁻²⁴"), "E3_3_track_ecg")
rank = _raw.artifact("E3_1_ranking.csv"); _raw.check("E3.1 all-four = 32", int((rank.criteria_met == 4).sum()), 32)
for h in ["c9f2acb6"]:
    _raw.check(f"hash {h} in log", h in LOG, True)
_raw.check("every status row done", all(m.group(1) == "done" for m in re.finditer(r"^\| E[0-9A-Z.]+ \| (\w[\w ]*?) \|", LOG, re.M)), True)
_raw.check("final report says Aim 2 criterion not met", "criterion was not met" in BARE or "did not meet its pre-specified" in BARE, True)
_raw.check("final report says nothing committed", "committed overnight" in BARE, True)
_raw.report("FINAL REPORT AUDIT")
