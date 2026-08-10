"""Canonical constants for the AI-READI analysis project.

Everything here is dataset fact, not analysis choice. Analysis choices
(thresholds, covariates) belong in each paper's PRESPEC.md.

See docs/CAVEATS.md for why several of these exist.
"""

from __future__ import annotations

# ── Dataset identity ────────────────────────────────────────────────────
# Standardised August 2026. The EDA-era notebooks used two different study
# IDs; only this one is correct. The old one (00b62456-...) is wrong.
STUDY_ID = "1438dd73-c4cb-48b8-8fa8-c858771207c3"
CONTAINER_NAME = "aireadi-container"
DATASET_VERSION = "3.0.0"

DATASET_ROOT = f"{STUDY_ID}/dataset"

# ── Blob paths ──────────────────────────────────────────────────────────
PATHS = {
    "participants": f"{DATASET_ROOT}/participants.tsv",
    "dataset_description": f"{DATASET_ROOT}/dataset_description.json",
    "person": f"{DATASET_ROOT}/clinical_data/person.csv",
    "observation": f"{DATASET_ROOT}/clinical_data/observation.csv",
    "measurement": f"{DATASET_ROOT}/clinical_data/measurement.csv",
    "condition_occurrence": f"{DATASET_ROOT}/clinical_data/condition_occurrence.csv",
    "procedure_occurrence": f"{DATASET_ROOT}/clinical_data/procedure_occurrence.csv",
    "visit_occurrence": f"{DATASET_ROOT}/clinical_data/visit_occurrence.csv",
    "manifest_cgm": f"{DATASET_ROOT}/wearable_blood_glucose/manifest.tsv",
    "manifest_activity": f"{DATASET_ROOT}/wearable_activity_monitor/manifest.tsv",
    "manifest_ecg": f"{DATASET_ROOT}/cardiac_ecg/manifest.tsv",
    "manifest_environment": f"{DATASET_ROOT}/environment/manifest.tsv",
}

# ── Severity groups ─────────────────────────────────────────────────────
# Ordered healthy -> insulin. Expected Ns are the v3.0.0 release counts and
# are asserted in QC; a mismatch means the wrong container or a new release.
GROUP_ORDER = ["Healthy", "Pre-DM", "Oral Med", "Insulin"]
GROUP_CODE_TO_LABEL = {0: "Healthy", 1: "Pre-DM", 2: "Oral Med", 3: "Insulin"}
EXPECTED_GROUP_N = {"Healthy": 776, "Pre-DM": 560, "Oral Med": 686, "Insulin": 258}
EXPECTED_TOTAL_N = 2280

# Raw participants.tsv strings -> ordinal code. Keys are lowercased/stripped.
GROUP_STR_TO_CODE = {
    "healthy": 0,
    "prediabetes": 1,
    "pre-diabetes": 1,
    "pre_diabetes": 1,
    "pre_diabetes_lifestyle_controlled": 1,
    "oral medication": 2,
    "oral_medication": 2,
    "non-insulin": 2,
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": 2,
    "insulin": 3,
    "insulin-dependent": 3,
    "insulin_dependent": 3,
    "insulin_controlled": 3,
}

GROUP_COLORS = {
    "Healthy": "#66C2A5",
    "Pre-DM": "#4DAFFA",
    "Oral Med": "#F5A623",
    "Insulin": "#E8413E",
}

# ── Survey special codes ────────────────────────────────────────────────
# 555 = not asked / not applicable, 777 = refused / don't know, 99 = sentinel.
# These are NOT data. Averaging them in silently corrupts every downstream
# score -- this is exactly what happened in the deleted EDA notebooks, which
# scrubbed only 99 and produced a discrimination score with max = 777.
SURVEY_SPECIAL_CODES = (555, 777, 99)

# ── Canonical source-value keys ─────────────────────────────────────────
# measurement.csv (measurement_source_value, text before the first comma)
MEASUREMENT_KEYS = {
    "hba1c": "import_hba1c",       # NOT lbscat_a1c (that is CBC haemoglobin, g/dL)
    "bmi": "bmi_vsorres",          # direct value, not computed from height/weight
    "moca_total": "moca_total_score",
}

