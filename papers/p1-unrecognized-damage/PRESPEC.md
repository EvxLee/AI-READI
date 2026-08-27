# Paper 1 — Pre-specified analysis plan (PRESPEC)

**Written and dated 2026-08-25 at `E3.2`, after Phases 0–2. Frozen on this date;
SHA-256 of this file is recorded in `RESULTS_LOG.md` at `E3.2` so any later
edit is detectable. Results-freeze deadline 2026-08-26.**

> **Amendment 1 — 2026-08-25, logged as `E3.2.AMEND.1`.** One amendment,
> made the same night after an adversarial review of this document and of
> the first `E3.3` run, *before* Evan's sign-off. It changes no analysis
> parameter in §10 — every cutoff, covariate set, family size, seed and grid
> is byte-identical — and adds: an explicit missing-data rule with a
> sensitivity analysis (§4.2), the claim-rule reading the runner applies
> (§4.2), the correct chronology of how this document was drafted
> (Provenance), a fuller statement of what "fixed at `E1.0`" does and does not
> mean (Provenance), honest labels for the per-site check (§5) and for the
> T1 / T2 / H3 reruns (§4.3–4.5), the A1.5 and both-denominator reruns that
> §4.1 promised but the first run omitted, and the wording fixes the review
> listed. The pre-amendment hash was `c6bbb2ec2505e9ba0a769b49fba7075344f65a0a31914a1794632013d9190806`; the post-amendment hash is in the
> `E3.2.AMEND.1` log entry.

> **Provenance disclosure.** This document is dated *after* the exploratory
> phases (0–2) ran, and the paper's Methods must say so plainly. Phases 0–2
> were exploratory by design (two-stage pre-specification, `PLAN.md` Part I,
> item 1); every run they produced — nulls included — is in `RESULTS_LOG.md`.
> The abnormality cutoffs and the unrecognized-fraction denominator were fixed
> and written down at `E1.0` *before any counting*, which is the part of a
> pre-specification that matters most for a descriptive paper. What this
> document adds is the choice of the headline set, the exact model forms and
> covariates for the two inferential aims, the multiplicity rule, and the
> robustness programme — chosen from the `E3.1` ranking table rather than from
> memory. The defence against the cherry-picking critique is the *complete
> log*, not a prospective spec: the claim is "nothing was hidden", not
> "nothing was explored".
>
> **What "fixed at `E1.0`" does and does not mean.** The three cutoffs were
> written down at `E1.0` (11 Aug) before the Phase-1 sweep ran, and were
> swept at `E1.5`. They were not chosen blind: the kidney spot-check at
> ACR ≥ 30 mg/g predates Phase 0 (`PLAN.md`, `E0.4`), the kidney and heart
> cutoffs are external guideline values, and the nerve cutoff — the one
> judgement call — was confirmed at `E1.DECIDE` (12 Aug) with the `E1.5`
> prevalence-at-each-rung numbers in view. The paper says exactly this.
>
> **Chronology of this document.** It was drafted at 01:13 on 25 Aug from
> the *first* `E3.1` run. An adversarial review then found five bookkeeping
> defects in that run (`E3.1.RUN1`); the corrected rerun at 01:28 changed the
> all-four tier by one row and changed nothing in the headline set chosen
> here. The document was confirmed against the corrected table, not
> rewritten from it.
>
> **Authorship of this freeze.** The headline set was chosen overnight on
> 25 Aug 2026 by Claude Code under Evan's delegated authority, from the
> position `E2.CLOSE` and `E2.OPEN` recommended, with the alternatives recorded
> in §9. Evan's sign-off on the morning of 26 Aug either confirms it or issues
> an amendment logged as `E3.2.AMEND` before the freeze. Nothing in this file
> is edited silently afterwards; a deviation is a new log entry with a reason.

---

## 1. Objective

One paper, two aims, one participant table.

- **Aim 1 (primary, descriptive):** how much detectable kidney, heart and
  nerve damage is present across the type 2 diabetes severity spectrum, and —
  for kidney and heart — how much of it the participant reported never having
  been told about. Framing decided at `E2.DECIDE`: the **population burden**
  (share of all evaluable participants carrying unrecognized damage) leads;
  the **falling conditional fraction** follows as the mechanism.
