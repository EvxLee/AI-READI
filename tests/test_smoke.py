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
import re

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


# ── PhenX family selection ──────────────────────────────────────────────

def _phenx_obs():
    keys = ["pxhi1", "pxhi2",                      # housing insecurity: 2 items
            "pxhic1", "pxhic2", "pxhic3",          # insurance: a different battery
            "pxfi1", "pxfi2", "pxfistartts"]       # food insecurity + a timestamp
    return pd.DataFrame({
        "person_id": [1] * len(keys),
        "observation_source_value": [f"{k}, item text" for k in keys],
        "value_as_number": [1.0] * len(keys),
    })


def test_housing_family_does_not_swallow_the_insurance_battery():
    """`pxhi` is a prefix of `pxhic`; a bare startswith merges two instruments.

    This is the EDA-era SDOH defect in a subtler form -- same wrong-instrument
    outcome, reached through prefix ambiguity rather than positional slicing.
    """
    obs = omop.add_item_key(_phenx_obs())
    housing = omop.phenx_family(obs, "housing_insecurity")
    assert sorted(housing.columns) == ["pxhi1", "pxhi2"]

    insurance = omop.phenx_family(obs, "insurance_type")
    assert not set(insurance.columns) & set(housing.columns)


def test_phenx_family_excludes_survey_metadata_fields():
    """`pxfistartts` is a timestamp, not a response; it must not be scored."""
    obs = omop.add_item_key(_phenx_obs())
    food = omop.phenx_family(obs, "food_insecurity")
    assert sorted(food.columns) == ["pxfi1", "pxfi2"]


# ── Paper 1 organ-damage markers ────────────────────────────────────────

def test_acr_guards_against_zero_urine_creatinine():
    """A dilute void is unmeasurable, not an infinite ratio.

    Left as inf it passes every `>= threshold` test and silently counts as
    kidney damage -- this is the one participant separating the documented
    "~320 abnormal" spot-check from the correct 319.
    """
    df = pd.DataFrame({
        "urine_albumin": [0.48, 30.0, 0.08],
        "urine_creatinine": [65.8, 50.0, 0.0],
    })
    out = cohort._add_kidney_acr(df)

    assert out["acr_mg_g"].iloc[0] == pytest.approx(7.295, abs=1e-3)
    assert out["acr_mg_g"].iloc[1] == pytest.approx(600.0)
    assert pd.isna(out["acr_mg_g"].iloc[2])
    assert not np.isinf(out["acr_mg_g"].dropna()).any()
    assert (out["acr_mg_g"] >= 30).sum() == 1        # not 2


def test_monofilament_summarises_the_worse_foot():
    df = pd.DataFrame({
        "monofilament_left": [10.0, 10.0, 4.0, np.nan],
        "monofilament_right": [10.0, 6.0, 7.0, 10.0],
    })
    out = cohort._add_monofilament_summary(df)

    assert list(out["monofilament_min"][:3]) == [10.0, 6.0, 4.0]
    assert list(out["monofilament_insensate_sites"][:3]) == [0.0, 4.0, 9.0]
    # One foot examined is not a whole-participant summary.
    assert pd.isna(out["monofilament_insensate_sites"].iloc[3])


def test_nerve_has_no_self_report_comparator():
    """E0.2: this release has no neuropathy item, and none may be invented.

    If a future release adds one, this test fails and the gate decision in
    RESULTS_LOG.md gets revisited deliberately rather than by accident.
    """
    assert constants.ORGAN_SELF_REPORT["nerve"] == []
    assert constants.ORGAN_SELF_REPORT["kidney"] == ["mhoccur_rnl"]
    assert set(constants.ORGAN_SELF_REPORT["heart"]) == {"mhoccur_mi", "mhoccur_cvdot"}
    # E0.GATE rejected the broad proxies outright -- they stay out of the
    # mapping entirely, not even as a sensitivity comparator.
    for proxy in constants.NERVE_PROXY_ITEMS_REJECTED:
        assert not any(proxy in items for items in constants.ORGAN_SELF_REPORT.values())


# ── Threshold flags ─────────────────────────────────────────────────────

def test_missing_score_is_not_a_negative_screen():
    flags = cohort._threshold_flag(pd.Series([12.0, 4.0, np.nan, 10.0]),
                                   constants.CESD_CUTOFF)
    assert flags.iloc[0] == 1.0
    assert flags.iloc[1] == 0.0
    assert pd.isna(flags.iloc[2])   # not 0.0
    assert flags.iloc[3] == 1.0     # cutoff is inclusive


# ── Saving results ──────────────────────────────────────────────────────

@pytest.fixture
def clean_log():
    """Restore RESULTS_LOG.md and remove test artifacts afterwards."""
    from aireadi import results
    path = results.log_path("p1")
    original = path.read_text(encoding="utf-8")
    written: list = []
    yield written
    path.write_text(original, encoding="utf-8")
    for p in written:
        if p is not None:
            p.unlink(missing_ok=True)


def test_refuses_to_save_participant_level_table(clean_log):
    """The last line of defence before a per-person table lands in results/."""
    from aireadi import results

    leaky = pd.DataFrame({"person_id": [1001, 1002], "troponin": [15.0, 3.0]})
    with pytest.raises(ValueError, match="participant-level"):
        results.save("E9.9", leaky, paper="p1", method="m", result="r",
                     decision="keep")

    assert not (results.results_dir("p1") / "E9_9.csv").exists()


def test_save_table_writes_file_and_logs(clean_log):
    from aireadi import results

    table = pd.DataFrame({"organ": ["kidney"], "pct": [72.1]}).set_index("organ")
    path = results.save("E1.2", table, paper="p1", method="Unrecognized per organ",
                        result="Kidney 72.1%", decision="keep", name="by_organ")
    clean_log.append(path)

    assert path.name == "E1_2_by_organ.csv"
    assert path.exists()

    text = results.log_path("p1").read_text(encoding="utf-8")
    assert "**Result:** Kidney 72.1%" in text
    assert "| E1.2 | done |" in text          # status row updated
    assert "`results/E1_2_by_organ.csv`" in text


def test_null_result_is_logged_without_an_artifact(clean_log):
    from aireadi import results

    results.log("E2D.1", paper="p1", method="Garmin vs damage",
                result="Nothing survives adjustment", decision="kill")

    text = results.log_path("p1").read_text(encoding="utf-8")
    assert "**Output:** none" in text
    assert "| E2D.1 | done | — |" in text


def test_pipe_in_a_result_cannot_break_the_status_table(clean_log):
    from aireadi import results

    results.log("E1.5", paper="p1", method="Threshold sweep",
                result="rho 0.2 | p 0.03", decision="keep")

    row = next(l for l in results.log_path("p1").read_text().splitlines()
               if l.startswith("| E1.5 |"))
    assert r"rho 0.2 \| p 0.03" in row              # the pipe was escaped
    cells = re.split(r"(?<!\\)\|", row)[1:-1]       # split on unescaped pipes only
    assert len(cells) == 5                          # table structure intact


def test_unknown_paper_is_rejected():
    from aireadi import results

    with pytest.raises(ValueError, match="paper must be one of"):
        results.results_dir("p3")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
