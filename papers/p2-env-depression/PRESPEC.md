# Paper 2 — Pre-specified analysis plan (PRESPEC)

**Overhauled: 2026-08-17.** This document was originally frozen 2026-08-10
with CES-D-10 depression score as the sole primary outcome. Project-head
direction on 2026-08-11 pivoted the paper toward glycemic control and BMI
as environmental-exposure outcomes, with depression demoted first to a
side analysis and, as of this overhaul, dropped from the plan entirely —
none of that work was ever run (see `RESULTS_LOG.md`'s history for the
full pivot timeline; the depression-era experiment list and both interim
amendments are preserved there and in git history, not repeated here).
This is now the plan going forward. Once committed, changes to what's
written here are deviations, not edits — log them in `RESULTS_LOG.md` with
a reason, don't rewrite this file silently.

---

## 1. Objective

Does personal environmental exposure (indoor air quality, temperature,
humidity) independently predict glycemic control and BMI in a type 2
diabetes cohort, after adjusting for age, diabetes severity group, and
clinical site? Three linked lines of work, run in this order:

- **Severity-pair models (EP.1–EP.7, done):** for every pair of the 4
  severity groups (Healthy, Pre-DM, Oral Med, Insulin) — 3 adjacent pairs
  plus 3 non-adjacent pairs as a gradient sanity check — a binary logistic
  model on the same environmental/BMI/wearable predictor set, reporting
  which predictors separate that pair and in which direction.
- **Primary model (EG.1, done):** does an environmental term (log PM2.5)
  survive in a model of glycemic control, once BMI, wearable behavior,
  age, and severity group are controlled for? This is the paper's central
  claim.
- **Mediation follow-up (EG.2–EG.3, done; EG.4+ open):** EG.1 came back
  null for the environmental term. Project-head hypothesis: pollution
  doesn't act on blood sugar directly, but discourages activity and raises
  BMI, which then worsens glycemic control. EG.2/EG.3 test the first link
  (pollution → activity/BMI); a later step should test the second link
  (activity/BMI → glycemic control) and, ideally, the full mediation
  chain in one model.

BMI is a secondary outcome in its own right — its relationship to
environmental exposure is reported directly (EG.2/EG.3), not folded
silently into another model's coefficient table.

Full rationale, literature framing, and honest limitations live in
`PLAN.md`; this document exists to lock down exactly what gets run, on
what data.

## 2. Cohort and data source

- Dataset: AI-READI v3.0.0, Study ID `1438dd73-c4cb-48b8-8fa8-c858771207c3`
  (the canonical value in `src/aireadi/constants.py` — confirm with
  `cohort.qc_report()` before trusting any pull; a mismatch means the wrong
  container or a new release).
- Expected cohort: 2,280 participants — Healthy 776, Pre-DM 560, Oral Med
  686, Insulin 258 (`constants.EXPECTED_GROUP_N`).
- Base table: `cohort.build_core_table()` (severity, age, site, BMI,
  HbA1c, comorbidity count, CGM manifest mean glucose, cleaned Garmin
  summaries), extended with:
  - `environmental_summary.csv` (`build_env_table.py`, this folder) — per-
    participant PM2.5, temperature, humidity, light, VOC, NOx aggregated
    from raw Lee Lab Anura sensor streams.
  - `cgm_glycemic_metrics.csv` (`build_cgm_table.py`, this folder) — the
    richer glycemic-control profile built from raw Dexcom G6 streams (see
    Section 3), not the manifest's single mean-glucose value.
- All cleaning (survey special codes, Garmin error codes, sleep
  fraction-to-hours, HbA1c field selection) is handled by the shared
  toolbox per `docs/CAVEATS.md`, not redefined in paper-specific code.

## 3. Outcomes

**Primary — glycemic control**, built from raw CGM streams
(`build_cgm_table.py`): mean, SD, CV, GMI, % time above 140 mg/dL, % time
above 180 mg/dL, % time below 70 mg/dL (hypoglycemia), spikes/day above
180, minutes/day above 180, average spike peak, and MAGE. Each metric has
its own coverage — `wearables.parse_dexcom_json` returns `None` for
streams with <12 valid readings (2 of 2,245 participants affected; see
ECGM.1 in `RESULTS_LOG.md`).

