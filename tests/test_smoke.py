"""Offline smoke tests for the shared data layer.

No network, no credentials, no Azure. Run after any change to
`src/aireadi/`, and after a fresh install to confirm the environment works:

    pytest tests/ -v          # or:  python tests/test_smoke.py

Several of these are regression guards for defects that already reached
analysis on this dataset. `test_special_codes_all_cleaned` is the important
one: the EDA-era code scrubbed only 99, and a 1-6 Likert item ended up
reporting a maximum of 777.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from aireadi import cohort, constants, omop, wearables


# ── Dataset identity ────────────────────────────────────────────────────

def test_canonical_dataset_identity():
    assert constants.STUDY_ID == "1438dd73-c4cb-48b8-8fa8-c858771207c3"
    assert constants.CONTAINER_NAME == "aireadi-container"
    assert constants.DATASET_VERSION == "3.0.0"


def test_expected_group_totals():
    assert sum(constants.EXPECTED_GROUP_N.values()) == constants.EXPECTED_TOTAL_N == 2280


# ── Survey special codes: the regression guard ──────────────────────────

def test_special_codes_all_cleaned():
    """555, 777 and 99 must all become NaN -- not just 99."""
    values = pd.Series([1.0, 2.0, 555.0, 777.0, 99.0, 6.0, np.nan])
    cleaned = omop.clean_survey_values(values)

    assert cleaned.isna().sum() == 4
    assert list(cleaned.dropna()) == [1.0, 2.0, 6.0]
    assert cleaned.max() == 6.0

    # The exact EDA failure, kept as a contrast: scrubbing only 99 leaves a
    # 1-6 Likert item reporting a maximum of 777.
    assert values.mask(values == 99).max() == 777.0


def test_refused_survey_value_does_not_become_a_score():
    obs = pd.DataFrame({
        "person_id": [1, 2],
        "observation_source_value": ["cestl, CESD Total", "cestl, CESD Total"],
        "value_as_number": [12, 777],
    })
    scores = omop.first_value(omop.add_item_key(obs), "cestl", name="cesd_total")
    assert scores.loc["1"] == 12
    assert pd.isna(scores.loc["2"])


# ── Source-value parsing ────────────────────────────────────────────────

def test_item_key_parsing():
    src = pd.Series([
        "cestl, CESD Total Score",
        "  PXFI1, The food that (I/we) bought  ",
        "bmi_vsorres, Body Mass Index",
    ])
    assert list(omop.item_key(src)) == ["cestl", "pxfi1", "bmi_vsorres"]


def test_person_id_is_string_for_safe_merges():
    obs = pd.DataFrame({
        "person_id": [1, 2],
        "observation_source_value": ["cestl, T", "cestl, T"],
        "value_as_number": [5, 6],
    })
    keyed = omop.add_item_key(obs)
    # Check the values, not the dtype: pandas 3.0 uses a dedicated str dtype
    # where 2.x used object.
    assert all(isinstance(v, str) for v in keyed["person_id"])


def test_missing_item_degrades_to_empty_series():
    obs = pd.DataFrame({
        "person_id": [1],
        "observation_source_value": ["cestl, T"],
        "value_as_number": [5],
    })
    ghost = omop.first_value(omop.add_item_key(obs), "not_a_real_item", name="ghost")
    assert len(ghost) == 0
    assert ghost.name == "ghost"


# ── Comorbidity counting ────────────────────────────────────────────────

def test_comorbidity_excludes_fall_count_and_gate_item():
    obs = pd.DataFrame({
        "person_id": [1, 1, 1, 2, 2],
        "observation_source_value": [
            "mhoccur_hbp, High blood pressure",
            "mhoccur_fallot, Number of falls",   # a COUNT, not a flag
            "mhoccur_yn, Any condition",         # a gate question
            "mhoccur_hbp, High blood pressure",
            "mhoccur_mi, Heart attack",
        ],
        "value_as_number": [1, 7, 1, 1, 1],
    })
    counts = omop.comorbidity_count(omop.add_item_key(obs))
    assert counts.loc["1"] == 1.0   # the fall count of 7 must not inflate this
    assert counts.loc["2"] == 2.0


# ── Labs ────────────────────────────────────────────────────────────────

@pytest.fixture
def measurement():
    return pd.DataFrame({
        "person_id": [1, 1, 2, 3, 4],
        "measurement_source_value": [
            "import_hba1c, Hemoglobin A1c",
            "import_hba1c, Hemoglobin A1c",
            "import_hba1c, Hemoglobin A1c",
            "lbscat_a1c, Hemoglobin - g/dL",   # CBC haemoglobin, NOT HbA1c
            "import_hba1c, Hemoglobin A1c",
        ],
        "value_as_number": [7.1, 8.2, 6.0, 13.5, 999.0],
        "measurement_date": ["2023-01-01", "2023-06-01", "2023-02-01",
                             "2023-01-01", "2023-01-01"],
        "operator_concept_id": [None] * 5,
    })


def test_hba1c_uses_import_hba1c_not_cbc_haemoglobin(measurement):
    out = omop.extract_lab(measurement, "import_hba1c", name="hba1c")
    assert float(out.loc[out.person_id == "1", "hba1c"].iloc[0]) == 8.2  # most recent
    assert "3" not in set(out.person_id)   # lbscat_a1c excluded
    assert "4" not in set(out.person_id)   # implausible 999 dropped


def test_troponin_below_detection_is_flagged():
    trop = pd.DataFrame({
        "person_id": [1, 2],
        "measurement_source_value": ["trop_hs, hs-Troponin", "trop_hs, hs-Troponin"],
        "value_as_number": [15.0, 3.0],
        "measurement_date": ["2023-01-01", "2023-01-01"],
        "operator_concept_id": [None, constants.OPERATOR_BELOW_DETECTION],
    })
    out = omop.extract_lab(trop, "trop_hs", name="troponin", flag_below_detection=True)
    assert out.loc[out.person_id == "2", "troponin_below_detection"].iloc[0]
    assert not out.loc[out.person_id == "1", "troponin_below_detection"].iloc[0]


# ── Garmin ──────────────────────────────────────────────────────────────

@pytest.fixture
def garmin():
    return pd.DataFrame({
        "person_id": [1, 2, 3],
        "average_heartrate_bpm": [72.0, 0.0, 80.0],           # 0 = error
        "average_oxygen_saturation_pct": [96.0, 0.0, 95.0],   # 0 = error
        "average_stress_level": [30.0, -2.0, 25.0],           # -2 = error
        "average_respiratory_rate_bpm": [7.5, -2.0, 8.0],     # -2 = error
        "average_sleep_hours": [0.30, 0.25, 0.33],            # fraction of a day
    })


def test_garmin_error_codes_become_missing(garmin):
    clean = wearables.clean_garmin_manifest(garmin)
    for col in ("average_heartrate_bpm", "average_oxygen_saturation_pct",
                "average_stress_level", "average_respiratory_rate_bpm"):
        assert pd.isna(clean.loc[1, col]), col
    # Without this the mean would be dragged to 50.7 by the zero.
    assert clean["average_heartrate_bpm"].mean() == 76.0


def test_sleep_fraction_converts_to_hours_exactly_once(garmin):
    clean = wearables.clean_garmin_manifest(garmin)
    assert clean.loc[0, "average_sleep_hours"] == pytest.approx(7.2)
    again = wearables.clean_garmin_manifest(clean)
    assert again.loc[0, "average_sleep_hours"] == pytest.approx(7.2)


# ── CGM ─────────────────────────────────────────────────────────────────

def _cgm_blob(values):
    return json.dumps({"body": {"cgm": [
        {"blood_glucose": {"value": v, "unit": "mg/dL"},
         "effective_time_frame": {"time_interval": {
             "start_date_time": f"2023-08-01T{i // 12:02d}:{(i % 12) * 5:02d}:00Z"}}}
        for i, v in enumerate(values)
    ]}}).encode()


SERIES = [100, 105, 110, 190, 200, 210, 195, 120, 115, 95, 90, 260, 270, 255, 100, 105]


def test_parses_aireadi_nested_format():
    ts = wearables.parse_dexcom_json(_cgm_blob(SERIES))
    assert ts is not None and len(ts) == len(SERIES)
    assert ts["timestamp"].is_monotonic_increasing


def test_parses_legacy_flat_format():
    flat = json.dumps([{"value": 100 + i, "displayTime": f"2023-08-01T00:{i:02d}:00"}
                       for i in range(20)]).encode()
    assert wearables.parse_dexcom_json(flat) is not None


@pytest.mark.parametrize("bad", [
    b"not json",
    json.dumps([{"value": 100, "time": "2023-08-01"}]).encode(),   # too few
])
def test_unusable_input_returns_none(bad):
    assert wearables.parse_dexcom_json(bad) is None


def test_implausible_glucose_filtered():
    assert wearables.parse_dexcom_json(_cgm_blob([5000] * 20)) is None


def test_cgm_metrics():
    ts = wearables.parse_dexcom_json(_cgm_blob(SERIES))
    m = wearables.cgm_metrics(ts["glucose_mg_dl"].values)
    assert m["tir"] + m["tar_180"] + m["tbr_70"] == pytest.approx(100)
    assert m["spike_count"] >= 2
    assert m["spike_count_250"] == 1
    assert np.isfinite(m["spike_area"]) and m["spike_area"] > 0
    assert m["gmi"] == pytest.approx(3.31 + 0.02392 * m["glucose_mean"])
    assert wearables.cgm_metrics([100, 105, 110]) is None


# ── Threshold flags ─────────────────────────────────────────────────────

def test_missing_score_is_not_a_negative_screen():
    flags = cohort._threshold_flag(pd.Series([12.0, 4.0, np.nan, 10.0]),
                                   constants.CESD_CUTOFF)
    assert flags.iloc[0] == 1.0
    assert flags.iloc[1] == 0.0
    assert pd.isna(flags.iloc[2])   # not 0.0
    assert flags.iloc[3] == 1.0     # cutoff is inclusive


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
