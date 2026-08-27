"""Independent verification of E1.5 (threshold sensitivity).

Rebuilds the cohort at every rung of every grid from raw and re-derives the
prevalence and unrecognized columns, plus the stability verdicts. Does not
import `aireadi`.
"""

from __future__ import annotations

import _raw

print("=" * 78)
print("VERIFY E1.5 — threshold sweep")
print("=" * 78)

sweep = _raw.artifact("E1_5_threshold_sweep.csv").set_index(["organ", "cutoff"])
stability = _raw.artifact("E1_5_conclusion_stability.csv").set_index("claim")

GRID = {
    "kidney": [20.0, 30.0, 50.0, 100.0, 300.0],
    "heart": ["detectable", 10.0, 14.0, 16.0, 19.0, 22.0],
    "nerve": [1, 2, 3, 4, 5],
}
KWARG = {"kidney": "acr", "heart": "troponin", "nerve": "missed"}

for organ, rungs in GRID.items():
    print(f"\n{organ.upper()}")
    for rung in rungs:
        d = _raw.build(**{KWARG[organ]: rung})
        key = (organ, str(rung))
        abn = d[f"abn_{organ}"]

        k, n = _raw.rate(abn)
        _raw.check(f"{organ} @{rung} n_abnormal", k, int(sweep.loc[key, "n_abnormal"]))
        _raw.check(f"{organ} @{rung} n_measured", n, int(sweep.loc[key, "n_measured"]))
        _raw.check(f"{organ} @{rung} prevalence", round(100 * k / n, 1),
                   float(sweep.loc[key, "prevalence_pct"]), tol=0.05)

        ks = [_raw.rate(abn[d.group == g])[0] for g in _raw.GROUPS]
        ns = [_raw.rate(abn[d.group == g])[1] for g in _raw.GROUPS]
        _raw.check(f"{organ} @{rung} prevalence trend |z|", round(_raw.trend_z(ks, ns), 3),
                   abs(float(sweep.loc[key, "prev_trend_z"])), tol=0.001)

        if organ in ("kidney", "heart"):
            sr = d[f"sr_{organ}"]
            uk = int((abn.eq(1) & sr.eq(0)).sum())
            un = int((abn.eq(1) & sr.notna()).sum())
            _raw.check(f"{organ} @{rung} n_unrecognized", uk,
                       int(sweep.loc[key, "n_unrecognized"]))
            _raw.check(f"{organ} @{rung} unrec denominator", un,
                       int(sweep.loc[key, "n_unrec_denominator"]))
            _raw.check(f"{organ} @{rung} unrecognized pct", round(100 * uk / un, 1),
                       float(sweep.loc[key, "unrecognized_pct"]), tol=0.05)
            uks = [int((abn.eq(1) & sr.eq(0) & (d.group == g)).sum()) for g in _raw.GROUPS]
            uns = [int((abn.eq(1) & sr.notna() & (d.group == g)).sum()) for g in _raw.GROUPS]
            _raw.check(f"{organ} @{rung} unrec trend |z|", round(_raw.trend_z(uks, uns), 3),
                       abs(float(sweep.loc[key, "unrec_trend_z"])), tol=0.001)

# ── Monotonicity: a stricter cutoff can only shrink the abnormal set ────
print("\nMONOTONICITY (a stricter cutoff cannot find more abnormal people)")
for organ in ("kidney", "nerve"):
    counts = [int(sweep.loc[(organ, str(r)), "n_abnormal"]) for r in GRID[organ]]
    _raw.check(f"{organ} n_abnormal is non-increasing across the grid",
               all(a >= b for a, b in zip(counts, counts[1:])), True)
heart_numeric = [10.0, 14.0, 16.0, 19.0, 22.0]
hc = [int(sweep.loc[("heart", str(r)), "n_abnormal"]) for r in heart_numeric]
_raw.check("heart n_abnormal is non-increasing across the numeric grid",
           all(a >= b for a, b in zip(hc, hc[1:])), True)
_raw.check("heart 'detectable' is the loosest rung",
           int(sweep.loc[("heart", "detectable"), "n_abnormal"]) >= max(hc), True)

# ── The stability verdicts must follow from the sweep itself ────────────
print("\nSTABILITY VERDICTS RE-DERIVED")
for organ in GRID:
    s = sweep.loc[organ]
    _raw.check(f"{organ} prevalence-trend verdict",
               bool((s.prev_trend_z > 0).all() and (s.prev_trend_p < 0.05).all()),
               bool(stability.loc[f"{organ} prevalence rises with severity",
                                  "holds_at_every_cutoff"]))
for organ in ("kidney", "heart"):
    s = sweep.loc[organ]
    _raw.check(f"{organ} majority-unrecognized verdict", bool((s.unrecognized_pct > 50).all()),
               bool(stability.loc[f"{organ} majority of abnormal results are unrecognized",
                                  "holds_at_every_cutoff"]))
    _raw.check(f"{organ} falling-fraction verdict", bool((s.unrec_trend_z < 0).all()),
               bool(stability.loc[f"{organ} unrecognized FRACTION falls with severity",
                                  "holds_at_every_cutoff"]))

# The flip that matters: kidney loses the majority claim at the strict end.
_raw.check("kidney majority claim FLIPS (verdict is False)",
           bool(stability.loc["kidney majority of abnormal results are unrecognized",
                              "holds_at_every_cutoff"]), False)
_raw.check("kidney @300 unrecognized is below 50%",
           float(sweep.loc[("kidney", "300.0"), "unrecognized_pct"]) < 50, True)

_raw.report("E1.5")
