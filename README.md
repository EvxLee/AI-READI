# AI-READI analysis

Analysis code for two cross-sectional studies of the NIH
[AI-READI](https://aireadi.org/) dataset (Bridge2AI) — a multimodal Type 2
diabetes cohort of ~2,280 adults spanning four severity groups, from healthy
to insulin-treated.

Work by the UCSF Tech Lab team: Evan Lee, Parwaan, and mentor Faris.

## The two papers

**Paper 1 — Unrecognized organ damage** (`papers/p1-organ-damage/`)

Three inexpensive tests performed at a single study visit — urine albumin
(kidney), monofilament exam (nerve), and high-sensitivity troponin (heart) —
compared against what participants reported a doctor had ever told them. The
question is how much detectable organ damage goes unrecognized, per organ,
across the diabetes severity spectrum. Depressive symptoms (CES-D-10) are a
clearly labelled secondary aim.

**Paper 2 — Environment, BMI, and wearables vs depressive symptoms**
(`papers/p2-env-depression/`)

Personal indoor environmental exposure (PM2.5 and other home-sensor
measures), body composition, and wearable-measured physiology, examined side
by side against one depression outcome (CES-D-10) in a staged diabetes
cohort.

---

## Getting started

### 0. What you need first

- **Python 3.10 or newer** (`python3 --version` to check).
- **Access to the project's Azure Blob container.** The AI-READI dataset is
  controlled-access and is *not* included in this repository. You need your
  own connection string, which requires an executed data use agreement — ask
  Evan or Faris. Nothing below the install step will work without it.

### 1. Install

```bash
git clone https://github.com/EvxLee/AI-READI.git
cd AI-READI

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt    # installs dependencies + the aireadi package
```

### 2. Check the install (no credentials needed)

```bash
pytest tests/ -q
```

Expected: `19 passed`. This runs entirely offline — if it passes, your
environment is correct.

### 3. Add your credentials

```bash
cp .env.example .env
```

Open `.env` and paste your connection string into
`AZURE_STORAGE_CONNECTION_STRING`. The container and study ID are already
filled in correctly; leave them alone. `.env` is gitignored and must never be
committed.

### 4. Confirm you can reach the data

```python
from aireadi import cohort

df = cohort.load_participants()
cohort.qc_report(df)
```

Expected output:

```
Rows: 2,280 (expected 2,280)

Severity group Ns:
  Healthy      776  (expected 776)  ok
  Pre-DM       560  (expected 560)  ok
  Oral Med     686  (expected 686)  ok
  Insulin      258  (expected 258)  ok
```

If the Ns don't match, you are pointed at the wrong container or a different
release — stop and check before analysing anything.

### 5. One-time setup for notebooks

```bash
nbstripout --install
```

This strips notebook outputs automatically on commit. Notebook outputs
routinely contain rows keyed by `person_id`, which must never be committed —
this makes that mistake hard to make by accident.

---

## Repository structure

| Folder / file | What it's for |
|---|---|
| `src/aireadi/` | **The shared toolbox.** Every rule for loading and cleaning this dataset lives here, once. Notebooks import from it instead of copy-pasting logic, so fixing a bug here fixes it for both papers. |
| `papers/` | **One folder per paper.** Each holds that paper's plan, experiment log, notebooks, and finished figures/tables. The two papers stay separate so nobody trips over the other's work. |
| `docs/` | **Reference material about the dataset.** Read `CAVEATS.md` before you touch data — it lists the traps that have already ruined analyses here. |
| `tests/` | **Automated checks that the toolbox still works.** Run `pytest tests/` after changing anything in `src/`. Catches broken cleaning logic before it reaches a result. |
| `data/` | **Your local working files.** Downloads land in `cache/`, derived tables in `processed/`. Entirely gitignored — nothing in here is ever committed or shared. |
| `requirements.txt` | The list of packages to install. One command sets up everything. |
| `pyproject.toml` | Tells the installer that `src/aireadi/` is a package, so `from aireadi import ...` works from any folder without path juggling. |
| `.env.example` | Template for your credentials. Copy to `.env` and fill in; `.env` is never committed. |
| `.claude/` | Settings for Claude Code (an AI coding assistant), if you use it. Harmless and ignorable if you don't. |

Inside each paper folder:

| File / folder | What it's for |
|---|---|
| `PLAN.md` | The research plan — the questions, the reasoning, the design. *(Kept locally, not committed — ask the paper's lead.)* |
| `PRESPEC.md` | The final analysis recipe, written at convergence, dated, then **frozen**. No changing outcome definitions after this. |
| `RESULTS_LOG.md` | Every analysis run, one line each — **including the ones that found nothing.** This is what lets the paper foreground its strongest results without a reviewer suspecting cherry-picking. |
| `notebooks/` | The experiments themselves. Thin: load, call the toolbox, plot, interpret. |
| `results/` | Finished figures and summary tables, named by experiment ID. **Aggregates only** — never anything with one row per person. |

---

## How to run an experiment

```python
from aireadi import cohort

# One row per participant: severity, age, site, BMI, HbA1c,
# CES-D-10, PAID-5, comorbidity count, CGM and Garmin summaries.
# Survey special codes and device error codes are already handled.
df = cohort.build_core_table()

# Looking for a variable and don't know its field name?
cohort.find_items("albumin|creatinine", table="measurement")
```

The first call downloads a few large tables and will take a couple of
minutes. They're cached in `data/cache/` afterwards, so every later run is
fast — nothing re-streams from Azure.

Then: save aggregate output to your paper's `results/`, and add one line to
`RESULTS_LOG.md` — including if the result was null.

---

## The rules

These are short, and they exist because breaking them has already cost this
project real work.

1. **Never commit participant-level data.** No raw files, no per-person
   tables, no notebook outputs with `person_id` in them. `data/` is
   gitignored; keep it that way.
2. **Read `docs/CAVEATS.md` before touching data.** The wrong HbA1c field,
   survey codes that look like real scores, device error codes that look like
   readings — all documented, all have bitten someone here.
3. **Log every run, including nulls,** in your paper's `RESULTS_LOG.md`.
4. **Numbers in any report come from executed output,** never from memory.
5. **Adjust for age + severity group + site** on any association claim.
   Severity confounds nearly everything in this cohort.
6. **Shared logic goes in `src/aireadi/`,** not copy-pasted between
   notebooks. If you write the same cleaning step twice, move it.

---

## Notes

The exploratory phase that preceded this layout is preserved in the
`eda-archive` git tag. Its conclusions are superseded — see `docs/CAVEATS.md`
for what went wrong and why.
