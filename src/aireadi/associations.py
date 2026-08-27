"""The Phase-2 standard recipe: one exposure against the damage outcomes.

Phase 2 asks the same question of eight different exposure families -- does
this variable track measured organ damage? -- so the recipe lives here once
rather than being retyped in seven runners that would then drift apart.

The recipe, fixed before Track C ran (`E2.0`):

1. **Unadjusted** association with each damage outcome.
2. **Adjusted** for age + severity group + site, the project default. Severity
   confounds nearly everything in this cohort, so an unadjusted association is
   reported only to show what adjustment does to it.
3. **+ HbA1c** where the exposure is not itself a glycaemic measure.
4. A **severity-stratified** look, because "the healthy group is not a clean
   control" -- a quarter of them already carry an abnormal result.

Three things this module does that a hand-rolled version tends to miss:

* **Continuous exposures are scaled to one standard deviation**, computed once
  on the whole cohort rather than per model, so an odds ratio for daily steps
  and one for stress level are directly comparable and do not silently change
  scale when the complete-case sample shifts between outcomes. The SD used is
  reported in every row.
* **Every row carries its own n.** Complete-case samples differ a lot across
  these exposures (SpO2 reaches 1,628 participants, CES-D 2,277), and a table
  that hides that invites comparing two effects fitted on different cohorts.
* **False-discovery control within each experiment.** Phase 2 fits hundreds of
  models. They are exploratory and stay labelled as such, but Phase 3 ranks
  findings off this log, and a ranking built on raw p-values from a sweep this
  wide would promote noise. `q` is Benjamini-Hochberg within whatever family
  the caller declares -- normally one experiment's adjusted models.

Nothing here decides what counts as damage; that is `thresholds`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from .thresholds import ORGANS, UNRECOGNIZED_ORGANS

__all__ = [
    "BINARY_OUTCOMES",
    "CONTINUOUS_OUTCOMES",
    "ADJUSTMENTS",
    "add_outcome_columns",
    "bootstrap_ci",
    "fdr",
    "fit",
    "sweep",
    "stratified",
]

# ── The declared outcome set ────────────────────────────────────────────
#
# Fixed once so no track can quietly test a different set of outcomes and
# report the best of them. Nerve is present for prevalence-style outcomes and
# absent from anything about recognition, per E0.GATE.
BINARY_OUTCOMES = {
    "abn_kidney": "Kidney abnormal (ACR >= 30 mg/g)",
    "abn_heart": "Heart abnormal (hs-cTnT >= 14 ng/L)",
    "abn_nerve": "Nerve abnormal (>= 2 insensate sites)",
    "abn_any": "Any of the three organs abnormal",
    "abn_multi": "Two or more organs abnormal",
}

# Marker magnitude, for the "continuous as well as binary" half of the recipe.
# Logged because ACR and troponin are both heavily right-skewed; the
# monofilament count is not, and is used as-is.
CONTINUOUS_OUTCOMES = {
    "log_acr": "log urine ACR (mg/g)",
    "log_troponin": "log hs-cTnT (ng/L)",
    "monofilament_missed": "Insensate sites, worse foot (0-10)",
}

# ── Urine albumin's reporting floor ─────────────────────────────────────
#
# 254 participants have a urine albumin of exactly 0. They are NOT flagged
# below-detection -- every albumin row carries operator 4172703 ("=") -- and the
# smallest positive value in the release is 0.01 mg/dL, so a zero is a real
# measurement rounded down below the assay's reporting granularity, not a
# missing one.
#
# This matters because a bare `log(ACR)` drops all 254, and they are not a
# random 11%: 14.5% of the Healthy group has a zero against 8.5% of the Insulin
# group. Dropping them would remove the least-damaged participants
# preferentially from the healthy end and bias every continuous kidney
# association in Phase 2 toward a flatter severity gradient.
#
# Standard substitution: half the reporting floor. That maps a zero albumin to
# 0.005 mg/dL, and at the cohort's median urine creatinine gives ACR ~ 0.076
# mg/g -- essentially the smallest positive ACR actually observed (0.0749),
# which is the sanity check that the floor was read correctly.
#
# No Phase-1 number is affected: E1.4 is the only Phase-1 analysis using log
# ACR and it runs only on abnormal participants (ACR >= 30 mg/g), where no
# zeros exist. `log_acr_positive` keeps the drop-the-zeros version so the
# sensitivity line can be reported rather than argued.
URINE_ALBUMIN_FLOOR = 0.01
ACR_UNIT_SCALE = 1000

# Covariate sets. "damage" is the project default; "recognition" adds the two
# covariates the E1.4 re-reading (17 Aug) established are mandatory for any
# analysis of unrecognized status -- marker magnitude, which dominates it, and
# age, the only term holding across all three heart models.
ADJUSTMENTS = {
    "unadjusted": [],
    "damage": ["age", "C(study_group_label)", "C(clinical_site)"],
    "damage+hba1c": ["age", "C(study_group_label)", "C(clinical_site)", "hba1c"],
    "recognition": ["age", "C(study_group_label)", "C(clinical_site)",
                    "hba1c", "bmi"],
}

_MONOFILAMENT_MAX = 10


def add_outcome_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add the derived outcome columns the recipe expects.

    `abn_any` and `abn_multi` come off `n_organs_abnormal`, which is already
    NaN unless every organ is evaluable -- so a participant missing one marker
    cannot enter as a clean negative on "any organ".
    """
    out = df.copy()
    n = out["n_organs_abnormal"]
    out["abn_any"] = n.gt(0).astype(float).mask(n.isna())
    out["abn_multi"] = n.ge(2).astype(float).mask(n.isna())

    # ACR with the albumin reporting floor substituted -- see
    # URINE_ALBUMIN_FLOOR above for why dropping the 254 zeros is not neutral.
    albumin = out["urine_albumin"].mask(
        out["urine_albumin"].eq(0), URINE_ALBUMIN_FLOOR / 2)
    creatinine = out["urine_creatinine"].where(out["urine_creatinine"] > 0)
    acr_floored = albumin / creatinine * ACR_UNIT_SCALE
    # Only the zeros are substituted; every other participant keeps the ACR the
    # cohort builder produced, so the two columns cannot disagree on anyone else.
    out["acr_floored"] = out["acr_mg_g"].mask(out["acr_mg_g"].eq(0), acr_floored)

    out["log_acr"] = np.log(out["acr_floored"].where(out["acr_floored"] > 0))
    out["log_acr_positive"] = np.log(out["acr_mg_g"].where(out["acr_mg_g"] > 0))
    out["log_troponin"] = np.log(out["troponin_t"].where(out["troponin_t"] > 0))
    out["monofilament_missed"] = _MONOFILAMENT_MAX - out["monofilament_min"]
    return out


