#!/usr/bin/env python3
"""Build a participant-level SDOH / survey score table.

Project head's follow-up (2026-08-26/27): "do a deep dive into how
environmental sensor data relates to survey data ... especially social
determinants of health including neighborhood security, CESD-10 for
depression, PAID-5 for problem areas in diabetes, dietary survey, and
substance use; if there are links, we can try connecting them to diabetic
severity."

Builds one score per construct, all from observation.csv via
`omop.add_item_key` / `omop.phenx_family`, following this repo's existing
prefix-selection convention (never positional slicing -- see
`constants.PHENX_FAMILIES` docstring):

  - neighborhood_score: mean of the 17 z-scored pxne items (PhenX
    Neighborhood battery -- "neighborhood security"). Items use different
    Likert scales (pxne1 is 1-5, pxne2 is 1-4, etc.), so each item is
    z-scored across participants before averaging, to avoid an item with a
    wider raw scale dominating the composite. Direction of "worse"
    neighborhood is NOT verified against the PhenX codebook here -- treat
    the sign as unconfirmed, magnitude/significance is what matters for
    this pass.
  - cesd_total: `cestl`, existing convention (0-30, screen-positive >= 10).
  - paid_total: `paidscore`, existing convention (0-20, cutoff >= 8).
  - diet_score: `dietscore` (0-9). Low coverage flagged in the build
    output -- this item was answered by far fewer participants than the
    others.
  - substance_use_count: sum of 7 binary "currently use" flags
    (alcohol/beer/liquor/wine/marijuana/cigarettes/vaping), 0-7. A simple
    count, not a validated composite -- flagged as such.
  - current_smoker: `susmkncf` alone, kept as its own binary column since
    smoking is the substance-use item most directly comparable to
    PM2.5/VOC/NOx exposure in the literature (an indoor combustion
    source), rather than being buried inside the 7-item count.

Output: data/processed/p2/sdoh_survey_scores.csv (participant-level,
gitignored, no identifiers beyond person_id per repo convention for
processed tables).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aireadi import azure_io, omop

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "sdoh_survey_scores.csv"

SUBSTANCE_KNCF_ITEMS = [
    "sualckncf",  # alcohol, any
    "subrkncf",   # beer
    "sulqkncf",   # liquor
    "suwnkncf",   # wine
    "sumrjkncf",  # marijuana
    "susmkncf",   # cigarettes
    "suvpkncf1",  # vaping
]


def main() -> None:
    obs_raw = azure_io.load_table("observation")
    obs = omop.add_item_key(obs_raw, clean_special=True)

    # Neighborhood: 17-item PhenX battery, z-scored per item then averaged.
    # phenx_family already returns one row per person, one column per item.
    neigh_wide = omop.phenx_family(obs, "neighborhood")
    neigh_z = (neigh_wide - neigh_wide.mean()) / neigh_wide.std()
    neighborhood_score = neigh_z.mean(axis=1, skipna=True).rename("neighborhood_score")
    neighborhood_n_items = neigh_wide.notna().sum(axis=1).rename("neighborhood_n_items_answered")

    cesd_total = omop.first_value(obs, "cestl", name="cesd_total")
    paid_total = omop.first_value(obs, "paidscore", name="paid_total")
    diet_score = omop.first_value(obs, "dietscore", name="diet_score")

    substance_wide = pd.concat([omop.first_value(obs, k, name=k) for k in SUBSTANCE_KNCF_ITEMS], axis=1)
    substance_use_count = substance_wide.sum(axis=1, skipna=True, min_count=1).rename("substance_use_count")
    current_smoker = substance_wide["susmkncf"].rename("current_smoker")

    table = pd.concat(
        [neighborhood_score, neighborhood_n_items, cesd_total, paid_total, diet_score,
         substance_use_count, current_smoker],
        axis=1,
    ).reset_index().rename(columns={"index": "person_id"})

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_PATH, index=False)

    print(f"\n{'='*90}\nSDOH/survey score table -- N={len(table)}\n{'='*90}")
    print(table.describe(include="all").round(2).to_string())
    print(f"\nCoverage (non-null count):\n{table.set_index('person_id').notna().sum().to_string()}")
    print(f"\nWritten to {OUT_PATH}")


if __name__ == "__main__":
    main()
