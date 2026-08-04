# True Exploratory Data Analysis Guide

**Comprehensive methodology for analyzing the AI-READI diabetes dataset**

---

## Overview

This guide documents the exploratory data analysis (EDA) approach for discovering patterns, relationships, and insights in the AI-READI multi-modal diabetes dataset.

**Key Differences from Initial Data Inspection:**
- **Initial Data Inspection**: Understanding data structure, formats, availability
- **True EDA**: Discovering clinical patterns, testing hypotheses, generating ML insights

---

## Table of Contents

1. [Analysis Objectives](#1-analysis-objectives)
2. [Data Preparation](#2-data-preparation)
3. [Analysis Sections](#3-analysis-sections)
4. [Interpretation Guidelines](#4-interpretation-guidelines)
5. [Expected Findings](#5-expected-findings)
6. [Next Steps](#6-next-steps)

---

## 1. Analysis Objectives

### Primary Goals

1. **Understand diabetes progression patterns**
   - How do glucose metrics differ across disease severity?
   - What percentage of participants meet clinical targets?
   - Are there unexpected patterns in glucose control?

2. **Discover multi-modal relationships**
   - Cardiac-metabolic connections (ECG + glucose)
   - Lifestyle impacts (activity, sleep, stress)
   - Cross-modal correlations

3. **Identify patient phenotypes**
   - Unsupervised clustering to find subgroups
   - Characterize clusters by clinical features
   - Compare to clinical study group labels

4. **Inform machine learning strategy**
   - Identify most predictive features
   - Understand data distributions for modeling
   - Generate hypotheses for personalized models

---

## 2. Data Preparation

### Required Scripts

Run these scripts in order to prepare the analysis dataset:

```bash
# Step 1: Download 20-30 CGM samples with complete multi-modal data
python3 scripts/download_cgm_samples.py

# Step 2: Calculate glucose metrics (TIR, TAR, TBR, CV, GMI)
python3 scripts/calculate_glucose_metrics.py

# Step 3: Merge all modalities into single dataset
python3 scripts/prepare_eda_dataset.py
```

### Output Dataset

**File**: `data/samples/eda_merged_dataset.csv`

**Columns**:
- **Demographics**: person_id, study_group, age, clinical_site
- **Glucose metrics**: mean_glucose, std_glucose, cv_glucose, tir, tar, tbr, gmi
- **Cardiac metrics**: Rate, PR, QRSD, QT, QTc, P, QRS, T
- **Activity metrics**: average_heartrate_bpm, average_oxygen_saturation_pct, average_stress_level, average_sleep_hours, average_daily_activity, average_active_calories_kcal

---

## 3. Analysis Sections

### Section 1: Cohort Characterization

**Purpose**: Understand the composition and demographics of the study population

**Analyses**:
- Study group distribution (pie chart, bar chart)
- Age distribution by study group (histogram)
- Data completeness heatmap
- Clinical site distribution (if available)

**Key Questions**:
- Is the sample balanced across diabetes severity levels?
- Are there age differences between groups?
- Which participants have complete multi-modal data?

---

### Section 2: Glucose Dynamics

**Purpose**: Understand glycemic control patterns across disease stages

#### 2.1 Mean Glucose Analysis

**Visualization**: Violin plot of mean glucose by study group

**Clinical Context**:
- Normal fasting glucose: 70-100 mg/dL
- Diabetes threshold: ≥126 mg/dL
- Higher mean glucose → worse glycemic control

**Expected Pattern**: Healthy < Pre-diabetes < Oral meds < Insulin

#### 2.2 Glucose Variability (CV)

**Visualization**: Box plot of CV by study group

**Clinical Context**:
- CV = (std / mean) × 100%
- Target: <36% for stable control
- High CV = unstable glucose, higher complication risk

**Expected Pattern**: Insulin-controlled may have higher CV (brittle diabetes)

#### 2.3 Time in Range (TIR) - THE GOLD STANDARD

**Visualizations**:
- Histogram overlay by study group
- Box plot comparison

**Clinical Context**:
- TIR = % of time glucose is 70-180 mg/dL
- Clinical target: >70%
- Each 5% increase reduces complications

**Key Analysis**:
- What percentage of each study group meets target?
- Are there healthy participants with poor TIR? (undiagnosed pre-diabetes)
- Are there insulin-controlled patients with excellent TIR?

#### 2.4 Time Above Range (TAR) and Time Below Range (TBR)

**TAR (Hyperglycemia)**:
- % of time glucose >180 mg/dL
- Target: <25%
- Associated with microvascular complications

**TBR (Hypoglycemia)**:
- % of time glucose <70 mg/dL
- Target: <4%
- Dangerous: can cause seizures, coma

#### 2.5 Glucose Metrics Correlation

**Visualization**: Heatmap of correlations between glucose metrics

**Expected Relationships**:
- High mean_glucose → Low TIR (negative correlation)
- High TAR → Low TIR (complementary measures)
- GMI correlates with mean_glucose (GMI is calculated from mean)

---

### Section 3: Cardiac-Metabolic Connections

**Purpose**: Explore relationships between glucose control and cardiac health

**Why This Matters**:
- Diabetes damages autonomic nervous system → altered heart function
- QTc prolongation (>450ms) → arrhythmia risk, sudden death
- Hyperglycemia correlates with cardiovascular complications

#### 3.1 Heart Rate vs. Mean Glucose

**Visualization**: Scatter plot colored by study group

**Hypothesis**: Hyperglycemia may correlate with elevated resting heart rate (autonomic dysfunction)

**Interpretation**:
- Positive correlation suggests autonomic impact
- Wide scatter suggests individual variation

#### 3.2 QTc Interval Analysis

**Visualization**: Box plot of QTc by study group

**Clinical Context**:
- QTc = Corrected QT interval (cardiac repolarization)
- Normal: <440ms (men), <460ms (women)
- Prolonged: >450ms → increased arrhythmia risk
- Diabetes is a risk factor for QTc prolongation

**Key Analysis**:
- Do insulin-controlled patients show longer QTc?
- What percentage have prolonged QTc by study group?

#### 3.3 ECG-Glucose Correlation Matrix

**Visualization**: Heatmap of ECG metrics vs. glucose metrics

**Features**: HR, QTc, PR vs. mean_glucose, cv_glucose, tir

**Look For**:
- Strong correlations suggesting mechanistic links
- Weak correlations suggesting independence

---

### Section 4: Lifestyle & Behavior Patterns

**Purpose**: Understand how modifiable risk factors affect glucose control

#### 4.1 Physical Activity vs. Glucose Control

**Visualizations**:
- Activity vs. mean glucose (scatter)
- Activity vs. TIR (scatter)

**Hypothesis**: Higher activity → better glucose control

**Potential Surprises**:
- Intense exercise can cause glucose spikes (adrenaline)
- Some inactive diabetics may have good control (medication effectiveness)

#### 4.2 Sleep Duration vs. Glycemic Variability

**Visualizations**:
- Sleep vs. CV (scatter)
- Sleep vs. TIR (scatter)

**Known Relationship**: Poor sleep increases glucose variability

**Look For**:
- Optimal sleep duration for glucose control
- Sleep deficiency thresholds

#### 4.3 Stress Level vs. Glucose

**Visualizations**:
- Stress vs. mean glucose (scatter)
- Stress vs. TAR (scatter)

**Mechanism**: Stress activates sympathetic nervous system → cortisol → hyperglycemia

**Expected Pattern**: Positive correlation between stress and glucose/TAR

#### 4.4 Multi-Variable Pairplot

**Purpose**: Explore all pairwise relationships simultaneously

**Features**: glucose, TIR, CV, activity, sleep, stress, study_group

**Look For**:
- Unexpected relationships
- Clusters in feature space
- Study group separation

---

### Section 5: Patient Phenotyping

**Purpose**: Discover patient subtypes using unsupervised learning

#### 5.1 K-Means Clustering

**Features**:
- Glucose: mean_glucose, cv_glucose, tir, tar, tbr
- Cardiac: Rate, QTc (if available)
- Activity: daily_activity, sleep_hours, stress_level (if available)

**Process**:
1. Standardize features (mean=0, std=1)
2. K-means clustering (try k=4)
3. Visualize in glucose space (TIR vs. mean glucose)
4. Characterize each cluster

**Potential Phenotypes**:
- "Cardiovascular-dominant": High QTc, poor activity, moderate glucose
- "Metabolic-dominant": Severe hyperglycemia, normal cardiac
- "Lifestyle-responsive": Good activity/sleep → good TIR despite diabetes
- "Treatment-refractory": Poor control despite insulin

#### 5.2 PCA Dimensionality Reduction

**Purpose**: Visualize high-dimensional data in 2D

**Visualizations**:
- PCA colored by cluster
- PCA colored by study group

**Interpretation**:
- PC1 & PC2 explained variance (how much info retained?)
- Do clusters separate clearly?
- Do study groups overlap or separate?

#### 5.3 Cluster Characterization

**Analysis**:
- Study group composition per cluster
- Mean glucose profile per cluster
- Cardiac/activity metrics per cluster
- Heatmap of cluster profiles

**Key Question**: Do unsupervised clusters align with clinical study groups, or reveal new subtypes?

---

### Section 6: Clinical Patterns

**Purpose**: Explore clinical metadata patterns

**Analyses**:
- Clinical site distribution
- Study group × clinical site cross-tabulation
- Data collection timeline
- Temporal trends (if dates available)

---

### Section 7: Key Findings Summary

**Purpose**: Synthesize main insights

**Components**:
1. Statistical summary table by study group
2. Percentage meeting clinical targets (TIR, TAR, TBR, QTc)
3. Key correlations discovered
4. Cluster characterization summary

---

### Section 8: ML Roadmap

**Purpose**: Translate EDA insights into ML strategy

**Recommended Features** (prioritized by correlation strength):
- High priority: Past glucose, time of day, CV, study group
- Medium priority: Activity, sleep, heart rate, stress
- Exploratory: QTc, PR, environmental factors

**Temporal Features to Engineer**:
- Rolling glucose statistics (15min, 1hr, 3hr windows)
- Glucose rate of change (derivative)
- Time since last meal
- Recent activity/sleep quality

**Proposed Models**:
1. Time series forecasting (LSTM, GRU, Transformer)
2. Spike detection (Random Forest, XGBoost)
3. Personalized models → cluster by weights

---

## 4. Interpretation Guidelines

### Statistical Significance

**Correlation Strength**:
- |r| < 0.3: Weak
- 0.3 ≤ |r| < 0.7: Moderate
- |r| ≥ 0.7: Strong

**Note**: With small sample sizes (n=20-30), even moderate correlations may not be statistically significant. Treat findings as exploratory.

### Clinical Significance

**TIR (Time in Range)**:
- >70%: Good control
- 50-70%: Moderate control
- <50%: Poor control

**CV (Coefficient of Variation)**:
- <36%: Stable control (target)
- 36-40%: Borderline
- >40%: High variability

**QTc Interval**:
- <440ms: Normal
- 440-450ms: Borderline
- >450ms: Prolonged (arrhythmia risk)

### Unexpected Findings to Look For

1. **Healthy participants with poor TIR**: May indicate undiagnosed pre-diabetes
2. **Insulin-controlled with excellent TIR**: Modern insulin therapy can achieve tight control
3. **Low CV with high mean glucose**: Stable hyperglycemia (still dangerous!)
4. **High activity but poor glucose**: May indicate other factors (medication non-adherence, severe disease)

---

## 5. Expected Findings

### Glucose Patterns

**Highly Likely**:
- Mean glucose increases with disease severity
- TIR decreases with disease severity
- TAR increases with disease severity

**Possible**:
- CV highest in insulin-controlled group (brittle diabetes)
- Bimodal TIR distribution in insulin group (excellent vs. poor control)

### Cardiac Patterns

**Likely**:
- QTc prolongation more common in diabetic groups
- Heart rate variability reduced in diabetes (autonomic dysfunction)

**Uncertain**:
- Direct correlation between glucose and QTc (may be weak)

### Lifestyle Patterns

**Expected**:
- Activity negatively correlates with mean glucose (more activity → lower glucose)
- Poor sleep correlates with higher CV (instability)
- Stress correlates with TAR (hyperglycemia)

**Potential Surprise**:
- Relationships may be weak (confounded by medication, disease severity)

### Clustering

**Likely**:
- 3-4 distinct clusters will emerge
- Clusters will partially align with study groups but reveal finer subtypes

**Discovery Potential**:
- New phenotypes not captured by clinical labels
- Example: "metabolically healthy diabetic" vs. "metabolically unhealthy pre-diabetic"

---

## 6. Next Steps

### After Completing EDA

1. **Validate Insights**: Discuss findings with domain experts (if available)
2. **Expand Sample**: Download more participants if patterns are unclear
3. **Temporal Analysis**: Download full CGM time series for time-based modeling
4. **Feature Engineering**: Create temporal features from CGM data
5. **Baseline Models**: Implement simple prediction models
6. **Personalized Modeling**: Train per-participant models
7. **Weight Clustering**: Cluster by model weights to discover mechanisms

### ML Development Pipeline

```
EDA (Current)
    ↓
Feature Engineering (Temporal features from CGM)
    ↓
Baseline Models (LSTM glucose prediction)
    ↓
Personalized Models (Per-participant training)
    ↓
Weight Clustering (Discover mechanistic subtypes)
    ↓
Clinical Validation (Compare to outcomes)
```

---

## Resources

- **Medical Background**: [AIREADI_INTRO.md](AIREADI_INTRO.md) - Comprehensive diabetes and dataset reference
- **Data Inspection**: [INITIAL_DATA_INSPECTION_GUIDE.md](INITIAL_DATA_INSPECTION_GUIDE.md) - Initial data structure documentation
- **Analysis Notebook**: [notebooks/02_exploratory_data_analysis.ipynb](../notebooks/02_exploratory_data_analysis.ipynb) - Interactive EDA workflow

---

## Key Takeaways

**This EDA is exploratory and hypothesis-generating, not confirmatory.**

With a sample of 20-30 participants, we can:
- ✓ Discover patterns and relationships
- ✓ Identify promising features for ML
- ✓ Generate hypotheses about diabetes subtypes
- ✗ NOT make definitive statistical claims (small sample)

**The primary value is informing the next phase: personalized predictive modeling.**

By understanding which features correlate with glucose control, we can build better models. By discovering patient phenotypes through clustering, we can test if personalized models reveal mechanistic insights when clustered by their weights.

**This is the foundation for precision diabetes medicine.**

---

*Last updated: 2026-01-23*
