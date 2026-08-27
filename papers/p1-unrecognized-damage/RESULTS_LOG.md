# Paper 1 — Results log

Every experiment run gets one line here, **including nulls**. This log is the
paper's defence against the cherry-picking critique that public-dataset
analyses attract: we can foreground the strongest findings precisely because
the record shows nothing was hidden.

**How this file works**

- One row per run: ID, one-line method, one-line result, keep/kill decision.
- A clean null is information. Log it and move on.
- Numbers here are copied from executed outputs, never from memory.
- Phases 0–2 are exploratory. Phase 3 picks the headline set, writes
  `PRESPEC.md` for exactly those, and reruns them per spec. Deviations from a
  dated `PRESPEC.md` get logged here with justification.
- Entries are appended by `results.save()` alongside the artifact they describe,
  so a result and its log line cannot drift apart.

*Repo-wide analysis and compliance rules — adjustment defaults, what may be
committed — live once, in `CLAUDE.md`.*

## Definitions fixed at E1.0

Exploratory until Phase 3 freezes them in `PRESPEC.md`; swept in E1.5. This is
the Methods paragraph in miniature — the numbers are in
`results/E1_0_threshold_spec.csv`, the reasoning is here.

| Organ | Marker | Abnormal | Why this cutoff |
|---|---|---|---|
| Kidney | urine ACR | **≥ 30 mg/g** | KDIGO category A2, the standard screening threshold. Needs no sex variable. |
| Heart | hs-cTnT | **≥ 14 ng/L** | Sex-neutral 99th-percentile upper reference limit for this assay. Sex-specific limits (~10 F / ~15–16 M) are impossible here — the public release removes sex. |
| Nerve | monofilament, worse foot | **≥ 2 insensate sites of 10** | Guideline "loss of protective sensation" was written for 3–4 site exams; on a 10-site exam a single equivocal miss would qualify. The guideline-literal ≥ 1 is the first rung of the E1.5 sweep and is reported as a sensitivity line (`E1.DECIDE`). |

**Unrecognized fraction** = (abnormal **and** self-report says no) ÷ (abnormal
**and** the self-report item was answered). Refusals are excluded from the
denominator, never recoded as "no" — the whole point of an unawareness estimate
is that "never told" and "would not say" are different. The alternative
denominator (all abnormal, refusals included) is reported beside it in every
table.

**Nerve carries no unrecognized fraction.** v3.0.0 has no neuropathy self-report
item and the broad `mhoccur_cns` / `mhoccur_circ` proxies were rejected outright
(`E0.GATE`). Nerve keeps prevalence, the multi-organ count, and the Phase-2
depression aim, and is out of the title (`E1.DECIDE`).

## Statements the Methods section must make

Three disclosures are decided and easy to lose between here and the manuscript,
so they live in the committed record rather than only in a report.

1. **`PRESPEC.md` is dated after the exploratory runs, and the paper says so
   plainly.** Phases 0–2 are exploratory; the spec is written at `E3.2` for the
   headline set only, then those analyses are rerun against it. The defence is
   the completeness of this log — "nothing was hidden", not "nothing was
   explored" — together with the fact that the abnormality cutoffs and the
   unrecognized denominator were fixed and written down at `E1.0` before any
   counting. A spec dated after the runs invites exactly the question it is
   meant to answer, so the disclosure is made in Methods rather than left for a
   reviewer to find.
2. **No neuropathy self-report item exists in v3.0.0**, so the monofilament exam
   carries no unrecognized fraction (`E0.GATE`). One Methods sentence, one
   Limitations sentence.
3. **The ECG interpretations are machine-generated and physician-unreviewed**
   (`E2E.1`). Labelled unadjudicated everywhere they appear, figures included.
4. **The self-report survey is not same-day with the clinic tests.** The three
   objective tests are concurrent with one another (urine albumin and troponin
   share a date for 99.9% of participants), but the `mhoccur` medical-history
   battery — and CES-D-10 and PAID-5 with it — was administered a median of 35
   days earlier (IQR 20-54; same-day for only 3.4%). One Methods sentence
   (`E2.TIMING`). Bias direction: a diagnosis received between survey and visit
   reads as "never told", so the estimate is if anything an overstatement of
   unawareness — the same direction as the existing self-report limitation.

## Verification protocol

Every experiment is run twice by two independent code paths, and is not finished
until the second one agrees:

1. **Run** — `scripts/run_e1_N.py` writes an aggregate table to `results/` and
   appends to this log via `results.save()`, so the artifact and its log entry
   land together.
2. **Verify** — `scripts/verify/verify_e1_N.py` recomputes every headline number
   straight from the raw cached CSVs **without importing `aireadi` at all**, and
   diffs itself against the committed artifact. A bug in the shared data layer
   cannot make its own output look correct.
3. **Write up** — one section of the phase report in `reports/` (local only).
   `scripts/verify/verify_report.py` then traces every number quoted in that
   report back to an artifact.

## Status

| ID | Status | Key output | One-line result | Keep/Kill |
|----|--------|-----------|-----------------|-----------|
| E0.1 | done | `results/E0_1_marker_profile.csv` | All three present. Kidney = ACR from import_urine_albumin/import_urine_creatinine (n=2225, median 7.0 mg/g). Heart = import_troponin_t (n=2233, 712 below the 6 ng/L detection limit). Nerve = msslffl/mssrffl, 0-10 sites felt per foot (n=2268). Trap confirmed: import_albumin is SERUM albumin, not the kidney marker. | keep |
| E0.2 | done | `results/E0_2_organ_self_report_map.csv` | Kidney = mhoccur_rnl (246 yes) and heart = mhoccur_mi + mhoccur_cvdot (382 yes) map cleanly. NERVE HAS NO COMPARATOR: the 30-item mhoccur battery contains no neuropathy/numbness/foot item, and condition_occurrence.csv re-expresses the same 30 items. Nearest proxies (mhoccur_cns 179, mhoccur_circ 204) are broad neuro / vascular, not neural-foot. | rescope — gate resolved, see E0.GATE |
| E0.3 | done | `results/E0_3_extension_variable_readiness.csv` | All tracks viable. Two need a build first: CGM TAR/CV/MAGE (manifest has mean glucose only) and ECG machine interpretations (in the .hea headers, not the manifest). DEFECT FOUND AND FIXED in omop.phenx_family: the `pxhi` housing prefix also matched the whole `pxhic` insurance battery, and every family pulled in its own survey timestamps as if they were Likert responses. | keep |
| E0.4 | done | `results/E0_4_cohort_qc_by_group.csv` | 2,280 rows, group Ns exactly 776/560/686/258, no duplicate person_id, dataset version 3.0.0. Marker coverage 97.6-99.5%. Kidney spot-check reproduces: 319 with ACR>=30 mg/g, of whom 89 self-report kidney problems and 226 do not (72% unrecognized). The documented '~320' counted one participant with zero urine creatinine (infinite ratio); guarded, the count is 319. | keep |
| E1.0 | done | `results/E1_0_threshold_spec.csv` | kidney ACR >= 30 mg/g -> 319 abnormal of 2,225 measured; heart hs-cTnT >= 14 ng/L -> 447 abnormal of 2,233 measured; nerve >= 2 insensate sites of 10 -> 331 abnormal of 2,268 measured. Unrecognized denominator = abnormal with an answered self-report item: kidney 315 of 319 abnormal (4 refused the item); heart 447 of 447 abnormal (0 refused the item). | keep |
| E1.1 | done | `results/E1_1_prevalence_by_group.csv` | Overall prevalence kidney 319/2,225 (14.3%); heart 447/2,233 (20.0%); nerve 331/2,268 (14.6%); any 767/2,216 (34.6%). Trend across severity: kidney z=8.81 p=1.3e-18; heart z=11.313 p=1.1e-29; nerve z=5.119 p=3.1e-07; any z=11.162 p=6.3e-29. | keep |
| E1.2 | done | `results/E1_2_unrecognized_by_group.csv` | Unrecognized: kidney 226/315 = 71.7% (95% CI 66.5-76.4); heart 298/447 = 66.7% (95% CI 62.2-70.9); either 471/615 = 76.6% (95% CI 73.1-79.8). Trend across severity: kidney z=-3.921 p=8.8e-05; heart z=-2.285 p=2.2e-02; either z=-2.851 p=4.4e-03. | keep |
| E1.3 | done | `results/E1_3_organ_counts.csv` | Among 2,216 measured on all three: 65.4% none, 23.2% one, 9.2% two, 2.2% all three. >=2 organs rises 5.9% -> 31.1% across severity (trend z=10.134, p=3.9e-24). | keep |
| E1.4 | done | `results/E1_4_models.csv` | Terms with p<0.05 across all models: kidney [A: age + severity + site] C(study_group_label)[T.Pre-DM] OR=0.32; kidney [A: age + severity + site] C(study_group_label)[T.Oral Med] OR=0.323; kidney [A: age + severity + site] C(study_group_label)[T.Insulin] OR=0.135; kidney [A: age + severity + site] C(clinical_site)[T.UCSD] OR=0.486; kidney [B: A + HbA1c + BMI] C(study_group_label)[T.Pre-DM] OR=0.246; kidney [B: A + HbA1c + BMI] C(study_group_label)[T.Oral Med] OR=0.185; kidney [B: A + HbA1c + BMI] C(study_group_label)[T.Insulin] OR=0.059; kidney [B: A + HbA1c + BMI] hba1c OR=1.32; kidney [C: B + marker magnitude] C(study_group_label)[T.Pre-DM] OR=0.195; kidney [C: B + marker magnitude] C(study_group_label)[T.Oral Med] OR=0.202; kidney [C: B + marker magnitude] C(study_group_label)[T.Insulin] OR=0.078; kidney [C: B + marker magnitude] hba1c OR=1.35; kidney [C: B + marker magnitude] log_acr OR=0.442; heart [A: age + severity + site] C(study_group_label)[T.Oral Med] OR=0.517; heart [A: age + severity + site] C(study_group_label)[T.Insulin] OR=0.467; heart [A: age + severity + site] age OR=0.961; heart [B: A + HbA1c + BMI] age OR=0.96; heart [C: B + marker magnitude] age OR=0.959; heart [C: B + marker magnitude] log_troponin OR=0.622 | keep |
| E1.5 | done | `results/E1_5_threshold_sweep.csv` | Prevalence spans kidney 2.8-21.0%; heart 9.0-68.1%; nerve 5.8-19.6%. Unrecognized fraction spans kidney 32.8-76.7%; heart 59.2-79.0%. Conclusions holding at every cutoff: 6/7. | keep |
| E2C.1 | done | `results/E2C_1_sweep.csv` | AIM 2 HAS 4 SURVIVING ASSOCIATION(S). Of 16 adjusted models, 4 reach p < 0.05 and 4 survive FDR correction. Surviving: CES-D-10 total (0-30) -> Nerve abnormal (>= 2 insensate sites): 1.2175 (1.0768-1.3766), q=0.0269; CES-D-10 total (0-30) -> Insensate sites, worse foot (0-10): 0.1133 (0.0332-0.1934), q=0.0439; CES-D-10 screen-positive (>= 10) -> Nerve abnormal (>= 2 insensate sites): 1.4795 (1.0947-1.9996), q=0.0439; CES-D-10 screen-positive (>= 10) -> Insensate sites, worse foot (0-10): 0.2568 (0.059-0.4546), q=0.0439. CES-D-10 n=2277, 455 screen-positive. | keep |
| E2C.2 | done | `results/E2C_2.csv` | H3 IS NULL. Of 6 fully-adjusted models, 1 reach p < 0.05 and 0 survive FDR. Surviving: none. Eligible denominators: kidney 315 abnormal with the item answered, 226 never told; heart 447 abnormal with the item answered, 298 never told; either 615 abnormal with the item answered, 471 never told. Note the asymmetry with E2C.1: depression tracks NERVE damage, the one organ for which unrecognized status cannot be computed at all. | keep |
| E2C.3 | done | `results/E2C_3_sweep.csv` | Of 16 adjusted models, 1 reach p < 0.05 and 0 survive FDR. Surviving: none. PAID-5 was administered cohort-wide, not only to the diabetic groups — coverage Healthy 97.0%, Pre-DM 98.4%, Oral Med 97.8%, Insulin 98.4% — so it spans the severity spectrum and needs no scope caveat. | keep |
| E2A.1 | done | `results/E2A_1_sweep.csv` | Of 40 adjusted models, 33 reach p < 0.05 and 33 survive FDR. Surviving: HbA1c (%) -> log urine ACR (mg/g): 0.3369 (0.2444-0.4295), q=5.09e-11; CGM time above 180 mg/dL (%) -> Kidney abnormal (ACR >= 30 mg/g): 1.4926 (1.3263-1.6797), q=4.5e-10; CGM mean glucose (mg/dL) -> Kidney abnormal (ACR >= 30 mg/g): 1.4815 (1.319-1.6641), q=4.5e-10; HbA1c (%) -> Kidney abnormal (ACR >= 30 mg/g): 1.4902 (1.3217-1.6802), q=7.18e-10; CGM time above 180 mg/dL (%) -> log urine ACR (mg/g): 0.2959 (0.2018-0.39), q=6.73e-09; CGM time above 180 mg/dL (%) -> Any of the three organs abnormal: 1.4172 (1.2651-1.5875), q=1.15e-08; CGM mean glucose (mg/dL) -> log urine ACR (mg/g): 0.2782 (0.1868-0.3697), q=1.59e-08; CGM mean glucose (mg/dL) -> Any of the three organs abnormal: 1.4077 (1.2545-1.5796), q=3.02e-08; and 25 more. Coverage: HbA1c (%) n=2211, CGM mean glucose (mg/dL) n=2245, CGM time above 180 mg/dL (%) n=2245, CGM coefficient of variation (%) n=2245, CGM MAGE (mg/dL) n=2244. Built CGM mean reproduces the manifest mean (median \|diff\| 0.002 mg/dL, n=2245). | keep |
| E2A.2 | done | `results/E2A_2_models.csv` | 3 of 15 models survive FDR. Surviving: undiagnosed_range/abn_kidney OR=4.1071 (Wald 2.0606-8.186, bootstrap 1.8291-8.5079), q=0.000893; undiagnosed_range/abn_any OR=2.575 (Wald 1.3478-4.9199, bootstrap 1.3033-5.207), q=0.021; undiagnosed_range_cgm/abn_kidney OR=2.9178 (Wald 1.4401-5.9115, bootstrap 1.247-5.7992), q=0.021. Discordance sizes: No diabetes label, HbA1c >= 6.5% 46/1336 (3.4%); No diabetes label, CGM mean >= 154 mg/dL 55/1336 (4.1%); Insulin group, HbA1c < 7.0% 122/258 (47.3%). DOUBLE-UNRECOGNIZED COUNT: of the 46 participants with no diabetes label but diabetes-range HbA1c, 19 have kidney or heart damage with both self-report items answered and 16 of those reported no corresponding diagnosis. | keep |
| E2B.1 | done | `results/E2B_1_sweep.csv` | Of 16 adjusted models, 11 reach p < 0.05 and 10 survive FDR. Surviving: BMI (kg/m2) -> Any of the three organs abnormal: 1.263 (1.1388-1.4007), q=0.000158; BMI (kg/m2) -> Insensate sites, worse foot (0-10): 0.1623 (0.0804-0.2442), q=0.000841; BMI (kg/m2) -> Nerve abnormal (>= 2 insensate sites): 1.2742 (1.1224-1.4466), q=0.000964; Obese (BMI >= 30) -> Any of the three organs abnormal: 1.4037 (1.1438-1.7228), q=0.00469; Obese (BMI >= 30) -> Heart abnormal (hs-cTnT >= 14 ng/L): 1.4721 (1.1521-1.8808), q=0.00635; BMI (kg/m2) -> Heart abnormal (hs-cTnT >= 14 ng/L): 1.206 (1.0657-1.3647), q=0.00755; BMI (kg/m2) -> log hs-cTnT (ng/L): 0.0322 (0.0107-0.0537), q=0.00755; Obese (BMI >= 30) -> log hs-cTnT (ng/L): 0.0608 (0.018-0.1037), q=0.0108; and 2 more. 0 of 10 raw associations are lost once age + severity + site enter, which is the expected direction: BMI is entangled with severity by design. | keep |
| E2E.1 | done | `results/E2E_1_unrecognized.csv` | UNADJUDICATED. All 2,251 of 2,251 ECG records carry an explicit unconfirmed-diagnosis stamp. 179 participants have an unhedged machine-read prior-infarct pattern; of the 178 who also answered the heart-attack item, 149 (83.7%, 95% CI 77.6-88.4) reported no heart attack. Including hedged statements raises the pattern count to 280. Tier counts: none 1945; definite prior infarct 179; probable prior infarct 54; consider prior infarct 47; acute or recent only 26. This is a waveform-pattern statement, not a diagnosis, and must be labelled unadjudicated everywhere it appears including figures. | keep |
| E2E.2 | done | `results/E2E_2_sweep.csv` | Of 40 adjusted models, 27 reach p < 0.05 and 23 survive FDR. Surviving: QRS duration (ms) -> log hs-cTnT (ng/L): 0.1078 (0.0876-0.128), q=1.98e-23; QRS duration (ms) -> Any of the three organs abnormal: 1.4621 (1.3199-1.6196), q=6.75e-12; QRS duration (ms) -> Heart abnormal (hs-cTnT >= 14 ng/L): 1.4358 (1.2934-1.5939), q=1.52e-10; ECG heart rate (bpm) -> log urine ACR (mg/g): 0.2264 (0.1438-0.309), q=8.56e-07; QRS duration (ms) -> Insensate sites, worse foot (0-10): 0.1779 (0.0985-0.2573), q=9.22e-05; QRS duration (ms) -> Nerve abnormal (>= 2 insensate sites): 1.2519 (1.1272-1.3904), q=0.000137; QTc interval (ms) -> log hs-cTnT (ng/L): 0.0438 (0.0234-0.0642), q=0.000137; ECG heart rate (bpm) -> log hs-cTnT (ng/L): 0.0464 (0.025-0.0678), q=0.000137; and 15 more. Coverage 2251 participants with QTc. | keep |
| E2D.1 | done | `results/E2D_1_sweep.csv` | Of 40 adjusted models, 8 reach p < 0.05 and 5 survive FDR. Surviving: Daily steps -> Heart abnormal (hs-cTnT >= 14 ng/L): 0.786 (0.6799-0.9087), q=0.0151; Resting heart rate (bpm) -> log urine ACR (mg/g): 0.1577 (0.0674-0.248), q=0.0151; Garmin stress score -> log urine ACR (mg/g): 0.1471 (0.0606-0.2337), q=0.0151; Daily steps -> Insensate sites, worse foot (0-10): -0.1353 (-0.2222--0.0485), q=0.0227; Daily steps -> Two or more organs abnormal: 0.7513 (0.6214-0.9083), q=0.0251. Coverage varies widely, so effects are not comparable across exposures without it: Daily steps n=1994, Resting heart rate (bpm) n=1987, Garmin stress score n=1987, Sleep (hours/night) n=2053, SpO2 (%) n=1628. Cross-sectional: steps and heart rate are as plausibly consequences of damage as causes, so any survivor is a correlate only. | keep |
| E2F.1 | done | `results/E2F_1_models.csv` | 1 of 18 fully-adjusted models survive FDR (3 reach p < 0.05 uncorrected). Surviving: Healthcare access barriers (0-3) -> Unrecognized — heart: 0.6599 (0.53-0.8215), q=0.00361. Coverage: Healthcare access barriers (0-3) n=2055, Prescription unaffordability (0-4) n=2022, Food insecurity, USDA count (0-5) n=2242, Food insecure (USDA >= 2) n=2242, Housing insecure (no steady place or at risk) n=2053, Clinician discrimination, mean (1-5) n=2048. NOT a correction of any published finding: the EDA-era 'insecurity paradox' was an artifact of the positional-slicing bug and existed only in this repo (CAVEATS). | keep |
| E3.1 | done | `results/E3_1_ranking.csv` | 207 Phase-2 associations scored; 79 survive FDR; 78 of those replicate in direction at all three sites; 32 meet all four criteria. Top: E2A.2 undiagnosed_range->abn_kidney 4.1071 (q=0.00089, sites 3/3 same direction); E2A.2 undiagnosed_range_cgm->abn_kidney 2.9178 (q=0.021, sites 3/3 same direction); E2A.2 undiagnosed_range->abn_any 2.575 (q=0.021, sites 3/3 same direction); E2F.1 healthcare_access_barriers->unrec_heart 0.6599 (q=0.0036, sites 3/3 same direction); E2A.1 tar_180->abn_kidney 1.4926 (q=4.5e-10, sites 3/3 same direction); E2A.1 hba1c->abn_kidney 1.4902 (q=7.2e-10, sites 3/3 same direction); E2A.1 glucose_mean->abn_kidney 1.4815 (q=4.5e-10, sites 3/3 same direction); E2A.1 mage->abn_kidney 1.4372 (q=1.6e-07, sites 3/3 same direction); E2E.2 qrsd_ms->abn_heart 1.4358 (q=1.5e-10, sites 3/3 same direction); E2E.2 qrsd_ms->log_troponin 0.1078 (q=2e-23, sites 3/3 same direction); E2A.1 tar_180->abn_any 1.4172 (q=1.2e-08, sites 3/3 same direction); E2A.1 glucose_mean->abn_multi 1.4135 (q=6.5e-07, sites 3/3 same direction). | keep — feeds E3.2 |
| E3.2 | done | — | HEADLINE SET: A1 the core sweep (prevalence, unrecognized fraction, population burden as the abstract lead, multi-organ counts, E1.4 who-is-unrecognized models) with per-site replication, cutoff sweeps extended to the burden, and bootstrap intervals; A2 CES-D-10 vs the five binary damage outcomes with the plan's covariate set age + BMI + HbA1c + severity + site (BMI is new relative to Phase 2), BH within 10, claim rule q<0.05 in both exposure forms, five robustness checks, H3 rerun; T1 undiagnosed-range glycaemia vs kidney damage (rank 1 of 207 in E3.1, 32 rows meet all four criteria) with Wald + bootstrap intervals and the CGM replication; T2 ECG numeric metrics vs the heart marker, supplement only; T3 the access-barrier negative reported as exploratory. Set aside for the headline: glycaemia (E2A.1; textbook, one sentence on CV beyond mean), BMI, wearables, PAID-5. Framing per E2.DECIDE: burden primary, falling fraction as mechanism. Required Methods statements 1-6 carried into PRESPEC.md §7. | keep — PRESPEC.md frozen 2026-08-25 (sha256 above); not committed to git tonight by Evan's instruction, so the hash is the freeze marker until his morning commit |
| E3.3 | done | `results/E3_3_headline_summary.csv` | AIM 1 REPRODUCES PHASE 1 EXACTLY (every k, n and %, both denominators, across 55 rows; 46 E1.4 model terms reproduce). Per-site: 11/11 core trends keep their sign at every site (a direction check, not a replication; 7 are significant within all three). Burden rises with severity at every cutoff rung: True (heart at the non-clinical 'detectable' rung p=0.040). AIM 2 with the spec covariates: CES-D-10 -> nerve OR 1.1606 (1.0193-1.3214) per SD, p=0.0245, q=0.245; screen-positive OR 1.3078 (0.9517-1.7973), p=0.098, q=0.49; PRE-SPECIFIED CRITERION NOT MET for any outcome. Attenuation from the Phase-2 OR 1.2175 decomposes on the fixed n=2,197 sample as: same covariates 1.1935 (sample change = 42% of the log-OR drop; the 68 lost participants are 23.5% nerve-abnormal vs 14.3%), + HbA1c 1.1842, + BMI 1.1673, both 1.1606. Missing-data sensitivity (single imputation, n=2,265): OR 1.188 q=0.0638, >=10 OR 1.3933 q=0.163 — criterion still not met. Robustness rows for nerve not significant: 12 (the >=1-insensate-site cutoff erases it: OR 1.0451; dropping the 20 odd monofilament rows p=0.054). Within-site direction 3/3, Q p=0.42. H3: 0 of 6 survive FDR. T1: undiagnosed-range -> kidney OR 4.1071 (Wald 2.0606-8.186, bootstrap 1.8291-8.5079), q=0.000596 (Phase-2 q=0.000893); CGM definition OR 2.9178, q=0.014; within-site direction 3/3, Q p=0.76; double-unrecognized 16 of 19; kidney damage by HbA1c band < 6.5% 109/1259 (8.7%), 6.5-6.9% 6/27 (22.2%), >= 7.0% 7/19 (36.8%). T2: QRS -> log troponin q=5e-24, same direction at 3 sites, Q p=0.35. | keep — headline set rerun per the amended spec; Aim 1 and T1 confirmed, Aim 2 reported as pre-specified criterion not met |
| E4.1 | done | `results/E4_1_table1.csv` | 28 rows. Age 60.9 (11.2); any organ abnormal 767 (34.6%); either-organ unrecognized burden 471 (21.3%) overall, 100 (40.7%) on insulin. | keep |
| E4.2 | done | `results/E4_2_figure1.png` | Either-organ burden 15.5% -> 40.7% across severity (z=8.15); either-organ fraction 84.9% -> 69.9% (z=-2.85). | keep — re-rendered after visual checks (labels off the interval caps; panel B endpoint labels with per-organ offsets; headroom for the Insulin label) |
| E4.3 | done | `results/E4_3_figure2.png` | Two or more organs: 5.9% Healthy -> 31.1% Insulin; most common single organ: heart (204); all three in 49. | keep — re-rendered once after a visual check (group n moved into the tick labels, off the title) |
| E4.4 | done | `results/E4_4_table2.csv` | 54 rows. Aim 2 nerve OR 1.1606 (1.0193-1.3214), q=0.245 — criterion not met; T1 kidney OR 4.1071 (bootstrap 1.8291-8.5079), q=0.000596. | keep |

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

