# Data caveats

Read this before touching AI-READI data. Every item below was learned the
hard way during the exploratory phase — several of them silently corrupted
analyses before anyone noticed.

## Labs and vitals

- **`lbscat_a1c` is CBC haemoglobin in g/dL, NOT HbA1c.** True HbA1c is
  **`import_hba1c`**. The names look interchangeable and are not.
- **BMI is `bmi_vsorres`** in the measurement table — a directly recorded
  value, not something to compute from height and weight.
- **`import_albumin` is SERUM albumin in g/dL, not the kidney marker.** The
  kidney marker is the urine albumin-to-creatinine ratio built from
  `import_urine_albumin` and `import_urine_creatinine`. The two urine fields
  carry the same unit, so `albumin / creatinine * 1000` gives ACR in mg/g
  (median 7.0, which is the expected healthy value).
- **254 participants have a urine albumin of exactly 0, and `log(ACR)` throws
  them away.** They are not flagged below-detection — every albumin row carries
  operator `4172703` ("=") — and the smallest positive value in the release is
  0.01 mg/dL, so a zero is a measurement rounded below the reporting floor, not
  a missing one. They are also not a random 11%: 14.5% of the Healthy group
  against 8.5% of Insulin, so dropping them strips the least-damaged
  participants preferentially off the healthy end and flattens every continuous
  kidney gradient. `associations.add_outcome_columns` substitutes half the
  reporting floor (0.005 mg/dL, giving ACR ≈ 0.076 mg/g at median creatinine —
  which lands on the smallest ACR actually observed, 0.0749, the check that the
  floor was read right) and keeps the drop-the-zeros version as
  `log_acr_positive` for the sensitivity line. Binary `abn_kidney` is untouched:
  0 and 0.076 are both below 30. Found at the start of Phase 2, 17 Aug 2026; no
  Phase-1 result is affected, because the only Phase-1 analysis using log ACR
  (`E1.4`) runs on abnormal participants only, where no zeros exist.
- **One participant has a urine creatinine of 0.** That is a void too dilute
  to interpret, not an infinite ratio — but left as `inf` it passes every
  `>= threshold` comparison and silently counts as kidney damage. This is the
  single participant separating the "~320 abnormal" figure quoted in `PLAN.md`
  from the correct 319. `cohort.build_p1_table` guards it.
- **Monofilament is two fields, `msslffl` and `mssrffl`** — sites felt out of
  10 per foot, where 10 is full protective sensation. Not a pass/fail flag.
- **The two derived monofilament columns are on different scales, and only one
  of them carries the cutoff.** `monofilament_min` is the WORSE FOOT (sites
  felt, 0–10) and is what `abn_nerve` thresholds: missed = `10 -
  monofilament_min`, abnormal at ≥ 2 missed. `monofilament_insensate_sites`
  sums BOTH feet (0–20) and is descriptive only. They differ by roughly a
  factor of two over the same participants, so a plot or a summary built on
  the wrong one puts the abnormality line in the wrong place while still
  looking entirely plausible. This caught a Phase-1 figure on 17 Aug 2026 —
  the giveaway was an x-axis running to 20 under a "of 10" label.
- **Troponin below-detection rows carry `operator_concept_id = 4171756`.**
  Their value is a detection limit, not a measurement. Handle them
  explicitly or every heart-injury count is wrong.
  `omop.extract_lab(..., flag_below_detection=True)` does this. All 712 such
  rows carry exactly 6.0; the other 1,521 carry operator 4172703 ("="). A
  naive `troponin >= 6` therefore calls 2,232 of 2,233 people abnormal. Any
  summary statistic must say which denominator it used: the median is 7.96
  over all measured results and 10.24 over the detectable ones.
- **One troponin row reads 1.77 ng/L with an "=" operator** — below the
  stated 6 ng/L limit of detection, so it is either a lower true LOD than
  documented or a lab error. n = 1, so it changes nothing, but do not treat
  6.0 as a hard floor when writing range checks.
- **Monofilament asymmetry is not always physiology.** 14 participants score
  0 on both feet, and 6 score 0 on one foot and 10 on the other. A completely
  insensate foot beside a perfect one is clinically unusual; if a nerve result
  ever turns on these rows, inspect them before interpreting.

## Surveys

- **Special codes 555 / 777 / 99 mean not-asked / refused / sentinel.**
  Set them to NaN; never average them in. Every EDA-era notebook scrubbed
  only `99`, which is how a 1–6 Likert item ended up reporting a maximum of
  777. Use `omop.clean_survey_values`.
  One caveat on the caveat: `99` is a legitimate value for some count items,
  so pass a narrower code tuple when cleaning counts.
- **CES-D-10:** range 0–30, screen-positive at ≥ 10, total field is `cestl`.
  Items `ces5` and `ces8` are positive-affect items but are stored **already
  reverse-scored** — the plain sum of the ten items reproduces `cestl`
  exactly. Applying `3 - x` double-reverses and corrupts the score.