def fdr(p: pd.Series | list[float]) -> np.ndarray:
    """Benjamini-Hochberg q-values, NaN-safe.

    Missing p-values (a model that failed to converge) stay NaN and are left
    out of the ranking rather than being treated as 1.0, which would inflate
    every other q in the family.
    """
    p = pd.Series(p, dtype="float64")
    q = pd.Series(np.nan, index=p.index, dtype="float64")
    ok = p.notna()
    if not ok.any():
        return q.to_numpy()

    vals = p[ok].sort_values()
    m = len(vals)
    raw = vals.to_numpy() * m / np.arange(1, m + 1)
    # Enforce monotonicity from the largest p downwards, the standard step-up.
    q.loc[vals.index] = np.minimum.accumulate(raw[::-1])[::-1].clip(max=1.0)
    return q.to_numpy()


def fit(
    df: pd.DataFrame,
    outcome: str,
    exposure: str,
    covariates: list[str] | None = None,
    *,
    family: str = "binomial",
    scale_by_sd: bool = True,
) -> dict:
    """Fit one model and return the exposure's effect as a single row.

    `family="binomial"` gives an odds ratio, `"gaussian"` a linear
    coefficient. A continuous exposure is expressed per one cohort-wide
    standard deviation unless `scale_by_sd=False`; a 0/1 exposure never is.

    Returns a dict rather than a fitted model on purpose: the runners assemble
    these into a tidy table, and keeping the model objects around invites
    reaching back into them for a number that never reaches the artifact.
    """
    covariates = list(covariates or [])
    binary_exposure = _is_binary(df[exposure])
    sd = float(df[exposure].std()) if not binary_exposure else float("nan")

    work = df.copy()
    term = exposure
    if scale_by_sd and not binary_exposure and sd and np.isfinite(sd):
        term = f"{exposure}_z"
        work[term] = work[exposure] / sd

    formula = f"{outcome} ~ " + " + ".join([term] + covariates)
    row = {
        "outcome": outcome, "exposure": exposure, "term": term,
        "n": 0, "estimate": np.nan, "ci_lo": np.nan, "ci_hi": np.nan,
        "p": np.nan, "sd_unit": sd, "scale": "per 1 SD" if term != exposure
        else ("per unit" if not binary_exposure else "yes vs no"),
    }

    try:
        if family == "binomial":
            model = smf.glm(formula, data=work, family=sm.families.Binomial())
        elif family == "gaussian":
            model = smf.ols(formula, data=work)
        else:
            raise ValueError(f"family must be 'binomial' or 'gaussian', got {family!r}")
        res = model.fit()
    except Exception as exc:                       # noqa: BLE001 - logged, not raised
        # A failure is a result: it goes in the table as NaN with a reason, so
        # a track that silently lost half its models cannot look complete.
        row["note"] = f"fit failed: {type(exc).__name__}"
        return row

    if term not in res.params.index:
        row["note"] = "exposure dropped from design (no variation?)"
        return row

    ci = res.conf_int()
    est, lo, hi = res.params[term], ci.loc[term, 0], ci.loc[term, 1]
    if family == "binomial":
        est, lo, hi = np.exp([est, lo, hi])

    row.update({
        "n": int(res.nobs),
        "estimate": round(float(est), 4),
        "ci_lo": round(float(lo), 4),
        "ci_hi": round(float(hi), 4),
        "p": float(res.pvalues[term]),
        "note": "",
    })
    return row


