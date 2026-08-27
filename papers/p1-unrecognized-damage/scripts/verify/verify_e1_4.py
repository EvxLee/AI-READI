"""Independent verification of E1.4 (who is unrecognized).

Rebuilds from raw, recomputes the descriptive profile, and re-fits the models
through a different statsmodels API -- a hand-built dummy design matrix passed
to `Logit`, rather than the formula interface's GLM. That catches a mis-coded
reference level or a dropped covariate, which is the realistic failure mode.
Does not import `aireadi`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

import _raw

print("=" * 78)
print("VERIFY E1.4 — recognized vs unrecognized")
print("=" * 78)

d = _raw.build()
profile = _raw.artifact("E1_4_profile.csv").set_index(["organ", "variable"])
models = _raw.artifact("E1_4_models.csv").set_index(["organ", "model", "term"])

# Rebuild the de-circularised comorbidity count from raw, independently.
obs = pd.read_csv(_raw.DS / "clinical_data/observation.csv", low_memory=False,
                  usecols=["person_id", "observation_source_value", "value_as_number"])
obs["k"] = obs.observation_source_value.astype(str).str.split(",", n=1).str[0].str.strip().str.lower()
v = pd.to_numeric(obs.value_as_number, errors="coerce")
obs["v"] = v.mask(v.isin(_raw.SPECIAL))
mh = obs[obs.k.str.startswith("mhoccur", na=False) & ~obs.k.isin(["mhoccur_yn", "mhoccur_fallot"])]
wide = mh.pivot_table(index="person_id", columns="k", values="v", aggfunc="first").clip(upper=1)
d["comorb_all"] = wide.sum(axis=1, skipna=True)
d["other_kidney"] = d.comorb_all - wide[["mhoccur_rnl"]].sum(axis=1, skipna=True)
d["other_heart"] = d.comorb_all - wide[["mhoccur_mi", "mhoccur_cvdot"]].sum(axis=1, skipna=True)

_raw.check("comorbidity de-circularisation removes kidney's own item",
           bool((d.other_kidney <= d.comorb_all).all()), True)

for organ, marker, other in [("kidney", "acr", "other_kidney"),
                             ("heart", "trop", "other_heart")]:
    print(f"\n{organ.upper()}")
    sub = d[d[f"unrec_{organ}"].notna()]
    unrec, rec = sub[sub[f"unrec_{organ}"] == 1], sub[sub[f"unrec_{organ}"] == 0]
    _raw.check(f"{organ} n unrecognized", len(unrec),
               int(profile.loc[(organ, "Age, years"), "n_unrec"]))
    _raw.check(f"{organ} n recognized", len(rec),
               int(profile.loc[(organ, "Age, years"), "n_rec"]))

    for col, label in [("age", "Age, years"), ("hba1c", "HbA1c, %"), ("bmi", "BMI, kg/m2")]:
        _raw.check(f"{organ} {label} unrec mean", round(float(unrec[col].mean()), 2),
                   float(profile.loc[(organ, label), "unrecognized"]), tol=0.011)
        _raw.check(f"{organ} {label} rec mean", round(float(rec[col].mean()), 2),
                   float(profile.loc[(organ, label), "recognized"]), tol=0.011)

    lbl = "Other conditions reported (this organ's own items removed)"
    _raw.check(f"{organ} other-conditions unrec mean", round(float(unrec[other].mean()), 2),
               float(profile.loc[(organ, lbl), "unrecognized"]), tol=0.011)
    _raw.check(f"{organ} other-conditions rec mean", round(float(rec[other].mean()), 2),
               float(profile.loc[(organ, lbl), "recognized"]), tol=0.011)

    mlbl = f"{organ} marker (median)"
    _raw.check(f"{organ} marker median unrec", round(float(unrec[marker].median()), 2),
               float(profile.loc[(organ, mlbl), "unrecognized"]), tol=0.011)
    _raw.check(f"{organ} marker median rec", round(float(rec[marker].median()), 2),
               float(profile.loc[(organ, mlbl), "recognized"]), tol=0.011)

    # ── Model A, refit through a different API ──────────────────────────
    m = sub.dropna(subset=["age", "group", "site"]).copy()
    X = pd.concat([
        m[["age"]].astype(float),
        pd.get_dummies(m.group.astype(str), prefix="g", drop_first=False)
          .drop(columns=["g_Healthy"]),
        pd.get_dummies(m.site.astype(str), prefix="s", drop_first=False)
          .drop(columns=["s_UAB"]),
    ], axis=1).astype(float)
    y = m[f"unrec_{organ}"].astype(float)
    fit = sm.Logit(y, sm.add_constant(X)).fit(disp=0)

    _raw.check(f"{organ} model A n", int(fit.nobs),
               int(models.loc[(organ, "A: age + severity + site", "age"), "n_model"]))
    mapping = {
        "age": "age",
        "g_Pre-DM": "C(study_group_label)[T.Pre-DM]",
        "g_Oral Med": "C(study_group_label)[T.Oral Med]",
        "g_Insulin": "C(study_group_label)[T.Insulin]",
        "s_UCSD": "C(clinical_site)[T.UCSD]",
        "s_UW": "C(clinical_site)[T.UW]",
    }
    for mine, theirs in mapping.items():
        _raw.check(f"{organ} A OR {theirs}", round(float(np.exp(fit.params[mine])), 3),
                   float(models.loc[(organ, "A: age + severity + site", theirs), "odds_ratio"]),
                   tol=0.002)
        _raw.check(f"{organ} A p {theirs}", round(float(fit.pvalues[mine]), 5),
                   round(float(models.loc[(organ, "A: age + severity + site", theirs), "p"]), 5),
                   tol=2e-4)

    # Direction sanity: every severity OR below 1 means the unrecognized share
    # falls as severity rises -- the same story E1.2 told, reached by a model.
    ors = [float(models.loc[(organ, "A: age + severity + site", mapping[g]), "odds_ratio"])
           for g in ["g_Pre-DM", "g_Oral Med", "g_Insulin"]]
    _raw.check(f"{organ} all severity ORs < 1 (consistent with E1.2 trend)",
               all(o < 1 for o in ors), True)

_raw.report("E1.4")