- **PAID-5:** raw range 0–20, cutoff ≥ 8.
- **DML items are 3-level ordinal {0, 5, 10}** — not continuous, not 0/1/2.
- **`mhoccur_plm` is broad chronic pulmonary disease, not asthma.**
- **`mhoccur_fallot` is a fall count, not a binary flag**, and `mhoccur_yn`
  is a gate question. Both must be excluded from any comorbidity tally.

## PhenX SDOH — a known defect, do not repeat it

Three of four SDOH variables in the deleted notebooks were built by
positionally slicing **one** instrument's item list:

```python
d_cols = pxrd_keys[:14]     # labelled "discrimination"
h_cols = pxrd_keys[14:28]   # labelled "healthcare access"
f_cols = pxrd_keys[28:]     # labelled "food/housing insecurity"
```

All three slices come from `pxrd*`, the PhenX **racial discrimination**
battery — so two of the three labels were simply wrong. Worse, `sorted()` is
a string sort, so the order runs `pxrd1, pxrd10, pxrd11, pxrd12, pxrd2, …`
and the slices are not even contiguous. Every SDOH result from that era —
including the "~60% food/housing insecure" figure and the whole "insecurity
paradox" storyline — is an artifact.

That paradox was never published by anyone; it existed only in this repo.
Do **not** frame future work as correcting a known field-level finding.

**The correct item families**, all present with 90–98% coverage and used in
zero notebooks so far:

| Family | Prefix | Items |
|---|---|---|
| Food insecurity | `pxfi` | 1–5 |
| Housing insecurity | `pxhi` | 1–2 |
| Healthcare access | `pxahc` | 1–10 |
| Clinician discrimination | `pxdhc` | 1–7 |
| Prescription affordability | `pxpa` | 1–4 |
| Insurance type | `pxhic` | 1–5, 7–8 (7 items — **`pxhic6` is absent from v3.0.0**) |
| Neighborhood | `pxne` | 1–17 (this one *was* scored correctly) |
| Racial discrimination | `pxrd` | the mis-sliced battery |

Always select by prefix — `omop.phenx_family("food_insecurity")`. Never by
position. `docs/reference/phenx_item_catalog.csv` lists every item with its
wording, coverage, and value range.

**Selecting the right items is only half the job — scoring them is the other
half, and three separate traps live there** (found in E2F.1, 17 Aug 2026;
`omop.phenx_scores` handles all three):

