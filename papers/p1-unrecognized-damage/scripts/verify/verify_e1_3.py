"""Independent verification of E1.3 (multi-organ counts and overlap).

Rebuilds from raw and checks the counts table, the intersection table and the
unrecognized-organ counts, including the arithmetic identities that tie them
together. Does not import `aireadi`.
"""

from __future__ import annotations

import pandas as pd

import _raw

print("=" * 78)
print("VERIFY E1.3 — multi-organ counts and overlap")
print("=" * 78)

d = _raw.build()
counts = _raw.artifact("E1_3_organ_counts.csv").set_index("stratum")
overlap = _raw.artifact("E1_3_overlap.csv").set_index("combination")
unrec = _raw.artifact("E1_3_unrecognized_counts.csv")
unrec.columns = ["label", "n", "pct"]

ORGANS = ["kidney", "heart", "nerve"]
complete = d[d[[f"abn_{o}" for o in ORGANS]].notna().all(axis=1)]
print(f"\n  complete on all three organs: {len(complete):,}")
_raw.check("complete-case n", len(complete), int(counts.loc["Overall", "n"]))

# ── Count distribution ──────────────────────────────────────────────────
print("\nCOUNT DISTRIBUTION")
for label, sub in [("Overall", complete),
                   *[(g, complete[complete.group == g]) for g in _raw.GROUPS]]:
    n_abn = sub[[f"abn_{o}" for o in ORGANS]].sum(axis=1)
    for i in range(4):
        _raw.check(f"{label} exactly {i} organs", int((n_abn == i).sum()),
                   int(counts.loc[label, f"organs_{i}"]))
    _raw.check(f"{label} mean organs", round(float(n_abn.mean()), 3),
               float(counts.loc[label, "mean_organs"]), tol=0.001)
    _raw.check(f"{label} categories sum to n", int(len(sub)), int(counts.loc[label, "n"]))

# The count distribution must reconcile with E1.1's per-organ prevalences:
# sum over people of (organs abnormal) = sum over organs of (people abnormal),
# both restricted to complete cases.
lhs = int(complete[[f"abn_{o}" for o in ORGANS]].sum(axis=1).sum())
rhs = sum(int((complete[f"abn_{o}"] == 1).sum()) for o in ORGANS)
_raw.check("total organ-events match across the two orientations", lhs, rhs)
_raw.check("weighted count identity", lhs,
           sum(i * int(counts.loc["Overall", f"organs_{i}"]) for i in range(4)))

# ── Intersections ───────────────────────────────────────────────────────
print("\nINTERSECTIONS")
combo = complete[[f"abn_{o}" for o in ORGANS]].astype(int).apply(
    lambda r: " + ".join(o for o, v in zip(ORGANS, r) if v) or "none", axis=1)
got = combo.value_counts()
for name in overlap.index:
    _raw.check(f"combination '{name}'", int(got.get(name, 0)), int(overlap.loc[name, "n"]))
_raw.check("combinations sum to complete cases", int(overlap.n.sum()), len(complete))
_raw.check("no unlisted combination exists", set(got.index) - set(overlap.index), set())

# Each single-organ total must equal that organ's complete-case prevalence.
for organ in ORGANS:
    from_combos = int(overlap.loc[[i for i in overlap.index if organ in i.split(" + ")],
                                  "n"].sum())
    _raw.check(f"{organ} across all combinations", from_combos,
               int((complete[f"abn_{organ}"] == 1).sum()))

# ── Unrecognized organ counts ───────────────────────────────────────────
print("\nUNRECOGNIZED ORGAN COUNTS")
ok = (d.abn_kidney.notna() & d.sr_kidney.notna()
      & d.abn_heart.notna() & d.sr_heart.notna())
n_unrec = (((d.abn_kidney == 1) & (d.sr_kidney == 0)).astype(int)
           + ((d.abn_heart == 1) & (d.sr_heart == 0)).astype(int))[ok]
_raw.check("evaluable on both organs", int(ok.sum()), int(unrec.n.sum()))
for i in range(3):
    _raw.check(f"exactly {i} unrecognized", int((n_unrec == i).sum()), int(unrec.n.iloc[i]))

# Cross-check against E1.2: people with >= 1 unrecognized organ must equal the
# "either" numerator reported there.
either = _raw.artifact("E1_2_unrecognized_by_group.csv")
either_k = int(either[either.organ == "either"].set_index("stratum").loc["Overall", "k"])
_raw.check("E1.3 (>=1 unrecognized) equals E1.2 'either' numerator",
           int((n_unrec >= 1).sum()), either_k)

_raw.report("E1.3")
