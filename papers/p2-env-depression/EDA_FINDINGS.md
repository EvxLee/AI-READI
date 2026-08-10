# AI-READI EDA Findings Report
### Environmental Variables, Wearable Sensor Data, BMI, Clinical Comorbidities & Diabetes Status
*Stratified by Age and Diabetes Severity across Full Cohort (N = 2,231 Environmental / N = 2,280 Clinical / N = 2,273 BMI / N = 2,245 CGM / N = 1,628-2,184 Wearable Activity)*

---

> **Important Epidemiological & Methodological Note:** All statistical significance tests (e.g., p-values, Kruskal-Wallis H-statistics, Spearman correlations) and interpretations reported throughout this document indicate **observational cross-sectional associations/correlations** across participant subgroups. They do **NOT** infer or establish direct causation.

---

## Overview

This report summarizes exploratory analysis of the **AI-READI dataset** (2,280 total participants), covering:
1. Distribution of **environmental sensor variables** across the **full cohort of N = 2,231 participants with complete sensor data** (temperature, humidity, light, PM2.5, VOC, NOx)
2. Distribution of **wearable sensor data** — **continuous glucose monitor (CGM)** readings (Dexcom G6) and **Garmin wearable activity monitor** streams (heart rate, oxygen saturation/SpO2, stress, sleep, respiratory rate, daily steps, active calories) — across the full cohort with available device data
3. Distribution of **BMI** (N = 2,273 with recorded body-mass-index measurements)
4. Distribution and correlation of **clinical comorbidities** with diabetes status (N = 2,280)
5. All findings **stratified by age** (40-54 / 55-69 / 70+) and **diabetes status** (4 groups), and their **12 combinations**
6. A **focused deep-dive** on the relationship between **BMI, physical activity, and indoor pollution (PM2.5)** in the younger (<70), insulin-dependent diabetes subgroup

### Clinical, Environmental, and Wearable Modality Cohort Breakdown

| Diabetes Status | Clinical N=2,280 | Environmental N=2,231 | BMI N=2,273 | CGM N=2,245 | Wearable Activity N=2,184\* | % of Cohort |
|---|---|---|---|---|---|---|
| **Healthy** | 776 | 755 | 773 | 761 | 741 | 33.8% |
| **Controlled Diabetes** *(oral/non-insulin meds)* | 686 | 674 | 685 | 681 | 655 | 30.2% |
| **No Diabetes** *(pre-diabetes, lifestyle-managed)* | 560 | 551 | 558 | 552 | 541 | 24.7% |
| **Insulin Dependent** *(T2D on insulin)* | 258 | 251 | 257 | 251 | 247 | 11.3% |
| **Total** | **2,280** | **2,231** | **2,273** | **2,245** | **2,184** | **100.0%** |

*\* "Wearable Activity N=2,184" reflects participants with the Garmin manifest file present (sleep/active-calories coverage). Individual Garmin streams have somewhat lower non-null coverage due to device dropout: heart rate N=1,999, stress N=1,987, respiratory rate N=1,962, daily steps N=2,141, SpO2 N=1,628 (SpO2 sensors have the highest dropout of all wearable streams).*

| Age Group | Total Participants | Environmental Cohort | % of Cohort |
|---|---|---|---|
| 40-54 | 726 | 712 | 31.9% |
| 55-69 | 1,006 | 983 | 44.1% |
| 70+ | 548 | 536 | 24.0% |

> **Full-Cohort Methodological Note:** Environmental analysis has been scaled to process **all 2,231 available participant environmental files**. Per-participant longitudinal averages were computed across their continuous monitoring periods (millions of readings ingested in parallel). CGM and wearable activity metrics use the **pre-aggregated per-participant summary statistics published in the AI-READI device manifests** (`manifest_wearable_blood_glucose.tsv`, `manifest_wearable_activity_monitor.tsv`), which are themselves derived from each participant's full ~11-day continuous monitoring stream. BMI is drawn from the OMOP `measurement.csv` clinical table (`bmi_vsorres` concept). This eliminates sampling noise and yields true population-level alignment with clinical outcomes.

> **Wearable Data Quality Note:** The Garmin manifest encodes sensor dropout/error readings as sentinel values (`0` for heart rate/SpO2, `-2` for stress/respiratory rate). These were treated as missing rather than real physiological readings before computing statistics below. The manifest's `average_sleep_hours` field is natively a **fraction of the day asleep** (range ~0-1, with a small number of >1 outliers from multi-day aggregation artifacts) rather than literal hours; it has been **converted to hours** (`x 24`) throughout this report for interpretability. The `average_respiratory_rate_bpm` field returns values in the 6-9 range rather than the clinically expected 12-20 breaths/min — this is a known device-native scaling quirk of the Garmin manifest field and is reported as-is (relative/ordinal comparisons across groups remain valid; absolute values should not be read as clinical breaths-per-minute).

---

## Part 1 - Environmental Variable Distributions (Full Cohort N = 2,231)

The Lee Lab Anura sensors recorded ambient temperature, relative humidity, light (lch0 spectral channel), PM2.5 particulate matter, volatile organic compounds (VOC Index), and nitrogen oxides (NOx Index) continuously for each participant.

> **Confirmed Sensor Placement:** All 2,231 environmental sensors were placed **inside participants' homes** (bedroom 767x, living room 706x, home office 74x, dining room 60x, etc.). All readings measure **indoor residential microenvironments**, not outdoor regional weather.

### 1.1 Overall Population Distribution Summary (N = 2,231)

