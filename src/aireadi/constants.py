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

# ── Paper 1 organ-damage markers ────────────────────────────────────────
# Confirmed by E0.1 against measurement.csv (2026-08-11). Do not guess these:
# `import_albumin` is SERUM albumin in g/dL and is NOT the kidney marker --
# the kidney marker is the urine albumin-to-creatinine ratio built from the
# two `import_urine_*` fields, which share units so the ratio is valid.
P1_MEASUREMENT_KEYS = {
    "urine_albumin": "import_urine_albumin",       # n=2226
    "urine_creatinine": "import_urine_creatinine",  # n=2226
    "troponin_t": "import_troponin_t",             # n=2233, 712 below detection
    "monofilament_left": "msslffl",                # n=2268, sites felt 0-10
    "monofilament_right": "mssrffl",               # n=2268, sites felt 0-10
}

# Urine albumin and creatinine are reported in the same units, so
# albumin/creatinine * 1000 yields ACR in mg/g. Sanity: median 7.0 mg/g,
# and ACR >= 30 reproduces the documented 320-participant kidney spot-check.
ACR_UNIT_SCALE = 1000

# Sites felt per foot on the monofilament exam. 10 = full protective sensation.
MONOFILAMENT_MAX_SITES = 10

# hs-cTnT limit of detection: below-detection rows are reported AT 6 ng/L and
# carry OPERATOR_BELOW_DETECTION. That value is a limit, not a reading.
TROPONIN_LOD_NG_L = 6.0
# The assay's own reported upper reference limit (measurement.range_high).
# Guideline 99th-percentile cutoffs are sex-specific and the public release has
# no sex variable -- final thresholds are a PRESPEC decision, swept in E1.5.
TROPONIN_ASSAY_URL_NG_L = 16.0

# ── Organ -> self-report comparator ─────────────────────────────────────
# Confirmed by E0.2 against the 30-item mhoccur battery and
# condition_occurrence.csv. Responses are 0/1 with 777 = refused.
#
# NERVE HAS NO COMPARATOR. The battery contains no neuropathy, numbness or
# foot-sensation item; the nearest keys are `mhoccur_cns` ("Other neurological
# conditions", which also covers the separately-listed MS/Parkinson's/dementia)
# and `mhoccur_circ` ("Circulation problems", which is vascular, not neural).
# Neither is a defensible comparator. This triggered the Phase 0 gate; Evan
# resolved it on 2026-08-11 (logged as E0.GATE): nerve is retained for measured
# prevalence, multi-organ counts and the Aim 2 depression analysis, and is
# excluded from the unrecognized fraction, which covers kidney and heart only.
ORGAN_SELF_REPORT = {
    "kidney": ["mhoccur_rnl"],              # "Kidney problems", 246 yes
    "heart": ["mhoccur_mi", "mhoccur_cvdot"],  # "Heart attack" 124, "Other heart issues" 317
    "nerve": [],                            # none exist -- see above
}

# Broad neuro/vascular items that look like a nerve comparator and are not.
# Recorded so nobody rediscovers them and reaches for them; the E0.GATE
# decision is that they are not used at all, not even as a sensitivity check.
NERVE_PROXY_ITEMS_REJECTED = ["mhoccur_cns", "mhoccur_circ"]

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

# Dropping the exact error codes is NOT enough. The manifest's averages were
# computed upstream WITH the error codes included, so the contamination is baked
# into the mean rather than sitting at the sentinel value: 12 participants carry a
# resting heart rate under 30 bpm (the lowest is 0.03), 113 carry a NEGATIVE stress
# score on a 0-100 scale, and one sleep average implies a fraction of a day above
# 1.4. A mean of -1.19 on a 0-100 scale can only arise if most contributing
# readings were the -2 sentinel. Found in E2D.1, 17 Aug 2026.
#
# So plausibility bounds are applied after the sentinel scrub. Values outside the
# instrument's own scale are invalid by definition; the physiological bounds are
# deliberately generous, meant to catch contaminated averages rather than to
# trim a distribution. A zero step count or zero sleep average is "device not
# worn", not a participant who took no steps for sixteen days.
GARMIN_PLAUSIBLE_RANGES = {
    "average_heartrate_bpm": (30.0, 120.0),      # multi-day resting average
    "average_stress_level": (0.0, 100.0),        # Garmin's own scale
    "average_sleep_hours": (1.0, 14.0),          # after the x24 conversion
    "average_oxygen_saturation_pct": (70.0, 100.0),
    "average_daily_activity": (1.0, 50000.0),    # steps; 0 means not worn
}

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

# The Dexcom G6 reports only between 40 and 400 mg/dL. Outside that it writes the
# STRINGS "Low" and "High" into `blood_glucose.value` instead of a number, and
# 39,632 readings across 495 participants (22% of the cohort) are one of those two
# tokens -- 34,449 "High" and 5,183 "Low".
#
# These are CENSORED values, not missing ones: the same situation as the troponin
# below-detection rows, and it must be handled as deliberately. A `float(value)`
# that skips them silently drops readings from precisely the participants with the
# worst control -- one participant has 2,258 of 2,568 readings recorded as "High",
# and two participants are lost entirely because nothing numeric survives. The
# resulting mean, CV, MAGE and time-above-range are all biased, and biased hardest
# where glycaemia matters most for organ damage.
#
# Substituting the reportable-range boundary is the standard convention and is
# conservative for time-above-range (a "High" is at least 400). It understates
# variability, which is the honest direction: a censored excursion cannot have its
# true amplitude recovered. Found 17 Aug 2026 while building E2A.1's CGM metrics.
CGM_SENTINEL_VALUES = {"high": 400.0, "low": 40.0}
CGM_REPORTABLE_RANGE = (40.0, 400.0)

# ── Clinical sites ──────────────────────────────────────────────────────
SITES = ["UW", "UAB", "UCSD"]
