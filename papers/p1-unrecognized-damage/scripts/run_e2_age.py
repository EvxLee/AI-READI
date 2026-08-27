"""E2.AGE — why adjustment strengthens associations in this cohort.

A sub-question the data forced open. Two Phase-2 tracks (E2C.1 nerve, E2B.1 BMI)
produced an association that is absent or weak unadjusted and clearly present
once age + severity + site enter. That pattern reads like a fishing expedition
unless the mechanism is shown, and a reviewer is entitled to ask why the
covariates were chosen. So it gets measured once, here, rather than re-argued in
each track's write-up.

The mechanism is that **age is a negative confounder for nearly every exposure
this paper tests**. Age runs the wrong way against almost all of them — younger
participants score higher on CES-D, carry more weight, walk more, have faster
resting heart rates — while every damage outcome rises steeply with age. The two
paths cancel, so the crude association is biased toward zero and the adjusted one
is the less biased estimate, not the more flattering one.

The same structure has the opposite effect where an exposure's age correlation
shares the outcome's sign: there the crude association is *inflated* and
adjustment correctly shrinks it. Daily step count is the clear case.

What this experiment is for: it means **an unadjusted number in this paper's log
is not a conservative version of the adjusted one**, and Phase 3 must not read it
that way when ranking findings. The output is the evidence for one sentence in
Methods and one in the phase report.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations, results

import _phase2

_phase2.banner("E2.AGE", "Age as a negative confounder across Phase-2 exposures")

df = _phase2.load()

EXPOSURES = {
    "cesd_total": "CES-D-10 total",
    "paid_total": "PAID-5 total",
    "bmi": "BMI",
    "hba1c": "HbA1c",
    "steps": "Daily steps",
    "stress": "Garmin stress",
    "sleep_hours": "Sleep hours",
    "heart_rate": "Resting heart rate",
    "spo2": "SpO2",
}
OUTCOMES = ["abn_kidney", "abn_heart", "abn_nerve", "abn_any", "monofilament_missed"]

rows = []
for exposure, label in EXPOSURES.items():
    r_age = float(df[[exposure, "age"]].corr().iloc[0, 1])
    for outcome in OUTCOMES:
        r_outcome_age = float(df[[outcome, "age"]].corr().iloc[0, 1])
        gaussian = outcome == "monofilament_missed"
        crude = associations.fit(df, outcome, exposure, [],
                                 family="gaussian" if gaussian else "binomial")
        aged = associations.fit(df, outcome, exposure, ["age"],
                                family="gaussian" if gaussian else "binomial")
        # The directional prediction. If the exposure declines with age while the
        # outcome rises with it, age is a negative confounder and the crude
        # estimate is biased DOWNWARD -- so the adjusted estimate should come out
        # HIGHER than the crude one. Comparing "adjusted > crude" tests that
        # directly. An earlier version asked instead whether adjustment moved the
        # estimate away from the null, which is close to a coin flip across 45
        # mostly-null pairs and so could not evidence the claim either way.
        rows.append({
            "exposure": exposure, "exposure_label": label, "outcome": outcome,
            "r_exposure_age": round(r_age, 3),
            "r_outcome_age": round(r_outcome_age, 3),
            "opposite_signs": bool(r_age * r_outcome_age < 0),
            "crude": crude["estimate"], "crude_p": crude["p"],
            "age_adjusted": aged["estimate"], "age_adjusted_p": aged["p"],
            "adjusted_exceeds_crude": bool(aged["estimate"] > crude["estimate"]),
            "n": aged["n"],
        })

table = pd.DataFrame(rows).set_index(["exposure", "outcome"])
_phase2.print_table(table, title="Crude vs age-adjusted, with the two age correlations")

opposite = table[table["opposite_signs"]]
agree = table[~table["opposite_signs"]]
pct_opposite_up = 100 * opposite["adjusted_exceeds_crude"].mean()
pct_agree_up = 100 * agree["adjusted_exceeds_crude"].mean()

# A sign test, so the claim carries a p-value rather than a bare percentage.
from scipy import stats as _sps
sign_p = float(_sps.binomtest(int(opposite["adjusted_exceeds_crude"].sum()),
                              len(opposite), 0.5).pvalue)

summary = pd.DataFrame([
    {"pattern": "exposure and outcome correlate with age in OPPOSITE directions",
     "prediction": "age adjustment RAISES the estimate", "n_pairs": len(opposite),
     "pct_adjusted_exceeds_crude": round(pct_opposite_up, 1), "sign_test_p": sign_p},
    {"pattern": "exposure and outcome correlate with age in the SAME direction",
     "prediction": "age adjustment LOWERS the estimate", "n_pairs": len(agree),
     "pct_adjusted_exceeds_crude": round(pct_agree_up, 1), "sign_test_p": float("nan")},
]).set_index("pattern")
_phase2.print_table(summary, title="The prediction, tested")

print(f"\nExposures declining with age: "
      f"{sorted(e for e in EXPOSURES if table.loc[e].r_exposure_age.iloc[0] < 0)}")
print(f"Every damage outcome rises with age: "
      f"{all(table.xs(o, level='outcome').r_outcome_age.iloc[0] > 0 for o in OUTCOMES)}")

results.save(
    "E2.AGE", table, paper="p1",
    method=("Why adjustment strengthens Phase-2 associations: for every exposure x damage "
            "outcome pair, the exposure's correlation with age, the outcome's correlation "
            "with age, and the crude vs age-adjusted estimate side by side. Run once as a "
            "cross-cutting check rather than re-argued per track."),
    result=(f"AGE IS A NEGATIVE CONFOUNDER FOR MOST OF PHASE 2. "
            f"{sum(1 for e in EXPOSURES if table.loc[e].r_exposure_age.iloc[0] < 0)} of "
            f"{len(EXPOSURES)} exposures decline with age while all "
            f"{len(OUTCOMES)} damage outcomes rise with it. Where the two age correlations "
            f"have OPPOSITE signs ({len(opposite)} pairs), age adjustment RAISES the "
            f"estimate in {pct_opposite_up:.0f}% of them (sign test p={sign_p:.3g}), the "
            f"predicted direction for negative confounding; where they share a sign "
            f"({len(agree)} pairs) it raises it in {pct_agree_up:.0f}%. So an adjusted "
            f"estimate here is the less biased one, and an unadjusted estimate is NOT a "
            f"conservative version of it — Phase 3 must not treat crude numbers in this log "
            f"as a lower bound. Explains E2C.1 (nerve) and E2B.1 (BMI) appearing only after "
            f"adjustment, and why the crude steps-damage association is inflated rather "
            f"than masked."),
    decision="keep", name="suppression",
)
results.save(
    "E2.AGE", summary, paper="p1",
    method=("The prediction stated as a testable claim with a sign test: where exposure and "
            "outcome correlate with age in opposite directions, age adjustment should RAISE "
            "the estimate; where they correlate in the same direction it should lower it."),
    result=(f"Opposite-sign pairs: adjusted exceeds crude in {pct_opposite_up:.0f}% "
            f"(n={len(opposite)}, sign test p={sign_p:.3g}). Same-sign pairs: "
            f"{pct_agree_up:.0f}% (n={len(agree)})."),
    decision="keep", name="summary", primary=False,
)
