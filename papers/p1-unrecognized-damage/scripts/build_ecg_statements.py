"""Harvest ECG machine interpretation statements — the second E0.3 "BUILD REQUIRED".

`machine_text` in the ECG manifest is the device name ("PageWriter TC"),
identical for all 2,257 rows. The actual interpretation lives in each
participant's WFDB `.hea` header as `interpretation_comment_*` lines, alongside
an explicit "Unconfirmed Diagnosis" stamp. Getting at it means fetching ~2,257
small header files — cheap, unlike the CGM build.

Output is participant-level and therefore goes to `data/processed/p1/`. E2E.1
consumes it and publishes only counts.

**Everything derived from this file is machine-generated and physician-unreviewed.**
That is not a caveat to add later; the headers say so themselves, and the
decision on record (PROJECT_CONTEXT, decision 2) is that any result from it is
labelled unadjudicated everywhere it appears, figures included. The build
therefore also extracts the confirmation status per record, so the label can be
evidenced from the data rather than asserted.

    python3 build_ecg_statements.py [--limit N]
"""

from __future__ import annotations

import re
import sys
import time

import pandas as pd

from aireadi import azure_io
from aireadi.constants import DATASET_ROOT

OUT = azure_io.repo_root() / "data" / "processed" / "p1" / "ecg_statements.parquet"

# Philips writes the interpretation as numbered comment lines. Both spellings
# appear across the release, so match either rather than assuming one.
COMMENT_RE = re.compile(
    r"^#\s*(?:interpretation_comment|comment)_(\d+)(?:_key)?\s*:\s*(.*)$",
    re.IGNORECASE)
UNCONFIRMED_RE = re.compile(r"unconfirmed|unreviewed|preliminary", re.IGNORECASE)


def parse_header(text: str) -> dict:
    """Pull interpretation statements and confirmation status out of one .hea.

    "Unconfirmed Diagnosis" is written as a comment line like any other, but it
    is a review-status stamp rather than a finding. It is recorded as the flag it
    is and kept OUT of the statement list, otherwise it would be the single most
    common "diagnosis" in the cohort and would inflate every statement count.
    """
    statements, unconfirmed = [], False
    for line in text.splitlines():
        if UNCONFIRMED_RE.search(line):
            unconfirmed = True
        match = COMMENT_RE.match(line.strip())
        if match:
            value = match.group(2).strip()
            if (value and not value.lower().startswith("none")
                    and not UNCONFIRMED_RE.search(value)):
                statements.append(value)
    return {"statements": " | ".join(statements),
            "n_statements": len(statements),
            "unconfirmed_stamp": unconfirmed}


limit = None
if "--limit" in sys.argv:
    limit = int(sys.argv[sys.argv.index("--limit") + 1])

manifest = azure_io.load_table("manifest_ecg")
print(f"ECG manifest: {len(manifest):,} rows, "
      f"{manifest.person_id.nunique():,} participants")

# Six participants have a repeat ECG (CAVEATS). Keep the FIRST record per
# person and record that a duplicate existed, so nobody is counted twice.
manifest = manifest.assign(person_id=manifest.person_id.astype(str))
duplicated = manifest.person_id.duplicated(keep=False)
print(f"repeat ECGs: {int(duplicated.sum())} rows across "
      f"{manifest.loc[duplicated, 'person_id'].nunique()} participants — keeping the first")
deduped = manifest.drop_duplicates("person_id", keep="first")
if limit:
    deduped = deduped.head(limit)

rows, failures = [], []
t0 = time.time()
for i, rec in enumerate(deduped.itertuples(index=False), start=1):
    blob = f"{DATASET_ROOT}/{str(rec.wfdb_hea_filepath).lstrip('/')}"
    try:
        text = azure_io.fetch(blob).read_text(encoding="utf-8", errors="replace")
        rows.append({"person_id": rec.person_id,
                     "had_repeat_ecg": rec.person_id in set(
                         manifest.loc[duplicated, "person_id"]),
                     **parse_header(text)})
    except Exception as exc:                       # noqa: BLE001
        failures.append((rec.person_id, f"{type(exc).__name__}: {exc}"))

    if i % 250 == 0 or i == len(deduped):
        rate = i / (time.time() - t0)
        print(f"  {i:,}/{len(deduped):,}  ok={len(rows):,}  failed={len(failures):,}  "
              f"{rate:.1f}/s  eta {(len(deduped) - i) / rate / 60:.1f} min", flush=True)

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_parquet(OUT)      # gitignored: participant-level

print(f"\nwrote {len(out):,} rows to {OUT}")
print(f"failures: {len(failures)}")
for person, why in failures[:10]:
    print(f"  {person}: {why}")

print(f"\nrecords carrying an explicit unconfirmed/unreviewed stamp: "
      f"{int(out.unconfirmed_stamp.sum()):,} of {len(out):,}")
print(f"records with at least one interpretation statement: "
      f"{int(out.n_statements.gt(0).sum()):,}")
print("\nmost common statements:")
flat = out.statements.str.split(" | ", regex=False).explode().str.strip()
print(flat[flat.ne("")].value_counts().head(25).to_string())