def sweep(
    df: pd.DataFrame,
    exposures: dict[str, str],
    *,
    outcomes: dict[str, str] | None = None,
    adjustments: list[str] | None = None,
    family_for: dict[str, str] | None = None,
    fdr_within: str = "damage",
) -> pd.DataFrame:
    """The standard recipe: every exposure against every damage outcome.

    `exposures` maps column -> readable label. `outcomes` defaults to the
    binary set plus the three marker magnitudes. `adjustments` names keys of
    `ADJUSTMENTS`. `fdr_within` names the adjustment whose p-values get
    Benjamini-Hochberg correction -- the primary family, normally the default
    age + severity + site models. Other rows keep a NaN q so nobody reads a
    correction that was not applied.
    """
    outcomes = outcomes or {**BINARY_OUTCOMES, **CONTINUOUS_OUTCOMES}
    adjustments = adjustments or ["unadjusted", "damage"]
    family_for = family_for or {}

    rows = []
    for exposure, exposure_label in exposures.items():
        if exposure not in df.columns:
            raise KeyError(f"exposure {exposure!r} is not a column")
        for outcome, outcome_label in outcomes.items():
            fam = family_for.get(
                outcome, "gaussian" if outcome in CONTINUOUS_OUTCOMES else "binomial")
            for adjustment in adjustments:
                covariates = _drop_self(ADJUSTMENTS[adjustment], exposure)
                row = fit(df, outcome, exposure, covariates, family=fam)
                row.update({
                    "exposure_label": exposure_label,
                    "outcome_label": outcome_label,
                    "adjustment": adjustment,
                    "family": fam,
                })
                rows.append(row)

    out = pd.DataFrame(rows)
    out["q"] = np.nan
    primary = out["adjustment"] == fdr_within
    if primary.any():
        out.loc[primary, "q"] = fdr(out.loc[primary, "p"])

    cols = ["exposure", "exposure_label", "outcome", "outcome_label", "adjustment",
            "family", "scale", "sd_unit", "n", "estimate", "ci_lo", "ci_hi", "p",
            "q", "note"]
    return out[cols].set_index(["exposure", "outcome", "adjustment"])


