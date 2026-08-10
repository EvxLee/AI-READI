# Paper 2 — Environment, BMI, and wearables vs depressive symptoms

**Lead:** Parwaan · **Drafting:** late September 2026 · **Submission:** early October 2026, after Paper 1 ships

Personal indoor environmental exposure (PM2.5, temperature, humidity, light,
VOC, NOx), body composition, and wearable-measured physiology (Garmin heart
rate, SpO2, stress, sleep, steps, plus CGM), examined side by side against one
depression outcome (CES-D-10) across the diabetes severity spectrum.

## Folder contents

| File | Committed | Purpose |
|---|---|---|
| `PLAN.md` | no — local | Full research plan |
| `PRESPEC.md` | yes | Analysis plan, dated, then **frozen** |
| `RESULTS_LOG.md` | yes | Every run, including nulls |
| `notebooks/` | yes, outputs cleared | Numbered experiments, thin |
| `results/` | yes | Figures and aggregate tables only |

## Starting points

`cohort.build_core_table()` already returns severity, age, site, BMI, HbA1c,
CES-D-10, PAID-5, comorbidity count, CGM mean glucose, and cleaned Garmin
summaries — one row per participant, with survey special codes and Garmin
error codes already handled.

`cohort.build_p2_table()` is the stub for the environmental block. It raises
`NotImplementedError` on purpose: the per-participant sensor CSVs are large
(50–65 MB each), so how they get aggregated is Parwaan's call. Build on
`build_core_table()` rather than beside it, so a fix to shared survey or
wearable logic reaches both papers.

## Environmental data notes

- Log-transform PM2.5 — median ~3, max ~1,178 µg/m³. A raw mean is meaningless.
- Exclude the sensor that logged 1,145 °C.
- Sensor placement varies (bedroom 767, living room 706, office 74, dining 60)
  and was not randomised. Check placement against severity group and report it.
- BMI, severity, and glucose overlap by design — run and report VIF diagnostics.

Full list in `docs/CAVEATS.md`. Read it before touching data.

## Honesty requirement

The primary model was run during scoping, before the analysis plan was
finalised. The methods section must disclose this plainly and present the
official run as documented confirmation, not a first look.

## Working rules

- Notebooks import from `src/aireadi`; they do not redefine cleaning logic.
- Every run gets a line in `RESULTS_LOG.md`. Nulls included.
- `results/` takes aggregates only. Nothing keyed by `person_id` is ever
  committed; derived tables go to `data/processed/p2/` (gitignored).
