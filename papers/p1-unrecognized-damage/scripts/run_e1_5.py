"""E1.5 — Threshold sensitivity: how much of Phase 1 survives a different cutoff.

Every rung of every sweep grid is re-run end to end: prevalence, unrecognized
fraction, and both trend tests. The question is not "do the numbers change" --
they must -- but "does any conclusion flip".

Troponin matters most. Guideline hs-cTnT cutoffs are sex-specific and the
public release removes sex, so the sweep is not a nicety here; it is the
mitigation for a variable we cannot have.
"""

from __future__ import annotations

import pandas as pd

from aireadi import results, stats, thresholds

import _phase1

_phase1.banner("E1.5", "Threshold sensitivity sweep")

base = _phase1.load()
ARG = {"kidney": "acr_mg_g", "heart": "troponin_ng_l", "nerve": "monofilament_missed"}

rows = []
for organ, arg in ARG.items():
    for rung in thresholds.SWEEP[arg]:
        df = thresholds.add_damage_flags(base, **{arg: rung})
        prev = stats.proportion_by_group(df, f"abn_{organ}")
        row = {
            "organ": organ, "cutoff": str(rung),
            "is_primary": rung == thresholds.PRIMARY[arg],
            "n_measured": int(prev.loc["Overall", "n"]),
            "n_abnormal": int(prev.loc["Overall", "k"]),
            "prevalence_pct": float(prev.loc["Overall", "pct"]),
            "prev_ci_lo": float(prev.loc["Overall", "ci_lo"]),
            "prev_ci_hi": float(prev.loc["Overall", "ci_hi"]),
            "prev_trend_z": float(prev.loc["Overall", "trend_z"]),
            "prev_trend_p": float(prev.loc["Overall", "trend_p"]),
        }
        for g in ["Healthy", "Pre-DM", "Oral Med", "Insulin"]:
            row[f"prev_{g}"] = float(prev.loc[g, "pct"])

        if organ in thresholds.UNRECOGNIZED_ORGANS:
            unrec = stats.proportion_by_group(df, f"unrec_{organ}")
            row.update({
                "n_unrec_denominator": int(unrec.loc["Overall", "n"]),
                "n_unrecognized": int(unrec.loc["Overall", "k"]),
                "unrecognized_pct": float(unrec.loc["Overall", "pct"]),
                "unrec_ci_lo": float(unrec.loc["Overall", "ci_lo"]),
                "unrec_ci_hi": float(unrec.loc["Overall", "ci_hi"]),
                "unrec_trend_z": float(unrec.loc["Overall", "trend_z"]),
                "unrec_trend_p": float(unrec.loc["Overall", "trend_p"]),
            })
            for g in ["Healthy", "Pre-DM", "Oral Med", "Insulin"]:
                row[f"unrec_{g}"] = float(unrec.loc[g, "pct"])
        rows.append(row)

sweep = pd.DataFrame(rows).set_index(["organ", "cutoff"])

pd.set_option("display.width", 240)
print("\nPrevalence across cutoffs:")
print(sweep[["is_primary", "n_abnormal", "prevalence_pct", "prev_ci_lo", "prev_ci_hi",
             "prev_trend_z", "prev_Healthy", "prev_Insulin"]].to_string())
print("\nUnrecognized fraction across cutoffs:")
u = sweep[sweep.unrecognized_pct.notna()]
print(u[["is_primary", "n_unrecognized", "n_unrec_denominator", "unrecognized_pct",
         "unrec_ci_lo", "unrec_ci_hi", "unrec_trend_z",
         "unrec_Healthy", "unrec_Insulin"]].to_string())

# ── Do any conclusions flip? ────────────────────────────────────────────
print("\nCONCLUSION STABILITY")
checks = []


def record(name: str, ok: bool, detail: str) -> None:
    checks.append({"claim": name, "holds_at_every_cutoff": ok, "detail": detail})
    print(f"  [{'HOLDS ' if ok else 'FLIPS '}] {name}: {detail}")


for organ in ARG:
    s = sweep.loc[organ]
    ok = bool((s.prev_trend_z > 0).all() and (s.prev_trend_p < 0.05).all())
    record(f"{organ} prevalence rises with severity", ok,
           f"trend z {s.prev_trend_z.min():.2f} to {s.prev_trend_z.max():.2f}, "
           f"max p {s.prev_trend_p.max():.1e}")

for organ in thresholds.UNRECOGNIZED_ORGANS:
    s = sweep.loc[organ]
    record(f"{organ} majority of abnormal results are unrecognized", bool((s.unrecognized_pct > 50).all()),
           f"range {s.unrecognized_pct.min():.1f}% to {s.unrecognized_pct.max():.1f}%")
    record(f"{organ} unrecognized FRACTION falls with severity", bool((s.unrec_trend_z < 0).all()),
           f"trend z {s.unrec_trend_z.min():.2f} to {s.unrec_trend_z.max():.2f}; "
           f"significant at {int((s.unrec_trend_p < 0.05).sum())}/{len(s)} cutoffs")