| Variable | Mean | Median | Std | Min | 25% | 75% | Max |
|---|---|---|---|---|---|---|---|
| **Temperature (C)** | 24.35 | 24.22 | 2.60 | 14.98 | 22.69 | 25.87 | 46.26 |
| **Humidity (%)** | 45.93 | 46.10 | 7.88 | 18.62 | 40.70 | 51.57 | 71.02 |
| **Light (lch0, relative)** | 0.009 | 0.001 | 0.036 | 0.000 | 0.000 | 0.006 | 0.826 |
| **PM2.5 (ug/m3)** | 15.21 | 3.03 | 63.65 | 0.00 | 1.49 | 6.62 | 1,178.30 |
| **VOC Index (ppb)** | 103.47 | 94.59 | 39.34 | 28.17 | 77.22 | 117.38 | 286.27 |
| **NOx Index (ppb)** | 1.010 | 0.995 | 0.088 | 0.667 | 0.995 | 0.995 | 3.400 |

*\* Temperature stats clean 1 single sensor hardware glitch artifact (1145 C).*

#### Population-Level Characteristics
- **Indoor Temperature**: Concentrated between 22.7-25.9 C (median 24.22 C), reflecting typical residential heating and cooling preferences across US climate zones.
- **Light Exposure**: Median is 0.001 (lch0 channel, 415nm wavelength relative intensity sampled 24/7). 8+ hours of sleep per night in dark rooms keeps population medians low, while daytime peak readings reach up to 0.826 near windows.
- **PM2.5 Indoor Air Quality**: Highly right-skewed with a population median of **3.03 ug/m3** (clean indoor air). However, acute indoor events (cooking, smoking, window infiltration) create a long upper tail up to 1,178 ug/m3, driving the population mean to 15.21 ug/m3.
- **VOC Index**: Normally distributed around a median of 94.59 ppb (IQR 77-117 ppb), reflecting indoor product usage, ventilation, and off-gassing.
- **NOx Index**: Highly stable baseline (median 0.995 ppb), with occasional spikes up to 3.40 ppb from gas stove combustion or outdoor traffic infiltration.

---

## Part 2 - Environmental Variables by Diabetes Status (Full Cohort N = 2,231)

### 2.1 Population Means, Medians, and Statistical Significance

> **Table Notation Note:** Entries in the table below are presented as **Mean [Median]**. For instance, `23.90 [23.72]` indicates a group Mean of 23.90 and a group Median of 23.72.

| Diabetes Status | N | Temp (C) [Med] | Humidity (%) [Med] | Light [Med] | PM2.5 (ug/m3) [Med] | VOC (ppb) [Med] | NOx (ppb) [Med] |
|---|---|---|---|---|---|---|---|
| **Healthy** | 755 | 23.90 [23.72] | 45.38 [45.45] | 0.009 [0.002] | 13.84 [2.65] | 105.25 [96.22] | 1.013 [0.995] |
| **No Diabetes** | 551 | 24.23 [24.05] | 46.40 [46.26] | 0.009 [0.001] | 13.77 [3.19] | 102.18 [94.58] | 1.006 [0.995] |
| **Controlled Diabetes** | 674 | 24.71 [24.63] | 46.30 [46.52] | 0.008 [0.001] | 14.68 [3.25] | 101.06 [92.77] | 1.008 [0.995] |
| **Insulin Dependent** | 251 | **25.00 [24.91]** | 45.52 [46.19] | 0.008 [0.001] | **24.01 [4.30]** | **107.42 [97.61]** | **1.019 [0.995]** |
| **Statistical Test (Kruskal-Wallis)** | | **H = 60.11, p < 0.0001** | H = 6.49, p = 0.0899 | **H = 9.13, p = 0.0276** | **H = 30.19, p < 0.0001** | H = 3.74, p = 0.2911 | H = 3.76, p = 0.2891 |

#### Observational Population Insights (Associations, Not Causation)

1. **PM2.5 Exposure Associated with Disease Severity (p < 0.0001)**:
   - In the full N=2,231 population, **insulin-dependent participants exhibit significantly higher indoor PM2.5 levels** (mean 24.01 ug/m3, median 4.30 ug/m3) compared to healthy controls (mean 13.84 ug/m3, median 2.65 ug/m3).
   - This statistical association is highly significant ($H = 30.19, p < 0.0001$).
   - **Observational Interpretation**: This correlation reflects an observed pattern in the data — advanced insulin-dependent diabetes correlates with higher indoor particulate accumulation, which may be associated with reduced indoor mobility, home structural factors, or ventilation differences. It does not establish whether PM2.5 exposure causes diabetes progression or vice versa.

2. **Indoor Thermostat Preference Association (p < 0.0001)**:
   - Participants with diabetes show an association with **warmer indoor home environments**: insulin-dependent (median 24.91 C) and controlled diabetes (median 24.63 C) vs. healthy controls (median 23.72 C).
   - This observed difference ($H = 60.11, p < 0.0001$) correlates with known clinical literature regarding altered thermoregulation, peripheral vascular cold sensitivity, and HVAC preferences in diabetic populations.

3. **Light Exposure Correlation (p = 0.0276)**:
   - Healthy controls display a minor positive association with daytime ambient light exposure (median 0.002) relative to diabetic cohorts (median 0.001), associated with differences in daytime mobility or sensor placement relative to natural lighting.

### 2.2 Regional Climate vs. Indoor Sensors

