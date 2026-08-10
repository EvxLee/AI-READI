# Paper 2 — Pre-specified analysis plan (PRESPEC)

**Frozen: 2026-08-10.** This document is committed and dated before any further
inferential test is run under the restructured repo (`src/aireadi` toolbox).
It is derived from `PLAN.md` (local-only; the full narrative plan, carried
over unchanged from the pre-restructure `GAMEPLAN.md`) and from the
experiment list in that document. Once committed, changes to what's written
here are deviations, not edits — log them in `RESULTS_LOG.md` with a reason,
don't rewrite this file silently.

**Disclosure required by this project's honesty rule:** the core Aim 1 model
(equivalent to E1.2 below) and the Aim 2 subgroup comparison (equivalent to
E2.2) were already run once during scoping, before this document existed —
see the "Scoping results" table in `RESULTS_LOG.md`. The runs under this
PRESPEC are the official, documented confirmation, not a first look. The
eventual methods section must say so plainly.

---

## 1. Objective

Two aims, one outcome (CES-D-10 depression score), tested against three
variable domains — personal indoor environmental exposure, body composition
(BMI), and wearable-measured physiology/behavior — across the AI-READI type 2
diabetes severity spectrum.

- **Aim 1 (primary):** across the whole cohort, which of the three domains
  independently predicts CES-D-10 score, after adjusting for age, diabetes
  severity group, and clinical site?
- **Aim 2 (secondary, well-powered):** within the insulin-dependent,
  under-70 subgroup — already flagged in `EDA_FINDINGS.md` Part 10 as
  carrying the cohort's highest BMI and PM2.5, independent of each other and
  of activity — does elevated depression line up with any of those same
  risk factors, or is it independent of them too?

Full rationale, literature framing, and honest limitations live in `PLAN.md`;
this document exists to lock down exactly what gets run, on what data, before
any of it happens.

## 2. Cohort and data source

- Dataset: AI-READI v3.0.0, Study ID `1438dd73-c4cb-48b8-8fa8-c858771207c3`
  (the canonical value in `src/aireadi/constants.py` — confirm with
  `cohort.qc_report()` before trusting any pull; a mismatch means the wrong
  container or a new release).
- Expected cohort: 2,280 participants — Healthy 776, Pre-DM 560, Oral Med
  686, Insulin 258 (`constants.EXPECTED_GROUP_N`).
- Base table: `cohort.build_core_table()` (severity, age, site, BMI, HbA1c,
  CES-D-10, PAID-5, comorbidity count, CGM mean glucose, cleaned Garmin
  summaries), extended by `cohort.build_p2_table()` for the environmental
  block (PM2.5, temperature, humidity, light, VOC, NOx). **`build_p2_table()`
  is not implemented yet** — defining the per-participant environmental
  aggregation is a prerequisite for E1.1 and is tracked as its own step, not
  part of this freeze.
- All cleaning (survey special codes, Garmin error codes, sleep
  fraction-to-hours, HbA1c field selection, troponin below-detection — not
  relevant here) is handled by the shared toolbox per `docs/CAVEATS.md`, not
  redefined in paper-specific code.

## 3. Outcome

- **CES-D-10 total score** (`cestl` / `cohort.build_core_table()`'s
  `cesd_total`), range 0–30. Items `ces5`/`ces8` are already reverse-scored
  in the source data — do not re-reverse them.
- **Binary robustness outcome:** `cesd_positive`, the ≥10 screen-positive
  cutoff already computed by `build_core_table()`.

## 4. Predictors

**Primary (pre-specified as the two variables of greatest interest):**
- `log1p(PM2.5)` — raw PM2.5 is not used; the distribution is extremely
  right-skewed (scoping-phase median ~3, max ~1,178 µg/m³).
- `bmi`

**Secondary (environmental):** temperature, humidity, light (lch0), VOC
Index, NOx Index — reported individually (E1.4) and as part of extended
sensitivity models, not the primary model.