stability = pd.DataFrame(checks).set_index("claim")

# ── What the nerve cutoff actually costs ────────────────────────────────
# Nerve is the one cutoff picked on judgement rather than a guideline, so the
# question "how much does that judgement matter" needs a real answer. It moves
# nerve prevalence and the multi-organ figures; it cannot touch the unrecognized
# headline, because nerve has no self-report comparator. The last column proves
# that rather than asserting it.
nerve_rows = []
for missed in thresholds.SWEEP["monofilament_missed"]:
    df = thresholds.add_damage_flags(base, monofilament_missed=missed)
    any_flag = df["n_organs_abnormal"].gt(0).astype(float).mask(
        df["n_organs_abnormal"].isna())
    two_flag = df["n_organs_abnormal"].ge(2).astype(float).mask(
        df["n_organs_abnormal"].isna())
    either = stats.proportion_by_group(df, "unrec_kidney", trend=False)
    nerve_rows.append({
        "nerve_rule": f">={missed} of 10 missed",
        "is_primary": missed == thresholds.PRIMARY["monofilament_missed"],
        "nerve_prevalence_pct": float(
            stats.proportion_by_group(df, "abn_nerve", trend=False).loc["Overall", "pct"]),
        "any_organ_pct": float(
            stats.proportion_by_group(df.assign(_x=any_flag), "_x", trend=False).loc["Overall", "pct"]),
        "two_plus_organs_pct": float(
            stats.proportion_by_group(df.assign(_x=two_flag), "_x", trend=False).loc["Overall", "pct"]),
        "kidney_unrecognized_pct": float(either.loc["Overall", "pct"]),
    })
nerve_impact = pd.DataFrame(nerve_rows).set_index("nerve_rule")
print("\nWhat the nerve cutoff moves (and what it cannot move):")
print(nerve_impact.to_string())
assert nerve_impact.kidney_unrecognized_pct.nunique() == 1, \
    "nerve cutoff changed the kidney unrecognized fraction — that must be impossible"

results.save(
    "E1.5", sweep, paper="p1",
    method=("Re-ran prevalence and the unrecognized fraction at every rung of each "
            "organ's cutoff grid (kidney ACR 20-300 mg/g; heart detectable-22 ng/L; "
            "nerve 1-5 insensate sites), including both trend tests."),
    result=(f"Prevalence spans "
            + "; ".join(f"{o} {sweep.loc[o, 'prevalence_pct'].min():.1f}-"
                        f"{sweep.loc[o, 'prevalence_pct'].max():.1f}%" for o in ARG)
            + f". Unrecognized fraction spans "
            + "; ".join(f"{o} {sweep.loc[o, 'unrecognized_pct'].min():.1f}-"
                        f"{sweep.loc[o, 'unrecognized_pct'].max():.1f}%"
                        for o in thresholds.UNRECOGNIZED_ORGANS)
            + f". Conclusions holding at every cutoff: "
              f"{int(stability.holds_at_every_cutoff.sum())}/{len(stability)}."),
    decision="keep", name="threshold_sweep",
)
results.save(
    "E1.5", stability, paper="p1",
    method="Checked whether each Phase-1 conclusion survives every cutoff in the sweep.",
    result="; ".join(f"{c} — {'holds' if r.holds_at_every_cutoff else 'FLIPS'}"
                     for c, r in stability.iterrows()),
    decision="keep", name="conclusion_stability", primary=False,
)
results.save(
    "E1.5", nerve_impact, paper="p1",
    method=("Downstream impact of the nerve cutoff — the one abnormality threshold "
            "chosen on judgement rather than a guideline — on nerve prevalence, the "
            "any-organ figure and the multi-organ figure, with the kidney unrecognized "
            "fraction carried alongside to demonstrate it is unaffected."),
    result=("Nerve prevalence moves "
            + " / ".join(f"{v}%" for v in nerve_impact.nerve_prevalence_pct)
            + " across >=1 to >=5 missed sites; any-organ moves "
            + " / ".join(f"{v}%" for v in nerve_impact.any_organ_pct)
            + "; 2+ organs moves "
            + " / ".join(f"{v}%" for v in nerve_impact.two_plus_organs_pct)
            + f". The kidney unrecognized fraction is "
              f"{nerve_impact.kidney_unrecognized_pct.iloc[0]}% at every rung — the nerve "
              f"cutoff cannot touch the headline, because nerve has no comparator."),
    decision="keep", name="nerve_cutoff_impact", primary=False,
)
