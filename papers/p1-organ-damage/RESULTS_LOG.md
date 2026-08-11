# Paper 1 — Results log

Every experiment run gets one line here, **including nulls**. This log is the
paper's defence against the cherry-picking critique that public-dataset
analyses attract: we can foreground the strongest findings precisely because
the record shows nothing was hidden.

**Rules**

- One row per run: ID, one-line method, one-line result, keep/kill decision.
- A clean null is information. Log it and move on.
- Numbers here are copied from executed outputs, never from memory.
- Phases 0–2 are exploratory. Phase 3 picks the headline set, writes
  `PRESPEC.md` for exactly those, and reruns them per spec.
- Deviations from a dated `PRESPEC.md` get logged here with justification.
- Aggregate outputs go in `results/`, keyed by experiment ID
  (e.g. `results/E2C_1_cesd_vs_markers.png`). Nothing keyed by `person_id`.

## Status

| ID | Status | Key output | One-line result | Keep/Kill |
|----|--------|-----------|-----------------|-----------|
| E0.1 | done | `results/E0_1_marker_profile.csv` | All three present. Kidney = ACR from import_urine_albumin/import_urine_creatinine (n=2225, median 7.0 mg/g). Heart = import_troponin_t (n=2233, 712 below the 6 ng/L detection limit). Nerve = msslffl/mssrffl, 0-10 sites felt per foot (n=2268). Trap confirmed: import_albumin is SERUM albumin, not the kidney marker. | keep |
| E0.2 | done | `results/E0_2_organ_self_report_map.csv` | Kidney = mhoccur_rnl (246 yes) and heart = mhoccur_mi + mhoccur_cvdot (382 yes) map cleanly. NERVE HAS NO COMPARATOR: the 30-item mhoccur battery contains no neuropathy/numbness/foot item, and condition_occurrence.csv re-expresses the same 30 items. Nearest proxies (mhoccur_cns 179, mhoccur_circ 204) are broad neuro / vascular, not neural-foot. | rescope — gate resolved, see E0.GATE |
| E0.3 | done | `results/E0_3_extension_variable_readiness.csv` | All tracks viable. Two need a build first: CGM TAR/CV/MAGE (manifest has mean glucose only) and ECG machine interpretations (in the .hea headers, not the manifest). DEFECT FOUND AND FIXED in omop.phenx_family: the `pxhi` housing prefix also matched the whole `pxhic` insurance battery, and every family pulled in its own survey timestamps as if they were Likert responses. | keep |
| E0.4 | done | `results/E0_4_cohort_qc_by_group.csv` | 2,280 rows, group Ns exactly 776/560/686/258, no duplicate person_id, dataset version 3.0.0. Marker coverage 97.6-99.5%. Kidney spot-check reproduces: 319 with ACR>=30 mg/g, of whom 89 self-report kidney problems and 226 do not (72% unrecognized). The documented '~320' counted one participant with zero urine creatinine (infinite ratio); guarded, the count is 319. | keep |
| E1.1 | not started | | Abnormal-result prevalence per organ, by severity | |
| E1.2 | not started | | Unrecognized fraction per organ — the headline numbers | |
| E1.3 | not started | | Multi-organ counts and overlap | |
| E1.4 | not started | | Recognized vs unrecognized: who falls through | |
| E1.5 | not started | | Threshold sensitivity, first pass | |
| E2C.1 | not started | | CES-D-10 vs each damage marker | |
| E2C.2 | not started | | CES-D vs unrecognized status among those with damage | |
| E2C.3 | not started | | PAID-5 vs each damage marker | |
| E2A.1 | not started | | HbA1c + CGM metrics vs damage | |
| E2A.2 | not started | | Damage among CGM/severity-discordant participants | |
| E2B.1 | not started | | BMI vs each damage marker | |
| E2E.1 | not started | | Machine-read prior infarct vs self-reported MI (unadjudicated) | |
| E2E.2 | not started | | ECG metrics vs troponin and other markers | |
| E2D.1 | not started | | Garmin metrics vs each damage marker (one clean pass) | |
| E2F.1 | not started | | Access barriers + insecurity vs unrecognized status | |
| E3.1 | not started | | Rank all findings on four criteria | |
| E3.2 | not started | | Pick headline set; write and date PRESPEC.md | |
| E3.3 | not started | | Confirmatory reruns + robustness. **Freeze 26 Aug 2026.** | |
| E4.1 | not started | | Table 1: cohort characteristics by severity | |
| E4.2 | not started | | Figure 1: unrecognized fraction by organ × severity | |
| E4.3 | not started | | Figure 2: multi-organ overlap | |
| E4.4 | not started | | Table 2 + supplement: headline models, replication, sweeps | |

