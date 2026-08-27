"""Garmin activity and Dexcom CGM handling.

Two independent concerns that share a theme: both devices write sentinel
values rather than nulls, and both need cleaning before any average is taken.

`clean_garmin_manifest` covers the summary metrics most analyses use.
`parse_dexcom_json` + `cgm_metrics` cover the raw glucose stream, needed only
when the manifest's mean glucose is not enough (variability, spikes, MAGE).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .constants import (
    CGM_INTERVAL_MINUTES,
    CGM_MIN_READINGS,
    CGM_SENTINEL_VALUES,
    CGM_SEVERE_HIGH,
    CGM_TIR_HIGH,
    CGM_TIR_LOW,
    GARMIN_ERROR_CODES,
    GARMIN_PLAUSIBLE_RANGES,
    PLAUSIBLE_RANGES,
    SLEEP_FRACTION_TO_HOURS,
)

__all__ = [
    "clean_garmin_manifest",
    "parse_dexcom_json",
    "cgm_metrics",
]

# np.trapz was renamed in NumPy 2.0; support both.
_trapezoid = getattr(np, "trapezoid", None) or np.trapz


def clean_garmin_manifest(manifest: pd.DataFrame, *,
                          apply_plausibility: bool = True) -> pd.DataFrame:
    """Clean the Garmin activity manifest into usable summary metrics.

    Applies four fixes that are wrong by default in the raw file:

    * error codes to NaN -- 0 for heart rate and SpO2, -2 for stress and
      respiratory rate. These are "no reading", not measurements, and
      averaging them in drags every summary toward zero;
    * `average_sleep_hours` is a fraction of a day, so multiply by 24;
    * **plausibility bounds**, because scrubbing the sentinel value does not
      undo it. These averages were computed upstream WITH the error codes in
      them, so a contaminated mean lands somewhere between the sentinel and the
      truth rather than on the sentinel: a resting heart rate of 0.03 bpm, a
      stress score of -1.19 on a 0-100 scale. Those rows pass an `!= 0` test and
      are still not measurements. Bounds are in `GARMIN_PLAUSIBLE_RANGES`;
      `apply_plausibility=False` returns the sentinel-only cleaning, which is
      what a sensitivity check needs;
    * respiratory rate is left as-is but is a device-quirk scale (reads 6-9
      against an expected 12-20). Relative comparison only, never absolute.

    Returns a `garmin_dropped_implausible` attribute on `.attrs` recording how
    many values each column lost to the bounds, so a caller can report it
    instead of discovering it later.
    """
    out = manifest.copy()
    out.columns = out.columns.str.strip().str.lower()
    if "person_id" in out.columns:
        out["person_id"] = out["person_id"].astype(str)

    for col, error_code in GARMIN_ERROR_CODES.items():
        if col in out.columns:
            vals = pd.to_numeric(out[col], errors="coerce")
            out[col] = vals.mask(vals.eq(error_code))

    if "average_sleep_hours" in out.columns:
        sleep = pd.to_numeric(out["average_sleep_hours"], errors="coerce")
        # The manifest stores a fraction of a day. Guard against a caller who
        # already scaled it: real sleep in hours never sits below 1.5.
        peak = sleep.max(skipna=True)
        if pd.notna(peak) and peak <= 1.5:
            sleep = sleep * SLEEP_FRACTION_TO_HOURS
        out["average_sleep_hours"] = sleep

    dropped: dict[str, int] = {}
    if apply_plausibility:
        for col, (lo, hi) in GARMIN_PLAUSIBLE_RANGES.items():
            if col in out.columns:
                vals = pd.to_numeric(out[col], errors="coerce")
                keep = vals.between(lo, hi)
                dropped[col] = int((vals.notna() & ~keep).sum())
                out[col] = vals.where(keep)
    out.attrs["garmin_dropped_implausible"] = dropped

    return out


def parse_dexcom_json(raw: bytes | str) -> pd.DataFrame | None:
    """Parse a Dexcom G6 JSON file into a sorted glucose time series.

    Primary AI-READI shape::

        {"body": {"cgm": [{"blood_glucose": {"value": X, "unit": "mg/dL"},
                           "effective_time_frame": {"time_interval":
                             {"start_date_time": "ISO8601"}}}, ...]}}

    Legacy flat shapes are handled as a fallback. Readings outside 40-400
    mg/dL are dropped. Returns a DataFrame of [timestamp, glucose_mg_dl]
    sorted ascending, or None when fewer than 12 valid readings survive
    (under an hour of data is not analysable).

    **The Dexcom writes "Low" and "High" as strings** when a reading falls
    outside its 40-400 mg/dL reportable range, and those are censored values
    rather than missing ones -- see `CGM_SENTINEL_VALUES`. They are mapped to the
    range boundary, not skipped: skipping them silently deletes readings from the
    participants with the worst control, which is the opposite of what a
    damage analysis can afford. The counts are reported on
    `.attrs["censored"]` as `{"high": n, "low": n}` so a caller can flag a
    heavily-censored participant instead of treating the stream as clean.
    """
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    readings = None
    if isinstance(data, dict):
        body = data.get("body")
        if isinstance(body, dict) and isinstance(body.get("cgm"), list):
            readings = body["cgm"]

    if readings is None:
        if isinstance(data, list):
            readings = data
        elif isinstance(data, dict):
            for key in ("Readings", "readings", "egvs", "glucose_readings", "data"):
                if isinstance(data.get(key), list):
                    readings = data[key]
                    break
            else:
                lists = [v for v in data.values() if isinstance(v, list)]
                readings = lists[0] if lists else None

    if not isinstance(readings, list) or len(readings) < CGM_MIN_READINGS:
        return None

    rows = []
    censored = {"high": 0, "low": 0}
    for r in readings:
        if not isinstance(r, dict):
            continue

        value, timestamp = None, None
        bg = r.get("blood_glucose")
        if isinstance(bg, dict):
            value = bg.get("value")
        etf = r.get("effective_time_frame")
        if isinstance(etf, dict):
            interval = etf.get("time_interval")
            if isinstance(interval, dict):
                timestamp = interval.get("start_date_time") or interval.get("end_date_time")

        if value is None:
            value = (r.get("value") or r.get("Value") or r.get("glucose")
                     or r.get("GlucoseValue") or r.get("glucoseValue"))
        if timestamp is None:
            timestamp = (r.get("displayTime") or r.get("DisplayTime")
                         or r.get("systemTime") or r.get("timestamp") or r.get("time"))

        if value is None or timestamp is None:
            continue

        # A sentinel string is a censored reading at the reportable-range
        # boundary. This branch has to come before float(), which would raise
        # and send it to the silent `continue` below.
        if isinstance(value, str):
            token = value.strip().lower()
            if token in CGM_SENTINEL_VALUES:
                censored[token] += 1
                rows.append({"timestamp": timestamp,
                             "glucose_mg_dl": CGM_SENTINEL_VALUES[token]})
                continue

        try:
            rows.append({"timestamp": timestamp, "glucose_mg_dl": float(value)})
        except (TypeError, ValueError):
            continue

    if not rows:
        return None

    lo, hi = PLAUSIBLE_RANGES["glucose_mg_dl"]
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = (
        df.dropna(subset=["timestamp", "glucose_mg_dl"])
        .loc[lambda d: d["glucose_mg_dl"].between(lo, hi)]
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
        .reset_index(drop=True)
    )
    if len(df) < CGM_MIN_READINGS:
        return None
    df.attrs["censored"] = censored
    return df


def _find_runs(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    """Inclusive (start, end) index pairs for runs of True at least min_len long."""
    runs: list[tuple[int, int]] = []
    in_run, start = False, 0
    for i, flag in enumerate(mask):
        if flag and not in_run:
            in_run, start = True, i
        elif not flag and in_run:
            in_run = False
            if i - start >= min_len:
                runs.append((start, i - 1))
    if in_run and (len(mask) - start) >= min_len:
        runs.append((start, len(mask) - 1))
    return runs


def cgm_metrics(glucose, *, high: float = CGM_TIR_HIGH, low: float = CGM_TIR_LOW,
                severe: float = CGM_SEVERE_HIGH,
                min_spike_readings: int = 2) -> dict | None:
    """Summarise one participant's glucose stream.

    Returns mean/SD/CV/median, time in/above/below range, spike counts and
    burden, and MAGE. Returns None for fewer than 12 valid readings.

    Assumes readings are evenly spaced at the Dexcom G6 five-minute interval,
    which is what durations and areas are scaled by.
    """
    g = np.asarray(glucose, dtype=float)
    g = g[np.isfinite(g)]
    if len(g) < CGM_MIN_READINGS:
        return None

    sd = float(np.std(g, ddof=1))
    mean = float(np.mean(g))
    m: dict[str, float] = {
        "readings_used": float(len(g)),
        "glucose_mean": mean,
        "glucose_sd": sd,
        "glucose_cv": float(sd / mean * 100) if mean else float("nan"),
        "glucose_median": float(np.median(g)),
        "tir": float(np.mean((g >= low) & (g <= high)) * 100),
        "tar_180": float(np.mean(g > high) * 100),
        "tar_250": float(np.mean(g > severe) * 100),
        "tbr_70": float(np.mean(g < low) * 100),
        # Dexcom's published estimate of HbA1c from mean glucose.
        "gmi": float(3.31 + 0.02392 * mean),
    }

    spikes = _find_runs(g > high, min_spike_readings)
    m["spike_count"] = float(len(spikes))
    if spikes:
        durations = [(e - s + 1) * CGM_INTERVAL_MINUTES for s, e in spikes]
        peaks = [float(np.max(g[s:e + 1])) for s, e in spikes]
        areas = [
            float(_trapezoid(np.maximum(g[s:e + 1] - high, 0)) * CGM_INTERVAL_MINUTES)
            for s, e in spikes
        ]
        m["spike_duration_mean"] = float(np.mean(durations))
        m["spike_duration_total"] = float(np.sum(durations))
        m["spike_peak_mean"] = float(np.mean(peaks))
        m["spike_area"] = float(np.sum(areas))
    else:
        m["spike_duration_mean"] = 0.0
        m["spike_duration_total"] = 0.0
        m["spike_peak_mean"] = float("nan")
        m["spike_area"] = 0.0

    m["spike_count_250"] = float(len(_find_runs(g > severe, min_spike_readings)))
    m["mage"] = _mage(g, sd)
    return m


def _mage(g: np.ndarray, sd: float) -> float:
    """Mean Amplitude of Glycemic Excursions.

    Mean size of the peak-to-nadir swings that exceed one standard deviation.
    """
    from scipy.signal import argrelextrema

    if sd <= 0 or len(g) < CGM_MIN_READINGS:
        return float("nan")
    try:
        peaks = argrelextrema(g, np.greater_equal, order=3)[0]
        nadirs = argrelextrema(g, np.less_equal, order=3)[0]
    except Exception:
        return float("nan")

    turning = np.sort(np.unique(np.concatenate([peaks, nadirs])))
    if len(turning) < 2:
        return float("nan")

    excursions = np.abs(np.diff(g[turning]))
    qualifying = excursions[excursions > sd]
    return float(np.mean(qualifying)) if len(qualifying) else float("nan")
