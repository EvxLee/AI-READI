"""E2E.2 — ECG numeric metrics vs troponin and the other damage markers.

Does electrical abnormality co-travel with biochemical injury? Unlike E2E.1 this
uses no machine *interpretation* at all — only the device's numeric measurements
(rate, PR, QRS duration, QT, QTc), which are instrument readings rather than
diagnostic opinions and so do not carry the unadjudicated caveat. They come
straight from the manifest columns E0.3 profiled as ready, no header harvest
needed.

The cardiac-coherence question is the useful one here: hs-troponin is the paper's
heart marker, and if the ECG's numeric measures track it, that is internal
corroboration that the troponin signal is cardiac rather than assay noise. If
they do not, it bounds what a single troponin draw can be said to establish.

QTc is the metric with prior expectation attached — prolongation is associated
with cardiac risk and with autonomic neuropathy, which makes it the one metric
here with a plausible route to the *nerve* outcome as well as the heart one.

The manifest holds 2,257 rows for 2,251 participants: six repeat ECGs, which are
deduplicated to the first record before merging (CAVEATS). Doing that after the
merge would double-count those people.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations, azure_io, results

import _phase2

_phase2.banner("E2E.2", "ECG numeric metrics vs troponin and the damage markers")

df = _phase2.load()

manifest = azure_io.load_table("manifest_ecg")
manifest["person_id"] = manifest["person_id"].astype(str)
print(f"ECG manifest: {len(manifest):,} rows, {manifest.person_id.nunique():,} participants")
ecg = manifest.drop_duplicates("person_id", keep="first")
print(f"after deduplicating repeat ECGs: {len(ecg):,} rows")

METRICS = {"Rate": "rate_bpm", "PR": "pr_ms", "QRSD": "qrsd_ms",
           "QT": "qt_ms", "QTc": "qtc_ms"}
ecg = ecg.rename(columns=METRICS)
for column in METRICS.values():
    ecg[column] = pd.to_numeric(ecg[column], errors="coerce")

df = df.merge(ecg[["person_id", *METRICS.values()]], on="person_id", how="left")

EXPOSURES = {
    "rate_bpm": "ECG heart rate (bpm)",
    "pr_ms": "PR interval (ms)",
    "qrsd_ms": "QRS duration (ms)",
    "qt_ms": "QT interval (ms)",
    "qtc_ms": "QTc interval (ms)",
}

print("\nCoverage and plausibility:")
for column, label in EXPOSURES.items():
    s = df[column]
    print(f"  {label:<24} n={int(s.notna().sum()):>5}  median {s.median():>6.1f}  "
          f"range {s.min():.0f}-{s.max():.0f}")

table = associations.sweep(
    df, EXPOSURES,
    adjustments=["unadjusted", "damage"],
    fdr_within="damage",
)
_phase2.print_table(table, title="ECG metrics vs damage — full sweep")

survivors = _phase2.headline(table)
raw_hits = _phase2.headline(table, use_q=False)
n_adjusted = int((table.index.get_level_values("adjustment") == "damage").sum())

print(f"\nAdjusted family: {n_adjusted} models, {len(raw_hits)} with p < 0.05, "
      f"{len(survivors)} surviving FDR")

# The coherence question stated as its own small table: each metric against the
# heart marker specifically, continuous and binary.
coherence_rows = []
for column, label in EXPOSURES.items():
    for outcome, gaussian in [("abn_heart", False), ("log_troponin", True)]:
        row = associations.fit(df, outcome, column, associations.ADJUSTMENTS["damage"],
                               family="gaussian" if gaussian else "binomial")
        coherence_rows.append({"metric": label, "outcome": outcome,
                               **{k: row[k] for k in ("n", "estimate", "ci_lo", "ci_hi", "p")}})
coherence = pd.DataFrame(coherence_rows).set_index(["metric", "outcome"])
coherence["q"] = associations.fdr(coherence["p"])
_phase2.print_table(coherence, title="Cardiac coherence: ECG metrics vs the heart marker")

results.save(
    "E2E.2", table, paper="p1",
    method=("ECG numeric metrics (rate, PR, QRS duration, QT, QTc) from the manifest — "
            "instrument measurements, NOT machine interpretations, so not subject to the "
            "E2E.1 unadjudicated caveat — against each damage outcome, unadjusted and "
            "adjusted for age + severity + site. Repeat ECGs deduplicated to the first "
            "record before merging. Effects per 1 SD; FDR within the adjusted family."),
    result=(f"Of {n_adjusted} adjusted models, {len(raw_hits)} reach p < 0.05 and "
            f"{len(survivors)} survive FDR. Surviving: "
            f"{_phase2.summarise(survivors) if len(survivors) else 'none'}. "
            f"Coverage {int(df.qtc_ms.notna().sum())} participants with QTc."),
    decision="keep", name="sweep",
)
results.save(
    "E2E.2", coherence, paper="p1",
    method=("Each ECG metric against the heart marker specifically (abnormal troponin and "
            "log troponin), age + severity + site adjusted — the internal-corroboration "
            "check on whether the troponin signal is cardiac."),
    result=("Metrics associated with the heart marker at q<0.05: "
            + ("; ".join(f"{m}/{o} est={r.estimate} (q={r.q:.3g})"
                         for (m, o), r in coherence[coherence.q < 0.05].iterrows())
               or "none")),
    decision="keep", name="coherence", primary=False,
)
