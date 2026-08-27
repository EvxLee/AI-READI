"""E1.4 — Who is unrecognized: recognized vs unrecognized, among the abnormal.

Restricted to participants who ARE abnormal and who answered the self-report
item. Outcome is "was never told" (1) vs "was told" (0). So this asks, given
damage, what distinguishes the people who know from the people who do not.

Two things are reported:

* a descriptive profile with standardised mean differences, which does not
  depend on any model being right, and
* logistic models -- the project-default age + severity + site adjustment, then
  the same plus HbA1c and BMI.

Marker magnitude is carried deliberately. The most obvious alternative
explanation for the whole paper is "the unrecognized are simply less abnormal",
and that has to be measured rather than argued away.

CES-D is NOT here. Depression vs unrecognized status is E2C.2, a Phase-2
question with its own prespecified recipe; running it early inside a Phase-1
descriptive table would be exactly the kind of unlogged peek the results log
exists to prevent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from aireadi import azure_io, constants, omop, results, thresholds

import _phase1

_phase1.banner("E1.4", "Recognized vs unrecognized among those with damage")

df = _phase1.load()
df["log_acr"] = np.log(df["acr_mg_g"].where(df["acr_mg_g"] > 0))
df["log_troponin"] = np.log(df["troponin_t"].where(df["troponin_t"] > 0))
MARKER = {"kidney": "log_acr", "heart": "log_troponin"}
RAW_MARKER = {"kidney": "acr_mg_g", "heart": "troponin_t"}

# ── Comorbidity count, with the circularity removed ─────────────────────
# The plain comorbidity count includes the organ's OWN self-reported item, so
# anyone classed as "recognized" scores at least one by construction and the
# comparison is rigged. Each organ therefore gets a count with its own items
# subtracted out. Kept organ-specific and local: which items to remove depends
# on which organ is being tested, so this is not shared-layer logic.
_obs = omop.add_item_key(azure_io.load_table(
    "observation", usecols=["person_id", "observation_source_value", "value_as_number"]))
_own = omop.pivot_items(_obs, keys=sorted(
    {i for items in constants.ORGAN_SELF_REPORT.values() for i in items}))
for _organ, _items in constants.ORGAN_SELF_REPORT.items():
    if not _items:
        continue
    _present = [c for c in _items if c in _own.columns]
    _yes = _own[_present].clip(upper=1).sum(axis=1, skipna=True).rename(f"_own_{_organ}")
    df = df.merge(_yes.reset_index(), on="person_id", how="left")
    df[f"other_comorbidity_{_organ}"] = df["comorbidity_count"] - df[f"_own_{_organ}"].fillna(0)


def smd_continuous(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna(), b.dropna()
    pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return float((a.mean() - b.mean()) / pooled) if pooled else float("nan")


def smd_binary(pa: float, pb: float) -> float:
    pooled = np.sqrt((pa * (1 - pa) + pb * (1 - pb)) / 2)
    return float((pa - pb) / pooled) if pooled else float("nan")


profile_rows, model_rows = [], []

for organ in thresholds.UNRECOGNIZED_ORGANS:
    sub = df[df[f"unrec_{organ}"].notna()].copy()
    unrec = sub[sub[f"unrec_{organ}"] == 1]
    rec = sub[sub[f"unrec_{organ}"] == 0]
    print(f"\n{organ.upper()} — {len(sub):,} abnormal with an answer: "
          f"{len(unrec):,} never told, {len(rec):,} told")

    for var, label in [("age", "Age, years"), ("hba1c", "HbA1c, %"),
                       ("bmi", "BMI, kg/m2"),
                       (f"other_comorbidity_{organ}",
                        "Other conditions reported (this organ's own items removed)"),
                       (RAW_MARKER[organ], f"{organ} marker (median)")]:
        use_median = var == RAW_MARKER[organ]
        profile_rows.append({
            "organ": organ, "variable": label,
            "unrecognized": round(float(unrec[var].median() if use_median
                                        else unrec[var].mean()), 2),
            "recognized": round(float(rec[var].median() if use_median
                                      else rec[var].mean()), 2),
            "spread_unrec": round(float(unrec[var].std()), 2),
            "spread_rec": round(float(rec[var].std()), 2),
            "n_unrec": int(unrec[var].notna().sum()),
            "n_rec": int(rec[var].notna().sum()),
            "smd": round(smd_continuous(unrec[var], rec[var]), 3),
        })

    for col in ("study_group_label", "clinical_site"):
        for level in (sub[col].cat.categories if isinstance(sub[col].dtype, pd.CategoricalDtype)
                      else sorted(sub[col].dropna().unique())):
            pa = float((unrec[col] == level).mean())
            pb = float((rec[col] == level).mean())
            profile_rows.append({
                "organ": organ, "variable": f"{col} = {level}, %",
                "unrecognized": round(100 * pa, 1), "recognized": round(100 * pb, 1),
                "spread_unrec": np.nan, "spread_rec": np.nan,
                "n_unrec": int((unrec[col] == level).sum()),
                "n_rec": int((rec[col] == level).sum()),
                "smd": round(smd_binary(pa, pb), 3),
            })

    # ── Models ──────────────────────────────────────────────────────────
    formulas = {
        "A: age + severity + site":
            f"unrec_{organ} ~ age + C(study_group_label) + C(clinical_site)",
        "B: A + HbA1c + BMI":
            f"unrec_{organ} ~ age + C(study_group_label) + C(clinical_site) + hba1c + bmi",
        "C: B + marker magnitude":
            f"unrec_{organ} ~ age + C(study_group_label) + C(clinical_site) + hba1c + bmi"
            f" + {MARKER[organ]}",
    }
    for name, formula in formulas.items():
        fit = smf.glm(formula, data=sub, family=sm.families.Binomial()).fit()
        params, cis = fit.params, fit.conf_int()
        for term in params.index:
            if term == "Intercept":
                continue
            model_rows.append({
                "organ": organ, "model": name, "term": term,
                "odds_ratio": round(float(np.exp(params[term])), 3),
                "ci_lo": round(float(np.exp(cis.loc[term, 0])), 3),
                "ci_hi": round(float(np.exp(cis.loc[term, 1])), 3),
                "p": float(fit.pvalues[term]),
                "n_model": int(fit.nobs),
            })
        print(f"  {name}: n={int(fit.nobs)}, "
              f"terms p<0.05 -> "
              f"{[t for t in params.index if t != 'Intercept' and fit.pvalues[t] < 0.05] or 'none'}")

profile = pd.DataFrame(profile_rows).set_index(["organ", "variable"])
models = pd.DataFrame(model_rows).set_index(["organ", "model", "term"])

pd.set_option("display.width", 200)
print("\nDescriptive profile (unrecognized vs recognized):")
print(profile.to_string())
print("\nAdjusted odds of being unrecognized:")
print(models.assign(p=models.p.map(lambda v: f"{v:.3g}")).to_string())

big = profile[profile.smd.abs() >= 0.2]
sig = models[models.p < 0.05]

results.save(
    "E1.4", profile, paper="p1",
    method=("Descriptive comparison of unrecognized vs recognized participants among "
            "those with an abnormal result, with standardised mean differences."),
    result=(f"Variables with |SMD| >= 0.2: "
            + ("; ".join(f"{o}/{v} {profile.loc[(o, v), 'smd']}" for o, v in big.index)
               if len(big) else "none")),
    decision="keep", name="profile", primary=False,
)
results.save(
    "E1.4", models, paper="p1",
    method=("Logistic regression of unrecognized status among the abnormal: "
            "(A) age + severity + site, (B) + HbA1c + BMI, (C) + log marker magnitude."),
    result=(f"Terms with p<0.05 across all models: "
            + ("; ".join(f"{o} [{m}] {t} OR={models.loc[(o, m, t), 'odds_ratio']}"
                         for o, m, t in sig.index) if len(sig) else "none")),
    decision="keep", name="models",
)
