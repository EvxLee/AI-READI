"""E2C.2 — CES-D-10 vs *unrecognized* status among participants with damage.

The falling-through-the-cracks question, and H3 in the plan: depression makes
appointments, follow-up and self-advocacy harder, so depressed participants may
be over-represented among the people whose damage nobody has told them about.
One paragraph in the paper at most.

This is a different question from E2C.1 and the log must not blur them. E2C.1
asks whether depression tracks *having* damage. This asks, among the people who
already have it, whether depression tracks *not knowing*. Phase 1 established
that those two move in opposite directions across severity, so the two
experiments can easily produce opposite-signed results without contradicting
each other.

Three covariate rules are inherited and non-negotiable here:

* **Severity**, because the unrecognized fraction falls across it (`E1.2`);
  without it this experiment would rediscover that trend and mistake it for a
  depression effect.
* **Marker magnitude**, because it is the dominant predictor of unrecognized
  status (`E1.4`: OR 0.44 per log ACR). Any variable tested without it is
  probably just tracking how abnormal people are.
* **Age**, because the E1.4 re-reading (17 Aug) found it the only term holding
  across all three heart models.

Nerve cannot appear here at all: v3.0.0 has no neuropathy self-report item
(`E0.GATE`), so "unrecognized" is undefined for it. That is worth stating
plainly, because E2C.1's association landed on nerve — the one organ where the
recognition question cannot be asked.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations, results, thresholds

import _phase2

_phase2.banner("E2C.2", "CES-D-10 vs unrecognized status among those with damage")

df = _phase2.load()

EXPOSURES = {
    "cesd_total": "CES-D-10 total (0-30)",
    "cesd_positive": "CES-D-10 screen-positive (>= 10)",
}
MARKER = {"kidney": "log_acr", "heart": "log_troponin"}

# Outcome: never told, among the abnormal with the item answered. `unrec_*` is
# already NaN for everyone else, so no restriction has to be applied by hand.
OUTCOMES = {f"unrec_{organ}": f"Unrecognized — {organ}"
            for organ in thresholds.UNRECOGNIZED_ORGANS}
OUTCOMES["unrec_either"] = "Unrecognized on either organ"

either = thresholds.either_organ(df)
df["unrec_either"] = df["unrecognized"] = either["unrecognized"]
df.loc[~(either["abnormal"] & either["answered"]), "unrec_either"] = float("nan")

for outcome, label in OUTCOMES.items():
    n = int(df[outcome].notna().sum())
    print(f"{label:<32} n={n:>4} eligible, {int(df[outcome].sum()):>4} never told")

rows = []
for outcome in OUTCOMES:
    organ = outcome.removeprefix("unrec_")
    # "either" carries both markers, since a participant can be unrecognized
    # via whichever organ is abnormal.
    markers = ([MARKER[organ]] if organ in MARKER
               else [MARKER[o] for o in thresholds.UNRECOGNIZED_ORGANS])
    for exposure, exposure_label in EXPOSURES.items():
        for adjustment, covariates in [
            ("unadjusted", []),
            ("severity only", ["C(study_group_label)"]),
            ("recognition", associations.ADJUSTMENTS["recognition"]),
            ("recognition+marker", associations.ADJUSTMENTS["recognition"] + markers),
        ]:
            row = associations.fit(df, outcome, exposure, covariates)
            row.update({"outcome_label": OUTCOMES[outcome],
                        "exposure_label": exposure_label,
                        "adjustment": adjustment})
            rows.append(row)

table = pd.DataFrame(rows)
primary = table["adjustment"] == "recognition+marker"
table.loc[primary, "q"] = associations.fdr(table.loc[primary, "p"])
table = table.set_index(["outcome", "exposure", "adjustment"])[
    ["outcome_label", "exposure_label", "scale", "sd_unit", "n", "estimate",
     "ci_lo", "ci_hi", "p", "q", "note"]]

_phase2.print_table(table, title="CES-D-10 vs unrecognized status — full sweep")

survivors = table[table["q"] < 0.05]
raw_hits = table[primary.to_numpy() & (table["p"] < 0.05).to_numpy()]
n_primary = int(primary.sum())
verdict = ("H3 IS NULL" if not len(survivors)
           else f"H3 HAS {len(survivors)} SURVIVING ASSOCIATION(S)")

print(f"\nPrimary family (recognition + marker magnitude): {n_primary} models, "
      f"{len(raw_hits)} with p < 0.05, {len(survivors)} surviving FDR")

results.save(
    "E2C.2", table, paper="p1",
    method=("CES-D-10 (continuous and >= 10) vs unrecognized status among participants "
            "with an abnormal result, per organ and for either organ. Four nested "
            "adjustments: unadjusted, severity only, age + severity + site + HbA1c + BMI, "
            "and that plus log marker magnitude — the last being the primary family, "
            "because E1.4 showed marker magnitude dominates unrecognized status and age "
            "is the only term holding across all heart models. FDR within that family. "
            "Nerve is absent by definition: no neuropathy self-report item exists "
            "(E0.GATE), so unrecognized status cannot be defined for it."),
    result=(f"{verdict}. Of {n_primary} fully-adjusted models, {len(raw_hits)} reach "
            f"p < 0.05 and {len(survivors)} survive FDR. Surviving: "
            f"{_phase2.summarise(survivors) if len(survivors) else 'none'}. Eligible "
            f"denominators: "
            + "; ".join(f"{o.removeprefix('unrec_')} {int(df[o].notna().sum())} abnormal "
                        f"with the item answered, {int(df[o].sum())} never told"
                        for o in OUTCOMES)
            + ". Note the asymmetry with E2C.1: depression tracks NERVE damage, the one "
              "organ for which unrecognized status cannot be computed at all."),
    decision="keep",
)
