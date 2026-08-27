"""E1.0 — Abnormality definitions and the Phase-1 analysis dataset.

Not in the original experiment list (PLAN.md, Part II). Added because E1.1-E1.5 all depend on
one question the Phase-0 report left open ("agree the abnormality cutoffs"),
and an undocumented cutoff is exactly the kind of thing a reviewer asks about.
Split out so the choice is a logged decision with a date, not an assumption
buried in five scripts.

These are Phase-1 EXPLORATORY defaults. E1.5 sweeps them; Phase 3 freezes one
set into PRESPEC.md.
"""

from __future__ import annotations

import pandas as pd

from aireadi import results, thresholds

import _phase1

_phase1.banner("E1.0", "Abnormality definitions + analysis dataset")

df = _phase1.load(rebuild=_phase1.rebuild_requested())

spec = thresholds.describe()
spec["sweep_in_E1_5"] = [
    ", ".join(f"{v:g}" for v in thresholds.SWEEP["acr_mg_g"]),
    ", ".join(str(v) for v in thresholds.SWEEP["troponin_ng_l"]),
    ", ".join(f"{v:g}" for v in thresholds.SWEEP["monofilament_missed"]),
]

# How many participants each definition can actually classify. The paper's
# denominators are set here, so they get reported here.
evaluable = []
for organ in thresholds.ORGANS:
    abn = df[f"abn_{organ}"]
    row = {
        "organ": organ,
        "n_measured": int(abn.notna().sum()),
        "pct_of_cohort": round(100 * abn.notna().sum() / len(df), 1),
        "n_abnormal": int((abn == 1).sum()),
    }
    if organ in thresholds.UNRECOGNIZED_ORGANS:
        sr = df[f"sr_{organ}"]
        # Two different refusal counts, and only one of them sets the
        # denominator. Cohort-wide missingness is context; what the
        # unrecognized fraction actually loses is refusals AMONG THE ABNORMAL.
        row["n_sr_missing_cohort"] = int(sr.isna().sum())
        row["n_sr_refused_among_abnormal"] = int((abn.eq(1) & sr.isna()).sum())
        row["n_abnormal_with_comparator"] = int((abn.eq(1) & sr.notna()).sum())
    else:
        row["n_sr_missing_cohort"] = pd.NA
        row["n_sr_refused_among_abnormal"] = pd.NA
        row["n_abnormal_with_comparator"] = pd.NA
    evaluable.append(row)

table = spec.join(pd.DataFrame(evaluable).set_index("organ"))

print("\nCutoffs in force for Phase 1:\n")
print(table.to_string())
print(f"\nCohort: {len(df):,} rows; "
      f"complete on all three markers: "
      f"{int(df[[f'abn_{o}' for o in thresholds.ORGANS]].notna().all(axis=1).sum()):,}")
print("\nUnrecognized-fraction denominator (decided here, applied throughout):")
print("  numerator   = abnormal AND self-report = no")
print("  denominator = abnormal AND self-report answered (refusals excluded)")
print("  the abnormal-including-refusals denominator is reported alongside as")
print("  a sensitivity figure, so the two can never be confused again.")

# Composed from the table above, never typed by hand: the log must quote
# executed output.
parts = [
    f"{o} {table.loc[o, 'definition']} -> {table.loc[o, 'n_abnormal']:,} abnormal "
    f"of {table.loc[o, 'n_measured']:,} measured"
    for o in thresholds.ORGANS
]
denoms = "; ".join(
    f"{o} {table.loc[o, 'n_abnormal_with_comparator']:,} of "
    f"{table.loc[o, 'n_abnormal']:,} abnormal "
    f"({table.loc[o, 'n_sr_refused_among_abnormal']} refused the item)"
    for o in thresholds.UNRECOGNIZED_ORGANS
)

results.save(
    "E1.0", table, paper="p1",
    method=("Fixed the Phase-1 abnormality cutoffs and the unrecognized-fraction "
            "denominator before running any core-sweep experiment; cutoffs are "
            "exploratory and swept in E1.5."),
    result=(f"{'; '.join(parts)}. Unrecognized denominator = abnormal with an "
            f"answered self-report item: {denoms}."),
    decision="keep", name="threshold_spec",
)