**Secondary (wearable/behavioral):** `mean_glucose` (CGM, included as a
glycemic-control check rather than a primary depression predictor — it
overlaps with severity group by construction), `heart_rate`, `stress`,
`sleep_hours`, `steps`, `active_calories`.

**Tertiary / sensitivity only (lowest device coverage):** `spo2`,
respiratory rate. Excluded from the primary model (E1.2/E1.3) specifically
to avoid losing ~370 participants to one lower-coverage stream; included only
in the extended sensitivity model (E1.5).

## 5. Covariates (every model, no exceptions)

`age`, `study_group_label` (4-level ordered severity), `clinical_site`.

## 6. Aim 1 — models and experiments

| ID | Model / method |
|---|---|
| E1.1 | Descriptive table: mean/median/IQR for every variable above plus CES-D-10, overall and by severity group |
| E1.2 (primary) | OLS: `cesd_total ~ log1p(pm25) + bmi + steps + stress + heart_rate + sleep_hours + age + study_group_label + clinical_site` |
| E1.3 | Logistic: same right-hand side, outcome `cesd_positive` |
| E1.4 | Univariate Spearman (each predictor vs. `cesd_total`) + Kruskal-Wallis (`cesd_total` across severity groups) |
| E1.5 | E1.2 plus `spo2` and `mean_glucose` |
| E1.6 | E1.2 re-run separately within each `clinical_site` |
| E1.7 | E1.2 re-run (a) excluding the known 1,145 °C sensor artifact, (b) with PM2.5 winsorized at the 99th percentile, (c) with VIF diagnostics on every predictor |

## 7. Aim 2 — subgroup, models, and experiments

**Subgroup definition:** `study_group_label == "Insulin"` and `age < 70`.
Scoping-phase N = 188; reconfirm under `build_core_table()` +
`build_p2_table()` before treating as final.

| ID | Model / method |
|---|---|
| E2.1 | Descriptive profile of the subgroup: BMI, PM2.5, steps, active_calories, stress, heart_rate, sleep_hours, `cesd_total` |
| E2.2 (headline) | Mann-Whitney U on `cesd_total`, subgroup vs. rest of cohort; proportion test on `cesd_positive` rate |
| E2.3 | Spearman, `cesd_total` vs. each of BMI, PM2.5, steps, active_calories, stress, heart_rate, sleep_hours — subgroup only |
| E2.4 | OLS within subgroup: `cesd_total ~ bmi + log1p(pm25) + steps + stress + heart_rate + sleep_hours` (explicitly under-powered relative to E1.2 at N=188 — report accordingly) |
| E2.5 | Median-split (subgroup's own BMI and steps medians) into four cells; compare mean `cesd_total` across cells |
| E2.6 | E2.2 and E2.3 repeated separately for the 40-54 and 55-69 age bands within the subgroup |

## 8. Sample sizes to reconfirm

Scoping-phase numbers (pre-toolbox, pre-restructure) were: core model N =
1,951; extended model (with SpO2/CGM) N = 1,587; Aim 2 subgroup N = 188 (out
of 2,277 with a non-missing CES-D-10 score). These must be reconfirmed by
`cohort.qc_report()` and a fresh listwise-deletion count once
`build_p2_table()` exists — do not carry them forward as final without
re-running E1.1 against the current pull.

## 9. Data-handling rules

Not duplicated here — see `docs/CAVEATS.md` for the authoritative list
(survey special codes, Garmin error codes, sleep fraction, PM2.5 skew,
sensor-placement confound, HbA1c field name, VIF/multicollinearity
expectation between BMI/severity/glucose). Every experiment above assumes
those rules are already applied via the shared toolbox, not reimplemented
per-notebook.

## 10. Reporting rule

Every run — including a null result — gets one entry in `RESULTS_LOG.md` via
`aireadi.results.save()` or `.log()`, with a keep/kill/rescope decision.
Aggregate outputs only go to `papers/p2-env-depression/results/`; nothing
keyed by `person_id` is ever written there.