**Secondary — BMI** (`cohort.build_core_table()`'s `bmi`), reported
against environmental exposure directly (EG.2/EG.3), not just as a
predictor inside the glycemic-control model.

**Group-membership outcome (severity pairs only, EP.1–EP.7):**
`study_group_label`, recoded as a 0/1 indicator within each of the 6
pairwise comparisons.

## 4. Predictors

**Primary (pre-specified as the variable of greatest interest):**
- `log1p(PM2.5)` — raw PM2.5 is not used; the distribution is extremely
  right-skewed (median ~3, max ~1,178 µg/m³).

**Secondary (environmental):** temperature, humidity, light (lch0), VOC
Index, NOx Index.

**Secondary (wearable/behavioral):** `mean_glucose` (CGM manifest mean,
included in the severity-pair models as a check against the richer
CGM-derived outcomes), `heart_rate`, `stress`, `sleep_hours`, `steps`,
`active_calories`.

**BMI** is a predictor in the severity-pair and primary glycemic-control
models (Sections 6–7) and an outcome in its own right in the mediation
models (Section 8).

## 5. Covariates (every model, no exceptions)

`age`, `study_group_label` where the model isn't itself testing severity
group membership, `clinical_site` (pooled models: dummy-coded; per-site
models: implicit, one fit per site).

## 6. Severity-pair models (EP.1–EP.7, all done)

| ID | Pair | Model |
|---|---|---|
| EP.1 | Healthy vs Pre-DM (adjacent) | Binary logistic, predictors = Section 4 set + age + site dummies |
| EP.2 | Pre-DM vs Oral Med (adjacent) | Same |
| EP.3 | Oral Med vs Insulin (adjacent) | Same |
| EP.4 | — | Cross-pair synthesis of EP.1–EP.3: predictors significant in >1 adjacent boundary |
| EP.5 | Healthy vs Oral Med (non-adjacent) | Same model, gradient sanity check |
| EP.6 | Healthy vs Insulin (non-adjacent, widest gap) | Same |
| EP.7 | Pre-DM vs Insulin (non-adjacent) | Same |

Results: `mean_glucose` significant in all 7; BMI significant at every
pair including "Healthy"; PM2.5/VOC significant only at pairs including
"Insulin". Full detail in `RESULTS_LOG.md`.

## 7. Primary model (EG.1, done)

Each of the 4 candidate glycemic-control outcomes (glucose_mean,
glucose_cv, tar_180, spikes_per_day_180 — chosen after checking skew)
regressed on: log1p(PM2.5) + other env vars + BMI + wearables + age +
severity-group dummies + site dummies (OLS).

**Result:** log(PM2.5) not significant in any of the 4 (p=0.99, 0.11,
0.30, 0.16). BMI significant for glucose_mean (p=0.037) and glucose_cv
(p=0.0007, negative direction). Decision: rescope, not kill — see the
mediation hypothesis in Section 8, and the overcontrol concern in EG.7
below.

## 8. Mediation follow-up (EG.2–EG.4 done; EG.5–EG.6 open)

EG.1's null environmental term prompted a mediation hypothesis
(2026-08-15, project head): pollution may not act on glycemic control
directly, but may discourage activity and raise BMI, each of which then
worsens glycemic control.

| ID | Model |
|---|---|
| EG.2 | First link, pooled: steps / active_calories / bmi ~ log1p(PM2.5) + age + site dummies, all 3 sites together |
| EG.3 | First link, per-site: same model, refit separately within UW / UAB / UCSD, no pooling |
| EG.4 | Second link: 4 candidate glycemic-control outcomes ~ steps + active_calories + bmi + age + severity dummies + site dummies |

**EG.2/EG.3 result:** log(PM2.5) significant (pooled) for all 3 outcomes,
but direction is mixed relative to the hypothesis — BMI moves as expected
(more pollution → higher BMI), while steps and active_calories move
**opposite** to it (more pollution → more activity). Per-site: the effect
is strongest and most consistent at UW; UAB shows it only for steps; UCSD
only for BMI. Not yet resolved whether this is a real site-specific
pattern or a confound.

**EG.4 result:** steps not significant for any of the 4 glycemic-control
outcomes; active_calories significant for 2/4; BMI significant for 1/4
(glucose_cv, negative direction — counter to the usual expectation, likely
the same severity-group absorption issue as EG.1). Steps looks like a dead
end for the mediation story on both links; active_calories is the more
promising activity measure.

**EG.7/EG.8 result (done, 2026-08-17):** dropping severity group confirms
overcontrol — log(PM2.5) becomes significant for glucose_cv and tar_180.
But EG.8's per-site check found this only replicates at UCSD, not UW or
UAB — real, but not yet a uniform cohort-wide effect.

**Open — EG.6, EG.9 planned, not yet run:**

| ID | Purpose |
|---|---|
| EG.6 | A single combined mediation model chaining pollution → activity/BMI → glycemic control, rather than two separate regressions (EG.2–EG.4 style) — needed to report an actual indirect effect with its own significance test, not just "both links looked plausible separately." Depends on EG.5's result for which activity measure to use. |
| EG.9 | VIF / multicollinearity diagnostics on EG.1's predictor set (BMI, severity group, glucose, PM2.5 are expected to be collinear per `docs/CAVEATS.md`). High VIF would give a more mundane explanation for EG.1's null pollution term than "no true effect," and should be reported either way. |

## 8a. Follow-up batch to EG.7/EG.8 (EG.10–EG.16, done 2026-08-18)

Project head's follow-up to EG.7/EG.8's site-concentrated pollution
effect, relayed 2026-08-18. All six pieces done:

| ID | What | Result |
|---|---|---|
| EG.10 | Severity-group distribution within EG.7a's significant-outcome (glucose_cv, tar_180) model rows, vs. the full cohort. | Not skewed — matches cohort within 0.4 points for every group. Rules out one severity group driving the effect. |
| EG.11 | Per-site descriptive stats for PM2.5/NOx/VOC (mean, median, SD, IQR, max). | UAB is the most-polluted and most-variable site, not UCSD — the site where EG.8's effect replicated is *not* the most exposed site. |
| EG.12 | Build intraday (within-day) and interday (between-day) glucose variability metrics from raw CGM streams — the standard Rodbard-style decomposition. `data/processed/p2/glucose_variability_metrics.csv`, gitignored. | N=2,245 pulled, 2,243 parsed; 4 participants lack the 2 valid days needed for interday variance. |
| EG.13 | Repeat EG.7a/EG.8's design with NOx instead of PM2.5. | Not significant pooled; significant at UCSD only for 3 of 4 outcomes — same site-concentration pattern as PM2.5. |
| EG.14 | Repeat with VOC instead of PM2.5. | Not significant pooled; weaker and less consistent per-site than PM2.5/NOx. |
| EG.15 | Repeat the pollution tests (PM2.5/NOx/VOC) against EG.12's new intraday/interday outcomes. | **PM2.5 → interday_glucose_variance is significant pooled (p=1.1e-05) and replicates at 2 of 3 sites (UAB, UCSD)** — the most cross-site-consistent finding in the paper so far. |
| EG.16 | Reverse-direction, exploratory only: log(PM2.5) ~ glycemic marker + bmi + age + site, for glucose_mean/glucose_cv/intraday/interday variance and hba1c. | All 5 markers significant; hba1c strongest (p=2.0e-06). Read as correlational, not causal — flagged as such in the write-up. |

## 9. CGM-derived metrics build and age comparison (ECGM.1–ECGM.2, done)

| ID | What |
|---|---|
| ECGM.1 | Build `cgm_glycemic_metrics.csv` from raw Dexcom streams (Section 3's metric list). N=2,245 streams pulled, 2,243 parsed (2 failed, <12 valid readings). |
| ECGM.2 | Within the insulin-dependent group, do glycemic-control metrics differ between age<70 (N=189) and 70+ (N=69)? Only glucose_cv differs significantly (p=0.008); mean glucose, TAR, TBR, spikes, MAGE do not. |

## 10. Baseline descriptive (E1.1, done)

General-purpose baseline table (not severity-pair, not a model): mean /
median / IQR for every Section 3–4 variable, overall and by severity
group, with Kruskal-Wallis across groups. N=2,280 merged
(core+wearable+environmental). 12 of 17 variables differed significantly
(p<0.05) across the 4 severity groups. Confirms the merged table looks
right before any model runs on it — kept as ID `E1.1` for continuity with
`RESULTS_LOG.md`, despite the `E1.x` numbering predating this overhaul.

## 11. Sample sizes (confirmed against the current pull)

EP.1–EP.7: N ranges 703–1,242 depending on pair (listwise deletion within
each pair's predictor set). EG.1: N=1,944. EG.2: N=2,110–2,225 depending
on outcome. ECGM.1: N=2,243 of 2,245 pulled. E1.1: N=2,280. All numbers are
from the current pull under `src/aireadi`, not carried over from any
earlier scoping phase.

## 12. Data-handling rules

Not duplicated here — see `docs/CAVEATS.md` for the authoritative list
(Garmin error codes, sleep fraction, PM2.5 skew, sensor-placement
confound, HbA1c field name, VIF/multicollinearity expectation between
BMI/severity/glucose, the `inf`-in-raw-sensor-data failure mode). Every
experiment above assumes those rules are already applied via the shared
toolbox, not reimplemented per-notebook.

## 13. Reporting rule

Every run — including a null result — gets one entry in `RESULTS_LOG.md`
via `aireadi.results.save()` or `.log()`, with a keep/kill/rescope
decision. Aggregate outputs only go to `papers/p2-env-depression/results/`;
nothing keyed by `person_id` is ever written there.
