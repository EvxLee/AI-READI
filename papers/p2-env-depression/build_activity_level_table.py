#!/usr/bin/env python3
"""Build per-participant minutes-in-activity-level from raw Garmin streams.

EG.4 found `steps` failed both mediation links (backwards direction in
EG.2/EG.3, not significant at all in EG.4). Project head asked, 2026-08-17,
whether we're using the raw activity-level breakdown instead of steps --
each participant's raw `physical_activity_filepath` stream (Garmin
vivosmart5) tags every timestamped interval with an `activity_name`:
`sedentary`, `generic`, `walking`, `running` (plus a small number of blank
placeholder entries at stream start, excluded here).

This builds two "active minutes per day" variants, both requested:
  * v1 -- anything above sedentary counts as active (generic+walking+running)
  * v2 -- only walking+running count as active (sedentary+generic = inactive)

Per-day normalization uses each participant's actual monitoring span
(max-min timestamp across all their entries), not the manifest's
`physical_activity_num_days` field, matching the convention already used
in `build_cgm_table.py`.

Files are small -- streamed into memory and discarded, same pattern as
`build_env_table.py` / `build_cgm_table.py`, not using azure_io.fetch()'s
permanent cache.

Output is participant-level, so per docs/CAVEATS.md and aireadi.results'
rules it is never committed: `data/processed/p2/activity_level_minutes.csv`,
gitignored.

Usage:
    python papers/p2-env-depression/build_activity_level_table.py [--limit N] [--workers N]
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd

from aireadi import azure_io

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2"
OUT_PATH = OUT_DIR / "activity_level_minutes.csv"

ACTIVE_V1 = {"generic", "walking", "running"}   # anything above sedentary
ACTIVE_V2 = {"walking", "running"}              # only walking/running counts as active
INACTIVE_NAMES = {"sedentary", "generic", "walking", "running"}  # excludes blank placeholder entries


def _dataset_root() -> str:
    return f"{azure_io.study_id()}/dataset"


def _parse_ts(t: str) -> datetime:
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def _aggregate_one(person_id: str, blob_path: str) -> dict | None:
    try:
        raw = azure_io.get_container().get_blob_client(blob_path).download_blob().readall()
    except Exception as exc:  # noqa: BLE001
        return {"person_id": person_id, "error": str(exc)}

    try:
        data = json.loads(raw)
        entries = data["body"]["activity"]
    except Exception as exc:  # noqa: BLE001
        return {"person_id": person_id, "error": f"unparseable: {exc}"}

    minutes_by_name: dict[str, float] = {"sedentary": 0.0, "generic": 0.0, "walking": 0.0, "running": 0.0}
    t_min, t_max = None, None
    for entry in entries:
        name = entry.get("activity_name", "")
        if name not in INACTIVE_NAMES:
            continue  # skip blank placeholder entries
        tf = entry["effective_time_frame"]["time_interval"]
        s = _parse_ts(tf["start_date_time"])
        e = _parse_ts(tf["end_date_time"])
        dur_min = (e - s).total_seconds() / 60
        if dur_min < 0:
            continue
        minutes_by_name[name] += dur_min
        t_min = s if t_min is None else min(t_min, s)
        t_max = e if t_max is None else max(t_max, e)

    total_minutes = sum(minutes_by_name.values())
    if total_minutes <= 0 or t_min is None:
        return {"person_id": person_id, "error": "no valid activity-level entries"}

    span_days = max((t_max - t_min).total_seconds() / 86400, 1e-6)

    active_v1 = sum(minutes_by_name[n] for n in ACTIVE_V1)
    active_v2 = sum(minutes_by_name[n] for n in ACTIVE_V2)

    return {
        "person_id": person_id,
        "monitoring_span_days": span_days,
        "sedentary_minutes": minutes_by_name["sedentary"],
        "generic_minutes": minutes_by_name["generic"],
        "walking_minutes": minutes_by_name["walking"],
        "running_minutes": minutes_by_name["running"],
        "total_minutes": total_minutes,
        "active_minutes_v1": active_v1,
        "active_minutes_v2": active_v2,
        "active_minutes_v1_per_day": active_v1 / span_days,
        "active_minutes_v2_per_day": active_v2 / span_days,
        "active_fraction_v1": active_v1 / total_minutes,
        "active_fraction_v2": active_v2 / total_minutes,
        "error": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    manifest = azure_io.load_table("manifest_activity")
    manifest["person_id"] = manifest["person_id"].astype(str)
    manifest = manifest[manifest["physical_activity_filepath"].notna()]
    if args.limit:
        manifest = manifest.head(args.limit)

    total = len(manifest)
    print(f"Aggregating {total} participant physical_activity streams with {args.workers} workers...", flush=True)

    root = _dataset_root()
    rows: list[dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_aggregate_one, r.person_id, f"{root}/{r.physical_activity_filepath.lstrip('/')}"): r.person_id
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
