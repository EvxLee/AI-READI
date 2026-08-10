# Paper 2 — Results log

Every run gets one line here, **including nulls**. Numbers are copied from
executed outputs, never from memory.

**Rules**

- One row per run: ID, one-line method, one-line result, keep/kill decision.
- `PRESPEC.md` is frozen once dated and committed. Deviations get logged here
  with justification.
- The primary Aim 1 model ran during scoping, before the plan was finalised.
  That is disclosed in the methods; the official run is documented
  confirmation, not a first look.
- Aggregate outputs go in `results/`, keyed by experiment ID. Nothing keyed by
  `person_id`.

## Scoping results (pre-plan, disclosed in methods)

| Run | Result |
|---|---|
| Aim 1 main model, N = 1,951 complete cases | CES-D-10 ~ log(PM2.5) + BMI + steps + stress + HR + sleep + age + severity + site. Indoor PM2.5 p = 1e-6; BMI p = 1.3e-5; insulin dependence p = 0.0018; younger age significant. |
| Aim 2 subgroup, insulin-dependent under 70, N = 188 | Mean CES-D-10 8.62 vs 5.61 for the rest; 36.7% positive screens vs 18.5%. |

Open question: is the subgroup's depression excess explained by its elevated
BMI / PM2.5 / wearable profile, or independent? Either answer publishes.

## Status

| ID | Status | Key output | One-line result | Keep/Kill |
|----|--------|-----------|-----------------|-----------|
| | not started | | | |

## Log

<!-- Append entries below. Newest last. Format:

### <ID> — <YYYY-MM-DD>
**Method:** one line.
**Result:** one line, numbers copied from output.
**Decision:** keep / kill / rescope, and why.
**Output:** results/<ID>_*.csv

-->