- **Aim 2 (secondary, inferential):** whether depressive symptoms (CES-D-10)
  are associated with *measured* damage after adjustment. Reported in one
  clearly labelled paragraph whatever the result.

Everything else in the paper is exploratory and labelled as such (§6).

## 2. Data

- AI-READI **v3.0.0**, study `1438dd73-c4cb-48b8-8fa8-c858771207c3`,
  container `aireadi-container`. N = 2,280: Healthy 776, Pre-DM 560,
  Oral Med 686, Insulin 258 (`constants.EXPECTED_GROUP_N`, asserted by
  `cohort.qc_report`). No newer release is adopted mid-paper.
- Participant table: `cohort.build_p1_table()` cached as
  `data/processed/p1/master_table.parquet` (gitignored), flags applied by
  `thresholds.add_damage_flags`, Phase-2 outcome columns by
  `associations.add_outcome_columns`. Derived exposures used by the headline
  set are attached by `scripts/_phase3.load_full()` exactly as their Phase-2
  runners built them.
- Every cleaning rule in `docs/CAVEATS.md` applies through the shared
  toolbox; none is re-implemented in a runner.

## 3. Definitions (frozen)

| Term | Definition | Fixed at |
|---|---|---|
| Kidney abnormal | urine ACR ≥ 30 mg/g (`import_urine_albumin` / `import_urine_creatinine` × 1000); creatinine 0 → not evaluable | `E1.0` |
| Heart abnormal | hs-cTnT ≥ 14 ng/L (`import_troponin_t`); below-detection rows (operator 4171756) are *not* abnormal | `E1.0` |
| Nerve abnormal | ≥ 2 insensate sites of 10 on the **worse** foot (`monofilament_min` ≤ 8) | `E1.0`, confirmed `E1.DECIDE` |
| Self-report comparator | kidney: `mhoccur_rnl`; heart: `mhoccur_mi` OR `mhoccur_cvdot`; nerve: **none exists** in v3.0.0 | `E0.2`, `E0.GATE` |
| Unrecognized (per organ) | abnormal AND self-report = 0, among abnormal with the item answered (777 refusals excluded, never recoded to "no"); the refusals-included denominator is reported beside it | `E1.0` |
| Unrecognized, either organ | abnormal on kidney or heart, among participants with **both** markers measured and **both** items answered (`thresholds.either_organ`) | `E1.FIG` |
| Population burden | abnormal AND unrecognized, per 100 *evaluable* participants (measured + item answered) | `E1.2` |
| Multi-organ count | number of abnormal organs among participants measured on all three | `E1.3` |
| Any organ | ≥ 1 abnormal among participants measured on all three | `E1.1` |
| Severity | `study_group_label`, ordered Healthy < Pre-DM < Oral Med < Insulin | `E0.4` |
| Default covariates | age + severity group + site (`associations.ADJUSTMENTS["damage"]`) | `CLAUDE.md` |
| Recognition covariates | default + HbA1c + BMI + log marker magnitude (+ age already present) | `E1.4` re-reading |
| Log ACR | urine albumin of exactly 0 substituted at half the 0.01 mg/dL reporting floor | `E2.DEFECTS` |

Nerve carries **no** unrecognized fraction; the broad `mhoccur_cns` /
`mhoccur_circ` items are not used in any analysis, not even as a sensitivity
check (`E0.GATE`).

## 4. The headline set

### 4.1 Aim 1 — confirmatory reruns of the core sweep (`A1.1`–`A1.5`)

Descriptive and pre-specified at `E1.0`; rerun per this spec at `E3.3` and
required to reproduce the Phase-1 artifacts exactly.

