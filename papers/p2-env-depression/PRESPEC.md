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

## Amendment — 2026-08-11, direction from project head

**This is a deviation from the frozen sections below, not a silent rewrite —
those sections are left intact for the audit trail.** Sections 1–10 below
described a paper with CES-D-10 depression score as the single, primary
outcome. As of 2026-08-11 that changes:

1. **Primary outcome becomes glycemic control**, not depression, built from
   participants' raw CGM streams (`build_cgm_table.py`, this folder) rather
   than the manifest's single mean-glucose value — mean, SD, CV, GMI, %
   time above 140 mg/dL, % time above 180 mg/dL, % time below 70 mg/dL
   (hypoglycemia), spikes/day above 180, minutes/day above 180, average
   spike peak, and MAGE. Every one of these needs its own N and coverage
   check the same way Section 2 did for the original variables — do not
   assume full coverage; some Dexcom streams may be too short (<12 readings)
   to produce a metric, same failure mode `wearables.parse_dexcom_json`
   already guards against.
2. **BMI is promoted from Section 4's predictor list to a secondary outcome
   in its own right** — its own relationship to environmental exposure and
   to glycemic control gets reported directly, not folded silently into the
   primary model's coefficient table.
3. **CES-D-10 (Sections 3, 6 Aim 1, 7 Aim 2 as originally written) becomes a
   tertiary, side analysis** — every experiment ID in Sections 6–7 below
   (E1.1–E1.7, E2.1–E2.6) still runs as specified, just understood now as
   the depression track rather than the paper's primary claim.
4. **New near-term step, ahead of a single combined 4-group model:** pairwise
   binary logistic regressions at each adjacent severity boundary (Healthy
   vs Pre-DM, Pre-DM vs Oral Med, Oral Med vs Insulin), same
   environmental/BMI/wearable predictor set as Section 4, adjusted for age
   and site. Tracked as EP.1–EP.3, with EP.4 as a cross-pair synthesis
   (which predictors are significant at more than one boundary). Already run
   once, 2026-08-11 (`RESULTS_LOG.md`) — treat that run the same way the
   original Aim 1/Aim 2 scoping runs are treated: disclosed, not hidden,
   official confirmation still to come once the CGM metrics and the combined
   model (EG.1) exist to compare against.
5. **New primary model (EG.1, not yet run):** a glycemic-control metric
   (candidate: `tar_180` or `glucose_cv`, final choice to be confirmed once
   `cgm_glycemic_metrics.csv` is built and its distribution inspected — see
   `PLAN.md`) regressed on the same predictor set as Section 4, plus age and
   severity group as covariates. Whether the environmental term is
   significant in this model is the paper's central claim under the pivot.
6. **New experiment (ECGM.2, not yet run):** compare CGM-derived metrics
   between the insulin-dependent age<70 subgroup and the 70+ group, to test
   whether glycemic control differs by age within the highest-severity
   group or is a pure severity effect.

## Amendment — 2026-08-15, direction from project head

EG.1 (Amendment §5) found log(PM2.5) not significant for any of 4
glycemic-control outcomes once BMI, wearables, age, and severity group are
covariates. Project head's read: pollution likely doesn't act on blood
sugar directly — it may instead discourage physical activity and raise
BMI, which then worsens glycemic control (mediation chain: worse pollution
→ less activity / higher BMI → worse blood sugar control). Also requested,
verbatim: run one version pooling all three clinical sites together, and
another separating them, since "these versions both provide different
useful information potentially."

7. **New experiments EG.2 (pooled) and EG.3 (per-site):** test the first
   link only — does log(PM2.5) predict steps, active_calories, and BMI,
   controlling for age? EG.2 pools all 3 sites (site as a covariate); EG.3
   refits the same model separately within each site. Both already run,
   2026-08-15 — see `RESULTS_LOG.md`. Result: log(PM2.5) is significant
   (pooled) for all three outcomes, but direction is **mixed relative to
   the hypothesis** — BMI moves in the hypothesized direction (higher
   pollution → higher BMI), while steps and active_calories move in the
   **opposite** direction (higher pollution → more activity, not less).
   Per-site breakdown shows the effect is strongest and most consistent at
   UW; not yet clear whether this is a real site-specific pattern or a
   confound (e.g., a covariate not yet in the model, or a Simpson's-paradox
   effect from between-site differences). Flagged for project-head
   discussion before proceeding to the second mediation link
   (activity/BMI → glycemic control).

Everything else in this document — the dataset, the covariates in Section 5,
`docs/CAVEATS.md`'s data-handling rules, the reporting rule in Section 10 —
is unchanged. Sections 1–10 below are preserved as originally frozen and
should be read as "the depression track's specification," not superseded.

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
