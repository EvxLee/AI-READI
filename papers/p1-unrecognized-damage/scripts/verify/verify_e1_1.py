"""Independent verification of E1.1 (prevalence).

Rebuilds the cohort from raw CSVs, recomputes every cell of
`E1_1_prevalence_by_group.csv`, and diffs. Does not import `aireadi`.
"""

from __future__ import annotations

import _raw

print("=" * 78)
print("VERIFY E1.1 — prevalence of measured organ damage")
print("=" * 78)

d = _raw.build()
art = _raw.artifact("E1_1_prevalence_by_group.csv")

print(f"\n  independent rebuild: {len(d):,} participants, "
      f"groups {d.group.value_counts().reindex(_raw.GROUPS).tolist()}")
_raw.check("cohort size", len(d), 2280)

for organ in ["kidney", "heart", "nerve", "any"]:
    print(f"\n{organ.upper()}")
    rows = art[art.organ == organ].set_index("stratum")

    k, n = _raw.rate(d[f"abn_{organ}"])
    _raw.check(f"{organ} overall k", k, int(rows.loc["Overall", "k"]))
    _raw.check(f"{organ} overall n", n, int(rows.loc["Overall", "n"]))
    _raw.check(f"{organ} overall pct", round(100 * k / n, 1),
               float(rows.loc["Overall", "pct"]), tol=0.05)
    lo, hi = _raw.wilson(k, n)
    _raw.check(f"{organ} overall CI lo", round(lo, 1), float(rows.loc["Overall", "ci_lo"]), tol=0.05)
    _raw.check(f"{organ} overall CI hi", round(hi, 1), float(rows.loc["Overall", "ci_hi"]), tol=0.05)

    ks, ns = [], []
    for g in _raw.GROUPS:
        gk, gn = _raw.rate(d.loc[d.group == g, f"abn_{organ}"])
        ks.append(gk)
        ns.append(gn)
        _raw.check(f"{organ} {g} k", gk, int(rows.loc[g, "k"]))
        _raw.check(f"{organ} {g} n", gn, int(rows.loc[g, "n"]))
        _raw.check(f"{organ} {g} pct", round(100 * gk / gn, 1), float(rows.loc[g, "pct"]), tol=0.05)

    # Group cells must reconstitute the overall row, or a stratum went missing.
    _raw.check(f"{organ} groups sum to overall k", sum(ks), k)
    _raw.check(f"{organ} groups sum to overall n", sum(ns), n)

    _raw.check(f"{organ} trend z", round(_raw.trend_z(ks, ns), 3),
               abs(float(rows.loc["Overall", "trend_z"])), tol=0.001)

# The "any organ" row must be internally consistent with the three organs:
# it can never be smaller than the largest single organ, nor larger than the sum.
sub = d.dropna(subset=["abn_kidney", "abn_heart", "abn_nerve"])
singles = [int((sub[f"abn_{o}"] == 1).sum()) for o in ("kidney", "heart", "nerve")]
any_k = int((sub.abn_any == 1).sum())
print()
_raw.check("any >= largest single organ (complete cases)", any_k >= max(singles), True)
_raw.check("any <= sum of organs (complete cases)", any_k <= sum(singles), True)

_raw.report("E1.1")
