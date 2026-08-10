# Paper 1 — Unrecognized organ damage in type 2 diabetes

**Lead:** Evan Lee · **Results freeze:** 26 August 2026 · **Submission:** mid-September 2026

Urine albumin (kidney), monofilament exam (nerve), and high-sensitivity
troponin (heart) — three inexpensive tests performed at one study visit —
compared against what participants reported a doctor had ever told them.
The paper asks how much detectable organ damage goes unrecognized, per organ,
across the diabetes severity spectrum. Depressive symptoms (CES-D-10) are a
secondary aim, labelled as such throughout.

## Folder contents

| File | Committed | Purpose |
|---|---|---|
| `PLAN.md` | no — local | Full research plan |
| `EXPERIMENTS.md` | no — local | Phased experiment list (E0.1 … E4.4) |
| `PRESPEC.md` | yes | Written at Phase 3, dated, then **frozen** |
| `RESULTS_LOG.md` | yes | Every run, including nulls |
| `notebooks/` | yes, outputs cleared | Numbered experiments, thin |
| `results/` | yes | Figures and aggregate tables only |

`PLAN.md` and `EXPERIMENTS.md` are gitignored at Evan's request — they are
working documents, not deliverables. Ask him for a copy.

## Working rules

- Notebooks import from `src/aireadi`; they do not redefine cleaning logic.
- Age + severity group + site adjustment is the default for any association
  claim. A correlation that dies under adjustment is not a finding.
- Every run gets a line in `RESULTS_LOG.md`. Nulls included.
- `results/` takes aggregates only, keyed by experiment ID. Nothing keyed by
  `person_id` is ever committed.
- Derived participant-level tables belong in `data/processed/p1/` (gitignored).

## Phase 0 is a gate

Before any analysis, locate and profile the three tests and their matching
self-report items (E0.1–E0.2). Use `cohort.find_items()` for discovery; the
marker field names are deliberately not hard-coded anywhere in the package.

If monofilament data or any organ's self-report mapping fails, stop and
rescope with Evan — for example to kidney and heart only — before proceeding.