# observation.csv (observation_source_value, text before the first comma)
OBSERVATION_KEYS = {
    "cesd_total": "cestl",         # CES-D-10 total, 0-30, screen-positive >= 10
    "paid_total": "paidscore",     # PAID-5, raw 0-20, cutoff >= 8
    "education_years": "years_of_education",
}

CESD_ITEMS = [f"ces{i}" for i in range(1, 11)]
CESD_CUTOFF = 10          # >= 10 screens positive
CESD_MAX = 30
PAID5_CUTOFF = 8          # >= 8 on the raw 0-20 scale
PAID5_MAX = 20

# CES-D items ces5 and ces8 are positive-affect items, but AI-READI stores
# them ALREADY reverse-scored: the plain sum of the 10 raw items reproduces
# `cestl` exactly. Applying (3 - x) here double-reverses and corrupts the
# score. Verified against cestl during the EDA.
CESD_ALREADY_REVERSED = ("ces5", "ces8")

# Correct PhenX SDOH item families. The deleted notebooks built three of
# these by positionally slicing the pxrd* (racial discrimination) battery on
# an alphabetically sorted list -- every SDOH result from that era is an
# artifact. Use these prefixes, never positional slices.
PHENX_FAMILIES = {
    "food_insecurity": "pxfi",          # pxfi1-5
    "housing_insecurity": "pxhi",       # pxhi1-2
    "healthcare_access": "pxahc",       # pxahc1-10
    "clinician_discrimination": "pxdhc",  # pxdhc1-7
    "prescription_affordability": "pxpa",  # pxpa1-4
    "insurance_type": "pxhic",          # pxhic1-8
    "neighborhood": "pxne",             # pxne1-17
    "racial_discrimination": "pxrd",    # the battery the EDA mis-sliced
}

# Medical-history items. `mhoccur_yn` is a gate question, not a disease, and
# `mhoccur_fallot` is a fall COUNT, not a binary flag -- both must be excluded
# from any comorbidity tally.
MHOCCUR_PREFIX = "mhoccur"
MHOCCUR_EXCLUDE = ("mhoccur_yn", "mhoccur_fallot")

# `mhoccur_plm` is broad chronic pulmonary disease, NOT asthma.

# ── Laboratory handling ─────────────────────────────────────────────────
# Rows below the assay's detection limit carry this operator. Ignoring it
# makes every heart-injury count wrong.
OPERATOR_BELOW_DETECTION = 4171756

# Physiologic plausibility bounds, applied before any aggregation.
PLAUSIBLE_RANGES = {
    "hba1c": (3.0, 20.0),
    "bmi": (10.0, 80.0),
    "glucose_mg_dl": (40.0, 400.0),
}

# ── Garmin wearable error codes ─────────────────────────────────────────
# The device writes these instead of nulls. Averaging them in drags every
# summary toward zero.
GARMIN_ERROR_CODES = {
    "average_heartrate_bpm": 0,
    "average_oxygen_saturation_pct": 0,
    "average_stress_level": -2,
    "average_respiratory_rate_bpm": -2,
}

# `average_sleep_hours` in the manifest is a FRACTION OF A DAY -- multiply by 24.
SLEEP_FRACTION_TO_HOURS = 24

# Respiratory rate reads 6-9 against an expected 12-20. Device quirk, not
# physiology: use for relative comparison only, never as an absolute value.
RESPIRATORY_RATE_IS_RELATIVE_ONLY = True

# ── Environmental sensors ───────────────────────────────────────────────
# One sensor logged 1,145 C. Anything at or above this bound is broken.
IMPLAUSIBLE_TEMPERATURE_C = 100.0

# PM2.5 has a very long tail (median ~3, max ~1,178 ug/m3): log-transform or
# use medians. A raw mean is meaningless.
PM25_NEEDS_LOG = True

# ── CGM ─────────────────────────────────────────────────────────────────
CGM_TIR_LOW = 70          # mg/dL
CGM_TIR_HIGH = 180
CGM_SEVERE_HIGH = 250
CGM_INTERVAL_MINUTES = 5  # Dexcom G6 sampling interval
CGM_MIN_READINGS = 12     # < 1 hour of data is not usable

# ── Clinical sites ──────────────────────────────────────────────────────
SITES = ["UW", "UAB", "UCSD"]