| ID | Analysis | Statistic | Reported |
|---|---|---|---|
| A1.1 | Prevalence of abnormal result per organ and any organ, overall and by severity | Wilson 95% CI; Cochran-Armitage trend, scores 0–3 | main text, Table 1 / Figure 1 |
| A1.2 | Unrecognized fraction, kidney / heart / either, overall and by severity, both denominators (refusals excluded; refusals included, reported alongside at `E3.3`) | Wilson 95% CI; Cochran-Armitage trend | main text, Figure 1 |
| A1.3 | Population burden, kidney / heart / either, by severity | Wilson 95% CI; Cochran-Armitage trend | **abstract lead**, Figure 1 |
| A1.4 | Multi-organ counts and overlap; unrecognized-organ counts | proportions; trend on ≥ 2 organs | Figure 2 |
| A1.5 | Who is unrecognized: logistic models A / B / C as in `E1.4`, refitted at `E3.3` and required to reproduce `E1_4_models.csv` | OR, 95% CI | Table 2 (kidney established, heart suggestive — `E1.4` re-reading) |

**Multiplicity:** none. These are descriptive, pre-specified, and reported in
full with intervals; the trend tests are one per pre-declared claim.

### 4.2 Aim 2 — CES-D-10 vs measured damage (`A2.1`–`A2.3`)

- **Exposures:** CES-D-10 total (`cestl`, 0–30, per cohort-wide SD) and
  screen-positive (≥ 10). Both are reported for every outcome; neither is
  chosen after the fact.
- **Primary outcomes (family of 10 models):** kidney, heart, nerve, any-organ,
  ≥ 2 organs abnormal — each binary outcome × each exposure form. Logistic
  regression.
- **Covariates:** age, BMI, HbA1c, severity group (the `PLAN.md` Part I
  item 4 set) plus site (the repo-wide default, `CLAUDE.md`). BMI and HbA1c
  are treated as confounders; a reader who regards them as mediators of a
  depression → nerve pathway will find the age + severity + site model in the
  adjustment ladder. *This differs from Phase 2,* which used
  age + severity + site (+ HbA1c in a second family) and not BMI. Adding BMI
  here is the plan's original specification and is the one way in which the
  confirmatory model is not a copy of the exploratory one; the Phase-2 result
  must survive it to be claimed.
- **Multiplicity and the claim rule:** Benjamini-Hochberg within the
  10-model family. A finding is claimed only if **both** exposure forms — the
  per-SD score *and* the ≥ 10 screen — reach q < 0.05 **and** agree in
  direction. (Amendment 1: the original sentence could be read as "q < 0.05
  in the primary form plus directional agreement"; the runner has always
  applied the both-forms reading, and this is it. Requiring the dichotomised
  form costs power and was chosen so that a threshold effect and a
  dose-response are claimed together or not at all.)
- **Missing data (Amendment 1):** complete-case within each model, as
  executed — a participant enters a model only with every covariate present.
  The spec covariates lose 68 of the 2,265 participants with CES-D and a
  nerve exam (65 lack HbA1c, 3 lack BMI), and those 68 are not missing at
  random with respect to the outcome. Sensitivity (`A2.4`): the 10-model
  family refitted on all 2,265 with missing BMI / HbA1c single-imputed at the
  severity-group median. Reported beside the complete-case result; it cannot
  change the verdict, only qualify the description of the attenuation. No
  multiple-imputation analysis aimed at the verdict will be run.
- **Supporting continuous outcome:** insensate sites on the worse foot (0–10),
  linear regression, same covariates; reported beside the binary result, not
  in the corrected family.
- **Expectation carried from Phase 2 (`E2C.1`; not a pre-registration):**
  the association is nerve-specific. If it holds, the paper reports an *association* with both
  causal directions named and neither preferred (`E2.OPEN` 1); no directional
  verb.
- **Robustness (`A2.2`), all reported, every failure included:** (a) within
  each site, with Cochran's Q / I²; (b) nerve cutoff at ≥ 1 and ≥ 3 insensate
  sites; (c) exclusion of the 20 clinically odd monofilament rows (both feet
  0; one foot 0 and the other 10); (d) PAID-5 mutual adjustment on the
  identical complete-case sample; (e) within each severity group, bootstrap
  interval where the smaller outcome cell < 50. CES-D is scaled by the
  **cohort-wide** SD in every row, including the within-group and
  restricted-sample rows (Amendment 1). The adjustment ladder is reported on
  the fixed spec complete-case sample as well as on the Phase-2 sample, so a
  sample change is never presented as a covariate effect.