### E0.AUDIT — 2026-08-11
**Method:** Independent re-verification of all of Phase 0 before starting Phase 1: every E0.1-E0.4 number recomputed from the raw cached CSVs by a second implementation that does not import `aireadi`, plus a fresh `build_p1_table()` diffed against the stored master table.
**Result:** Phase 0 stands. Cohort identity, marker coverage, the E0.2 mapping (including an exhaustive re-search that confirms no neuropathy item exists — the nearest hit, `dmlfeet`, is "How often do you inspect your feet?", a self-care behaviour, not a diagnosis), the E0.3 readiness counts and the E0.4 kidney spot-check all reproduce exactly; the rebuilt master table is numerically identical to the stored one. FOUR RECORD DEFECTS FIXED: (1) E0_1's troponin median 10.24 / p95 33.2 are over the 1,521 detectable results while the same row reports n=2,233 — denominators now labelled; (2) this E0.4 entry's "72%" is 226/315, not 226/319 (=70.8%) — the 4 abnormal participants who refused the kidney item; the denominator is now defined explicitly at E1.0; (3) the Phase-0 report's provisional severity gradient (8.3/10.2/18.2/30.8%) does not reproduce — the correct values are 8.6/10.4/18.1/30.6% and are superseded by E1.1; (4) `docs/CAVEATS.md` listed `pxhic` as 8 items — v3.0.0 has 7 (`pxhic6` is absent). Two undocumented data quirks added to CAVEATS: one troponin row reads 1.77 ng/L below the stated 6 ng/L limit with an "=" operator, and 6 participants score 0 on one foot and 10 on the other.
**Decision:** keep — Phase 0 gate remains passed; no analysis conclusion changes.
**Output:** none (corrections applied in place to results/E0_1_marker_profile.csv and docs/CAVEATS.md)

### E0.GATE — 2026-08-11
**Method:** Phase 0 gate review with Evan: nerve has a complete monofilament exam (n=2,268) but no self-report comparator anywhere in v3.0.0.
**Result:** DECISION (Evan, 2026-08-11): nerve is retained for measured prevalence, multi-organ damage counts and the Aim 2 depression analysis, and is EXCLUDED from the unrecognized fraction. The Aim 1 unrecognized headline covers kidney and heart only. The broad mhoccur_cns / mhoccur_circ proxies are not used at all, not even as a labelled sensitivity check. The missing neuropathy item is stated in Limitations.
**Decision:** rescope — agreed; Phase 1 proceeds on two organs for E1.2, three organs for E1.1 and E1.3
**Output:** none

### E1.0 — 2026-08-11
**Method:** Fixed the Phase-1 abnormality cutoffs and the unrecognized-fraction denominator before running any core-sweep experiment; cutoffs are exploratory and swept in E1.5.
**Result:** kidney ACR >= 30 mg/g -> 319 abnormal of 2,225 measured; heart hs-cTnT >= 14 ng/L -> 447 abnormal of 2,233 measured; nerve >= 2 insensate sites of 10 -> 331 abnormal of 2,268 measured. Unrecognized denominator = abnormal with an answered self-report item: kidney 315 of 319 abnormal (4 refused the item); heart 447 of 447 abnormal (0 refused the item).
**Decision:** keep
**Output:** results/E1_0_threshold_spec.csv

### E1.1 — 2026-08-11
**Method:** Prevalence of an abnormal result per organ and for any organ, overall and by severity group, with Wilson 95% CIs and a Cochran-Armitage trend test across the four ordered groups.
**Result:** Overall prevalence kidney 319/2,225 (14.3%); heart 447/2,233 (20.0%); nerve 331/2,268 (14.6%); any 767/2,216 (34.6%). Trend across severity: kidney z=8.81 p=1.3e-18; heart z=11.313 p=1.1e-29; nerve z=5.119 p=3.1e-07; any z=11.162 p=6.3e-29.
**Decision:** keep
**Output:** results/E1_1_prevalence_by_group.csv

### E1.2 — 2026-08-11
**Method:** Unrecognized fraction (abnormal result AND no corresponding self-reported diagnosis) for kidney and heart, overall and by severity group, Wilson 95% CIs and Cochran-Armitage trend. Denominator = abnormal with the item answered; the refusals-included denominator is reported alongside.
**Result:** Unrecognized: kidney 226/315 = 71.7% (95% CI 66.5-76.4); heart 298/447 = 66.7% (95% CI 62.2-70.9); either 471/615 = 76.6% (95% CI 73.1-79.8). Trend across severity: kidney z=-3.921 p=8.8e-05; heart z=-2.285 p=2.2e-02; either z=-2.851 p=4.4e-03.
**Decision:** keep
**Output:** results/E1_2_unrecognized_by_group.csv

### E1.2 — 2026-08-11
**Method:** 2x2 of measured result against self-report, per organ. (Survey precedes the clinic visit by a median 35 days — `E2.TIMING`.)
**Result:** Concordance table: kidney abnormal-not-reported 226, abnormal-reported 89, normal-reported 149, normal-not-reported 1,751; heart abnormal-not-reported 298, abnormal-reported 149, normal-reported 226, normal-not-reported 1,560
**Decision:** keep
**Output:** results/E1_2_concordance.csv

### E1.2 — 2026-08-11
**Method:** Population burden: share of ALL evaluable participants who are both abnormal and unrecognized, by severity group. The conditional fraction and the population burden answer different questions and move in opposite directions across severity, so both are reported.
**Result:** Burden rises with severity even though the conditional fraction falls: kidney 10.2% overall (trend z=5.234, p=1.7e-07); heart 13.3% overall (trend z=7.361, p=1.8e-13); either 21.3% overall (trend z=8.153, p=3.6e-16)
**Decision:** keep
**Output:** results/E1_2_population_burden.csv

### E1.3 — 2026-08-11
**Method:** Per-participant count of organs with an abnormal result, overall and by severity, restricted to participants measured on all three.
**Result:** Among 2,216 measured on all three: 65.4% none, 23.2% one, 9.2% two, 2.2% all three. >=2 organs rises 5.9% -> 31.1% across severity (trend z=10.134, p=3.9e-24).
**Decision:** keep
**Output:** results/E1_3_organ_counts.csv

### E1.3 — 2026-08-11
**Method:** Counts for every observed combination of abnormal organs.
**Result:** Most common single organ: heart (204); all three organs abnormal in 49.
**Decision:** keep
**Output:** results/E1_3_overlap.csv

### E1.3 — 2026-08-11
**Method:** Per-participant count of organs abnormal AND unrecognized (kidney+heart).
**Result:** Of 2,214 evaluable on both organs, 19.2% carry one unrecognized organ and 2.1% carry two.
**Decision:** keep
**Output:** results/E1_3_unrecognized_counts.csv

### E1.3 — 2026-08-11
**Method:** UpSet-style figure of abnormal-organ intersections.
**Result:** Figure written; see E1_3_overlap.csv for the counts.
**Decision:** keep
**Output:** results/E1_3_overlap_figure.png

### E1.4 — 2026-08-11
**Method:** Descriptive comparison of unrecognized vs recognized participants among those with an abnormal result, with standardised mean differences.
**Result:** Variables with |SMD| >= 0.2: kidney/Other conditions reported (this organ's own items removed) -0.488; kidney/kidney marker (median) -0.681; kidney/study_group_label = Healthy, % 0.47; kidney/study_group_label = Insulin, % -0.41; heart/Age, years -0.362; heart/Other conditions reported (this organ's own items removed) -0.729
**Decision:** keep
**Output:** results/E1_4_profile.csv

### E1.4 — 2026-08-11
**Method:** Logistic regression of unrecognized status among the abnormal: (A) age + severity + site, (B) + HbA1c + BMI, (C) + log marker magnitude.
**Result:** Terms with p<0.05 across all models: kidney [A: age + severity + site] C(study_group_label)[T.Pre-DM] OR=0.32; kidney [A: age + severity + site] C(study_group_label)[T.Oral Med] OR=0.323; kidney [A: age + severity + site] C(study_group_label)[T.Insulin] OR=0.135; kidney [A: age + severity + site] C(clinical_site)[T.UCSD] OR=0.486; kidney [B: A + HbA1c + BMI] C(study_group_label)[T.Pre-DM] OR=0.246; kidney [B: A + HbA1c + BMI] C(study_group_label)[T.Oral Med] OR=0.185; kidney [B: A + HbA1c + BMI] C(study_group_label)[T.Insulin] OR=0.059; kidney [B: A + HbA1c + BMI] hba1c OR=1.32; kidney [C: B + marker magnitude] C(study_group_label)[T.Pre-DM] OR=0.195; kidney [C: B + marker magnitude] C(study_group_label)[T.Oral Med] OR=0.202; kidney [C: B + marker magnitude] C(study_group_label)[T.Insulin] OR=0.078; kidney [C: B + marker magnitude] hba1c OR=1.35; kidney [C: B + marker magnitude] log_acr OR=0.442; heart [A: age + severity + site] C(study_group_label)[T.Oral Med] OR=0.517; heart [A: age + severity + site] C(study_group_label)[T.Insulin] OR=0.467; heart [A: age + severity + site] age OR=0.961; heart [B: A + HbA1c + BMI] age OR=0.96; heart [C: B + marker magnitude] age OR=0.959; heart [C: B + marker magnitude] log_troponin OR=0.622
**Decision:** keep
**Output:** results/E1_4_models.csv

### E1.DECIDE — 2026-08-12
**Method:** Phase-1 close-out decisions with Evan on the two items the core sweep left open: the nerve abnormality cutoff and the working title.
**Result:** DECISIONS (Evan, 2026-08-12): (1) Nerve abnormal = >=2 insensate sites of 10 on the worse foot, confirmed as primary; the guideline-literal >=1 (19.6% vs 14.6% prevalence) is carried as a reported sensitivity line. The cutoff moves nerve prevalence 19.6/14.6/10.7% and any-organ 37.9/34.6/32.2% at >=1/2/3 misses, and does not touch the unrecognized headline at all. (2) Nerve is RETAINED in the paper (prevalence, multi-organ counts, Aim 2) but REMOVED from the title, which becomes 'Unrecognized kidney and heart damage across the type 2 diabetes spectrum: a cross-sectional analysis of the AI-READI dataset'. The old title promised an unrecognized figure for feet that v3.0.0 cannot support. Rejected the alternative of dropping nerve entirely: 99.5% coverage, one third of the any-organ figure, and concurrent three-organ measurement is the paper's stated novelty claim. Methods gets one sentence on the missing neuropathy item; Limitations gets one more.
**Decision:** keep — nerve scope and title settled; supersedes the E0.GATE follow-up
**Output:** none

### E1.5 — 2026-08-12
**Method:** Re-ran prevalence and the unrecognized fraction at every rung of each organ's cutoff grid (kidney ACR 20-300 mg/g; heart detectable-22 ng/L; nerve 1-5 insensate sites), including both trend tests.
**Result:** Prevalence spans kidney 2.8-21.0%; heart 9.0-68.1%; nerve 5.8-19.6%. Unrecognized fraction spans kidney 32.8-76.7%; heart 59.2-79.0%. Conclusions holding at every cutoff: 6/7.
**Decision:** keep
**Output:** results/E1_5_threshold_sweep.csv

### E1.5 — 2026-08-12
**Method:** Checked whether each Phase-1 conclusion survives every cutoff in the sweep.
**Result:** kidney prevalence rises with severity — holds; heart prevalence rises with severity — holds; nerve prevalence rises with severity — holds; kidney majority of abnormal results are unrecognized — FLIPS; kidney unrecognized FRACTION falls with severity — holds; heart majority of abnormal results are unrecognized — holds; heart unrecognized FRACTION falls with severity — holds
**Decision:** keep
**Output:** results/E1_5_conclusion_stability.csv

