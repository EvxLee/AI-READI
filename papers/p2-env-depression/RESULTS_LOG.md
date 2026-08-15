# Paper 2 — Results log

Every run gets one line here, **including nulls**. Numbers are copied from
executed outputs, never from memory.

**Rules**

- One row per run: ID, one-line method, one-line result, keep/kill decision.
- `PRESPEC.md` is frozen once dated and committed. Deviations get logged here
  with justification.
- The primary Aim 1 model ran during scoping, before the plan was finalised.
  That is disclosed in the methods; the official run is documented
  confirmation, not a first look.
- Aggregate outputs go in `results/`, keyed by experiment ID. Nothing keyed by
  `person_id`.
- The Status table's **Description** column is filled in for every planned
  experiment up front (cross-referenced from `PRESPEC.md`'s experiment
  list), independent of whether that experiment has run yet. `Key
  output`/`One-line result`/`Keep-Kill` only get filled in once a run
  actually happens.
- `aireadi.results.save()` auto-fills a row's `Status`/`Key
  output`/`One-line result`/`Keep-Kill` cells but rewrites the entire table
  row when it does, which would wipe the `Description` cell. After any
  auto-update, re-check that row's Description is still intact before
  committing, and restore it if not.

## Amendment — 2026-08-11, direction from project head

Primary outcome pivots from CES-D-10 depression score to diabetes/glycemic
control (built from raw CGM streams, not the manifest mean). BMI promoted
to a secondary outcome in its own right. CES-D-10 work (all of E1.x/E2.x
below) continues as a tertiary, side-analysis track, not the headline. Full
reasoning in `PLAN.md`'s "v3 pivot" section and `PRESPEC.md`'s Amendment.
New experiment IDs added below: **EP.1-EP.4** (pairwise adjacent-severity
binary models, already run), **ECGM.1-ECGM.2** (CGM-derived glycemic
metrics build + age-group comparison), **EG.1** (primary model: glycemic
control ~ environment + BMI + wearables + age + severity).

**Added 2026-08-12:** **EP.5-EP.7** (the 3 remaining non-adjacent severity
pairs — Healthy vs Oral Med, Healthy vs Insulin, Pre-DM vs Insulin — a
gradient/continuum sanity check requested by the project head alongside the
original adjacent-pair ask: "you might as well do every pair of those four
groups").

## Scoping results (pre-plan, disclosed in methods)

| Run | Result |
|---|---|
| Aim 1 main model, N = 1,951 complete cases | CES-D-10 ~ log(PM2.5) + BMI + steps + stress + HR + sleep + age + severity + site. Indoor PM2.5 p = 1e-6; BMI p = 1.3e-5; insulin dependence p = 0.0018; younger age significant. |
| Aim 2 subgroup, insulin-dependent under 70, N = 188 | Mean CES-D-10 8.62 vs 5.61 for the rest; 36.7% positive screens vs 18.5%. |

Open question: is the subgroup's depression excess explained by its elevated
BMI / PM2.5 / wearable profile, or independent? Either answer publishes.

## Status

| ID | Status | Key output | Description — what we want from it | One-line result | Keep/Kill |
|----|--------|-----------|-----------------|-----------------|-----------|
| E1.1 | done | `results/E1_1.csv` | Baseline population picture across environment, BMI, wearables, and CES-D-10 — confirms the merged table looks right before any model runs on it. Track: primary (general-purpose, not depression-specific). | N=2280 participants merged (core+wearable+environmental). 12/17 variables differ significantly (p<0.05, Kruskal-Wallis) across the 4 severity groups. | keep |
| EP.1 | done | `results/EP_1.csv` | N=1151. Significant (p<0.05): mean_glucose (higher -> more Pre-DM-like, p=7.74e-11), bmi (higher -> more Pre-DM-like, p=0.000347). | keep |
| EP.2 | done | `results/EP_2.csv` | N=1063. Significant (p<0.05): mean_glucose (higher -> more Oral Med-like, p=7.1e-21), sleep_hours (higher -> more Pre-DM-like, p=0.00133), age (higher -> more Oral Med-like, p=0.00795), heart_rate (higher -> more Oral Med-like, p=0.0132), mean_temp (higher -> more Oral Med-like, p=0.0163), stress (higher -> more Oral Med-like, p=0.042). | keep |
| EP.3 | done | `results/EP_3.csv` | N=794. Significant (p<0.05): mean_glucose (higher -> more Insulin-like, p=1.08e-13), log_pm25 (higher -> more Insulin-like, p=0.0076), mean_voc (higher -> more Insulin-like, p=0.0192), steps (higher -> more Oral Med-like, p=0.0426). | keep |
| EP.4 | done | `results/EP_4.csv` | 1 predictor(s) significant across >1 adjacent-pair boundary: mean_glucose. Full per-predictor breakdown in EP_combined.csv. | keep |
| EP.5 | done | `results/EP_5.csv` | Non-adjacent pairwise binary model, Healthy vs Oral Med (skips Pre-DM) — gradient sanity check: do adjacent-pair predictors stay significant/same-direction across a wider severity gap? Track: primary. | N=1242. Significant (p<0.05): mean_glucose (p=3.4e-44), bmi (p<0.0001), mean_temp (p=0.0012), heart_rate (p=0.0261). | keep |
| EP.6 | done | `results/EP_6.csv` | Non-adjacent pairwise binary model, Healthy vs Insulin (widest gap, skips Pre-DM and Oral Med). Track: primary. | N=882. Significant (p<0.05): mean_glucose (p=1.5e-32), bmi (p<0.0001), mean_temp (p<0.0001), heart_rate (p=0.0041), mean_nox (p=0.0052), steps (p=0.0076, more Healthy-like), mean_voc (p=0.0228). | keep |
| EP.7 | done | `results/EP_7.csv` | Non-adjacent pairwise binary model, Pre-DM vs Insulin (skips Oral Med). Track: primary. | N=703. Significant (p<0.05): mean_glucose (p=2.0e-26), mean_temp (p=0.0005), heart_rate (p=0.0014), age (p=0.0055), mean_voc (p=0.0061), steps (p=0.0095, more Pre-DM-like). | keep |
| ECGM.1 | done | `data/processed/p2/cgm_glycemic_metrics.csv` (gitignored, participant-level; not a `results/` artifact) | Build per-participant glycemic-control metrics (mean, SD, CV, GMI, TAR140, TAR180, TBR70, spikes/day, spike-minutes/day, spike peak, MAGE) from raw Dexcom streams — this is the new primary outcome's data source. Track: primary. | N=2245 streams pulled, 2243 parsed successfully (2 had <12 valid readings). No coverage issue. | keep |
| ECGM.2 | done | `results/ECGM_2.csv` | Do CGM-derived glycemic metrics differ between the insulin-dependent age<70 subgroup and the 70+ group — is glucose control an age effect within the highest-severity group, or purely a severity effect? Track: primary/tertiary crossover (feeds both). | N(<70)=189, N(70+)=69. Only glucose_cv differs significantly (p=0.008, higher variability in 70+); mean glucose, TAR, TBR, spikes, MAGE do not differ by age within the insulin-dependent group. | keep |
| EG.1 | done | `results/EG_1.csv` (+ `EG_1_summary.csv`, `EG_1_<outcome>.csv` per candidate outcome) | Primary model: glycemic-control metric ~ log(PM2.5) + other env vars + BMI + wearables + age + severity group (+ site). Is the environmental term significant once severity is controlled for — the paper's central claim under the pivot. Track: primary. | N=1944 (4 candidate outcomes: glucose_mean, glucose_cv, tar_180, spikes_per_day_180). log(PM2.5) NOT significant in any of the 4 (p=0.99, 0.11, 0.30, 0.16). BMI significant for glucose_mean (p=0.037) and glucose_cv (p=0.0007, negative direction). | rescope — see takeaways below |
| EG.2 | done | `results/EG_2.csv` | Mediation step 1, pooled across all 3 sites: does log(PM2.5) predict activity (steps, active_calories) and BMI, controlling for age + site dummies? Tests project head's hypothesis chain (worse pollution -> less activity/higher BMI -> worse glycemic control) at its first link. Track: primary. | N=2110-2225. log(PM2.5) significant (p<0.05) for all 3 outcomes: steps (p=1.09e-06, coef=+412.9 — MORE steps, opposite of hypothesized direction), active_calories (p=0.000207, coef=+12.3 — also opposite direction), bmi (p=1.11e-11, coef=+1.08 — matches hypothesized direction). | keep — surprising direction on steps/active_calories flagged for discussion |
| EG.3 | done | `results/EG_3.csv` | Mediation step 1, same model refit separately within each of the 3 clinical sites (no pooling) — checks whether EG.2's pooled effect is a real within-site relationship or an artifact of between-site differences. Track: primary. | log(PM2.5) significant at: UW (steps, active_calories, bmi — all 3, all positive direction, matching pooled), UAB (steps only, positive), UCSD (bmi only, positive). Direction consistent with EG.2 everywhere it's significant; effect is strongest and most consistent at UW. | keep |
| E1.2 | not started | | Depression-track test: does PM2.5, BMI, or wearable behavior independently predict depression score once age, severity, and site are controlled for? Track: tertiary/side (was primary pre-pivot). | | |
| E1.3 | not started | | Robustness check: do the same predictors hold when depression is treated as the ≥10 clinical screen (yes/no) instead of a continuous score? Track: tertiary/side. | | |
| E1.4 | not started | | Which single variables carry a depression signal on their own, before any adjustment? Track: tertiary/side. | | |
| E1.5 | not started | | Does the E1.2 story change once the lower-coverage variables (SpO2, CGM glucose) are added back in? Track: tertiary/side. | | |
| E1.6 | not started | | Does the result replicate independently at each of the three clinical sites, or is one site driving it? Track: tertiary/side. | | |
| E1.7 | not started | | Does the result survive known data-quality issues (broken temperature sensor, PM2.5 outliers) and variable overlap (VIF)? Track: tertiary/side. | | |
| E2.1 | not started | | Full profile of the highest-risk subgroup (insulin-dependent, under 70), including depression for the first time. Track: tertiary/side — this is the "pollution + activity + depression in the younger/worse-diabetes subgroup" thread the project head asked to keep exploring. | | |
| E2.2 | not started | | Headline subgroup test: is this subgroup's depression burden actually higher than the rest of the cohort's? Track: tertiary/side. | | |
| E2.3 | not started | | Within the subgroup, does depression line up with its already-elevated BMI, PM2.5, or wearable profile? Track: tertiary/side. | | |
| E2.4 | not started | | Adjusted version of E2.3: does any variable still predict depression within the subgroup once the others are controlled for? Track: tertiary/side. | | |
| E2.5 | not started | | Does the specific high-BMI + low-activity combination the team originally asked about show elevated depression? Track: tertiary/side. | | |
| E2.6 | not started | | Is the subgroup's depression gap driven by one specific age band, or true across both? Track: tertiary/side. | | |

## Log

<!-- Append entries below. Newest last. Format:

### <ID> — <YYYY-MM-DD>
**Method:** one line.
**Result:** one line, numbers copied from output.
**Decision:** keep / kill / rescope, and why.
**Output:** results/<ID>_*.csv

-->

### E1.1 — 2026-08-10
**Method:** Descriptive stats (n/mean/median/IQR overall; n/mean/median by severity group; Kruskal-Wallis across groups) for all 17 pre-specified variables (PRESPEC.md sections 3-4), built on cohort.build_core_table() plus environmental_summary.csv
**Result:** N=2280 participants merged (core+wearable+environmental). 12/17 variables differ significantly (p<0.05, Kruskal-Wallis) across the 4 severity groups.
**Decision:** keep
**Output:** results/E1_1.csv

### EP.1 — 2026-08-11
**Method:** Binary logistic regression: outcome=1 if Pre-DM else 0 (restricted to Healthy/Pre-DM), predictors=log_pm25, mean_temp, mean_hum, mean_light, mean_voc, mean_nox, bmi, mean_glucose, steps, stress, heart_rate, sleep_hours, active_calories, age + clinical_site dummies
**Result:** N=1151. Significant (p<0.05): mean_glucose (higher -> more Pre-DM-like, p=7.74e-11), bmi (higher -> more Pre-DM-like, p=0.000347).
**Decision:** keep
**Output:** results/EP_1.csv

### EP.2 — 2026-08-11
**Method:** Binary logistic regression: outcome=1 if Oral Med else 0 (restricted to Pre-DM/Oral Med), predictors=log_pm25, mean_temp, mean_hum, mean_light, mean_voc, mean_nox, bmi, mean_glucose, steps, stress, heart_rate, sleep_hours, active_calories, age + clinical_site dummies
**Result:** N=1063. Significant (p<0.05): mean_glucose (higher -> more Oral Med-like, p=7.1e-21), sleep_hours (higher -> more Pre-DM-like, p=0.00133), age (higher -> more Oral Med-like, p=0.00795), heart_rate (higher -> more Oral Med-like, p=0.0132), mean_temp (higher -> more Oral Med-like, p=0.0163), stress (higher -> more Oral Med-like, p=0.042).
**Decision:** keep
**Output:** results/EP_2.csv

### EP.3 — 2026-08-11
**Method:** Binary logistic regression: outcome=1 if Insulin else 0 (restricted to Oral Med/Insulin), predictors=log_pm25, mean_temp, mean_hum, mean_light, mean_voc, mean_nox, bmi, mean_glucose, steps, stress, heart_rate, sleep_hours, active_calories, age + clinical_site dummies
**Result:** N=794. Significant (p<0.05): mean_glucose (higher -> more Insulin-like, p=1.08e-13), log_pm25 (higher -> more Insulin-like, p=0.0076), mean_voc (higher -> more Insulin-like, p=0.0192), steps (higher -> more Oral Med-like, p=0.0426).
**Decision:** keep
**Output:** results/EP_3.csv

### EP.4 — 2026-08-11
**Method:** Cross-pair synthesis of EP.1-EP.3: predictors significant (p<0.05) in more than one adjacent-severity-boundary logistic model, i.e. a consistent direction of effect as severity increases rather than a one-boundary artifact.
**Result:** 1 predictor(s) significant across >1 adjacent-pair boundary: mean_glucose. Full per-predictor breakdown in EP_combined.csv.
**Decision:** keep
**Output:** results/EP_4.csv

### EG.1_glucose_mean — 2026-08-11
**Method:** OLS: glucose_mean ~ log1p(PM2.5) + env vars + BMI + wearables + age + severity-group dummies + site dummies
**Result:** N=1944, R2=0.286. log_pm25 p=0.988, bmi p=0.0366.
**Decision:** keep
**Output:** results/EG_1_glucose_mean.csv

### EG.1_glucose_cv — 2026-08-11
**Method:** OLS: glucose_cv ~ log1p(PM2.5) + env vars + BMI + wearables + age + severity-group dummies + site dummies
**Result:** N=1944, R2=0.228. log_pm25 p=0.114, bmi p=0.000712.
**Decision:** keep
**Output:** results/EG_1_glucose_cv.csv

### EG.1_tar_180 — 2026-08-11
**Method:** OLS: tar_180 ~ log1p(PM2.5) + env vars + BMI + wearables + age + severity-group dummies + site dummies
**Result:** N=1944, R2=0.312. log_pm25 p=0.299, bmi p=0.179.
**Decision:** keep
**Output:** results/EG_1_tar_180.csv

### EG.1_spikes_per_day_180 — 2026-08-11
**Method:** OLS: spikes_per_day_180 ~ log1p(PM2.5) + env vars + BMI + wearables + age + severity-group dummies + site dummies
**Result:** N=1944, R2=0.251. log_pm25 p=0.156, bmi p=0.0648.
**Decision:** keep
**Output:** results/EG_1_spikes_per_day_180.csv

### EG.1 — 2026-08-11
**Method:** Cross-outcome summary of the primary model (see EG.1_<outcome> rows for each individual fit): tests log(PM2.5) and BMI against 4 candidate CGM-derived glycemic-control outcomes (glucose_mean, glucose_cv, tar_180, spikes_per_day_180).
**Result:** Across 4 candidate glycemic-control outcomes (glucose_mean, glucose_cv, tar_180, spikes_per_day_180), log(PM2.5) significant (p<0.05) in 0/4; BMI significant in 2/4. See EG_1_summary.csv for per-outcome detail.
**Decision:** keep
**Output:** results/EG_1.csv

### ECGM.2 — 2026-08-11
**Method:** Mann-Whitney U comparing 8 CGM-derived glycemic-control metrics between the insulin-dependent age<70 subgroup and the insulin-dependent 70+ group.
**Result:** Insulin-dependent subgroup: N(<70)=189, N(70+)=69. Metrics differing significantly by age (p<0.05, Mann-Whitney): glucose_cv.
**Decision:** keep
**Output:** results/ECGM_2.csv

### EP.1 — 2026-08-12
**Method:** Binary logistic regression: outcome=1 if Pre-DM else 0 (restricted to Healthy/Pre-DM), predictors=log_pm25, mean_temp, mean_hum, mean_light, mean_voc, mean_nox, bmi, mean_glucose, steps, stress, heart_rate, sleep_hours, active_calories, age + clinical_site dummies
**Result:** N=1151. Significant (p<0.05): mean_glucose (higher -> more Pre-DM-like, p=7.74e-11), bmi (higher -> more Pre-DM-like, p=0.000347).
**Decision:** keep
**Output:** results/EP_1.csv

### EP.2 — 2026-08-12
**Method:** Binary logistic regression: outcome=1 if Oral Med else 0 (restricted to Pre-DM/Oral Med), predictors=log_pm25, mean_temp, mean_hum, mean_light, mean_voc, mean_nox, bmi, mean_glucose, steps, stress, heart_rate, sleep_hours, active_calories, age + clinical_site dummies
**Result:** N=1063. Significant (p<0.05): mean_glucose (higher -> more Oral Med-like, p=7.1e-21), sleep_hours (higher -> more Pre-DM-like, p=0.00133), age (higher -> more Oral Med-like, p=0.00795), heart_rate (higher -> more Oral Med-like, p=0.0132), mean_temp (higher -> more Oral Med-like, p=0.0163), stress (higher -> more Oral Med-like, p=0.042).
**Decision:** keep
**Output:** results/EP_2.csv

### EP.3 — 2026-08-12
**Method:** Binary logistic regression: outcome=1 if Insulin else 0 (restricted to Oral Med/Insulin), predictors=log_pm25, mean_temp, mean_hum, mean_light, mean_voc, mean_nox, bmi, mean_glucose, steps, stress, heart_rate, sleep_hours, active_calories, age + clinical_site dummies
**Result:** N=794. Significant (p<0.05): mean_glucose (higher -> more Insulin-like, p=1.08e-13), log_pm25 (higher -> more Insulin-like, p=0.0076), mean_voc (higher -> more Insulin-like, p=0.0192), steps (higher -> more Oral Med-like, p=0.0426).
**Decision:** keep
**Output:** results/EP_3.csv

### EP.5 — 2026-08-12
**Method:** Binary logistic regression: outcome=1 if Oral Med else 0 (restricted to Healthy/Oral Med), predictors=log_pm25, mean_temp, mean_hum, mean_light, mean_voc, mean_nox, bmi, mean_glucose, steps, stress, heart_rate, sleep_hours, active_calories, age + clinical_site dummies
**Result:** N=1242. Significant (p<0.05): mean_glucose (higher -> more Oral Med-like, p=3.41e-44), bmi (higher -> more Oral Med-like, p=7.69e-07), mean_temp (higher -> more Oral Med-like, p=0.00119), heart_rate (higher -> more Oral Med-like, p=0.0261).
**Decision:** keep
**Output:** results/EP_5.csv

### EP.6 — 2026-08-12
**Method:** Binary logistic regression: outcome=1 if Insulin else 0 (restricted to Healthy/Insulin), predictors=log_pm25, mean_temp, mean_hum, mean_light, mean_voc, mean_nox, bmi, mean_glucose, steps, stress, heart_rate, sleep_hours, active_calories, age + clinical_site dummies
**Result:** N=882. Significant (p<0.05): mean_glucose (higher -> more Insulin-like, p=1.54e-32), bmi (higher -> more Insulin-like, p=1.94e-05), mean_temp (higher -> more Insulin-like, p=2.63e-05), heart_rate (higher -> more Insulin-like, p=0.00412), mean_nox (higher -> more Insulin-like, p=0.00517), steps (higher -> more Healthy-like, p=0.00765), mean_voc (higher -> more Insulin-like, p=0.0228).
**Decision:** keep
**Output:** results/EP_6.csv

### EP.7 — 2026-08-12
**Method:** Binary logistic regression: outcome=1 if Insulin else 0 (restricted to Pre-DM/Insulin), predictors=log_pm25, mean_temp, mean_hum, mean_light, mean_voc, mean_nox, bmi, mean_glucose, steps, stress, heart_rate, sleep_hours, active_calories, age + clinical_site dummies
**Result:** N=703. Significant (p<0.05): mean_glucose (higher -> more Insulin-like, p=1.95e-26), mean_temp (higher -> more Insulin-like, p=0.000508), heart_rate (higher -> more Insulin-like, p=0.00136), age (higher -> more Insulin-like, p=0.00547), mean_voc (higher -> more Insulin-like, p=0.0061), steps (higher -> more Pre-DM-like, p=0.00952).
**Decision:** keep
**Output:** results/EP_7.csv

### EP.4 — 2026-08-12
**Method:** Cross-pair synthesis of EP.1-EP.3 (adjacent boundaries only): predictors significant (p<0.05) in more than one adjacent-severity-boundary logistic model, i.e. a consistent direction of effect as severity increases rather than a one-boundary artifact.
**Result:** 1 predictor(s) significant across >1 adjacent-pair boundary: mean_glucose. Full per-predictor breakdown in EP_combined.csv.
**Decision:** keep
**Output:** results/EP_4.csv

### EG.2 — 2026-08-15
**Method:** OLS, pooled across all 3 clinical sites: activity/BMI ~ log1p(PM2.5) + age + clinical_site dummies. Tests the first link in the project head's mediation hypothesis (pollution -> activity/BMI -> glycemic control), not the full chain.
**Result:** Pooled across all 3 sites (site as covariate). log(PM2.5) significant (p<0.05) for: steps (p=1.09e-06, coef=+ 412.9048), active_calories (p=0.000207, coef=+ 12.2959), bmi (p=1.11e-11, coef=+ 1.0837).
**Decision:** keep
**Output:** results/EG_2.csv

### EG.3 — 2026-08-15
**Method:** OLS, fit separately within each of the 3 clinical sites (UW, UAB, UCSD): activity/BMI ~ log1p(PM2.5) + age. Same first-link mediation test as EG.2, run without pooling to check whether the pooled effect holds at each site individually.
**Result:** Same model refit separately per site (no pooling, no site dummy). log(PM2.5) significant (p<0.05) for: UW/steps (p=0.0002, coef=+ 490.9384), UW/active_calories (p=0.000108, coef=+ 21.4722), UW/bmi (p=4.25e-10, coef=+ 1.6735), UAB/steps (p=0.00171, coef=+ 417.5841), UCSD/bmi (p=1.43e-05, coef=+ 1.3545). Compare against EG.2's pooled estimate -- a pooled-significant effect that disappears or reverses at one site means the pooled estimate is being driven by between-site differences, not a within-site pollution effect.
**Decision:** keep
**Output:** results/EG_3.csv