- **H3 (`A2.3`, exploratory, reported once):** CES-D-10 vs unrecognized
  status among the abnormal (kidney, heart, either), recognition covariates
  (§3, which include log marker magnitude), BH within its 6-model family.
  This is the `E2C.2` model unchanged; the rerun reproduces it. Phase 2 found it null
  with every estimate below 1; it is rerun per spec and reported in one
  sentence whatever it shows.

### 4.3 Promoted track finding — unrecognized diabetes beneath unrecognized damage (`T1`)

Selected from `E3.1` as the one Phase-2 finding that is large, adjusted,
site-consistent and directly about Aim 1's subject. Labelled
**exploratory-confirmatory** in the paper: found in Phase 2, rerun per this
spec, but not a pre-declared hypothesis. **What the rerun adds and does not
add (Amendment 1):** the model and covariates are those of `E2A.2` exactly, so
the point estimates and p-values reproduce Phase 2; the FDR family is
narrowed from 15 (which included the null insulin-at-target rows) to the 10
models named here, which moves q but not p. The paper reports the Phase-2 q
beside the spec q. What is new is the robustness programme below.

- **Exposure:** no diabetes label (Healthy or Pre-DM group) with HbA1c ≥ 6.5%
  (ADA diagnostic threshold), yes/no, within the Healthy + Pre-DM universe.
- **Primary outcome:** kidney abnormal. **Secondary:** heart, nerve, any,
  ≥ 2 organs.
- **Model:** logistic, age + site (severity is excluded because the exposure
  is defined relative to it). Wald **and** percentile-bootstrap 95% CI
  (2,000 resamples, seed 20260817), both reported because the exposed cell is
  under 50.
- **Multiplicity:** BH across the 10 models (5 outcomes × the HbA1c and CGM
  definitions).
- **Replication by an independent definition:** CGM mean glucose ≥ 154 mg/dL
  (GMI ≡ HbA1c 7.0%) in place of HbA1c.
- **The count the paper quotes:** among exposed participants abnormal on
  kidney or heart with both self-report items answered, the number who
  reported no corresponding diagnosis.
- **Robustness:** within each site, with Cochran's Q / I²; kidney cutoff at
  ACR 20 and 50 mg/g; HbA1c ≥ 7.0% as a *threshold shift* (the 6.5–6.9% band
  then joins the comparison group, so the three bands < 6.5 / 6.5–6.9 / ≥ 7.0
  are reported as counts, not only as an odds ratio). Every robustness row
  with an exposed cell under 50 carries a percentile-bootstrap interval
  beside the Wald interval (Amendment 1).

### 4.4 Supplementary corroboration — ECG numeric metrics vs the heart marker (`T2`)

Instrument measurements (rate, PR, QRS duration, QT, QTc from the manifest;
repeat ECGs deduplicated to the first record), **not** machine
interpretations, against abnormal troponin and log troponin, age + severity +
site, BH within the 10-model family, within each site. Supplement only; its
role is to corroborate that the troponin signal is cardiac (`E2.OPEN` 2). The
models are those of `E2E.2` exactly; the family is narrowed from 40 to the 10
heart-marker models, which moves q but not p (Amendment 1).

### 4.5 Stated negative — access barriers do not explain being unrecognized (`T3`)

Reported **from the Phase-2 artifact as exploratory, with its `E3.1`
per-site direction**, not rerun as confirmatory: healthcare access barriers
vs unrecognized heart damage runs opposite to the falling-through-the-cracks
hypothesis (OR < 1 pooled and in every site). One paragraph; interpretation
offered is treatment burden / reverse causation, stated as interpretation.

## 5. Robustness programme common to the headline set (`E3.3`)

