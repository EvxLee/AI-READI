# Paper 1 — Unrecognized kidney and heart damage in type 2 diabetes

**Working title:** *Unrecognized kidney and heart damage across the type 2
diabetes spectrum: a cross-sectional analysis of the AI-READI dataset*

**Lead:** Evan Lee · **Results freeze:** 26 August 2026 · **Submission:** mid-September 2026

Three inexpensive tests performed at one study visit — urine albumin (kidney),
high-sensitivity troponin (heart), and a monofilament exam (nerve) — compared
against what participants reported a doctor had ever told them. The three tests
are concurrent with one another; the self-report survey precedes the clinic
visit by a median of 35 days (`E2.TIMING`). The paper asks
how much detectable organ damage goes unrecognized across the diabetes severity
spectrum. Depressive symptoms (CES-D-10) are a secondary aim, labelled as such
throughout.

**Nerve is measured but not in the title.** v3.0.0 contains no neuropathy
self-report item, so the monofilament exam cannot carry an "unrecognized"
figure (`E0.GATE`, 11 Aug). It keeps measured prevalence, the multi-organ
count, and the depression aim; the title is scoped to the two organs that can
support the unrecognized claim (`E1.DECIDE`, 12 Aug). One Methods sentence and
one Limitations sentence state the gap.

## Where the paper stands

| Phase | Status |
|---|---|
| **Phase 0** — foundation, gate | ✅ done 11 Aug, independently re-audited (`E0.AUDIT`) |
| **Phase 1** — core sweep | ✅ done 12 Aug, all six batches verified |
| **Phase 2** — extension tracks | ✅ done 17 Aug, all ten experiments verified |
| **Phase 3** — convergence + `PRESPEC.md` | ✅ done 25 Aug (overnight, unattended): `PRESPEC.md` frozen and amended once (`E3.2.AMEND.1`), headline set rerun per spec, `E3.FREEZE` logged, verified from raw (136 checks), reviewed by two adversarial audits. **Aim 2 did not meet its pre-specified criterion.** Evan's sign-off on `PRESPEC.md` pending |
| **Phase 4** — paper-ready outputs | ✅ done 25 Aug: Table 1, Figures 1–2, Table 2, supplement S1–S5, verified (99 checks) |

Phases are run manually, one at a time. Results were frozen at `E3.FREEZE` on
25 Aug; the plan's deadline was 26 Aug.

Headline so far: of 615 participants with kidney or heart damage on a study-visit
test, **471 (76.6%) reported no corresponding diagnosis**. Framing settled at
`E2.DECIDE`: lead with the population **burden**, with the falling conditional
fraction as the mechanism that explains it.

Phase 2 found a nerve-specific depression signal (CES-D-10 → nerve damage, OR
1.22 per SD, q = 0.027, age + severity + site). **Phase 3 tested it against the
pre-specified model** (age + BMI + HbA1c + severity + site, Benjamini-Hochberg
within ten models): OR 1.16 (1.02–1.32), q = 0.25 — **the pre-specified
criterion was not met**, and the paper reports Aim 2 as an exploratory signal
that did not survive it. Phase 3 confirmed the one promoted track finding:
participants with diabetes-range HbA1c but no diabetes label carry four times
the odds of kidney damage (OR 4.11, bootstrap 1.83–8.51), and 16 of the 19 with
kidney or heart damage had never been told. Phase 2's clean negative stands:
access barriers do **not** explain being unrecognized.

## Folder contents

| File | Committed | Purpose |
|---|---|---|
| `README.md` | yes | This file — orientation, status, how to run |
| `RESULTS_LOG.md` | yes | The durable record: cutoff definitions, verification protocol, and every run including nulls |
| `PRESPEC.md` | yes | Written at `E3.2` (25 Aug), hash-frozen, amended once (`E3.2.AMEND.1`, parameters unchanged). Evan's sign-off pending; any change is a logged `E3.2.AMEND.n` |
| `PLAN.md` | no — local | Part I: why this paper — aims, rationale, limitations, venues. Part II: the phased experiment list (E0.1 … E4.4) |
| `scripts/` | yes | One runner per experiment — the reproducible method record |
| `scripts/verify/` | yes | Independent re-implementations that check each result |
| `notebooks/` | yes, **outputs cleared** | One notebook per phase — the readable walkthrough |
| `results/` | yes | Figures and aggregate tables only |

### Notebooks vs scripts

They are two views of the same analysis, and neither redefines the other's
logic — both call `src/aireadi`.

| | `scripts/run_e1_N.py` | `notebooks/0N_*.ipynb` |
|---|---|---|
| For | machines: reproducible, re-runnable, writes the artifact **and** its log entry via `results.save()` | people: reading the argument end to end, with figures and interpretation |
| Output | CSV/PNG in `results/` + a `RESULTS_LOG.md` entry | figures in `results/`, no log entry |