Because all Anura environmental sensors are indoors, indoor temperature measures HVAC preferences rather than outdoor climate. To test the hypothesis that **warmer regional climate reduces outdoor physical activity**, we cross-referenced the `clinical_site` variable (`UW` Seattle, `UAB` Birmingham, `UCSD` San Diego) with continuous glucose monitoring (CGM) and Garmin wearable activity streams across the full N=2,280 cohort — see **Part 4** below, which now incorporates these wearable modalities directly.

---

## Part 3 - Environmental Variables by Age Group (Full Cohort N = 2,231)

### 3.1 Population Means and Medians by Age Stratum

> **Table Notation Note:** Entries in the table below are presented as **Mean [Median]**. For instance, `24.08 [24.03]` indicates an age group Mean of 24.08 and an age group Median of 24.03.

| Age Group | N | Temp (C) [Med] | Humidity (%) [Med] | Light [Med] | PM2.5 (ug/m3) [Med] | VOC (ppb) [Med] | NOx (ppb) [Med] |
|---|---|---|---|---|---|---|---|
| **40-54** | 712 | 24.08 [24.03] | 46.15 [46.17] | 0.008 [0.001] | **19.01 [3.23]** | 104.59 [96.19] | 1.011 [0.995] |
| **55-69** | 983 | **24.42 [24.21]** | 45.93 [46.17] | **0.011 [0.001]** | 15.38 [2.98] | 104.32 [94.26] | 1.008 [0.995] |
| **70+** | 536 | 24.59 [24.50] | 45.62 [45.79] | 0.007 [0.002] | **9.86 [2.94]** | 100.41 [93.77] | 1.014 [0.995] |
| **Statistical Test (Kruskal-Wallis)** | | **H = 11.58, p = 0.0031** | H = 1.08, p = 0.5816 | **H = 16.00, p = 0.0003** | **H = 8.88, p = 0.0118** | H = 2.79, p = 0.2476 | H = 2.76, p = 0.2517 |

#### Observational Population Insights (Associations, Not Causation)

1. **PM2.5 Exposure Inversely Correlated with Age (p = 0.0118)**:
   - Younger adults (40-54) exhibit higher mean indoor PM2.5 (19.01 ug/m3), associated with a gradual reduction in middle age (15.38 ug/m3) and reaching a minimum in seniors 70+ (9.86 ug/m3).
   - This observed pattern correlates with differences in indoor cooking frequency, household density, and ventilation behavior across age brackets.

2. **Thermostat Setting Preference Associated with Age (p = 0.0031)**:
   - Seniors (70+) show a correlation with warmer thermostat preferences (median 24.50 C) relative to younger adults 40-54 (median 24.03 C), associated with age-related changes in metabolic rate and circulation.

3. **Light Exposure Association (p = 0.0003)**:
   - Middle-aged adults (55-69) correlate with higher ambient light exposure (mean 0.011) compared to seniors 70+ (0.007).

---

## Part 4 - Wearable Sensor & BMI Variable Distributions (Full Cohort)

**New in this update.** This section incorporates the two remaining longitudinal wearable modalities in AI-READI — the **Dexcom G6 continuous glucose monitor (CGM)** and the **Garmin wearable activity monitor** — plus **BMI** as a clinical anthropometric variable, alongside age and diabetes status.

### 4.1 Overall Population Distribution Summary

| Variable | N | Mean | Median | Std | Min | 25% | 75% | Max |
|---|---|---|---|---|---|---|---|---|
| **BMI (kg/m²)** | 2,273 | 30.08 | 28.39 | 7.48 | 15.95 | 24.93 | 33.68 | 95.24 |
| **CGM Mean Glucose (mg/dL)** | 2,245 | 135.29 | 124.95 | 34.72 | 67.56 | 113.45 | 145.46 | 310.92 |
| **Heart Rate (bpm)** | 1,999 | 73.71 | 73.91 | 10.82 | 0.03\* | 67.86 | 80.16 | 112.86 |
| **Oxygen Saturation, SpO2 (%)** | 1,628 | 91.44 | 91.54 | 1.87 | 82.64 | 90.20 | 92.68 | 97.67 |
| **Stress Level (index)** | 1,987 | 25.51 | 23.26 | 13.57 | 0.14 | 15.32 | 33.87 | 74.75 |
| **Sleep (hours/night)** | 2,184 | 9.35 | 9.36 | 2.70 | 0.00 | 8.16 | 10.56 | 33.84\*\* |
| **Respiratory Rate (device units)** | 1,962 | 7.52 | 7.67 | 2.61 | 0.06 | 6.05 | 9.17 | 15.99 |
| **Daily Steps (steps/day)** | 2,141 | 6,163.9 | 5,688.5 | 3,846.0 | 0 | 3,793.9 | 7,984.8 | 25,726.5 |
| **Active Calories (kcal/day)** | 2,184 | 199.2 | 177.1 | 150.4 | 0 | 103.5 | 267.7 | 1,640.2 |

*\* Heart rate floor after sentinel-value cleaning; a small number of near-zero residual outliers remain. \*\* Sleep has a small number (n=12, 0.5%) of >18-hour outliers from multi-day aggregation artifacts in the source manifest; median/quartiles are robust to these.*

#### Population-Level Characteristics

