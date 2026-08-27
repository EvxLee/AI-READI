"""E2C.3 — PAID-5 diabetes distress vs measured organ damage.

Same recipe as E2C.1, different questionnaire. PAID-5 asks about distress
*specific to living with diabetes*; CES-D-10 asks about general depressive
symptoms. In the exploratory phase PAID-5 outperformed CES-D against glycaemic
outcomes, and the question here is whether that carries over to organ damage,
which is a different outcome entirely.

Coverage is reported by severity group before anything is fitted, because the
obvious assumption about this instrument is wrong: a diabetes-distress
questionnaire sounds like it would only be administered to participants who have
diabetes, and it was in fact administered cohort-wide — 97% of the Healthy group
answered it. So PAID-5 does span the severity spectrum and no scope caveat is
needed. The coverage table stays in the artifact as the evidence for that,
rather than the claim resting on anyone's recollection.

E2C.1 found the depression signal on nerve, so the head-to-head that matters is
on nerve: does diabetes-specific distress track insensate feet as well as, or
better than, general depressive symptoms? Both questionnaires are fitted on the
identical sample for that comparison, because comparing a coefficient from
n=2,265 against one from n=2,229 is not a comparison.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations, results

import _phase2

_phase2.banner("E2C.3", "PAID-5 diabetes distress vs measured organ damage")

df = _phase2.load()

EXPOSURES = {
    "paid_total": "PAID-5 total (0-20)",
    "paid_positive": "PAID-5 distress-positive (>= 8)",
}

coverage = (df.assign(has_paid=df["paid_total"].notna())
              .groupby("study_group_label", observed=True)
              .agg(n=("has_paid", "size"), with_paid=("has_paid", "sum"),
                   mean_paid=("paid_total", "mean")))
coverage["pct_covered"] = (100 * coverage["with_paid"] / coverage["n"]).round(1)
coverage["mean_paid"] = coverage["mean_paid"].round(2)
_phase2.print_table(coverage, title="PAID-5 coverage by severity group")

table = associations.sweep(
    df, EXPOSURES,
    adjustments=["unadjusted", "damage", "damage+hba1c"],
    fdr_within="damage",
)
_phase2.print_table(table, title="PAID-5 vs damage — full sweep")

survivors = _phase2.headline(table)
raw_hits = _phase2.headline(table, use_q=False)
n_adjusted = int((table.index.get_level_values("adjustment") == "damage").sum())

print(f"\nAdjusted family: {n_adjusted} models, {len(raw_hits)} with p < 0.05, "
      f"{len(survivors)} surviving FDR")

# ── Head-to-head on nerve, same sample for both questionnaires ──────────
same_sample = df.dropna(subset=["paid_total", "cesd_total", "abn_nerve",
                                "age", "study_group_label", "clinical_site"])
head_rows = []
for exposure, label in [("cesd_total", "CES-D-10 total"),
                        ("paid_total", "PAID-5 total"),
                        ("paid_positive", "PAID-5 >= 8"),
                        ("cesd_positive", "CES-D-10 >= 10")]:
    for outcome in ("abn_nerve", "monofilament_missed"):
        row = associations.fit(
            same_sample, outcome, exposure, associations.ADJUSTMENTS["damage"],
            family="gaussian" if outcome == "monofilament_missed" else "binomial")
        head_rows.append({"questionnaire": label, "outcome": outcome,
                          **{k: row[k] for k in ("n", "estimate", "ci_lo", "ci_hi", "p")}})

# Both in one model: if they carry the same signal, neither survives the other.
for outcome in ("abn_nerve", "monofilament_missed"):
    fam = "gaussian" if outcome == "monofilament_missed" else "binomial"
    for exposure, other in [("cesd_total", "paid_total"), ("paid_total", "cesd_total")]:
        row = associations.fit(
            same_sample, outcome, exposure,
            associations.ADJUSTMENTS["damage"] + [other], family=fam)
        head_rows.append({"questionnaire": f"{exposure} | mutually adjusted",
                          "outcome": outcome,
                          **{k: row[k] for k in ("n", "estimate", "ci_lo", "ci_hi", "p")}})

head = pd.DataFrame(head_rows).set_index(["questionnaire", "outcome"])
_phase2.print_table(head, title=f"Nerve head-to-head on the identical sample (n={len(same_sample):,})")

results.save(
    "E2C.3", table, paper="p1",
    method=("PAID-5, continuous and at the >= 8 distress cutoff, against each damage "
            "outcome: unadjusted, adjusted for age + severity + site, and + HbA1c. "
            "Same recipe as E2C.1; FDR within the adjusted family."),
    result=(f"Of {n_adjusted} adjusted models, {len(raw_hits)} reach p < 0.05 and "
            f"{len(survivors)} survive FDR. Surviving: "
            f"{_phase2.summarise(survivors) if len(survivors) else 'none'}. PAID-5 was "
            f"administered cohort-wide, not only to the diabetic groups — coverage "
            + ", ".join(f"{g} {r.pct_covered}%" for g, r in coverage.iterrows())
            + " — so it spans the severity spectrum and needs no scope caveat."),
    decision="keep", name="sweep",
)
results.save(
    "E2C.3", coverage, paper="p1",
    method="PAID-5 coverage and mean score by severity group, bounding what the exposure can claim.",
    result=("; ".join(f"{g}: {int(r.with_paid)}/{int(r.n)} ({r.pct_covered}%), mean {r.mean_paid}"
                      for g, r in coverage.iterrows())),
    decision="keep", name="coverage", primary=False,
)
results.save(
    "E2C.3", head, paper="p1",
    method=(f"CES-D-10 vs PAID-5 head-to-head against nerve damage on the identical "
            f"complete-case sample (n={len(same_sample):,}), each alone and then mutually "
            f"adjusted, so the two questionnaires are compared rather than two samples."),
    result=("; ".join(f"{q}/{o}: {r.estimate} ({r.ci_lo}-{r.ci_hi}), p={r.p:.3g}"
                      for (q, o), r in head.iterrows())),
    decision="keep", name="nerve_head_to_head", primary=False,
)