```
notebooks/00_phase0_foundation.ipynb        E0.1–E0.4 and the gate decision
notebooks/01_phase1_core_sweep.ipynb        E1.0–E1.5, the six core-sweep batches
notebooks/02_phase2_extension_tracks.ipynb  E2.AGE and tracks A–F
notebooks/03_phase3_convergence.ipynb       E3.1 ranking, PRESPEC, E3.3 confirmatory reruns
notebooks/04_phase4_paper_outputs.ipynb     Table 1, Figures 1–2, Table 2, supplement
```

Two Phase-2 experiments needed a build before they could run — the items `E0.3`
flagged BUILD REQUIRED. Both write participant-level tables to gitignored
`data/processed/p1/` and are run once:

```bash
python3 scripts/build_cgm_metrics.py      # 2,245 Dexcom streams -> CV, MAGE, TAR
python3 scripts/build_ecg_statements.py   # 2,251 WFDB headers -> interpretations
```

**Clear outputs before committing** — `jupyter nbconvert --clear-output
--inplace papers/p1-unrecognized-damage/notebooks/*.ipynb`. The notebooks are
written not to print participant rows in the first place (they show schema and
completeness instead of `df.head()`), so an un-cleared notebook is harmless by
construction rather than only by discipline.

Chart styling and the palette live in `src/aireadi/figures.py`, not in the
notebooks. Severity group gets a single-hue **ordinal** ramp because it is
ordered; organ gets **categorical** hues because it is identity. Both palettes
were validated for colour-vision separation against the chart surface.

## Sending a report to someone

A report in `reports/` links its figures by **relative path**. That works
locally and breaks the moment the file travels — email the `.md` and the
recipient sees broken image references, because the images were never inside
the file. Export first:

```bash
PYTHONPATH=src python3 -m aireadi.report_export --pdf reports/2026-08-12-phase1-report.md
```

This writes two shareable files beside the source:

| Format | Use it when | Note |
|---|---|---|
| **`.pdf`** | **Slack, email — the default choice** | Slack previews it inline in the message |
| `.html` | you want it scrollable and responsive | one self-contained file; recipient downloads, then opens in any browser |

Both embed every figure as base64 with **no external references at all** — no
CDN, no linked images, no scripts. They work offline and survive forwarding.
Drop `--pdf` for HTML only.

`PLAN.md` is gitignored at Evan's request — a working document, not a
deliverable. Ask him for a copy. Narrative phase
write-ups live in `reports/` (also gitignored), one per phase, named
`YYYY-MM-DD-phaseN-report.md`.

**Nothing in `reports/` or the two local plans is authoritative.** If a number
or a decision matters, it is in `RESULTS_LOG.md` — that is the file the paper
is written from.

## Working rules

Repo-wide rules — adjustment defaults, logging, what may be committed — are in
`CLAUDE.md` at the root, stated once. Two are specific to this paper:

- **Every result is run twice.** Once through `src/aireadi`, then again by a
  verifier in `scripts/verify/` that rebuilds each variable from the raw CSVs
  without importing the package. An experiment is not finished until its
  verifier prints zero discrepancies. `verify_report.py` extends this to prose:
  it traces every number quoted in a phase report back to a committed artifact.
- **Derived participant-level tables belong in `data/processed/p1/`** —
  gitignored, never `results/`.

## Running an experiment

```bash
python3 papers/p1-unrecognized-damage/scripts/run_e1_1.py          # run
python3 papers/p1-unrecognized-damage/scripts/verify/verify_e1_1.py  # check
```

Phase 2's verifiers cover a whole track at a time rather than one experiment:
`verify_e2c.py` for the psychosocial track and `verify_e2_tracks.py` for A, B, D,
E, F and `E2.AGE` — 111 checks between them. `verify_phase2_report.py` audits the
phase report, in both directions: every number quoted must trace to an artifact,
**and** every association surviving FDR must appear in the prose. That second
direction is there because the Phase-1 audit originally only checked the first,
and a kidney-only result reached the report generalised to both organs.

Phase 3 and 4 follow the same pattern: `verify_e3.py` (136 checks: the E2.TIMING
artifact, the E3.1 ranking's bookkeeping and two from-raw site refits, and every
E3.3 headline model refitted through statsmodels' array API) and `verify_e4.py`
(99 checks: Table 1 from raw, Table 2 and the supplement against their sources).
`verify_phase3_report.py` and `verify_phase4_report.py` audit the reports.
`run_e3_3.py` reads every parameter from the JSON block in `PRESPEC.md`, so the
frozen spec and the executed analysis cannot drift.

Each runner writes its aggregate table to `results/` and appends to
`RESULTS_LOG.md` in one call via `results.save()`, so an artifact and its log
entry can never drift apart.

## Phase 0 was a gate

Before any analysis, the three tests and their matching self-report items were
located and profiled (E0.1–E0.2). The gate triggered: nerve has an excellent
exam and no comparator. Resolved at `E0.GATE` — see above. Full record in
`RESULTS_LOG.md`; plain-language write-ups in `reports/`.
