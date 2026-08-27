"""Build per-participant CGM variability metrics — the E0.3 "BUILD REQUIRED" item.

The CGM manifest carries mean glucose and nothing else, so time-above-range,
coefficient of variation and MAGE have to come from the raw per-participant
streams: 2,245 Dexcom G6 JSON files, ~1.9 MB each. This script fetches them
through the normal fetch-once cache and writes one participant-level row each.

Run once. The output lands in `data/processed/p1/` because it is
participant-level and therefore may never enter `papers/*/results/`; the
experiment that consumes it (E2A.1) writes only aggregates.

    python3 build_cgm_metrics.py            # resumes; skips cached files
    python3 build_cgm_metrics.py --limit 50 # a quick smoke run

Why the metrics are what they are: mean glucose already exists in the manifest
and is the average. CV and MAGE are *variability* — the same average reached
smoothly or in swings — which is a different construct and the reason this build
is worth 4 GB. TAR>180 is the clinical standard-of-care measure. All of them
come from `wearables.cgm_metrics`, so this script decides nothing about the
statistics; it only moves bytes and loops.
"""

from __future__ import annotations

import sys
import time

import pandas as pd

from aireadi import azure_io, wearables
from aireadi.constants import DATASET_ROOT

OUT = azure_io.repo_root() / "data" / "processed" / "p1" / "cgm_metrics.parquet"

limit = None
if "--limit" in sys.argv:
    limit = int(sys.argv[sys.argv.index("--limit") + 1])

manifest = azure_io.load_table("manifest_cgm")
if limit:
    manifest = manifest.head(limit)

print(f"CGM build — {len(manifest):,} participants")
print(f"output: {OUT}")

rows, failures = [], []
t0 = time.time()

for i, rec in enumerate(manifest.itertuples(index=False), start=1):
    blob = f"{DATASET_ROOT}/{str(rec.glucose_filepath).lstrip('/')}"
    try:
        local = azure_io.fetch(blob)
        stream = wearables.parse_dexcom_json(local.read_bytes())
        if stream is None or stream.empty:
            failures.append((rec.person_id, "empty stream"))
            continue
        metrics = wearables.cgm_metrics(stream["glucose_mg_dl"])
        if metrics is None:
            failures.append((rec.person_id, "under 12 valid readings"))
            continue
        # Censored-reading counts travel with the metrics, so an analysis can
        # exclude a heavily-censored participant rather than discover later that
        # half their stream was a "High" string.
        censored = stream.attrs.get("censored", {"high": 0, "low": 0})
        rows.append({"person_id": str(rec.person_id),
                     "cgm_days": float(rec.glucose_sensor_sampling_duration_days),
                     "censored_high": censored["high"],
                     "censored_low": censored["low"],
                     "pct_censored": round(
                         100 * (censored["high"] + censored["low"])
                         / max(metrics["readings_used"], 1), 2),
                     **metrics})
    except Exception as exc:                       # noqa: BLE001
        failures.append((rec.person_id, f"{type(exc).__name__}: {exc}"))

    if i % 250 == 0 or i == len(manifest):
        rate = i / (time.time() - t0)
        print(f"  {i:,}/{len(manifest):,}  ok={len(rows):,}  failed={len(failures):,}  "
              f"{rate:.1f}/s  eta {(len(manifest) - i) / rate / 60:.1f} min", flush=True)

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_parquet(OUT)      # gitignored: participant-level

print(f"\nwrote {len(out):,} rows x {out.shape[1]} columns to {OUT}")
print(f"failures: {len(failures)}")
for person, why in failures[:20]:
    print(f"  {person}: {why}")
if len(failures) > 20:
    print(f"  ... and {len(failures) - 20} more")

# A sanity check the runner should not have to repeat: the built mean must
# agree with the manifest's own average, which is the one number both paths
# compute. If these disagree, the parser is reading the wrong field.
check = out.merge(
    manifest.assign(person_id=manifest.person_id.astype(str))
            [["person_id", "average_glucose_level_mg_dl"]],
    on="person_id", how="inner")
delta = (check["glucose_mean"] - check["average_glucose_level_mg_dl"]).abs()
print(f"\nbuilt mean vs manifest mean: n={len(check):,}, "
      f"median |diff|={delta.median():.3f} mg/dL, max={delta.max():.2f} mg/dL")
print(f"disagreements over 5 mg/dL: {int((delta > 5).sum())} "
      f"(expected: the manifest average handles the censored 'High'/'Low' readings "
      f"differently from this build, which places them at the 40/400 boundary)")

censored_any = out[out[["censored_high", "censored_low"]].sum(axis=1) > 0]
print(f"\ncensored readings: {int(out.censored_high.sum()):,} High + "
      f"{int(out.censored_low.sum()):,} Low across {len(censored_any):,} participants; "
      f"{int((out.pct_censored > 5).sum())} participants over 5% censored, "
      f"{int((out.pct_censored > 25).sum())} over 25%")
