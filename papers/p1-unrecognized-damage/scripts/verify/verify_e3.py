"""Independent verification of Phase 3 (E2.TIMING artifact, E3.1, E3.3).

Same contract as every other verifier: rebuild each variable from the raw
cached CSVs with plain pandas, refit through statsmodels' array API rather
than the formula API the runners use, and diff against the committed
artifacts. Imports nothing from `aireadi`.

What is re-derived here:

* E2.TIMING — the survey-to-visit interval and the marker concurrence, from
  the raw observation/measurement dates.
* E3.1 — the ranking's bookkeeping (survivor counts against the source
  artifacts, criteria arithmetic, no unstable site fit counted), and a from-raw
  refit of the within-site Aim-2 nerve model and the within-site kidney
  unrecognized trend.
* E3.3 — the Aim-1 confirmatory table against Phase 1 and against a fresh
  rebuild; every per-site trend; the Aim-2 spec model (age + BMI + HbA1c +
  severity + site) for all ten family members; the T1 primary model; the T2
  QRS model; two rungs of the burden sweep; and the bootstrap columns
  bracketing their point estimates.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
import statsmodels.api as sm

import _raw

print("=" * 78)
print("VERIFY E3 — E2.TIMING artifact, E3.1 ranking, E3.3 confirmatory reruns")
print("=" * 78)

d = _raw.build()
d["log_trop"] = np.log(d.trop.where(d.trop > 0))
d["missed"] = 10 - d.mono_worse
d["abn_any"] = np.where(d.n_abn.isna(), np.nan, (d.n_abn > 0).astype(float))
d["abn_multi"] = np.where(d.n_abn.isna(), np.nan, (d.n_abn >= 2).astype(float))
alb_floored = d.alb.mask(d.alb.eq(0), 0.01 / 2)
acr_floored = alb_floored / d.crt.where(d.crt > 0) * 1000
d["log_acr"] = np.log(acr_floored.where(acr_floored > 0))
d["unrec_either"] = np.where(
    d.abn_kidney.notna() & d.abn_heart.notna() & d.sr_kidney.notna() & d.sr_heart.notna(),
    ((d.abn_kidney.eq(1) & d.sr_kidney.eq(0)) | (d.abn_heart.eq(1) & d.sr_heart.eq(0))).astype(float),
    np.nan)
d["abn_either"] = np.where(d.abn_kidney.notna() & d.abn_heart.notna(),
                           ((d.abn_kidney == 1) | (d.abn_heart == 1)).astype(float), np.nan)

SITES = ["UW", "UAB", "UCSD"]


def refit(frame, outcome, exposure, *, covariates=("age", "group", "site"), gaussian=False,
          extra=(), scale=True, sd_source=None):
    cols = ["age"] if "age" in covariates else []
    m = frame.dropna(subset=[outcome, exposure] + cols + list(extra)).copy()
    if "group" in covariates:
        m = m[m.group.notna()]
    if "site" in covariates:
        m = m[m.site.notna()]
    x = m[[exposure]].astype(float)
    src = sd_source if sd_source is not None else frame
    if scale and set(np.round(src[exposure].dropna().unique(), 6)) - {0.0, 1.0}:
        x = x / float(src[exposure].std())
    parts = [x]
    if cols:
        parts.append(m[cols].astype(float))
    if "group" in covariates:
        parts.append(pd.get_dummies(m.group.astype(str), prefix="g").drop(columns=["g_Healthy"]))
    if "site" in covariates:
        dummies = pd.get_dummies(m.site.astype(str), prefix="s")
        parts.append(dummies.drop(columns=[c for c in ["s_UAB"] if c in dummies.columns]))
    for e in extra:
        parts.append(m[[e]].astype(float))
    X = sm.add_constant(pd.concat(parts, axis=1).astype(float))
    y = m[outcome].astype(float)
    fit = sm.OLS(y, X).fit() if gaussian else sm.Logit(y, X).fit(disp=0)
    est = fit.params[exposure] if gaussian else float(np.exp(fit.params[exposure]))
    return round(float(est), 4), float(fit.pvalues[exposure]), int(fit.nobs)


def trend(flag: pd.Series, groups: pd.Series):
    ks, ns = [], []
    for g in _raw.GROUPS:
        s = flag[groups == g].dropna()
        ks.append(int((s > 0).sum())); ns.append(int(len(s)))
    from statsmodels.stats.contingency_tables import Table
    tab = np.array([[k, n - k] for k, n in zip(ks, ns)])
    res = Table(tab).test_ordinal_association(row_scores=np.arange(4), col_scores=np.array([1, 0]))
    n_total = float(sum(ns))
    z = float(res.zscore) * np.sqrt(n_total / (n_total - 1))
    return z, ks, ns


# ── E2.TIMING ───────────────────────────────────────────────────────────
print("\nE2.TIMING — from the raw dates")
lag_art = _raw.artifact("E2_TIMING_survey_lag.csv").set_index("survey_item")
conc_art = _raw.artifact("E2_TIMING_marker_concurrence.csv").set_index("marker_item")

obs = pd.read_csv(_raw.DS / "clinical_data/observation.csv", low_memory=False,
                  usecols=["person_id", "observation_source_value", "observation_date"])
obs["k"] = _raw._key(obs.observation_source_value)
obs["dt"] = pd.to_datetime(obs.observation_date, errors="coerce")
meas = pd.read_csv(_raw.DS / "clinical_data/measurement.csv", low_memory=False,
                   usecols=["person_id", "measurement_source_value", "measurement_date"])
meas["k"] = _raw._key(meas.measurement_source_value)
meas["dt"] = pd.to_datetime(meas.measurement_date, errors="coerce")


def first_dt(frame, key):
    return frame[frame.k == key].groupby("person_id").dt.min()


trop_dt = first_dt(meas, "import_troponin_t")
for key in ("mhoccur_rnl", "cestl", "paidscore"):
    lag = (trop_dt - first_dt(obs, key)).dt.days.dropna()
    _raw.check(f"E2.TIMING {key} median lag", float(lag.median()),
               float(lag_art.loc[key, "median_days_before_visit"]), tol=0.01)
    _raw.check(f"E2.TIMING {key} IQR lo", float(lag.quantile(0.25)), float(lag_art.loc[key, "iqr_lo"]), tol=0.01)
    _raw.check(f"E2.TIMING {key} IQR hi", float(lag.quantile(0.75)), float(lag_art.loc[key, "iqr_hi"]), tol=0.01)
    _raw.check(f"E2.TIMING {key} % same-day", round(100 * float((lag == 0).mean()), 1),
               float(lag_art.loc[key, "pct_same_day"]), tol=0.05)
    _raw.check(f"E2.TIMING {key} n paired", int(len(lag)), int(lag_art.loc[key, "n_paired"]))
alb_dt = first_dt(meas, "import_urine_albumin")
paired = pd.concat([alb_dt, trop_dt], axis=1, keys=["a", "b"]).dropna()
_raw.check("E2.TIMING albumin same-day as troponin %", round(100 * float((paired.a == paired.b).mean()), 1),
           float(conc_art.loc["import_urine_albumin", "pct_same_day_as_troponin"]), tol=0.05)
_raw.check("E2.TIMING the survey lag is a MEDIAN of weeks, not days",
           bool(lag_art.loc["mhoccur_rnl", "median_days_before_visit"] > 14), True)

# ── E3.1 ────────────────────────────────────────────────────────────────
print("\nE3.1 — ranking bookkeeping and two from-raw site refits")
rank = _raw.artifact("E3_1_ranking.csv")
site = _raw.artifact("E3_1_site_replication.csv")
core = _raw.artifact("E3_1_core_claims.csv")
core_site = _raw.artifact("E3_1_core_claims_by_site.csv")

# Survivor counts must equal q<0.05 counts in the source artifacts.
expected_surv = 0
for art, adj in [("E2C_1_sweep.csv", "damage"), ("E2C_3_sweep.csv", "damage"), ("E2A_1_sweep.csv", "damage"),
                 ("E2B_1_sweep.csv", "damage"), ("E2D_1_sweep.csv", "damage"), ("E2E_2_sweep.csv", "damage"),
                 ("E2F_1_models.csv", "full"), ("E2C_2.csv", "recognition+marker")]:
    t = _raw.artifact(art)
    t = t[t.adjustment == adj]
    expected_surv += int((t.q < 0.05).sum())
expected_surv += int((_raw.artifact("E2A_2_models.csv").q < 0.05).sum())
_raw.check("E3.1 FDR-survivor count equals the source artifacts", int(rank.crit_survives_adjustment.sum()), expected_surv)
_raw.check("E3.1 candidate count", len(rank), 207)
_raw.check("E3.1 criteria_met is the sum of the four booleans",
           bool((rank[["crit_effect_size", "crit_survives_adjustment", "crit_consistent_sites",
                       "crit_coherent_with_core"]].sum(axis=1) == rank.criteria_met).all()), True)
_raw.check("E3.1 no absurd site estimate survives as a valid fit",
           int(((site.estimate.abs() > 1e3) | (site.ci_hi > 1e4)).sum()), 0)
unstable = site[site.note.astype(str).str.contains("unstable", na=False)]
_raw.check("E3.1 unstable site fits carry NaN estimates", bool(unstable.estimate.isna().all()), True)
# A row with an unstable site fit must not be marked site-consistent.
for _, u in unstable.drop_duplicates(["experiment", "exposure", "outcome"]).iterrows():
    r = rank[(rank.experiment == u.experiment) & (rank.exposure == u.exposure) & (rank.outcome == u.outcome)]
    _raw.check(f"E3.1 {u.experiment} {u.exposure}/{u.outcome} not site-consistent after an unstable fit",
               bool(r.crit_consistent_sites.iloc[0]), False)
_raw.check("E3.1 unadjusted rows are absent (nothing ranks on crude numbers)",
           bool(rank.q.notna().sum() == len(rank)), True)

# From-raw refit: CES-D -> nerve within each site (age + severity), cohort-wide SD.
obs_v = pd.read_csv(_raw.DS / "clinical_data/observation.csv", low_memory=False,
                    usecols=["person_id", "observation_source_value", "value_as_number"])
obs_v["k"] = _raw._key(obs_v.observation_source_value)
v = pd.to_numeric(obs_v.value_as_number, errors="coerce")
obs_v["v"] = v.mask(v.isin(_raw.SPECIAL))
d["cesd"] = obs_v[obs_v.k == "cestl"].groupby("person_id").v.first()
d["cesd_pos"] = np.where(d.cesd.isna(), np.nan, (d.cesd >= 10).astype(float))
d["paid"] = obs_v[obs_v.k == "paidscore"].groupby("person_id").v.first()
for s in SITES:
    est, p, n = refit(d[d.site == s], "abn_nerve", "cesd", covariates=("age", "group"), sd_source=d)
    want = site[(site.experiment == "E2C.1") & (site.exposure == "cesd_total")
                & (site.outcome == "abn_nerve") & (site.site == s)].iloc[0]
    _raw.check(f"E3.1 CES-D -> nerve within {s} OR", est, float(want.estimate), tol=0.004)
    _raw.check(f"E3.1 CES-D -> nerve within {s} n", n, int(want.n))
for s in SITES:
    z, ks, ns = trend(d.loc[d.site == s, "unrec_kidney"], d.loc[d.site == s, "group"])
    want = core_site[(core_site.claim == "kidney unrecognized fraction falls with severity") & (core_site.site == s)].iloc[0]
    _raw.check(f"E3.1 kidney unrecognized trend within {s} |z|", round(abs(z), 3), abs(float(want.trend_z)), tol=0.002)
    _raw.check(f"E3.1 kidney unrecognized trend within {s} is negative", bool(want.trend_z < 0), True)
_raw.check("E3.1 the pre-declared Aim-2 nerve row meets all four criteria",
           int(rank[(rank.experiment == "E2C.1") & (rank.exposure == "cesd_total") & (rank.outcome == "abn_nerve")].criteria_met.iloc[0]), 4)
_raw.check("E3.1 the undiagnosed-range kidney row meets all four criteria",
           int(rank[(rank.experiment == "E2A.2") & (rank.exposure == "undiagnosed_range") & (rank.outcome == "abn_kidney")].criteria_met.iloc[0]), 4)

# ── E3.3 ────────────────────────────────────────────────────────────────
print("\nE3.3 — confirmatory reruns")
spec_text = (_raw.REPO / "papers/p1-unrecognized-damage/PRESPEC.md").read_text()
spec = json.loads(re.search(r"```json\s*\n(.*?)\n```", spec_text, re.S).group(1))
_raw.check("PRESPEC cutoffs match E1.0", (spec["cutoffs"]["acr_mg_g"], spec["cutoffs"]["troponin_ng_l"],
                                          spec["cutoffs"]["monofilament_missed"]), (30.0, 14.0, 2))

confirm = _raw.artifact("E3_3_aim1_confirmatory.csv")
e11 = _raw.artifact("E1_1_prevalence_by_group.csv").set_index(["organ", "stratum"])
e12 = _raw.artifact("E1_2_unrecognized_by_group.csv").set_index(["organ", "stratum"])
e12b = _raw.artifact("E1_2_population_burden.csv").set_index(["organ", "stratum"])
_raw.check("E3.3 reproduces_phase1 flag is True on every row", bool(confirm.reproduces_phase1.all()), True)
for organ in ["kidney", "heart", "nerve", "any"]:
    got = confirm[(confirm.claim == "prevalence") & (confirm.organ == organ)].set_index("stratum")
    _raw.check(f"E3.3 A1.1 {organ} overall k/n vs E1.1", (int(got.loc["Overall", "k"]), int(got.loc["Overall", "n"])),
               (int(e11.loc[(organ, "Overall"), "k"]), int(e11.loc[(organ, "Overall"), "n"])))
for organ in ["kidney", "heart", "either"]:
    got = confirm[(confirm.claim == "unrecognized_fraction") & (confirm.organ == organ)].set_index("stratum")
    _raw.check(f"E3.3 A1.2 {organ} overall vs E1.2", (int(got.loc["Overall", "k"]), int(got.loc["Overall", "n"])),
               (int(e12.loc[(organ, "Overall"), "k"]), int(e12.loc[(organ, "Overall"), "n"])))
    got = confirm[(confirm.claim == "population_burden") & (confirm.organ == organ)].set_index("stratum")
    _raw.check(f"E3.3 A1.3 {organ} overall vs E1.2 burden", (int(got.loc["Overall", "k"]), int(got.loc["Overall", "n"])),
               (int(e12b.loc[(organ, "Overall"), "k"]), int(e12b.loc[(organ, "Overall"), "n"])))
# And from raw, not just against Phase 1.
z, ks, ns = trend(d.unrec_either, d.group)
got = confirm[(confirm.claim == "population_burden") & (confirm.organ == "either")].set_index("stratum")
_raw.check("E3.3 either-organ burden from raw: k", sum(ks), int(got.loc["Overall", "k"]))
_raw.check("E3.3 either-organ burden from raw: n", sum(ns), int(got.loc["Overall", "n"]))
_raw.check("E3.3 either-organ burden trend |z| from raw", round(abs(z), 3), abs(float(got.loc["Overall", "trend_z"])), tol=0.002)

by_site = _raw.artifact("E3_3_aim1_by_site.csv")
for s in SITES:
    for claim, col in [("population_burden", "unrec_either"), ("prevalence", "abn_any")]:
        organ = "either" if claim == "population_burden" else "any"
        z, ks, ns = trend(d.loc[d.site == s, col], d.loc[d.site == s, "group"])
        want = by_site[(by_site.claim == claim) & (by_site.organ == organ) & (by_site.site == s)].iloc[0]
        _raw.check(f"E3.3 {claim}/{organ} within {s} |z|", round(abs(z), 3), abs(float(want.trend_z)), tol=0.002)
        _raw.check(f"E3.3 {claim}/{organ} within {s} n", sum(ns), int(want.n))
    z, ks, ns = trend(d.loc[d.site == s, "unrec_kidney"], d.loc[d.site == s, "group"])
    want = by_site[(by_site.claim == "unrecognized_fraction") & (by_site.organ == "kidney") & (by_site.site == s)].iloc[0]
    _raw.check(f"E3.3 kidney fraction within {s} |z|", round(abs(z), 3), abs(float(want.trend_z)), tol=0.002)
_raw.check("E3.3 either-organ burden rises at every site",
           bool((by_site[(by_site.claim == "population_burden") & (by_site.organ == "either")].trend_z > 0).all()), True)

# A1.2 both denominators and A1.5 — promised by the spec, present in the artifacts.
_raw.check("E3.3 A1.2 refusals-included denominator present",
           bool({"n_incl_refusals", "pct_incl_refusals"} <= set(confirm.columns)), True)
for organ in ["kidney", "heart", "either"]:
    got = confirm[(confirm.claim == "unrecognized_fraction") & (confirm.organ == organ)].set_index("stratum")
    _raw.check(f"E3.3 A1.2 {organ} refusals-included % vs E1.2", float(got.loc["Overall", "pct_incl_refusals"]),
               float(e12.loc[(organ, "Overall"), "pct_incl_refusals"]), tol=0.05)
a15 = _raw.artifact("E3_3_aim1_recognition_models.csv")
e14 = _raw.artifact("E1_4_models.csv").set_index(["organ", "model", "term"])
_raw.check("E3.3 A1.5 every term reproduces E1.4", bool(a15.reproduces_e14.all()), True)
_raw.check("E3.3 A1.5 term count equals E1.4", len(a15), len(e14))
# From raw: the recognition-sample size and the kidney model-A Insulin term.
kid = d[d.unrec_kidney.notna()].copy()
kid["insulin"] = (kid.group == "Insulin").astype(float)
n_kid = int(kid.dropna(subset=["unrec_kidney", "age", "site"]).shape[0])
_raw.check("E3.3 A1.5 kidney recognition sample n", n_kid,
           int(a15[(a15.organ == "kidney") & (a15.model.str.startswith("A"))].n_model.iloc[0]))
X = sm.add_constant(pd.concat([kid[["age"]].astype(float),
                               pd.get_dummies(kid.group.astype(str), prefix="g").drop(columns=["g_Healthy"]),
                               pd.get_dummies(kid.site.astype(str), prefix="s").drop(columns=["s_UAB"])], axis=1).astype(float))
fitA = sm.Logit(kid.unrec_kidney.astype(float), X).fit(disp=0)
_raw.check("E3.3 A1.5 kidney model A Insulin OR from raw", round(float(np.exp(fitA.params["g_Insulin"])), 3),
           float(a15[(a15.organ == "kidney") & (a15.model.str.startswith("A")) & (a15.term == "C(study_group_label)[T.Insulin]")].odds_ratio.iloc[0]), tol=0.002)

# The ladder is on a fixed sample as well as the Phase-2 sample.
ladder = _raw.artifact("E3_3_aim2_ladder.csv")
fixed = ladder[ladder["sample"].str.startswith("fixed") & (ladder.outcome == "abn_nerve")].set_index("step")
_raw.check("E3.3 ladder fixed-sample rungs share one n", int(fixed.n.nunique()), 1)
_raw.check("E3.3 ladder fixed-sample full spec equals the confirmatory nerve OR",
           float(fixed.loc["full spec (+ BMI + HbA1c)", "estimate"]),
           float(aim2.loc[("cesd_total", "abn_nerve"), "estimate"]) if False else float(_raw.artifact("E3_3_aim2_confirmatory.csv").set_index(["exposure", "outcome"]).loc[("cesd_total", "abn_nerve"), "estimate"]), tol=1e-6)
# The missing-data sensitivity keeps everyone.
imp = _raw.artifact("E3_3_aim2_missing_sensitivity.csv")
_raw.check("E3.3 A2.4 imputed family n = Phase-2 sample", int(imp[imp.outcome == "abn_nerve"].n.iloc[0]), 2265)

# Aim 2 with the spec covariates: age + BMI + HbA1c + severity + site.
aim2 = _raw.artifact("E3_3_aim2_confirmatory.csv").set_index(["exposure", "outcome"])
_raw.check("E3.3 A2 corrected family size", int(aim2.in_corrected_family.sum()), spec["aim2"]["fdr_family_size"])
for exposure, mine in [("cesd_total", "cesd"), ("cesd_positive", "cesd_pos")]:
    for outcome in ["abn_kidney", "abn_heart", "abn_nerve", "abn_any", "abn_multi"]:
        est, p, n = refit(d, outcome, mine, covariates=("age", "group", "site"), extra=("bmi", "hba1c"))
        want = aim2.loc[(exposure, outcome)]
        _raw.check(f"E3.3 A2 {exposure}/{outcome} OR", est, float(want.estimate), tol=0.004)
        _raw.check(f"E3.3 A2 {exposure}/{outcome} n", n, int(want.n))
est, p, n = refit(d, "missed", "cesd", covariates=("age", "group", "site"), extra=("bmi", "hba1c"), gaussian=True)
_raw.check("E3.3 A2 CES-D -> insensate sites beta", est, float(aim2.loc[("cesd_total", "monofilament_missed"), "estimate"]), tol=0.004)
# BH re-applied here from the p-values.
fam = aim2[aim2.in_corrected_family]
p_sorted = fam.p.sort_values()
m = len(p_sorted)
raw_q = p_sorted.to_numpy() * m / np.arange(1, m + 1)
q = pd.Series(np.minimum.accumulate(raw_q[::-1])[::-1].clip(max=1), index=p_sorted.index)
for idx in fam.index:
    _raw.check(f"E3.3 A2 q recomputed {idx[0]}/{idx[1]}", round(float(q.loc[idx]), 6), round(float(fam.loc[idx, "q"]), 6), tol=1e-6)
nerve = aim2.loc[("cesd_total", "abn_nerve")]
# The claim rule is checked as bookkeeping, not as an expectation: the summary's
# verdict must follow from q and direction in the artifact, whatever they are.
summary_a2 = _raw.artifact("E3_3_headline_summary.csv").set_index("claim")
rule_met = bool(nerve.q < 0.05 and aim2.loc[("cesd_positive", "abn_nerve"), "q"] < 0.05
                and (aim2.loc[("cesd_positive", "abn_nerve"), "estimate"] > 1) == (nerve.estimate > 1))
verdict = str(summary_a2.loc["A2.1 CES-D-10 -> nerve abnormal (spec covariates)", "verdict"])
_raw.check("E3.3 A2 summary verdict agrees with the claim rule applied to the artifact",
           verdict.startswith("claimed"), rule_met)
_raw.check("E3.3 A2 nerve is still the smallest-q outcome in the family",
           str(fam.q.idxmin()), str(("cesd_total", "abn_nerve")))

# Within-severity rows on the COHORT-WIDE SD (Amendment 1), checked for Insulin.
strata = _raw.artifact("E3_3_aim2_by_severity.csv").set_index("stratum")
ins = d[d.group == "Insulin"]
est, p, n = refit(ins, "abn_nerve", "cesd", covariates=("age", "site"), extra=("bmi", "hba1c"), sd_source=d)
_raw.check("E3.3 A2.2(e) Insulin OR on the cohort-wide SD", est, float(strata.loc["Insulin", "estimate"]), tol=0.004)
_raw.check("E3.3 A2.2(e) Insulin n", n, int(strata.loc["Insulin", "n"]))

# T1 primary: within Healthy + Pre-DM, age + site.
t1 = _raw.artifact("E3_3_track_undiagnosed.csv").set_index(["definition", "outcome"])
no_label = d.group.isin(["Healthy", "Pre-DM"])
d["undiagnosed_range"] = np.where(d.hba1c.isna(), np.nan, (no_label & d.hba1c.ge(6.5)).astype(float))
for outcome in ["abn_kidney", "abn_any", "abn_heart"]:
    est, p, n = refit(d[no_label], outcome, "undiagnosed_range", covariates=("age", "site"))
    want = t1.loc[("undiagnosed_range", outcome)]
    _raw.check(f"E3.3 T1 undiagnosed_range/{outcome} OR", est, float(want.estimate), tol=0.01)
    _raw.check(f"E3.3 T1 undiagnosed_range/{outcome} n", n, int(want.n))
prim = t1.loc[("undiagnosed_range", "abn_kidney")]
_raw.check("E3.3 T1 bootstrap interval brackets the point estimate",
           bool(prim.boot_ci_lo < prim.estimate < prim.boot_ci_hi), True)
_raw.check("E3.3 T1 exposed count", int(prim.n_exposed), int(d.loc[no_label].dropna(subset=["abn_kidney", "hba1c", "age", "site"]).undiagnosed_range.sum()))
_raw.check("E3.3 T1 family size", len(t1), spec["track_undiagnosed"]["fdr_family_size"])

# T2: QRS vs log troponin, OLS.
t2 = _raw.artifact("E3_3_track_ecg.csv").set_index(["exposure", "outcome"])
ecg_manifest = pd.read_csv(_raw.DS / "cardiac_ecg/manifest.tsv", sep="\t").drop_duplicates("person_id", keep="first")
ecg = ecg_manifest.set_index(ecg_manifest.person_id.astype(int))
d["qrsd"] = pd.to_numeric(ecg["QRSD"], errors="coerce")
d["qtc"] = pd.to_numeric(ecg["QTc"], errors="coerce")
est, p, n = refit(d, "log_trop", "qrsd", gaussian=True)
_raw.check("E3.3 T2 QRS -> log troponin beta", est, float(t2.loc[("qrsd_ms", "log_troponin"), "estimate"]), tol=0.004)
est, p, n = refit(d, "abn_heart", "qtc")
_raw.check("E3.3 T2 QTc -> abnormal troponin OR", est, float(t2.loc[("qtc_ms", "abn_heart"), "estimate"]), tol=0.004)
_raw.check("E3.3 T2 family size", len(t2), spec["track_ecg"]["fdr_family_size"])

# Burden sweep: two rungs re-derived from raw.
sweep = _raw.artifact("E3_3_burden_sweep.csv").set_index(["organ", "cutoff"])
d100 = _raw.build(acr=100.0)
flag = np.where(d100.abn_kidney.isna() | d100.sr_kidney.isna(), np.nan,
                (d100.abn_kidney.eq(1) & d100.sr_kidney.eq(0)).astype(float))
s = pd.Series(flag).dropna()
_raw.check("E3.3 burden sweep kidney ACR>=100 %", round(100 * float(s.mean()), 1),
           float(sweep.loc[("kidney", "100.0"), "burden_pct"]), tol=0.05)
d22 = _raw.build(troponin=22.0)
flag = np.where(d22.abn_heart.isna() | d22.sr_heart.isna(), np.nan,
                (d22.abn_heart.eq(1) & d22.sr_heart.eq(0)).astype(float))
s = pd.Series(flag).dropna()
_raw.check("E3.3 burden sweep heart cTnT>=22 %", round(100 * float(s.mean()), 1),
           float(sweep.loc[("heart", "22.0"), "burden_pct"]), tol=0.05)
_raw.check("E3.3 burden rises with severity at every rung (z > 0)", bool((sweep.burden_trend_z > 0).all()), True)

# Bootstrap intervals bracket the Wilson point estimate everywhere.
boot = _raw.artifact("E3_3_aim1_bootstrap.csv")
_raw.check("E3.3 bootstrap intervals bracket the point estimate on every row",
           bool(((boot.boot_lo <= boot.pct) & (boot.pct <= boot.boot_hi)).all()), True)

# Headline summary carries the same numbers as its sources.
summary = _raw.artifact("E3_3_headline_summary.csv").set_index("claim")
_raw.check("E3.3 summary quotes the nerve OR from the Aim-2 artifact",
           f"{nerve.estimate}" in str(summary.loc["A2.1 CES-D-10 -> nerve abnormal (spec covariates)", "value"]), True)
_raw.check("E3.3 summary quotes the T1 OR from the track artifact",
           f"{prim.estimate}" in str(summary.loc["T1 undiagnosed-range -> kidney abnormal", "value"]), True)

_raw.report("E3")