- **BMI**: Population median of 28.39 (overweight range) with a heavy right tail to 95.24. **41.3%** of the cohort with a recorded BMI is **obese (≥30)**, 33.0% overweight (25-30), 24.7% normal weight (18.5-25), and 1.0% underweight.
- **CGM Mean Glucose**: Median of 124.95 mg/dL sits above the healthy postprandial target (<140 mg/dL) but reflects a heterogeneous cohort spanning healthy to insulin-dependent participants; right-skewed with a max of 310.92 mg/dL.
- **Wearable Heart Rate**: Median resting/ambulatory average of ~74 bpm, within normal range population-wide.
- **SpO2**: Tight distribution around a median of 91.5%, slightly below the clinical "normal" reference of ≥95% typically quoted for pulse oximetry — consistent with continuous wrist-worn (rather than fingertip) SpO2 sensors, which read systematically lower than clinical pulse oximeters.
- **Sleep**: Median of 9.36 hours/night — on the high end of the recommended 7-9 hour range, though wrist-worn "sleep" staging tends to overestimate total sleep time relative to polysomnography.
- **Daily Steps**: Median of 5,689 steps/day, below the commonly cited 7,500-10,000 steps/day target — consistent with a cohort skewed toward middle-aged/older adults with chronic disease burden.

---

## Part 5 - Wearable Sensor & BMI Variables by Diabetes Status (Full Cohort)

### 5.1 Population Means, Medians, and Statistical Significance

> **Table Notation Note:** Entries below are presented as **Mean [Median]**.

| Diabetes Status | N (BMI) | BMI [Med] | N (CGM) | Glucose (mg/dL) [Med] | HR (bpm) [Med] | SpO2 (%) [Med] | Stress [Med] | Sleep (hrs) [Med] | Resp. Rate [Med] | Steps [Med] | Active kcal [Med] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Healthy** | 773 | 28.24 [26.75] | 761 | 117.99 [115.73] | 72.27 [72.16] | 91.51 [91.62] | 23.24 [21.14] | 9.30 [9.36] | 7.40 [7.58] | 6,208 [5,694] | 198.0 [180.6] |
| **No Diabetes** | 558 | 29.67 [27.92] | 552 | 125.86 [122.42] | 71.80 [72.80] | 91.49 [91.66] | 23.22 [21.00] | 9.31 [9.36] | 7.14 [7.30] | 5,923 [5,711] | 195.3 [179.1] |
| **Controlled Diabetes** | 685 | 31.16 [29.84] | 681 | 147.42 [139.26] | 75.62 [75.91] | 91.44 [91.48] | 28.18 [25.99] | 9.32 [9.36] | 7.75 [7.88] | 6,278 [5,774] | 199.3 [174.0] |
| **Insulin Dependent** | 257 | **33.62 [31.86]** | 251 | **175.59 [168.56]** | **77.28 [77.54]** | 91.14 [91.28] | **30.35 [29.05]** | 9.68 [9.60] | **8.09 [8.28]** | 6,256 [5,265] | 211.1 [160.1] |
| **Kruskal-Wallis** | | **H=140.90, p<0.0001** | | **H=666.60, p<0.0001** | **H=85.82, p<0.0001** | H=6.00, p=0.1117 | **H=75.43, p<0.0001** | H=3.88, p=0.2745 | **H=27.64, p<0.0001** | H=2.62, p=0.4535 | H=2.46, p=0.4821 |

### 5.2 BMI Category Distribution by Diabetes Status

| Diabetes Status | % Normal (18.5-25) | % Overweight (25-30) | % Obese (≥30) | % Underweight (<18.5) |
|---|---|---|---|---|
| **Healthy** | 31.8% | 35.6% | 30.7% | 1.9% |
| **No Diabetes** | 28.1% | 33.7% | 37.3% | 0.9% |
| **Controlled Diabetes** | 19.3% | 31.4% | 49.3% | 0.0% |
| **Insulin Dependent** | **10.5%** | 28.0% | **60.7%** | 0.8% |

#### Observational Population Insights (Associations, Not Causation)

1. **BMI Rises Monotonically with Diabetes Severity (p < 0.0001)**:
   - Median BMI climbs from 26.75 (healthy) → 27.92 (no diabetes/pre-diabetes) → 29.84 (controlled diabetes) → **31.86 (insulin dependent)**.
   - **60.7%** of insulin-dependent participants are obese, roughly double the rate in healthy controls (30.7%), while normal-weight prevalence drops from 31.8% to 10.5%. This mirrors the well-established clinical relationship between adiposity, insulin resistance, and disease progression, and is directionally consistent with the **Part 7 comorbidity finding** that "Obesity" is the 6th most common condition in this cohort (845 participants).

2. **CGM Mean Glucose Confirms Study-Group Labels (p < 0.0001)**:
   - Wearable-derived mean glucose increases sharply with severity (115.73 → 122.42 → 139.26 → **168.56 mg/dL median**), validating that the `study_group` clinical labels track directly with objective, continuously-measured glycemic control — insulin-dependent participants sit well into the hyperglycemic range on average.

3. **Elevated Resting Heart Rate and Stress in More Severe Diabetes (p < 0.0001)**:
   - Both average heart rate (72.2 → 77.3 bpm) and Garmin's HRV-derived stress index (21.1 → 29.1 median) rise with diabetes severity, consistent with the autonomic dysfunction and elevated sympathetic tone described in the clinical literature for advanced T2D (see cardiac autonomic neuropathy background in `AIREADI_INTRO.md`).

4. **SpO2, Sleep Duration, and Daily Steps Show No Significant Group Difference**:
   - Oxygen saturation (p=0.11), sleep hours (p=0.27), daily steps (p=0.45), and active calories (p=0.48) do **not** differ significantly by diabetes status at the population level. Notably, **insulin-dependent participants are not measurably less active (by step count) than healthier groups** in this cohort — a finding revisited in the **Part 10 deep-dive** below, where it turns out to matter for interpreting the BMI/pollution relationship.