## Log

<!-- Append entries below. Newest last. Format:

### E0.1 — 2026-08-11
**Method:** one line.
**Result:** one line, numbers copied from output.
**Decision:** keep / kill / rescope, and why.
**Output:** results/E0_1_*.csv

-->

### E0.1 — 2026-08-11
**Method:** Located and profiled the three damage markers in measurement.csv; checked units, coverage and below-detection handling.
**Result:** All three present. Kidney = ACR from import_urine_albumin/import_urine_creatinine (n=2225, median 7.0 mg/g). Heart = import_troponin_t (n=2233, 712 below the 6 ng/L detection limit). Nerve = msslffl/mssrffl, 0-10 sites felt per foot (n=2268). Trap confirmed: import_albumin is SERUM albumin, not the kidney marker.
**Decision:** keep
**Output:** results/E0_1_marker_profile.csv

### E0.2 — 2026-08-11
**Method:** Searched all 361 observation items and condition_occurrence.csv for history items mapping to kidney, nerve/foot and heart.
**Result:** Kidney = mhoccur_rnl (246 yes) and heart = mhoccur_mi + mhoccur_cvdot (382 yes) map cleanly. NERVE HAS NO COMPARATOR: the 30-item mhoccur battery contains no neuropathy/numbness/foot item, and condition_occurrence.csv re-expresses the same 30 items. Nearest proxies (mhoccur_cns 179, mhoccur_circ 204) are broad neuro / vascular, not neural-foot.
**Decision:** rescope — GATE TRIGGERED, see report for Evan
**Output:** results/E0_2_organ_self_report_map.csv

### E0.3 — 2026-08-11
**Method:** Profiled every Phase-2 extension variable for coverage, cleaning and accessibility before committing to the tracks.
**Result:** All tracks viable. Two need a build first: CGM TAR/CV/MAGE (manifest has mean glucose only) and ECG machine interpretations (in the .hea headers, not the manifest). DEFECT FOUND AND FIXED in omop.phenx_family: the `pxhi` housing prefix also matched the whole `pxhic` insurance battery, and every family pulled in its own survey timestamps as if they were Likert responses.
**Decision:** keep
**Output:** results/E0_3_extension_variable_readiness.csv

### E0.4 — 2026-08-11
**Method:** Built the master participant table via cohort.build_p1_table(); checked Ns, missingness and the documented kidney spot-check.
**Result:** 2,280 rows, group Ns exactly 776/560/686/258, no duplicate person_id, dataset version 3.0.0. Marker coverage 97.6-99.5%. Kidney spot-check reproduces: 319 with ACR>=30 mg/g, of whom 89 self-report kidney problems and 226 do not (72% unrecognized). The documented '~320' counted one participant with zero urine creatinine (infinite ratio); guarded, the count is 319.
**Decision:** keep
**Output:** results/E0_4_cohort_qc_by_group.csv

### E0.GATE — 2026-08-11
**Method:** Phase 0 gate review with Evan: nerve has a complete monofilament exam (n=2,268) but no self-report comparator anywhere in v3.0.0.
**Result:** DECISION (Evan, 2026-08-11): nerve is retained for measured prevalence, multi-organ damage counts and the Aim 2 depression analysis, and is EXCLUDED from the unrecognized fraction. The Aim 1 unrecognized headline covers kidney and heart only. The broad mhoccur_cns / mhoccur_circ proxies are not used at all, not even as a labelled sensitivity check. The missing neuropathy item is stated in Limitations.
**Decision:** rescope — agreed; Phase 1 proceeds on two organs for E1.2, three organs for E1.1 and E1.3
**Output:** none
