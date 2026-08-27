"""Independent verification of E1.2 (unrecognized fraction — the headline).

Rebuilds from raw, recomputes the conditional fraction, the concordance 2x2
and the population burden, and checks them against each other as well as
against the artifacts. Does not import `aireadi`.
"""

from __future__ import annotations

import _raw

print("=" * 78)
print("VERIFY E1.2 — unrecognized fraction")
print("=" * 78)

d = _raw.build()
frac = _raw.artifact("E1_2_unrecognized_by_group.csv")
conc = _raw.artifact("E1_2_concordance.csv").set_index("organ")
burden = _raw.artifact("E1_2_population_burden.csv")

# ── Conditional fraction, per organ ─────────────────────────────────────
for organ in ["kidney", "heart"]:
    print(f"\n{organ.upper()} — unrecognized among the abnormal who answered")
    rows = frac[frac.organ == organ].set_index("stratum")
    abn, sr = d[f"abn_{organ}"], d[f"sr_{organ}"]

    # Built from scratch here, not read off the flag column.
    denom = (abn == 1) & sr.notna()
    numer = (abn == 1) & (sr == 0)

    k, n = int(numer.sum()), int(denom.sum())
    _raw.check(f"{organ} overall unrecognized", k, int(rows.loc["Overall", "k"]))
    _raw.check(f"{organ} overall denominator", n, int(rows.loc["Overall", "n"]))
    _raw.check(f"{organ} overall pct", round(100 * k / n, 1),
               float(rows.loc["Overall", "pct"]), tol=0.05)
    lo, hi = _raw.wilson(k, n)
    _raw.check(f"{organ} CI lo", round(lo, 1), float(rows.loc["Overall", "ci_lo"]), tol=0.05)
    _raw.check(f"{organ} CI hi", round(hi, 1), float(rows.loc["Overall", "ci_hi"]), tol=0.05)

    ks, ns = [], []
    for g in _raw.GROUPS:
        m = d.group == g
        gk, gn = int((numer & m).sum()), int((denom & m).sum())
        ks.append(gk)
        ns.append(gn)
        _raw.check(f"{organ} {g} k", gk, int(rows.loc[g, "k"]))
        _raw.check(f"{organ} {g} n", gn, int(rows.loc[g, "n"]))
    _raw.check(f"{organ} strata sum to overall", (sum(ks), sum(ns)), (k, n))
    _raw.check(f"{organ} trend |z|", round(_raw.trend_z(ks, ns), 3),
               abs(float(rows.loc["Overall", "trend_z"])), tol=0.001)

    # The refusals-included denominator must equal all abnormal.
    _raw.check(f"{organ} denominator incl. refusals", int((abn == 1).sum()),
               int(rows.loc["Overall", "n_incl_refusals"]))

# ── The trend runs DOWNWARD: assert the direction explicitly ────────────
print("\nDIRECTION OF THE TREND (the counter-intuitive part)")
for organ in ["kidney", "heart"]:
    abn, sr = d[f"abn_{organ}"], d[f"sr_{organ}"]
    pct = []
    for g in _raw.GROUPS:
        m = d.group == g
        k = int((abn.eq(1) & sr.eq(0) & m).sum())
        n = int((abn.eq(1) & sr.notna() & m).sum())
        pct.append(round(100 * k / n, 1))
    print(f"  {organ} unrecognized % by severity: {pct}")
    _raw.check(f"{organ} Healthy fraction exceeds Insulin fraction",
               pct[0] > pct[-1], True)
    _raw.check(f"{organ} artifact trend_z is negative",
               float(frac[frac.organ == organ].set_index("stratum").loc["Overall", "trend_z"]) < 0,
               True)

# ── Concordance 2x2 ─────────────────────────────────────────────────────
print("\nCONCORDANCE 2x2")
for organ in ["kidney", "heart"]:
    abn, sr = d[f"abn_{organ}"], d[f"sr_{organ}"]
    cells = {
        "abnormal_and_not_reported": int((abn.eq(1) & sr.eq(0)).sum()),
        "abnormal_and_reported": int((abn.eq(1) & sr.eq(1)).sum()),
        "normal_and_reported": int((abn.eq(0) & sr.eq(1)).sum()),
        "normal_and_not_reported": int((abn.eq(0) & sr.eq(0)).sum()),
    }
    for name, got in cells.items():
        _raw.check(f"{organ} {name}", got, int(conc.loc[organ, name]))
    _raw.check(f"{organ} cells sum to n_evaluable", sum(cells.values()),
               int(conc.loc[organ, "n_evaluable"]))
    _raw.check(f"{organ} n_evaluable = measured minus refusals",
               int((abn.notna() & sr.notna()).sum()), int(conc.loc[organ, "n_evaluable"]))

# ── Population burden, and its relationship to the fraction ─────────────
print("\nPOPULATION BURDEN")
for organ in ["kidney", "heart"]:
    rows = burden[burden.organ == organ].set_index("stratum")
    abn, sr = d[f"abn_{organ}"], d[f"sr_{organ}"]
    numer = abn.eq(1) & sr.eq(0)
    denom = abn.notna() & sr.notna()
    ks, ns = [], []
    for g in _raw.GROUPS:
        m = d.group == g
        ks.append(int((numer & m).sum()))
        ns.append(int((denom & m).sum()))
        _raw.check(f"{organ} burden {g} k", ks[-1], int(rows.loc[g, "k"]))
        _raw.check(f"{organ} burden {g} n", ns[-1], int(rows.loc[g, "n"]))
    _raw.check(f"{organ} burden overall k", sum(ks), int(rows.loc["Overall", "k"]))
    _raw.check(f"{organ} burden trend |z|", round(_raw.trend_z(ks, ns), 3),
               abs(float(rows.loc["Overall", "trend_z"])), tol=0.001)
    _raw.check(f"{organ} burden trend_z is POSITIVE while fraction trend_z is negative",
               float(rows.loc["Overall", "trend_z"]) > 0, True)

    # The two views must be arithmetically reconcilable: burden = prevalence x fraction.
    fr = frac[frac.organ == organ].set_index("stratum")
    for g in _raw.GROUPS:
        prev = int((abn.eq(1) & denom & (d.group == g)).sum()) / ns[_raw.GROUPS.index(g)]
        recon = 100 * prev * float(fr.loc[g, "pct"]) / 100
        _raw.check(f"{organ} {g} burden = prevalence x fraction",
                   round(recon, 1), float(rows.loc[g, "pct"]), tol=0.15)

_raw.report("E1.2")
