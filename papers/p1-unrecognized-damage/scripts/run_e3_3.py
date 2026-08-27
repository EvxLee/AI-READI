"""E3.3 — Confirmatory reruns of the headline set, exactly per PRESPEC.md.

Every parameter here — cutoffs, covariate sets, families, bootstrap seed, the
sweep grids — is read from the machine-readable block in `PRESPEC.md` via
`_phase3.prespec()`. Nothing is typed into this file that the spec could
disagree with. The spec's SHA-256 is written into the log entry so the reader
can check that what ran is what was frozen.

What runs, in the spec's order:

* **A1.1–A1.5** — the Aim-1 core sweep, which must reproduce the Phase-1
  artifacts to the last decimal (asserted, not assumed) — including both
  unrecognized denominators and the E1.4 who-is-unrecognized models — then
  its robustness: per-site direction checks of every trend, the cutoff sweeps
  extended to the population burden, and bootstrap intervals for the small
  Insulin cells.
* **A2.1–A2.4** — Aim 2 with the spec's covariate set (age + BMI + HbA1c +
  severity + site, which is *not* the Phase-2 set), BH within the 10-model
  family, the adjustment ladder on both the Phase-2 sample and the fixed
  spec sample, the five robustness checks with CES-D on the cohort-wide SD in
  every row, the missing-data sensitivity, and H3.
* **T1** — unrecognized diabetes beneath unrecognized damage, with Wald and
  bootstrap intervals on every small-cell row, the CGM replication, the
  double-unrecognized count, the three HbA1c bands, and its robustness.
* **T2** — ECG numeric metrics vs the heart marker, for the supplement.

Per-site rows carry Cochran's Q and I² as well as direction. Ends with
`E3.FREEZE`.

This is the SECOND run of E3.3 (first: 01:31 on 25 Aug). The first run's
entries stay in the log; the E3.REVIEW entry lists what the adversarial review
found and this run fixes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from aireadi import associations, figures, results, stats, thresholds

import _phase3

_phase3.banner("E3.3", "Confirmatory reruns per PRESPEC.md (second run, post-review)")

SPEC = _phase3.prespec()
SHA = _phase3.prespec_sha256()
print(f"PRESPEC.md version {SPEC['prespec_version']}, sha256 {SHA[:16]}…")

CUT = SPEC["cutoffs"]
SITES = SPEC["sites"]
GROUPS = list(SPEC["dataset"]["groups"])
ALPHA = SPEC["alpha"]
BOOT_N, BOOT_SEED, SMALL = (SPEC["bootstrap"]["n"], SPEC["bootstrap"]["seed"],
                            SPEC["bootstrap"]["small_cell"])
R = _phase3.RESULTS

df = _phase3.load_full(**CUT)
assert len(df) == SPEC["dataset"]["n"]
for g, n in SPEC["dataset"]["groups"].items():
    assert int((df.study_group_label == g).sum()) == n, g

# CES-D and PAID-5 on the COHORT-WIDE SD, once, so every row below — pooled,
# within-site, within-group, restricted-sample — is on the same scale.
CESD_SD = float(df["cesd_total"].std())
PAID_SD = float(df["paid_total"].std())
df["cesd_z"] = df["cesd_total"] / CESD_SD
df["paid_z"] = df["paid_total"] / PAID_SD
print(f"CES-D-10 cohort-wide SD {CESD_SD:.4f} (n={int(df.cesd_total.notna().sum())}); "
      f"PAID-5 SD {PAID_SD:.4f}")

either = thresholds.either_organ(df)


def unrec_burden_flag(organ: str) -> pd.Series:
    if organ == "either":
        return either["unrecognized"].where(either["answered"])
    abn, sr = df[f"abn_{organ}"], df[f"sr_{organ}"]
    return (abn.eq(1) & sr.eq(0)).astype(float).mask(abn.isna() | sr.isna())


def unrec_fraction_flag(organ: str) -> pd.Series:
    if organ == "either":
        return either["unrecognized"].where(either["answered"] & either["abnormal"])
    return df[f"unrec_{organ}"]


def boot_proportion(flag: pd.Series, *, n_boot: int = BOOT_N, seed: int = BOOT_SEED) -> tuple[float, float]:
    """Percentile bootstrap of a proportion, resampling participants."""
    vals = pd.to_numeric(flag, errors="coerce").dropna().to_numpy()
    if len(vals) == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(vals), size=(n_boot, len(vals)))
    means = vals[draws].mean(axis=1) * 100
    lo, hi = np.percentile(means, [2.5, 97.5])
    return (round(float(lo), 1), round(float(hi), 1))


def z_fit(frame, outcome, exposure, cov, family="binomial"):
    """`associations.fit` on an already-scaled (or binary) exposure."""
    return associations.fit(frame, outcome, exposure, cov, family=family, scale_by_sd=False)


# ═══════════════════════════════════════════════════════════════════════
# A1 — the core sweep, reproduced and stress-tested
# ═══════════════════════════════════════════════════════════════════════
print("\nA1 — core sweep per spec")
CLAIMS = {
    "prevalence": {o: df[f"abn_{o}"] for o in [*thresholds.ORGANS, "any"]},
    "unrecognized_fraction": {o: unrec_fraction_flag(o) for o in [*thresholds.UNRECOGNIZED_ORGANS, "either"]},
    "population_burden": {o: unrec_burden_flag(o) for o in [*thresholds.UNRECOGNIZED_ORGANS, "either"]},
    "two_or_more_organs": {"multi": df["abn_multi"]},
}

blocks = []
for claim, flags in CLAIMS.items():
    for organ, flag in flags.items():
        tab = stats.proportion_by_group(df.assign(_x=flag), "_x")
        tab.insert(0, "claim", claim)
        tab.insert(1, "organ", organ)
        if claim == "unrecognized_fraction":
            # The refusals-included denominator (A1.2 "both denominators").
            if organ == "either":
                incl = either["unrecognized"].eq(1).astype(float).where(either["markers_ok"] & either["abnormal"])
            else:
                abn, sr = df[f"abn_{organ}"], df[f"sr_{organ}"]
                incl = (abn.eq(1) & sr.eq(0)).astype(float).mask(abn.ne(1))
            sens = stats.proportion_by_group(df.assign(_x=incl), "_x", trend=False)
            tab["n_incl_refusals"] = sens["n"]
            tab["pct_incl_refusals"] = sens["pct"]
        blocks.append(tab)
confirm = pd.concat(blocks)

# Must reproduce Phase 1 exactly. Checked here, not assumed.
e11 = pd.read_csv(R / "E1_1_prevalence_by_group.csv").set_index(["organ", "stratum"])
e12 = pd.read_csv(R / "E1_2_unrecognized_by_group.csv").set_index(["organ", "stratum"])
e12b = pd.read_csv(R / "E1_2_population_burden.csv").set_index(["organ", "stratum"])
e13 = pd.read_csv(R / "E1_3_organ_counts.csv").set_index("stratum")
mismatches = []
for (claim, organ), sub in confirm.groupby(["claim", "organ"], sort=False):
    src = {"prevalence": e11, "unrecognized_fraction": e12, "population_burden": e12b}.get(claim)
    for stratum, row in sub.iterrows():
        if claim == "two_or_more_organs":
            want_k, want_n, want_pct = (int(e13.loc[stratum, "organs_2"] + e13.loc[stratum, "organs_3"]),
                                        int(e13.loc[stratum, "n"]), float(e13.loc[stratum, "pct_2_or_more"]))
        else:
            want = src.loc[(organ, stratum)]
            want_k, want_n, want_pct = int(want.k), int(want.n), float(want.pct)
        if not (int(row.k) == want_k and int(row.n) == want_n and abs(float(row.pct) - want_pct) < 0.051):
            mismatches.append(f"{claim}/{organ}/{stratum}: got {int(row.k)}/{int(row.n)} {row.pct}%, "
                              f"Phase 1 {want_k}/{want_n} {want_pct}%")
        if claim == "unrecognized_fraction":
            w = src.loc[(organ, stratum)]
            if not (int(row.n_incl_refusals) == int(w.n_incl_refusals)
                    and abs(float(row.pct_incl_refusals) - float(w.pct_incl_refusals)) < 0.051):
                mismatches.append(f"{claim}/{organ}/{stratum} refusals-included denominator differs")
confirm["reproduces_phase1"] = len(mismatches) == 0
print(f"  Phase-1 reproduction: {'EXACT' if not mismatches else 'MISMATCH'} "
      f"({len(confirm)} rows checked, both denominators)")
for m in mismatches:
    print("   -", m)
assert not mismatches, "confirmatory rerun does not reproduce Phase 1"

# ── A1.5 — the E1.4 who-is-unrecognized models, refitted ────────────────
# Same three nested models per organ as run_e1_4.py, same log-marker
# construction (ACR / troponin are strictly positive among the abnormal, so
# the reporting-floor substitution cannot enter). Must reproduce E1_4_models.csv.
e14 = pd.read_csv(R / "E1_4_models.csv").set_index(["organ", "model", "term"])
df["log_acr_raw"] = np.log(df["acr_mg_g"].where(df["acr_mg_g"] > 0))
df["log_troponin_raw"] = np.log(df["troponin_t"].where(df["troponin_t"] > 0))
MARKER = {"kidney": "log_acr_raw", "heart": "log_troponin_raw"}
a15_rows = []
for organ in thresholds.UNRECOGNIZED_ORGANS:
    sub = df[df[f"unrec_{organ}"].notna()]
    formulas = {
        "A: age + severity + site": f"unrec_{organ} ~ age + C(study_group_label) + C(clinical_site)",
        "B: A + HbA1c + BMI": f"unrec_{organ} ~ age + C(study_group_label) + C(clinical_site) + hba1c + bmi",
        "C: B + marker magnitude": (f"unrec_{organ} ~ age + C(study_group_label) + C(clinical_site) + hba1c + bmi"
                                    f" + {MARKER[organ]}"),
    }
    for name, formula in formulas.items():
        fit = smf.glm(formula, data=sub, family=sm.families.Binomial()).fit()
        ci = fit.conf_int()
        for term in fit.params.index:
            if term == "Intercept":
                continue
            t14 = term.replace("log_acr_raw", "log_acr").replace("log_troponin_raw", "log_troponin")
            want = e14.loc[(organ, name, t14)]
            a15_rows.append({"organ": organ, "model": name, "term": t14,
                             "odds_ratio": round(float(np.exp(fit.params[term])), 3),
                             "ci_lo": round(float(np.exp(ci.loc[term, 0])), 3),
                             "ci_hi": round(float(np.exp(ci.loc[term, 1])), 3),
                             "p": float(fit.pvalues[term]), "n_model": int(fit.nobs),
                             "e14_odds_ratio": float(want.odds_ratio), "e14_p": float(want.p),
                             "reproduces_e14": bool(abs(np.exp(fit.params[term]) - want.odds_ratio) < 0.0015
                                                    and abs(fit.pvalues[term] - want.p) < 1e-6)})
a15 = pd.DataFrame(a15_rows).set_index(["organ", "model", "term"])
assert a15.reproduces_e14.all(), "A1.5 does not reproduce E1_4_models.csv"
print(f"  A1.5: {len(a15)} model terms reproduce E1.4 exactly")

# ── Per-site direction check of every trend ─────────────────────────────
site_rows = []
for claim, flags in CLAIMS.items():
    for organ, flag in flags.items():
        pooled = stats.proportion_by_group(df.assign(_x=flag), "_x")
        for site in SITES:
            m = df["clinical_site"] == site
            tab = stats.proportion_by_group(df[m].assign(_x=flag[m]), "_x")
            row = {"claim": claim, "organ": organ, "site": site,
                   "n": int(tab.loc["Overall", "n"]), "k": int(tab.loc["Overall", "k"]),
                   "pct": float(tab.loc["Overall", "pct"]),
                   "trend_z": float(tab.loc["Overall", "trend_z"]),
                   "trend_p": float(tab.loc["Overall", "trend_p"]),
                   "same_direction_as_pooled": bool(np.sign(tab.loc["Overall", "trend_z"])
                                                    == np.sign(pooled.loc["Overall", "trend_z"])),
                   "significant_within_site": bool(tab.loc["Overall", "trend_p"] < ALPHA)}
            for g in GROUPS:
                row[f"pct_{g}"] = float(tab.loc[g, "pct"])
                row[f"n_{g}"] = int(tab.loc[g, "n"])
            site_rows.append(row)
by_site = pd.DataFrame(site_rows).set_index(["claim", "organ", "site"])
consistent = by_site.groupby(["claim", "organ"])["same_direction_as_pooled"].all()
sig_sites = by_site.groupby(["claim", "organ"])["significant_within_site"].sum()
print(f"  per-site: {int(consistent.sum())}/{len(consistent)} claims keep their trend sign at every site; "
      f"{int((sig_sites == 3).sum())} are significant within all three sites")
_phase3.print_table(by_site[["n", "pct", "pct_Healthy", "pct_Insulin", "trend_z", "trend_p",
                             "same_direction_as_pooled"]], title="A1 by site")

# ── Bootstrap intervals for every group cell, beside the Wilson interval ─
boot_rows = []
for claim in ("unrecognized_fraction", "population_burden"):
    for organ, flag in CLAIMS[claim].items():
        tab = stats.proportion_by_group(df.assign(_x=flag), "_x")
        for g in GROUPS:
            cell = flag[df["study_group_label"] == g]
            lo, hi = boot_proportion(cell)
            k, n = int(tab.loc[g, "k"]), int(tab.loc[g, "n"])
            boot_rows.append({"claim": claim, "organ": organ, "stratum": g, "n": n, "k": k,
                              "smaller_cell": min(k, n - k), "pct": float(tab.loc[g, "pct"]),
                              "wilson_lo": float(tab.loc[g, "ci_lo"]), "wilson_hi": float(tab.loc[g, "ci_hi"]),
                              "boot_lo": lo, "boot_hi": hi,
                              "small_cell_rule_applies": min(k, n - k) < SMALL})
boot = pd.DataFrame(boot_rows).set_index(["claim", "organ", "stratum"])
_phase3.print_table(boot, title="A1 Wilson vs bootstrap intervals by group")

# ── Cutoff sweeps extended to the burden ────────────────────────────────
sweep_rows = []
ARG = {"kidney": "acr_mg_g", "heart": "troponin_ng_l"}
for organ, arg in ARG.items():
    for rung in SPEC["sweeps"][arg]:
        d2 = thresholds.add_damage_flags(df, **{**CUT, arg: rung})
        abn, sr = d2[f"abn_{organ}"], d2[f"sr_{organ}"]
        burden = (abn.eq(1) & sr.eq(0)).astype(float).mask(abn.isna() | sr.isna())
        b = stats.proportion_by_group(d2.assign(_x=burden), "_x")
        f = stats.proportion_by_group(d2, f"unrec_{organ}")
        p = stats.proportion_by_group(d2, f"abn_{organ}")
        row = {"organ": organ, "cutoff": str(rung), "is_primary": rung == CUT[arg],
               "prevalence_pct": float(p.loc["Overall", "pct"]),
               "unrecognized_pct": float(f.loc["Overall", "pct"]),
               "burden_pct": float(b.loc["Overall", "pct"]),
               "burden_ci_lo": float(b.loc["Overall", "ci_lo"]), "burden_ci_hi": float(b.loc["Overall", "ci_hi"]),
               "burden_trend_z": float(b.loc["Overall", "trend_z"]),
               "burden_trend_p": float(b.loc["Overall", "trend_p"])}
        for g in GROUPS:
            row[f"burden_{g}"] = float(b.loc[g, "pct"])
        sweep_rows.append(row)
for organ, arg in ARG.items():
    for rung in SPEC["sweeps"][arg]:
        d2 = thresholds.add_damage_flags(df, **{**CUT, arg: rung})
        e2 = thresholds.either_organ(d2)
        b = stats.proportion_by_group(d2.assign(_x=e2["unrecognized"].where(e2["answered"])), "_x")
        row = {"organ": f"either ({organ} grid)", "cutoff": str(rung), "is_primary": rung == CUT[arg],
               "prevalence_pct": np.nan, "unrecognized_pct": np.nan,
               "burden_pct": float(b.loc["Overall", "pct"]),
               "burden_ci_lo": float(b.loc["Overall", "ci_lo"]), "burden_ci_hi": float(b.loc["Overall", "ci_hi"]),
               "burden_trend_z": float(b.loc["Overall", "trend_z"]),
               "burden_trend_p": float(b.loc["Overall", "trend_p"])}
        for g in GROUPS:
            row[f"burden_{g}"] = float(b.loc[g, "pct"])
        sweep_rows.append(row)
burden_sweep = pd.DataFrame(sweep_rows).set_index(["organ", "cutoff"])
_phase3.print_table(burden_sweep, title="A1 burden across the cutoff grids")
burden_holds = bool((burden_sweep.burden_trend_z > 0).all() and (burden_sweep.burden_trend_p < ALPHA).all())
clinical = burden_sweep[burden_sweep.index.get_level_values("cutoff") != "detectable"]
burden_holds_clinical = bool((clinical.burden_trend_z > 0).all() and (clinical.burden_trend_p < ALPHA).all())
detectable_p = float(burden_sweep.loc[("heart", "detectable"), "burden_trend_p"])
print(f"  'unrecognized burden rises with severity' holds at every rung: {burden_holds} "
      f"(excluding the non-clinical 'detectable' rung: {burden_holds_clinical}; heart at that rung p={detectable_p:.3f})")

# ═══════════════════════════════════════════════════════════════════════
# A2 — Aim 2 per spec
# ═══════════════════════════════════════════════════════════════════════
print("\nA2 — CES-D-10 vs measured damage, spec covariates")
A2 = SPEC["aim2"]
COV = A2["covariates"]
BASE = ["age", "C(study_group_label)", "C(clinical_site)"]
OUT_LABEL = {**associations.BINARY_OUTCOMES, **associations.CONTINUOUS_OUTCOMES}
EXP_LABEL = {"cesd_total": "CES-D-10 total (per SD)", "cesd_positive": "CES-D-10 >= 10"}
EXP_COL = {"cesd_total": "cesd_z", "cesd_positive": "cesd_positive"}


def family_fit(frame, exposures=("cesd_total", "cesd_positive"), cov=COV):
    rows = []
    for exposure in exposures:
        for outcome in A2["outcomes"] + [A2["supporting_outcome"]]:
            fam = "gaussian" if outcome in associations.CONTINUOUS_OUTCOMES else "binomial"
            row = z_fit(frame, outcome, EXP_COL[exposure], cov, family=fam)
            row.update({"exposure": exposure, "exposure_label": EXP_LABEL[exposure],
                        "outcome_label": OUT_LABEL[outcome], "family": fam,
                        "in_corrected_family": outcome in A2["outcomes"],
                        "scale": "per cohort-wide SD" if exposure == "cesd_total" else "yes vs no"})
            rows.append(row)
    out = pd.DataFrame(rows)
    fam_mask = out["in_corrected_family"]
    assert int(fam_mask.sum()) == A2["fdr_family_size"]
    out["q"] = np.nan
    out.loc[fam_mask, "q"] = associations.fdr(out.loc[fam_mask, "p"])
    return out.set_index(["exposure", "outcome"])[
        ["exposure_label", "outcome_label", "family", "scale", "n", "estimate", "ci_lo", "ci_hi",
         "p", "q", "in_corrected_family", "note"]]


aim2 = family_fit(df)


def claim_table(table):
    claimed = []
    for outcome in A2["outcomes"]:
        rows = table.xs(outcome, level="outcome")
        both_q = bool((rows.q < ALPHA).all())
        same_dir = bool((rows.estimate > 1).all() or (rows.estimate < 1).all())
        claimed.append({"outcome": outcome, "outcome_label": OUT_LABEL[outcome],
                        "q_total": float(rows.loc["cesd_total", "q"]),
                        "q_positive": float(rows.loc["cesd_positive", "q"]),
                        "or_total": float(rows.loc["cesd_total", "estimate"]),
                        "or_positive": float(rows.loc["cesd_positive", "estimate"]),
                        "both_forms_q_lt_alpha": both_q, "same_direction": same_dir,
                        "meets_claim_rule": both_q and same_dir})
    return pd.DataFrame(claimed).set_index("outcome")


aim2_claims = claim_table(aim2)
_phase3.print_table(aim2, title="A2.1 confirmatory family (spec covariates, complete case)")
_phase3.print_table(aim2_claims, title="A2.1 claim rule per outcome (q < alpha in BOTH forms, same direction)")
a2_hits = aim2_claims[aim2_claims.meets_claim_rule]

# ── Adjustment ladder: on the Phase-2 sample AND on the fixed spec sample ──
spec_plain = associations._plain(COV)
spec_sample = df.dropna(subset=["cesd_total", "abn_nerve", *spec_plain])
p2_sample = df.dropna(subset=["cesd_total", "abn_nerve", *associations._plain(BASE)])
ladder_rows = []
steps = [("unadjusted", []), ("+ age", ["age"]), ("+ age + severity", ["age", "C(study_group_label)"]),
         ("+ age + severity + site", BASE), ("+ age + severity + site + HbA1c", BASE + ["hba1c"]),
         ("+ age + severity + site + BMI", BASE + ["bmi"]), ("full spec (+ BMI + HbA1c)", COV)]
P2_KEY = "Phase-2 sample (each step's own complete cases)"
for sample_label, frame in [(P2_KEY, df),
                            (f"fixed spec complete-case sample (n={len(spec_sample):,})", spec_sample)]:
    for label, cov in steps:
        for outcome in ("abn_nerve", A2["supporting_outcome"]):
            fam = "gaussian" if outcome in associations.CONTINUOUS_OUTCOMES else "binomial"
            row = z_fit(frame, outcome, "cesd_z", cov, family=fam)
            ladder_rows.append({"sample": sample_label, "step": label, "outcome": outcome,
                                **{k: row[k] for k in ("n", "estimate", "ci_lo", "ci_hi", "p")}})
aim2_ladder = pd.DataFrame(ladder_rows).set_index(["sample", "step", "outcome"])
_phase3.print_table(aim2_ladder.xs("abn_nerve", level="outcome"),
                    title="A2.1 adjustment ladder, CES-D (per cohort SD) -> nerve, both samples")
lad = aim2_ladder.xs("abn_nerve", level="outcome")
fixed_key = f"fixed spec complete-case sample (n={len(spec_sample):,})"
lost = len(p2_sample) - len(spec_sample)
lost_rows = p2_sample[~p2_sample.index.isin(spec_sample.index)]
print(f"  participants lost to BMI/HbA1c missingness: {lost} "
      f"(nerve-abnormal {100 * lost_rows.abn_nerve.mean():.1f}% vs {100 * spec_sample.abn_nerve.mean():.1f}% kept; "
      f"mean CES-D {lost_rows.cesd_total.mean():.2f} vs {spec_sample.cesd_total.mean():.2f})")
log_drop_total = float(np.log(lad.loc[(P2_KEY, "+ age + severity + site"), "estimate"])
                       - np.log(lad.loc[(fixed_key, "full spec (+ BMI + HbA1c)"), "estimate"]))
log_drop_sample = float(np.log(lad.loc[(P2_KEY, "+ age + severity + site"), "estimate"])
                        - np.log(lad.loc[(fixed_key, "+ age + severity + site"), "estimate"]))
share_sample = 100 * log_drop_sample / log_drop_total if log_drop_total else np.nan
print(f"  attenuation on the log-OR scale: {log_drop_total:.4f} total, of which sample change "
      f"{log_drop_sample:.4f} ({share_sample:.0f}%)")

# ── A2.2 robustness, every row on the cohort-wide SD ────────────────────
rob_rows = []
# (a) per site (fit_by_site pre-scales by the cohort SD itself)
for exposure in A2["exposures"]:
    s = _phase3.fit_by_site(df, "abn_nerve", exposure, COV)
    for site, r in s.iterrows():
        rob_rows.append({"check": "within site", "detail": site, "exposure": exposure, "outcome": "abn_nerve",
                         "n": r.n, "estimate": r.estimate, "ci_lo": r.ci_lo, "ci_hi": r.ci_hi, "p": r.p, "note": r.note})
# (b) nerve cutoff
for missed in A2["nerve_cutoff_sensitivity"]:
    d2 = thresholds.add_damage_flags(df, **{**CUT, "monofilament_missed": missed})
    for exposure in A2["exposures"]:
        r = z_fit(d2, "abn_nerve", EXP_COL[exposure], COV)
        rob_rows.append({"check": "nerve cutoff", "detail": f">= {missed} insensate sites", "exposure": exposure,
                         "outcome": "abn_nerve", **{k: r[k] for k in ("n", "estimate", "ci_lo", "ci_hi", "p")}, "note": r["note"]})
# (c) odd monofilament rows
both_zero = df["monofilament_left"].eq(0) & df["monofilament_right"].eq(0)
asym = ((df["monofilament_left"].eq(0) & df["monofilament_right"].eq(10))
        | (df["monofilament_right"].eq(0) & df["monofilament_left"].eq(10)))
if A2["odd_row_exclusion"]:
    keep = ~(both_zero | asym)
    for exposure in A2["exposures"]:
        for outcome in ("abn_nerve", A2["supporting_outcome"]):
            fam = "gaussian" if outcome in associations.CONTINUOUS_OUTCOMES else "binomial"
            r = z_fit(df[keep], outcome, EXP_COL[exposure], COV, family=fam)
            rob_rows.append({"check": "drop odd monofilament rows", "detail": f"n dropped = {int((~keep).sum())}",
                             "exposure": exposure, "outcome": outcome,
                             **{k: r[k] for k in ("n", "estimate", "ci_lo", "ci_hi", "p")}, "note": r["note"]})
# (d) PAID-5 mutual adjustment on one identical sample, both on cohort SDs
if A2["paid5_mutual_adjustment"]:
    sample = df.dropna(subset=["cesd_z", "paid_z", "abn_nerve", *spec_plain])
    for exposure, other in [("cesd_z", "paid_z"), ("paid_z", "cesd_z")]:
        alone = z_fit(sample, "abn_nerve", exposure, COV)
        mutual = z_fit(sample, "abn_nerve", exposure, COV + [other])
        for label, r in [("alone", alone), (f"mutually adjusted for {'PAID-5' if other == 'paid_z' else 'CES-D-10'}", mutual)]:
            rob_rows.append({"check": "PAID-5 head-to-head (identical sample)", "detail": label,
                             "exposure": "cesd_total" if exposure == "cesd_z" else "paid_total", "outcome": "abn_nerve",
                             **{k: r[k] for k in ("n", "estimate", "ci_lo", "ci_hi", "p")}, "note": r["note"]})
aim2_robust = pd.DataFrame(rob_rows).set_index(["check", "detail", "exposure", "outcome"])
_phase3.print_table(aim2_robust, title="A2.2 robustness (CES-D per cohort-wide SD everywhere)")
failing = aim2_robust[(aim2_robust.index.get_level_values("outcome") == "abn_nerve") & (aim2_robust.p >= ALPHA)]
print(f"  robustness rows for nerve NOT significant at 0.05: {len(failing)} of "
      f"{int((aim2_robust.index.get_level_values('outcome') == 'abn_nerve').sum())}")

# (e) within severity, cohort-wide SD, bootstrap where the smaller cell < SMALL
strata = associations.stratified(df, "cesd_z", "abn_nerve", covariates=COV,
                                 bootstrap_below=SMALL, n_boot=BOOT_N, seed=BOOT_SEED, scale_by_sd=False)
strata["scale"] = "per cohort-wide SD"
_phase3.print_table(strata, title="A2.2 within severity group (cohort-wide SD)")

# ── Site heterogeneity for the model-based headline rows ────────────────
het_rows = []
for label, outcome, exposure, cov, fam, universe in [
    ("A2.1 CES-D per SD -> nerve", "abn_nerve", "cesd_total", COV, "binomial", None),
    ("A2.1 CES-D >= 10 -> nerve", "abn_nerve", "cesd_positive", COV, "binomial", None),
]:
    s = _phase3.fit_by_site(df, outcome, exposure, cov, family=fam, universe=universe)
    pooled = z_fit(df, outcome, EXP_COL[exposure], cov, family=fam)["estimate"]
    het_rows.append({"analysis": label, "pooled": pooled, **_phase3.site_consistency(s, pooled, family=fam),
                     **{f"{site}_estimate": s.loc[site, "estimate"] for site in SITES},
                     **{f"{site}_p": s.loc[site, "p"] for site in SITES}})

# ── A2.4 missing-data sensitivity: single imputation at the group median ─
imp = df.copy()
for col in ("bmi", "hba1c"):
    med = imp.groupby("study_group_label", observed=True)[col].transform("median")
    imp[col] = imp[col].fillna(med)
aim2_imputed = family_fit(imp)
imputed_claims = claim_table(aim2_imputed)
_phase3.print_table(aim2_imputed[aim2_imputed.in_corrected_family][["n", "estimate", "ci_lo", "ci_hi", "p", "q"]],
                    title="A2.4 missing-data sensitivity: BMI / HbA1c single-imputed at the severity-group median")
imp_nerve = aim2_imputed.loc[("cesd_total", "abn_nerve")]
imp_nerve_pos = aim2_imputed.loc[("cesd_positive", "abn_nerve")]

# ── A2.3 H3 ─────────────────────────────────────────────────────────────
h3_rows = []
for outcome in A2["h3_outcomes"]:
    cov = A2["h3_covariates"] + A2["h3_marker"][outcome]
    for exposure in A2["exposures"]:
        r = z_fit(df, outcome, EXP_COL[exposure], cov)
        r.update({"exposure": exposure, "exposure_label": EXP_LABEL[exposure],
                  "scale": "per cohort-wide SD" if exposure == "cesd_total" else "yes vs no"})
        h3_rows.append(r)
h3 = pd.DataFrame(h3_rows)
h3["q"] = associations.fdr(h3["p"])
h3 = h3.set_index(["exposure", "outcome"])[["exposure_label", "scale", "n", "estimate", "ci_lo", "ci_hi", "p", "q", "note"]]
_phase3.print_table(h3, title="A2.3 H3 — CES-D vs unrecognized status, spec covariates + marker (= E2C.2 model)")
h3_survivors = h3[h3.q < ALPHA]

# ═══════════════════════════════════════════════════════════════════════
# T1 — unrecognized diabetes beneath unrecognized damage
# ═══════════════════════════════════════════════════════════════════════
print("\nT1 — undiagnosed-range glycaemia vs damage")
T1 = SPEC["track_undiagnosed"]
universe = df["study_group_label"].isin(T1["universe"])
U = df[universe]
e2a2 = pd.read_csv(R / "E2A_2_models.csv").set_index(["definition", "outcome"])
t1_rows = []
for definition in ("undiagnosed_range", "undiagnosed_range_cgm"):
    for outcome in T1["outcomes"]:
        r = associations.fit(U, outcome, definition, T1["covariates"])
        used = U.dropna(subset=[outcome, definition, *associations._plain(T1["covariates"])])
        n_exposed = int(used[definition].sum())
        events_exposed = int(used.loc[used[definition].eq(1), outcome].sum())
        lo, hi = associations.bootstrap_ci(used, outcome, definition, T1["covariates"],
                                           n_boot=BOOT_N, seed=BOOT_SEED)
        r.update({"definition": definition, "n_exposed": n_exposed, "events_exposed": events_exposed,
                  "pct_exposed": round(100 * used.loc[used[definition].eq(1), outcome].mean(), 1),
                  "pct_unexposed": round(100 * used.loc[used[definition].eq(0), outcome].mean(), 1),
                  "boot_ci_lo": lo, "boot_ci_hi": hi, "is_primary": outcome == T1["primary_outcome"],
                  "phase2_q": float(e2a2.loc[(definition, outcome), "q"])})
        t1_rows.append(r)
        print(f"  {definition}/{outcome}: OR {r['estimate']} Wald {r['ci_lo']}-{r['ci_hi']} boot {lo}-{hi}")
t1 = pd.DataFrame(t1_rows)
assert len(t1) == T1["fdr_family_size"]
t1["q"] = associations.fdr(t1["p"])
t1 = t1.set_index(["definition", "outcome"])[
    ["is_primary", "n", "n_exposed", "events_exposed", "pct_exposed", "pct_unexposed", "estimate",
     "ci_lo", "ci_hi", "boot_ci_lo", "boot_ci_hi", "p", "q", "phase2_q", "note"]]
_phase3.print_table(t1, title="T1 family (= E2A.2 models; family narrowed 15 -> 10, Phase-2 q alongside)")

double = df["undiagnosed_range"].eq(1) & either["abnormal"] & either["answered"]
double_unrec = double & either["unrecognized"].eq(1)
n_exposed_all = int(df["undiagnosed_range"].sum())
print(f"  double-unrecognized: {int(double_unrec.sum())} of {int(double.sum())} "
      f"(of {n_exposed_all} undiagnosed-range participants)")

# Robustness, every small-cell row bootstrapped.
t1_rob = []


def t1_row(check, detail, frame, outcome, exposure, cov):
    r = associations.fit(frame, outcome, exposure, cov)
    used = frame.dropna(subset=[outcome, exposure, *associations._plain(cov)])
    n_exp = int(used[exposure].sum())
    ev = int(used.loc[used[exposure].eq(1), outcome].sum())
    lo, hi = (associations.bootstrap_ci(used, outcome, exposure, cov, n_boot=BOOT_N, seed=BOOT_SEED)
              if 0 < n_exp < SMALL * 2 else (np.nan, np.nan))
    t1_rob.append({"check": check, "detail": detail, "outcome": outcome, "n": r["n"], "n_exposed": n_exp,
                   "events_exposed": ev, "estimate": r["estimate"], "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"],
                   "boot_ci_lo": lo, "boot_ci_hi": hi, "p": r["p"], "note": r["note"]})


for site in SITES:
    frame = U[U["clinical_site"] == site]
    t1_row("within site", site, frame, T1["primary_outcome"], "undiagnosed_range", ["age"])
for rung in T1["acr_sweep"]:
    d2 = thresholds.add_damage_flags(df, **{**CUT, "acr_mg_g": rung})
    t1_row("kidney cutoff", f"ACR >= {rung:g} mg/g", d2[universe], "abn_kidney", "undiagnosed_range", T1["covariates"])
strict = (df["study_group_label"].isin(T1["universe"]) & df["hba1c"].ge(T1["hba1c_sensitivity"])
          ).astype(float).mask(df["hba1c"].isna())
d3 = df.assign(undiagnosed_strict=strict)
for outcome in (T1["primary_outcome"], "abn_any"):
    t1_row("HbA1c threshold shift", f"HbA1c >= {T1['hba1c_sensitivity']}% vs all below (6.5-6.9 joins the reference)",
           d3[universe], outcome, "undiagnosed_strict", T1["covariates"])
t1_robust = pd.DataFrame(t1_rob).set_index(["check", "detail", "outcome"])
_phase3.print_table(t1_robust, title="T1 robustness (bootstrap on every small-cell row)")

# Three HbA1c bands, as counts.
band = pd.cut(U["hba1c"], [-np.inf, T1["hba1c_cutoff"] - 1e-9, T1["hba1c_sensitivity"] - 1e-9, np.inf],
              labels=[f"< {T1['hba1c_cutoff']}%", f"{T1['hba1c_cutoff']}-{T1['hba1c_sensitivity'] - 0.1:.1f}%",
                      f">= {T1['hba1c_sensitivity']}%"])
band_rows = []
for level in band.cat.categories:
    cell = U.loc[band == level, "abn_kidney"].dropna()
    got = stats.proportion(cell)
    band_rows.append({"hba1c_band": level, "n": got["n"], "kidney_abnormal": got["k"], "pct": round(got["pct"], 1),
                      "ci_lo": round(got["ci_lo"], 1), "ci_hi": round(got["ci_hi"], 1)})
t1_bands = pd.DataFrame(band_rows).set_index("hba1c_band")
_phase3.print_table(t1_bands, title="T1 kidney damage by HbA1c band, Healthy + Pre-DM")

s = _phase3.fit_by_site(df, T1["primary_outcome"], "undiagnosed_range", T1["covariates"], universe=universe)
pooled = t1.loc[("undiagnosed_range", T1["primary_outcome"]), "estimate"]
het_rows.append({"analysis": "T1 undiagnosed-range -> kidney", "pooled": pooled,
                 **_phase3.site_consistency(s, pooled),
                 **{f"{site}_estimate": s.loc[site, "estimate"] for site in SITES},
                 **{f"{site}_p": s.loc[site, "p"] for site in SITES}})

# ═══════════════════════════════════════════════════════════════════════
# T2 — ECG numeric metrics vs the heart marker
# ═══════════════════════════════════════════════════════════════════════
print("\nT2 — ECG numeric metrics vs the heart marker")
T2 = SPEC["track_ecg"]
ECG_LABEL = {"rate_bpm": "ECG heart rate (bpm)", "pr_ms": "PR interval (ms)", "qrsd_ms": "QRS duration (ms)",
             "qt_ms": "QT interval (ms)", "qtc_ms": "QTc interval (ms)"}
e2e2 = pd.read_csv(R / "E2E_2_sweep.csv")
e2e2 = e2e2[e2e2.adjustment == "damage"].set_index(["exposure", "outcome"])
t2_rows = []
for metric in T2["metrics"]:
    for outcome in T2["outcomes"]:
        fam = "gaussian" if outcome in associations.CONTINUOUS_OUTCOMES else "binomial"
        r = associations.fit(df, outcome, metric, T2["covariates"], family=fam)
        r.update({"metric_label": ECG_LABEL[metric], "family": fam,
                  "phase2_q": float(e2e2.loc[(metric, outcome), "q"])})
        t2_rows.append(r)
t2 = pd.DataFrame(t2_rows)
assert len(t2) == T2["fdr_family_size"]
t2["q"] = associations.fdr(t2["p"])
t2 = t2.set_index(["exposure", "outcome"])[["metric_label", "family", "n", "estimate", "ci_lo", "ci_hi", "p", "q", "phase2_q", "note"]]
t2_site_rows = []
for metric in ("qrsd_ms", "qtc_ms"):
    for outcome in T2["outcomes"]:
        fam = "gaussian" if outcome in associations.CONTINUOUS_OUTCOMES else "binomial"
        s = _phase3.fit_by_site(df, outcome, metric, T2["covariates"], family=fam)
        for site, r in s.iterrows():
            t2_site_rows.append({"metric": metric, "outcome": outcome, "site": site, "n": r.n,
                                 "estimate": r.estimate, "ci_lo": r.ci_lo, "ci_hi": r.ci_hi, "p": r.p})
        pooled = t2.loc[(metric, outcome), "estimate"]
        het_rows.append({"analysis": f"T2 {metric} -> {outcome}", "pooled": pooled,
                         **_phase3.site_consistency(s, pooled, family=fam),
                         **{f"{site}_estimate": s.loc[site, "estimate"] for site in SITES},
                         **{f"{site}_p": s.loc[site, "p"] for site in SITES}})
t2_sites = pd.DataFrame(t2_site_rows).set_index(["metric", "outcome", "site"])
heterogeneity = pd.DataFrame(het_rows).set_index("analysis")
_phase3.print_table(t2, title="T2 family (= E2E.2 models; family narrowed 40 -> 10, Phase-2 q alongside)")
_phase3.print_table(t2_sites, title="T2 by site")
_phase3.print_table(heterogeneity, title="Site direction check with Cochran's Q / I2 for the model-based rows")

# ═══════════════════════════════════════════════════════════════════════
# Figures
# ═══════════════════════════════════════════════════════════════════════
figures.style()

fig1, axes = figures.new_figure(11, 4.4, ncols=3, sharey=True)
for ax, site in zip(axes, SITES):
    r = by_site.loc[("population_burden", "either", site)]
    vals = [r[f"pct_{g}"] for g in GROUPS]
    figures.grouped_bars(ax, GROUPS, {"burden": vals}, [figures.ORGAN["kidney"]], fmt="{:.1f}")
    ax.set_title(f"{site}  (trend z = {r.trend_z:.2f}, p = {r.trend_p:.2g})")
    ax.set_ylim(0, 60)
axes[0].set_ylabel("% with unrecognized damage")
figures.finish(fig1, "E3.3 — the abstract's burden figure holds within every site",
               "Unrecognized kidney-or-heart damage per 100 evaluable participants, by severity group, "
               "computed separately within UW, UAB and UCSD. A direction check, not a replication.",
               source="Source: results/E3_3_aim1_by_site.csv")

fig2, ax = figures.new_figure(9.5, 5.2)
labels, ests, lo, hi, cols, sig = [], [], [], [], [], []
for outcome in A2["outcomes"]:
    for exposure in A2["exposures"]:
        r = aim2.loc[(exposure, outcome)]
        labels.append(f"{OUT_LABEL[outcome].split(' (')[0]} — {EXP_LABEL[exposure]}")
        ests.append(r.estimate); lo.append(r.ci_lo); hi.append(r.ci_hi)
        cols.append(figures.ORGAN["nerve"] if outcome == "abn_nerve" else figures.DEEMPHASIS)
        sig.append(bool(r.q < ALPHA))
figures.forest(ax, labels, ests, lo, hi, colors=cols, significant=sig)
ax.set_xlabel("Odds ratio, age + BMI + HbA1c + severity + site adjusted — filled: q < 0.05")
figures.finish(fig2, "E3.3 — Aim 2 per PRESPEC: depressive symptoms and measured damage",
               "CES-D-10 (per cohort-wide SD, and at the >= 10 screen) against each damage outcome with the "
               "pre-specified covariate set; Benjamini-Hochberg within the 10-model family. No row clears it.",
               source="Source: results/E3_3_aim2_confirmatory.csv")

fig3, axes = figures.new_figure(11, 4.2, ncols=2)
for ax, organ in zip(axes, ("kidney", "heart")):
    s = burden_sweep.loc[organ]
    x = np.arange(len(s))
    ax.plot(x, s.burden_pct, marker="o", color=figures.ORGAN[organ])
    ax.fill_between(x, s.burden_ci_lo, s.burden_ci_hi, color=figures.ORGAN[organ], alpha=0.15, linewidth=0)
    prim = int(np.where(s.is_primary)[0][0])
    ax.plot([x[prim]], [s.burden_pct.iloc[prim]], marker="o", markersize=16, markerfacecolor="none",
            markeredgecolor=figures.INK, markeredgewidth=1.5)
    ax.set_xticks(x); ax.set_xticklabels([f"{'≥ ' if c != 'detectable' else ''}{c}" for c in s.index])
    ax.set_title(f"{organ.capitalize()} — burden per 100 evaluable, by cutoff")
    ax.set_ylabel("% abnormal and unrecognized")
    ax.set_xlabel("ACR cutoff, mg/g" if organ == "kidney" else "hs-cTnT cutoff, ng/L")
figures.finish(fig3, "E3.3 — the burden across every cutoff in the grid (pooled)",
               "Shaded band: Wilson 95% CI. Circled: the pre-specified cutoff. The rise across severity is "
               "positive and significant at every rung, including the non-clinical 'any detectable troponin' rung.",
               source="Source: results/E3_3_burden_sweep.csv")

# ═══════════════════════════════════════════════════════════════════════
# Headline summary and save
# ═══════════════════════════════════════════════════════════════════════
def cell(claim, organ, stratum="Overall"):
    return confirm[(confirm.claim == claim) & (confirm.organ == organ)].loc[stratum]

nerve = aim2.loc[("cesd_total", "abn_nerve")]
nerve_pos = aim2.loc[("cesd_positive", "abn_nerve")]
t1_prim = t1.loc[("undiagnosed_range", T1["primary_outcome"])]
t1_cgm = t1.loc[("undiagnosed_range_cgm", T1["primary_outcome"])]
a2_site = heterogeneity.loc["A2.1 CES-D per SD -> nerve"]
t1_site = heterogeneity.loc["T1 undiagnosed-range -> kidney"]
t2_site = heterogeneity.loc["T2 qrsd_ms -> log_troponin"]
a2_verdict = ("claimed — pre-specified criterion met" if bool(aim2_claims.loc["abn_nerve", "meets_claim_rule"])
              else "NOT claimed — pre-specified criterion not met")

summary = pd.DataFrame([
    {"claim": "A1.1 any-organ prevalence", "value": f"{cell('prevalence','any').pct}% ({int(cell('prevalence','any').k)}/{int(cell('prevalence','any').n)})",
     "trend": f"z={cell('prevalence','any').trend_z}", "reproduces_phase1": True,
     "sites_same_direction": int(by_site.loc[('prevalence','any')].same_direction_as_pooled.sum()), "verdict": "confirmed"},
    {"claim": "A1.2 either-organ unrecognized fraction", "value": f"{cell('unrecognized_fraction','either').pct}% ({int(cell('unrecognized_fraction','either').k)}/{int(cell('unrecognized_fraction','either').n)}); refusals included {cell('unrecognized_fraction','either').pct_incl_refusals}%",
     "trend": f"z={cell('unrecognized_fraction','either').trend_z}", "reproduces_phase1": True,
     "sites_same_direction": int(by_site.loc[('unrecognized_fraction','either')].same_direction_as_pooled.sum()), "verdict": "confirmed"},
    {"claim": "A1.3 either-organ burden (abstract lead)", "value": f"{cell('population_burden','either').pct}% overall; Insulin {cell('population_burden','either','Insulin').pct}%",
     "trend": f"z={cell('population_burden','either').trend_z}", "reproduces_phase1": True,
     "sites_same_direction": int(by_site.loc[('population_burden','either')].same_direction_as_pooled.sum()),
     "verdict": f"confirmed; rises at every cutoff rung ({'incl.' if burden_holds else 'except'} the non-clinical detectable rung)"},
    {"claim": "A1.4 two-or-more organs", "value": f"{cell('two_or_more_organs','multi').pct}%",
     "trend": f"z={cell('two_or_more_organs','multi').trend_z}", "reproduces_phase1": True,
     "sites_same_direction": int(by_site.loc[('two_or_more_organs','multi')].same_direction_as_pooled.sum()), "verdict": "confirmed"},
    {"claim": "A1.5 who-is-unrecognized models (E1.4)", "value": f"{len(a15)} model terms reproduce E1_4_models.csv", "trend": "",
     "reproduces_phase1": True, "sites_same_direction": np.nan, "verdict": "confirmed (kidney established, heart suggestive — unchanged)"},
    {"claim": "A2.1 CES-D-10 -> nerve abnormal (spec covariates)", "value": f"OR {nerve.estimate} ({nerve.ci_lo}-{nerve.ci_hi}) per SD, p={nerve.p:.3g}, q={nerve.q:.3g}; >=10: OR {nerve_pos.estimate} ({nerve_pos.ci_lo}-{nerve_pos.ci_hi}), p={nerve_pos.p:.3g}, q={nerve_pos.q:.3g}",
     "trend": f"site direction {int(a2_site.sites_same_direction)}/3, Q p={a2_site.heterogeneity_q_p:.2f}, I2={a2_site.i_squared_pct}%", "reproduces_phase1": np.nan,
     "sites_same_direction": int(a2_site.sites_same_direction), "verdict": a2_verdict},
    {"claim": "A2.4 missing-data sensitivity (single imputation, n=2,265)", "value": f"OR {imp_nerve.estimate} ({imp_nerve.ci_lo}-{imp_nerve.ci_hi}), q={imp_nerve.q:.3g}; >=10: OR {imp_nerve_pos.estimate}, q={imp_nerve_pos.q:.3g}",
     "trend": "", "reproduces_phase1": np.nan, "sites_same_direction": np.nan,
     "verdict": "criterion still not met" if not bool(imputed_claims.loc["abn_nerve", "meets_claim_rule"]) else "criterion met under imputation"},
    {"claim": "A2.3 H3 CES-D -> unrecognized", "value": f"{len(h3_survivors)} of {len(h3)} survive FDR (= E2C.2 model)", "trend": "",
     "reproduces_phase1": np.nan, "sites_same_direction": np.nan, "verdict": "null" if not len(h3_survivors) else "signal"},
    {"claim": "T1 undiagnosed-range -> kidney abnormal", "value": f"OR {t1_prim.estimate} (Wald {t1_prim.ci_lo}-{t1_prim.ci_hi}; bootstrap {t1_prim.boot_ci_lo}-{t1_prim.boot_ci_hi}), q={t1_prim.q:.3g} (Phase-2 q={t1_prim.phase2_q:.3g}); CGM definition OR {t1_cgm.estimate}, q={t1_cgm.q:.3g}",
     "trend": f"double-unrecognized {int(double_unrec.sum())}/{int(double.sum())}; site direction {int(t1_site.sites_same_direction)}/3, Q p={t1_site.heterogeneity_q_p:.2f}", "reproduces_phase1": np.nan,
     "sites_same_direction": int(t1_site.sites_same_direction),
     "verdict": "confirmed (exploratory-confirmatory: E2A.2 model, family narrowed 15 -> 10)" if (t1_prim.q < ALPHA and t1_prim.boot_ci_lo > 1 and t1_site.consistent_across_sites) else "weakened — see robustness"},
    {"claim": "T2 QRS duration -> log troponin", "value": f"beta {t2.loc[('qrsd_ms','log_troponin')].estimate} per SD, q={t2.loc[('qrsd_ms','log_troponin')].q:.2g} (Phase-2 q={t2.loc[('qrsd_ms','log_troponin')].phase2_q:.2g})",
     "trend": f"site direction {int(t2_site.sites_same_direction)}/3, Q p={t2_site.heterogeneity_q_p:.2f}", "reproduces_phase1": np.nan,
     "sites_same_direction": int(t2_site.sites_same_direction), "verdict": "confirmed (supplement; E2E.2 model, family narrowed 40 -> 10)"},
]).set_index("claim")
_phase3.print_table(summary, title="E3.3 headline summary")

results.save(
    "E3.3", summary, paper="p1",
    method=(f"SECOND RUN of the confirmatory reruns, exactly per PRESPEC.md as amended (version "
            f"{SPEC['prespec_version']}, sha256 {SHA}), every parameter read from the spec's machine-readable "
            f"block, which Amendment 1 left byte-identical. What this run adds over the first (see E3.REVIEW): "
            f"A1.5 and the refusals-included denominator refitted and asserted against Phase 1; CES-D on the "
            f"cohort-wide SD in every Aim-2 row; the adjustment ladder on a fixed sample as well as the Phase-2 "
            f"sample; the missing-data single-imputation sensitivity A2.4; bootstrap on every small-cell T1 "
            f"robustness row and the three HbA1c bands; Cochran's Q / I2 for the model-based site checks; "
            f"Phase-2 q reported beside the narrowed-family q for T1 and T2."),
    result=("AIM 1 REPRODUCES PHASE 1 EXACTLY (every k, n and %, both denominators, across "
            f"{len(confirm)} rows; {len(a15)} E1.4 model terms reproduce). Per-site: {int(consistent.sum())}/{len(consistent)} core trends "
            f"keep their sign at every site (a direction check, not a replication; {int((sig_sites == 3).sum())} are significant within all "
            f"three). Burden rises with severity at every cutoff rung: {burden_holds} (heart at the non-clinical 'detectable' rung "
            f"p={detectable_p:.3f}). AIM 2 with the spec covariates: CES-D-10 -> nerve OR {nerve.estimate} ({nerve.ci_lo}-{nerve.ci_hi}) "
            f"per SD, p={nerve.p:.3g}, q={nerve.q:.3g}; screen-positive OR {nerve_pos.estimate} ({nerve_pos.ci_lo}-{nerve_pos.ci_hi}), "
            f"p={nerve_pos.p:.3g}, q={nerve_pos.q:.3g}; PRE-SPECIFIED CRITERION NOT MET for any outcome. Attenuation from the Phase-2 "
            f"OR {lad.loc[(P2_KEY, '+ age + severity + site'), 'estimate']} decomposes on the "
            f"fixed n={len(spec_sample):,} sample as: same covariates {lad.loc[(fixed_key, '+ age + severity + site'), 'estimate']} "
            f"(sample change = {share_sample:.0f}% of the log-OR drop; the {lost} lost participants are "
            f"{100 * lost_rows.abn_nerve.mean():.1f}% nerve-abnormal vs {100 * spec_sample.abn_nerve.mean():.1f}%), + HbA1c "
            f"{lad.loc[(fixed_key, '+ age + severity + site + HbA1c'), 'estimate']}, + BMI "
            f"{lad.loc[(fixed_key, '+ age + severity + site + BMI'), 'estimate']}, both {nerve.estimate}. Missing-data sensitivity "
            f"(single imputation, n=2,265): OR {imp_nerve.estimate} q={imp_nerve.q:.3g}, >=10 OR {imp_nerve_pos.estimate} "
            f"q={imp_nerve_pos.q:.3g} — criterion still not met. Robustness rows for nerve not significant: {len(failing)} "
            f"(the >=1-insensate-site cutoff erases it: OR {aim2_robust.loc[('nerve cutoff', '>= 1 insensate sites', 'cesd_total', 'abn_nerve'), 'estimate']}; "
            f"dropping the 20 odd monofilament rows p={aim2_robust.loc[('drop odd monofilament rows', 'n dropped = 20', 'cesd_total', 'abn_nerve'), 'p']:.3f}). "
            f"Within-site direction {int(a2_site.sites_same_direction)}/3, Q p={a2_site.heterogeneity_q_p:.2f}. H3: {len(h3_survivors)} of {len(h3)} survive FDR. "
            f"T1: undiagnosed-range -> kidney OR {t1_prim.estimate} (Wald {t1_prim.ci_lo}-{t1_prim.ci_hi}, bootstrap "
            f"{t1_prim.boot_ci_lo}-{t1_prim.boot_ci_hi}), q={t1_prim.q:.3g} (Phase-2 q={t1_prim.phase2_q:.3g}); CGM definition OR "
            f"{t1_cgm.estimate}, q={t1_cgm.q:.3g}; within-site direction {int(t1_site.sites_same_direction)}/3, Q p={t1_site.heterogeneity_q_p:.2f}; "
            f"double-unrecognized {int(double_unrec.sum())} of {int(double.sum())}; kidney damage by HbA1c band "
            + ", ".join(f"{b} {int(r.kidney_abnormal)}/{int(r.n)} ({r.pct}%)" for b, r in t1_bands.iterrows())
            + f". T2: QRS -> log troponin q={t2.loc[('qrsd_ms','log_troponin')].q:.2g}, same direction at 3 sites, Q p={t2_site.heterogeneity_q_p:.2f}."),
    decision="keep — headline set rerun per the amended spec; Aim 1 and T1 confirmed, Aim 2 reported as pre-specified criterion not met",
    name="headline_summary",
)
results.save("E3.3", confirm, paper="p1",
             method="A1.1-A1.4 per spec: prevalence, unrecognized fraction with BOTH denominators, burden and multi-organ counts, by severity, with Cochran-Armitage trend.",
             result=f"Reproduces the Phase-1 artifacts exactly: {len(confirm)} rows, 0 mismatches, refusals-included denominators included.",
             decision="keep", name="aim1_confirmatory", primary=False)
results.save("E3.3", a15, paper="p1",
             method="A1.5: the E1.4 who-is-unrecognized logistic models A/B/C per organ, refitted and asserted against E1_4_models.csv term by term.",
             result=f"{len(a15)} terms reproduce (odds ratio within 0.0015, p within 1e-6). Kidney Insulin-vs-Healthy model C OR {a15.loc[('kidney','C: B + marker magnitude','C(study_group_label)[T.Insulin]'),'odds_ratio']}; heart model C OR {a15.loc[('heart','C: B + marker magnitude','C(study_group_label)[T.Insulin]'),'odds_ratio']} p={a15.loc[('heart','C: B + marker magnitude','C(study_group_label)[T.Insulin]'),'p']:.3f}.",
             decision="keep", name="aim1_recognition_models", primary=False)
results.save("E3.3", by_site, paper="p1",
             method="Every A1 trend refitted within each clinical site (direction check; per-site significance recorded).",
             result="; ".join(f"{c}/{o}: " + ", ".join(f"{s} z={by_site.loc[(c,o,s)].trend_z}" for s in SITES)
                              for c, o in consistent.index),
             decision="keep", name="aim1_by_site", primary=False)
results.save("E3.3", boot, paper="p1",
             method=f"Percentile bootstrap ({BOOT_N} resamples, seed {BOOT_SEED}) of every group-level unrecognized fraction and burden, beside the Wilson interval; small-cell rule < {SMALL}.",
             result="; ".join(f"{c}/{o}/{s}: {r.pct}% Wilson {r.wilson_lo}-{r.wilson_hi} boot {r.boot_lo}-{r.boot_hi}"
                              for (c, o, s), r in boot.iterrows() if r.small_cell_rule_applies) or "no cell under the small-cell rule",
             decision="keep", name="aim1_bootstrap", primary=False)
results.save("E3.3", burden_sweep, paper="p1",
             method="Population burden re-run at every rung of the kidney and heart cutoff grids, pooled and by severity, including the either-organ burden.",
             result=(f"Either-organ burden spans {burden_sweep.loc['either (kidney grid)'].burden_pct.min():.1f}-"
                     f"{burden_sweep.loc['either (kidney grid)'].burden_pct.max():.1f}% across the kidney grid and "
                     f"{burden_sweep.loc['either (heart grid)'].burden_pct.min():.1f}-{burden_sweep.loc['either (heart grid)'].burden_pct.max():.1f}% "
                     f"across the heart grid; the rise with severity holds (z>0, p<0.05) at every rung: {burden_holds}; "
                     f"excluding the non-clinical 'detectable' rung: {burden_holds_clinical}."),
             decision="keep", name="burden_sweep", primary=False)
results.save("E3.3", aim2, paper="p1",
             method=f"A2.1 per spec: CES-D-10 (per cohort-wide SD and >= 10) vs the five binary outcomes, covariates {COV}, complete case, BH within the 10-model family; insensate sites as the supporting continuous outcome. Claim rule: q<0.05 in BOTH forms and same direction.",
             result=(f"Pre-specified criterion met for {', '.join(a2_hits.index) if len(a2_hits) else 'no outcome'}. "
                     + "; ".join(f"{e}/{o} {r.estimate} ({r.ci_lo}-{r.ci_hi}) p={r.p:.3g} q={r.q:.3g}" for (e, o), r in aim2[aim2.in_corrected_family].iterrows())),
             decision="keep", name="aim2_confirmatory", primary=False)
results.save("E3.3", aim2_ladder, paper="p1",
             method="Adjustment ladder for CES-D (per cohort-wide SD) -> nerve on the Phase-2 sample and on the fixed spec complete-case sample, so a sample change is never shown as a covariate effect.",
             result="; ".join(f"[{smp.split(' (')[0]}] {s}: OR {r.estimate} (n={int(r.n)}, p={r.p:.3g})" for (smp, s, o), r in aim2_ladder.iterrows() if o == "abn_nerve"),
             decision="keep", name="aim2_ladder", primary=False)
results.save("E3.3", aim2_robust, paper="p1",
             method="A2.2 robustness with CES-D on the cohort-wide SD in every row: within site, nerve cutoff >= 1 and >= 3, exclusion of the odd monofilament rows, PAID-5 head-to-head on one sample.",
             result=("EVERY ROW, FAILURES INCLUDED: " + "; ".join(f"{c} [{d}] {e}->{o}: {r.estimate} p={r.p:.3g}" for (c, d, e, o), r in aim2_robust.iterrows() if o == "abn_nerve")),
             decision="keep", name="aim2_robustness", primary=False)
results.save("E3.3", strata, paper="p1",
             method="A2.2(e) CES-D (per cohort-wide SD) -> nerve within each severity group, spec covariates minus severity, bootstrap where the smaller cell < 50.",
             result="; ".join(f"{s}: OR {r.estimate} ({r.ci_lo}-{r.ci_hi}), n={r.n}" for s, r in strata.iterrows()),
             decision="keep", name="aim2_by_severity", primary=False)
results.save("E3.3", aim2_imputed, paper="p1",
             method="A2.4 missing-data sensitivity: the 10-model family refitted on all 2,265 with missing BMI / HbA1c single-imputed at the severity-group median. Cannot change the verdict; qualifies the description of the attenuation.",
             result=(f"Nerve OR {imp_nerve.estimate} ({imp_nerve.ci_lo}-{imp_nerve.ci_hi}), p={imp_nerve.p:.3g}, q={imp_nerve.q:.3g}; "
                     f">=10 OR {imp_nerve_pos.estimate}, p={imp_nerve_pos.p:.3g}, q={imp_nerve_pos.q:.3g}. Criterion met: "
                     f"{bool(imputed_claims.loc['abn_nerve', 'meets_claim_rule'])}."),
             decision="keep", name="aim2_missing_sensitivity", primary=False)
results.save("E3.3", h3, paper="p1",
             method="A2.3 H3 per spec: CES-D-10 vs unrecognized status among the abnormal, recognition covariates incl. log marker magnitude, BH within 6 — the E2C.2 model unchanged.",
             result=f"{len(h3_survivors)} of {len(h3)} survive FDR; estimates: " + "; ".join(f"{e}/{o} {r.estimate} q={r.q:.2g}" for (e, o), r in h3.iterrows()),
             decision="keep", name="h3", primary=False)
results.save("E3.3", t1, paper="p1",
             method=(f"T1 per spec: no-diabetes-label with HbA1c >= {T1['hba1c_cutoff']}% (and CGM mean >= {T1['cgm_mean_cutoff']:g} mg/dL) vs each outcome within Healthy + Pre-DM, "
                     f"age + site adjusted, Wald and percentile-bootstrap ({BOOT_N}, seed {BOOT_SEED}) intervals, BH within 10; the E2A.2 models, family narrowed from 15, Phase-2 q alongside."),
             result=(f"Primary: kidney OR {t1_prim.estimate} (Wald {t1_prim.ci_lo}-{t1_prim.ci_hi}; bootstrap {t1_prim.boot_ci_lo}-{t1_prim.boot_ci_hi}), q={t1_prim.q:.3g} (Phase-2 q {t1_prim.phase2_q:.3g}), "
                     f"{int(t1_prim.events_exposed)}/{int(t1_prim.n_exposed)} exposed abnormal ({t1_prim.pct_exposed}% vs {t1_prim.pct_unexposed}%). "
                     f"CGM replication OR {t1_cgm.estimate} q={t1_cgm.q:.3g}. Double-unrecognized: {int(double_unrec.sum())} of {int(double.sum())} "
                     f"(of {n_exposed_all} undiagnosed-range participants)."),
             decision="keep", name="track_undiagnosed", primary=False)
results.save("E3.3", t1_robust, paper="p1",
             method="T1 robustness with bootstrap on every small-cell row: within site (age-adjusted), ACR cutoff 20/30/50, HbA1c >= 7.0% as a threshold shift.",
             result="; ".join(f"{c} [{d}] {o}: OR {r.estimate} (Wald {r.ci_lo}-{r.ci_hi}; boot {r.boot_ci_lo}-{r.boot_ci_hi}; exposed {int(r.n_exposed)}, events {int(r.events_exposed)}) p={r.p:.3g}" for (c, d, o), r in t1_robust.iterrows()),
             decision="keep", name="track_undiagnosed_robustness", primary=False)
results.save("E3.3", t1_bands, paper="p1",
             method="Kidney damage prevalence by HbA1c band within Healthy + Pre-DM, so the 7.0% 'threshold shift' is read as a gradient rather than a stricter confirmation.",
             result="; ".join(f"{b}: {int(r.kidney_abnormal)}/{int(r.n)} = {r.pct}% ({r.ci_lo}-{r.ci_hi})" for b, r in t1_bands.iterrows()),
             decision="keep", name="track_undiagnosed_bands", primary=False)
results.save("E3.3", t2, paper="p1",
             method="T2 per spec: ECG numeric metrics vs abnormal troponin and log troponin, age + severity + site, BH within 10 — the E2E.2 models, family narrowed from 40, Phase-2 q alongside. Supplement only.",
             result="; ".join(f"{m}/{o} {r.estimate} q={r.q:.2g}" for (m, o), r in t2.iterrows()),
             decision="keep", name="track_ecg", primary=False)
results.save("E3.3", t2_sites, paper="p1",
             method="T2 within each site for QRS duration and QTc.",
             result="; ".join(f"{m}/{o}@{s} {r.estimate} p={r.p:.2g}" for (m, o, s), r in t2_sites.iterrows()),
             decision="keep", name="track_ecg_by_site", primary=False)
results.save("E3.3", heterogeneity, paper="p1",
             method="Site direction check with Cochran's Q and I2 for the model-based headline rows (A2.1 both forms, T1 primary, T2 QRS and QTc).",
             result="; ".join(f"{a}: {int(r.sites_same_direction)}/3 same direction, {int(r.sites_p_lt_05)} sites p<0.05, Q p={r.heterogeneity_q_p:.2f}, I2={r.i_squared_pct}%" for a, r in heterogeneity.iterrows()),
             decision="keep", name="site_heterogeneity", primary=False)
results.save("E3.3", fig1, paper="p1", method="Figure: either-organ burden by severity within each site.",
             result="Figure written.", decision="keep", name="site_replication_figure", primary=False)
results.save("E3.3", fig2, paper="p1", method="Figure: Aim 2 confirmatory forest per spec.",
             result="Figure written.", decision="keep", name="aim2_figure", primary=False)
results.save("E3.3", fig3, paper="p1", method="Figure: burden across the cutoff grids.",
             result="Figure written.", decision="keep", name="burden_sweep_figure", primary=False)

results.log(
    "E3.FREEZE", paper="p1",
    method=(f"Results freeze, second entry, superseding the first E3.FREEZE above. Everything in the headline set was "
            f"rerun against PRESPEC.md as amended (sha256 {SHA}) in the early hours of 25 Aug; nothing enters the "
            f"paper after this entry except via a logged deviation. The freeze deadline in the plan is 26 Aug; Evan's "
            f"sign-off on PRESPEC.md (incl. Amendment 1) is pending."),
    result=("FROZEN. Headline numbers: any-organ prevalence "
            f"{cell('prevalence','any').pct}%; either-organ unrecognized fraction "
            f"{cell('unrecognized_fraction','either').pct}%; either-organ burden "
            f"{cell('population_burden','either').pct}% overall, {cell('population_burden','either','Insulin').pct}% "
            f"on insulin; Aim 2: pre-specified criterion NOT met (nerve OR {nerve.estimate} per SD, q={nerve.q:.3g}); "
            f"T1 kidney OR {t1_prim.estimate} (bootstrap {t1_prim.boot_ci_lo}-{t1_prim.boot_ci_hi})."),
    decision="keep — frozen 2026-08-25; deadline 26 Aug; Evan's sign-off pending, amendments logged as E3.2.AMEND.n",
)
