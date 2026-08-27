"""E2A.2 — Damage among participants whose glycaemia disagrees with their label.

The severity groups are treatment categories: diet-controlled, oral medication,
insulin. Treatment is assigned from a clinical history, so a participant can sit
in a group that no longer describes their glucose. This experiment looks at the
two kinds of mismatch:

* **Worse than the label** — diabetes-range glycaemia (HbA1c >= 6.5%) in someone
  carrying no diabetes label at all, i.e. in the Healthy or Pre-DM groups. These
  are participants whose *diabetes* is unrecognized, not only their organ
  damage, and they are the group most directly relevant to Aim 1's screening
  argument.
* **Better than the label** — at-target glycaemia (HbA1c < 7.0%) in the Insulin
  group.

The question in both directions is the same: does measured damage follow the
measurement or the label?

Cutoffs are the standard diagnostic and treatment-target values (ADA: HbA1c
>= 6.5% diagnoses diabetes; < 7.0% is the usual adult target), chosen because
they are external and conventional rather than fitted here. The CGM equivalent
uses mean glucose >= 154 mg/dL, the value Dexcom's own GMI formula maps to an
HbA1c of 7.0%; it is reported as a parallel definition, not averaged with the
HbA1c one.

Small cells are the live risk in this experiment, so every proportion carries a
Wilson interval and the artifact reports each cell's n.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aireadi import associations, azure_io, results, stats, thresholds

import _phase2

_phase2.banner("E2A.2", "Damage among the glycaemia/label discordant")

df = _phase2.load()

CGM = azure_io.repo_root() / "data" / "processed" / "p1" / "cgm_metrics.parquet"
if CGM.exists():
    cgm = pd.read_parquet(CGM)
    cgm["person_id"] = cgm["person_id"].astype(str)
    df = df.merge(cgm[["person_id", "glucose_mean"]], on="person_id", how="left")
else:
    df["glucose_mean"] = np.nan
    print("WARNING: no CGM build found; HbA1c definition only")

HBA1C_DIABETES = 6.5      # ADA diagnostic threshold
HBA1C_TARGET = 7.0        # usual adult treatment target
CGM_MEAN_TARGET = 154.0   # GMI 7.0% == mean glucose 154 mg/dL

NO_LABEL = ["Healthy", "Pre-DM"]

df["undiagnosed_range"] = (
    df["study_group_label"].isin(NO_LABEL) & df["hba1c"].ge(HBA1C_DIABETES)
).astype(float).mask(df["hba1c"].isna())
df["undiagnosed_range_cgm"] = (
    df["study_group_label"].isin(NO_LABEL) & df["glucose_mean"].ge(CGM_MEAN_TARGET)
).astype(float).mask(df["glucose_mean"].isna())
df["insulin_at_target"] = (
    df["study_group_label"].eq("Insulin") & df["hba1c"].lt(HBA1C_TARGET)
).astype(float).mask(df["hba1c"].isna())

# ── Cell counts first, so nothing downstream rests on an invisible n ────
counts = []
for label, mask, universe in [
    (f"No diabetes label, HbA1c >= {HBA1C_DIABETES}%",
     df["undiagnosed_range"].eq(1), df["study_group_label"].isin(NO_LABEL)),
    (f"No diabetes label, CGM mean >= {CGM_MEAN_TARGET:g} mg/dL",
     df["undiagnosed_range_cgm"].eq(1), df["study_group_label"].isin(NO_LABEL)),
    (f"Insulin group, HbA1c < {HBA1C_TARGET}%",
     df["insulin_at_target"].eq(1), df["study_group_label"].eq("Insulin")),
]:
    counts.append({"group": label, "n_discordant": int(mask.sum()),
                   "n_universe": int(universe.sum()),
                   "pct": round(100 * mask.sum() / max(universe.sum(), 1), 1)})
discordance = pd.DataFrame(counts).set_index("group")
_phase2.print_table(discordance, title="How much discordance is there?")

# ── Damage prevalence, discordant vs concordant, within the same universe ──
rows = []
for exposure, universe_mask, universe_label in [
    ("undiagnosed_range", df["study_group_label"].isin(NO_LABEL), "Healthy + Pre-DM"),
    ("undiagnosed_range_cgm", df["study_group_label"].isin(NO_LABEL), "Healthy + Pre-DM"),
    ("insulin_at_target", df["study_group_label"].eq("Insulin"), "Insulin only"),
]:
    universe = df[universe_mask]
    for outcome in [*(f"abn_{o}" for o in thresholds.ORGANS), "abn_any", "abn_multi"]:
        for side, value in [("discordant", 1), ("concordant", 0)]:
            cell = universe.loc[universe[exposure].eq(value), outcome]
            got = stats.proportion(cell)
            rows.append({"definition": exposure, "universe": universe_label,
                         "outcome": outcome, "side": side,
                         "k": got["k"], "n": got["n"], "pct": round(got["pct"], 1),
                         "ci_lo": round(got["ci_lo"], 1), "ci_hi": round(got["ci_hi"], 1)})
prevalence = pd.DataFrame(rows).set_index(["definition", "outcome", "side"])
_phase2.print_table(prevalence, title="Damage prevalence: discordant vs concordant")

# ── Adjusted comparison within the same universe ────────────────────────
#
# Severity is NOT a covariate here: discordance is defined relative to it, so
# adjusting for it would partly adjust away the exposure. Age and site remain.
model_rows = []
for exposure, universe_mask in [
    ("undiagnosed_range", df["study_group_label"].isin(NO_LABEL)),
    ("undiagnosed_range_cgm", df["study_group_label"].isin(NO_LABEL)),
    ("insulin_at_target", df["study_group_label"].eq("Insulin")),
]:
    universe = df[universe_mask]
    for outcome in [*(f"abn_{o}" for o in thresholds.ORGANS), "abn_any", "abn_multi"]:
        covariates = ["age", "C(clinical_site)"]
        row = associations.fit(universe, outcome, exposure, covariates)
        row["definition"] = exposure

        # Bootstrap wherever the discordant cell is small, which is the whole
        # point of this experiment: n = 46 and 55 for the two undiagnosed-range
        # definitions. A Wald interval on 13 events is not to be quoted alone.
        used = universe.dropna(subset=[outcome, exposure, "age", "clinical_site"])
        n_discordant = int(used[exposure].sum())
        row["n_discordant"] = n_discordant
        if 0 < n_discordant < 100:
            lo, hi = associations.bootstrap_ci(used, outcome, exposure, covariates)
            row["boot_ci_lo"], row["boot_ci_hi"] = lo, hi
        else:
            row["boot_ci_lo"] = row["boot_ci_hi"] = float("nan")
        model_rows.append(row)
models = pd.DataFrame(model_rows)
models["q"] = associations.fdr(models["p"])
models = models.set_index(["definition", "outcome"])[
    ["scale", "n", "n_discordant", "estimate", "ci_lo", "ci_hi",
     "boot_ci_lo", "boot_ci_hi", "p", "q", "note"]]
_phase2.print_table(models, title="Adjusted odds of damage, discordant vs concordant (age + site)")

# ── The number this experiment exists to produce ────────────────────────
#
# Participants with no diabetes label, diabetes-range glycaemia, organ damage,
# and no corresponding diagnosis: unrecognized on both counts at once.
either = thresholds.either_organ(df)
double = df["undiagnosed_range"].eq(1) & either["abnormal"] & either["answered"]
double_unrec = double & either["unrecognized"].eq(1)
print(f"\nNo diabetes label + HbA1c >= {HBA1C_DIABETES}%: "
      f"{int(df.undiagnosed_range.sum())} participants; "
      f"{int(double.sum())} of them are abnormal on kidney or heart with both items "
      f"answered, and {int(double_unrec.sum())} of those reported no diagnosis "
      f"({100 * double_unrec.sum() / max(double.sum(), 1):.1f}%)")

survivors = models[models["q"] < 0.05]

results.save(
    "E2A.2", models, paper="p1",
    method=(f"Damage among participants whose glycaemia disagrees with their severity "
            f"label, compared with concordant participants in the same universe: "
            f"no-diabetes-label with HbA1c >= {HBA1C_DIABETES}% (and the parallel CGM "
            f"mean >= {CGM_MEAN_TARGET:g} mg/dL definition) within Healthy + Pre-DM, and "
            f"Insulin-group participants at target (HbA1c < {HBA1C_TARGET}%). Adjusted for "
            f"age + site; severity is excluded because discordance is defined relative to "
            f"it. FDR across the {len(models)} models."),
    result=(f"{len(survivors)} of {len(models)} models survive FDR. Surviving: "
            + ("; ".join(f"{d}/{o} OR={r.estimate} (Wald {r.ci_lo}-{r.ci_hi}, "
                         f"bootstrap {r.boot_ci_lo}-{r.boot_ci_hi}), q={r.q:.3g}"
                         for (d, o), r in survivors.iterrows()) or "none")
            + f". Discordance sizes: "
            + "; ".join(f"{g} {int(r.n_discordant)}/{int(r.n_universe)} ({r.pct}%)"
                        for g, r in discordance.iterrows())
            + f". DOUBLE-UNRECOGNIZED COUNT: of the "
              f"{int(df.undiagnosed_range.sum())} participants with no diabetes label but "
              f"diabetes-range HbA1c, {int(double.sum())} have kidney or heart damage with "
              f"both self-report items answered and {int(double_unrec.sum())} of those "
              f"reported no corresponding diagnosis."),
    decision="keep", name="models",
)
results.save(
    "E2A.2", prevalence, paper="p1",
    method=("Damage prevalence with Wilson intervals for discordant and concordant "
            "participants side by side, within the same universe, per organ."),
    result=("; ".join(
        f"{d}/{o}: discordant {prevalence.loc[(d, o, 'discordant'), 'pct']}% "
        f"(n={int(prevalence.loc[(d, o, 'discordant'), 'n'])}) vs concordant "
        f"{prevalence.loc[(d, o, 'concordant'), 'pct']}% "
        f"(n={int(prevalence.loc[(d, o, 'concordant'), 'n'])})"
        for d, o, _ in prevalence.index if _ == "discordant")),
    decision="keep", name="prevalence", primary=False,
)
results.save(
    "E2A.2", discordance, paper="p1",
    method="Size of each glycaemia/label discordance group and the universe it sits in.",
    result="; ".join(f"{g}: {int(r.n_discordant)}/{int(r.n_universe)} ({r.pct}%)"
                     for g, r in discordance.iterrows()),
    decision="keep", name="discordance", primary=False,
)
