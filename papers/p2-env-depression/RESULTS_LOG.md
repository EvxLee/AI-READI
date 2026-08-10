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
| E1.1 | done | `results/E1_1.csv` | Baseline population picture across environment, BMI, wearables, and CES-D-10 — confirms the merged table looks right before any model runs on it. | N=2280 participants merged (core+wearable+environmental). 12/17 variables differ significantly (p<0.05, Kruskal-Wallis) across the 4 severity groups. | keep |
| E1.2 | not started | | Primary test: does PM2.5, BMI, or wearable behavior independently predict depression score once age, severity, and site are controlled for? | | |
| E1.3 | not started | | Robustness check: do the same predictors hold when depression is treated as the ≥10 clinical screen (yes/no) instead of a continuous score? | | |
| E1.4 | not started | | Which single variables carry a depression signal on their own, before any adjustment? | | |
| E1.5 | not started | | Does the E1.2 story change once the lower-coverage variables (SpO2, CGM glucose) are added back in? | | |
| E1.6 | not started | | Does the result replicate independently at each of the three clinical sites, or is one site driving it? | | |
| E1.7 | not started | | Does the result survive known data-quality issues (broken temperature sensor, PM2.5 outliers) and variable overlap (VIF)? | | |
| E2.1 | not started | | Full profile of the highest-risk subgroup (insulin-dependent, under 70), including depression for the first time. | | |
| E2.2 | not started | | Headline subgroup test: is this subgroup's depression burden actually higher than the rest of the cohort's? | | |
| E2.3 | not started | | Within the subgroup, does depression line up with its already-elevated BMI, PM2.5, or wearable profile? | | |
| E2.4 | not started | | Adjusted version of E2.3: does any variable still predict depression within the subgroup once the others are controlled for? | | |
| E2.5 | not started | | Does the specific high-BMI + low-activity combination the team originally asked about show elevated depression? | | |
| E2.6 | not started | | Is the subgroup's depression gap driven by one specific age band, or true across both? | | |

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
