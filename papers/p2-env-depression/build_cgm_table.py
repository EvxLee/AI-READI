#!/usr/bin/env python3
"""Build per-participant glycemic-control metrics from raw Dexcom G6 streams.

`cohort.build_core_table()` only carries the manifest's single pre-computed
`average_glucose_level_mg_dl` -- not the richer glycemic-control profile
(variability, time-in-range, spike frequency/severity) needed once glycemic
control becomes an outcome variable in its own right (env pivot, 2026-08-11 --
see PLAN.md and PRESPEC.md's amendment). This script builds that richer
table from the raw per-participant Dexcom JSON streams.

Reuses `wearables.parse_dexcom_json` + `wearables.cgm_metrics` from the
shared toolbox for parsing and the core TIR/TAR/TBR/spike/MAGE metrics, and
adds two things that function doesn't already give us:

* TAR at 140 mg/dL specifically (cgm_metrics' `high` defaults to 180; the
  request was for both 140 and 180 as separate thresholds), and
* per-day rates for spike count and time-above-threshold, since a raw count
  over a monitoring window of variable length (2-15 days per participant,
  manifest field `glucose_sensor_sampling_duration_days`) is not comparable
  across participants on its own.

Files are small (~2 MB / ~2,850 readings each, 2,245 participants, ~4.5 GB
total) -- streamed into memory and discarded, same pattern as
`build_env_table.py`, not using azure_io.fetch()'s permanent cache.

Output is participant-level, so per docs/CAVEATS.md and aireadi.results'
rules it is never committed: `data/processed/p2/cgm_glycemic_metrics.csv`,
gitignored.

Usage:
    python papers/p2-env-depression/build_cgm_table.py [--limit N] [--workers N]
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from aireadi import azure_io, wearables

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2"
OUT_PATH = OUT_DIR / "cgm_glycemic_metrics.csv"


def _dataset_root() -> str:
    return f"{azure_io.study_id()}/dataset"


def _tar_140(glucose) -> float:
    """% of readings above 140 mg/dL -- the project's other requested cutoff
    alongside the CGM_TIR_HIGH default of 180."""
    import numpy as np
    g = np.asarray(glucose, dtype=float)
    g = g[np.isfinite(g)]
    return float((g > 140).mean() * 100) if len(g) else float("nan")


def _aggregate_one(person_id: str, blob_path: str) -> dict | None:
    try:
        raw = azure_io.get_container().get_blob_client(blob_path).download_blob().readall()
    except Exception as exc:  # noqa: BLE001
        return {"person_id": person_id, "error": str(exc)}

    stream = wearables.parse_dexcom_json(raw)
    if stream is None:
        return {"person_id": person_id, "error": "unparseable or <12 valid readings"}

    m = wearables.cgm_metrics(stream["glucose_mg_dl"].values)
    if m is None:
        return {"person_id": person_id, "error": "cgm_metrics returned None"}

    span_days = (stream["timestamp"].max() - stream["timestamp"].min()).total_seconds() / 86400
    span_days = max(span_days, 1e-6)  # guard divide-by-zero on a degenerate single-day stream

    m["person_id"] = person_id
    m["tar_140"] = _tar_140(stream["glucose_mg_dl"].values)
    m["monitoring_span_days"] = span_days
    m["spikes_per_day_180"] = m["spike_count"] / span_days
    m["spikes_per_day_250"] = m["spike_count_250"] / span_days
    m["minutes_above_180_per_day"] = m["spike_duration_total"] / span_days
    m["error"] = None
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    manifest = azure_io.load_table("manifest_cgm")
    manifest["person_id"] = manifest["person_id"].astype(str)
    if args.limit:
        manifest = manifest.head(args.limit)

    total = len(manifest)
    print(f"Aggregating {total} participant CGM streams with {args.workers} workers...", flush=True)

    root = _dataset_root()
    rows: list[dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_aggregate_one, r.person_id, f"{root}/{r.glucose_filepath.lstrip('/')}"): r.person_id
            for r in manifest.itertuples()
        }
        done = 0
        for fut in as_completed(futures):
            rows.append(fut.result())
            done += 1
            if done % 100 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed
                eta = (total - done) / rate if rate else float("nan")
                print(f"  {done}/{total} done  ({elapsed:,.0f}s elapsed, ~{eta:,.0f}s remaining)", flush=True)

    out = pd.DataFrame(rows)
    n_errors = out["error"].notna().sum() if "error" in out.columns else 0
    if n_errors:
        print(f"NOTE: {n_errors} participant stream(s) failed/skipped -- see 'error' column")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(out)} rows to {OUT_PATH} in {time.time() - t0:,.0f}s total.")


if __name__ == "__main__":
    main()
