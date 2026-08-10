# CLAUDE.md

Context and rules for Claude Code working in this repository.

## What this project is

A UCSF Tech Lab team (Evan, Parwaan, mentor Faris) is producing two
journal-quality medical papers from the NIH AI-READI dataset — a multimodal
Type 2 diabetes cohort of ~2,280 adults across four severity groups — before
the team's tenure ends in autumn 2026.

- **Paper 1** (`papers/p1-organ-damage/`, Evan primary): unrecognized
  kidney / nerve / heart damage — urine albumin, monofilament exam,
  hs-troponin — against same-day self-reported diagnoses, across the severity
  spectrum, with CES-D-10 depression as a clearly labelled *secondary* aim.
  Results freeze **26 Aug 2026**; submission mid-September. **This is the
  priority.**
- **Paper 2** (`papers/p2-env-depression/`, Parwaan primary): CES-D-10 against
  personal home environmental exposure (PM2.5 and others), BMI, and wearable
  metrics. Drafted late September, submitted early October, after P1 ships.

Keep the scopes distinct: P1 does not adopt environmental variables, P2 does
not test organ-damage markers.

An earlier exploratory phase produced 34 notebooks and was wound up in August
2026. That work was scaffolding, not a deliverable; it survives only in the
`eda-archive` git tag. Do not resurrect it.

## Dataset

- **AI-READI v3.0.0**, ~2,280 participants (Healthy 776, Pre-DM 560,
  Oral Med 686, Insulin 258), collected 2023–2025 at UW, UAB, and UCSD.
- **Canonical container:** `aireadi-container`
- **Canonical study ID:** `1438dd73-c4cb-48b8-8fa8-c858771207c3`

The EDA-era code used a second, older study ID (`00b62456-…`). It is wrong.
Both canonical values live in `src/aireadi/constants.py` and are the single
source of truth.

If a newer release (the anticipated ~4,000-participant final) lands
mid-project, **do not switch datasets mid-paper**. A locked analysis stays on
the version it started on; a new release earns one line in limitations and
future work. Every analysis states which version it ran on.

## Compliance — non-negotiable

AI-READI is **controlled-access under a data use agreement**.

- Never commit participant-level data: no raw files, no derived per-person
  tables, no notebook outputs containing rows keyed by `person_id`.
- Clear all notebook outputs before committing.
- `data/` is entirely gitignored. Raw downloads go to `data/cache/`, derived
  tables to `data/processed/<paper>/`.
- `papers/*/results/` takes **aggregates only**: figures, group-level tables,
  model summaries.
- Note for context: participant-level CSVs were committed in the initial
  commit (`7638547`) and remain in git history. Ask Evan before making the
  repository public or sharing it.

## How to work here

- **Notebooks stay thin.** Shared logic lives in `src/aireadi/`. A notebook
  loads, calls, plots, and interprets — it does not redefine a cleaning rule.
  If you write the same transformation twice, move it into the package.
- **Azure is fetch-once.** `azure_io` downloads a blob into `data/cache/` and
  reuses it. Do not stream large tables on every run.
- **Read `docs/CAVEATS.md` before touching data.** It lists the traps —
  wrong HbA1c field, survey special codes, troponin below-detection rows,
  Garmin error codes, the PhenX SDOH defect. Several of them have silently
  corrupted analyses before.
- **Log every run** in the paper's `RESULTS_LOG.md`: ID, one-line method,
  one-line result, keep/kill decision. **Nulls included, always.** The log is
  the defence against the cherry-picking critique that public-dataset papers
  attract.
- **Each paper's `PRESPEC.md` is frozen once dated and committed.** No new
  outcome definitions mid-analysis. Deviations get logged with justification
  in `RESULTS_LOG.md`.
- **Numbers quoted in any report or summary are re-read from executed
  outputs, never recalled from memory.**
- **Age + severity group + site adjustment is the default** for any
  association claim. Severity confounds almost everything.

## Layout

```
src/aireadi/        shared data layer — the only place cleaning logic lives
  constants.py      dataset identity, item keys, error codes, thresholds
  azure_io.py       blob fetch with a local cache
  omop.py           observation/measurement parsing + special-code cleaning
  wearables.py      Garmin cleaning, Dexcom CGM parsing and metrics
  cohort.py         participant-level table builders, discovery, QC
papers/p{1,2}-*/    PLAN, PRESPEC, EXPERIMENTS, RESULTS_LOG, notebooks, results
docs/               CAVEATS.md, DATASET_OVERVIEW.md, reference/
data/               gitignored — cache/ and processed/
```

`PROJECT_CONTEXT.md` (gitignored, local only) carries the full scientific
context: hypotheses, expected abstracts, venue candidates, and the reasoning
behind decisions already made. Read it before touching any analysis.