---

## Part 6 - Wearable Sensor & BMI Variables by Age Group (Full Cohort)

### 6.1 Population Means and Medians by Age Stratum

| Age Group | N (BMI) | BMI [Med] | N (CGM) | Glucose [Med] | HR [Med] | SpO2 [Med] | Stress [Med] | Sleep (hrs) [Med] | Resp. Rate [Med] | Steps [Med] | Active kcal [Med] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **40-54** | 725 | **31.63 [29.94]** | 716 | 133.74 [122.29] | **76.56 [76.82]** | 91.65 [91.68] | **27.50 [26.03]** | 9.52 [9.60] | 7.32 [7.49] | **7,331 [6,803]** | **233.6 [216.3]** |
| **55-69** | 1,001 | 29.90 [28.34] | 989 | 134.95 [125.21] | 73.42 [73.52] | 91.31 [91.41] | 24.97 [22.77] | 9.33 [9.36] | 7.48 [7.62] | 6,052 [5,613] | 203.4 [178.8] |
| **70+** | 547 | 28.36 [27.36] | 540 | 137.99 [128.91] | 70.33 [70.11] | 91.39 [91.48] | 23.77 [20.43] | 9.14 [9.12] | **7.86 [7.92]** | 4,782 [4,299] | 145.7 [122.7] |
| **Kruskal-Wallis** | | **H=48.17, p<0.0001** | | **H=25.76, p<0.0001** | **H=125.77, p<0.0001** | **H=11.42, p=0.0033** | **H=29.38, p<0.0001** | **H=12.83, p=0.0016** | **H=11.33, p=0.0035** | **H=156.80, p<0.0001** | **H=141.20, p<0.0001** |

#### Observational Population Insights (Associations, Not Causation)

1. **BMI is Highest in the Youngest Age Stratum (p < 0.0001)**:
   - Counter-intuitively, median BMI is highest in the **40-54** group (29.94) and declines with age (28.34 in 55-69, 27.36 in 70+). This is the opposite pattern from PM2.5 by age (Part 3), which also decreases with age — both trends point toward the youngest adult stratum carrying the heaviest combined metabolic/environmental risk burden, explored directly in Part 10.

2. **Physical Activity Declines Sharply with Age (p < 0.0001)**:
   - Daily steps fall by **35%** from the 40-54 group (median 6,803) to 70+ (median 4,299), and active calories fall by **43%** (216 → 123 kcal/day) — the strongest, most monotonic wearable-activity trend in this report. Resting heart rate and stress decline with age as well, plausibly reflecting a mix of true physiological aging (lower sympathetic drive) and more sedentary lifestyles.

3. **CGM Glucose Rises Modestly with Age (p < 0.0001)**, consistent with known age-related declines in glucose tolerance independent of diabetes status.

---

## Part 7 - Clinical Comorbidities (Full Cohort N = 2,280)

### 7.1 Top 20 Conditions Across All Participants

| Rank | Condition | Count (Full Cohort N=2,280) |
|---|---|---|
| 1 | Elevated A1C (elevated blood sugar) | 1,202 |
| 2 | High blood pressure | 1,151 |
| 3 | High blood cholesterol | 1,145 |
| 4 | Arthritis (joint pain) | 941 |
| 5 | Type II Diabetes | 899 |
| 6 | Obesity | 845 |
| 7 | Dry eye (one or both eyes) | 741 |
| 8 | Cataracts (one or both eyes) | 688 |
| 9 | Pre-diabetes | 555 |
| 10 | Urinary problems | 517 |
| 11 | Digestive problems | 516 |
| 12 | Cancer (any type) | 402 |
| 13 | Hearing impairment | 331 |
| 14 | Other heart issues | 317 |
| 15 | Chronic pulmonary (lung) problems | 303 |
| 16 | Osteoporosis | 291 |
| 17 | Kidney problems | 246 |
| 18 | Circulation problems | 204 |
| 19 | Glaucoma | 192 |
| 20 | Other neurological conditions | 179 |

### 7.2 Mean Number of Comorbidities by Diabetes Status

| Diabetes Status | Mean Conditions | Median | Std Dev |
|---|---|---|---|
| **Healthy** | 3.39 | 3.0 | 2.67 |
| **No Diabetes** | 5.54 | 5.0 | 2.75 |
| **Controlled Diabetes** | 6.76 | 6.0 | 2.84 |
| **Insulin Dependent** | **7.75** | 7.0 | 3.24 |

Comorbidity burden increases monotonically with diabetes severity. Insulin-dependent participants carry **more than twice the disease burden** of healthy controls. The **Obesity** condition flag (845 participants, rank 6) is directly corroborated by the objective **BMI data introduced in Part 5** — 60.7% of insulin-dependent participants are BMI-obese.

---

## Part 8 - Stratification by Age Group (Clinical Comorbidities)

### 8.1 Mean Number of Comorbidities by Age

| Age Group | Mean Conditions | Median | Std Dev |
|---|---|---|---|
| **40-54** | 4.03 | 4.0 | 2.74 |
| **55-69** | 5.53 | 5.0 | 3.06 |
| **70+** | **7.09** | 7.0 | 3.31 |

---

## Part 9 - The 12 Combinations: Diabetes Status x Age Group (Full Cohort)

### 9.1 Participant Sample Matrix across All 12 Subgroups