### E1.4 — 2026-08-17 (re-reading, no rerun)
**Method:** Coverage audit of the Phase-1 report against every artifact — the reverse of `verify_report.py`, which had only checked that numbers *in* the report trace back to an output, never that the outputs reached the report. No analysis was rerun; `E1_4_models.csv` is unchanged.
**Result:** The report generalised a kidney result to both organs. Corrected reading: for KIDNEY the severity effect survives and strengthens under full adjustment (Insulin vs Healthy OR 0.135 -> 0.059 -> 0.078, p < 4e-5 in all three models) and marker magnitude dominates (log_acr OR 0.442, p 3.1e-10). For HEART the severity effect is significant in model A only and attenuates to non-significance once HbA1c/BMI and marker magnitude enter (OR 0.467 p 0.015 -> 0.548 p 0.090 -> 0.588 p 0.137); troponin magnitude is marginal (OR 0.622, p 0.043; medians 19.6 vs 23.1, SMD -0.115) and AGE is the only term holding in all three models (OR 0.96/yr, p 1.7e-4). Also recorded: the falling-fraction trend is directionally consistent at every cutoff but statistically significant at only 3/5 kidney and 3/6 heart rungs, per `E1_5_conclusion_stability.csv`.
**Decision:** keep — no numbers change. Interpretation is now organ-specific: the falling-fraction finding is established for kidney and suggestive for heart, and the paper must say so rather than write both as equally supported. Phase-2 tracks touching unrecognized status must adjust for AGE as well as marker magnitude (heart), not magnitude alone.
**Output:** none (report corrected; `verify_report.py` extended from ~135 to 215 checks, now covering the model-attenuation contrast, the full E1_3 overlap enumeration, per-group denominators, mean organs damaged, and the full heart threshold grid)

### E1.CLOSE — 2026-08-17
**Method:** Marker entry only. Confirmed Phase 1 has nothing outstanding, after the two framing questions it left open were settled at `E2.DECIDE` and Phase 2 ran to completion (`E2.CLOSE`).
**Result:** Phase 1 carries no open items. The two questions it handed forward were decided at `E2.DECIDE` — primary framing is the population BURDEN with the falling conditional fraction as the mechanism, and the UCSD kidney site difference is dropped from the paper while staying in `E1_4_models.csv`. See that entry for the reasoning; it is not restated here. The three abnormality cutoffs stand as fixed at `E1.0` and confirmed at `E1.DECIDE` (ACR >= 30, hs-cTnT >= 14, >= 2 insensate of 10), each swept at E1.5 where 6 of 7 conclusions hold at every rung. Phase 1 was additionally re-verified after the three data defects found in Phase 2 (`E2.DEFECTS`) and is unaffected: it uses no wearable, CGM or SDOH variable, and its only log-ACR analysis (E1.4) runs on abnormal participants where no reporting-floor zeros exist.
**Decision:** keep — PHASE 1 CLOSED. One item travels to the manuscript rather than to a phase: Methods must state the staged pre-specification plainly, recorded as a required statement at `E2.DECIDE` item 3.
**Output:** none (decisions only)

### E1.FIG — 2026-08-17
**Method:** Built the Phase-0 and Phase-1 notebooks (`notebooks/00_phase0_foundation.ipynb`, `01_phase1_core_sweep.ipynb`) as the readable walkthrough of work that previously existed only as `scripts/run_e*.py`, and added seven figures. Chart styling moved into `src/aireadi/figures.py`; severity uses a single-hue ordinal ramp (it is ordered), organ uses categorical hues (it is identity), both validated for colour-vision separation against the chart surface. Notebooks recompute the headline aggregates through the package rather than reading the CSVs, so the numbers are re-derived, not copied.
**Result:** Figures added to results/: E0_1_marker_distributions, E0_4_cohort_and_coverage, E1_1_prevalence_figure, E1_2_unrecognized_figure, E1_3_organ_counts_figure, E1_4_forest_figure, E1_5_sweep_figure. All notebook-recomputed values reproduce the committed artifacts exactly. TWO DEFECTS FOUND BY DRAWING THE DATA: (1) a figure plotted `monofilament_insensate_sites` (BOTH feet, 0-20) under a "of 10" axis while the abnormality cutoff is defined on `monofilament_min` (WORSE foot, 0-10) — the giveaway was an axis running to 20; the analysis was correct, the figure was not, and the trap is now in CAVEATS.md. (2) The notebook's hand-written "either organ" rule gave 625/478 against the runner's verified 615/471 — the runner requires BOTH organs evaluable, the notebook accepted EITHER. The definition now lives in `thresholds.either_organ()` with both call sites using it, plus a regression test; the refactor was confirmed behaviour-preserving against the artifact (615/471/76.6/z=-2.851) and verify_e1_2 still passes.
**Decision:** keep — no analysis number changes. Notebook outputs are cleared before commit and the notebooks avoid printing participant rows by construction (schema/completeness instead of `df.head()`).
**Output:** results/E1_1_prevalence_figure.png and six others; src/aireadi/figures.py; thresholds.either_organ()

### E1.5 — 2026-08-12
**Method:** Downstream impact of the nerve cutoff — the one abnormality threshold chosen on judgement rather than a guideline — on nerve prevalence, the any-organ figure and the multi-organ figure, with the kidney unrecognized fraction carried alongside to demonstrate it is unaffected.
**Result:** Nerve prevalence moves 19.6% / 14.6% / 10.7% / 7.7% / 5.8% across >=1 to >=5 missed sites; any-organ moves 37.9% / 34.6% / 32.2% / 30.6% / 29.7%; 2+ organs moves 12.8% / 11.4% / 10.5% / 9.4% / 8.6%. The kidney unrecognized fraction is 71.7% at every rung — the nerve cutoff cannot touch the headline, because nerve has no comparator.
**Decision:** keep
**Output:** results/E1_5_nerve_cutoff_impact.csv

