# AI-READI Dataset Introduction & Background

**Comprehensive reference guide for understanding the AI-READI diabetes dataset and medical context**

---

## Table of Contents

1. [Diabetes & Medical Background](#diabetes--medical-background)
2. [AI-READI Dataset Overview](#ai-readi-dataset-overview)
3. [Data Structure & Organization](#data-structure--organization)
4. [Quick Reference Tables](#quick-reference-tables)
5. [Glossary](#glossary)

---

## Diabetes & Medical Background

### Understanding Type 2 Diabetes

**Type 2 Diabetes (T2D)** is a chronic metabolic disorder characterized by:

- **Insulin resistance**: Body cells don't respond properly to insulin, the hormone that regulates blood sugar
- **Beta-cell dysfunction**: Over time, the pancreas can't produce enough insulin to overcome resistance
- **Hyperglycemia**: Chronically elevated blood glucose levels damage organs and tissues

**Normal Glucose Ranges:**
- **Fasting glucose**: 70-100 mg/dL (healthy)
- **Postprandial** (after meals): < 140 mg/dL (healthy)
- **Diabetes diagnosis**: Fasting ≥ 126 mg/dL or HbA1c ≥ 6.5%

### Disease Progression

Type 2 diabetes develops progressively through distinct stages:

```
Healthy → Pre-diabetes → T2D (oral meds) → T2D (insulin required)
```

1. **Healthy**: Normal glucose metabolism, insulin sensitivity intact
2. **Pre-diabetes**: Impaired glucose tolerance, often reversible with lifestyle changes
3. **T2D (oral medication)**: Requires pharmacological intervention (Metformin, GLP-1 agonists, SGLT2 inhibitors)
4. **T2D (insulin-dependent)**: Advanced disease, significant beta-cell failure, requires insulin therapy

### Key Complications of Diabetes

Diabetes is a **systemic disease** affecting multiple organ systems:

**Microvascular Complications** (small blood vessels):
- **Retinopathy**: Damage to retinal blood vessels → vision loss → blindness
- **Nephropathy**: Kidney damage → chronic kidney disease → dialysis
- **Neuropathy**: Nerve damage → numbness, pain, loss of sensation (especially feet)

**Macrovascular Complications** (large blood vessels):
- **Cardiovascular disease**: Heart attacks, stroke (2-4x higher risk in diabetics)
- **Peripheral artery disease**: Poor leg circulation → ulcers → amputation risk

**Autonomic Dysfunction**:
- **Cardiac autonomic neuropathy (CAN)**: Affects heart rate variability, prolongs QTc interval
- Increased risk of sudden cardiac death
- Impaired response to hypoglycemia ("hypoglycemia unawareness")

### Why Multi-Modal Data Matters

Diabetes affects multiple organ systems simultaneously, making multi-modal monitoring essential:

1. **Glucose monitoring (CGM)**: Direct measure of glycemic control, the primary target
2. **Cardiac (ECG)**: Detects cardiovascular complications (QTc prolongation, arrhythmias, silent ischemia)
3. **Retinal imaging**: Early detection of microvascular damage before symptoms appear
4. **Activity/sleep monitoring**: Lifestyle factors that directly modulate glucose levels
5. **Clinical labs**: Kidney function, lipids, HbA1c for long-term glucose assessment

**The AI-READI dataset captures all these dimensions simultaneously for each participant!**

---

## Clinical Metrics Explained

### Glucose Metrics (from Continuous Glucose Monitoring)

#### Mean Glucose
- **Definition**: Average blood sugar over the monitoring period
- **Target**: < 154 mg/dL for diabetics
- **Interpretation**: Higher values indicate poor overall control

#### Time in Range (TIR)
- **Definition**: Percentage of time glucose is 70-180 mg/dL
- **Gold standard** for glycemic control quality
- **Target**: > 70% for good control
- **Clinical significance**: Each 5% increase in TIR reduces complications risk
- **Why it matters**: Better predictor of complications than HbA1c alone

#### Time Above Range (TAR)
- **Definition**: Percentage of time glucose > 180 mg/dL (hyperglycemia)
- **Target**: < 25%
- **Associated with**: Microvascular complications (retinopathy, nephropathy, neuropathy)
- **Breakdown**:
  - Level 1 (181-250 mg/dL): Moderate hyperglycemia
  - Level 2 (> 250 mg/dL): Severe hyperglycemia

#### Time Below Range (TBR)
- **Definition**: Percentage of time glucose < 70 mg/dL (hypoglycemia)
- **Target**: < 4% total, < 1% severe (< 54 mg/dL)
- **Dangerous**: Can cause seizures, loss of consciousness, coma
- **Why it matters**: Hypoglycemia is an acute emergency, not just a control metric

#### Coefficient of Variation (CV)
- **Formula**: CV = (standard deviation / mean) × 100%
- **Measures**: Glucose variability/stability
- **Target**: < 36%
- **Interpretation**:
  - High CV = unstable control, "brittle diabetes"
  - Low CV = stable, predictable glucose patterns
  - Higher complication risk with high CV independent of mean glucose

#### Glucose Management Indicator (GMI)
- **Formula**: GMI = 3.31 + 0.02392 × mean_glucose
- **Purpose**: Estimates HbA1c from CGM data
- **Approximates**: 3-month average glucose
- **Units**: Percentage (same as HbA1c)
- **Note**: May differ from lab HbA1c due to individual red blood cell turnover

---

### Cardiac Metrics (from 12-Lead ECG)

#### Heart Rate (HR)
- **Normal resting**: 60-100 beats per minute (bpm)
- **In diabetes**: Often elevated due to autonomic dysfunction
- **Significance**: Persistent tachycardia may indicate cardiac autonomic neuropathy

#### QT Interval
- **Definition**: Duration of ventricular depolarization + repolarization
- **Measured in**: Milliseconds (ms)
- **Represents**: Total time for heart ventricles to contract and recover

#### QTc (Corrected QT)
- **Definition**: QT interval adjusted for heart rate (using Bazett's or Fridericia formula)
- **Critical safety metric** for arrhythmia risk
- **Normal values**:
  - Men: < 440 ms
  - Women: < 460 ms
- **Prolonged QTc**: > 450 ms increases risk of:
  - Torsades de pointes (dangerous arrhythmia)
  - Sudden cardiac death
- **Diabetes connection**: T2D is a risk factor for QTc prolongation
- **Why it matters**: Identifies patients at high risk for cardiac events

#### PR Interval
- **Definition**: Time from atrial to ventricular activation
- **Normal range**: 120-200 ms
- **Prolonged PR** (> 200 ms): Indicates heart block (delayed conduction)
- **Short PR** (< 120 ms): May indicate pre-excitation syndromes

#### QRS Duration (QRSD)
- **Definition**: Ventricular depolarization time
- **Normal**: < 120 ms
- **Wide QRS** (≥ 120 ms): Suggests:
  - Bundle branch block
  - Ventricular conduction abnormality
  - Ventricular hypertrophy

#### P/QRS/T Axes
- **Definition**: Electrical axis of heart vectors in degrees
- **Normal P axis**: 0° to +75°
- **Normal QRS axis**: -30° to +90°
- **Normal T axis**: 0° to +90°
- **Abnormal axes**: Suggest structural heart disease, chamber enlargement, or conduction defects

---

## AI-READI Dataset Overview

### What is AI-READI?

**AI-READI** = **Artificial Intelligence Ready and Equitable Atlas for Diabetes Health**

This is an **NIH-funded flagship dataset** (Grant OT2OD032644) designed to enable AI/ML research on Type 2 Diabetes. It's part of the **Bridge2AI initiative**, a national effort to create AI-ready, ethically collected health data with emphasis on equity and diversity.

**Key Dataset Facts:**
- **Participants**: 2,280 individuals across diabetes severity spectrum
- **Collection period**: July 19, 2023 - May 1, 2025
- **Your subset**: 97.54 GB (24,256 files in Azure Blob)
- **Full dataset**: 3.82 TB total (356,343 files)
- **De-identified**: No protected health information (PHI)
  - Sex/gender, race/ethnicity, and medication information removed for privacy
- **Multi-modal**: 6+ different data collection modalities per participant

---

### Data Modalities & Interconnections

The AI-READI dataset captures **comprehensive multi-modal longitudinal data** for each participant:

#### 1. Clinical Data (OMOP CDM Format)

- **Format**: CSV tables following OMOP Common Data Model v5.x standard
- **Purpose**: Standardized clinical phenotyping for interoperability
- **Key Tables**:
  - `person.csv`: Demographics (2,280 participants, year of birth only for privacy)
  - `observation.csv`: Clinical observations, retinal imaging metadata (108 MB)
  - `measurement.csv`: Lab values, vital signs, ophthalmology measurements (35 MB)
  - `condition_occurrence.csv`: Diagnoses and medical conditions
  - `procedure_occurrence.csv`: Medical procedures performed
  - `visit_occurrence.csv`: Study visit records and dates
- **Data Quality**: 589 of 1,241 quality checks passed in DQD report

**What is OMOP CDM?**
- Observational Medical Outcomes Partnership Common Data Model
- Standardizes clinical data structure across institutions
- Enables reproducible research and meta-analyses
- Uses concept IDs from standardized vocabularies (SNOMED, LOINC)

#### 2. Continuous Glucose Monitoring (CGM)

- **Device**: Dexcom G6 continuous glucose monitor
- **Coverage**: 2,245 participants with glucose data
- **Duration**: ~11 days of continuous monitoring per participant
- **Sampling rate**: 5-minute intervals (288 readings per day)
- **Total readings**: ~2,800 glucose measurements per participant
- **Format**: JSON files with timestamp-value pairs
- **Example**: Participant 1001 has average glucose of 123.3 mg/dL over 2,856 readings

**Why CGM vs. fingerstick?**
- Captures glucose dynamics: spikes, dips, variability
- Enables TIR calculation (impossible with discrete measurements)
- Reveals nocturnal patterns often missed
- Reduces patient burden (no painful fingersticks)

#### 3. 12-Lead ECG (Cardiac)

- **Device**: Philips PageWriter TC30 electrocardiograph
- **Format**: WFDB (WaveForm DataBase) - `.hea` header + `.dat` binary
- **Coverage**: 2,257 participants
- **Specifications**:
  - 12 standard leads: I, II, III, aVR, aVL, aVF, V1, V2, V3, V4, V5, V6
  - Sampling rate: 500 Hz
  - Duration: 11 seconds per recording
  - Signal length: 5,500 samples per lead
- **Derived metrics** (in manifest):
  - Heart rate (bpm)
  - PR interval (ms)
  - QRS duration (ms)
  - QT and QTc intervals (ms)
  - P/QRS/T wave axes (degrees)
- **Purpose**: Cardiac health assessment, detect diabetes-related cardiovascular complications

**Why WFDB format?**
- Industry standard for physiological waveforms
- Supported by PhysioNet and PhysioBank
- Excellent Python library support (`wfdb` package)
- Lossless compression of signal data

#### 4. Wearable Activity Monitoring

- **Device**: Garmin fitness trackers
- **Coverage**: 2,184 participants
- **Metrics collected**:
  - Heart rate (continuous)
  - Oxygen saturation (SpO2)
  - Stress levels (HRV-derived)
  - Sleep duration and quality
  - Respiratory rate
  - Physical activity levels
  - Active calories burned
- **Duration**: Multi-day continuous monitoring
- **Format**: JSON time series data

**Why activity matters for diabetes:**
- Physical activity directly lowers glucose
- Sleep quality affects insulin sensitivity
- Stress increases cortisol → hyperglycemia
- Sedentary behavior is independent risk factor

#### 5. Environmental Sensors

- **Device**: Lee Lab Anura environmental sensors
- **Coverage**: 2,231 participants
- **Data collected**:
  - Temperature
  - Humidity
  - Light levels
  - Other environmental conditions
- **File size**: 50-65 MB CSV per participant (dense time series)
- **Purpose**: Environmental context for metabolic variations

**Why environment matters:**
- Temperature affects glucose metabolism
- Seasonal patterns in glycemic control
- Indoor air quality may influence inflammation

#### 6. Retinal Imaging (Ophthalmic)

- **Modalities available**:
  - **Fundus photography**: Color images of retina
  - **OCT** (Optical Coherence Tomography): 3D retinal structure
  - **OCTA** (OCT Angiography): Retinal blood vessel imaging
  - **FLIO** (Fluorescence Lifetime Imaging Ophthalmoscopy): Metabolic imaging
- **Devices**: OptoMed, Eidon UWF systems
- **Purpose**:
  - Diabetic retinopathy detection and staging
  - Microvascular complication assessment
  - Early biomarker discovery
- **Format**: DICOM images + metadata in observation table

**Why retinal imaging?**
- Eyes are "window" to systemic microvascular health
- Diabetic retinopathy is leading cause of blindness
- Can detect damage before symptoms appear
- Non-invasive biomarker for overall diabetic complications

---

### How Data Modalities Interconnect

The dataset uses a **patient-centric multi-modal design**:

```
participants.tsv (Master Index)
    ├── person_id (unique identifier, links all modalities)
    ├── study_group (diabetes severity classification)
    ├── age (at enrollment)
    ├── clinical_site (collection location: UW, UAB, UCSD)
    ├── study_visit_date (temporal anchor)
    └── Data availability flags (TRUE/FALSE for each modality):
        ├── cardiac_ecg
        ├── clinical_data
        ├── wearable_blood_glucose
        ├── wearable_activity_monitor
        ├── environment
        ├── retinal_photography
        ├── retinal_oct
        ├── retinal_octa
        └── retinal_flio

Each modality links to person_id:
    ├── Clinical tables: person.csv, measurement.csv, observation.csv
    │   └── Join on: person_id
    ├── CGM: manifest_wearable_blood_glucose.tsv → JSON files
    │   └── Join on: person_id
    ├── ECG: manifest_cardiac_ecg.tsv → .dat/.hea WFDB files
    │   └── Join on: person_id
    ├── Activity: manifest_wearable_activity_monitor.tsv → JSON files
    │   └── Join on: person_id
    └── Environment: manifest_environment.tsv → CSV files
        └── Join on: person_id
```

**Key Insight**: Each participant has:
- Clinical snapshot (demographics, labs, conditions) - **CROSS-SECTIONAL**
- Continuous glucose time series (~11 days) - **LONGITUDINAL**
- Single ECG recording (11 seconds) - **SNAPSHOT**
- Multi-day wearable sensor data - **LONGITUDINAL**
- Environmental monitoring period - **LONGITUDINAL**
- Retinal imaging session - **SNAPSHOT**

This enables both **cross-sectional** (comparing participants) and **longitudinal** (tracking individuals over time) analyses.

---

### Study Groups & Diabetes Severity

Participants in `participants.tsv` are categorized into **4 diabetes severity groups**:

1. **healthy**
   - No diabetes diagnosis
   - Normal glucose metabolism
   - Control group for comparison

2. **pre_diabetes_lifestyle_controlled**
   - Prediabetes (impaired glucose tolerance)
   - Managed without medication
   - Lifestyle interventions (diet, exercise)

3. **oral_medication_and_or_non_insulin_injectable_medication_controlled**
   - Type 2 diabetes diagnosis
   - Treated with oral medications (e.g., Metformin, sulfonylureas)
   - And/or non-insulin injectables (e.g., GLP-1 receptor agonists)

4. **insulin_controlled**
   - Type 2 diabetes requiring insulin therapy
   - Most advanced disease stage in this cohort
   - May also be on oral medications

**This stratification is CRITICAL for ML modeling!**
- Enables supervised learning (predict group from features)
- Allows within-group and between-group comparisons
- Tests whether glucose patterns differ by treatment type vs. disease severity

---

### What Makes This Dataset AI-Ready?

The AI-READI dataset was specifically designed for machine learning:

1. **Standardization**
   - OMOP CDM for clinical data (interoperability)
   - WFDB for ECG (PhysioNet compatibility)
   - JSON for wearable/sensor data (easy parsing)

2. **Rich Metadata**
   - Manifest files link all modalities with quality metrics
   - Dataset description JSON documents structure
   - Data quality dashboard (DQD) reports completeness

3. **Temporal Alignment**
   - Study visit dates enable cross-modal synchronization
   - Timestamp data in sensor streams allows precise alignment

4. **Completeness Tracking**
   - Boolean flags indicate which modalities exist per participant
   - Missing data patterns are documented
   - Enables stratified sampling and missing data imputation

5. **Multi-modal Integration**
   - Enables fusion models: glucose + ECG + activity → predictions
   - Tests whether multi-modal features outperform single-modality
   - Supports transfer learning across modalities

6. **Equity Focus**
   - Diverse participant population (though demographics removed in public version)
   - Multiple clinical sites for generalizability
   - Explicit attention to health disparities

---

## Data Structure & Organization

### Patient-Centric Design

**Every data file links back to a `person_id`**, creating a hub-and-spoke structure:

```
person_id: 1001
    ├── participants.tsv → age: 69, study_group: pre_diabetes_lifestyle_controlled
    ├── person.csv → year_of_birth: 1948 (OMOP clinical)
    ├── measurement.csv → visual acuity scores, vitals (OMOP clinical)
    ├── observation.csv → retinal imaging metadata (OMOP clinical)
    ├── 1001_DEX.json → 2,856 glucose readings, avg: 123.3 mg/dL
    ├── 1001_ecg_25aafb4b.dat/hea → 12-lead ECG, HR: 60 bpm, QTc: 403 ms
    ├── 1001_ENV.csv → Environmental sensor time series
    └── Wearable activity data → Heart rate, sleep, activity levels
```

### File Formats and Locations

**In Azure Blob Storage**, the directory structure is:

```
00b62456-0b93-4975-a992-42ba6a50ed5c/  (study ID)
└── dataset/
    ├── clinical_data/              # OMOP CDM CSV tables
    │   ├── person.csv
    │   ├── observation.csv
    │   ├── measurement.csv
    │   ├── condition_occurrence.csv
    │   ├── procedure_occurrence.csv
    │   └── visit_occurrence.csv
    │
    ├── cardiac_ecg/
    │   └── ecg_12lead/
    │       └── philips_tc30/
    │           ├── 1001/
    │           │   ├── 1001_ecg_25aafb4b.hea
    │           │   └── 1001_ecg_25aafb4b.dat
    │           ├── 1002/
    │           └── ...
    │
    ├── wearable_blood_glucose/
    │   └── continuous_glucose_monitoring/
    │       └── dexcom_g6/
    │           ├── 1001/1001_DEX.json
    │           ├── 1002/1002_DEX.json
    │           └── ...
    │
    ├── wearable_activity_monitor/
    │   └── garmin_*/
    │       ├── {person_id}/
    │       │   ├── heartrate.json
    │       │   ├── sleep.json
    │       │   ├── activity.json
    │       │   └── ...
    │       └── ...
    │
    ├── environment/
    │   └── environmental_sensor/
    │       └── leelab_anura/
    │           ├── 1001/1001_ENV.csv
    │           └── ...
    │
    ├── retinal_photography/
    ├── retinal_oct/
    ├── retinal_octa/
    ├── retinal_flio/
    │
    ├── participants.tsv            # Master participant index
    ├── dataset_description.json    # Study metadata
    ├── manifest.tsv                # File catalog (multiple per modality)
    └── dqd_omop.json              # Data quality report
```

### Manifest Files Explained

**Manifests are TSV files that catalog and describe data files for each modality.**

**Purpose:**
- Link person_id to file paths
- Provide derived summary statistics (avoid downloading raw files)
- Document quality metrics
- Enable rapid data exploration without downloading large files

**Examples:**

**manifest_wearable_blood_glucose.tsv:**
```
person_id | glucose_filepath | glucose_level_record_count | average_glucose_level_mg_dl | glucose_sensor_sampling_duration_days
1001      | /path/1001_DEX.json | 2856 | 123.30 | 11
```

**manifest_cardiac_ecg.tsv:**
```
person_id | wfdb_hea_filepath | wfdb_dat_filepath | Rate | QTc | PR | QRSD | manufacturer
1001      | /path/1001.hea | /path/1001.dat | 60 | 403 | 159 | 85 | Philips
```

**How to use manifests:**
1. Download manifest TSV files first (small, fast)
2. Analyze summary statistics without downloading raw data
3. Identify interesting participants based on metrics
4. Download only selected raw files for detailed analysis

---

## Quick Reference Tables

### Glucose Ranges and Targets

| Metric | Healthy | Pre-diabetes | Diabetes | Target (Diabetes Mgmt) |
|--------|---------|--------------|----------|------------------------|
| **Fasting Glucose** | 70-100 mg/dL | 100-125 mg/dL | ≥ 126 mg/dL | 80-130 mg/dL |
| **Postprandial (2hr)** | < 140 mg/dL | 140-199 mg/dL | ≥ 200 mg/dL | < 180 mg/dL |
| **HbA1c** | < 5.7% | 5.7-6.4% | ≥ 6.5% | < 7% (individualized) |
| **Mean Glucose (CGM)** | 70-120 mg/dL | 100-140 mg/dL | Variable | < 154 mg/dL |
| **Time in Range (TIR)** | > 90% | 70-90% | Variable | > 70% |
| **Time Above Range (TAR)** | < 5% | 5-15% | Variable | < 25% |
| **Time Below Range (TBR)** | < 1% | < 2% | Variable | < 4% (< 1% severe) |
| **CV (Variability)** | < 30% | 30-35% | Variable | < 36% |

### ECG Normal Values

| Parameter | Normal Range | Borderline | Abnormal | Clinical Significance |
|-----------|--------------|------------|----------|----------------------|
| **Heart Rate** | 60-100 bpm | 50-60 or 100-110 | < 50 or > 110 | Bradycardia / Tachycardia |
| **PR Interval** | 120-200 ms | 200-220 ms | > 220 ms | Heart block (delayed AV conduction) |
| **QRS Duration** | < 120 ms | 120-140 ms | > 140 ms | Bundle branch block |
| **QT Interval** | < 400-460 ms (HR-dependent) | - | > 500 ms | Arrhythmia risk |
| **QTc (Men)** | < 440 ms | 440-450 ms | > 450 ms | Prolonged QTc → sudden death risk |
| **QTc (Women)** | < 460 ms | 460-470 ms | > 470 ms | Prolonged QTc → sudden death risk |
| **P Axis** | 0° to +75° | -30° to 0° | < -30° or > +75° | Atrial abnormality |
| **QRS Axis** | -30° to +90° | +90° to +110° | > +110° or < -30° | Right/left axis deviation |

### Clinical Interpretation Guidelines

**Glucose Control Quality (based on TIR):**
- **Excellent**: TIR > 85%, TAR < 10%, TBR < 2%
- **Good**: TIR 70-85%, TAR 10-25%, TBR 2-4%
- **Fair**: TIR 50-70%, TAR 25-40%, TBR 4-6%
- **Poor**: TIR < 50%, TAR > 40%, or TBR > 6%

**Glucose Variability (based on CV):**
- **Stable**: CV < 30%
- **Moderate variability**: CV 30-36%
- **High variability ("brittle")**: CV > 36%

**Cardiac Risk (based on QTc):**
- **Normal**: QTc < 440 ms (men), < 460 ms (women)
- **Borderline**: QTc 440-450 ms (men), 460-470 ms (women)
- **Prolonged (moderate risk)**: QTc 450-500 ms
- **Severely prolonged (high risk)**: QTc > 500 ms

---

## Glossary

**AI-READI**: Artificial Intelligence Ready and Equitable Atlas for Diabetes Health - NIH-funded dataset

**Beta-cell**: Insulin-producing cells in the pancreas; dysfunction leads to diabetes

**Bridge2AI**: NIH initiative to create AI-ready biomedical datasets with equity focus

**CGM**: Continuous Glucose Monitoring - sensor that measures glucose every 5 minutes

**CV (Coefficient of Variation)**: (Standard deviation / Mean) × 100%; measures glucose variability

**Dexcom G6**: Specific CGM device model used in AI-READI dataset

**DICOM**: Digital Imaging and Communications in Medicine - standard for medical images

**GMI (Glucose Management Indicator)**: Estimated HbA1c calculated from CGM mean glucose

**HbA1c**: Hemoglobin A1c - 3-month average blood sugar (glycated hemoglobin percentage)

**Hyperglycemia**: High blood sugar (> 180 mg/dL)

**Hypoglycemia**: Low blood sugar (< 70 mg/dL); dangerous acute condition

**Insulin Resistance**: Reduced cellular response to insulin, requiring more insulin for same effect

**OMOP CDM**: Observational Medical Outcomes Partnership Common Data Model - standardizes clinical data

**QTc**: Heart rate-corrected QT interval; critical cardiac safety metric

**TAR (Time Above Range)**: % of CGM readings > 180 mg/dL (hyperglycemia)

**TBR (Time Below Range)**: % of CGM readings < 70 mg/dL (hypoglycemia)

**TIR (Time in Range)**: % of CGM readings 70-180 mg/dL; gold standard for glycemic control

**Type 2 Diabetes (T2D)**: Chronic metabolic disease with insulin resistance and/or beta-cell dysfunction

**WFDB**: WaveForm DataBase format - standard for physiological signals (ECG, EEG, etc.)

---

## Additional Resources

**AI-READI Project:**
- Official website: https://aireadi.org/
- Documentation: https://docs.aireadi.org/
- Dataset on FAIRhub: https://doi.org/10.60775/fairhub.3

**Clinical Standards:**
- OMOP CDM: https://ohdsi.github.io/CommonDataModel/
- CGM Guidelines: https://diabetesjournals.org/care/article/42/8/1593/36502
- WFDB: https://wfdb.readthedocs.io/

**Diabetes Education:**
- American Diabetes Association: https://diabetes.org/
- CGM Interpretation: Time in Range Consensus
- Cardiac Complications: Diabetic Cardiac Autonomic Neuropathy Reviews

---

**Document Version**: 1.0
**Last Updated**: January 2026
**For**: AI-READI Dataset v3.0.0 Analysis Project