Every single subgroup in the 4 x 3 matrix contains substantial population N:

| Diabetes Status | 40-54 (Env N / Clin N) | 55-69 (Env N / Clin N) | 70+ (Env N / Clin N) |
|---|---|---|---|
| **Healthy** | 272 / 278 | 312 / 322 | 171 / 176 |
| **No Diabetes** | 190 / 194 | 237 / 239 | 124 / 127 |
| **Controlled Diabetes** | 175 / 178 | 326 / 332 | 173 / 176 |
| **Insulin Dependent** | 75 / 76 | 108 / 113 | 68 / 69 |

### 9.2 Mean Clinical Comorbidities — All 12 Combinations

| Diabetes Status | 40-54 | 55-69 | 70+ |
|---|---|---|---|
| **Healthy** | 2.16 | 3.47 | 5.19 |
| **No Diabetes** | 4.34 | 5.60 | 7.27 |
| **Controlled Diabetes** | 5.60 | 6.65 | 8.16 |
| **Insulin Dependent** | 6.41 | 7.95 | **8.91** |

### 9.3 Environmental Metrics — Full Population Matrix across All 12 Subgroups (N = 2,231)

| Diabetes Status x Age Group | Env N | Temp (C) | Humidity (%) | Light (lch0) | PM2.5 (ug/m3) | VOC Index (ppb) | NOx Index (ppb) |
|---|---|---|---|---|---|---|---|
| **Healthy, 40-54** | 272 | 23.49 | 45.93 | 0.009 | 14.74 | 105.22 | 1.016 |
| **Healthy, 55-69** | 312 | 23.98 | 45.41 | 0.010 | 14.88 | 105.96 | 1.006 |
| **Healthy, 70+** | 171 | 24.41 | 44.46 | 0.009 | 10.49 | 103.99 | 1.021 |
| **No Diabetes, 40-54** | 190 | 24.29 | 46.75 | 0.007 | 22.85 | 102.34 | 1.008 |
| **No Diabetes, 55-69** | 237 | 24.05 | 45.99 | 0.012 | 9.84 | 103.01 | 1.005 |
| **No Diabetes, 70+** | 124 | 24.46 | 46.66 | 0.007 | 7.36 | 100.32 | 1.006 |
| **Controlled, 40-54** | 175 | 24.32 | 46.25 | 0.006 | 14.58 | 103.89 | 1.009 |
| **Controlled, 55-69** | 326 | 24.93 | 46.37 | 0.011 | 15.87 | 103.01 | 1.010 |
| **Controlled, 70+** | 173 | 24.69 | 46.20 | 0.005 | 12.53 | 94.51 | 1.002 |
| **Insulin Dependent, 40-54** | 75 | 25.07 | 45.20 | 0.007 | **35.11** | 109.57 | 1.003 |
| **Insulin Dependent, 55-69** | 108 | 24.92 | 45.97 | 0.010 | **27.49** | 106.40 | 1.016 |
| **Insulin Dependent, 70+** | 68 | 25.04 | 45.16 | 0.006 | 5.99 | 106.65 | 1.042 |

### 9.4 BMI — Full Population Matrix across All 12 Subgroups *(New)*

| Diabetes Status x Age Group | N | Mean BMI |
|---|---|---|
| **Healthy, 40-54** | 278 | 28.78 |
| **Healthy, 55-69** | 322 | 28.44 |
| **Healthy, 70+** | 176 | 27.02 |
| **No Diabetes, 40-54** | 194 | 31.38 |
| **No Diabetes, 55-69** | 239 | 28.86 |
| **No Diabetes, 70+** | 127 | 28.58 |
| **Controlled, 40-54** | 178 | 34.25 |
| **Controlled, 55-69** | 332 | 30.97 |
| **Controlled, 70+** | 176 | 28.42 |
| **Insulin Dependent, 40-54** | 76 | **36.61** |
| **Insulin Dependent, 55-69** | 113 | 33.10 |
| **Insulin Dependent, 70+** | 69 | 31.19 |

### 9.5 Daily Steps — Full Population Matrix across All 12 Subgroups *(New)*

| Diabetes Status x Age Group | Mean Daily Steps |
|---|---|
| **Healthy, 40-54** | 7,130 |
| **Healthy, 55-69** | 6,068 |
| **Healthy, 70+** | 4,946 |
| **No Diabetes, 40-54** | 6,799 |
| **No Diabetes, 55-69** | 5,861 |
| **No Diabetes, 70+** | 4,681 |
| **Controlled, 40-54** | 7,967 |
| **Controlled, 55-69** | 6,114 |
| **Controlled, 70+** | 4,795 |
| **Insulin Dependent, 40-54** | **7,958** |
| **Insulin Dependent, 55-69** | 6,226 |
| **Insulin Dependent, 70+** | 4,525 |

#### Key Full-Cohort Matrix Insights

1. **Younger & Middle-Aged Insulin Dependent Subgroups Experience Peak PM2.5**:
   - **Insulin Dependent (40-54)** registers the single highest PM2.5 exposure in the entire matrix (**35.11 ug/m3** across N=75 participants).
   - **Insulin Dependent (55-69)** follows closely at **27.49 ug/m3** (N=108).
   - This confirms an observed correlation: younger/middle-aged patients with severe, insulin-dependent diabetes correlate with higher indoor particulate pollution exposure.