### E2.DECIDE — 2026-08-17
**Method:** Phase-2 opening decisions with Evan on the two framing items Phase 1 left open, plus the standing Methods disclosure.
**Result:** DECISIONS (Evan, 2026-08-17, delegated to Claude's judgement except where noted): (1) PRIMARY FRAMING = population BURDEN, with the falling conditional fraction presented as the mechanism that explains it. Both are computed and both are reported; the abstract leads with burden because it is the public-health quantity and the screening argument ("21.3% of all evaluable participants carry unrecognized kidney or heart damage, rising to 40.7% on insulin"), and the falling fraction (76.6% overall, trend z=-2.851) follows immediately as the explanation — recognition improves with severity but prevalence outruns it. Leading with the fraction alone invites the reading that the problem shrinks with severity, which is the opposite of the burden result. (2) The UCSD kidney-recognition site difference is DROPPED (Evan, explicit): one comparison among several, does not survive full adjustment. It is not reported as a finding, not given a sentence, and not shown in a figure. It stays in `E1_4_models.csv` where any reader can find it, and the per-site replication required at `E3.3` is unaffected — that is a robustness check, not a site claim. (3) The staged-pre-specification disclosure is now recorded as a required Methods statement in this file rather than living only in a report.
**Decision:** keep — framing settled; Phase 2 proceeds
**Output:** none

### E2C.1 — 2026-08-17
**Method:** CES-D-10, continuous and at the >= 10 screen-positive cutoff, against each damage outcome (kidney/heart/nerve/any/multi-organ abnormal, and log marker magnitude): unadjusted, adjusted for age + severity + site, and + HbA1c. Odds ratios per 1 SD of score; Benjamini-Hochberg within the adjusted family.
**Result:** AIM 2 HAS 4 SURVIVING ASSOCIATION(S). Of 16 adjusted models, 4 reach p < 0.05 and 4 survive FDR correction. Surviving: CES-D-10 total (0-30) -> Nerve abnormal (>= 2 insensate sites): 1.2175 (1.0768-1.3766), q=0.0269; CES-D-10 total (0-30) -> Insensate sites, worse foot (0-10): 0.1133 (0.0332-0.1934), q=0.0439; CES-D-10 screen-positive (>= 10) -> Nerve abnormal (>= 2 insensate sites): 1.4795 (1.0947-1.9996), q=0.0439; CES-D-10 screen-positive (>= 10) -> Insensate sites, worse foot (0-10): 0.2568 (0.059-0.4546), q=0.0439. CES-D-10 n=2277, 455 screen-positive.
**Decision:** keep
**Output:** results/E2C_1_sweep.csv

### E2C.1 — 2026-08-17
**Method:** CES-D-10 (per SD) vs any-organ damage (pre-declared) and vs nerve damage (post-hoc, following the sweep), fitted within each severity group, age + site adjusted, with bootstrap intervals where the smaller outcome cell falls under 50.
**Result:** Within-group estimates: abn_any/Healthy OR=0.9695 (0.7984-1.1773), n=761; abn_any/Pre-DM OR=1.1407 (0.9324-1.3954), n=548; abn_any/Oral Med OR=0.9979 (0.8415-1.1834), n=662; abn_any/Insulin OR=0.9017 (0.6754-1.2038), n=242; abn_nerve/Healthy OR=1.2322 (0.9698-1.5656), n=771; abn_nerve/Pre-DM OR=1.1958 (0.9089-1.5731), n=557; abn_nerve/Oral Med OR=1.1946 (0.9671-1.4755), n=685; abn_nerve/Insulin OR=1.3057 (0.9565-1.7823), n=252
**Decision:** keep
**Output:** results/E2C_1_by_severity.csv

### E2C.1 — 2026-08-17
**Method:** Nerve-association robustness: each adjustment covariate added on its own to explain why the association appears only after adjustment, plus the CAVEATS-mandated re-fit excluding the clinically odd monofilament rows (both feet 0; one foot 0 with the other 10).
**Result:** AGE IS THE SUPPRESSOR: OR per SD 1.078 unadjusted (p=0.19) -> 1.262 with age alone (p=0.000146) -> 1.218 fully adjusted. CES-D falls with age (r=-0.219) while insensate sites rise with it (r=0.206), so the two cancel until age is held constant; severity alone (1.037) and site alone (1.068) do nothing. The result does NOT turn on the odd monofilament rows: dropping all 20 of them leaves OR 1.194, p=0.00599.
**Decision:** keep
**Output:** results/E2C_1_nerve_robustness.csv

### E2C.2 — 2026-08-17
**Method:** CES-D-10 (continuous and >= 10) vs unrecognized status among participants with an abnormal result, per organ and for either organ. Four nested adjustments: unadjusted, severity only, age + severity + site + HbA1c + BMI, and that plus log marker magnitude — the last being the primary family, because E1.4 showed marker magnitude dominates unrecognized status and age is the only term holding across all heart models. FDR within that family. Nerve is absent by definition: no neuropathy self-report item exists (E0.GATE), so unrecognized status cannot be defined for it.
**Result:** H3 IS NULL. Of 6 fully-adjusted models, 1 reach p < 0.05 and 0 survive FDR. Surviving: none. Eligible denominators: kidney 315 abnormal with the item answered, 226 never told; heart 447 abnormal with the item answered, 298 never told; either 615 abnormal with the item answered, 471 never told. Note the asymmetry with E2C.1: depression tracks NERVE damage, the one organ for which unrecognized status cannot be computed at all.
**Decision:** keep
**Output:** results/E2C_2.csv

### E2C.3 — 2026-08-17
**Method:** PAID-5, continuous and at the >= 8 distress cutoff, against each damage outcome: unadjusted, adjusted for age + severity + site, and + HbA1c. Same recipe as E2C.1; FDR within the adjusted family.
**Result:** Of 16 adjusted models, 1 reach p < 0.05 and 0 survive FDR. Surviving: none. PAID-5 was administered cohort-wide, not only to the diabetic groups — coverage Healthy 97.0%, Pre-DM 98.4%, Oral Med 97.8%, Insulin 98.4% — so it spans the severity spectrum and needs no scope caveat.
**Decision:** keep
**Output:** results/E2C_3_sweep.csv

### E2C.3 — 2026-08-17
**Method:** PAID-5 coverage and mean score by severity group, bounding what the exposure can claim.
**Result:** Healthy: 753/776 (97.0%), mean 2.57; Pre-DM: 551/560 (98.4%), mean 4.44; Oral Med: 671/686 (97.8%), mean 4.63; Insulin: 254/258 (98.4%), mean 5.61
**Decision:** keep
**Output:** results/E2C_3_coverage.csv

### E2C.3 — 2026-08-17
**Method:** CES-D-10 vs PAID-5 head-to-head against nerve damage on the identical complete-case sample (n=2,217), each alone and then mutually adjusted, so the two questionnaires are compared rather than two samples.
**Result:** CES-D-10 total/abn_nerve: 1.2104 (1.0686-1.371), p=0.00267; CES-D-10 total/monofilament_missed: 0.115 (0.0342-0.1957), p=0.00529; PAID-5 total/abn_nerve: 0.9909 (0.8681-1.1311), p=0.892; PAID-5 total/monofilament_missed: -0.0104 (-0.0916-0.0708), p=0.802; PAID-5 >= 8/abn_nerve: 0.9964 (0.7214-1.3762), p=0.982; PAID-5 >= 8/monofilament_missed: -0.0088 (-0.2076-0.1901), p=0.931; CES-D-10 >= 10/abn_nerve: 1.4326 (1.053-1.949), p=0.0221; CES-D-10 >= 10/monofilament_missed: 0.2494 (0.0496-0.4491), p=0.0144; cesd_total | mutually adjusted/abn_nerve: 1.2516 (1.0942-1.4317), p=0.00107; paid_total | mutually adjusted/abn_nerve: 0.9101 (0.7881-1.0511), p=0.2; cesd_total | mutually adjusted/monofilament_missed: 0.1331 (0.0475-0.2187), p=0.00232; paid_total | mutually adjusted/monofilament_missed: -0.0548 (-0.1408-0.0311), p=0.211
**Decision:** keep
**Output:** results/E2C_3_nerve_head_to_head.csv

### E2B.1 — 2026-08-17
**Method:** BMI, continuous and at the >= 30 obesity cutoff, against each damage outcome: unadjusted, adjusted for age + severity + site, and + HbA1c. Odds ratios per 1 SD; FDR within the adjusted family.
**Result:** Of 16 adjusted models, 11 reach p < 0.05 and 10 survive FDR. Surviving: BMI (kg/m2) -> Any of the three organs abnormal: 1.263 (1.1388-1.4007), q=0.000158; BMI (kg/m2) -> Insensate sites, worse foot (0-10): 0.1623 (0.0804-0.2442), q=0.000841; BMI (kg/m2) -> Nerve abnormal (>= 2 insensate sites): 1.2742 (1.1224-1.4466), q=0.000964; Obese (BMI >= 30) -> Any of the three organs abnormal: 1.4037 (1.1438-1.7228), q=0.00469; Obese (BMI >= 30) -> Heart abnormal (hs-cTnT >= 14 ng/L): 1.4721 (1.1521-1.8808), q=0.00635; BMI (kg/m2) -> Heart abnormal (hs-cTnT >= 14 ng/L): 1.206 (1.0657-1.3647), q=0.00755; BMI (kg/m2) -> log hs-cTnT (ng/L): 0.0322 (0.0107-0.0537), q=0.00755; Obese (BMI >= 30) -> log hs-cTnT (ng/L): 0.0608 (0.018-0.1037), q=0.0108; and 2 more. 0 of 10 raw associations are lost once age + severity + site enter, which is the expected direction: BMI is entangled with severity by design.
**Decision:** keep
**Output:** results/E2B_1_sweep.csv

### E2B.1 — 2026-08-17
**Method:** Side-by-side unadjusted and adjusted BMI effects, flagging which raw associations do not survive age + severity + site.
**Result:** Lost to adjustment: none. Surviving adjustment: bmi/abn_heart, bmi/abn_nerve, bmi/abn_any, bmi/abn_multi, bmi_obese/abn_heart, bmi_obese/abn_nerve, bmi_obese/abn_any
**Decision:** keep
**Output:** results/E2B_1_attenuation.csv

### E2B.1 — 2026-08-17
**Method:** Damage prevalence by clinical BMI band, descriptive and unadjusted.
**Result:** <18.5: n=22, any 36.4%; 18.5-25: n=562, any 28.8%; 25-30: n=750, any 34.4%; 30-35: n=457, any 39.2%; >=35: n=481, any 37.3%
**Decision:** keep
**Output:** results/E2B_1_bands.csv

### E2B.1 — 2026-08-17
**Method:** BMI (per SD) vs any-organ damage within each severity group, age + site adjusted, bootstrap intervals where the smaller cell is under 50.
**Result:** Healthy OR=1.1507 (0.9557-1.3853), p=0.138; Pre-DM OR=1.3521 (1.1037-1.6564), p=0.00358; Oral Med OR=1.2398 (1.0366-1.4829), p=0.0186; Insulin OR=1.3033 (0.9679-1.755), p=0.081
**Decision:** keep
**Output:** results/E2B_1_by_severity.csv

### E2E.1 — 2026-08-17
**Method:** UNADJUDICATED, MACHINE-GENERATED, PHYSICIAN-UNREVIEWED. Machine-read prior infarct statements harvested from the WFDB .hea headers (build_ecg_statements.py) against self-reported heart attack (survey precedes the visit by a median 35 days — `E2.TIMING`). Certainty tiers kept separate rather than pooled; acute/recent patterns excluded, since those are not PRIOR infarcts. Repeat ECGs deduplicated to the first record. Reported as one supplementary row, never a headline (PROJECT_CONTEXT decision 2).
**Result:** UNADJUDICATED. All 2,251 of 2,251 ECG records carry an explicit unconfirmed-diagnosis stamp. 179 participants have an unhedged machine-read prior-infarct pattern; of the 178 who also answered the heart-attack item, 149 (83.7%, 95% CI 77.6-88.4) reported no heart attack. Including hedged statements raises the pattern count to 280. Tier counts: none 1945; definite prior infarct 179; probable prior infarct 54; consider prior infarct 47; acute or recent only 26. This is a waveform-pattern statement, not a diagnosis, and must be labelled unadjudicated everywhere it appears including figures.
**Decision:** keep
**Output:** results/E2E_1_unrecognized.csv

### E2E.1 — 2026-08-17
**Method:** Machine-read infarct statement counts by certainty tier (UNADJUDICATED).
**Result:** none: 1945 (86.41%); definite prior infarct: 179 (7.95%); probable prior infarct: 54 (2.4%); consider prior infarct: 47 (2.09%); acute or recent only: 26 (1.16%)
**Decision:** keep
**Output:** results/E2E_1_tiers.csv

### E2E.1 — 2026-08-17
**Method:** Troponin abnormality rate and median by machine-read infarct tier, checking whether the ECG pattern co-travels with biochemical injury (UNADJUDICATED).
**Result:** acute or recent only: n=26, 20.8% troponin-abnormal, median 9.0 ng/L; consider prior infarct: n=47, 27.7% troponin-abnormal, median 7.73 ng/L; definite prior infarct: n=179, 32.8% troponin-abnormal, median 9.83 ng/L; none: n=1945, 18.8% troponin-abnormal, median 7.84 ng/L; probable prior infarct: n=54, 17.0% troponin-abnormal, median 7.71 ng/L
**Decision:** keep
**Output:** results/E2E_1_by_tier.csv

### E2E.2 — 2026-08-17
**Method:** ECG numeric metrics (rate, PR, QRS duration, QT, QTc) from the manifest — instrument measurements, NOT machine interpretations, so not subject to the E2E.1 unadjudicated caveat — against each damage outcome, unadjusted and adjusted for age + severity + site. Repeat ECGs deduplicated to the first record before merging. Effects per 1 SD; FDR within the adjusted family.
**Result:** Of 40 adjusted models, 27 reach p < 0.05 and 23 survive FDR. Surviving: QRS duration (ms) -> log hs-cTnT (ng/L): 0.1078 (0.0876-0.128), q=1.98e-23; QRS duration (ms) -> Any of the three organs abnormal: 1.4621 (1.3199-1.6196), q=6.75e-12; QRS duration (ms) -> Heart abnormal (hs-cTnT >= 14 ng/L): 1.4358 (1.2934-1.5939), q=1.52e-10; ECG heart rate (bpm) -> log urine ACR (mg/g): 0.2264 (0.1438-0.309), q=8.56e-07; QRS duration (ms) -> Insensate sites, worse foot (0-10): 0.1779 (0.0985-0.2573), q=9.22e-05; QRS duration (ms) -> Nerve abnormal (>= 2 insensate sites): 1.2519 (1.1272-1.3904), q=0.000137; QTc interval (ms) -> log hs-cTnT (ng/L): 0.0438 (0.0234-0.0642), q=0.000137; ECG heart rate (bpm) -> log hs-cTnT (ng/L): 0.0464 (0.025-0.0678), q=0.000137; and 15 more. Coverage 2251 participants with QTc.
**Decision:** keep
**Output:** results/E2E_2_sweep.csv

### E2E.2 — 2026-08-17
**Method:** Each ECG metric against the heart marker specifically (abnormal troponin and log troponin), age + severity + site adjusted — the internal-corroboration check on whether the troponin signal is cardiac.
**Result:** Metrics associated with the heart marker at q<0.05: ECG heart rate (bpm)/abn_heart est=1.2058 (q=0.00312); ECG heart rate (bpm)/log_troponin est=0.0464 (q=6.84e-05); PR interval (ms)/abn_heart est=1.1554 (q=0.0145); PR interval (ms)/log_troponin est=0.0328 (q=0.00312); QRS duration (ms)/abn_heart est=1.4358 (q=5.69e-11); QRS duration (ms)/log_troponin est=0.1078 (q=4.95e-24); QTc interval (ms)/abn_heart est=1.2042 (q=0.00165); QTc interval (ms)/log_troponin est=0.0438 (q=6.84e-05)
**Decision:** keep
**Output:** results/E2E_2_coherence.csv


### E2.AGE — 2026-08-17
**Method:** Why adjustment strengthens Phase-2 associations: for every exposure x damage outcome pair, the exposure's correlation with age, the outcome's correlation with age, and the crude vs age-adjusted estimate side by side. Run once as a cross-cutting check rather than re-argued per track.
**Result:** AGE IS A NEGATIVE CONFOUNDER FOR MOST OF PHASE 2. 8 of 9 exposures decline with age while all 5 damage outcomes rise with it. Where the two age correlations have OPPOSITE signs (40 pairs), age adjustment RAISES the estimate in 100% of them (sign test p=1.82e-12), the predicted direction for negative confounding; where they share a sign (5 pairs) it raises it in 60%. So an adjusted estimate here is the less biased one, and an unadjusted estimate is NOT a conservative version of it — Phase 3 must not treat crude numbers in this log as a lower bound. Explains E2C.1 (nerve) and E2B.1 (BMI) appearing only after adjustment, and why the crude steps-damage association is inflated rather than masked.
**Decision:** keep
**Output:** results/E2_AGE_suppression.csv

### E2.AGE — 2026-08-17
**Method:** The prediction stated as a testable claim with a sign test: where exposure and outcome correlate with age in opposite directions, age adjustment should RAISE the estimate; where they correlate in the same direction it should lower it.
**Result:** Opposite-sign pairs: adjusted exceeds crude in 100% (n=40, sign test p=1.82e-12). Same-sign pairs: 60% (n=5).
**Decision:** keep
**Output:** results/E2_AGE_summary.csv

### E2A.1 — 2026-08-17
**Method:** HbA1c, CGM mean glucose, TAR>180, CV and MAGE against each damage outcome, unadjusted and adjusted for age + severity + site (HbA1c excluded from the covariate set here, being an exposure). Odds ratios per 1 SD; FDR within the adjusted family. CV, MAGE and TAR were built from 2,245 per-participant Dexcom streams (build_cgm_metrics.py), the E0.3 BUILD REQUIRED item.
**Result:** Of 40 adjusted models, 33 reach p < 0.05 and 33 survive FDR. Surviving: HbA1c (%) -> log urine ACR (mg/g): 0.3369 (0.2444-0.4295), q=5.09e-11; CGM time above 180 mg/dL (%) -> Kidney abnormal (ACR >= 30 mg/g): 1.4926 (1.3263-1.6797), q=4.5e-10; CGM mean glucose (mg/dL) -> Kidney abnormal (ACR >= 30 mg/g): 1.4815 (1.319-1.6641), q=4.5e-10; HbA1c (%) -> Kidney abnormal (ACR >= 30 mg/g): 1.4902 (1.3217-1.6802), q=7.18e-10; CGM time above 180 mg/dL (%) -> log urine ACR (mg/g): 0.2959 (0.2018-0.39), q=6.73e-09; CGM time above 180 mg/dL (%) -> Any of the three organs abnormal: 1.4172 (1.2651-1.5875), q=1.15e-08; CGM mean glucose (mg/dL) -> log urine ACR (mg/g): 0.2782 (0.1868-0.3697), q=1.59e-08; CGM mean glucose (mg/dL) -> Any of the three organs abnormal: 1.4077 (1.2545-1.5796), q=3.02e-08; and 25 more. Coverage: HbA1c (%) n=2211, CGM mean glucose (mg/dL) n=2245, CGM time above 180 mg/dL (%) n=2245, CGM coefficient of variation (%) n=2245, CGM MAGE (mg/dL) n=2244. Built CGM mean reproduces the manifest mean (median |diff| 0.002 mg/dL, n=2245).
**Decision:** keep
**Output:** results/E2A_1_sweep.csv

### E2A.1 — 2026-08-17
**Method:** Whether each glycaemic-variability metric (TAR>180, CV, MAGE) and HbA1c adds anything to mean glucose: fitted alone and then with mean glucose in the model, on one identical complete-case sample so the two are comparable.
**Result:** On the shared sample (n=2,244), metrics still significant with mean glucose in the model: glucose_cv/abn_kidney OR=1.3221 (p=1.54e-05); glucose_cv/abn_any OR=1.1363 (p=0.0192); glucose_cv/abn_multi OR=1.2348 (p=0.00467); mage/abn_kidney OR=1.2064 (p=0.0173); hba1c/abn_kidney OR=1.2085 (p=0.0449)
**Decision:** keep
**Output:** results/E2A_1_incremental.csv

### E2A.1 — 2026-08-17
**Method:** CGM censoring sensitivity. The Dexcom writes 'Low'/'High' as strings outside its 40-400 mg/dL reportable range — 39,632 readings across 495 participants in v3.0.0, a defect found and fixed during this build (see CAVEATS). Those are censored, not missing, and are placed at the boundary, which attenuates variability. Every glycaemic exposure is refit excluding the participants over 25% censored.
**Result:** 4 of 20 conclusions change when the 23 heavily-censored participants are excluded: glucose_mean/abn_heart p 0.0011 -> 0.146; glucose_mean/abn_nerve p 0.000947 -> 0.218; glucose_mean/abn_multi p 2.11e-07 -> 0.0663; tar_180/abn_heart p 0.00373 -> 0.0911. Before the fix, 2 participants were dropped entirely and 59 had a mean disagreeing with the manifest by more than 5 mg/dL.
**Decision:** keep
**Output:** results/E2A_1_censoring_sensitivity.csv


### E2A.2 — 2026-08-17
**Method:** Damage among participants whose glycaemia disagrees with their severity label, compared with concordant participants in the same universe: no-diabetes-label with HbA1c >= 6.5% (and the parallel CGM mean >= 154 mg/dL definition) within Healthy + Pre-DM, and Insulin-group participants at target (HbA1c < 7.0%). Adjusted for age + site; severity is excluded because discordance is defined relative to it. FDR across the 15 models.
**Result:** 3 of 15 models survive FDR. Surviving: undiagnosed_range/abn_kidney OR=4.1071 (Wald 2.0606-8.186, bootstrap 1.8291-8.5079), q=0.000893; undiagnosed_range/abn_any OR=2.575 (Wald 1.3478-4.9199, bootstrap 1.3033-5.207), q=0.021; undiagnosed_range_cgm/abn_kidney OR=2.9178 (Wald 1.4401-5.9115, bootstrap 1.247-5.7992), q=0.021. Discordance sizes: No diabetes label, HbA1c >= 6.5% 46/1336 (3.4%); No diabetes label, CGM mean >= 154 mg/dL 55/1336 (4.1%); Insulin group, HbA1c < 7.0% 122/258 (47.3%). DOUBLE-UNRECOGNIZED COUNT: of the 46 participants with no diabetes label but diabetes-range HbA1c, 19 have kidney or heart damage with both self-report items answered and 16 of those reported no corresponding diagnosis.
**Decision:** keep
**Output:** results/E2A_2_models.csv

### E2A.2 — 2026-08-17
**Method:** Damage prevalence with Wilson intervals for discordant and concordant participants side by side, within the same universe, per organ.
**Result:** undiagnosed_range/abn_kidney: discordant 28.3% (n=46) vs concordant 8.7% (n=1259); undiagnosed_range/abn_heart: discordant 21.7% (n=46) vs concordant 12.5% (n=1260); undiagnosed_range/abn_nerve: discordant 11.1% (n=45) vs concordant 11.5% (n=1257); undiagnosed_range/abn_any: discordant 44.4% (n=45) vs concordant 25.5% (n=1256); undiagnosed_range/abn_multi: discordant 11.1% (n=45) vs concordant 6.2% (n=1256); undiagnosed_range_cgm/abn_kidney: discordant 21.2% (n=52) vs concordant 8.7% (n=1243); undiagnosed_range_cgm/abn_heart: discordant 15.1% (n=53) vs concordant 13.0% (n=1243); undiagnosed_range_cgm/abn_nerve: discordant 14.5% (n=55) vs concordant 11.6% (n=1255); undiagnosed_range_cgm/abn_any: discordant 30.8% (n=52) vs concordant 26.0% (n=1240); undiagnosed_range_cgm/abn_multi: discordant 11.5% (n=52) vs concordant 6.3% (n=1240); insulin_at_target/abn_kidney: discordant 28.9% (n=121) vs concordant 33.1% (n=124); insulin_at_target/abn_heart: discordant 49.2% (n=122) vs concordant 50.0% (n=126); insulin_at_target/abn_nerve: discordant 23.1% (n=121) vs concordant 29.3% (n=123); insulin_at_target/abn_any: discordant 63.3% (n=120) vs concordant 68.9% (n=122); insulin_at_target/abn_multi: discordant 29.2% (n=120) vs concordant 33.6% (n=122)
**Decision:** keep
**Output:** results/E2A_2_prevalence.csv

### E2A.2 — 2026-08-17
**Method:** Size of each glycaemia/label discordance group and the universe it sits in.
**Result:** No diabetes label, HbA1c >= 6.5%: 46/1336 (3.4%); No diabetes label, CGM mean >= 154 mg/dL: 55/1336 (4.1%); Insulin group, HbA1c < 7.0%: 122/258 (47.3%)
**Decision:** keep
**Output:** results/E2A_2_discordance.csv


### E2F.1 — 2026-08-17
**Method:** Healthcare access barriers, prescription unaffordability, food insecurity (USDA 5-item short form), housing insecurity and clinician discrimination against unrecognized status, per organ and either organ. Unadjusted and fully adjusted (age + severity + site + HbA1c + BMI + log marker magnitude), the latter being the primary family with FDR applied. Scores built by omop.phenx_scores, which handles the non-monotonic coding of pxhi1/pxfi1/pxfi2, excludes skip-gated items from sums, and drops nominal items.
**Result:** 1 of 18 fully-adjusted models survive FDR (3 reach p < 0.05 uncorrected). Surviving: Healthcare access barriers (0-3) -> Unrecognized — heart: 0.6599 (0.53-0.8215), q=0.00361. Coverage: Healthcare access barriers (0-3) n=2055, Prescription unaffordability (0-4) n=2022, Food insecurity, USDA count (0-5) n=2242, Food insecure (USDA >= 2) n=2242, Housing insecure (no steady place or at risk) n=2053, Clinician discrimination, mean (1-5) n=2048. NOT a correction of any published finding: the EDA-era 'insecurity paradox' was an artifact of the positional-slicing bug and existed only in this repo (CAVEATS).
**Decision:** keep
**Output:** results/E2F_1_models.csv

### E2F.1 — 2026-08-17
**Method:** Mean SDOH score by severity group, as a scoring sanity check — barriers should coexist and should not be flat across a cohort where severity tracks socioeconomic position.
**Result:** Healthy: access 0.186, food 0.287, discrimination 1.353; Pre-DM: access 0.193, food 0.384, discrimination 1.397; Oral Med: access 0.226, food 0.561, discrimination 1.34; Insulin: access 0.445, food 1.118, discrimination 1.42
**Decision:** keep
**Output:** results/E2F_1_by_group.csv

### E2F.1 — 2026-08-17
**Method:** Access barriers vs unrecognized status within each severity group, fully adjusted, as the plan requires for insecurity variables. Both the pre-declared either-organ outcome and the heart outcome where the pooled association survived.
**Result:** unrec_either/Healthy OR=0.6633 (0.3745-1.1749), n=124, p=0.159; unrec_either/Pre-DM OR=0.9566 (0.6391-1.432), n=99, p=0.829; unrec_either/Oral Med OR=0.8725 (0.6096-1.2487), n=184, p=0.456; unrec_either/Insulin OR=1.1272 (0.6668-1.9056), n=121, p=0.655; unrec_heart/Healthy OR=0.5612 (0.3174-0.9922), n=83, p=0.0469; unrec_heart/Pre-DM OR=0.3851 (0.1872-0.7922), n=62, p=0.00952; unrec_heart/Oral Med OR=0.7103 (0.4776-1.0564), n=128, p=0.0912; unrec_heart/Insulin OR=0.7694 (0.4865-1.2168), n=102, p=0.262
**Decision:** keep
**Output:** results/E2F_1_by_severity.csv

### E2D.1 — 2026-08-17
**Method:** Garmin steps, resting heart rate, stress, sleep and SpO2 against each damage outcome: unadjusted, adjusted for age + severity + site, and + HbA1c. Error codes cleaned (0 for HR/SpO2, -2 for stress) and asserted absent; sleep converted from fraction-of-day; respiratory rate excluded as a known device quirk. Effects per 1 SD; FDR within the adjusted family. ONE PASS by standing decision — wearables are not part of this paper's identity.
**Result:** Of 40 adjusted models, 8 reach p < 0.05 and 5 survive FDR. Surviving: Daily steps -> Heart abnormal (hs-cTnT >= 14 ng/L): 0.786 (0.6799-0.9087), q=0.0151; Resting heart rate (bpm) -> log urine ACR (mg/g): 0.1577 (0.0674-0.248), q=0.0151; Garmin stress score -> log urine ACR (mg/g): 0.1471 (0.0606-0.2337), q=0.0151; Daily steps -> Insensate sites, worse foot (0-10): -0.1353 (-0.2222--0.0485), q=0.0227; Daily steps -> Two or more organs abnormal: 0.7513 (0.6214-0.9083), q=0.0251. Coverage varies widely, so effects are not comparable across exposures without it: Daily steps n=1994, Resting heart rate (bpm) n=1987, Garmin stress score n=1987, Sleep (hours/night) n=2053, SpO2 (%) n=1628. Cross-sectional: steps and heart rate are as plausibly consequences of damage as causes, so any survivor is a correlate only.
**Decision:** keep
**Output:** results/E2D_1_sweep.csv

### E2D.1 — 2026-08-17
**Method:** Per-exposure wearable coverage, bounding cross-exposure comparison.
**Result:** Daily steps: 1994 (87.5%); Resting heart rate (bpm): 1987 (87.1%); Garmin stress score: 1987 (87.1%); Sleep (hours/night): 2053 (90.0%); SpO2 (%): 1628 (71.4%)
**Decision:** keep
**Output:** results/E2D_1_coverage.csv

### E2D.1 — 2026-08-17
**Method:** DEFECT FOUND AND FIXED. The same adjusted sweep run on the sentinel-only cleaning and on the bounded cleaning, to measure what the contaminated manifest averages were doing. AI-READI computed the Garmin averages with the device error codes included, so 12 heart rates under 30 bpm (lowest 0.03) and 113 negative stress scores on a 0-100 scale survived the documented sentinel scrub. `wearables.clean_garmin_manifest` now applies GARMIN_PLAUSIBLE_RANGES; CAVEATS.md updated.
**Result:** Values dropped by the bounds: heartrate bpm 12, stress level 113, sleep hours 131, oxygen saturation pct 0, daily activity 147. 3 of 40 adjusted conclusions change: steps/abn_any q 0.0468 -> 0.111; heart_rate/log_acr q 0.0661 -> 0.0151; stress/log_acr q 0.0506 -> 0.0151. No Phase-1 result is affected — Phase 1 uses no wearable variable, and all five Phase-1 verifiers still pass after the master table was rebuilt.
**Decision:** keep
**Output:** results/E2D_1_plausibility_sensitivity.csv

### E2.CLOSE — 2026-08-17
**Method:** Phase-2 close-out. Ten experiments across six tracks plus the E2.AGE cross-cutting check, all exploratory, all logged including nulls. Two BUILD REQUIRED items from E0.3 were built first: CGM variability metrics from 2,245 Dexcom streams and ECG interpretation statements from 2,251 WFDB headers. Verification: `verify_e2c.py` and `verify_e2_tracks.py` (111 checks) rebuild every exposure and outcome from the raw CSVs without importing `aireadi` and refit through a different statsmodels API; `verify_phase2_report.py` (105 checks) audits the phase report in both directions — every quoted number must trace to an artifact AND every FDR survivor must appear in the prose. All three report zero discrepancies. Benjamini-Hochberg applied within each experiment's adjusted family, since Phase 3 ranks findings off this log.
**Result:** AIM 2 IS NOT NULL AND IS ORGAN-SPECIFIC: CES-D-10 tracks nerve damage (OR 1.218 per SD, 1.077-1.377, q=0.027; screen-positive OR 1.480, q=0.044) and nothing else — kidney and heart are flat. Age is the suppressor (crude OR 1.078 p=0.19 -> 1.262 with age alone), it survives dropping all 20 clinically odd monofilament rows (OR 1.194, p=0.006), and it is specific to depression not diabetes distress (same sample n=2,217: CES-D 1.252 p=0.0011, PAID-5 0.910 p=0.20 mutually adjusted). Other keepers: participants with no diabetes label but HbA1c>=6.5% (n=46) carry 4.11x the kidney damage (Wald 2.06-8.19, bootstrap 1.83-8.51, q=0.0009), replicated by an independent CGM definition (2.92, q=0.021), and 16 of the 19 of them with kidney/heart damage reported no diagnosis; ECG QRS duration corroborates the troponin marker (q=5e-24), strengthening Aim 1's heart half; CGM CV is the only variability metric adding anything beyond mean glucose (kidney OR 1.322, q=0.0003) while TAR>180 and MAGE add nothing; BMI tracks every organ except kidney (kidney OR 1.026, q=0.75). CLEAN NULLS: H3 (E2C.2) — depression does not predict being unrecognized, and all six fully-adjusted estimates point the OPPOSITE way; PAID-5 (E2C.3) entirely; insulin-group-at-target shows no damage difference. NOTABLE NEGATIVE: access barriers do NOT explain unrecognized status — the one survivor of 18 runs opposite to the hypothesis (heart OR 0.660, 0.530-0.822, q=0.0036) and holds within all four severity groups, most plausibly treatment burden and reverse causation. E2.AGE: age is a negative confounder for 8 of 9 exposures while all damage outcomes rise with age; adjustment raises the estimate in 100% of the 40 opposite-sign pairs (sign test p=1.8e-12), so an unadjusted number in this log is NOT a conservative version of the adjusted one and Phase 3 must not rank it as a lower bound.
**Decision:** keep — Phase 2 complete. Recommended to Phase 3 for the headline set: the nerve depression finding (Aim 2), the undiagnosed-range kidney result, ECG corroboration as supplement, and the access-barrier negative stated plainly. Not recommended: BMI (real but unsurprising and P2 territory), wearables (direction uninterpretable), PAID-5 and E2C.2 (null). Open for Evan before E3.2: the nerve finding's causal direction is genuinely ambiguous and must be stated as such; whether E2E.1's 83.7% stays one supplementary row now that the number is known; whether the E2.AGE sentence enters Methods.
**Output:** none (30 artifacts across E2C.1-E2F.1, notebooks/02_phase2_extension_tracks.ipynb, reports/2026-08-17-phase2-report.md)

### E2.DEFECTS — 2026-08-17
**Method:** Three data defects found while running Phase 2, each fixed in `src/aireadi` and documented in `docs/CAVEATS.md`, with the fix's effect measured rather than asserted. Phase 1 was re-verified after each.
**Result:** (1) URINE ALBUMIN REPORTING FLOOR: 254 participants have a urine albumin of exactly 0 — carrying the "=" operator, not a below-detection flag, with the smallest positive value 0.01 mg/dL — so a bare log(ACR) drops all 254, and they are 14.5% of Healthy against 8.5% of Insulin, which would have biased every continuous kidney association toward a flatter severity gradient. Now substituted at half the floor; `log_acr_positive` keeps the drop-the-zeros version for sensitivity. (2) GARMIN MANIFEST AVERAGES ARE CONTAMINATED: AI-READI computed `average_*` with the device error codes included, so a contaminated mean lands between the sentinel and the truth and passes any `!= 0` test — 12 resting heart rates under 30 bpm (lowest 0.03), 113 NEGATIVE stress scores on a 0-100 scale, 131 implausible sleep averages, 147 step averages of exactly 0 after 16 days of wear. `GARMIN_PLAUSIBLE_RANGES` now applies after the scrub; THREE of 40 conclusions change (steps vs any-organ stops surviving FDR q 0.047->0.111; heart rate and stress vs log ACR start surviving, 0.066->0.015 and 0.051->0.015). PAPER 2 LEANS ON THESE COLUMNS AND MUST REBUILD ITS TABLES. (3) DEXCOM SENTINEL STRINGS: the G6 writes "Low" and "High" as STRINGS outside its 40-400 mg/dL reportable range — 39,632 readings across 495 participants (22% of the cohort), 34,449 High and 5,183 Low. float() raises and the reading vanishes, stripping data from precisely the worst-controlled participants: one had 2,258 of 2,568 readings as "High" and two lost their entire stream. These are censored like the troponin below-detection rows and are now placed at the boundary with per-participant counts retained; all 2,245 participants now yield usable metrics (was 2,243). Additionally, TWO PHENX BATTERIES ARE NON-MONOTONIC IN THEIR CODED VALUES: `pxhi1` runs 0=no steady place, 1=steady, 2=at risk, so security is 1>2>0; `pxfi1`/`pxfi2` have level 1 rarer than level 2, the tell that the answer order is never/often/sometimes. Three items are skip-gated and two nominal. `omop.phenx_scores` owns all of this.
**Decision:** keep — NO PHASE-1 RESULT IS AFFECTED. Phase 1 uses no wearable, CGM or SDOH variable, and the only Phase-1 analysis using log ACR (E1.4) runs on abnormal participants only, where no zeros exist. All five Phase-1 verifiers and 54 unit tests pass after the master table was rebuilt.
**Output:** none (fixes in src/aireadi/associations.py, wearables.py, omop.py, constants.py; docs/CAVEATS.md)

### E2.TIMING — 2026-08-20
**Method:** Checked the actual dates behind the paper's "same-day" language, prompted by an audit of the eye scoping. Compared `observation_date` for the survey batteries against `measurement_date` for each objective marker, per participant.
**Result:** THE TESTS ARE CONCURRENT; THE SURVEY IS NOT. Urine albumin and troponin share a date for 2,223 of 2,225 participants (99.9%), and visual acuity is same-day as troponin for 95.5% of 2,214 — so "three tests at one study visit" is correct. But the `mhoccur` medical-history battery precedes the clinic visit by a median of 35 days (IQR 20-54), same-day for only 3.4%, and the identical lag applies to every survey in the battery: CES-D-10 (3.5% same-day), PAID-5 (2.0%), the ophthalmic survey (3.7%). Marker-by-marker same-day agreement with the history survey is 3.3% urine albumin, 3.4% troponin, 3.8% monofilament, 3.9% visual acuity — uniform, so no organ is advantaged or disadvantaged relative to another.
**Decision:** keep — WORDING FIX ONLY, NO RESULT CHANGES. Every analysis joins survey to marker per participant, which is correct regardless of the interval; no number moves. Corrected in `README.md` (root and paper), `PLAN.md` and two `RESULTS_LOG.md` method lines; recorded as required Methods statement 4 above. The bias runs toward overstating unawareness (a diagnosis received in the interval reads as "never told"), which is the same direction as the self-report limitation already declared, so the headline is conservative rather than inflated.
**Output:** none (documentation only)

### E2.OPEN — 2026-08-25
**Method:** The three items `E2.CLOSE` left open for Evan, settled on Claude's judgement so `E3.2` starts from a position rather than three questions. Each is recorded with the alternative that was weighed, marked with an asterisk in the phase report, so any of them can be reopened without reconstructing the argument. NONE IS FROZEN — freezing happens when `PRESPEC.md` is dated, and Evan overrides any of the three.
**Result:** (1) NERVE–DEPRESSION DIRECTION: reported as an association with both causal pathways named in the same sentence and neither preferred; no directional verb anywhere in the manuscript. The design cannot separate them — exposure and outcome are measured at one visit, and CES-D-10 asks about the past week while insensate sites accumulate over years, so the questionnaire cannot even be ordered before the damage in time. * Alternative set aside: leading with neuropathy -> depression on the strength of the organ-specificity pattern, rejected because that pattern is equally consistent with the reverse (the organ you can feel is also the one whose care low mood degrades first) and a directional claim invites a demand for longitudinal data v3.0.0 does not have. (2) TRACK E: standing decision holds now that the number is known, which is the point at which it was worth re-testing — `E2E.1` keeps one supplementary row, labelled unadjudicated at every appearance including the figure, never in the abstract and never in a main-text figure; `E2E.2` sits beside it as the half of the track that earns its place, being measurements rather than interpretations (QRS vs log troponin q=5e-24). * Alternatives set aside: promoting the 83.7% to a labelled main-text sentence, rejected because Aim 1's credibility rests on three clinically standard markers and the one machine-generated number in the most visible position invites the reviewer to carry that doubt back onto the other three; and dropping `E2E.1` altogether, rejected as selective reporting of a completed run that does corroborate directionally (32.8% abnormal troponin in the definite tier vs 18.8% with no pattern). (3) E2.AGE IN METHODS: yes, one sentence where the covariate set is specified, with the sign test (100% of 40 opposite-sign pairs, p=1.8e-12) and the figure in the supplement. * Alternatives set aside: the Discussion, too late because the suspicion forms while the reviewer reads Results; and supplement-only, because the reader who never opens the supplement is the one who needs it.
**Decision:** keep — all three settled, none frozen. `E3.2` writes them into `PRESPEC.md` or overrides them there.
**Output:** none (decisions only; recorded in reports/2026-08-17-phase2-report.md)

### E2.DOCS — 2026-08-25
**Method:** Documentation close-out of Phase 2, no analysis rerun. Audited the phase report against its artifacts by hand in the places the verifier did not reach, embedded the figures that existed but had never entered the report, and folded in `E2.TIMING`, which post-dates the report.
**Result:** DEFECT FOUND IN THE REPORT, NOT THE ANALYSIS. The `E2.AGE` narrative quoted daily steps -0.26 and resting heart rate -0.23 as their correlations with age; `E2_AGE_suppression.csv` says -0.298 and -0.271. Both were recalled rather than re-read, which is the failure mode the project rule exists to prevent, and `verify_phase2_report.py` had never checked those four quoted correlations — only the sign-test summary. Confirmed the analysis itself is sound: all nine exposure-age correlations recompute exactly from the current master table, so the artifact is right and only the prose was wrong. Also confirmed the cached master table is post-fix despite a misleading mtime — its Garmin columns carry no negative stress, no heart rate under 30 and no zero-step averages, and coverage matches E2D.1's reported n exactly. Report corrected; ten figures added (E2.AGE, E2C.1 and its robustness panel, E2C.3, E2A.1, E2A.2, the shared E2B/E2E panel, E2E.1, E2F.1 and its scoring panel), Track D's deliberate absence of a figure stated in the text rather than left as a gap; `E2.TIMING` written up as its own section, flagged as the one section a verifier cannot trace because that check produced documentation instead of a CSV; `PLAN.md` header corrected from "not started" to complete. `verify_phase2_report.py` extended to check every quoted age correlation against the artifact and to confirm each referenced figure exists.
**Decision:** keep — NO ANALYSIS NUMBER CHANGES. One report number was wrong and is now right; the artifact it disagreed with was correct all along. Phase 2 is document-complete. Outstanding for Evan: `E2.TIMING` still has no artifact behind it, so the 35-day median is quotable only from this log — worth a small runner before Methods cites it.
**Output:** none (reports/2026-08-17-phase2-report.md; PLAN.md; scripts/verify/verify_phase2_report.py)

### E2.TIMING — 2026-08-25
**Method:** Artifact for the E2.TIMING documentation check (E2.DOCS asked for one before Methods cites the number). Per participant, the interval from each survey battery's date to the troponin draw, which anchors the clinic visit; and pairwise same-day agreement between the objective markers and with the history survey.
**Result:** The mhoccur history battery precedes the clinic visit by a median of 35 days (IQR 20-54), same-day for 3.4% of 2,233 paired participants; 0.5% answered it after the visit. The same lag applies to every survey in the battery: same-day CES-D-10 3.5%, PAID-5 2.0%, PhenX 3.8%, Diabetes 3.7%. The objective tests are concurrent: urine albumin shares a date with troponin for 99.9% of 2,225. Marker-by-marker same-day agreement with the history survey runs 3.3-3.9%, so no organ is advantaged relative to another.
**Decision:** keep — wording artifact only; no result changes, bias runs toward overstating unawareness
**Output:** results/E2_TIMING_survey_lag.csv

### E2.TIMING — 2026-08-25
**Method:** Pairwise same-day agreement between the objective markers, and with the history survey.
**Result:** hs-troponin T (heart): 100.0% same-day as troponin (n=2233), 3.4% same-day as history survey; urine albumin (kidney): 99.9% same-day as troponin (n=2225), 3.3% same-day as history survey; monofilament exam (nerve): 95.7% same-day as troponin (n=2224), 3.8% same-day as history survey; visual acuity (photopic, OD): 95.5% same-day as troponin (n=2214), 3.9% same-day as history survey
**Decision:** keep
**Output:** results/E2_TIMING_marker_concurrence.csv

### E3.1 — 2026-08-25
**Method:** Every model in every Phase-2 primary adjusted family (E2C.1, E2C.2, E2C.3, E2A.1, E2A.2, E2B.1, E2D.1, E2E.2, E2F.1) scored on the plan's four criteria: effect size (per-SD OR >= 1.2, yes/no OR >= 1.5, or standardised beta >= 0.10 SD), survival of adjustment (q < 0.05 in the primary family), consistency across the three sites (refitted within UW, UAB and UCSD with the same covariates; every site on the pooled side of the null), and coherence with the core story (fixed rubric: pre-declared hypotheses and Aim-1-adjacent findings count, tracks with no committed hypothesis do not). Ranked by criteria met, then by the effect's margin over its floor, then q. SECOND RUN of the night: the first run counted three separation-unstable site fits as valid, tripped the spread floor on rounded percentages, scored the descriptive core claims on the crude trend p, and ordered tiers by q alone; all four were caught by the adversarial review and fixed before anything was read from it.
**Result:** 207 Phase-2 associations scored; 79 survive FDR; 78 of those replicate in direction at all three sites; 32 meet all four criteria. Top: E2A.2 undiagnosed_range->abn_kidney 4.1071 (q=0.00089, sites 3/3 same direction); E2A.2 undiagnosed_range_cgm->abn_kidney 2.9178 (q=0.021, sites 3/3 same direction); E2A.2 undiagnosed_range->abn_any 2.575 (q=0.021, sites 3/3 same direction); E2F.1 healthcare_access_barriers->unrec_heart 0.6599 (q=0.0036, sites 3/3 same direction); E2A.1 tar_180->abn_kidney 1.4926 (q=4.5e-10, sites 3/3 same direction); E2A.1 hba1c->abn_kidney 1.4902 (q=7.2e-10, sites 3/3 same direction); E2A.1 glucose_mean->abn_kidney 1.4815 (q=4.5e-10, sites 3/3 same direction); E2A.1 mage->abn_kidney 1.4372 (q=1.6e-07, sites 3/3 same direction); E2E.2 qrsd_ms->abn_heart 1.4358 (q=1.5e-10, sites 3/3 same direction); E2E.2 qrsd_ms->log_troponin 0.1078 (q=2e-23, sites 3/3 same direction); E2A.1 tar_180->abn_any 1.4172 (q=1.2e-08, sites 3/3 same direction); E2A.1 glucose_mean->abn_multi 1.4135 (q=6.5e-07, sites 3/3 same direction).
**Decision:** keep — feeds E3.2
**Output:** results/E3_1_ranking.csv

### E3.1 — 2026-08-25
**Method:** Per-site refit of every scored Phase-2 association (site dropped as a covariate).
**Result:** 621 site-level fits (207 associations x 3 sites); 3 did not yield a usable fit (separation in tiny cells), recorded as NaN with a note and excluded from direction counting.
**Decision:** keep
**Output:** results/E3_1_site_replication.csv

### E3.1 — 2026-08-25
**Method:** The Phase-1 core claims (prevalence, unrecognized fraction, burden, multi-organ trends) on the same four criteria: effect size = Insulin-minus-Healthy spread >= 10 points from the counts; adjustment = a logistic model of the flag on an ordinal severity score + age + site (the E1.4 model A and C Insulin terms carried alongside for the two recognition claims); site consistency = the trend keeps its sign inside every site.
**Result:** kidney prevalence rises with severity: spread 22.02 pts, sites same-direction 3/3, criteria 4/4; heart prevalence rises with severity: spread 36.54 pts, sites same-direction 3/3, criteria 4/4; nerve prevalence rises with severity: spread 14.32 pts, sites same-direction 3/3, criteria 4/4; any-organ prevalence rises with severity: spread 40.21 pts, sites same-direction 3/3, criteria 4/4; kidney unrecognized fraction falls with severity: spread -32.31 pts, sites same-direction 3/3, criteria 4/4; heart unrecognized fraction falls with severity: spread -11.63 pts, sites same-direction 3/3, criteria 4/4; either-organ unrecognized fraction falls with severity: spread -14.96 pts, sites same-direction 3/3, criteria 4/4; kidney unrecognized burden rises with severity: spread 10.03 pts, sites same-direction 3/3, criteria 4/4; heart unrecognized burden rises with severity: spread 21.4 pts, sites same-direction 3/3, criteria 4/4; either-organ unrecognized burden rises with severity: spread 25.1 pts, sites same-direction 3/3, criteria 4/4; two-or-more organs rises with severity: spread 25.23 pts, sites same-direction 3/3, criteria 4/4
**Decision:** keep
**Output:** results/E3_1_core_claims.csv

### E3.1 — 2026-08-25
**Method:** Per-site prevalence / unrecognized / burden trends behind the core-claim scoring.
**Result:** kidney prevalence rises with severity@UW: z=5.132; kidney prevalence rises with severity@UAB: z=5.519; kidney prevalence rises with severity@UCSD: z=4.395; heart prevalence rises with severity@UW: z=7.642; heart prevalence rises with severity@UAB: z=6.747; heart prevalence rises with severity@UCSD: z=4.397; nerve prevalence rises with severity@UW: z=4.979; nerve prevalence rises with severity@UAB: z=2.62; nerve prevalence rises with severity@UCSD: z=0.467; any-organ prevalence rises with severity@UW: z=8.189; any-organ prevalence rises with severity@UAB: z=6.414; any-organ prevalence rises with severity@UCSD: z=3.904; kidney unrecognized fraction falls with severity@UW: z=-2.567; kidney unrecognized fraction falls with severity@UAB: z=-2.967; kidney unrecognized fraction falls with severity@UCSD: z=-1.732; heart unrecognized fraction falls with severity@UW: z=-1.088; heart unrecognized fraction falls with severity@UAB: z=-1.514; heart unrecognized fraction falls with severity@UCSD: z=-1.134; either-organ unrecognized fraction falls with severity@UW: z=-1.542; either-organ unrecognized fraction falls with severity@UAB: z=-2.109; either-organ unrecognized fraction falls with severity@UCSD: z=-0.976; kidney unrecognized burden rises with severity@UW: z=2.805; kidney unrecognized burden rises with severity@UAB: z=3.299; kidney unrecognized burden rises with severity@UCSD: z=2.566; heart unrecognized burden rises with severity@UW: z=5.595; heart unrecognized burden rises with severity@UAB: z=4.108; heart unrecognized burden rises with severity@UCSD: z=2.648; either-organ unrecognized burden rises with severity@UW: z=5.577; either-organ unrecognized burden rises with severity@UAB: z=4.571; either-organ unrecognized burden rises with severity@UCSD: z=3.663; two-or-more organs rises with severity@UW: z=6.778; two-or-more organs rises with severity@UAB: z=6.02; two-or-more organs rises with severity@UCSD: z=3.87
**Decision:** keep
**Output:** results/E3_1_core_claims_by_site.csv

### E3.1 — 2026-08-25
**Method:** Forest of pooled and per-site estimates for the associations meeting all four criteria.
**Result:** Figure written; numbers in E3_1_ranking.csv and E3_1_site_replication.csv.
**Decision:** keep
**Output:** results/E3_1_figure.png

### E3.2 — 2026-08-25
**Method:** Headline set chosen from the E3.1 table and written into PRESPEC.md (version 2026-08-25), dated 2026-08-25 and frozen; sha256 c6bbb2ec2505e9ba0a769b49fba7075344f65a0a31914a1794632013d9190806. Chosen overnight on Claude's judgement under Evan's delegated authority, from the E2.CLOSE / E2.OPEN starting position; the alternatives weighed are recorded in PRESPEC.md §9 so any can be reopened. Evan's sign-off confirms or amends (logged as E3.2.AMEND) before the 26 Aug freeze.
**Result:** HEADLINE SET: A1 the core sweep (prevalence, unrecognized fraction, population burden as the abstract lead, multi-organ counts, E1.4 who-is-unrecognized models) with per-site replication, cutoff sweeps extended to the burden, and bootstrap intervals; A2 CES-D-10 vs the five binary damage outcomes with the plan's covariate set age + BMI + HbA1c + severity + site (BMI is new relative to Phase 2), BH within 10, claim rule q<0.05 in both exposure forms, five robustness checks, H3 rerun; T1 undiagnosed-range glycaemia vs kidney damage (rank 1 of 207 in E3.1, 32 rows meet all four criteria) with Wald + bootstrap intervals and the CGM replication; T2 ECG numeric metrics vs the heart marker, supplement only; T3 the access-barrier negative reported as exploratory. Set aside for the headline: glycaemia (E2A.1; textbook, one sentence on CV beyond mean), BMI, wearables, PAID-5. Framing per E2.DECIDE: burden primary, falling fraction as mechanism. Required Methods statements 1-6 carried into PRESPEC.md §7.
**Decision:** keep — PRESPEC.md frozen 2026-08-25 (sha256 above); not committed to git tonight by Evan's instruction, so the hash is the freeze marker until his morning commit
**Output:** none

### E3.3 — 2026-08-25
**Method:** Confirmatory reruns of the headline set exactly per PRESPEC.md (version 2026-08-25, sha256 c6bbb2ec2505e9ba0a769b49fba7075344f65a0a31914a1794632013d9190806), every parameter read from the spec's machine-readable block: Aim-1 core sweep (must reproduce Phase 1 exactly), Aim 2 with the spec covariates age + BMI + HbA1c + severity + site and BH within the 10-model family, H3, the promoted undiagnosed-range track with Wald and bootstrap intervals, and the ECG corroboration; plus per-site replication, cutoff sweeps extended to the burden, and bootstrap intervals for every small cell.
**Result:** AIM 1 REPRODUCES PHASE 1 EXACTLY (every k, n and % across 55 rows). Per-site: 11/11 core trends keep their sign at every site. Burden rises with severity at every cutoff rung: True. AIM 2 with the spec covariates: CES-D-10 -> nerve OR 1.1606 (1.0193-1.3214) per SD, q=0.245; screen-positive OR 1.3078 (0.9517-1.7973), q=0.49; claim rule met for: none; within-site direction 3/3. H3: 0 of 6 survive FDR. T1: undiagnosed-range -> kidney OR 4.1071 (Wald 2.0606-8.186, bootstrap 1.8291-8.5079), q=0.000596; CGM definition OR 2.9178, q=0.014; within-site direction 3/3; double-unrecognized 16 of 19. T2: QRS -> log troponin q=5e-24, same direction at 3 sites.
**Decision:** keep — headline set confirmed per spec
**Output:** results/E3_3_headline_summary.csv

### E3.3 — 2026-08-25
**Method:** A1.1-A1.4 per spec: prevalence, unrecognized fraction (both denominators implicit via E1.2), burden and multi-organ counts, by severity, with Cochran-Armitage trend.
**Result:** Reproduces the Phase-1 artifacts exactly: 55 rows, 0 mismatches.
**Decision:** keep
**Output:** results/E3_3_aim1_confirmatory.csv

### E3.3 — 2026-08-25
**Method:** Every A1 trend refitted within each clinical site.
**Result:** population_burden/either: UW z=5.577, UAB z=4.571, UCSD z=3.663; population_burden/heart: UW z=5.595, UAB z=4.108, UCSD z=2.648; population_burden/kidney: UW z=2.805, UAB z=3.299, UCSD z=2.566; prevalence/any: UW z=8.189, UAB z=6.414, UCSD z=3.904; prevalence/heart: UW z=7.642, UAB z=6.747, UCSD z=4.397; prevalence/kidney: UW z=5.132, UAB z=5.519, UCSD z=4.395; prevalence/nerve: UW z=4.979, UAB z=2.62, UCSD z=0.467; two_or_more_organs/multi: UW z=6.778, UAB z=6.02, UCSD z=3.87; unrecognized_fraction/either: UW z=-1.542, UAB z=-2.109, UCSD z=-0.976; unrecognized_fraction/heart: UW z=-1.088, UAB z=-1.514, UCSD z=-1.134; unrecognized_fraction/kidney: UW z=-2.567, UAB z=-2.967, UCSD z=-1.732
**Decision:** keep
**Output:** results/E3_3_aim1_by_site.csv

### E3.3 — 2026-08-25
**Method:** Percentile bootstrap (2000 resamples, seed 20260817) of every group-level unrecognized fraction and burden, beside the Wilson interval; small-cell rule < 50.
**Result:** unrecognized_fraction/kidney/Healthy: 88.9% Wilson 78.8-94.5 boot 81.0-95.2; unrecognized_fraction/kidney/Pre-DM: 71.4% Wilson 58.5-81.6 boot 58.9-82.1; unrecognized_fraction/kidney/Oral Med: 72.5% Wilson 63.9-79.7 boot 64.2-80.0; unrecognized_fraction/kidney/Insulin: 56.6% Wilson 45.4-67.1 boot 46.0-67.1; unrecognized_fraction/heart/Healthy: 74.2% Wilson 64.7-81.9 boot 66.0-82.5; unrecognized_fraction/heart/Pre-DM: 73.7% Wilson 62.8-82.3 boot 63.2-82.9; unrecognized_fraction/heart/Insulin: 62.6% Wilson 53.8-70.6 boot 53.7-70.7; unrecognized_fraction/either/Healthy: 84.9% Wilson 78.0-89.9 boot 79.1-90.6; unrecognized_fraction/either/Pre-DM: 76.3% Wilson 67.8-83.0 boot 68.6-83.9; unrecognized_fraction/either/Insulin: 69.9% Wilson 62.0-76.8 boot 62.2-76.9; population_burden/kidney/Pre-DM: 7.3% Wilson 5.4-9.8 boot 5.3-9.5; population_burden/kidney/Insulin: 17.4% Wilson 13.2-22.6 boot 12.6-22.3
**Decision:** keep
**Output:** results/E3_3_aim1_bootstrap.csv

### E3.3 — 2026-08-25
**Method:** Population burden re-run at every rung of the kidney and heart cutoff grids, pooled and by severity, including the either-organ burden.
**Result:** Either-organ burden spans 13.6-26.6% across the kidney grid and 14.5-57.9% across the heart grid; the rise with severity holds (z>0, p<0.05) at every rung: True.
**Decision:** keep
**Output:** results/E3_3_burden_sweep.csv

### E3.3 — 2026-08-25
**Method:** A2.1 per spec: CES-D-10 (per SD and >= 10) vs the five binary outcomes, covariates ['age', 'bmi', 'hba1c', 'C(study_group_label)', 'C(clinical_site)'], BH within the 10-model family; insensate sites as the supporting continuous outcome.
**Result:** Claim rule met for no outcome. cesd_total/abn_kidney 0.9155 (0.7983-1.0499) q=0.548; cesd_total/abn_heart 0.925 (0.8126-1.053) q=0.548; cesd_total/abn_nerve 1.1606 (1.0193-1.3214) q=0.245; cesd_total/abn_any 0.9863 (0.8889-1.0942) q=0.882; cesd_total/abn_multi 0.96 (0.8167-1.1283) q=0.882; cesd_positive/abn_kidney 0.8292 (0.5927-1.1599) q=0.548; cesd_positive/abn_heart 0.8671 (0.6338-1.1863) q=0.621; cesd_positive/abn_nerve 1.3078 (0.9517-1.7973) q=0.49; cesd_positive/abn_any 0.9812 (0.7597-1.2674) q=0.885; cesd_positive/abn_multi 0.9457 (0.6431-1.3908) q=0.882
**Decision:** keep
**Output:** results/E3_3_aim2_confirmatory.csv

### E3.3 — 2026-08-25
**Method:** Adjustment ladder for CES-D total -> nerve, so the direction of change under adjustment is visible (E2.AGE).
**Result:** unadjusted: OR 1.0783 p=0.19; + age: OR 1.2615 p=0.000146; + age + severity: OR 1.2211 p=0.00138; + age + severity + site: OR 1.2175 p=0.00168; full spec (+ BMI + HbA1c): OR 1.1606 p=0.0245
**Decision:** keep
**Output:** results/E3_3_aim2_ladder.csv

### E3.3 — 2026-08-25
**Method:** A2.2 robustness: within site, nerve cutoff >= 1 and >= 3, exclusion of the odd monofilament rows, PAID-5 head-to-head on one sample.
**Result:** within site [UW] cesd_total->abn_nerve: 1.0923 p=0.5; within site [UAB] cesd_total->abn_nerve: 1.1016 p=0.353; within site [UCSD] cesd_total->abn_nerve: 1.3301 p=0.0188; within site [UW] cesd_positive->abn_nerve: 1.184 p=0.577; within site [UAB] cesd_positive->abn_nerve: 1.1383 p=0.597; within site [UCSD] cesd_positive->abn_nerve: 1.8813 p=0.054; nerve cutoff [>= 1 insensate sites] cesd_total->abn_nerve: 1.0451 p=0.466; nerve cutoff [>= 1 insensate sites] cesd_positive->abn_nerve: 1.0127 p=0.933; nerve cutoff [>= 3 insensate sites] cesd_total->abn_nerve: 1.1806 p=0.0275; nerve cutoff [>= 3 insensate sites] cesd_positive->abn_nerve: 1.429 p=0.0501; drop odd monofilament rows [n dropped = 20] cesd_total->abn_nerve: 1.1403 p=0.0538; drop odd monofilament rows [n dropped = 20] cesd_positive->abn_nerve: 1.2761 p=0.143; PAID-5 head-to-head (identical sample) [alone] cesd_total->abn_nerve: 1.1504 p=0.0342; PAID-5 head-to-head (identical sample) [mutually adjusted for paid_total] cesd_total->abn_nerve: 1.1887 p=0.0152; PAID-5 head-to-head (identical sample) [alone] paid_total->abn_nerve: 0.9728 p=0.696; PAID-5 head-to-head (identical sample) [mutually adjusted for cesd_total] paid_total->abn_nerve: 0.9109 p=0.223
**Decision:** keep
**Output:** results/E3_3_aim2_robustness.csv

### E3.3 — 2026-08-25
**Method:** A2.2(e) CES-D total -> nerve within each severity group, spec covariates minus severity, bootstrap where the smaller cell < 50.
**Result:** Healthy: OR 1.1231 (0.8678-1.4535), n=756; Pre-DM: OR 1.172 (0.8865-1.5496), n=543; Oral Med: OR 1.1736 (0.9352-1.4727), n=657; Insulin: OR 1.2095 (0.8723-1.6771), n=241
**Decision:** keep
**Output:** results/E3_3_aim2_by_severity.csv

### E3.3 — 2026-08-25
**Method:** A2.3 H3 per spec: CES-D-10 vs unrecognized status among the abnormal, recognition covariates + log marker magnitude, BH within 6.
**Result:** 0 of 6 survive FDR; estimates: cesd_total/unrec_kidney 0.9299 q=0.66; cesd_positive/unrec_kidney 0.7141 q=0.45; cesd_total/unrec_heart 0.7608 q=0.13; cesd_positive/unrec_heart 0.6041 q=0.17; cesd_total/unrec_either 0.8321 q=0.17; cesd_positive/unrec_either 0.7158 q=0.31
**Decision:** keep
**Output:** results/E3_3_h3.csv

### E3.3 — 2026-08-25
**Method:** T1 per spec: no-diabetes-label with HbA1c >= 6.5% (and CGM mean >= 154 mg/dL) vs each outcome within Healthy + Pre-DM, age + site adjusted, Wald and percentile-bootstrap (2000, seed 20260817) intervals, BH within 10.
**Result:** Primary: kidney OR 4.1071 (Wald 2.0606-8.186; bootstrap 1.8291-8.5079), q=0.000596, 13/46 exposed abnormal (28.3% vs 8.7%). CGM replication OR 2.9178 q=0.014. Double-unrecognized: 16 of 19 (of 46 undiagnosed-range participants).
**Decision:** keep
**Output:** results/E3_3_track_undiagnosed.csv

### E3.3 — 2026-08-25
**Method:** T1 robustness: within site, ACR cutoff 20/30/50, stricter HbA1c >= 7.0%.
**Result:** within site [UW] abn_kidney: OR 3.1625 (1.1418-8.7593) p=0.0268; within site [UAB] abn_kidney: OR 5.6363 (1.789-17.7579) p=0.00314; within site [UCSD] abn_kidney: OR 3.9323 (0.7273-21.2595) p=0.112; kidney cutoff [ACR >= 20 mg/g] abn_kidney: OR 3.4251 (1.8194-6.4478) p=0.000137; kidney cutoff [ACR >= 30 mg/g] abn_kidney: OR 4.1071 (2.0606-8.186) p=5.96e-05; kidney cutoff [ACR >= 50 mg/g] abn_kidney: OR 3.5804 (1.5203-8.4322) p=0.00352; stricter HbA1c cutoff [HbA1c >= 7.0% (n exposed = 19)] abn_kidney: OR 6.0408 (2.2723-16.0591) p=0.000312; stricter HbA1c cutoff [HbA1c >= 7.0% (n exposed = 19)] abn_any: OR 4.5811 (1.7201-12.2004) p=0.00232
**Decision:** keep
**Output:** results/E3_3_track_undiagnosed_robustness.csv

### E3.3 — 2026-08-25
**Method:** T2 per spec: ECG numeric metrics vs abnormal troponin and log troponin, age + severity + site, BH within 10. Supplement only.
**Result:** rate_bpm/abn_heart 1.2058 q=0.0031; rate_bpm/log_troponin 0.0464 q=6.8e-05; pr_ms/abn_heart 1.1554 q=0.014; pr_ms/log_troponin 0.0328 q=0.0031; qrsd_ms/abn_heart 1.4358 q=5.7e-11; qrsd_ms/log_troponin 0.1078 q=5e-24; qt_ms/abn_heart 1.0279 q=0.71; qt_ms/log_troponin 0.0004 q=0.97; qtc_ms/abn_heart 1.2042 q=0.0016; qtc_ms/log_troponin 0.0438 q=6.8e-05
**Decision:** keep
**Output:** results/E3_3_track_ecg.csv

### E3.3 — 2026-08-25
**Method:** T2 within each site for QRS duration and QTc.
**Result:** qrsd_ms/abn_heart@UW 1.7411 p=3e-08; qrsd_ms/abn_heart@UAB 1.2821 p=0.0057; qrsd_ms/abn_heart@UCSD 1.3638 p=0.00064; qrsd_ms/log_troponin@UW 0.1268 p=3.5e-15; qrsd_ms/log_troponin@UAB 0.0928 p=8.3e-07; qrsd_ms/log_troponin@UCSD 0.1033 p=8.2e-08; qtc_ms/abn_heart@UW 1.3347 p=0.0039; qtc_ms/abn_heart@UAB 1.1536 p=0.12; qtc_ms/abn_heart@UCSD 1.1508 p=0.15; qtc_ms/log_troponin@UW 0.0505 p=0.0016; qtc_ms/log_troponin@UAB 0.0374 p=0.047; qtc_ms/log_troponin@UCSD 0.0447 p=0.022
**Decision:** keep
**Output:** results/E3_3_track_ecg_by_site.csv

### E3.3 — 2026-08-25
**Method:** Figure: either-organ burden by severity within each site.
**Result:** Figure written.
**Decision:** keep
**Output:** results/E3_3_site_replication_figure.png

### E3.3 — 2026-08-25
**Method:** Figure: Aim 2 confirmatory forest per spec.
**Result:** Figure written.
**Decision:** keep
**Output:** results/E3_3_aim2_figure.png

### E3.3 — 2026-08-25
**Method:** Figure: burden across the cutoff grids.
**Result:** Figure written.
**Decision:** keep
**Output:** results/E3_3_burden_sweep_figure.png

### E3.FREEZE — 2026-08-25
**Method:** Results freeze. Everything in the headline set was rerun against PRESPEC.md (sha256 c6bbb2ec2505e9ba0a769b49fba7075344f65a0a31914a1794632013d9190806) in this run; nothing enters the paper after this entry except via a logged deviation.
**Result:** FROZEN. Headline numbers: any-organ prevalence 34.6%; either-organ unrecognized fraction 76.6%; either-organ burden 21.3% overall, 40.7% on insulin; Aim 2 nerve OR 1.1606 per SD (q=0.245); T1 kidney OR 4.1071 (bootstrap 1.8291-8.5079).
**Decision:** keep — frozen 2026-08-26 (run overnight 25/26 Aug); Evan's sign-off on PRESPEC.md pending, amendments logged as E3.2.AMEND
**Output:** none

### E3.3 — 2026-08-25
**Method:** Addendum to the A2.1 adjustment ladder: the Phase-2 model refitted on the spec's complete-case sample (isolating the 68 participants lost to BMI/HbA1c missingness), then HbA1c alone, BMI alone, and the full spec, so the attenuation from OR 1.22 to 1.16 is decomposed rather than asserted.
**Result:** CES-D total -> nerve OR: Phase-2 model on the Phase-2 sample (age + severity + site): 1.2175 (n=2265, p=0.00168); Phase-2 model on the SPEC complete-case sample (same covariates): 1.19 (n=2197, p=0.00705); + HbA1c only: 1.1852 (n=2200, p=0.00974); + BMI only: 1.1928 (n=2262, p=0.00525); full spec (+ BMI + HbA1c): 1.1606 (n=2197, p=0.0245). The three changes each shave a little and none dominates; the estimate never crosses 1 and stays nominally significant, but the corrected q in the 10-model family does not.
**Decision:** keep — explanatory; no spec parameter changed
**Output:** results/E3_3_aim2_decomposition.csv

### E3.1.RUN1 — 2026-08-25 (reconstructed record of the superseded first run)
**Method:** The first execution of `run_e3_1.py` (25 Aug, ~01:10) scored the same 207 associations and 11 core claims. Its five log entries were deleted from this file before the corrected rerun, which the PRESPEC/E3.3 review (`E3.REVIEW`) rightly objected to: the log's rule is that every run is recorded. This entry reconstructs the run from its printed output; its artifacts were overwritten by the rerun at 01:28.
**Result:** 207 associations scored; 79 survived FDR; 78 replicated in direction at all three sites; 33 met all four criteria; core claims meeting all four: 9 of 11. Five bookkeeping defects, all caught by the E3.1 adversarial review: (1) three separation-unstable per-site logistic fits (E2F.1 housing_insecure at one site each for unrec_kidney/heart/either, OR ~1e8-1e9, CI 0-inf) were counted as valid same-direction fits; (2) the 10-point spread floor was compared on rounded percentages, so the kidney burden claim (17.4 - 7.4 = 9.999...) was scored 3/4 instead of 4/4; (3) the effect floor for a yes/no exposure on a continuous outcome used the per-SD threshold; (4) tiers were ordered by q alone; (5) nine of eleven core claims scored 'survives adjustment' on the crude trend p. The membership of the all-four tier changed by one row (CES-D screen-positive -> insensate sites dropped under the stricter floor: 33 -> 32); no headline-set candidate changed status.
**Decision:** superseded by the E3.1 entries above. PRESPEC.md was DRAFTED from this first table (01:13) and CONFIRMED against the corrected one (01:28); the rerun changed nothing in the headline set. Recorded so the chronology in the log matches what happened.
**Output:** none (artifacts overwritten by the rerun)

### E3.REVIEW — 2026-08-25
**Method:** Two adversarial multi-agent reviews run overnight before Phase 3 closed: (1) of `run_e3_1.py` and its artifacts (3 reviewers, 24 candidate findings, each given to a separate refuter; 12 not refuted, 5 real defects — fixed, rerun); (2) of `PRESPEC.md` and `run_e3_3.py` (4 lenses incl. a mentor-perspective interpretation lens and an independent reproduction; 30 candidate findings, 27 not refuted). Independent reproductions in review 2 matched every Aim-1, Aim-2, T1 and T2 number exactly.
**Result:** CONFIRMED AND ACTED ON (in E3.2.AMEND.1 and the E3.3 rerun below): (a) the Aim-2 adjustment ladder changed sample and covariates in the same step, so 'attenuated under adjustment' conflated a 68-participant complete-case loss (~42% of the log-OR drop; the 68 are enriched for both CES-D and nerve abnormality) with the covariates — ladder now on a fixed sample; (b) no missing-data rule was stated — now stated (complete case) with a single-imputation sensitivity; (c) A1.5 (E1.4 who-is-unrecognized models) and the refusals-included denominator were promised and not rerun — now rerun; (d) three Aim-2 robustness sub-tables (within severity, odd-row exclusion, PAID-5 head-to-head) scaled CES-D by the subsample SD, not the cohort-wide SD the spec states — now cohort-wide; (e) T1 robustness rows lacked the small-cell bootstrap — added; (f) the claim rule's prose was ambiguous between 'q<0.05 in the primary form' and 'in both forms' — the runner applies BOTH; stated; (g) per-site 'replication' is a direction sanity check with ~1-in-4 chance agreement under the null — relabelled, and Cochran's Q / I2 now reported; (h) the spec's chronology: PRESPEC was drafted from the first E3.1 run — stated; (i) 'cutoffs fixed at E1.0 before any counting' overstates: the E0.4 kidney spot-check at ACR>=30 predates E1.0 and the nerve cutoff was confirmed at E1.DECIDE with the E1.5 sweep in view — reworded; (j) T1/T2/H3 'reruns' are the Phase-2 models with narrower FDR families (q moves, p does not) — labelled as such and Phase-2 q reported alongside; (k) the stricter HbA1c>=7.0 sensitivity moves the 6.5-6.9 band into the reference group — reported as three bands; (l) the >=1-insensate-site check is the robustness check that FAILS and must be reported as such; (m) small wording defects (covariate-set attribution, H3 double-listing, 'pre-registered expectation'). NOT ACTED ON, by design: restoring the 68 missing participants does not rescue the claim (single imputation: nerve q 0.064 / 0.163) and no multiple-imputation analysis aimed at the verdict will be run; the 10-model family is not what failed the claim — the screen-positive form fails at raw p=0.098 under any family.
**Decision:** keep — Phase 3 does not close until the amendment and the rerun below are in.
**Output:** none (review journals under the session's workflow directory)

### E3.2.AMEND.1 — 2026-08-25
**Method:** Amendment 1 to PRESPEC.md, made 25 Aug after the E3.REVIEW findings and before Evan's sign-off. Pre-amendment sha256 c6bbb2ec2505e9ba0a769b49fba7075344f65a0a31914a1794632013d9190806; post-amendment sha256 c9f2acb6cc294205c64b4dcbaa58c1ac5b5e5e431a583764c7d0c5a52f409deb. The §10 machine-readable parameter block is byte-identical: no cutoff, covariate set, family size, seed or grid changed.
**Result:** ADDED: an explicit missing-data rule (complete case, as executed) with a single-imputation sensitivity A2.4; the claim-rule reading the runner applies (q<0.05 in BOTH exposure forms and same direction); the chronology of the document (drafted from the first E3.1 run, confirmed against the corrected one); a fuller statement of what 'fixed at E1.0' means; cohort-wide SD scaling stated for every Aim-2 row; the adjustment ladder on a fixed sample; the per-site check relabelled a sanity check with Q/I2; T1/T2/H3 reruns labelled as the Phase-2 models with narrowed families; T1's stricter HbA1c cutoff described as a threshold shift with three-band counts; bootstrap on every small-cell T1 robustness row; A1.5 and the refusals-included denominator explicitly required at E3.3; covariate-set attribution, H3 double-listing and 'pre-registered expectation' wording fixed.
**Decision:** keep — amendment logged; the E3.3 rerun that follows runs against the amended document
**Output:** none

### E3.3 — 2026-08-25
**Method:** SECOND RUN of the confirmatory reruns, exactly per PRESPEC.md as amended (version 2026-08-25, sha256 c9f2acb6cc294205c64b4dcbaa58c1ac5b5e5e431a583764c7d0c5a52f409deb), every parameter read from the spec's machine-readable block, which Amendment 1 left byte-identical. What this run adds over the first (see E3.REVIEW): A1.5 and the refusals-included denominator refitted and asserted against Phase 1; CES-D on the cohort-wide SD in every Aim-2 row; the adjustment ladder on a fixed sample as well as the Phase-2 sample; the missing-data single-imputation sensitivity A2.4; bootstrap on every small-cell T1 robustness row and the three HbA1c bands; Cochran's Q / I2 for the model-based site checks; Phase-2 q reported beside the narrowed-family q for T1 and T2.
**Result:** AIM 1 REPRODUCES PHASE 1 EXACTLY (every k, n and %, both denominators, across 55 rows; 46 E1.4 model terms reproduce). Per-site: 11/11 core trends keep their sign at every site (a direction check, not a replication; 7 are significant within all three). Burden rises with severity at every cutoff rung: True (heart at the non-clinical 'detectable' rung p=0.040). AIM 2 with the spec covariates: CES-D-10 -> nerve OR 1.1606 (1.0193-1.3214) per SD, p=0.0245, q=0.245; screen-positive OR 1.3078 (0.9517-1.7973), p=0.098, q=0.49; PRE-SPECIFIED CRITERION NOT MET for any outcome. Attenuation from the Phase-2 OR 1.2175 decomposes on the fixed n=2,197 sample as: same covariates 1.1935 (sample change = 42% of the log-OR drop; the 68 lost participants are 23.5% nerve-abnormal vs 14.3%), + HbA1c 1.1842, + BMI 1.1673, both 1.1606. Missing-data sensitivity (single imputation, n=2,265): OR 1.188 q=0.0638, >=10 OR 1.3933 q=0.163 — criterion still not met. Robustness rows for nerve not significant: 12 (the >=1-insensate-site cutoff erases it: OR 1.0451; dropping the 20 odd monofilament rows p=0.054). Within-site direction 3/3, Q p=0.42. H3: 0 of 6 survive FDR. T1: undiagnosed-range -> kidney OR 4.1071 (Wald 2.0606-8.186, bootstrap 1.8291-8.5079), q=0.000596 (Phase-2 q=0.000893); CGM definition OR 2.9178, q=0.014; within-site direction 3/3, Q p=0.76; double-unrecognized 16 of 19; kidney damage by HbA1c band < 6.5% 109/1259 (8.7%), 6.5-6.9% 6/27 (22.2%), >= 7.0% 7/19 (36.8%). T2: QRS -> log troponin q=5e-24, same direction at 3 sites, Q p=0.35.
**Decision:** keep — headline set rerun per the amended spec; Aim 1 and T1 confirmed, Aim 2 reported as pre-specified criterion not met
**Output:** results/E3_3_headline_summary.csv

### E3.3 — 2026-08-25
**Method:** A1.1-A1.4 per spec: prevalence, unrecognized fraction with BOTH denominators, burden and multi-organ counts, by severity, with Cochran-Armitage trend.
**Result:** Reproduces the Phase-1 artifacts exactly: 55 rows, 0 mismatches, refusals-included denominators included.
**Decision:** keep
**Output:** results/E3_3_aim1_confirmatory.csv

### E3.3 — 2026-08-25
**Method:** A1.5: the E1.4 who-is-unrecognized logistic models A/B/C per organ, refitted and asserted against E1_4_models.csv term by term.
**Result:** 46 terms reproduce (odds ratio within 0.0015, p within 1e-6). Kidney Insulin-vs-Healthy model C OR 0.078; heart model C OR 0.588 p=0.137.
**Decision:** keep
**Output:** results/E3_3_aim1_recognition_models.csv

### E3.3 — 2026-08-25
**Method:** Every A1 trend refitted within each clinical site (direction check; per-site significance recorded).
**Result:** population_burden/either: UW z=5.577, UAB z=4.571, UCSD z=3.663; population_burden/heart: UW z=5.595, UAB z=4.108, UCSD z=2.648; population_burden/kidney: UW z=2.805, UAB z=3.299, UCSD z=2.566; prevalence/any: UW z=8.189, UAB z=6.414, UCSD z=3.904; prevalence/heart: UW z=7.642, UAB z=6.747, UCSD z=4.397; prevalence/kidney: UW z=5.132, UAB z=5.519, UCSD z=4.395; prevalence/nerve: UW z=4.979, UAB z=2.62, UCSD z=0.467; two_or_more_organs/multi: UW z=6.778, UAB z=6.02, UCSD z=3.87; unrecognized_fraction/either: UW z=-1.542, UAB z=-2.109, UCSD z=-0.976; unrecognized_fraction/heart: UW z=-1.088, UAB z=-1.514, UCSD z=-1.134; unrecognized_fraction/kidney: UW z=-2.567, UAB z=-2.967, UCSD z=-1.732
**Decision:** keep
**Output:** results/E3_3_aim1_by_site.csv

### E3.3 — 2026-08-25
**Method:** Percentile bootstrap (2000 resamples, seed 20260817) of every group-level unrecognized fraction and burden, beside the Wilson interval; small-cell rule < 50.
**Result:** unrecognized_fraction/kidney/Healthy: 88.9% Wilson 78.8-94.5 boot 81.0-95.2; unrecognized_fraction/kidney/Pre-DM: 71.4% Wilson 58.5-81.6 boot 58.9-82.1; unrecognized_fraction/kidney/Oral Med: 72.5% Wilson 63.9-79.7 boot 64.2-80.0; unrecognized_fraction/kidney/Insulin: 56.6% Wilson 45.4-67.1 boot 46.0-67.1; unrecognized_fraction/heart/Healthy: 74.2% Wilson 64.7-81.9 boot 66.0-82.5; unrecognized_fraction/heart/Pre-DM: 73.7% Wilson 62.8-82.3 boot 63.2-82.9; unrecognized_fraction/heart/Insulin: 62.6% Wilson 53.8-70.6 boot 53.7-70.7; unrecognized_fraction/either/Healthy: 84.9% Wilson 78.0-89.9 boot 79.1-90.6; unrecognized_fraction/either/Pre-DM: 76.3% Wilson 67.8-83.0 boot 68.6-83.9; unrecognized_fraction/either/Insulin: 69.9% Wilson 62.0-76.8 boot 62.2-76.9; population_burden/kidney/Pre-DM: 7.3% Wilson 5.4-9.8 boot 5.3-9.5; population_burden/kidney/Insulin: 17.4% Wilson 13.2-22.6 boot 12.6-22.3
**Decision:** keep
**Output:** results/E3_3_aim1_bootstrap.csv

### E3.3 — 2026-08-25
**Method:** Population burden re-run at every rung of the kidney and heart cutoff grids, pooled and by severity, including the either-organ burden.
**Result:** Either-organ burden spans 13.6-26.6% across the kidney grid and 14.5-57.9% across the heart grid; the rise with severity holds (z>0, p<0.05) at every rung: True; excluding the non-clinical 'detectable' rung: True.
**Decision:** keep
**Output:** results/E3_3_burden_sweep.csv

### E3.3 — 2026-08-25
**Method:** A2.1 per spec: CES-D-10 (per cohort-wide SD and >= 10) vs the five binary outcomes, covariates ['age', 'bmi', 'hba1c', 'C(study_group_label)', 'C(clinical_site)'], complete case, BH within the 10-model family; insensate sites as the supporting continuous outcome. Claim rule: q<0.05 in BOTH forms and same direction.
**Result:** Pre-specified criterion met for no outcome. cesd_total/abn_kidney 0.9155 (0.7983-1.0499) p=0.207 q=0.548; cesd_total/abn_heart 0.925 (0.8126-1.053) p=0.238 q=0.548; cesd_total/abn_nerve 1.1606 (1.0193-1.3214) p=0.0245 q=0.245; cesd_total/abn_any 0.9863 (0.8889-1.0942) p=0.794 q=0.882; cesd_total/abn_multi 0.96 (0.8167-1.1283) p=0.62 q=0.882; cesd_positive/abn_kidney 0.8292 (0.5927-1.1599) p=0.274 q=0.548; cesd_positive/abn_heart 0.8671 (0.6338-1.1863) p=0.373 q=0.621; cesd_positive/abn_nerve 1.3078 (0.9517-1.7973) p=0.098 q=0.49; cesd_positive/abn_any 0.9812 (0.7597-1.2674) p=0.885 q=0.885; cesd_positive/abn_multi 0.9457 (0.6431-1.3908) p=0.777 q=0.882
**Decision:** keep
**Output:** results/E3_3_aim2_confirmatory.csv

### E3.3 — 2026-08-25
**Method:** Adjustment ladder for CES-D (per cohort-wide SD) -> nerve on the Phase-2 sample and on the fixed spec complete-case sample, so a sample change is never shown as a covariate effect.
**Result:** [Phase-2 sample] unadjusted: OR 1.0783 (n=2265, p=0.19); [Phase-2 sample] + age: OR 1.2615 (n=2265, p=0.000146); [Phase-2 sample] + age + severity: OR 1.2211 (n=2265, p=0.00138); [Phase-2 sample] + age + severity + site: OR 1.2175 (n=2265, p=0.00168); [Phase-2 sample] + age + severity + site + HbA1c: OR 1.1852 (n=2200, p=0.00974); [Phase-2 sample] + age + severity + site + BMI: OR 1.1928 (n=2262, p=0.00525); [Phase-2 sample] full spec (+ BMI + HbA1c): OR 1.1606 (n=2197, p=0.0245); [fixed spec complete-case sample] unadjusted: OR 1.0561 (n=2197, p=0.366); [fixed spec complete-case sample] + age: OR 1.24 (n=2197, p=0.000777); [fixed spec complete-case sample] + age + severity: OR 1.1978 (n=2197, p=0.00579); [fixed spec complete-case sample] + age + severity + site: OR 1.1935 (n=2197, p=0.00705); [fixed spec complete-case sample] + age + severity + site + HbA1c: OR 1.1842 (n=2197, p=0.0102); [fixed spec complete-case sample] + age + severity + site + BMI: OR 1.1673 (n=2197, p=0.0192); [fixed spec complete-case sample] full spec (+ BMI + HbA1c): OR 1.1606 (n=2197, p=0.0245)
**Decision:** keep
**Output:** results/E3_3_aim2_ladder.csv

### E3.3 — 2026-08-25
**Method:** A2.2 robustness with CES-D on the cohort-wide SD in every row: within site, nerve cutoff >= 1 and >= 3, exclusion of the odd monofilament rows, PAID-5 head-to-head on one sample.
**Result:** EVERY ROW, FAILURES INCLUDED: within site [UW] cesd_total->abn_nerve: 1.0923 p=0.5; within site [UAB] cesd_total->abn_nerve: 1.1016 p=0.353; within site [UCSD] cesd_total->abn_nerve: 1.3301 p=0.0188; within site [UW] cesd_positive->abn_nerve: 1.184 p=0.577; within site [UAB] cesd_positive->abn_nerve: 1.1383 p=0.597; within site [UCSD] cesd_positive->abn_nerve: 1.8813 p=0.054; nerve cutoff [>= 1 insensate sites] cesd_total->abn_nerve: 1.0451 p=0.466; nerve cutoff [>= 1 insensate sites] cesd_positive->abn_nerve: 1.0127 p=0.933; nerve cutoff [>= 3 insensate sites] cesd_total->abn_nerve: 1.1806 p=0.0275; nerve cutoff [>= 3 insensate sites] cesd_positive->abn_nerve: 1.429 p=0.0501; drop odd monofilament rows [n dropped = 20] cesd_total->abn_nerve: 1.1405 p=0.0538; drop odd monofilament rows [n dropped = 20] cesd_positive->abn_nerve: 1.2761 p=0.143; PAID-5 head-to-head (identical sample) [alone] cesd_total->abn_nerve: 1.1527 p=0.0342; PAID-5 head-to-head (identical sample) [mutually adjusted for PAID-5] cesd_total->abn_nerve: 1.1915 p=0.0152; PAID-5 head-to-head (identical sample) [alone] paid_total->abn_nerve: 0.9726 p=0.696; PAID-5 head-to-head (identical sample) [mutually adjusted for CES-D-10] paid_total->abn_nerve: 0.9102 p=0.223
**Decision:** keep
**Output:** results/E3_3_aim2_robustness.csv

### E3.3 — 2026-08-25
**Method:** A2.2(e) CES-D (per cohort-wide SD) -> nerve within each severity group, spec covariates minus severity, bootstrap where the smaller cell < 50.
**Result:** Healthy: OR 1.1322 (0.8593-1.4918), n=756; Pre-DM: OR 1.1722 (0.8864-1.5503), n=543; Oral Med: OR 1.1745 (0.9349-1.4755), n=657; Insulin: OR 1.1839 (0.8858-1.5824), n=241
**Decision:** keep
**Output:** results/E3_3_aim2_by_severity.csv

### E3.3 — 2026-08-25
**Method:** A2.4 missing-data sensitivity: the 10-model family refitted on all 2,265 with missing BMI / HbA1c single-imputed at the severity-group median. Cannot change the verdict; qualifies the description of the attenuation.
**Result:** Nerve OR 1.188 (1.0497-1.3445), p=0.00638, q=0.0638; >=10 OR 1.3933, p=0.0327, q=0.163. Criterion met: False.
**Decision:** keep
**Output:** results/E3_3_aim2_missing_sensitivity.csv

### E3.3 — 2026-08-25
**Method:** A2.3 H3 per spec: CES-D-10 vs unrecognized status among the abnormal, recognition covariates incl. log marker magnitude, BH within 6 — the E2C.2 model unchanged.
**Result:** 0 of 6 survive FDR; estimates: cesd_total/unrec_kidney 0.9299 q=0.66; cesd_positive/unrec_kidney 0.7141 q=0.45; cesd_total/unrec_heart 0.7608 q=0.13; cesd_positive/unrec_heart 0.6041 q=0.17; cesd_total/unrec_either 0.8321 q=0.17; cesd_positive/unrec_either 0.7158 q=0.31
**Decision:** keep
**Output:** results/E3_3_h3.csv

### E3.3 — 2026-08-25
**Method:** T1 per spec: no-diabetes-label with HbA1c >= 6.5% (and CGM mean >= 154 mg/dL) vs each outcome within Healthy + Pre-DM, age + site adjusted, Wald and percentile-bootstrap (2000, seed 20260817) intervals, BH within 10; the E2A.2 models, family narrowed from 15, Phase-2 q alongside.
**Result:** Primary: kidney OR 4.1071 (Wald 2.0606-8.186; bootstrap 1.8291-8.5079), q=0.000596 (Phase-2 q 0.000893), 13/46 exposed abnormal (28.3% vs 8.7%). CGM replication OR 2.9178 q=0.014. Double-unrecognized: 16 of 19 (of 46 undiagnosed-range participants).
**Decision:** keep
**Output:** results/E3_3_track_undiagnosed.csv

### E3.3 — 2026-08-25
**Method:** T1 robustness with bootstrap on every small-cell row: within site (age-adjusted), ACR cutoff 20/30/50, HbA1c >= 7.0% as a threshold shift.
**Result:** within site [UW] abn_kidney: OR 3.1625 (Wald 1.1418-8.7593; boot 0.7448-8.5738; exposed 23, events 6) p=0.0268; within site [UAB] abn_kidney: OR 5.6363 (Wald 1.789-17.7579; boot 1.3333-17.8413; exposed 16, events 5) p=0.00314; within site [UCSD] abn_kidney: OR 3.9323 (Wald 0.7273-21.2595; boot 0.0-27.3499; exposed 7, events 2) p=0.112; kidney cutoff [ACR >= 20 mg/g] abn_kidney: OR 3.4251 (Wald 1.8194-6.4478; boot 1.729-6.6469; exposed 46, events 17) p=0.000137; kidney cutoff [ACR >= 30 mg/g] abn_kidney: OR 4.1071 (Wald 2.0606-8.186; boot 1.8291-8.5079; exposed 46, events 13) p=5.96e-05; kidney cutoff [ACR >= 50 mg/g] abn_kidney: OR 3.5804 (Wald 1.5203-8.4322; boot 1.0791-8.1232; exposed 46, events 7) p=0.00352; HbA1c threshold shift [HbA1c >= 7.0% vs all below (6.5-6.9 joins the reference)] abn_kidney: OR 6.0408 (Wald 2.2723-16.0591; boot 1.7242-19.0621; exposed 19, events 7) p=0.000312; HbA1c threshold shift [HbA1c >= 7.0% vs all below (6.5-6.9 joins the reference)] abn_any: OR 4.5811 (Wald 1.7201-12.2004; boot 1.5607-14.0735; exposed 19, events 11) p=0.00232
**Decision:** keep
**Output:** results/E3_3_track_undiagnosed_robustness.csv

### E3.3 — 2026-08-25
**Method:** Kidney damage prevalence by HbA1c band within Healthy + Pre-DM, so the 7.0% 'threshold shift' is read as a gradient rather than a stricter confirmation.
**Result:** < 6.5%: 109/1259 = 8.7% (7.2-10.3); 6.5-6.9%: 6/27 = 22.2% (10.6-40.8); >= 7.0%: 7/19 = 36.8% (19.1-59.0)
**Decision:** keep
**Output:** results/E3_3_track_undiagnosed_bands.csv

### E3.3 — 2026-08-25
**Method:** T2 per spec: ECG numeric metrics vs abnormal troponin and log troponin, age + severity + site, BH within 10 — the E2E.2 models, family narrowed from 40, Phase-2 q alongside. Supplement only.
**Result:** rate_bpm/abn_heart 1.2058 q=0.0031; rate_bpm/log_troponin 0.0464 q=6.8e-05; pr_ms/abn_heart 1.1554 q=0.014; pr_ms/log_troponin 0.0328 q=0.0031; qrsd_ms/abn_heart 1.4358 q=5.7e-11; qrsd_ms/log_troponin 0.1078 q=5e-24; qt_ms/abn_heart 1.0279 q=0.71; qt_ms/log_troponin 0.0004 q=0.97; qtc_ms/abn_heart 1.2042 q=0.0016; qtc_ms/log_troponin 0.0438 q=6.8e-05
**Decision:** keep
**Output:** results/E3_3_track_ecg.csv

### E3.3 — 2026-08-25
**Method:** T2 within each site for QRS duration and QTc.
**Result:** qrsd_ms/abn_heart@UW 1.7411 p=3e-08; qrsd_ms/abn_heart@UAB 1.2821 p=0.0057; qrsd_ms/abn_heart@UCSD 1.3638 p=0.00064; qrsd_ms/log_troponin@UW 0.1268 p=3.5e-15; qrsd_ms/log_troponin@UAB 0.0928 p=8.3e-07; qrsd_ms/log_troponin@UCSD 0.1033 p=8.2e-08; qtc_ms/abn_heart@UW 1.3347 p=0.0039; qtc_ms/abn_heart@UAB 1.1536 p=0.12; qtc_ms/abn_heart@UCSD 1.1508 p=0.15; qtc_ms/log_troponin@UW 0.0505 p=0.0016; qtc_ms/log_troponin@UAB 0.0374 p=0.047; qtc_ms/log_troponin@UCSD 0.0447 p=0.022
**Decision:** keep
**Output:** results/E3_3_track_ecg_by_site.csv

### E3.3 — 2026-08-25
**Method:** Site direction check with Cochran's Q and I2 for the model-based headline rows (A2.1 both forms, T1 primary, T2 QRS and QTc).
**Result:** A2.1 CES-D per SD -> nerve: 3/3 same direction, 1 sites p<0.05, Q p=0.42, I2=0.0%; A2.1 CES-D >= 10 -> nerve: 3/3 same direction, 0 sites p<0.05, Q p=0.44, I2=0.0%; T1 undiagnosed-range -> kidney: 3/3 same direction, 2 sites p<0.05, Q p=0.76, I2=0.0%; T2 qrsd_ms -> abn_heart: 3/3 same direction, 3 sites p<0.05, Q p=0.06, I2=64.4%; T2 qrsd_ms -> log_troponin: 3/3 same direction, 3 sites p<0.05, Q p=0.35, I2=4.8%; T2 qtc_ms -> abn_heart: 3/3 same direction, 1 sites p<0.05, Q p=0.47, I2=0.0%; T2 qtc_ms -> log_troponin: 3/3 same direction, 3 sites p<0.05, Q p=0.87, I2=0.0%
**Decision:** keep
**Output:** results/E3_3_site_heterogeneity.csv

### E3.3 — 2026-08-25
**Method:** Figure: either-organ burden by severity within each site.
**Result:** Figure written.
**Decision:** keep
**Output:** results/E3_3_site_replication_figure.png

### E3.3 — 2026-08-25
**Method:** Figure: Aim 2 confirmatory forest per spec.
**Result:** Figure written.
**Decision:** keep
**Output:** results/E3_3_aim2_figure.png

### E3.3 — 2026-08-25
**Method:** Figure: burden across the cutoff grids.
**Result:** Figure written.
**Decision:** keep
**Output:** results/E3_3_burden_sweep_figure.png

### E3.FREEZE — 2026-08-25
**Method:** Results freeze, second entry, superseding the first E3.FREEZE above. Everything in the headline set was rerun against PRESPEC.md as amended (sha256 c9f2acb6cc294205c64b4dcbaa58c1ac5b5e5e431a583764c7d0c5a52f409deb) in the early hours of 25 Aug; nothing enters the paper after this entry except via a logged deviation. The freeze deadline in the plan is 26 Aug; Evan's sign-off on PRESPEC.md (incl. Amendment 1) is pending.
**Result:** FROZEN. Headline numbers: any-organ prevalence 34.6%; either-organ unrecognized fraction 76.6%; either-organ burden 21.3% overall, 40.7% on insulin; Aim 2: pre-specified criterion NOT met (nerve OR 1.1606 per SD, q=0.245); T1 kidney OR 4.1071 (bootstrap 1.8291-8.5079).
**Decision:** keep — frozen 2026-08-25; deadline 26 Aug; Evan's sign-off pending, amendments logged as E3.2.AMEND.n
**Output:** none

### E4.1 — 2026-08-25
**Method:** Table 1 built from the master participant table: age, site, BMI, HbA1c, CGM glucose, CES-D-10, PAID-5, comorbidity count, each organ's marker distribution, abnormality prevalence, self-report and unrecognized burden, by severity group; mean (SD) / median [IQR] / n (%), Kruskal-Wallis or chi-square across groups, n missing per variable.
**Result:** 28 rows. Age 60.9 (11.2); any organ abnormal 767 (34.6%); either-organ unrecognized burden 471 (21.3%) overall, 100 (40.7%) on insulin.
**Decision:** keep
**Output:** results/E4_1_table1.csv

### E4.2 — 2026-08-25
**Method:** Figure 1: panel A the population burden of unrecognized kidney / heart / either-organ damage per 100 evaluable participants by severity group (primary, per E2.DECIDE); panel B the conditional unrecognized fraction among the abnormal (mechanism). Wilson 95% CIs. Drawn from the E1.2 artifacts that E3.3 reproduced exactly; PNG 300 dpi, PDF and SVG written alongside.
**Result:** Either-organ burden 15.5% -> 40.7% across severity (z=8.15); either-organ fraction 84.9% -> 69.9% (z=-2.85).
**Decision:** keep
**Output:** results/E4_2_figure1.png

### E4.3 — 2026-08-25
**Method:** Figure 2: panel A the distribution of abnormal-organ counts (0-3) by severity group, stacked; panel B every observed combination of kidney / heart / nerve damage. From the E1.3 artifacts; PNG 300 dpi, PDF and SVG written alongside.
**Result:** Two or more organs: 5.9% Healthy -> 31.1% Insulin; most common single organ: heart (204); all three in 49.
**Decision:** keep
**Output:** results/E4_3_figure2.png

### E4.4 — 2026-08-25
**Method:** Table 2 assembled from frozen E3.3 artifacts, nothing refitted: block A the E1.4 who-is-unrecognized models (A1.5), block B the ten pre-specified Aim-2 models with the Phase-2 exploratory estimate alongside, block C the T1 undiagnosed-range models with Wald and bootstrap intervals. Provenance recorded per row.
**Result:** 54 rows. Aim 2 nerve OR 1.1606 (1.0193-1.3214), q=0.245 — criterion not met; T1 kidney OR 4.1071 (bootstrap 1.8291-8.5079), q=0.000596.
**Decision:** keep
**Output:** results/E4_4_table2.csv

### E4.4 — 2026-08-25
**Method:** Supplement S1: within-site direction check for every core trend, plus Cochran's Q / I² for the model-based rows.
**Result:** 33 site rows, all same direction as pooled; 7 model rows.
**Decision:** keep
**Output:** results/E4_4_S1_site_direction.csv

### E4.4 — 2026-08-25
**Method:** Supplement S2: prevalence, unrecognized fraction and burden at every rung of both cutoff grids (E1.5 + E3.3 burden sweep).
**Result:** 27 rows across kidney, heart and either-organ grids.
**Decision:** keep
**Output:** results/E4_4_S2_cutoff_sweeps.csv

### E4.4 — 2026-08-25
**Method:** Supplement S3: one row per experiment from the RESULTS_LOG status table, with adjusted-model and FDR-survivor counts and the label each carries in the paper.
**Result:** 27 experiments; Phase-2 primary families total 207 adjusted models with 79 FDR survivors.
**Decision:** keep
**Output:** results/E4_4_S3_experiment_log.csv

### E4.4 — 2026-08-25
**Method:** Supplement S4: T2 ECG numeric models plus the single UNADJUDICATED machine-read infarct row.
**Result:** 10 numeric rows + 4 unadjudicated row(s).
**Decision:** keep
**Output:** results/E4_4_S4_ecg.csv

### E4.4 — 2026-08-25
**Method:** Supplement S5: the E2.AGE sign test and per-pair correlations behind the Methods sentence on age as a negative confounder.
**Result:** 47 rows.
**Decision:** keep
**Output:** results/E4_4_S5_age_confounding.csv

### E4.2 — 2026-08-25
**Method:** Figure 1: panel A the population burden of unrecognized kidney / heart / either-organ damage per 100 evaluable participants by severity group (primary, per E2.DECIDE); panel B the conditional unrecognized fraction among the abnormal (mechanism). Wilson 95% CIs. Drawn from the E1.2 artifacts that E3.3 reproduced exactly; PNG 300 dpi, PDF and SVG written alongside.
**Result:** Either-organ burden 15.5% -> 40.7% across severity (z=8.15); either-organ fraction 84.9% -> 69.9% (z=-2.85).
**Decision:** keep — re-rendered once after a visual check (labels moved off the interval caps; panel B labels at the endpoints only)
**Output:** results/E4_2_figure1.png

### E4.3 — 2026-08-25
**Method:** Figure 2: panel A the distribution of abnormal-organ counts (0-3) by severity group, stacked; panel B every observed combination of kidney / heart / nerve damage. From the E1.3 artifacts; PNG 300 dpi, PDF and SVG written alongside.
**Result:** Two or more organs: 5.9% Healthy -> 31.1% Insulin; most common single organ: heart (204); all three in 49.
**Decision:** keep — re-rendered once after a visual check (group n moved into the tick labels, off the title)
**Output:** results/E4_3_figure2.png

### E4.2 — 2026-08-25
**Method:** Figure 1: panel A the population burden of unrecognized kidney / heart / either-organ damage per 100 evaluable participants by severity group (primary, per E2.DECIDE); panel B the conditional unrecognized fraction among the abnormal (mechanism). Wilson 95% CIs. Drawn from the E1.2 artifacts that E3.3 reproduced exactly; PNG 300 dpi, PDF and SVG written alongside.
**Result:** Either-organ burden 15.5% -> 40.7% across severity (z=8.15); either-organ fraction 84.9% -> 69.9% (z=-2.85).
**Decision:** keep — re-rendered after visual checks (labels off the interval caps; panel B endpoint labels with per-organ offsets; headroom for the Insulin label)
**Output:** results/E4_2_figure1.png

### E4.4 — 2026-08-25
**Method:** Table 2 assembled from frozen E3.3 artifacts, nothing refitted: block A the E1.4 who-is-unrecognized models (A1.5), block B the ten pre-specified Aim-2 models with the Phase-2 exploratory estimate alongside, block C the T1 undiagnosed-range models with Wald and bootstrap intervals. Provenance recorded per row.
**Result:** 54 rows. Aim 2 nerve OR 1.1606 (1.0193-1.3214), q=0.245 — criterion not met; T1 kidney OR 4.1071 (bootstrap 1.8291-8.5079), q=0.000596.
**Decision:** keep
**Output:** results/E4_4_table2.csv

### E4.4 — 2026-08-25
**Method:** Supplement S1: within-site direction check for every core trend, plus Cochran's Q / I² for the model-based rows.
**Result:** 33 site rows, all same direction as pooled; 7 model rows.
**Decision:** keep
**Output:** results/E4_4_S1_site_direction.csv

### E4.4 — 2026-08-25
**Method:** Supplement S2: prevalence, unrecognized fraction and burden at every rung of both cutoff grids (E1.5 + E3.3 burden sweep).
**Result:** 27 rows across kidney, heart and either-organ grids.
**Decision:** keep
**Output:** results/E4_4_S2_cutoff_sweeps.csv

### E4.4 — 2026-08-25
**Method:** Supplement S3: one row per experiment from the RESULTS_LOG status table, with adjusted-model and FDR-survivor counts and the label each carries in the paper.
**Result:** 27 experiments; Phase-2 primary families total 207 adjusted models with 79 FDR survivors.
**Decision:** keep
**Output:** results/E4_4_S3_experiment_log.csv

### E4.4 — 2026-08-25
**Method:** Supplement S4: T2 ECG numeric models plus the single UNADJUDICATED machine-read infarct row.
**Result:** 10 numeric rows + 4 unadjudicated row(s).
**Decision:** keep
**Output:** results/E4_4_S4_ecg.csv

### E4.4 — 2026-08-25
**Method:** Supplement S5: the E2.AGE sign test and per-pair correlations behind the Methods sentence on age as a negative confounder.
**Result:** 47 rows.
**Decision:** keep
**Output:** results/E4_4_S5_age_confounding.csv
