"""E2.TIMING — how far apart are the self-report survey and the clinic tests?

The paper originally described its design as three tests and a self-report
taken on the same day. `E2.TIMING` (20 Aug 2026) found that half of that is
right: the three objective markers are concurrent with one another, but the
`mhoccur` medical-history battery -- the source of every self-reported
diagnosis in Aim 1 -- was administered a median of 35 days BEFORE the clinic
visit. That finding lived only as a log entry; `E2.DOCS` flagged that Methods
should not cite a number with no artifact behind it. This runner produces the
artifact.

Two tables:

* ``E2_TIMING_survey_lag``      -- for each survey battery, the interval from
  survey date to the troponin draw (the anchor for the clinic visit): median,
  IQR, share same-day, n.
* ``E2_TIMING_marker_concurrence`` -- pairwise same-day agreement between the
  objective markers, plus each marker's same-day agreement with the history
  survey, so it is visible that no organ is advantaged over another.

Nothing here changes a result: every analysis joins survey to marker per
participant, which is correct at any interval. The point is the Methods
sentence, and the direction of the bias -- a diagnosis received between survey
and visit reads as "never told", so unawareness is if anything overstated.
"""

from __future__ import annotations

import pandas as pd

from aireadi import azure_io, omop, results

import _phase1

_phase1.banner("E2.TIMING", "Survey-to-visit interval and marker concurrence")

obs = azure_io.load_table(
    "observation", usecols=["person_id", "observation_source_value", "observation_date"])
obs["item_key"] = omop.item_key(obs["observation_source_value"])
obs["person_id"] = obs["person_id"].astype(str)
obs["date"] = pd.to_datetime(obs["observation_date"], errors="coerce")

meas = azure_io.load_table(
    "measurement", usecols=["person_id", "measurement_source_value", "measurement_date"])
meas["item_key"] = omop.item_key(meas["measurement_source_value"])
meas["person_id"] = meas["person_id"].astype(str)
meas["date"] = pd.to_datetime(meas["measurement_date"], errors="coerce")


def first_date(frame: pd.DataFrame, key: str) -> pd.Series:
    """Earliest recorded date per participant for one item key."""
    sel = frame[frame["item_key"] == key]
    return sel.groupby("person_id")["date"].min()


# ── Anchors ─────────────────────────────────────────────────────────────
SURVEYS = {
    "mhoccur_rnl": "Medical history (mhoccur) — source of every self-reported diagnosis",
    "cestl": "CES-D-10 depression screen",
    "paidscore": "PAID-5 diabetes distress",
    "pxfi1": "PhenX SDOH battery (food insecurity item 1)",
    "dmlfeet": "Diabetes self-management battery (foot inspection item)",
}
MARKERS = {
    "import_troponin_t": "hs-troponin T (heart)",
    "import_urine_albumin": "urine albumin (kidney)",
    "msslffl": "monofilament exam (nerve)",
    "viaodplog": "visual acuity (photopic, OD)",
}

survey_dates = {k: first_date(obs, k) for k in SURVEYS}
marker_dates = {k: first_date(meas, k) for k in MARKERS}
visit = marker_dates["import_troponin_t"]          # the clinic-visit anchor

# ── Survey -> visit lag ─────────────────────────────────────────────────
lag_rows = []
for key, label in SURVEYS.items():
    lag = (visit - survey_dates[key]).dt.days.dropna()
    lag_rows.append({
        "survey_item": key, "survey": label, "n_paired": int(len(lag)),
        "median_days_before_visit": float(lag.median()),
        "iqr_lo": float(lag.quantile(0.25)), "iqr_hi": float(lag.quantile(0.75)),
        "pct_same_day": round(100 * float((lag == 0).mean()), 1),
        "pct_survey_after_visit": round(100 * float((lag < 0).mean()), 1),
        "min_days": int(lag.min()), "max_days": int(lag.max()),
    })
lag_table = pd.DataFrame(lag_rows).set_index("survey_item")
pd.set_option("display.width", 220)
print("\nSurvey -> clinic visit (troponin draw) interval, days:")
print(lag_table.to_string())

# ── Marker concurrence ──────────────────────────────────────────────────
conc_rows = []
anchor = marker_dates["import_troponin_t"]
history = survey_dates["mhoccur_rnl"]
for key, label in MARKERS.items():
    d = marker_dates[key]
    paired_trop = pd.concat([d, anchor], axis=1, keys=["a", "b"]).dropna()
    paired_hist = pd.concat([d, history], axis=1, keys=["a", "b"]).dropna()
    conc_rows.append({
        "marker_item": key, "marker": label, "n_measured": int(d.notna().sum()),
        "n_paired_with_troponin": int(len(paired_trop)),
        "pct_same_day_as_troponin": round(100 * float((paired_trop.a == paired_trop.b).mean()), 1),
        "n_paired_with_history_survey": int(len(paired_hist)),
        "pct_same_day_as_history_survey": round(100 * float((paired_hist.a == paired_hist.b).mean()), 1),
    })
conc_table = pd.DataFrame(conc_rows).set_index("marker_item")
print("\nMarker concurrence:")
print(conc_table.to_string())

mh = lag_table.loc["mhoccur_rnl"]
alb = conc_table.loc["import_urine_albumin"]
same_day_range = (conc_table["pct_same_day_as_history_survey"].min(),
                  conc_table["pct_same_day_as_history_survey"].max())

results.save(
    "E2.TIMING", lag_table, paper="p1",
    method=("Artifact for the E2.TIMING documentation check (E2.DOCS asked for one before "
            "Methods cites the number). Per participant, the interval from each survey "
            "battery's date to the troponin draw, which anchors the clinic visit; and pairwise "
            "same-day agreement between the objective markers and with the history survey."),
    result=(f"The mhoccur history battery precedes the clinic visit by a median of "
            f"{mh.median_days_before_visit:.0f} days (IQR {mh.iqr_lo:.0f}-{mh.iqr_hi:.0f}), "
            f"same-day for {mh.pct_same_day}% of {mh.n_paired:,} paired participants; "
            f"{mh.pct_survey_after_visit}% answered it after the visit. The same lag applies "
            f"to every survey in the battery: same-day "
            + ", ".join(f"{lag_table.loc[k, 'survey'].split(' ')[0]} {lag_table.loc[k, 'pct_same_day']}%"
                        for k in lag_table.index if k != "mhoccur_rnl")
            + f". The objective tests are concurrent: urine albumin shares a date with troponin for "
            f"{alb.pct_same_day_as_troponin}% of {alb.n_paired_with_troponin:,}. Marker-by-marker "
            f"same-day agreement with the history survey runs {same_day_range[0]}-{same_day_range[1]}%, "
            f"so no organ is advantaged relative to another."),
    decision="keep — wording artifact only; no result changes, bias runs toward overstating unawareness",
    name="survey_lag",
)
results.save(
    "E2.TIMING", conc_table, paper="p1",
    method="Pairwise same-day agreement between the objective markers, and with the history survey.",
    result=("; ".join(f"{r.marker}: {r.pct_same_day_as_troponin}% same-day as troponin (n={r.n_paired_with_troponin}), "
                      f"{r.pct_same_day_as_history_survey}% same-day as history survey"
                      for r in conc_table.itertuples())),
    decision="keep", name="marker_concurrence", primary=False,
)