2. **The Same Subgroup Also Carries the Highest BMI in the Entire Matrix**:
   - **Insulin Dependent, 40-54** has the highest mean BMI of all 12 subgroups (**36.61**, class II obesity), directly co-located with the peak PM2.5 exposure cell above. Both extremes converge on the identical cell — see **Part 10** for a within-subgroup test of whether these two variables are actually *correlated with each other* (they are not, once tested directly at the individual level).

3. **Daily Steps Do NOT Mirror the BMI/PM2.5 Pattern**:
   - The Insulin Dependent, 40-54 cell has the *highest* mean step count (7,958) of the four insulin-dependent age strata, and is comparable to or higher than the same-age Healthy (7,130) and No-Diabetes (6,799) cells. **Elevated BMI and PM2.5 in this subgroup are not accompanied by low measured physical activity** at the group level — an important nuance for the deep-dive below.

4. **Thermostat Preference Correlation**:
   - Across all age strata (40-54, 55-69, 70+), insulin-dependent diabetics maintain tight indoor home temperatures (~24.9 - 25.1 C), higher than healthy controls of the same age.

---

## Part 10 - Deep Dive: BMI, Physical Activity, and Pollution in the Insulin-Dependent, Age < 70 Subgroup *(New)*

This section directly tests the hypothesis motivating this update: **is there a relationship between high BMI, low physical activity, and indoor pollution exposure, specifically within the younger (<70), insulin-dependent diabetes group?** This group (N=189, combining the 40-54 and 55-69 insulin-dependent strata) represents the most clinically advanced, working-age diabetic population in the cohort.

### 10.1 Subgroup Profile (Insulin Dependent, Age < 70, N = 189)

| Variable | N | Mean | Median | Std | 25% | 75% | Max |
|---|---|---|---|---|---|---|---|
| **BMI** | 188 | 34.52 | 32.30 | 9.06 | 28.38 | 39.42 | 74.53 |
| **Daily Steps** | 177 | 6,901 | 5,933 | 4,841 | 4,020 | 8,914 | 24,006 |
| **Active Calories (kcal)** | 181 | 239.6 | 189.0 | 227.0 | 98.1 | 316.4 | 1,640.2 |
| **PM2.5 (ug/m3)** | 183 | 30.61 | 4.97 | 103.29 | 2.04 | 10.06 | 1,178.30 |
| **CGM Mean Glucose (mg/dL)** | 183 | 177.95 | 168.60 | 49.72 | 139.85 | 207.70 | 300.52 |

- **65.4%** of this subgroup is BMI-obese, and a further 25.0% is overweight — **90.4% combined** are above normal weight, the highest concentration in the entire cohort.
- PM2.5 is extremely right-skewed (mean 30.61 vs. median 4.97 ug/m3), driven by a small number of high-exposure homes; median exposure is still ~65% higher than the whole-cohort median of 3.03 ug/m3 (Part 1).

### 10.2 Direct Statistical Comparison vs. Rest of Cohort

| Variable | Focus Group Mean (n) | Rest of Cohort Mean (n) | Mann-Whitney p-value | Significant? |
|---|---|---|---|---|
| **BMI** | 34.52 (188) | 29.68 (2,085) | p = 1.43×10⁻¹⁵ | **Yes** — much higher |
| **Daily Steps** | 6,901 (177) | 6,097 (1,964) | p = 0.157 | No — **not lower**, directionally higher |
| **PM2.5** | 30.61 (183) | 13.84 (2,047) | p = 2.83×10⁻⁶ | **Yes** — much higher |

### 10.3 Within-Subgroup Correlations (Spearman, N=189)

| Pair | r (Spearman) | p-value | N |
|---|---|---|---|
| BMI vs. Daily Steps | -0.032 | 0.673 | 176 |
| BMI vs. Active Calories | -0.048 | 0.521 | 180 |
| BMI vs. PM2.5 | 0.027 | 0.721 | 182 |
| BMI vs. CGM Glucose | -0.094 | 0.209 | 182 |
| Daily Steps vs. Active Calories | 0.714 | <0.0001 | 177 |
| **Daily Steps vs. PM2.5** | **0.175** | **0.021** | 173 |
| Active Calories vs. PM2.5 | 0.127 | 0.091 | 177 |
| Active Calories vs. CGM Glucose | 0.076 | 0.313 | 177 |
| PM2.5 vs. CGM Glucose | 0.086 | 0.255 | 179 |

### 10.4 Median-Split: High-BMI + Low-Activity Overlap

Splitting the subgroup at its own median BMI (32.30) and median daily steps (5,933):

| Segment | N | Mean PM2.5 (ug/m3) |
|---|---|---|
| **High BMI AND Low Activity** (both above/below subgroup median) | 44 / 176 (25%) | 20.89 |
| Everyone else in the focus group | 132 / 176 (75%) | 33.60 |

### 10.5 Interpretation — A More Nuanced Picture Than Hypothesized

The data **partially supports and partially complicates** the hypothesized relationship:

1. **Confirmed independently**: Both **BMI** and **indoor PM2.5 exposure** are significantly and substantially elevated in the younger, insulin-dependent subgroup compared to the rest of the cohort (BMI +16%, PM2.5 +121%, both p<0.0001). This subgroup is a genuine "double-burden" population for metabolic and environmental risk.

2. **Not confirmed**: **Physical activity is not reduced** in this subgroup — daily steps are statistically indistinguishable from (and directionally slightly higher than) the rest of the cohort (p=0.157), consistent with the age-stratified finding in Part 6 that activity decline is primarily an **age** effect, not a diabetes-severity effect. Elevated stress and heart rate (Part 5) accompany this subgroup, but not measurably lower step counts.

