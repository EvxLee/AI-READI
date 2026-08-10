# AI-READI analysis

Analysis code for two cross-sectional studies of the NIH
[AI-READI](https://aireadi.org/) dataset (Bridge2AI) — a multimodal Type 2
diabetes cohort of ~2,280 adults spanning four severity groups, from healthy
to insulin-treated.

Work by the UCSF Tech Lab team: Evan Lee, Parwaan (P2 lead), and mentor Faris.

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

Each paper's folder holds its analysis plan, prespecification, experiment
list, results log, notebooks, and committed aggregate outputs.

## Data access

The dataset is **controlled-access** and is not distributed with this
repository. Running anything here requires your own credentials for the
project's Azure Blob container under an executed data use agreement.

No participant-level data is committed to this repository, by policy — see
`CLAUDE.md`.

## Setup

```bash
git clone https://github.com/EvxLee/AI-READI.git
cd AI-READI

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # installs deps + the aireadi package

cp .env.example .env                 # then fill in your connection string
```

Verify the install without touching the network:

```bash
python -c "import aireadi; print(aireadi.__version__, aireadi.STUDY_ID)"
```

## Using the shared package

All data access and cleaning lives in `src/aireadi/`. Notebooks import from
it and stay thin, so a fix reaches both papers at once.

```python
from aireadi import cohort, omop, azure_io

# One row per participant: severity, age, site, BMI, HbA1c,
# CES-D-10, PAID-5, comorbidity count, CGM and Garmin summaries.
df = cohort.build_core_table()
cohort.qc_report(df)

# Find the source-value keys for a variable you have not located yet.
cohort.find_items("albumin|creatinine", table="measurement")
```

Blobs are downloaded once into `data/cache/` and reused; nothing streams from
Azure on every run.

## Layout

```
src/aireadi/     shared data layer (constants, azure_io, omop, wearables, cohort)
papers/          one folder per paper: plan, prespec, experiments, log, notebooks, results
docs/            CAVEATS.md (read first), DATASET_OVERVIEW.md, reference/
data/            gitignored: cache/ for raw downloads, processed/ for derived tables
```

## Before you touch the data

Read **`docs/CAVEATS.md`**. It documents the traps that have already
corrupted analyses on this dataset — the wrong HbA1c field, survey special
codes, troponin below-detection rows, Garmin error codes, and a survey-scoring
defect that invalidated an entire earlier analysis track.

The exploratory phase that preceded this repository layout is preserved in the
`eda-archive` git tag. Its conclusions are superseded; see `docs/CAVEATS.md`
for what went wrong.
