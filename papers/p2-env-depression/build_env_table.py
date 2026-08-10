#!/usr/bin/env python3
"""Aggregate the raw per-participant Lee Lab Anura environmental sensor CSVs
into one row per participant: mean/median temperature, humidity, light
(lch0), PM2.5, VOC, and NOx.

This is paper-2-specific (`cohort.build_p2_table()` in the shared toolbox is
still a stub -- see its docstring), so it lives here rather than in
`src/aireadi`. It builds on the shared toolbox for everything else (Azure
access, constants) rather than reimplementing it.

Each raw file is ~25-30 MB (2,231 files, ~61.5 GB total for the cohort), so
this streams each blob directly into memory and discards it after
aggregating, rather than using `azure_io.fetch()`'s permanent local cache --
we don't want 61 GB of raw sensor readings sitting in data/cache/ forever
for a table this is trivial to rebuild.

Output is participant-level (has person_id), so per docs/CAVEATS.md and
aireadi.results' rules it is never committed: it goes to
`data/processed/p2/environmental_summary.csv`, which is gitignored.

Usage:
    python papers/p2-env-depression/build_env_table.py [--limit N] [--workers N]
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from aireadi import azure_io
from aireadi.constants import IMPLAUSIBLE_TEMPERATURE_C

# env_sensor_filepath in the manifest is relative to "<study_id>/dataset/",
# same root every other table in constants.PATHS uses.
def _dataset_root() -> str:
    return f"{azure_io.study_id()}/dataset"

USECOLS = ["lch0", "pm2.5", "hum", "temp", "voc", "nox"]
HEADER_COMMENT_LINES = 45  # "# header_lines: 45" -- verified against 1001_ENV.csv

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2"
OUT_PATH = OUT_DIR / "environmental_summary.csv"


def _aggregate_one(person_id: str, blob_path: str) -> dict | None:
    """Download one participant's raw sensor CSV, aggregate, discard."""
    try:
        raw = azure_io.get_container().get_blob_client(blob_path).download_blob().readall()
    except Exception as exc:  # noqa: BLE001 -- report and skip, don't kill the run
        return {"person_id": person_id, "error": str(exc)}

    try:
        df = pd.read_csv(
            io.BytesIO(raw), skiprows=HEADER_COMMENT_LINES, usecols=USECOLS,
            na_values=["nan"], low_memory=False,
        )
    except Exception as exc:  # noqa: BLE001
        return {"person_id": person_id, "error": f"parse failed: {exc}"}

    n_raw = len(df)

    def _clean(col: str) -> pd.Series:
        # A handful of sensors emit a literal "inf" string on channel
        # saturation (confirmed on lch0 for 3 participants: a single inf
        # poisons any mean, even with thousands of good readings alongside
        # it). Treat as missing, same as any other bad reading.
        v = pd.to_numeric(df[col], errors="coerce")
        return v.mask(np.isinf(v))

    temp = _clean("temp")
    n_temp_excluded = int((temp >= IMPLAUSIBLE_TEMPERATURE_C).sum())
    temp = temp.mask(temp >= IMPLAUSIBLE_TEMPERATURE_C)

    pm25 = _clean("pm2.5")
    hum = _clean("hum")
    lch0 = _clean("lch0")
    voc = _clean("voc")
    nox = _clean("nox")

    return {
        "person_id": person_id,
        "n_raw_rows": n_raw,
        "n_temp_excluded_implausible": n_temp_excluded,
        "mean_temp": temp.mean(), "median_temp": temp.median(),
        "mean_hum": hum.mean(), "median_hum": hum.median(),
        "mean_light": lch0.mean(), "median_light": lch0.median(),
        "mean_pm25": pm25.mean(), "median_pm25": pm25.median(),
        "mean_voc": voc.mean(), "median_voc": voc.median(),
        "mean_nox": nox.mean(), "median_nox": nox.median(),
        "error": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                     help="Only process the first N participants (for a quick test run).")
    ap.add_argument("--workers", type=int, default=10,
                     help="Concurrent downloads. Network-bound, not CPU-bound.")
    args = ap.parse_args()

    manifest = azure_io.load_table("manifest_environment")
    manifest["person_id"] = manifest["person_id"].astype(str)
    if args.limit:
        manifest = manifest.head(args.limit)

    total = len(manifest)
    print(f"Aggregating {total} participant environmental sensor files "
          f"with {args.workers} concurrent workers...", flush=True)

    root = _dataset_root()
    rows: list[dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_aggregate_one, r.person_id, f"{root}/{r.env_sensor_filepath.lstrip('/')}"): r.person_id
            for r in manifest.itertuples()
        }
        done = 0
        for fut in as_completed(futures):
            rows.append(fut.result())
            done += 1
            if done % 50 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed
                eta = (total - done) / rate if rate else float("nan")
                print(f"  {done}/{total} done  ({elapsed:,.0f}s elapsed, "
                      f"~{eta:,.0f}s remaining)", flush=True)

    out = pd.DataFrame(rows)
    n_errors = out["error"].notna().sum()
    if n_errors:
        print(f"WARNING: {n_errors} participant file(s) failed -- see 'error' column", file=sys.stderr)

    # Merge in placement + sampling-extent metadata already present in the
    # manifest, so the placement-confound check (docs/CAVEATS.md) doesn't
    # need a second raw-file pass.
    meta = manifest[["person_id", "sensor_location", "sensor_sampling_extent_in_days"]]
    out = out.merge(meta, on="person_id", how="left")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(out)} rows to {OUT_PATH} in {time.time() - t0:,.0f}s total.")


if __name__ == "__main__":
    main()
