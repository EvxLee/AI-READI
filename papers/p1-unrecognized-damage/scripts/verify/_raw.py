"""An independent rebuild of the Phase-1 analysis dataset.

Deliberately imports NOTHING from `aireadi`. Every field is re-derived from
the cached raw CSVs with plain pandas, and the statistics come from
statsmodels rather than from `aireadi.stats`. The point is that a defect in
the shared data layer cannot verify itself: if both paths agree, they agree
for a reason.

Where a choice had to be made twice, it is made differently on purpose --
e.g. self-report flags here are built by an explicit any/all reduction over
the raw item columns rather than a pivot-and-max.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
DS = REPO / "data/cache/1438dd73-c4cb-48b8-8fa8-c858771207c3/dataset"

SPECIAL = (555, 777, 99)
GROUPS = ["Healthy", "Pre-DM", "Oral Med", "Insulin"]
_GROUP_MAP = {
    "healthy": "Healthy",
    "pre_diabetes_lifestyle_controlled": "Pre-DM",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "Oral Med",
    "insulin_dependent": "Insulin",
}

FAILURES: list[str] = []


def _key(s: pd.Series) -> pd.Series:
    return s.astype(str).str.split(",", n=1).str[0].str.strip().str.lower()


def build(*, acr=30.0, troponin=14.0, missed=2) -> pd.DataFrame:
    """Participant table with damage flags, rebuilt from raw."""
    parts = pd.read_csv(DS / "participants.tsv", sep="\t")
    if set(parts.study_group.unique()) - set(_GROUP_MAP):
        raise AssertionError("unexpected study_group value in participants.tsv")
    d = pd.DataFrame({
        "person_id": parts.person_id.astype(int),
        "group": pd.Categorical(parts.study_group.map(_GROUP_MAP), GROUPS, ordered=True),
        "site": parts.clinical_site,
        "age": parts.age,
    }).set_index("person_id")

    meas = pd.read_csv(DS / "clinical_data/measurement.csv", low_memory=False)
    meas["k"] = _key(meas.measurement_source_value)
    meas["v"] = pd.to_numeric(meas.value_as_number, errors="coerce")
    meas["dt"] = pd.to_datetime(meas.measurement_date, errors="coerce")
    meas = meas.sort_values("dt")

    def lab(key, lo=None, hi=None):
        s = meas[meas.k == key]
        if lo is not None:
            s = s[s.v.between(lo, hi)]
        return s.groupby("person_id").v.last()

    d["alb"] = lab("import_urine_albumin")
    d["crt"] = lab("import_urine_creatinine")
    d["acr"] = d.alb / d.crt.where(d.crt > 0) * 1000
    d["trop"] = lab("import_troponin_t")
    trop_rows = meas[meas.k == "import_troponin_t"]
    d["trop_bd"] = trop_rows.groupby("person_id").apply(
        lambda g: bool(pd.to_numeric(g.operator_concept_id, errors="coerce")
                       .eq(4171756).iloc[-1]), include_groups=False)
    d["mono_l"] = lab("msslffl")
    d["mono_r"] = lab("mssrffl")
    d["mono_worse"] = d[["mono_l", "mono_r"]].min(axis=1)
    d.loc[d[["mono_l", "mono_r"]].isna().any(axis=1), "mono_worse"] = np.nan
    d["hba1c"] = lab("import_hba1c", 3.0, 20.0)
    d["bmi"] = lab("bmi_vsorres", 10.0, 80.0)

    obs = pd.read_csv(DS / "clinical_data/observation.csv", low_memory=False,
                      usecols=["person_id", "observation_source_value", "value_as_number"])
    obs["k"] = _key(obs.observation_source_value)
    v = pd.to_numeric(obs.value_as_number, errors="coerce")
    obs["v"] = v.mask(v.isin(SPECIAL))
    d["cesd"] = obs[obs.k == "cestl"].groupby("person_id").v.first()

    # Self-report: explicit any/all reduction over the raw items, not a pivot.
    def sr(items):
        wide = pd.DataFrame({
            it: obs[obs.k == it].groupby("person_id").v.first() for it in items
        })
        yes = (wide == 1).any(axis=1)
        all_missing = wide.isna().all(axis=1)
        return yes.astype(float).mask(all_missing)

    d["sr_kidney"] = sr(["mhoccur_rnl"])
    d["sr_heart"] = sr(["mhoccur_mi", "mhoccur_cvdot"])

    # Damage flags. NaN in -> NaN out, everywhere.
    d["abn_kidney"] = np.where(d.acr.isna(), np.nan, (d.acr >= acr).astype(float))
    if troponin == "detectable":
        d["abn_heart"] = np.where(d.trop.isna(), np.nan,
                                  (~d.trop_bd.fillna(False).astype(bool)).astype(float))
    else:
        d["abn_heart"] = np.where(d.trop.isna(), np.nan, (d.trop >= troponin).astype(float))
    d["abn_nerve"] = np.where(d.mono_worse.isna(), np.nan,
                              ((10 - d.mono_worse) >= missed).astype(float))

    for organ in ("kidney", "heart"):
        a, s = d[f"abn_{organ}"], d[f"sr_{organ}"]
        d[f"unrec_{organ}"] = np.where((a == 1) & s.notna(), (s == 0).astype(float), np.nan)

    abn = d[["abn_kidney", "abn_heart", "abn_nerve"]]
    d["n_abn"] = np.where(abn.isna().any(axis=1), np.nan, abn.sum(axis=1))
    ok = (d.abn_kidney.notna() & d.sr_kidney.notna()
          & d.abn_heart.notna() & d.sr_heart.notna())
    d["n_unrec"] = np.where(
        ok, ((d.abn_kidney == 1) & (d.sr_kidney == 0)).astype(float)
            + ((d.abn_heart == 1) & (d.sr_heart == 0)).astype(float), np.nan)
    d["abn_any"] = np.where(d.n_abn.isna(), np.nan, (d.n_abn > 0).astype(float))
    return d


# ── Statistics, from statsmodels rather than aireadi.stats ──────────────

def wilson(k: int, n: int) -> tuple[float, float]:
    from statsmodels.stats.proportion import proportion_confint
    if n == 0:
        return (float("nan"), float("nan"))
    lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
    return (100 * lo, 100 * hi)


def trend_z(successes, totals) -> float:
    """Cochran-Armitage z via statsmodels' linear-by-linear test.

    That test scales by N-1 where classic CA uses N; the sqrt(N/(N-1))
    correction is applied here so the two are directly comparable.
    """
    from statsmodels.stats.contingency_tables import Table
    tab = np.array([[k, n - k] for k, n in zip(successes, totals)])
    res = Table(tab).test_ordinal_association(
        row_scores=np.arange(len(successes)), col_scores=np.array([1, 0]))
    n_total = float(sum(totals))
    return abs(res.zscore) * np.sqrt(n_total / (n_total - 1))


def rate(series: pd.Series) -> tuple[int, int]:
    s = pd.Series(series).dropna()
    return int((s > 0).sum()), int(len(s))


def check(label: str, got, want, *, tol: float = 0.0) -> None:
    if isinstance(want, float) or isinstance(got, float):
        ok = abs(float(got) - float(want)) <= tol
    else:
        ok = got == want
    print(f"  [{'OK ' if ok else 'FAIL'}] {label:<58} got {got!r:>12}  artifact {want!r:>12}")
    if not ok:
        FAILURES.append(f"{label}: got {got!r}, artifact {want!r}")


def artifact(name: str) -> pd.DataFrame:
    return pd.read_csv(REPO / "papers/p1-unrecognized-damage/results" / name)


def report(experiment: str) -> None:
    print()
    if FAILURES:
        print(f"{experiment} VERIFICATION FAILED — {len(FAILURES)} discrepancies:")
        for f in FAILURES:
            print("   -", f)
        raise SystemExit(1)
    print(f"{experiment} VERIFIED — every number reproduced from raw by an "
          f"independent path.")
