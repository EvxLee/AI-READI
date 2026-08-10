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
| E0.1 | not started | | Locate + profile urine albumin, monofilament, hs-troponin | |
| E0.2 | not started | | Map self-report items to kidney / nerve / heart | |
| E0.3 | not started | | Profile extension variables (CES-D, PAID-5, BMI, HbA1c, CGM, Garmin, ECG, SDOH) | |
| E0.4 | not started | | Build master participant table; QC vs 776/560/686/258; reproduce kidney spot-check | |
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