def stratified(
    df: pd.DataFrame,
    exposure: str,
    outcome: str,
    *,
    covariates: list[str] | None = None,
    family: str = "binomial",
    group: str = "study_group_label",
    bootstrap_below: int = 50,
    n_boot: int = 2000,
    seed: int = 20260817,
    scale_by_sd: bool = True,
) -> pd.DataFrame:
    """The same association fitted within each severity group.

    `scale_by_sd=False` fits the exposure as given, for a column the caller has
    already scaled by the COHORT-WIDE SD. With the default, `fit` rescales by
    the stratum's own SD, so an Insulin-group odds ratio is per a unit 13%
    larger than the pooled one -- which is what PRESPEC §4.2 forbids.

    Severity-stratified estimates are where this cohort's small cells bite:
    the Insulin group is n ~ 258 and its abnormal-organ cells run 43-77. Where
    the smaller outcome cell is under `bootstrap_below`, a percentile bootstrap
    interval is computed alongside the Wald one and both are reported, because
    a Wald interval on a handful of events is not trustworthy and quietly
    replacing it would hide that a cell is thin.
    """
    covariates = _drop_self(covariates if covariates is not None
                            else ADJUSTMENTS["damage"], exposure)
    # Severity is the stratifying variable, so it cannot also be a covariate.
    covariates = [c for c in covariates if group not in c]

    levels = (list(df[group].cat.categories)
              if isinstance(df[group].dtype, pd.CategoricalDtype)
              else sorted(df[group].dropna().unique()))

    rows = []
    for level in levels:
        sub = df[df[group] == level]
        row = fit(sub, outcome, exposure, covariates, family=family, scale_by_sd=scale_by_sd)
        row["stratum"] = str(level)

        used = sub.dropna(subset=[outcome, exposure] + _plain(covariates))
        cells = used[outcome].value_counts()
        smaller = int(cells.min()) if len(cells) else 0
        row["smaller_cell"] = smaller if family == "binomial" else int(len(used))

        if family == "binomial" and 0 < smaller < bootstrap_below:
            lo, hi = bootstrap_ci(used, outcome, exposure, covariates,
                                   family=family, n_boot=n_boot, seed=seed,
                                   scale_by_sd=scale_by_sd)
            row["boot_ci_lo"], row["boot_ci_hi"] = lo, hi
            row["interval_note"] = f"bootstrap: smaller cell n={smaller}"
        else:
            row["boot_ci_lo"] = row["boot_ci_hi"] = np.nan
            row["interval_note"] = ""
        rows.append(row)

    out = pd.DataFrame(rows)
    out["q"] = fdr(out["p"])
    cols = ["stratum", "exposure", "outcome", "scale", "n", "smaller_cell",
            "estimate", "ci_lo", "ci_hi", "boot_ci_lo", "boot_ci_hi", "p", "q",
            "interval_note", "note"]
    return out[cols].set_index("stratum")


# ── internals ──────────────────────────────────────────────────────────

def _is_binary(s: pd.Series) -> bool:
    vals = pd.to_numeric(s, errors="coerce").dropna().unique()
    return len(vals) <= 2 and set(np.round(vals, 6)) <= {0.0, 1.0}


def _drop_self(covariates: list[str], exposure: str) -> list[str]:
    """Never adjust an exposure for itself.

    BMI and HbA1c are both covariates in the default sets and exposures in
    their own tracks (E2B.1, E2A.1). Left in, the model would carry the same
    column twice and the exposure's own effect would be split across two
    perfectly collinear terms.
    """
    return [c for c in covariates if c != exposure and c != f"C({exposure})"]


def _plain(covariates: list[str]) -> list[str]:
    """Column names behind formula terms, for complete-case counting."""
    return [c[2:-1] if c.startswith("C(") and c.endswith(")") else c
            for c in covariates]


def bootstrap_ci(used: pd.DataFrame, outcome: str, exposure: str,
                 covariates: list[str], *, family: str = "binomial",
                 n_boot: int = 2000, seed: int = 20260817,
                 scale_by_sd: bool = True) -> tuple[float, float]:
    """Percentile bootstrap interval for the exposure effect.

    Public because the project rule is to bootstrap anything claimed from a cell
    under about 50, and that applies outside the stratified helper too — E2A.2's
    discordance groups are n = 46 and 55.

    Resamples participants, refits, and takes the 2.5th/97.5th percentiles of
    the surviving estimates. Replicates that fail to converge -- common when a
    resample happens to contain no events -- are dropped, and the interval is
    NaN if fewer than half survive, rather than reporting a percentile of a
    handful of fits.
    """
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(n_boot):
        draw = used.iloc[rng.integers(0, len(used), len(used))]
        est = fit(draw, outcome, exposure, covariates, family=family,
                  scale_by_sd=scale_by_sd)["estimate"]
        if est is not None and np.isfinite(est):
            estimates.append(est)

    if len(estimates) < n_boot // 2:
        return (float("nan"), float("nan"))
    lo, hi = np.percentile(estimates, [2.5, 97.5])
    return (round(float(lo), 4), round(float(hi), 4))