| Check | Applies to | Rule |
|---|---|---|
| Per-site direction check | A1.1–A1.3 trends; A2.1; T1; T2 | same direction at UW, UAB and UCSD; per-site significance reported, not required (three sites of ~760 are under-powered individually). **This is a sanity check, not replication** — with three sites, sign agreement alone has roughly a one-in-four chance under the null. Cochran's Q and I² are reported for the model-based rows (Amendment 1). |
| Cutoff sweeps | A1.1–A1.3 | the `E1.5` grids: ACR 20/30/50/100/300; hs-cTnT detectable/10/14/16/19/22; insensate ≥ 1–5. Burden is now swept as well as prevalence and fraction. |
| Bootstrap intervals | any cell < 50: Insulin × abnormal × unrecognized; T1's exposed cell; within-group A2 | percentile bootstrap, 2,000 resamples, seed 20260817, reported beside the Wald / Wilson interval |
| Adjustment ladder | A2.1 | unadjusted → + age → + severity → + site → full, so the direction of change under adjustment is visible (`E2.AGE`) |

**Significance conventions.** Two-sided α = 0.05. Benjamini-Hochberg within
each declared family, never across families. Effect-size floors from `E3.1`
(per-SD OR ≥ 1.2; yes/no OR ≥ 1.5; standardised β ≥ 0.10 SD; ≥ 10-point
Healthy-to-Insulin spread) are the bar for "worth a sentence", not claims of
clinical importance. A p-value alone does not qualify a finding.

**Software.** Python 3.13.1, pandas 2.3.1, numpy 2.2.6, scipy 1.16.2,
statsmodels 0.14.6, matplotlib 3.10.7.

## 6. What is exploratory, and how it is labelled

| Finding | Where it appears | Label |
|---|---|---|
| BMI vs damage (`E2B.1`) | supplement S3 | exploratory; real but expected, and Paper 2's territory |
| Glycaemia vs damage (`E2A.1`) | one Results sentence: CGM CV adds to mean glucose for kidney, TAR and MAGE do not; full sweep in S3 | exploratory; expected biology |
| Wearables (`E2D.1`) | supplement S3 | exploratory; cross-sectional, direction uninterpretable |
| PAID-5 (`E2C.3`) | Aim 2 robustness (d) | exploratory null |
| Machine-read prior infarct (`E2E.1`) | **one supplementary row, labelled unadjudicated** at every appearance including the figure; never abstract, never main-text figure | `E2.OPEN` 2 |
| Age as a negative confounder (`E2.AGE`) | one Methods sentence; sign test and figure in supplement | `E2.OPEN` 3 |
| UCSD kidney-recognition site term (`E1.4`) | `E1_4_models.csv` only | dropped from the paper, `E2.DECIDE` 2 |
| Everything else in `RESULTS_LOG.md` | supplement S3, one line per experiment | exploratory |

## 7. Required Methods statements

Carried from `RESULTS_LOG.md` "Statements the Methods section must make":
(1) staged pre-specification, dated after the exploratory runs; (2) no
neuropathy self-report item exists in v3.0.0; (3) ECG interpretations are
machine-generated and physician-unreviewed; (4) the history survey precedes
the clinic tests by a median of 35 days (IQR 20–54; `E2_TIMING_survey_lag.csv`)
while the three tests are concurrent with one another; bias direction is
toward overstating unawareness. Plus (5) the `E2.AGE` sentence at the point
the covariate set is specified, and (6) "unrecognized abnormal findings that
warrant follow-up", never "undiagnosed disease".

## 8. Paper-ready outputs (Phase 4)

- **Table 1** — cohort characteristics by severity group (`E4.1`).
- **Figure 1** — population burden by organ × severity (primary panel) with the
  conditional unrecognized fraction beside it (mechanism panel) (`E4.2`).
- **Figure 2** — multi-organ overlap and organ-count distribution (`E4.3`).
- **Table 2** — Aim 2 confirmatory models and T1 (`E4.4`).
- **Supplement** — S1 per-site replication; S2 cutoff sweeps incl. burden;
  S3 one line per experiment from the full log; S4 ECG rows (T2, and the
  unadjudicated `E2E.1` row); S5 `E2.AGE` (`E4.4`).

## 9. Alternatives weighed at `E3.2` (recorded so any can be reopened)

1. **Promote glycaemia (`E2A.1`) as a headline track finding.** It tops the
   `E3.1` ranking by q, survives adjustment and replicates at every site. Set
   aside for the headline because "measured glycaemia tracks organ damage" is
   textbook, the paper is about *recognition*, and the plan caps promoted
   track findings at 1–3. Its one novel element — variability (CV) adds
   information beyond the mean; TAR and MAGE do not — gets a sentence.
