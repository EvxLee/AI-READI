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

## History

Depression (CES-D-10) was the paper's sole primary outcome through
2026-08-10, with a scoping-phase Aim 1/Aim 2 already run pre-PRESPEC. On
2026-08-11 the project head pivoted the paper to glycemic control and BMI
as environmental-exposure outcomes, demoting depression to a side track;
on 2026-08-17 depression was dropped from the plan entirely, since none of
that side-track work (E1.2–E1.7, E2.1–E2.6) was ever run — those IDs and
the original depression-era scoping numbers are removed from the Status
table below and are not part of the plan going forward. Full history is in
git log; `PRESPEC.md`'s overhaul header links back to the interim
amendments if needed.

Current experiment families: **EP.1–EP.7** (severity-pair binary models —
3 adjacent + 3 non-adjacent + 1 cross-pair synthesis), **ECGM.1–ECGM.2**
(CGM-derived glycemic metrics build + age-group comparison), **EG.1**
(primary model: glycemic control ~ environment + BMI + wearables + age +
severity), **EG.2–EG.3** (mediation follow-up: does pollution predict
activity/BMI, pooled and per-site), **E1.1** (general-purpose baseline
descriptive, kept for its original ID — not depression-specific).

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
| EG.4 | done | `results/EG_4.csv` | Second mediation link: does activity (steps/active_calories) or BMI predict glycemic control, controlling for age/severity? Necessary condition for the mediation story: if activity/BMI don't predict glycemic control here, pollution's effect on them (EG.2/EG.3) can't be mediating anything. Track: primary. | Across 4 candidate glycemic-control outcomes (glucose_mean, glucose_cv, tar_180, spikes_per_day_180), steps significant (p<0.05) in 0/4; active_calories significant in 2/4 (glucose_mean, tar_180); bmi significant in 1/4 (glucose_cv, negative direction). | keep |
| EG.5 | done | see EG.5a/EG.5b/EG.5c | Rebuild EG.2-EG.4 with a minutes-in-activity-level measure (from raw Garmin physical_activity stream: sedentary/generic/walking/running labels) replacing steps, which failed both mediation links. active_calories and bmi stay as-is. Two grouping variants: v1 = sedentary-vs-rest, v2 = sedentary+generic-vs-walking+running. Track: primary. | Mixed improvement over steps: active_minutes_v1 significant (pooled, link 1) and significant in 2/4 link-2 outcomes, unlike steps which was significant in 0/4 for link 2. v2 not significant pooled but flips sign at UW. Full detail in EG.5a-c. | keep |
| EG.5a | done | `results/EG_5a.csv` | Link 1, pooled across all 3 sites: active_minutes_v1/v2, active_calories, bmi ~ log1p(PM2.5) + age + site dummies. EG.5's rework of EG.2. Track: primary. | N~2085-2225. log(PM2.5) significant for active_minutes_v1_per_day (p=0.0423, positive — more pollution, more active minutes, same backwards direction as steps), active_calories (p=0.0002, positive), bmi (p=1.11e-11, positive, as hypothesized). active_minutes_v2_per_day not significant (p=0.054, negative trend). | keep |
| EG.5b | done | `results/EG_5b.csv` | Link 1, per-site (no pooling): same model as EG.5a, refit within UW/UAB/UCSD separately. EG.5's rework of EG.3. Track: primary. | log(PM2.5) significant at: UW (active_minutes_v2_per_day, p=0.020, NEGATIVE — opposite of the pooled v1 direction; active_calories p=0.0001; bmi p<0.0001), UCSD (bmi only, p=1.4e-05). UAB: none significant. The v1/v2 sign flip between pooled and per-site suggests the pooled active-minutes result is not a stable within-site effect. | keep |
| EG.5c | done | `results/EG_5c.csv` (+ per-fit `EG_5c_<variant>_<outcome>.csv`) | Link 2: 4 candidate glycemic-control outcomes ~ active_minutes_v1/v2 + active_calories + bmi + age + severity dummies + site dummies. EG.5's rework of EG.4. Track: primary. | 8 fits (2 variants x 4 outcomes). active_minutes_v1_per_day significant for glucose_mean (p=0.0257, positive) and spikes_per_day_180 (p=0.0387, positive); not significant for glucose_cv or tar_180. active_minutes_v2_per_day not significant for any of the 4. Better than steps (0/4 in EG.4) but still weak and inconsistent between v1/v2. | keep |
| EG.6 | not started | | Single combined mediation model chaining pollution -> activity/BMI -> glycemic control, instead of two separate regressions, to report an actual indirect effect with its own significance test. Depends on EG.5's result for which activity measure to use. Track: primary. | | |
| EG.7 | done | `results/EG_7.csv` (+ EG.7a/EG.7b per-outcome detail) | Sensitivity: rerun EG.1 (EG.7a) and EG.4 (EG.7b) with severity-group dummies removed, to test whether severity group was absorbing pollution's/BMI's true effect (overcontrol) rather than acting as a neutral confounder. Track: primary. | **Confirmed overcontrol, for pollution specifically.** log(PM2.5) flips from non-significant to significant (p<0.05) once severity is dropped, in 2/4 outcomes (glucose_cv p=0.0061, tar_180 p=0.0168 — both were p>0.1 with severity in). BMI is significant for 2/4 in both versions but the picture shifts: glucose_mean stays significant and gets much stronger (p<0.0001 vs. p=0.037), tar_180 goes from ns to p<0.0001, while glucose_cv (significant with severity, p=0.0007) becomes ns without it. steps stays non-significant in all 4 either way (0/4) — the overcontrol issue is specific to pollution/BMI, not steps. | keep — this explains a real chunk of EG.1's null result |
| EG.8 | done | `results/EG_8.csv` | Per-site replication of EG.7a's no-severity primary model: does the newly-significant pollution effect on glycemic control hold at each site individually, or is it driven by one site? Track: primary. | **Mixed, not a clean replication.** log(PM2.5)-glucose_cv is significant at UCSD only (p=0.0012, positive, same direction as pooled), not at UW or UAB. log(PM2.5)-tar_180 (pooled p=0.0168) is not significant at any single site individually (UAB closest, p=0.056). So the pollution-glycemic-control link from EG.7a is real for at least one site/outcome pair, but it is not a uniform, cohort-wide effect -- it looks concentrated at UCSD, similar to how the mediation-link effect (EG.2/EG.3) was concentrated at UW. | keep — real but site-heterogeneous, worth reporting as such |
| EG.9 | not started | | VIF/multicollinearity diagnostics on EG.1's predictor set (BMI, severity, glucose, PM2.5 expected to be collinear per docs/CAVEATS.md). High VIF would explain EG.1's null pollution term without requiring "no true effect." Track: primary. | | |
| EG.10 | done | `results/EG_10.csv` | Project-head follow-up to EG.8: is EG.7a's glucose_cv/tar_180 significance concentrated in one severity group, or evenly spread? Compares severity-group distribution within those model rows to the full cohort. Track: primary. | Not skewed. Severity-group distribution within both significant-outcome models matches the full cohort within 0.4 percentage points for every group. Rules out "one severity group is driving the effect" as an explanation for EG.7a/EG.8's results. | keep |
| EG.11 | done | `results/EG_11.csv` | Project-head follow-up to EG.8: per-site descriptive stats (mean/median/SD/IQR/max) for PM2.5, NOx, VOC, to test whether UCSD (where EG.8's effect replicated) is simply more or more variably polluted than UW/UAB. Track: primary. | **Does not support the hypothesis.** UAB has the highest PM2.5 mean (19.0) and SD (55.6) of the 3 sites; UCSD is only moderate (mean 12.3, SD 40.8), lower than UAB on both. UW is lowest on both. So UCSD is not the most-polluted or most-variable site, yet it's the one where EG.8's effect replicated — the site concentration isn't explained by pollution exposure level alone. | keep |
| EG.12 | done | `data/processed/p2/glucose_variability_metrics.csv` (gitignored, participant-level; not a `results/` artifact) | Build intraday (within-day) and interday (between-day) glucose variability metrics from raw CGM streams, per project head's request for the standard Rodbard-style variability decomposition. Track: primary. | N=2245 streams pulled, 2243 parsed. 4 participants have <2 valid days so interday_glucose_variance is NaN for them. Design choice (flagged for lead confirmation): a day needs >=12 readings to count. | keep |
| EG.13 | done | `results/EG_13.csv` (+ EG.13a pooled, EG.13b per-site) | Repeat EG.7a/EG.8's no-severity design with NOx (log1p) in place of PM2.5, pooled + per-site. Track: primary. | Pooled: log_nox not significant for any of the 4 outcomes (closest: glucose_cv p=0.051). Per-site: significant at UCSD only, for glucose_mean (p=0.0235), tar_180 (p=0.018), spikes_per_day_180 (p=0.0286) — none of these were pooled-significant. Same UCSD-concentration pattern as PM2.5. | keep |
| EG.14 | done | `results/EG_14.csv` (+ EG.14a pooled, EG.14b per-site) | Repeat EG.7a/EG.8's no-severity design with VOC (log1p) in place of PM2.5, pooled + per-site. Track: primary. | Pooled: log_voc not significant for any of the 4 outcomes. Per-site: UAB/spikes_per_day_180 (p=0.0127), UCSD/glucose_cv (p=0.0214) — weaker and less consistent than PM2.5 or NOx. | keep |
| EG.15 | done | `results/EG_15_summary.csv` | Repeat the no-severity pollution tests (PM2.5, NOx, VOC) against EG.12's new intraday/interday variability outcomes, pooled + per-site. Track: primary. | **Strongest result in the EG series.** PM2.5 -> interday_glucose_variance is significant pooled (p=1.1e-05) AND replicates at 2 of 3 sites individually (UAB p=0.014, UCSD p=0.0067; UW p=0.14, weaker but same positive direction). PM2.5 -> intraday_glucose_variance significant pooled only (p=0.033), no site replicates alone. NOx/VOC mostly null except NOx/UCSD/intraday (p=0.043). | keep — PM2.5-interday effect is the most cross-site-consistent finding so far |
| EG.16 | done | `results/EG_16_summary.csv` | Project-head-requested reverse-direction, exploratory/correlational check: log(PM2.5) ~ glycemic marker + bmi + age + site, for glucose_mean, glucose_cv, intraday/interday variance, and hba1c (for comparison). Track: primary. | All 5 glycemic markers significant (p<0.05): glucose_mean (p=0.025), glucose_cv (p=0.0011), intraday variance (p=0.035), interday variance (p=1.1e-05), hba1c (p=2.0e-06, strongest). Read as correlational only — pollution isn't caused by blood sugar; likely reflects shared geographic/site structure even after controlling for site dummies. | keep — flagged as exploratory, not causal |
| EG.17 | done | `data/processed/p2/cgm_range_features.csv` (gitignored, participant-level; not a `results/` artifact) | Build the project head's exact 5-level glycemic-range feature set (2026-08-19): severe_hypo (<54), moderate_hypo (54-69), normal (70-180), moderate_hyper (181-250), severe_hyper (>250), each with minutes/day, fraction of readings, mean glucose within range, and windows/day. Plus overall glucose_mean, glucose_overall_variance (pooled-reading variance, distinct from EG.12's interday metric), glucose_mean_daily_variance (matches EG.12's intraday_glucose_variance), and glucose_cv_ratio (SD/mean, unscaled). Supersedes the earlier informal 140/180 thresholds — existing tar_180/spikes_per_day_180 already used 180 so no prior results need rework. Track: primary. | N=2245 streams pulled, 2243 parsed (2 failed, <12 valid readings). 27 columns total. Not yet run through the pollution models — that's the next step (EG.18+), pending confirmation of which of the 15 range-features to prioritize testing. | keep |
| EG.18 | done | `results/EG_18_summary.csv` | Full grid: all 24 EG.17 features x 3 pollutants (PM2.5/NOx/VOC) x pooled+per-site, no-severity design. 288 fits total. Track: primary. | 44/288 significant at p<0.05 (~3x the ~14 expected by chance, not multiple-comparison-corrected — flagged as a caveat). Strongest, cross-site-replicated finding: PM2.5 -> moderate_hyper_mean_glucose (average glucose while in the 181-250 band) significant pooled (p=0.0033) AND independently at both UCSD (p=0.045) and UAB (p=0.047) — the first result in the whole EG series to replicate at 2 of 3 sites with the same design. PM2.5 also pooled-significant (not yet site-replicated) for glucose_cv_ratio, glucose_overall_variance, normal_minutes_per_day/fraction (negative — less time in range), moderate_hypo and severe_hypo/hyper time/fraction/windows. NOx/VOC mostly site-specific-only (UCSD), consistent with EG.13/EG.14's pattern. | keep — moderate_hyper_mean_glucose is the strongest candidate headline result so far |

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

### EG.4_glucose_mean — 2026-08-17
**Method:** OLS: glucose_mean ~ steps + active_calories + bmi + age + severity-group dummies + site dummies
**Result:** N=2116, R2=0.280. steps p=0.556, active_calories p=0.0046, bmi p=0.0703.
**Decision:** keep
**Output:** results/EG_4_glucose_mean.csv

### EG.4_glucose_cv — 2026-08-17
**Method:** OLS: glucose_cv ~ steps + active_calories + bmi + age + severity-group dummies + site dummies
**Result:** N=2116, R2=0.228. steps p=0.803, active_calories p=0.143, bmi p=0.0218.
**Decision:** keep
**Output:** results/EG_4_glucose_cv.csv

### EG.4_tar_180 — 2026-08-17
**Method:** OLS: tar_180 ~ steps + active_calories + bmi + age + severity-group dummies + site dummies
**Result:** N=2116, R2=0.309. steps p=0.434, active_calories p=0.00891, bmi p=0.207.
**Decision:** keep
**Output:** results/EG_4_tar_180.csv

### EG.4_spikes_per_day_180 — 2026-08-17
**Method:** OLS: spikes_per_day_180 ~ steps + active_calories + bmi + age + severity-group dummies + site dummies
**Result:** N=2116, R2=0.252. steps p=0.239, active_calories p=0.208, bmi p=0.0956.
**Decision:** keep
**Output:** results/EG_4_spikes_per_day_180.csv

### EG.4 — 2026-08-17
**Method:** Cross-outcome summary of the second mediation link (see EG.4_<outcome> rows for each individual fit): tests steps, active_calories, and BMI against 4 candidate CGM-derived glycemic-control outcomes, controlling for age and severity group.
**Result:** Across 4 candidate glycemic-control outcomes (glucose_mean, glucose_cv, tar_180, spikes_per_day_180), steps significant (p<0.05) in 0/4; active_calories significant in 2/4; bmi significant in 1/4. See EG_4_summary.csv for per-outcome detail.
**Decision:** keep
**Output:** results/EG_4.csv

### EG.5a — 2026-08-17
**Method:** OLS, pooled across all 3 sites: active_minutes_v1_per_day / active_minutes_v2_per_day / active_calories / bmi ~ log1p(PM2.5) + age + clinical_site dummies. EG.5 rework of EG.2, replacing steps with the raw activity-level-minutes measure.
**Result:** Pooled across all 3 sites. log(PM2.5) significant (p<0.05) for: active_minutes_v1_per_day (p=0.0423, coef=+ 6.7102), active_calories (p=0.000207, coef=+ 12.2959), bmi (p=1.11e-11, coef=+ 1.0837).
**Decision:** keep
**Output:** results/EG_5a.csv

### EG.5b — 2026-08-17
**Method:** OLS, refit separately within each of the 3 sites: active_minutes_v1_per_day / active_minutes_v2_per_day / active_calories / bmi ~ log1p(PM2.5) + age. EG.5 rework of EG.3, replacing steps.
**Result:** Per-site (no pooling). log(PM2.5) significant (p<0.05) for: UW/active_minutes_v2_per_day (p=0.0202, coef=- 8.8862), UW/active_calories (p=0.000108, coef=+ 21.4722), UW/bmi (p=4.25e-10, coef=+ 1.6735), UCSD/bmi (p=1.43e-05, coef=+ 1.3545).
**Decision:** keep
**Output:** results/EG_5b.csv

### EG.5c_active_minutes_v1_per_day_glucose_mean — 2026-08-17
**Method:** OLS: glucose_mean ~ active_minutes_v1_per_day + active_calories + bmi + age + severity-group dummies + site dummies. EG.5 rework of EG.4, replacing steps with active_minutes_v1_per_day.
**Result:** N=2090, R2=0.281. active_minutes_v1_per_day p=0.0257, active_calories p=0.138, bmi p=0.0545.
**Decision:** keep
**Output:** results/EG_5c_active_minutes_v1_per_day_glucose_mean.csv

### EG.5c_active_minutes_v1_per_day_glucose_cv — 2026-08-17
**Method:** OLS: glucose_cv ~ active_minutes_v1_per_day + active_calories + bmi + age + severity-group dummies + site dummies. EG.5 rework of EG.4, replacing steps with active_minutes_v1_per_day.
**Result:** N=2090, R2=0.225. active_minutes_v1_per_day p=0.316, active_calories p=0.463, bmi p=0.0149.
**Decision:** keep
**Output:** results/EG_5c_active_minutes_v1_per_day_glucose_cv.csv

### EG.5c_active_minutes_v1_per_day_tar_180 — 2026-08-17
**Method:** OLS: tar_180 ~ active_minutes_v1_per_day + active_calories + bmi + age + severity-group dummies + site dummies. EG.5 rework of EG.4, replacing steps with active_minutes_v1_per_day.
**Result:** N=2090, R2=0.307. active_minutes_v1_per_day p=0.113, active_calories p=0.157, bmi p=0.177.
**Decision:** keep
**Output:** results/EG_5c_active_minutes_v1_per_day_tar_180.csv

### EG.5c_active_minutes_v1_per_day_spikes_per_day_180 — 2026-08-17
**Method:** OLS: spikes_per_day_180 ~ active_minutes_v1_per_day + active_calories + bmi + age + severity-group dummies + site dummies. EG.5 rework of EG.4, replacing steps with active_minutes_v1_per_day.
**Result:** N=2090, R2=0.252. active_minutes_v1_per_day p=0.0387, active_calories p=0.498, bmi p=0.105.
**Decision:** keep
**Output:** results/EG_5c_active_minutes_v1_per_day_spikes_per_day_180.csv

### EG.5c_active_minutes_v2_per_day_glucose_mean — 2026-08-17
**Method:** OLS: glucose_mean ~ active_minutes_v2_per_day + active_calories + bmi + age + severity-group dummies + site dummies. EG.5 rework of EG.4, replacing steps with active_minutes_v2_per_day.
**Result:** N=2090, R2=0.279. active_minutes_v2_per_day p=0.842, active_calories p=0.00132, bmi p=0.0668.
**Decision:** keep
**Output:** results/EG_5c_active_minutes_v2_per_day_glucose_mean.csv

### EG.5c_active_minutes_v2_per_day_glucose_cv — 2026-08-17
**Method:** OLS: glucose_cv ~ active_minutes_v2_per_day + active_calories + bmi + age + severity-group dummies + site dummies. EG.5 rework of EG.4, replacing steps with active_minutes_v2_per_day.
**Result:** N=2090, R2=0.225. active_minutes_v2_per_day p=0.0946, active_calories p=0.283, bmi p=0.00953.
**Decision:** keep
**Output:** results/EG_5c_active_minutes_v2_per_day_glucose_cv.csv

### EG.5c_active_minutes_v2_per_day_tar_180 — 2026-08-17
**Method:** OLS: tar_180 ~ active_minutes_v2_per_day + active_calories + bmi + age + severity-group dummies + site dummies. EG.5 rework of EG.4, replacing steps with active_minutes_v2_per_day.
**Result:** N=2090, R2=0.306. active_minutes_v2_per_day p=0.619, active_calories p=0.00515, bmi p=0.213.
**Decision:** keep
**Output:** results/EG_5c_active_minutes_v2_per_day_tar_180.csv

### EG.5c_active_minutes_v2_per_day_spikes_per_day_180 — 2026-08-17
**Method:** OLS: spikes_per_day_180 ~ active_minutes_v2_per_day + active_calories + bmi + age + severity-group dummies + site dummies. EG.5 rework of EG.4, replacing steps with active_minutes_v2_per_day.
**Result:** N=2090, R2=0.251. active_minutes_v2_per_day p=0.09, active_calories p=0.909, bmi p=0.145.
**Decision:** keep
**Output:** results/EG_5c_active_minutes_v2_per_day_spikes_per_day_180.csv

### EG.5c — 2026-08-17
**Method:** Cross-outcome summary of EG.5's second link (see EG.5c_<variant>_<outcome> rows for each individual fit): tests active_minutes_v1_per_day and active_minutes_v2_per_day (in place of steps) against 4 candidate glycemic-control outcomes, controlling for active_calories, bmi, age, and severity group.
**Result:** Across 2 active-minutes variants x 4 outcomes (8 fits), the active-minutes predictor significant (p<0.05) in 2/8. See EG_5c_summary.csv for per-fit detail; compare against EG.4 where steps was significant in 0/4.
**Decision:** keep
**Output:** results/EG_5c.csv

### EG.7a_glucose_mean — 2026-08-17
**Method:** OLS: glucose_mean ~ log1p(PM2.5) + env vars + BMI + wearables + age + site dummies (NO severity-group dummies -- EG.1 minus severity, to test overcontrol).
**Result:** N=1944, R2=0.063. log_pm25 p=0.159 (was 0.988 with severity), bmi p=1.7e-07.
**Decision:** keep
**Output:** results/EG_7a_glucose_mean.csv

### EG.7a_glucose_cv — 2026-08-17
**Method:** OLS: glucose_cv ~ log1p(PM2.5) + env vars + BMI + wearables + age + site dummies (NO severity-group dummies -- EG.1 minus severity, to test overcontrol).
**Result:** N=1944, R2=0.061. log_pm25 p=0.00614 (was 0.114 with severity), bmi p=0.794.
**Decision:** keep
**Output:** results/EG_7a_glucose_cv.csv

### EG.7a_tar_180 — 2026-08-17
**Method:** OLS: tar_180 ~ log1p(PM2.5) + env vars + BMI + wearables + age + site dummies (NO severity-group dummies -- EG.1 minus severity, to test overcontrol).
**Result:** N=1944, R2=0.066. log_pm25 p=0.0168 (was 0.299 with severity), bmi p=3.95e-06.
**Decision:** keep
**Output:** results/EG_7a_tar_180.csv

### EG.7a_spikes_per_day_180 — 2026-08-17
**Method:** OLS: spikes_per_day_180 ~ log1p(PM2.5) + env vars + BMI + wearables + age + site dummies (NO severity-group dummies -- EG.1 minus severity, to test overcontrol).
**Result:** N=1944, R2=0.052. log_pm25 p=0.788 (was 0.156 with severity), bmi p=0.103.
**Decision:** keep
**Output:** results/EG_7a_spikes_per_day_180.csv

### EG.7b_glucose_mean — 2026-08-17
**Method:** OLS: glucose_mean ~ steps + active_calories + bmi + age + site dummies (NO severity-group dummies -- EG.4 minus severity, to test overcontrol).
**Result:** N=2116, R2=0.037. steps p=0.652 (was 0.556 with severity), active_calories p=0.00242, bmi p=1.25e-11.
**Decision:** keep
**Output:** results/EG_7b_glucose_mean.csv

### EG.7b_glucose_cv — 2026-08-17
**Method:** OLS: glucose_cv ~ steps + active_calories + bmi + age + site dummies (NO severity-group dummies -- EG.4 minus severity, to test overcontrol).
**Result:** N=2116, R2=0.032. steps p=0.841 (was 0.803 with severity), active_calories p=0.458, bmi p=0.0146.
**Decision:** keep
**Output:** results/EG_7b_glucose_cv.csv

### EG.7b_tar_180 — 2026-08-17
**Method:** OLS: tar_180 ~ steps + active_calories + bmi + age + site dummies (NO severity-group dummies -- EG.4 minus severity, to test overcontrol).
**Result:** N=2116, R2=0.039. steps p=0.527 (was 0.434 with severity), active_calories p=0.00428, bmi p=1.4e-10.
**Decision:** keep
**Output:** results/EG_7b_tar_180.csv

### EG.7b_spikes_per_day_180 — 2026-08-17
**Method:** OLS: spikes_per_day_180 ~ steps + active_calories + bmi + age + site dummies (NO severity-group dummies -- EG.4 minus severity, to test overcontrol).
**Result:** N=2116, R2=0.031. steps p=0.464 (was 0.239 with severity), active_calories p=0.147, bmi p=0.000474.
**Decision:** keep
**Output:** results/EG_7b_spikes_per_day_180.csv

### EG.7 — 2026-08-17
**Method:** Overcontrol sensitivity check: EG.1 and EG.4 rerun with severity-group dummies removed from the predictor set, compared side by side against the original with-severity p-values.
**Result:** log(PM2.5) flips from non-significant to significant (p<0.05) once severity is dropped, in 2/4 outcomes. steps flips the same way in 0/4 outcomes. See EG_7a_summary.csv / EG_7b_summary.csv for full before/after detail.
**Decision:** keep
**Output:** results/EG_7.csv

### EG.8 — 2026-08-17
**Method:** OLS, EG.7a's no-severity predictor set refit separately within each of the 3 clinical sites (UW, UAB, UCSD). Checks whether EG.7a's pooled pollution effect on glycemic control replicates at each site or is driven by one site.
**Result:** log(PM2.5) significant (p<0.05) per-site for: UCSD/glucose_cv (p=0.00118, coef=+ 1.0034). Compare against EG.7a's pooled result (significant for glucose_cv p=0.0061, tar_180 p=0.0168) -- a pooled-significant effect that doesn't replicate at any single site means it is likely driven by between-site differences, not a real within-site effect.
**Decision:** keep
**Output:** results/EG_8.csv

### EG.10 — 2026-08-18
**Method:** Descriptive: study_group_label distribution among the complete-case rows used in EG.7a's glucose_cv and tar_180 models, compared to the full cohort's distribution.
**Result:** Severity-group distribution within EG.7a's glucose_cv/tar_180 model rows, compared to the full cohort's distribution. Max absolute deviation from cohort proportions: 0.4 percentage points. See EG_10.csv for the full breakdown.
**Decision:** keep
**Output:** results/EG_10.csv

### EG.11 — 2026-08-18
**Method:** Descriptive: mean/median/SD/IQR/max for mean_pm25, mean_nox, mean_voc, broken out by clinical_site, from environmental_summary.csv.
**Result:** Per-site PM2.5/NOx/VOC descriptive stats (mean, median, SD, IQR, max). PM2.5 SD is highest at UAB (SD=40.83). Full table in EG_11.csv -- checked against EG.8's finding that the pollution-glucose_cv effect only replicated at UCSD.
**Decision:** keep
**Output:** results/EG_11.csv

### EG.13a — 2026-08-18
**Method:** OLS, pooled, no severity-group dummies: glycemic control ~ log_nox + other env vars + BMI + wearables + age + site dummies.
**Result:** log_nox significant (p<0.05) for: none.
**Decision:** keep
**Output:** results/EG_13a.csv

### EG.13b — 2026-08-18
**Method:** OLS, per-site (no pooling), no severity-group dummies: glycemic control ~ log_nox + other env vars + BMI + wearables + age, refit within each site.
**Result:** Pooled: log_nox significant for none. Per-site: significant for UCSD/glucose_mean (p=0.0235), UCSD/tar_180 (p=0.018), UCSD/spikes_per_day_180 (p=0.0286).
**Decision:** keep
**Output:** results/EG_13b.csv

### EG.13 — 2026-08-18
**Method:** Combined pooled + per-site test of log_nox (in place of PM2.5) against the same no-severity primary-model design as EG.7a/EG.8.
**Result:** Pooled: log_nox significant for none. Per-site: significant for UCSD/glucose_mean (p=0.0235), UCSD/tar_180 (p=0.018), UCSD/spikes_per_day_180 (p=0.0286).
**Decision:** keep
**Output:** results/EG_13.csv

### EG.14a — 2026-08-18
**Method:** OLS, pooled, no severity-group dummies: glycemic control ~ log_voc + other env vars + BMI + wearables + age + site dummies.
**Result:** log_voc significant (p<0.05) for: none.
**Decision:** keep
**Output:** results/EG_14a.csv

### EG.14b — 2026-08-18
**Method:** OLS, per-site (no pooling), no severity-group dummies: glycemic control ~ log_voc + other env vars + BMI + wearables + age, refit within each site.
**Result:** Pooled: log_voc significant for none. Per-site: significant for UAB/spikes_per_day_180 (p=0.0127), UCSD/glucose_cv (p=0.0214).
**Decision:** keep
**Output:** results/EG_14b.csv

### EG.14 — 2026-08-18
**Method:** Combined pooled + per-site test of log_voc (in place of PM2.5) against the same no-severity primary-model design as EG.7a/EG.8.
**Result:** Pooled: log_voc significant for none. Per-site: significant for UAB/spikes_per_day_180 (p=0.0127), UCSD/glucose_cv (p=0.0214).
**Decision:** keep
**Output:** results/EG_14.csv

### EG.15 — 2026-08-18
**Method:** OLS, no severity-group dummies: intraday_glucose_variance / interday_glucose_variance ~ log(pollutant) + other env vars + BMI + wearables + age (+ site dummies pooled, or refit per-site). Pollutant = PM2.5, NOx, or VOC.
**Result:** Across 3 pollutants x 2 new variability outcomes x (pooled + 3 sites), significant (p<0.05) for: PM2.5/pooled/intraday_glucose_variance (p=0.0325), PM2.5/pooled/interday_glucose_variance (p=1.12e-05), PM2.5/per_site/UAB/interday_glucose_variance (p=0.014), PM2.5/per_site/UCSD/interday_glucose_variance (p=0.00673), NOx/per_site/UCSD/intraday_glucose_variance (p=0.0426). See EG_15_summary.csv for full detail.
**Decision:** keep
**Output:** results/EG_15.csv

### EG.16 — 2026-08-18
**Method:** OLS, exploratory/correlational (not causal): log1p(PM2.5) ~ glycemic_predictor + bmi + age + site dummies, run separately for each glycemic_predictor in {glucose_mean, glucose_cv, intraday_glucose_variance, interday_glucose_variance, hba1c}. Tests which glycemic marker co-varies most with pollution exposure, per project head's request; pollution is not plausibly caused by blood sugar, so this is read as a correlational comparison, not a mechanism test.
**Result:** Reverse-direction (log(PM2.5) ~ glycemic marker + bmi + age + site), exploratory/correlational only. Significant (p<0.05): glucose_mean (p=0.0247), glucose_cv (p=0.00111), intraday_glucose_variance (p=0.0355), interday_glucose_variance (p=1.08e-05), hba1c (p=1.99e-06). hba1c p=1.99e-06, for comparison against the CGM-derived metrics.
**Decision:** keep
**Output:** results/EG_16.csv

### EG.18 — 2026-08-19
**Method:** OLS, no severity-group dummies: each of EG.17's 24 range/overall glucose features ~ log(pollutant) + other env vars + BMI + wearables + age (+ site dummies pooled, or refit per-site). Pollutant = PM2.5, NOx, or VOC. Full grid, 288 fits max.
**Result:** 288 total fits (24 outcomes x 3 pollutants x pooled+3 sites). 44 significant at p<0.05. Pooled-significant: PM2.5/glucose_cv_ratio (p=0.000394), PM2.5/glucose_overall_variance (p=0.000573), PM2.5/normal_minutes_per_day (p=0.000937), PM2.5/severe_hyper_windows_per_day (p=0.00101), PM2.5/moderate_hypo_fraction (p=0.00137), PM2.5/moderate_hypo_minutes_per_day (p=0.00145), PM2.5/normal_fraction (p=0.00176), PM2.5/moderate_hypo_windows_per_day (p=0.00233), PM2.5/moderate_hyper_mean_glucose (p=0.00328), PM2.5/severe_hypo_minutes_per_day (p=0.00393), PM2.5/severe_hyper_minutes_per_day (p=0.00507), PM2.5/severe_hyper_fraction (p=0.0119), VOC/normal_windows_per_day (p=0.0156), PM2.5/severe_hypo_windows_per_day (p=0.0176), PM2.5/severe_hypo_fraction (p=0.0252), VOC/moderate_hypo_mean_glucose (p=0.0306), PM2.5/glucose_mean_daily_variance (p=0.0325). Outcomes significant at >=2 sites independently (real cross-site replication): PM2.5/moderate_hyper_mean_glucose at ['UCSD', 'UAB'].
**Decision:** keep
**Output:** results/EG_18.csv
