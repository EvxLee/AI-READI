"""Independent verification of Phase-2 tracks A, B, D, E and F, plus E2.AGE.

Same contract as the Phase-1 verifiers: rebuild every exposure and outcome from
the raw cached files, refit through a different statsmodels API than the runners
use, and diff against the committed artifacts. Imports nothing from `aireadi`.

Four Phase-2 defects are re-derived here from scratch rather than checked against
the fixed code, because a fix that only agrees with itself proves nothing:

* the Dexcom "Low"/"High" sentinel strings, re-counted straight from the JSON;
* the Garmin manifest averages that survive the sentinel scrub while still being
  outside the instrument's own scale;
* the urine-albumin reporting floor;
* the non-monotonic PhenX coding, re-checked against the raw value frequencies.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
import statsmodels.api as sm

import _raw

print("=" * 78)
print("VERIFY E2 TRACKS — A (glycaemia), B (BMI), D (wearables), E (ECG), F (SDOH)")
print("=" * 78)

d = _raw.build()

# Rebuild the Phase-2 outcome columns independently.
alb_floored = d.alb.mask(d.alb.eq(0), 0.01 / 2)
acr_floored = alb_floored / d.crt.where(d.crt > 0) * 1000
d["log_acr"] = np.log(acr_floored.where(acr_floored > 0))
d["log_trop"] = np.log(d.trop.where(d.trop > 0))
d["missed"] = 10 - d.mono_worse
d["abn_any"] = np.where(d.n_abn.isna(), np.nan, (d.n_abn > 0).astype(float))
d["abn_multi"] = np.where(d.n_abn.isna(), np.nan, (d.n_abn >= 2).astype(float))


def refit(frame, outcome, exposure, *, covariates=("age", "group", "site"),
          gaussian=False, scale=True, extra=(), sd_source=None):
    cols = ["age"] if "age" in covariates else []
    m = frame.dropna(subset=[outcome, exposure] + cols + list(extra)).copy()
    if "group" in covariates:
        m = m[m.group.notna()]
    if "site" in covariates:
        m = m[m.site.notna()]

    x = m[[exposure]].astype(float)
    if scale and set(np.round(m[exposure].dropna().unique(), 6)) - {0.0, 1.0}:
        x = x / float((sd_source if sd_source is not None else frame)[exposure].std())
    parts = [x]
    if cols:
        parts.append(m[cols].astype(float))
    if "group" in covariates:
        parts.append(pd.get_dummies(m.group.astype(str), prefix="g").drop(columns=["g_Healthy"]))
    if "site" in covariates:
        parts.append(pd.get_dummies(m.site.astype(str), prefix="s").drop(columns=["s_UAB"]))
    for e in extra:
        parts.append(m[[e]].astype(float))

    X = sm.add_constant(pd.concat(parts, axis=1).astype(float))
    y = m[outcome].astype(float)
    fit = (sm.OLS(y, X).fit() if gaussian else sm.Logit(y, X).fit(disp=0))
    est = fit.params[exposure] if gaussian else float(np.exp(fit.params[exposure]))
    return round(float(est), 4), float(fit.pvalues[exposure]), int(fit.nobs)


# ── Track B: BMI ────────────────────────────────────────────────────────
print("\nE2B.1 — BMI")
bmi_sweep = _raw.artifact("E2B_1_sweep.csv").set_index(["exposure", "outcome", "adjustment"])
d["bmi_obese"] = np.where(d.bmi.isna(), np.nan, (d.bmi >= 30).astype(float))

for exposure, col in [("bmi", "bmi"), ("bmi_obese", "bmi_obese")]:
    for outcome, mine, gauss in [("abn_kidney", "abn_kidney", False),
                                 ("abn_heart", "abn_heart", False),
                                 ("abn_nerve", "abn_nerve", False),
                                 ("abn_any", "abn_any", False),
                                 ("monofilament_missed", "missed", True)]:
        est, p, n = refit(d, mine, col, gaussian=gauss)
        want = bmi_sweep.loc[(exposure, outcome, "damage")]
        _raw.check(f"E2B.1 {exposure}/{outcome} adjusted est", est,
                   float(want.estimate), tol=0.004)
        _raw.check(f"E2B.1 {exposure}/{outcome} n", n, int(want.n))

_raw.check("E2B.1 BMI is NOT associated with kidney damage",
           bool(float(bmi_sweep.loc[("bmi", "abn_kidney", "damage"), "p"]) > 0.05), True)
_raw.check("E2B.1 BMI IS associated with heart, nerve and any-organ damage",
           all(float(bmi_sweep.loc[("bmi", o, "damage"), "q"]) < 0.05
               for o in ["abn_heart", "abn_nerve", "abn_any"]), True)

# ── Track A: glycaemia and the CGM sentinel defect ──────────────────────
print("\nE2A.1 — glycaemia, and the Dexcom sentinel strings")
cgm_sweep = _raw.artifact("E2A_1_sweep.csv").set_index(["exposure", "outcome", "adjustment"])

# Re-count the sentinels from the raw JSON. This is the defect's own evidence.
manifest = pd.read_csv(_raw.DS / "wearable_blood_glucose/manifest.tsv", sep="\t")
tokens, affected, streams = {"Low": 0, "High": 0}, 0, {}
for fp in manifest.glucose_filepath:
    path = _raw.DS / str(fp).lstrip("/")
    if not path.exists():
        continue
    try:
        records = json.loads(path.read_text())["body"]["cgm"]
    except Exception:
        continue
    values = [(r.get("blood_glucose") or {}).get("value") for r in records]
    found = [v for v in values if isinstance(v, str)]
    if found:
        affected += 1
        for v in found:
            tokens[v] = tokens.get(v, 0) + 1
    numeric = [40.0 if v == "Low" else 400.0 if v == "High" else v for v in values]
    numeric = pd.to_numeric(pd.Series(numeric), errors="coerce").dropna()
    numeric = numeric[numeric.between(40, 400)]
    if len(numeric) >= 12:
        streams[str(path.parent.name)] = numeric

_raw.check("E2A.1 Dexcom writes 'High' as a string", tokens.get("High", 0), 34449)
_raw.check("E2A.1 Dexcom writes 'Low' as a string", tokens.get("Low", 0), 5183)
_raw.check("E2A.1 participants with at least one sentinel reading", affected, 495)
_raw.check("E2A.1 every participant yields a usable stream once sentinels are kept",
           len(streams), 2245)

built = pd.DataFrame({
    "person_id": list(streams),
    "glucose_mean": [float(s.mean()) for s in streams.values()],
    "glucose_cv": [float(s.std(ddof=1) / s.mean() * 100) for s in streams.values()],
    "tar_180": [float((s > 180).mean() * 100) for s in streams.values()],
}).set_index("person_id")
built.index = built.index.astype(int)

g = d.join(built, how="left")
for exposure, col, gauss in [("hba1c", "hba1c", False),
                             ("glucose_mean", "glucose_mean", False),
                             ("tar_180", "tar_180", False),
                             ("glucose_cv", "glucose_cv", False)]:
    for outcome, mine in [("abn_kidney", "abn_kidney"), ("abn_any", "abn_any")]:
        est, p, n = refit(g, mine, col)
        want = cgm_sweep.loc[(exposure, outcome, "damage")]
        _raw.check(f"E2A.1 {exposure}/{outcome} adjusted est", est,
                   float(want.estimate), tol=0.02)
        _raw.check(f"E2A.1 {exposure}/{outcome} n", n, int(want.n), )

# The headline of the incremental analysis: CV adds beyond mean glucose, TAR does not.
incremental = _raw.artifact("E2A_1_incremental.csv").set_index(["exposure", "outcome"])
_raw.check("E2A.1 CV adds to mean glucose for kidney",
           bool(float(incremental.loc[("glucose_cv", "abn_kidney"),
                                      "q_with_mean_glucose"]) < 0.05), True)
_raw.check("E2A.1 TAR>180 adds nothing to mean glucose, any outcome",
           bool((incremental.loc["tar_180", "q_with_mean_glucose"] >= 0.05).all()), True)

est_cv, p_cv, n_cv = refit(g, "abn_kidney", "glucose_cv", extra=("glucose_mean",))
_raw.check("E2A.1 CV-with-mean-glucose kidney OR reproduces", est_cv,
           float(incremental.loc[("glucose_cv", "abn_kidney"), "or_with_mean_glucose"]),
           tol=0.02)

# ── E2A.2 discordance ───────────────────────────────────────────────────
print("\nE2A.2 — glycaemia/label discordance")
disc = _raw.artifact("E2A_2_models.csv").set_index(["definition", "outcome"])
counts = _raw.artifact("E2A_2_discordance.csv").set_index("group")

no_label = d.group.isin(["Healthy", "Pre-DM"])
d["undiagnosed_range"] = np.where(d.hba1c.isna(), np.nan,
                                  (no_label & d.hba1c.ge(6.5)).astype(float))
_raw.check("E2A.2 no-label participants with HbA1c >= 6.5%",
           int(d.undiagnosed_range.sum()),
           int(counts.loc["No diabetes label, HbA1c >= 6.5%", "n_discordant"]))

universe = d[no_label]
for outcome, mine in [("abn_kidney", "abn_kidney"), ("abn_any", "abn_any")]:
    est, p, n = refit(universe, mine, "undiagnosed_range", covariates=("age", "site"))
    want = disc.loc[("undiagnosed_range", outcome)]
    _raw.check(f"E2A.2 undiagnosed_range/{outcome} OR", est, float(want.estimate), tol=0.01)
    _raw.check(f"E2A.2 undiagnosed_range/{outcome} n", n, int(want.n))

_raw.check("E2A.2 undiagnosed-range participants carry more kidney damage",
           bool(float(disc.loc[("undiagnosed_range", "abn_kidney"), "estimate"]) > 1
                and float(disc.loc[("undiagnosed_range", "abn_kidney"), "q"]) < 0.05), True)
_raw.check("E2A.2 bootstrap interval excludes 1 for the kidney result",
           bool(float(disc.loc[("undiagnosed_range", "abn_kidney"), "boot_ci_lo"]) > 1), True)
_raw.check("E2A.2 the CGM definition replicates the kidney result",
           bool(float(disc.loc[("undiagnosed_range_cgm", "abn_kidney"), "q"]) < 0.05), True)
_raw.check("E2A.2 insulin-at-target shows no damage difference",
           bool((disc.loc["insulin_at_target", "q"] >= 0.05).all()), True)

# ── Track D: the Garmin plausibility defect ─────────────────────────────
print("\nE2D.1 — wearables, and the contaminated manifest averages")
activity = pd.read_csv(_raw.DS / "wearable_activity_monitor/manifest.tsv", sep="\t")
activity["person_id"] = activity.person_id.astype(int)

# Sentinel scrub only -- the documented cleaning -- then count what survives it
# outside the instrument's own scale. That gap is the defect.
hr = pd.to_numeric(activity.average_heartrate_bpm, errors="coerce").replace(0, np.nan)
stress = pd.to_numeric(activity.average_stress_level, errors="coerce").replace(-2, np.nan)
sleep = pd.to_numeric(activity.average_sleep_hours, errors="coerce") * 24
steps = pd.to_numeric(activity.average_daily_activity, errors="coerce")

_raw.check("E2D.1 heart rates under 30 bpm surviving the sentinel scrub",
           int((hr.notna() & hr.lt(30)).sum()), 12)
_raw.check("E2D.1 NEGATIVE stress scores surviving the sentinel scrub",
           int((stress.notna() & stress.lt(0)).sum()), 113)
_raw.check("E2D.1 lowest surviving heart rate is not a measurement",
           bool(hr.min() < 1), True)
_raw.check("E2D.1 sleep averages outside 1-14 h surviving the scrub",
           int((sleep.notna() & ~sleep.between(1, 14)).sum()), 131)
_raw.check("E2D.1 zero step averages surviving the scrub",
           int((steps.notna() & steps.le(0)).sum()), 147)

# .to_numpy() matters here. Passing `index=` alongside a Series REINDEXES it
# rather than relabelling it, so the person_id index would be matched against the
# Series' own 0..n positional index and silently keep only the handful of rows
# where a person_id happened to equal a row number.
clean = pd.DataFrame({
    "heart_rate": hr.where(hr.between(30, 120)).to_numpy(),
    "stress": stress.where(stress.between(0, 100)).to_numpy(),
    "sleep_hours": sleep.where(sleep.between(1, 14)).to_numpy(),
    "steps": steps.where(steps.between(1, 50000)).to_numpy(),
    "spo2": pd.to_numeric(activity.average_oxygen_saturation_pct,
                          errors="coerce").replace(0, np.nan).to_numpy(),
}, index=pd.Index(activity.person_id, name="person_id"))
_raw.check("E2D.1 wearable join aligns on person_id (not positional)",
           bool(clean.steps.notna().sum() > 1900), True)

w = d.join(clean, how="left")
wear = _raw.artifact("E2D_1_sweep.csv").set_index(["exposure", "outcome", "adjustment"])
for exposure in ("steps", "heart_rate", "stress", "sleep_hours", "spo2"):
    for outcome, mine in [("abn_heart", "abn_heart"), ("abn_any", "abn_any")]:
        est, p, n = refit(w, mine, exposure)
        want = wear.loc[(exposure, outcome, "damage")]
        _raw.check(f"E2D.1 {exposure}/{outcome} adjusted est", est,
                   float(want.estimate), tol=0.004)
        _raw.check(f"E2D.1 {exposure}/{outcome} n", n, int(want.n))

sensitivity = _raw.artifact("E2D_1_plausibility_sensitivity.csv").set_index(
    ["exposure", "outcome"])
_raw.check("E2D.1 the plausibility fix changes conclusions",
           int(sensitivity.changed_conclusion.sum()), 3)

# ── Track E: ECG ────────────────────────────────────────────────────────
print("\nE2E — ECG statements and metrics")
ecg_manifest = pd.read_csv(_raw.DS / "cardiac_ecg/manifest.tsv", sep="\t")
_raw.check("E2E manifest rows", len(ecg_manifest), 2257)
_raw.check("E2E distinct participants", ecg_manifest.person_id.nunique(), 2251)
_raw.check("E2E machine_text is the device name, not the interpretation",
           ecg_manifest.machine_text.nunique(), 1)

tiers = _raw.artifact("E2E_1_tiers.csv").set_index("tier")
unrec = _raw.artifact("E2E_1_unrecognized.csv").set_index(["ecg_pattern", "self_report"])

# Re-harvest a sample of headers and re-derive the tier independently.
deduped = ecg_manifest.drop_duplicates("person_id", keep="first")
definite, unconfirmed_seen, checked = 0, 0, 0
for rec in deduped.itertuples(index=False):
    path = _raw.DS / str(rec.wfdb_hea_filepath).lstrip("/")
    if not path.exists():
        continue
    checked += 1
    text = path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"unconfirmed", text, re.IGNORECASE):
        unconfirmed_seen += 1
    lines = [ln.strip() for ln in text.splitlines()]
    statements = []
    for ln in lines:
        m = re.match(r"^#\s*(?:interpretation_comment|comment)_\d+(?:_key)?\s*:\s*(.*)$",
                     ln, re.IGNORECASE)
        if m and m.group(1).strip() and not re.search(r"unconfirmed", m.group(1), re.I):
            statements.append(m.group(1).strip())
    prior = [s for s in statements if "infarct" in s.lower()
             and "acute" not in s.lower() and "recent" not in s.lower()]
    if any("consider" not in s.lower() and "probable" not in s.lower() for s in prior):
        definite += 1

_raw.check("E2E.1 headers re-harvested", checked, 2251)
_raw.check("E2E.1 every record carries an unconfirmed stamp", unconfirmed_seen, checked)
_raw.check("E2E.1 definite prior-infarct count re-derived",
           definite, int(tiers.loc["definite prior infarct", "n_participants"]))
_raw.check("E2E.1 most machine-read prior infarcts have no reported heart attack",
           bool(float(unrec.loc[("Definite machine-read prior infarct",
                                 "Self-reported heart attack (mhoccur_mi)"),
                                "pct_unrecognized"]) > 50), True)

ecg = deduped.set_index(deduped.person_id.astype(int))
for column in ("Rate", "PR", "QRSD", "QT", "QTc"):
    d[column.lower()] = pd.to_numeric(ecg[column], errors="coerce")
coherence = _raw.artifact("E2E_2_coherence.csv").set_index(["metric", "outcome"])
for column, label in [("qrsd", "QRS duration (ms)"), ("qtc", "QTc interval (ms)"),
                      ("qt", "QT interval (ms)")]:
    est, p, n = refit(d, "abn_heart", column)
    _raw.check(f"E2E.2 {label} vs abnormal troponin OR", est,
               float(coherence.loc[(label, "abn_heart"), "estimate"]), tol=0.004)
_raw.check("E2E.2 QRS duration tracks the heart marker",
           bool(float(coherence.loc[("QRS duration (ms)", "log_troponin"), "q"]) < 0.05), True)
_raw.check("E2E.2 QT alone does NOT (only the rate-corrected QTc does)",
           bool(float(coherence.loc[("QT interval (ms)", "log_troponin"), "q"]) >= 0.05
                and float(coherence.loc[("QTc interval (ms)", "log_troponin"), "q"]) < 0.05),
           True)

# ── Track F: SDOH scoring ───────────────────────────────────────────────
print("\nE2F.1 — SDOH scoring")
obs = pd.read_csv(_raw.DS / "clinical_data/observation.csv", low_memory=False,
                  usecols=["person_id", "observation_source_value", "value_as_number"])
obs["k"] = (obs.observation_source_value.astype(str).str.split(",", n=1).str[0]
            .str.strip().str.lower())
v = pd.to_numeric(obs.value_as_number, errors="coerce")
obs["v"] = v.mask(v.isin(_raw.SPECIAL))


def item(key):
    return obs[obs.k == key].groupby("person_id").v.first()


# The non-monotonic coding, re-established from the raw frequencies rather than
# taken from the fix.
pxhi1 = item("pxhi1")
counts_hi = pxhi1.value_counts()
_raw.check("E2F.1 pxhi1 modal value is the SECURE level, not an endpoint",
           int(counts_hi.idxmax()), 1)
_raw.check("E2F.1 pxhi1 is non-monotonic (both 0 and 2 are rarer than 1)",
           bool(counts_hi.get(0, 0) < counts_hi.get(1, 0)
                and counts_hi.get(2, 0) < counts_hi.get(1, 0)), True)
pxfi1 = item("pxfi1")
counts_fi = pxfi1.value_counts()
_raw.check("E2F.1 pxfi1 level 1 is RARER than level 2 (answer order, not severity)",
           bool(counts_fi.get(1, 0) < counts_fi.get(2, 0)), True)

# Rebuild the scores independently and check them against the by-group artifact.
food = pd.concat([item(f"pxfi{i}").isin([1, 2]).astype(float).mask(item(f"pxfi{i}").isna())
                  for i in (1, 2)]
                 + [item(f"pxfi{i}").eq(1).astype(float).mask(item(f"pxfi{i}").isna())
                    for i in (3, 4, 5)], axis=1)
food_score = food.sum(axis=1, skipna=True).mask(food.notna().sum(axis=1).lt(4))
access = pd.concat([item(k) for k in ("pxahc8", "pxahc9", "pxahc10")], axis=1)
access_score = access.eq(1).sum(axis=1).astype(float).mask(access.notna().sum(axis=1).lt(2))

by_group = _raw.artifact("E2F_1_by_group.csv").set_index("study_group_label")
scored = pd.DataFrame({"food": food_score, "access": access_score}).join(d[["group"]])
for level in _raw.GROUPS:
    sub = scored[scored.group == level]
    _raw.check(f"E2F.1 food-insecurity mean, {level}", round(float(sub.food.mean()), 3),
               float(by_group.loc[level, "food_insecurity"]), tol=0.002)
    _raw.check(f"E2F.1 access-barrier mean, {level}", round(float(sub.access.mean()), 3),
               float(by_group.loc[level, "healthcare_access_barriers"]), tol=0.002)

_raw.check("E2F.1 hardship rises monotonically across severity (scoring sanity)",
           bool(by_group.loc[_raw.GROUPS, "food_insecurity"].is_monotonic_increasing
                and by_group.loc[_raw.GROUPS, "healthcare_access_barriers"]
                .is_monotonic_increasing), True)

models = _raw.artifact("E2F_1_models.csv")
full = models[models.adjustment == "full"]
survivors = full[full.q < 0.05]
_raw.check("E2F.1 the surviving association runs OPPOSITE to the falling-through-"
           "the-cracks hypothesis", bool((survivors.estimate < 1).all()), True)

# ── E2.AGE ──────────────────────────────────────────────────────────────
print("\nE2.AGE — age as a negative confounder")
age_table = _raw.artifact("E2_AGE_suppression.csv").set_index(["exposure", "outcome"])
summary = _raw.artifact("E2_AGE_summary.csv").set_index("pattern")

d["cesd"] = item("cestl")
for column, mine in [("cesd_total", "cesd"), ("bmi", "bmi")]:
    r_age = round(float(d[[mine, "age"]].corr().iloc[0, 1]), 3)
    _raw.check(f"E2.AGE r({column}, age)", r_age,
               float(age_table.loc[(column, "abn_any"), "r_exposure_age"]), tol=0.002)
_raw.check("E2.AGE every damage outcome rises with age",
           bool((age_table.r_outcome_age > 0).all()), True)
opposite = age_table[age_table.opposite_signs]
_raw.check("E2.AGE age adjustment raises the estimate in EVERY opposite-sign pair",
           bool(opposite.adjusted_exceeds_crude.all()), True)
_raw.check("E2.AGE opposite-sign pair count", len(opposite),
           int(summary.iloc[0]["n_pairs"]))

_raw.report("E2 TRACKS")
