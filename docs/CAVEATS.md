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
- **One participant has a urine creatinine of 0.** That is a void too dilute
  to interpret, not an infinite ratio — but left as `inf` it passes every
  `>= threshold` comparison and silently counts as kidney damage. This is the
  single participant separating the "~320 abnormal" figure quoted in `PLAN.md`
  from the correct 319. `cohort.build_p1_table` guards it.
- **Monofilament is two fields, `msslffl` and `mssrffl`** — sites felt out of
  10 per foot, where 10 is full protective sensation. Not a pass/fail flag.
- **Troponin below-detection rows carry `operator_concept_id = 4171756`.**
  Their value is a detection limit, not a measurement. Handle them
  explicitly or every heart-injury count is wrong.
  `omop.extract_lab(..., flag_below_detection=True)` does this.

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
| Insurance type | `pxhic` | 1–8 |
| Neighborhood | `pxne` | 1–17 (this one *was* scored correctly) |
| Racial discrimination | `pxrd` | the mis-sliced battery |

Always select by prefix — `omop.phenx_family("food_insecurity")`. Never by
position. `docs/reference/phenx_item_catalog.csv` lists every item with its
wording, coverage, and value range.

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
- **`average_sleep_hours` is a fraction of a day** — multiply by 24.
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