- **Two batteries are NOT monotonic in their coded values.** `pxhi1` ("What is
  your living situation today?") is 0 = no steady place (n=15), 1 = steady place
  (n=1,943), 2 = have a place but worried about losing it (n=95) — so security
  runs 1 > 2 > 0, and a model treating the code as a severity scale points the
  effect somewhere meaningless. `pxfi1`/`pxfi2` are the same shape: their 1 level
  is *rarer* than their 2 level (63 vs 246), which is the tell that the answer
  order is never / often / sometimes rather than a graded scale. Recode to an
  affirmative indicator; never sum the raw code.
- **Skip-gated items cannot go in a summed score.** `pxahc3` (n=256), `pxahc4`
  (n=1,788) and `pxahc6` (n=30) are asked only of some participants, so a sum
  including them measures how many questions someone was asked.
- **Some items are nominal.** `pxahc5` ("what kind of place do you go to", 1–6)
  and `pxhi2` (housing-problem list, 8 = none, n=1,707) are categories, not
  quantities.

Use the validated instrument scoring where one exists — food insecurity is the
USDA 5-item short form, scored as an affirmative count with the cutoff at ≥ 2,
which sidesteps the `pxfi1`/`pxfi2` coding problem by construction.

**A bare prefix match is not enough either** (found and fixed in E0.1–E0.4,
Aug 2026). `pxhi` is a prefix of `pxhic`, so a `startswith` selection put all
seven insurance items inside the two-item housing-insecurity score — the same
wrong-instrument outcome as the positional bug, reached a different way. Every
family also picked up its own survey metadata (`pxrdcmpdat`, `pxnestartts`,
`pxfistartts`), scoring dates and timestamps as if they were Likert responses.
`phenx_family` now matches `<prefix><digit>`, which yields exactly the item
counts in the table above. If you select items by hand anywhere, do the same.

## Self-report history

- **There is no neuropathy item in v3.0.0.** The `mhoccur` battery has 30
  items covering kidney, heart, stroke, circulation and "other neurological
  conditions", but nothing for nerve damage, numbness, or foot sensation.
  `condition_occurrence.csv` is the same 30 items re-expressed as OMOP
  conditions and adds nothing. So the monofilament exam has no self-report
  comparator and **nerve cannot carry an "unrecognized" fraction**. Decided at
  the Phase 0 gate (`E0.GATE`, 2026-08-11): nerve keeps measured prevalence,
  multi-organ counts and the depression aim; the unrecognized fraction covers
  kidney and heart only. **`mhoccur_cns` and `mhoccur_circ` are not stand-ins**
  — one is a leftovers bin sitting beside separate MS/Parkinson's/dementia
  items, the other is vascular. Neither is used, in any analysis.
- **Responses are 0/1 with 777 = refused**, and `mhoccur_yn` does not gate the
  individual items: 551 answered yes to the gate, but 246 reported kidney
  problems and 382 reported a heart condition, so the items were answered
  cohort-wide. Do not filter on the gate.
- **A refusal is not a "no".** Keep it NaN — the whole point of an unawareness
  estimate is that "never told" and "would not say" are different.

## ECG

- **`machine_text` in the ECG manifest is the device name** ("PageWriter TC"),
  identical for all 2,257 rows — it is not the machine interpretation. The
  interpretation statements live in the per-participant WFDB `.hea` headers as
  `interpretation_comment_*` and `comment_*_key`, and carry an explicit
  "Unconfirmed Diagnosis" line. Reading them means harvesting ~2,257 small
  header files.
- **The manifest has 2,257 rows for 2,251 participants** — six have a repeat
  ECG. Deduplicate before merging or those people get double-counted.

## Wearables

- **Garmin error codes:** `0` for heart rate and SpO2, `-2` for stress and
  respiratory rate. These mean "no reading". Treat as missing before
  averaging or every summary drifts toward zero.
- **Scrubbing the error code is NOT enough — the manifest averages are already
  contaminated.** AI-READI computed `average_*` upstream *with* the sentinels
  included, so a contaminated mean lands between the sentinel and the truth
  instead of on it, and sails through any `!= 0` test. In v3.0.0: 12
  participants have a resting heart rate below 30 bpm (lowest **0.03**), 113
  have a **negative** stress score on a 0–100 scale (lowest −1.19 — only
  reachable if most contributing readings were the −2 sentinel), 131 have a
  sleep average outside 1–14 h (including one implying a fraction of a day above
  1.4), and 147 have a step average of exactly 0 after sixteen days of wear. Apply
  `GARMIN_PLAUSIBLE_RANGES` after the scrub;
  `wearables.clean_garmin_manifest` does this by default and
  `apply_plausibility=False` reproduces the old behaviour for sensitivity
  checks. **This changes conclusions:** in E2D.1 three of 40 adjusted results
  flip — steps vs any-organ damage stops surviving FDR (q 0.047 → 0.111) while
  heart rate and stress vs log ACR start surviving (q 0.066 → 0.015 and
  0.051 → 0.015). Found 17 Aug 2026. No Phase-1 result is affected: Phase 1 uses
  no wearable variable, and all five verifiers pass after the rebuild. **Paper 2
  leans on these columns heavily and must rebuild its tables.**
- **`average_sleep_hours` is a fraction of a day** — multiply by 24.
- **Dexcom CGM writes `"Low"` and `"High"` as STRINGS, not numbers.** The G6 only
  reports between 40 and 400 mg/dL; outside that range `blood_glucose.value`
  holds one of those two tokens. In v3.0.0 that is **39,632 readings across 495
  participants** (22% of the cohort): 34,449 `"High"` and 5,183 `"Low"`. A
  `float(value)` raises and — if the exception is swallowed — silently deletes
  them, which strips readings from exactly the participants with the worst
  control: one participant has 2,258 of 2,568 readings as `"High"`, and two
  participants lose their entire stream and drop out of the analysis. Mean, CV,
  MAGE and time-above-range are all biased as a result, hardest where glycaemia
  matters most for organ damage. These are **censored** values, like the troponin
  below-detection rows, and `parse_dexcom_json` now maps them to the
  reportable-range boundary (`CGM_SENTINEL_VALUES`) and reports per-participant
  counts on `.attrs["censored"]`. That is conservative for time-above-range and
  understates variability, which is the honest direction — a censored excursion's
  true amplitude is unrecoverable. 51 participants are over 5% censored and 23
  over 25%; exclude or flag those in any variability analysis. Also note the
  manifest's own `average_glucose_level_mg_dl` handles these differently and
  disagrees with a boundary-substituted mean for 59 participants, so the two are
  not interchangeable. Found 17 Aug 2026 (E2A.1 build).
- **Respiratory rate reads 6–9 against an expected 12–20.** Device quirk:
  relative comparison only, never as an absolute value.
- `wearables.clean_garmin_manifest` applies all three.

## Environment

- **One sensor logged 1,145 °C.** Exclude it.
- **PM2.5 has a very long tail** (median ~3, max ~1,178 µg/m³): log-transform
  or use medians. A raw mean is meaningless.
- Sensor placement varies (bedroom 767, living room 706, office 74, dining
  60) and was not randomised. Check placement against severity group and
  report it.

## Cohort and statistics

- **Severity confounds nearly everything.** Age + severity group + site
  adjustment is the default for any association claim. A raw correlation that
  dies under adjustment is not a finding — this was the single biggest lesson
  of the exploratory phase.
- **Small subgroups are fragile.** Insulin is n ≈ 258. Use bootstrap CIs and
  say so.
- **Expected group Ns:** Healthy 776, Pre-DM 560, Oral Med 686, Insulin 258
  (total 2,280). `cohort.qc_report` checks these; a mismatch usually means
  the wrong container or a new release.
- **The public release removes sex, race/ethnicity, and medications.** No
  antidepressant adjustment is possible, and troponin cutoffs cannot be
  sex-specific — mitigate with threshold sensitivity sweeps.
