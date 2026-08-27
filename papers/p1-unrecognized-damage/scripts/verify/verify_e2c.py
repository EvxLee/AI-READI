"""Independent verification of Track C (E2C.1, E2C.2, E2C.3).

Rebuilds the exposures and outcomes from the raw cached CSVs and re-fits every
headline model through a different statsmodels API -- `sm.Logit` / `sm.OLS` on a
hand-built design matrix, rather than the formula interface's GLM that the
runners use. That catches the realistic failure modes: a mis-coded reference
level, a covariate silently dropped by a formula, a standardisation applied to
the wrong column, or an exposure scaled by an SD computed on the wrong sample.

Does not import `aireadi`. In particular it rebuilds the urine-albumin floor
substitution independently, because that is a Phase-2 analysis choice made in
`associations` and an artifact that only agrees with itself proves nothing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

import _raw

print("=" * 78)
print("VERIFY E2C — Track C, psychosocial exposures vs measured damage")
print("=" * 78)

d = _raw.build()

# ── Exposures and outcomes, rebuilt from raw ────────────────────────────
obs = pd.read_csv(_raw.DS / "clinical_data/observation.csv", low_memory=False,
                  usecols=["person_id", "observation_source_value", "value_as_number"])
obs["k"] = (obs.observation_source_value.astype(str).str.split(",", n=1).str[0]
            .str.strip().str.lower())
v = pd.to_numeric(obs.value_as_number, errors="coerce")
obs["v"] = v.mask(v.isin(_raw.SPECIAL))

d["cesd"] = obs[obs.k == "cestl"].groupby("person_id").v.first()
d["paid"] = obs[obs.k == "paidscore"].groupby("person_id").v.first()
d["cesd_pos"] = (d.cesd >= 10).astype(float).mask(d.cesd.isna())
d["paid_pos"] = (d.paid >= 8).astype(float).mask(d.paid.isna())

# Urine-albumin reporting floor, re-derived rather than taken on trust: confirm
# the zeros are NOT below-detection rows and that 0.01 really is the smallest
# positive value, then substitute half of it.
meas = pd.read_csv(_raw.DS / "clinical_data/measurement.csv", low_memory=False)
meas["k"] = (meas.measurement_source_value.astype(str).str.split(",", n=1).str[0]
             .str.strip().str.lower())
alb_rows = meas[meas.k == "import_urine_albumin"].copy()
alb_rows["v"] = pd.to_numeric(alb_rows.value_as_number, errors="coerce")
zero_ops = set(pd.to_numeric(
    alb_rows.loc[alb_rows.v.eq(0), "operator_concept_id"], errors="coerce").dropna())
_raw.check("zero-albumin rows are NOT flagged below-detection",
           4171756 not in zero_ops, True)
_raw.check("smallest positive urine albumin is 0.01 mg/dL",
           round(float(alb_rows.loc[alb_rows.v > 0, "v"].min()), 4), 0.01, tol=1e-9)
_raw.check("count of zero-albumin participants", int((d.alb == 0).sum()), 254)

alb_floored = d.alb.mask(d.alb.eq(0), 0.01 / 2)
acr_floored = alb_floored / d.crt.where(d.crt > 0) * 1000
d["log_acr"] = np.log(acr_floored.where(acr_floored > 0))
d["log_trop"] = np.log(d.trop.where(d.trop > 0))
d["missed"] = 10 - d.mono_worse
_raw.check("floored log ACR keeps all measured participants",
           int(d.log_acr.notna().sum()), int(d.acr.notna().sum()))
_raw.check("abn_kidney unchanged by the substitution", int(d.abn_kidney.sum()), 319)

d["abn_any"] = np.where(d.n_abn.isna(), np.nan, (d.n_abn > 0).astype(float))
d["abn_multi"] = np.where(d.n_abn.isna(), np.nan, (d.n_abn >= 2).astype(float))


def refit(frame, outcome, exposure, *, covariates=("age", "group", "site"),
          gaussian=False, scale=True, extra=()):
    """Refit via a hand-built design matrix and Logit/OLS. Returns (est, p, n)."""
    cols = ["age"] if "age" in covariates else []
    need = [outcome, exposure] + cols + list(extra)
    m = frame.dropna(subset=need).copy()
    if "group" in covariates:
        m = m[m.group.notna()]
    if "site" in covariates:
        m = m[m.site.notna()]

    x = m[[exposure]].astype(float)
    if scale and set(np.round(m[exposure].dropna().unique(), 6)) - {0.0, 1.0}:
        # SD over the WHOLE cohort, matching the runner -- not over this
        # model's complete cases, which is the easy mistake to make.
        x = x / float(frame[exposure].std())
    parts = [x]
    if cols:
        parts.append(m[cols].astype(float))
    if "group" in covariates:
        parts.append(pd.get_dummies(m.group.astype(str), prefix="g")
                     .drop(columns=["g_Healthy"]))
    if "site" in covariates:
        parts.append(pd.get_dummies(m.site.astype(str), prefix="s")
                     .drop(columns=["s_UAB"]))
    for e in extra:
        parts.append(m[[e]].astype(float))

    X = sm.add_constant(pd.concat(parts, axis=1).astype(float))
    y = m[outcome].astype(float)
    fit = (sm.OLS(y, X).fit() if gaussian else sm.Logit(y, X).fit(disp=0))
    est = fit.params[exposure] if gaussian else float(np.exp(fit.params[exposure]))
    return round(float(est), 4), float(fit.pvalues[exposure]), int(fit.nobs)


# ── E2C.1 ───────────────────────────────────────────────────────────────
print("\nE2C.1 — CES-D-10 vs damage")
sweep = _raw.artifact("E2C_1_sweep.csv").set_index(["exposure", "outcome", "adjustment"])

for exposure, mine in [("cesd_total", "cesd"), ("cesd_positive", "cesd_pos")]:
    for outcome, col, gauss in [("abn_kidney", "abn_kidney", False),
                                ("abn_heart", "abn_heart", False),
                                ("abn_nerve", "abn_nerve", False),
                                ("abn_any", "abn_any", False),
                                ("abn_multi", "abn_multi", False),
                                ("log_acr", "log_acr", True),
                                ("log_troponin", "log_trop", True),
                                ("monofilament_missed", "missed", True)]:
        for adjustment, covariates in [("unadjusted", ()), ("damage", ("age", "group", "site"))]:
            est, p, n = refit(d, col, mine, covariates=covariates, gaussian=gauss)
            want = sweep.loc[(exposure, outcome, adjustment)]
            _raw.check(f"E2C.1 {exposure}/{outcome}/{adjustment} est",
                       est, float(want.estimate), tol=0.004)
            _raw.check(f"E2C.1 {exposure}/{outcome}/{adjustment} n", n, int(want.n))
            _raw.check(f"E2C.1 {exposure}/{outcome}/{adjustment} p",
                       round(p, 5), round(float(want.p), 5), tol=3e-4)

# The four surviving associations are all nerve, and all in the same direction.
surviving = sweep[(sweep.index.get_level_values("adjustment") == "damage")
                  & (sweep.q < 0.05)]
_raw.check("E2C.1 every FDR survivor is a nerve outcome",
           sorted({o for _, o, _ in surviving.index}),
           ["abn_nerve", "monofilament_missed"])
_raw.check("E2C.1 all nerve survivors point the same way (more symptoms, more damage)",
           bool((surviving.estimate > np.where(
               surviving.index.get_level_values("outcome") == "abn_nerve", 1, 0)).all()),
           True)

# FDR recomputed independently.
adjusted = sweep[sweep.index.get_level_values("adjustment") == "damage"].copy()
from statsmodels.stats.multitest import multipletests
_, q_ref, _, _ = multipletests(adjusted.p.to_numpy(), method="fdr_bh")
_raw.check("E2C.1 Benjamini-Hochberg q reproduces statsmodels",
           float(np.max(np.abs(q_ref - adjusted.q.to_numpy()))), 0.0, tol=1e-9)

# Suppression: unadjusted null, age-adjusted significant.
robust = _raw.artifact("E2C_1_nerve_robustness.csv").set_index(["check", "outcome"])
est_u, p_u, _ = refit(d, "abn_nerve", "cesd", covariates=())
est_a, p_a, _ = refit(d, "abn_nerve", "cesd", covariates=("age",))
_raw.check("E2C.1 unadjusted nerve OR", est_u,
           float(robust.loc[("unadjusted", "abn_nerve"), "estimate"]), tol=0.004)
_raw.check("E2C.1 age-only nerve OR", est_a,
           float(robust.loc[("+ age only", "abn_nerve"), "estimate"]), tol=0.004)
_raw.check("E2C.1 unadjusted is null and age-adjusted is not (suppression by age)",
           bool(p_u > 0.05 and p_a < 0.01), True)
_raw.check("E2C.1 CES-D falls with age", bool(d[["cesd", "age"]].corr().iloc[0, 1] < 0), True)
_raw.check("E2C.1 insensate sites rise with age",
           bool(d[["missed", "age"]].corr().iloc[0, 1] > 0), True)

# CAVEATS rows: the result must not depend on them.
both0 = d.mono_l.eq(0) & d.mono_r.eq(0)
asym = ((d.mono_l.eq(0) & d.mono_r.eq(10)) | (d.mono_r.eq(0) & d.mono_l.eq(10)))
_raw.check("E2C.1 both-feet-zero count", int(both0.sum()), 14)
_raw.check("E2C.1 0-vs-10 asymmetric count", int(asym.sum()), 6)
est_drop, p_drop, _ = refit(d[~(both0 | asym)], "abn_nerve", "cesd")
_raw.check("E2C.1 nerve OR dropping all 20 odd rows", est_drop,
           float(robust.loc[("drop both sets (n=20)", "abn_nerve"), "estimate"]), tol=0.004)
_raw.check("E2C.1 association survives dropping the odd rows", bool(p_drop < 0.05), True)

# ── E2C.2 ───────────────────────────────────────────────────────────────
print("\nE2C.2 — CES-D-10 vs unrecognized status")
unrec = _raw.artifact("E2C_2.csv").set_index(["outcome", "exposure", "adjustment"])

d["unrec_either"] = np.where(
    d.abn_kidney.notna() & d.sr_kidney.notna() & d.abn_heart.notna() & d.sr_heart.notna()
    & ((d.abn_kidney == 1) | (d.abn_heart == 1)),
    (((d.abn_kidney == 1) & (d.sr_kidney == 0))
     | ((d.abn_heart == 1) & (d.sr_heart == 0))).astype(float), np.nan)

_raw.check("E2C.2 kidney eligible denominator", int(d.unrec_kidney.notna().sum()), 315)
_raw.check("E2C.2 heart eligible denominator", int(d.unrec_heart.notna().sum()), 447)
_raw.check("E2C.2 either eligible denominator", int(d.unrec_either.notna().sum()), 615)
_raw.check("E2C.2 either numerator matches E1.2", int(d.unrec_either.sum()), 471)

for outcome, marker in [("unrec_kidney", ["log_acr"]), ("unrec_heart", ["log_trop"]),
                        ("unrec_either", ["log_acr", "log_trop"])]:
    for exposure, mine in [("cesd_total", "cesd"), ("cesd_positive", "cesd_pos")]:
        est, p, n = refit(d, outcome, mine, extra=tuple(["hba1c", "bmi"] + marker))
        want = unrec.loc[(outcome, exposure, "recognition+marker")]
        _raw.check(f"E2C.2 {outcome}/{exposure} fully-adjusted est",
                   est, float(want.estimate), tol=0.006)
        _raw.check(f"E2C.2 {outcome}/{exposure} n", n, int(want.n))

_raw.check("E2C.2 nothing survives FDR (H3 null)",
           int((unrec.q < 0.05).sum()), 0)
_raw.check("E2C.2 direction is opposite to H3 for every fully-adjusted model",
           bool((unrec.xs("recognition+marker", level="adjustment").estimate < 1).all()), True)
_raw.check("E2C.2 nerve is absent from the outcome set (E0.GATE)",
           any("nerve" in str(o) for o in unrec.index.get_level_values("outcome")), False)

# ── E2C.3 ───────────────────────────────────────────────────────────────
print("\nE2C.3 — PAID-5 vs damage, and the nerve head-to-head")
paid = _raw.artifact("E2C_3_sweep.csv").set_index(["exposure", "outcome", "adjustment"])
coverage = _raw.artifact("E2C_3_coverage.csv").set_index("study_group_label")
head = _raw.artifact("E2C_3_nerve_head_to_head.csv").set_index(["questionnaire", "outcome"])

for group in _raw.GROUPS:
    got = int((d.paid.notna() & d.group.eq(group)).sum())
    _raw.check(f"E2C.3 PAID-5 coverage {group}", got,
               int(coverage.loc[group, "with_paid"]))
_raw.check("E2C.3 PAID-5 was administered cohort-wide, Healthy included",
           bool(coverage.pct_covered.min() > 90), True)

for exposure, mine in [("paid_total", "paid"), ("paid_positive", "paid_pos")]:
    for outcome, col, gauss in [("abn_kidney", "abn_kidney", False),
                                ("abn_heart", "abn_heart", False),
                                ("abn_nerve", "abn_nerve", False),
                                ("abn_any", "abn_any", False),
                                ("monofilament_missed", "missed", True)]:
        est, p, n = refit(d, col, mine, gaussian=gauss)
        want = paid.loc[(exposure, outcome, "damage")]
        _raw.check(f"E2C.3 {exposure}/{outcome} adjusted est", est,
                   float(want.estimate), tol=0.004)
        _raw.check(f"E2C.3 {exposure}/{outcome} n", n, int(want.n))

_raw.check("E2C.3 PAID-5 has no FDR survivor", int((paid.q < 0.05).sum()), 0)

# Head-to-head on one sample: CES-D holds, PAID-5 does not, and mutual
# adjustment does not rescue PAID-5.
same = d.dropna(subset=["paid", "cesd", "abn_nerve", "age"])
same = same[same.group.notna() & same.site.notna()]
_raw.check("E2C.3 head-to-head sample size", len(same),
           int(head.loc[("CES-D-10 total", "abn_nerve"), "n"]))
for label, exposure, other in [("cesd_total | mutually adjusted", "cesd", "paid"),
                               ("paid_total | mutually adjusted", "paid", "cesd")]:
    est, p, n = refit(same, "abn_nerve", exposure, extra=(other,))
    _raw.check(f"E2C.3 {label} nerve OR", est,
               float(head.loc[(label, "abn_nerve"), "estimate"]), tol=0.006)
cesd_p = float(head.loc[("cesd_total | mutually adjusted", "abn_nerve"), "p"])
paid_p = float(head.loc[("paid_total | mutually adjusted", "abn_nerve"), "p"])
_raw.check("E2C.3 nerve signal is specific to CES-D, not diabetes distress",
           bool(cesd_p < 0.01 and paid_p > 0.05), True)

_raw.report("E2C")
