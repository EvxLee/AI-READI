"""E2D.1 — Garmin wearable metrics vs measured organ damage. One clean pass.

Scope is fixed in advance and is not to be extended: the exploratory phase found
wearables weak against glycaemic outcomes, damage is a different outcome so one
pass is justified, and they are explicitly not part of this paper's identity
(PROJECT_CONTEXT, decision 3). Whatever this produces gets one log entry. If it
is interesting it becomes at most a sentence; it does not become a track.

The device's own error codes are the trap here — 0 for heart rate and SpO2, -2
for stress and respiratory rate, written instead of nulls — and averaging them in
drags every summary toward zero. This runner found that scrubbing the sentinel
value is not sufficient: AI-READI computed the manifest averages *with* the error
codes included, so a contaminated mean lands between the sentinel and the truth
rather than on it. Twelve participants carried a resting heart rate under 30 bpm
(lowest 0.03) and 113 carried a negative stress score on a 0-100 scale — all of
which pass an `!= sentinel` test and none of which are measurements.
`wearables.clean_garmin_manifest` now applies plausibility bounds as well, and
the sweep is run both ways so the effect of that fix is visible rather than
asserted.

Respiratory rate is deliberately absent. It reads 6-9 against an expected 12-20
(CAVEATS): a device quirk usable for relative comparison but not as an absolute
value, and there is no relative comparison to make here.

Interpretation caution for the write-up: step count and resting heart rate are as
plausibly *consequences* of organ damage as causes of it, in a cross-sectional
snapshot. Any surviving association is a correlate, stated as such.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations, azure_io, constants, results, wearables

import _phase2

_phase2.banner("E2D.1", "Garmin wearable metrics vs measured organ damage")

df = _phase2.load()

EXPOSURES = {
    "steps": "Daily steps",
    "heart_rate": "Resting heart rate (bpm)",
    "stress": "Garmin stress score",
    "sleep_hours": "Sleep (hours/night)",
    "spo2": "SpO2 (%)",
}

# Re-check the cleaning rather than trust it: an error code that survived would
# sit at exactly 0 (heart rate, SpO2) or -2 (stress), and would manufacture an
# association out of device failures.
print("Error-code check (a leak would show as a value at the sentinel):")
for column, sentinel in [("heart_rate", 0), ("spo2", 0), ("stress", -2)]:
    hits = int(df[column].eq(sentinel).sum())
    print(f"  {column:<14} values at {sentinel:>2}: {hits}   "
          f"min {df[column].min():.2f}  {'OK' if hits == 0 else 'LEAK'}")
assert not any(df[c].eq(s).any() for c, s in
               [("heart_rate", 0), ("spo2", 0), ("stress", -2)]), \
    "Garmin error code survived cleaning — see CAVEATS.md"

# Every remaining value must sit inside the instrument's own scale. This is the
# check the sentinel scrub cannot do.
for column, (lo, hi) in [("heart_rate", (30, 120)), ("stress", (0, 100)),
                         ("sleep_hours", (1, 14)), ("spo2", (70, 100)),
                         ("steps", (1, 50000))]:
    bad = int((df[column].notna() & ~df[column].between(lo, hi)).sum())
    assert bad == 0, (f"{column}: {bad} values outside {lo}-{hi} survived cleaning "
                      f"— plausibility bounds not applied?")
print("plausibility bounds hold for every wearable column")

print(f"\nSleep sanity (fraction-of-day x24 applied): median "
      f"{df.sleep_hours.median():.2f} h, range {df.sleep_hours.min():.2f}-"
      f"{df.sleep_hours.max():.2f}")
print("\nCoverage:")
for column, label in EXPOSURES.items():
    print(f"  {label:<26} n={int(df[column].notna().sum()):>5}  "
          f"median {df[column].median():>8.2f}")

table = associations.sweep(
    df, EXPOSURES,
    adjustments=["unadjusted", "damage", "damage+hba1c"],
    fdr_within="damage",
)
_phase2.print_table(table, title="Wearables vs damage — full sweep")

survivors = _phase2.headline(table)
raw_hits = _phase2.headline(table, use_q=False)
n_adjusted = int((table.index.get_level_values("adjustment") == "damage").sum())

print(f"\nAdjusted family: {n_adjusted} models, {len(raw_hits)} with p < 0.05, "
      f"{len(survivors)} surviving FDR")

# Complete-case n varies a lot across these exposures (SpO2 reaches ~1,600 while
# steps reaches ~2,100), so the artifact records it per exposure. Comparing two
# effect sizes fitted on different cohorts is the mistake this prevents.
coverage = pd.DataFrame([
    {"exposure": column, "label": label,
     "n_available": int(df[column].notna().sum()),
     "pct_of_cohort": round(100 * df[column].notna().mean(), 1)}
    for column, label in EXPOSURES.items()]).set_index("exposure")
_phase2.print_table(coverage, title="Per-exposure coverage")

# ── Sensitivity to the plausibility fix ─────────────────────────────────
#
# The same sweep on the sentinel-only cleaning, so the cost of the contaminated
# averages is measured rather than asserted. Any conclusion that appears in one
# and not the other is a conclusion about device failures.
raw_manifest = azure_io.load_table("manifest_activity")
# The bounds report what they removed, so the log line quotes the cleaning rather
# than a number typed alongside it.
dropped_counts = wearables.clean_garmin_manifest(raw_manifest).attrs[
    "garmin_dropped_implausible"]
print(f"\nvalues dropped by the plausibility bounds: {dropped_counts}")

dirty = wearables.clean_garmin_manifest(raw_manifest, apply_plausibility=False)
dirty = dirty.rename(columns={"average_daily_activity": "steps",
                              "average_heartrate_bpm": "heart_rate",
                              "average_stress_level": "stress",
                              "average_sleep_hours": "sleep_hours",
                              "average_oxygen_saturation_pct": "spo2"})
before = df.drop(columns=list(EXPOSURES)).merge(
    dirty[["person_id", *EXPOSURES]], on="person_id", how="left")
before_table = associations.sweep(before, EXPOSURES, adjustments=["damage"],
                                  fdr_within="damage")

compare_rows = []
for exposure in EXPOSURES:
    for outcome in {**associations.BINARY_OUTCOMES, **associations.CONTINUOUS_OUTCOMES}:
        b = before_table.loc[(exposure, outcome, "damage")]
        a = table.loc[(exposure, outcome, "damage")]
        compare_rows.append({
            "exposure": exposure, "outcome": outcome,
            "n_before": int(b.n), "n_after": int(a.n),
            "est_before": b.estimate, "q_before": b.q,
            "est_after": a.estimate, "q_after": a.q,
            "changed_conclusion": bool((b.q < 0.05) != (a.q < 0.05)),
        })
sensitivity = pd.DataFrame(compare_rows).set_index(["exposure", "outcome"])
flipped = sensitivity[sensitivity["changed_conclusion"]]
_phase2.print_table(sensitivity,
                    title="Sensitivity to the plausibility fix (sentinel-only vs bounded)")
print(f"\nConclusions that change once implausible averages are dropped: {len(flipped)}")

results.save(
    "E2D.1", table, paper="p1",
    method=("Garmin steps, resting heart rate, stress, sleep and SpO2 against each damage "
            "outcome: unadjusted, adjusted for age + severity + site, and + HbA1c. Error "
            "codes cleaned (0 for HR/SpO2, -2 for stress) and asserted absent; sleep "
            "converted from fraction-of-day; respiratory rate excluded as a known device "
            "quirk. Effects per 1 SD; FDR within the adjusted family. ONE PASS by standing "
            "decision — wearables are not part of this paper's identity."),
    result=(f"Of {n_adjusted} adjusted models, {len(raw_hits)} reach p < 0.05 and "
            f"{len(survivors)} survive FDR. Surviving: "
            f"{_phase2.summarise(survivors) if len(survivors) else 'none'}. Coverage varies "
            f"widely, so effects are not comparable across exposures without it: "
            + ", ".join(f"{r.label} n={int(r.n_available)}" for _, r in coverage.iterrows())
            + ". Cross-sectional: steps and heart rate are as plausibly consequences of "
              "damage as causes, so any survivor is a correlate only."),
    decision="keep", name="sweep",
)
results.save(
    "E2D.1", coverage, paper="p1",
    method="Per-exposure wearable coverage, bounding cross-exposure comparison.",
    result="; ".join(f"{r.label}: {int(r.n_available)} ({r.pct_of_cohort}%)"
                     for _, r in coverage.iterrows()),
    decision="keep", name="coverage", primary=False,
)
results.save(
    "E2D.1", sensitivity, paper="p1",
    method=("DEFECT FOUND AND FIXED. The same adjusted sweep run on the sentinel-only "
            "cleaning and on the bounded cleaning, to measure what the contaminated "
            "manifest averages were doing. AI-READI computed the Garmin averages with the "
            "device error codes included, so 12 heart rates under 30 bpm (lowest 0.03) and "
            "113 negative stress scores on a 0-100 scale survived the documented "
            "sentinel scrub. `wearables.clean_garmin_manifest` now applies "
            "GARMIN_PLAUSIBLE_RANGES; CAVEATS.md updated."),
    result=(f"Values dropped by the bounds: "
            + ", ".join(f"{k.replace('average_', '').replace('_', ' ')} {v}"
                        for k, v in dropped_counts.items())
            + f". {len(flipped)} of {len(sensitivity)} adjusted conclusions change: "
            + ("; ".join(f"{e}/{o} q {r.q_before:.3g} -> {r.q_after:.3g}"
                         for (e, o), r in flipped.iterrows()) or "none")
            + ". No Phase-1 result is affected — Phase 1 uses no wearable variable, and all "
              "five Phase-1 verifiers still pass after the master table was rebuilt."),
    decision="keep", name="plausibility_sensitivity", primary=False,
)
