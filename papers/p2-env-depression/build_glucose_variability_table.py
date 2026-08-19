#!/usr/bin/env python3
"""EG.12 -- build intraday/interday glucose variability metrics from raw CGM streams.

Project head's follow-up (2026-08-18): the existing glucose_cv metric
(overall coefficient of variation) doesn't separate within-day glycemic
swings from day-to-day drift. Requested the standard within-day/between-
day variability decomposition used in the CGM literature (Rodbard's
SDw/SDb):

  * intraday_glucose_variance -- for each of a person's monitoring days,
    the variance of that day's readings, averaged across their valid days.
    Captures how much glucose swings within a single day.
  * interday_glucose_variance -- the variance of each day's mean glucose,
    across a person's valid days. Captures how much a person's typical
    glucose level drifts from one day to the next.

Reuses `wearables.parse_dexcom_json` (same as `build_cgm_table.py`), which
returns a [timestamp, glucose_mg_dl] DataFrame sorted ascending. Groups by
calendar date (`timestamp.dt.date`).

Design decision (not specified by the project head, flagged here for
confirmation once the "new metrics" he mentioned arrive): a day needs at
least `CGM_MIN_READINGS` (12, the same threshold already used for
whole-stream validity) valid readings to count toward intraday variance;
a person needs at least 2 valid days for interday variance to be defined.

Output: `data/processed/p2/glucose_variability_metrics.csv`
(participant-level, gitignored, same pattern as `build_cgm_table.py`).
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from aireadi import azure_io, wearables
from aireadi.constants import CGM_MIN_READINGS

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2"
OUT_PATH = OUT_DIR / "glucose_variability_metrics.csv"

MIN_VALID_DAYS_FOR_INTERDAY = 2


def _dataset_root() -> str:
    return f"{azure_io.study_id()}/dataset"


def _aggregate_one(person_id: str, blob_path: str) -> dict | None:
    try:
        raw = azure_io.get_container().get_blob_client(blob_path).download_blob().readall()
    except Exception as exc:  # noqa: BLE001
        return {"person_id": person_id, "error": str(exc)}

    stream = wearables.parse_dexcom_json(raw)
    if stream is None:
        return {"person_id": person_id, "error": "unparseable or <12 valid readings"}

    stream = stream.copy()
    stream["date"] = stream["timestamp"].dt.date
    by_day = stream.groupby("date")["glucose_mg_dl"]
    day_counts = by_day.count()
    valid_days = day_counts[day_counts >= CGM_MIN_READINGS].index

    if len(valid_days) == 0:
        return {"person_id": person_id, "error": "no day with >=12 readings"}

    day_variances = by_day.var().loc[valid_days]
    day_means = by_day.mean().loc[valid_days]

    intraday_variance = float(day_variances.mean())
    n_valid_days = len(valid_days)
    interday_variance = float(day_means.var()) if n_valid_days >= MIN_VALID_DAYS_FOR_INTERDAY else float("nan")

    return {
        "person_id": person_id,
        "n_valid_days": n_valid_days,
        "intraday_glucose_variance": intraday_variance,
        "interday_glucose_variance": interday_variance,
        "error": None,
    }


def main() -> None:
    manifest = azure_io.load_table("manifest_cgm")
    manifest["person_id"] = manifest["person_id"].astype(str)

    total = len(manifest)
    print(f"Aggregating {total} participant CGM streams with 16 workers...", flush=True)

    root = _dataset_root()
    rows: list[dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {
            pool.submit(_aggregate_one, r.person_id, f"{root}/{r.glucose_filepath.lstrip('/')}"): r.person_id
            for r in manifest.itertuples()
        }
        done = 0
        for fut in as_completed(futures):
            rows.append(fut.result())
            done += 1
            if done % 200 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed
                eta = (total - done) / rate if rate else float("nan")
                print(f"  {done}/{total} done  ({elapsed:,.0f}s elapsed, ~{eta:,.0f}s remaining)", flush=True)

    out = pd.DataFrame(rows)
    n_errors = out["error"].notna().sum() if "error" in out.columns else 0
    n_no_interday = out["interday_glucose_variance"].isna().sum() if "interday_glucose_variance" in out.columns else 0
    if n_errors:
        print(f"NOTE: {n_errors} participant stream(s) failed/skipped -- see 'error' column")
    if n_no_interday:
        print(f"NOTE: {n_no_interday} participant(s) have <{MIN_VALID_DAYS_FOR_INTERDAY} valid days -- interday_glucose_variance is NaN")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(out)} rows to {OUT_PATH} in {time.time() - t0:,.0f}s total.")


if __name__ == "__main__":
    main()
