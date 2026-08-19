#!/usr/bin/env python3
"""EG.17 -- build the 5-level glycemic-range feature set the project head specified (2026-08-19).

Supersedes the earlier ad-hoc 140/180 thresholds with his exact 5 ranges:

    severe_hypo:     g < 54            (strict)
    moderate_hypo:   54 <= g <= 69
    normal:          70 <= g <= 180
    moderate_hyper:  181 <= g <= 250
    severe_hyper:    g > 250           (strict)

For each range, four features per participant (3 originally requested +
fraction, added 2026-08-19 -- "more transferable across people" than raw
minutes since it normalizes out how many days someone was monitored):
    {range}_minutes_per_day  -- average time per day spent in this range
    {range}_fraction         -- fraction of all valid readings in this range
                                 (redundant with minutes_per_day by his own
                                 note, kept because it's comparable across
                                 people with different monitoring lengths)
    {range}_mean_glucose     -- average CGM reading, among readings in this range
    {range}_windows_per_day  -- average number of separate episodes ("windows")
                                 in this range per day (a window = a run of
                                 >=2 consecutive readings in the range, same
                                 min-run convention wearables.cgm_metrics()
                                 already uses for spike detection -- flagged
                                 here since he didn't specify a minimum, and
                                 the "normal" range's windows/day will mostly
                                 be ~1 per day given how much time is spent
                                 there, unlike the other 4 ranges)

Plus 4 requested overall summary features (not range-specific):
    glucose_mean            -- mean CGM across all days (same as
                                wearables.cgm_metrics()'s glucose_mean)
    glucose_overall_variance -- variance of every reading pooled together
                                 across the whole stream (NOT the same as
                                 EG.12's interday_glucose_variance, which is
                                 the variance of daily *means* -- this is
                                 variance of all raw readings)
    glucose_mean_daily_variance -- mean of each day's own variance,
                                    averaged across days. Same computation
                                    as EG.12's intraday_glucose_variance,
                                    recomputed here so this table is
                                    self-contained; the two should agree.
    glucose_cv_ratio         -- SD / mean (raw ratio, not multiplied by 100
                                 the way wearables.cgm_metrics()'s
                                 glucose_cv is) -- added 2026-08-19 per his
                                 explicit request.

Per-day rates use each participant's actual monitoring span (max-min
timestamp), same convention as build_cgm_table.py / build_glucose_variability_table.py.

Output: data/processed/p2/cgm_range_features.csv (participant-level,
gitignored, same pattern as the other raw-CGM-stream builds).
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from aireadi import azure_io, wearables
from aireadi.constants import CGM_MIN_READINGS

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2"
OUT_PATH = OUT_DIR / "cgm_range_features.csv"

CGM_INTERVAL_MINUTES = 5
MIN_WINDOW_READINGS = 2  # design choice, flagged in the docstring above

RANGES = [
    ("severe_hypo", lambda g: g < 54),
    ("moderate_hypo", lambda g: (g >= 54) & (g <= 69)),
    ("normal", lambda g: (g >= 70) & (g <= 180)),
    ("moderate_hyper", lambda g: (g >= 181) & (g <= 250)),
    ("severe_hyper", lambda g: g > 250),
]


def _dataset_root() -> str:
    return f"{azure_io.study_id()}/dataset"


def _find_runs(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    """Contiguous True-runs of at least min_len, as (start, end) index pairs."""
    runs = []
    start = None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                runs.append((start, i - 1))
            start = None
    if start is not None and len(mask) - start >= min_len:
        runs.append((start, len(mask) - 1))
    return runs


def _aggregate_one(person_id: str, blob_path: str) -> dict | None:
    try:
        raw = azure_io.get_container().get_blob_client(blob_path).download_blob().readall()
    except Exception as exc:  # noqa: BLE001
        return {"person_id": person_id, "error": str(exc)}

    stream = wearables.parse_dexcom_json(raw)
    if stream is None:
        return {"person_id": person_id, "error": "unparseable or <12 valid readings"}

    g = stream["glucose_mg_dl"].to_numpy(dtype=float)
    span_days = max((stream["timestamp"].max() - stream["timestamp"].min()).total_seconds() / 86400, 1e-6)

    total_readings = len(g)
    result: dict[str, float | str | None] = {"person_id": person_id}
    for name, cond in RANGES:
        mask = cond(g)
        minutes_in_range = float(mask.sum() * CGM_INTERVAL_MINUTES)
        readings_in_range = g[mask]
        runs = _find_runs(mask, MIN_WINDOW_READINGS)
        result[f"{name}_minutes_per_day"] = minutes_in_range / span_days
        result[f"{name}_fraction"] = float(mask.sum() / total_readings) if total_readings else float("nan")
        result[f"{name}_mean_glucose"] = float(readings_in_range.mean()) if len(readings_in_range) else float("nan")
        result[f"{name}_windows_per_day"] = len(runs) / span_days

    stream = stream.copy()
    stream["date"] = stream["timestamp"].dt.date
    by_day = stream.groupby("date")["glucose_mg_dl"]
    day_counts = by_day.count()
    valid_days = day_counts[day_counts >= CGM_MIN_READINGS].index

    glucose_mean = float(g.mean())
    glucose_sd = float(np.std(g, ddof=1))
    result["glucose_mean"] = glucose_mean
    result["glucose_overall_variance"] = float(np.var(g, ddof=1))
    result["glucose_mean_daily_variance"] = (
        float(by_day.var().loc[valid_days].mean()) if len(valid_days) else float("nan")
    )
    result["glucose_cv_ratio"] = glucose_sd / glucose_mean if glucose_mean else float("nan")
    result["monitoring_span_days"] = span_days
    result["error"] = None
    return result


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
    if n_errors:
        print(f"NOTE: {n_errors} participant stream(s) failed/skipped -- see 'error' column")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(out)} rows to {OUT_PATH} in {time.time() - t0:,.0f}s total.")


if __name__ == "__main__":
    main()
