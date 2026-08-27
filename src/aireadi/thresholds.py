"""Paper 1 abnormality definitions -- what counts as "damage".

These are ANALYSIS CHOICES, not dataset facts, which is why they live here and
not in `constants.py`. They are the Phase-1 exploratory defaults agreed at
E1.0 (2026-08-11); the sweep in E1.5 shows how much each result moves under
the alternatives, and Phase 3 freezes one set into `PRESPEC.md`.

Each organ carries a primary cutoff plus the sweep grid used in E1.5::

    from aireadi import thresholds

    df = thresholds.add_damage_flags(master_table)      # primary cutoffs
    df = thresholds.add_damage_flags(master_table,
                                     troponin_ng_l=16)  # a sensitivity run

Three flag families are added per organ:

* ``abn_<organ>``           -- 1 abnormal, 0 normal, NaN not measured
* ``unrec_<organ>``         -- 1 abnormal AND self-report says no, 0 abnormal
  AND self-report says yes, NaN otherwise (not abnormal, not measured, or no
  usable self-report). Nerve never gets one: E0.2 established this release has
  no neuropathy item, and E0.GATE ruled the broad proxies out entirely.
* ``n_organs_abnormal`` / ``n_organs_unrecognized`` -- per-person counts, NaN
  unless every contributing organ is evaluable, so a partial row can never
  masquerade as a clean zero.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .constants import ORGAN_SELF_REPORT

__all__ = [
    "PRIMARY",
    "SWEEP",
    "ORGANS",
    "UNRECOGNIZED_ORGANS",
    "add_damage_flags",
    "describe",
]

# ── Primary (Phase-1 default) cutoffs ───────────────────────────────────
#
# kidney   ACR >= 30 mg/g. KDIGO category A2 ("moderately increased
#          albuminuria"), the standard screening threshold for diabetic
#          kidney disease. Unambiguous and needs no sex variable.
#
# heart    hs-cTnT >= 14 ng/L. The overall (sex-neutral) 99th-percentile upper
#          reference limit in general use for this assay. Guideline cutoffs are
#          sex-specific (~10 ng/L women, ~15-16 ng/L men) and the public
#          release removes sex, so a sex-neutral limit is the only honest
#          choice; the assay's own reported range_high in this dataset is
#          16 ng/L, which is carried in the sweep.
#
# nerve    >= 2 insensate sites of 10 on the worse foot. Guideline LOPS
#          definitions ("absent sensation at >= 1 site") were written for
#          3-4 site exams; applied literally to a 10-site exam a single
#          equivocal miss would qualify. Requiring two keeps specificity
#          comparable. The guideline-literal >= 1 is the first sweep rung and
#          the difference between them is reported in E1.5.
PRIMARY = {
    "acr_mg_g": 30.0,        # kidney: ACR >= 30 mg/g
    "troponin_ng_l": 14.0,   # heart:  hs-cTnT >= 14 ng/L
    "monofilament_missed": 2,  # nerve: >= 2 insensate sites on the worse foot
}

# Sweep grids for E1.5. The primary value is a member of each grid.
SWEEP = {
    "acr_mg_g": [20.0, 30.0, 50.0, 100.0, 300.0],
    "troponin_ng_l": ["detectable", 10.0, 14.0, 16.0, 19.0, 22.0],
    "monofilament_missed": [1, 2, 3, 4, 5],
}

ORGANS = ["kidney", "heart", "nerve"]
# Nerve is excluded by the E0.GATE decision: no self-report comparator exists.
UNRECOGNIZED_ORGANS = [o for o in ORGANS if ORGAN_SELF_REPORT.get(o)]

_MONOFILAMENT_MAX = 10


def add_damage_flags(
    df: pd.DataFrame,
    *,
    acr_mg_g: float = PRIMARY["acr_mg_g"],
    troponin_ng_l: float | str = PRIMARY["troponin_ng_l"],
    monofilament_missed: int = PRIMARY["monofilament_missed"],
) -> pd.DataFrame:
    """Return a copy of `df` with abnormality and unrecognized flags added.

    `troponin_ng_l` accepts the string ``"detectable"``, meaning "any result
    the assay could actually measure" -- i.e. not carrying the below-detection
    operator. That rung exists because 712 participants have a troponin
    reported AT the 6 ng/L limit; those are limits, not readings, and a naive
    ``>= 6`` comparison would call all 2,232 of them abnormal.

    Missingness is preserved everywhere. A participant with no marker stays
    NaN rather than becoming a silent negative, which is the whole point of a
    prevalence estimate.
    """
    out = df.copy()

    out["abn_kidney"] = _flag(out["acr_mg_g"].ge(acr_mg_g), out["acr_mg_g"])

    if isinstance(troponin_ng_l, str):
        if troponin_ng_l != "detectable":
            raise ValueError(
                f"troponin_ng_l must be a number or 'detectable', got {troponin_ng_l!r}"
            )
        below = out["troponin_t_below_detection"].astype("boolean").fillna(False)
        out["abn_heart"] = _flag(~below.astype(bool), out["troponin_t"])
    else:
        out["abn_heart"] = _flag(out["troponin_t"].ge(troponin_ng_l), out["troponin_t"])

    missed = _MONOFILAMENT_MAX - out["monofilament_min"]
    out["abn_nerve"] = _flag(missed.ge(monofilament_missed), out["monofilament_min"])

    for organ in UNRECOGNIZED_ORGANS:
        abn, sr = out[f"abn_{organ}"], out[f"sr_{organ}"]
        # Defined only among participants who are abnormal AND gave a usable
        # answer. Everyone else is NaN, so the denominator of the unrecognized
        # fraction is exactly "abnormal with a comparator".
        out[f"unrec_{organ}"] = np.where(
            abn.eq(1) & sr.notna(), sr.eq(0).astype(float), np.nan
        )

    abn_cols = [f"abn_{o}" for o in ORGANS]
    out["n_organs_abnormal"] = out[abn_cols].sum(axis=1).mask(
        out[abn_cols].isna().any(axis=1)
    )

    # An organ counts toward the unrecognized tally only if it is evaluable:
    # measured, and with a usable self-report. Abnormal-and-unrecognized = 1.
    unrec_parts, evaluable = [], []
    for organ in UNRECOGNIZED_ORGANS:
        abn, sr = out[f"abn_{organ}"], out[f"sr_{organ}"]
        unrec_parts.append((abn.eq(1) & sr.eq(0)).astype(float))
        evaluable.append(abn.notna() & sr.notna())
    ok = pd.concat(evaluable, axis=1).all(axis=1)
    out["n_organs_unrecognized"] = pd.concat(unrec_parts, axis=1).sum(axis=1).mask(~ok)

    return out


def either_organ(df: pd.DataFrame) -> pd.DataFrame:
    """Masks for the abstract's "either organ" figure.

    Returns one row per participant with:

    ``abnormal``   -- abnormal on kidney or heart
    ``answered``   -- BOTH organs measured AND both self-report items answered
    ``markers_ok`` -- both organs measured (the refusals-included denominator)
    ``unrecognized`` -- abnormal and never told, on at least one organ

    **Both organs must be evaluable, not either.** A participant who is
    unrecognized on kidney but unmeasured on heart would otherwise enter the
    numerator while contributing an incomplete denominator, and the combined
    figure would not be a clean proportion. The strict rule gives 615
    evaluable / 471 unrecognized; the loose "either evaluable" rule gives
    625 / 478. This function exists because those two readings were written
    independently in a runner and a notebook and silently disagreed.
    """
    abn_cols = [f"abn_{o}" for o in UNRECOGNIZED_ORGANS]
    sr_cols = [f"sr_{o}" for o in UNRECOGNIZED_ORGANS]

    markers_ok = df[abn_cols].notna().all(axis=1)
    return pd.DataFrame({
        "abnormal": df[abn_cols].max(axis=1).eq(1),
        "markers_ok": markers_ok,
        "answered": markers_ok & df[sr_cols].notna().all(axis=1),
        "unrecognized": df["n_organs_unrecognized"].gt(0).astype(float),
    }, index=df.index)


def _flag(condition: pd.Series, source: pd.Series) -> pd.Series:
    """Binary flag from `condition`, NaN wherever `source` is missing.

    A bare `.astype(float)` on the comparison turns every unmeasured
    participant into a confident negative.
    """
    return condition.astype(float).mask(source.isna())


def describe(
    *,
    acr_mg_g: float = PRIMARY["acr_mg_g"],
    troponin_ng_l: float | str = PRIMARY["troponin_ng_l"],
    monofilament_missed: int = PRIMARY["monofilament_missed"],
) -> pd.DataFrame:
    """One row per organ describing the cutoff in force -- for the results log."""
    trop = ("any detectable result (above the 6 ng/L limit of detection)"
            if isinstance(troponin_ng_l, str) else f"hs-cTnT >= {troponin_ng_l:g} ng/L")
    return pd.DataFrame(
        [
            {"organ": "kidney", "marker": "urine ACR",
             "definition": f"ACR >= {acr_mg_g:g} mg/g",
             "self_report_comparator": "mhoccur_rnl"},
            {"organ": "heart", "marker": "hs-cTnT",
             "definition": trop,
             "self_report_comparator": "mhoccur_mi | mhoccur_cvdot"},
            {"organ": "nerve", "marker": "monofilament (worse foot)",
             "definition": f">= {monofilament_missed:g} insensate sites of 10",
             "self_report_comparator": "none — E0.GATE"},
        ]
    ).set_index("organ")
