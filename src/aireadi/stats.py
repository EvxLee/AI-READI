"""Proportions, confidence intervals and trend tests for the core sweep.

Paper 1's backbone is counting, so the statistics that matter are the ones
that put an honest interval around a count and test whether it rises across
the severity spectrum.

* `wilson_ci` -- Wilson score interval. Used rather than the textbook normal
  approximation because several cells here are small (Insulin n ~ 258, and
  some abnormal-organ cells are in the dozens) and the normal interval both
  undercovers and runs off the end of [0, 1] there.
* `proportion_by_group` -- one table: overall row, one row per severity group,
  counts, percentages, intervals.
* `cochran_armitage` -- trend across ordered groups. A plain chi-square asks
  "are these four proportions different"; the paper's claim is the stronger,
  ordered one, "do they rise with severity", so that is what gets tested.

Denominators are always explicit. Everything ignores NaN, and every function
reports the n it actually used.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as _sps

__all__ = [
    "wilson_ci",
    "proportion",
    "proportion_by_group",
    "cochran_armitage",
    "chi_square",
]


def wilson_ci(k: int, n: int, *, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials, as proportions.

    Returns (nan, nan) for n == 0 rather than raising, so an empty cell in a
    stratified table does not take the whole table down.
    """
    if n <= 0:
        return (float("nan"), float("nan"))
    z = _sps.norm.ppf(1 - alpha / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def proportion(flag: pd.Series, *, alpha: float = 0.05) -> dict:
    """Count, denominator, percentage and Wilson interval for a 0/1/NaN flag.

    The denominator is the number of NON-MISSING values -- participants who
    could be classified. Anyone unmeasured is excluded rather than counted as
    a negative.
    """
    s = pd.to_numeric(pd.Series(flag), errors="coerce").dropna()
    n = int(len(s))
    k = int((s > 0).sum())
    lo, hi = wilson_ci(k, n, alpha=alpha)
    return {
        "n": n, "k": k,
        "pct": 100 * k / n if n else float("nan"),
        "ci_lo": 100 * lo, "ci_hi": 100 * hi,
    }


def proportion_by_group(
    df: pd.DataFrame,
    flag: str,
    *,
    group: str = "study_group_label",
    alpha: float = 0.05,
    trend: bool = True,
) -> pd.DataFrame:
    """Prevalence of `flag` overall and within each level of `group`.

    Rows: "Overall" first, then the group levels in their categorical order,
    so an ordered severity factor stays ordered. When `trend` is True and the
    group is ordered, a Cochran-Armitage trend statistic is attached as
    columns on every row (the same value repeated, so the table stays flat and
    survives a round-trip through CSV).
    """
    rows = [{"stratum": "Overall", **proportion(df[flag], alpha=alpha)}]

    levels = (
        list(df[group].cat.categories)
        if isinstance(df[group].dtype, pd.CategoricalDtype)
        else sorted(df[group].dropna().unique())
    )
    for level in levels:
        sub = df.loc[df[group] == level, flag]
        rows.append({"stratum": str(level), **proportion(sub, alpha=alpha)})

    out = pd.DataFrame(rows).set_index("stratum")

    if trend and len(levels) > 2:
        strata = out.loc[[str(x) for x in levels]]
        z, p = cochran_armitage(strata["k"].tolist(), strata["n"].tolist())
        out["trend_z"] = z
        out["trend_p"] = p
        chi2, chi_p = chi_square(strata["k"].tolist(), strata["n"].tolist())
        out["chi2_p"] = chi_p

    # Percentages and z round for readability; p-values NEVER do. These trends
    # run to p ~ 1e-20, and rounding to six places prints them as a flat 0.0,
    # which reads as a formatting bug and throws away the magnitude.
    return out.round({"pct": 1, "ci_lo": 1, "ci_hi": 1, "trend_z": 3})


def cochran_armitage(
    successes: list[int], totals: list[int], scores: list[float] | None = None
) -> tuple[float, float]:
    """Cochran-Armitage test for trend in proportions across ordered groups.

    `scores` defaults to 0, 1, 2, ... -- equally spaced severity steps, which
    is the only defensible default when the groups are treatment categories
    rather than a measured quantity. Returns (z, two-sided p).

    A positive z means the proportion rises with the score.
    """
    k = np.asarray(successes, dtype=float)
    n = np.asarray(totals, dtype=float)
    if len(k) != len(n):
        raise ValueError("successes and totals must be the same length")
    x = np.arange(len(k), dtype=float) if scores is None else np.asarray(scores, float)

    n_total = n.sum()
    k_total = k.sum()
    if n_total == 0 or k_total in (0, n_total):
        return (float("nan"), float("nan"))

    p = k_total / n_total
    t = float(np.sum(k * x) - p * np.sum(n * x))
    var = p * (1 - p) * (np.sum(n * x**2) - (np.sum(n * x) ** 2) / n_total)
    if var <= 0:
        return (float("nan"), float("nan"))
    z = t / np.sqrt(var)
    return (float(z), float(2 * _sps.norm.sf(abs(z))))


def chi_square(successes: list[int], totals: list[int]) -> tuple[float, float]:
    """Plain chi-square of independence across groups -- the unordered check.

    Reported alongside the trend test so a pattern that is merely *different*
    across groups is not mistaken for one that *rises*.
    """
    k = np.asarray(successes, dtype=float)
    n = np.asarray(totals, dtype=float)
    table = np.vstack([k, n - k])
    if (table.sum(axis=0) == 0).any() or (table.sum(axis=1) == 0).any():
        return (float("nan"), float("nan"))
    chi2, p, _, _ = _sps.chi2_contingency(table)
    return (float(chi2), float(p))