3. **BMI, activity, and PM2.5 do not correlate with each other *within* this subgroup**: at the individual level, BMI shows essentially zero correlation with daily steps (r=-0.03), active calories (r=-0.05), or PM2.5 (r=0.03) among these 189 participants. The **median-split analysis in 10.4 runs opposite to the hypothesis** — participants who are simultaneously high-BMI *and* low-activity actually have **lower** average PM2.5 (20.89) than the rest of the focus group (33.60), though the small cell size (n=44) and PM2.5's extreme skew (a handful of outlier homes near 1,000+ ug/m3 outside this cell) make this difference fragile rather than a reliable inverse relationship.

4. **The one statistically significant within-group link goes the "wrong" direction**: Daily steps correlate weakly *positively*, not negatively, with PM2.5 (r=0.175, p=0.021) — more physically active participants in this subgroup show slightly *higher* indoor pollution exposure, plausibly because higher activity/mobility increases exposure to cooking, cleaning, or other indoor particulate-generating activities, or because both track a third factor (e.g., household size, home square footage) not captured here.

**Bottom line**: High BMI, elevated indoor pollution, and (from Parts 7/9) the heaviest comorbidity burden all co-locate in the younger insulin-dependent population — but they appear to be **three parallel consequences of advanced, working-age T2D** (and/or of household/socioeconomic confounders) rather than an activity-mediated causal chain (i.e., "low activity → high BMI → more time exposed to indoor pollution") that the raw group-level averages might suggest at first glance. This is a genuinely useful negative/nuanced finding for downstream ML feature engineering: BMI and PM2.5 should likely be modeled as **independent risk axes** for this subgroup rather than a single composite "sedentary-lifestyle" signal.

---

## Part 11 - Summary and Population-Level Takeaways

### Population Environmental, Wearable, BMI & Clinical Summary (Full Cohort)

| Metric / Domain | Finding | Clinical & Methodological Impact |
|---|---|---|
| **PM2.5 Exposure** | Significantly elevated in **Insulin Dependent** cohort (mean 24.01 ug/m3, peak 35.11 ug/m3 in age 40-54) | Advanced T2D correlates with higher indoor particulate exposure, likely associated with reduced mobility and indoor air quality disparities. |
| **Indoor Temperature** | Diabetics maintain warmer home environments (median 24.6 - 24.9 C vs 23.7 C in healthy controls) | Associated with altered thermoregulation and peripheral vascular cold sensitivity in diabetic populations. |
| **Age vs PM2.5** | Indoor PM2.5 exposure decreases monotonically with age (19.01 → 15.38 → 9.86 ug/m3) | Correlates with higher cooking activity and indoor particulate generation in younger cohorts. |
| **BMI** *(New)* | Rises monotonically with diabetes severity (median 26.75 → 27.92 → 29.84 → **31.86**); 60.7% of insulin-dependent participants are obese | Confirms the "Obesity" comorbidity flag objectively; strongest single anthropometric marker of disease severity in this cohort. |
| **BMI vs Age** *(New)* | BMI is **highest in the youngest (40-54) stratum** (median 29.94) and declines with age | Counter-intuitive for a chronic-disease cohort; suggests younger adults carry disproportionate metabolic risk before age-related weight decline sets in. |
| **CGM Glucose** *(New)* | Wearable-measured mean glucose tracks study-group labels almost perfectly (115.7 → 122.4 → 139.3 → **168.6 mg/dL** median) | Validates clinical study-group assignment against objective, continuous physiological data. |
| **Physical Activity (Steps)** *(New)* | Declines sharply with **age** (-35%, 6,803→4,299 median steps 40-54 to 70+) but **not** with diabetes status (p=0.45) | Activity decline in this cohort is an aging phenomenon, not a diabetes-severity phenomenon — important for feature engineering (age should not be treated as a proxy-free stand-in for activity). |
| **BMI x Activity x Pollution** *(New — Part 10)* | High BMI and high PM2.5 both concentrate in the insulin-dependent, <70 subgroup, but are **not correlated with each other or with activity** at the individual level within that subgroup | These likely represent parallel, independent consequences of advanced disease/socioeconomic context rather than one causal activity-mediated chain — model as separate risk axes, not a composite score. |
| **Comorbidity Escalation** | Disease burden scales linearly with diabetes severity (3.39 → 5.54 → 6.76 → 7.75 conditions) | Diabetes acts as a systemic disease multiplier across all organ systems. |
| **Highest Risk Subgroup** | **Insulin Dependent x Age 40-54** now emerges as the multi-modal highest-risk cell: peak PM2.5 (35.11), peak BMI (36.61), and (with Age 70+) among the highest comorbidity trajectories | Highest priority target for clinical management, environmental/behavioral intervention, and multi-modal risk models — a younger, working-age population with the most years of disease progression ahead. |

---

*Prepared as part of the AI-READI EDA project.*
*Full Environmental Cohort: N = 2,231 participants (100% of available sensor files ingested).*
*Full Clinical Cohort: N = 2,280 participants.*
*Full BMI Cohort: N = 2,273 participants (OMOP `measurement.csv`, `bmi_vsorres` concept).*
*Full CGM Cohort: N = 2,245 participants (Dexcom G6 manifest summary statistics).*
*Full Wearable Activity Cohort: N = 2,184 participants (Garmin manifest summary statistics; per-stream N varies 1,628-2,141 due to device dropout).*
*Data source: AI-READI Dataset v3.0.0, Azure Blob Storage.*