2. **Promote the ECG numeric coherence (`E2E.2`) to the main text.** Set aside:
   it is corroboration of a marker, not a finding about people. Supplement.
3. **Treat the nerve–depression result as directional.** Set aside per
   `E2.OPEN` 1; the design cannot order exposure and outcome in time.
4. **Rerun the access-barrier negative as confirmatory.** Set aside: it is a
   single survivor of 18 models, reported as exploratory with its per-site
   direction; promoting a negative to confirmatory status would overstate it.
5. **Keep Phase 2's covariate set for Aim 2 (no BMI).** Set aside: the plan
   specified BMI in Aim 2's adjustment, and a confirmatory model that copies
   the exploratory one confirms nothing.
6. **Drop nerve from Aim 1's any-organ figure.** Set aside at `E1.DECIDE`;
   unchanged.

## 10. Machine-readable parameters

`scripts/_phase3.prespec()` parses this block; `E3.3` runs against it, so
the spec and the executed analysis cannot drift.

```json
{
  "prespec_version": "2026-08-25",
  "freeze_date": "2026-08-26",
  "dataset": {"release": "3.0.0", "n": 2280,
              "groups": {"Healthy": 776, "Pre-DM": 560, "Oral Med": 686, "Insulin": 258}},
  "cutoffs": {"acr_mg_g": 30.0, "troponin_ng_l": 14.0, "monofilament_missed": 2},
  "sweeps": {"acr_mg_g": [20.0, 30.0, 50.0, 100.0, 300.0],
             "troponin_ng_l": ["detectable", 10.0, 14.0, 16.0, 19.0, 22.0],
             "monofilament_missed": [1, 2, 3, 4, 5]},
  "self_report": {"kidney": ["mhoccur_rnl"], "heart": ["mhoccur_mi", "mhoccur_cvdot"], "nerve": []},
  "sites": ["UW", "UAB", "UCSD"],
  "alpha": 0.05,
  "bootstrap": {"n": 2000, "seed": 20260817, "small_cell": 50},
  "aim2": {
    "exposures": ["cesd_total", "cesd_positive"],
    "outcomes": ["abn_kidney", "abn_heart", "abn_nerve", "abn_any", "abn_multi"],
    "supporting_outcome": "monofilament_missed",
    "covariates": ["age", "bmi", "hba1c", "C(study_group_label)", "C(clinical_site)"],
    "fdr_family_size": 10,
    "claim_rule": "q < 0.05 and same direction in both exposure forms",
    "nerve_cutoff_sensitivity": [1, 3],
    "odd_row_exclusion": true,
    "paid5_mutual_adjustment": true,
    "h3_outcomes": ["unrec_kidney", "unrec_heart", "unrec_either"],
    "h3_covariates": ["age", "C(study_group_label)", "C(clinical_site)", "hba1c", "bmi"],
    "h3_marker": {"unrec_kidney": ["log_acr"], "unrec_heart": ["log_troponin"],
                  "unrec_either": ["log_acr", "log_troponin"]}
  },
  "track_undiagnosed": {
    "universe": ["Healthy", "Pre-DM"],
    "hba1c_cutoff": 6.5, "hba1c_sensitivity": 7.0, "cgm_mean_cutoff": 154.0,
    "primary_outcome": "abn_kidney",
    "outcomes": ["abn_kidney", "abn_heart", "abn_nerve", "abn_any", "abn_multi"],
    "covariates": ["age", "C(clinical_site)"],
    "fdr_family_size": 10,
    "acr_sweep": [20.0, 30.0, 50.0]
  },
  "track_ecg": {
    "metrics": ["rate_bpm", "pr_ms", "qrsd_ms", "qt_ms", "qtc_ms"],
    "outcomes": ["abn_heart", "log_troponin"],
    "covariates": ["age", "C(study_group_label)", "C(clinical_site)"],
    "fdr_family_size": 10
  },
  "effect_floors": {"or_per_sd": 1.2, "or_binary": 1.5, "beta_sd": 0.10, "trend_spread_points": 10.0}
}
```

*— end —*
