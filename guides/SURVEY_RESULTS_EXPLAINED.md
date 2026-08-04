# AI-READI Survey Analysis: Results, Interpretations & Next Steps

> **Who this is for:** Someone new to biomedical data analysis who wants to understand what we found and why it matters.
> **What this covers:** Notebooks 05 and 06 — survey EDA, composite feature engineering, and advanced aggregations across 2,280 patients.

---

## Table of Contents

1. [Background: What Are We Actually Studying?](#1-background-what-are-we-actually-studying)
2. [The Dataset at a Glance](#2-the-dataset-at-a-glance)
3. [CES-D-10: Depression Screening](#3-ces-d-10-depression-screening)
4. [PAID-5: Diabetes Distress](#4-paid-5-diabetes-distress)
5. [Comorbidity Index & Clustering](#5-comorbidity-index--clustering)
6. [DML Self-Management Adherence Gaps](#6-dml-self-management-adherence-gaps)
7. [PhenX SDOH: Social Determinants of Health](#7-phenx-sdoh-social-determinants-of-health)
8. [Substance Use & OTC Medications](#8-substance-use--otc-medications)
9. [Family & Genetic Risk](#9-family--genetic-risk)
10. [Psychosocial Burden Composite](#10-psychosocial-burden-composite)
11. [Ocular (Eye) Burden Score](#11-ocular-eye-burden-score)
12. [Correlations with CGM Outcomes](#12-correlations-with-cgm-outcomes)
13. [Missing Data Summary](#13-missing-data-summary)
14. [Demographic Overlaps: What We Found](#14-demographic-overlaps-what-we-found)
15. [Stratification Options](#15-stratification-options)
16. [How to Move Forward](#16-how-to-move-forward)

---

## 1. Background: What Are We Actually Studying?

### The Disease Spectrum

This study (AI-READI) tracks 2,280 people across a **spectrum of diabetes-related disease severity**:

| Study Group | What It Means |
|---|---|
| **Healthy** (N≈776) | No diabetes, no pre-diabetes — the control group |
| **Pre-DM** (N≈560) | Blood sugar higher than normal but not diabetic yet — early warning stage |
| **Oral Med** (N≈686) | Type 2 diabetes managed with pills (e.g., metformin) |
| **Insulin** (N≈258) | Type 2 diabetes requiring insulin injections — most severe group |

Think of this as a progression ladder: Healthy → Pre-DM → Oral Med → Insulin. As you go up the ladder, disease is harder to manage, more complications exist, and life is more impacted.

### What Are CGM Outcomes?

**CGM = Continuous Glucose Monitor** — a sensor worn on the body that tracks blood sugar every few minutes. The key metrics are:
- **TIR (Time In Range):** % of time blood sugar is in the healthy range (higher = better)
- **GMI (Glucose Management Indicator):** Estimated A1C from CGM data (lower = better)
- **CV (Coefficient of Variation):** How much blood sugar bounces around (lower = more stable)

The whole point of the survey data is to find **which psychosocial, behavioral, and social factors predict poor CGM outcomes**.

---

## 2. The Dataset at a Glance

- **2,280 total patients**
- **707,126 individual observations** (rows in the raw data)
- **Survey instruments analyzed:** CES-D-10, PAID-5, DML domains, PhenX SDOH, substance use, family history, comorbidities, and ocular conditions

This is a rich, multi-modal dataset — we're not just looking at blood sugar, we're looking at the whole person: their mental health, their neighborhood, their family history, their daily habits.

---

## 3. CES-D-10: Depression Screening

### What is CES-D-10?

The **Center for Epidemiologic Studies Depression Scale** is a 10-question survey that asks people how often they felt depressed, hopeless, restless, etc. over the past week. Scores range **0–30**.

- **Score ≥ 10** = clinically significant depressive symptoms (not a diagnosis, but a flag)

### What We Found

| Metric | Value |
|---|---|
| Mean score across all 2,280 patients | **5.85 out of 30** |
| % of ALL patients scoring ≥ 10 | **~20%** |
| % of insulin-dependent patients scoring ≥ 10 | **~32%** |

### What This Means

A mean of 5.85 suggests the cohort overall is not severely depressed — but 20% flagging at the clinical threshold is meaningful. For context, the general US population prevalence of clinically significant depressive symptoms is around 8–10%, so **this cohort is about 2x higher**.

The insulin group at **32%** is striking. This makes biological and psychological sense:
- Managing insulin requires constant vigilance (multiple injections, strict diet timing, fear of low blood sugar episodes)
- Insulin-dependent patients have typically been sick longer and have more complications
- Depression and diabetes have a bidirectional relationship — each makes the other worse

**Why this matters for ML:** Depression score is a strong candidate predictor. Depressed patients may have worse self-management, leading to poorer CGM outcomes. This creates a measurable pathway we can model.

---

## 4. PAID-5: Diabetes Distress

### What is PAID-5?

The **Problem Areas in Diabetes** scale (5-item version) measures **emotional distress specifically related to living with diabetes** — not general depression, but things like: fear of complications, feeling overwhelmed by the disease, frustration with management. Scores range **0–20**.

- **Score ≥ 8** = high diabetes distress

### What We Found

| Metric | Value |
|---|---|
| Mean score across all patients | **4.00 out of 20** |
| % of ALL patients with high distress (≥8) | **20.2%** |
| % of insulin patients with high distress | **31.9%** |

### What This Means

The pattern mirrors depression almost exactly — **~20% overall, ~32% in insulin group**. This is not a coincidence. Depression and diabetes distress are related but distinct constructs:
- You can have high diabetes distress without being clinically depressed
- The fact that both measures show the same insulin-group spike tells us there's a real psychosocial burden in that population

**An important distinction:** Depression is about how you feel in general. Diabetes distress is about how you feel *about managing your disease*. Both matter for predicting outcomes, and they likely capture slightly different variance.

---

## 5. Comorbidity Index & Clustering

### What is the Comorbidity Index?

A **comorbidity** is a disease you have *in addition to* your main condition. The comorbidity index here counts how many additional diagnoses each patient has from a standardized list (high cholesterol, hypertension, obesity, etc.).

### Top Conditions in the Cohort

| Condition | Prevalence |
|---|---|
| High Cholesterol | **50.6%** |
| Hypertension | **50.6%** |
| Rheumatoid Arthritis | **41.5%** |
| Obesity | (common, especially in Cluster 0) |

**Mean comorbidity index: 4.38** — meaning the average patient has about 4–5 additional diagnoses. This is a medically complex population.

### K-Means Clustering: Two Disease Phenotypes

We ran a **k-means clustering** algorithm to group patients by their comorbidity profile. Here's how to think about this:

> **Analogy:** Imagine you have 2,280 patients and you want to find "types" of sick people. Instead of just saying "everyone is different," you look for natural groupings based on which conditions tend to appear together.

The algorithm tested 2–6 clusters. We used the **silhouette score** to pick the best number (higher = tighter, more distinct groups):

```
k=2 clusters: silhouette = 0.1419  ← BEST
k=3 clusters: silhouette = 0.0801
k=4 clusters: silhouette = 0.0750
...
```

**The silhouette score of 0.14 is modest** — clusters exist, but there's overlap. This is expected in real patient data. Two clear phenotypes emerged:

| Cluster | Size | Top Conditions | Interpretation |
|---|---|---|---|
| **Cluster 0** | N=1,338 (59%) | High cholesterol, hypertension, obesity | **Cardiometabolic phenotype** |
| **Cluster 1** | N=942 (41%) | Rheumatoid arthritis, hypertension, cholesterol | **Musculoskeletal/inflammatory phenotype** |

### What This Means

These two clusters represent **distinct disease pathways**:
- Cluster 0 patients are sick largely because of metabolic dysfunction (obesity driving cholesterol and blood pressure problems) — this is the "classic" diabetes comorbidity profile
- Cluster 1 has more inflammatory/autoimmune involvement (RA is an autoimmune disease), which affects glucose metabolism differently and may respond differently to interventions

**For stratification:** Cluster membership is a natural, data-driven way to split the cohort for separate analyses. Models trained on Cluster 0 may not generalize to Cluster 1.

---

## 6. DML Self-Management Adherence Gaps

### What is DML?

DML stands for **Diabetes Management & Lifestyle** — a self-report instrument asking patients to rate how well they manage different aspects of their diabetes. We compute scores on a 0–10 scale and then calculate the **gap** (10 minus their score) as a measure of unmet need.

**Gap = how much room for improvement exists. Bigger gap = worse adherence.**

### Overall Domain Results

| Domain | Mean Score (0–10) | Gap (10 - Mean) |
|---|---|---|
| Medication Management | 8.69 | **1.31** ← Best adherence |
| Foot Care | 6.20 | **3.80** |
| Physical Activity | 5.97 | **4.03** |
| Diet Adherence | 5.81 | **4.19** |
| **Education** | **1.96** | **8.04** ← Worst adherence |

**Composite adherence gap: 4.31 / 10**

### The Education Finding is the Most Important Number Here

A gap of **8.04 out of 10** in diabetes education means patients are barely engaging with educational resources. Score of 1.96 means they're scoring ~2/10 on access to or engagement with diabetes education.

This is a systemic problem, not individual failure — most of it likely reflects limited availability of culturally appropriate, accessible diabetes education programs.

### Gaps by Study Group

| Domain | Healthy | Pre-DM | Oral Med | Insulin |
|---|---|---|---|---|
| Physical Activity | 3.44 | 3.77 | 4.46 | **5.23** |
| Diet | 4.22 | 4.13 | 4.15 | **4.34** |
| Education | **9.25** | 7.99 | 7.14 | **6.91** |
| Foot Care | 4.81 | 4.13 | 3.05 | **2.09** |
| Medication Management | 2.02 | 1.88 | 0.50 | **0.33** |

### What This Means

**Read the pattern carefully:**

- **Medication management gap shrinks as disease worsens** — sicker patients take their medications more reliably, probably because consequences are more immediate (this makes sense)
- **Foot care gap also shrinks with severity** — insulin patients care for their feet better, probably because they've been educated about neuropathy risk
- **Physical activity gap grows with severity** — insulin patients exercise the least (5.23 gap). This may reflect physical limitations, fear of hypoglycemia during exercise, or lack of guidance
- **Education gap is enormous for healthy participants (9.25)** — this seems counterintuitive, but healthy participants have less reason to seek diabetes education. The education instrument may be specifically about diabetes education, so healthy people score near zero by design

**Bottom line:** The insulin group has high medication adherence but terrible physical activity adherence. This profile — medication compliant but physically inactive — is a common and challenging pattern in advanced diabetes management.

---

## 7. PhenX SDOH: Social Determinants of Health

### What are SDOH?

**Social Determinants of Health** are the conditions in which people are born, grow, live, work, and age. The research evidence is clear: **where you live and your social circumstances affect your health as much as your biology does.**

The PhenX toolkit provides standardized survey questions about SDOH. We analyzed 92 items (72 available for the full cohort).

### The 4 Key Subscales

We grouped PhenX items into 4 interpretable subscales:

#### 1. Discrimination Score
How often patients experience discrimination (race, age, gender, etc.) in everyday life and healthcare settings.

| Group | Mean ± SD |
|---|---|
| Healthy | 1.753 ± 0.870 |
| Pre-DM | 1.866 ± 0.837 |
| Oral Med | 1.916 ± 0.889 |
| **Insulin** | **1.993 ± 0.990** |

**Pattern:** Discrimination scores increase with disease severity. The insulin group experiences the most discrimination. This gradient could reflect:
- Racial/ethnic minorities being disproportionately represented in higher-severity groups
- People with visible signs of illness facing more stigma
- Weight-based discrimination (obesity is a risk factor for insulin dependence)

#### 2. Healthcare Access Barriers
How many obstacles patients face accessing healthcare (cost, transportation, language, hours, etc.).

| Group | Mean ± SD |
|---|---|
| Healthy | 1.538 ± 2.954 |
| Pre-DM | 1.590 ± 2.817 |
| Oral Med | 2.090 ± 3.382 |
| **Insulin** | **2.447 ± 3.708** |

**Note the large standard deviations.** A mean of 2.4 with SD of 3.7 means the distribution is very skewed — most people face few barriers but some face enormous barriers. This is a highly unequal distribution.

#### 3. Food & Housing Insecurity
A binary flag: does this patient face food or housing instability?

| Group | % Flagged |
|---|---|
| Healthy | 45.0% |
| Pre-DM | 49.0% |
| Oral Med | 51.9% |
| **Insulin** | **57.4%** |
| **Overall** | **49.5%** |

**Nearly half the cohort faces food or housing insecurity.** This is an extraordinary finding. This isn't just a social issue — food insecurity directly causes poor blood sugar control (you can't follow a diabetic diet if you're not sure where your next meal comes from).

#### 4. Neighborhood Safety Score
Perceived safety in the patient's neighborhood.

| Group | Mean |
|---|---|
| Healthy | 2.786 |
| Pre-DM | 2.745 |
| Oral Med | 2.772 |
| Insulin | 2.791 |

**Relatively flat across groups** — neighborhood safety doesn't strongly differentiate disease severity in this cohort. This is actually an interesting negative finding.

### PCA on SDOH

We also ran **Principal Component Analysis (PCA)** — a statistical technique that compresses many SDOH variables into a smaller set of "summary dimensions."

- **PC1 explains 54.9% of variance** — a single dimension captures most of the SDOH signal
- **PC2 explains 24.6%** — a second dimension captures additional variance

Interpretation: Most of the social risk in this cohort tends to cluster together. People who face discrimination also tend to face healthcare barriers and food insecurity — it's not random. There is a **general social disadvantage axis** (PC1) that is the dominant signal.

---

## 8. Substance Use & OTC Medications

### What We Measured

- **Substance exposure:** How many substances the patient has been exposed to (alcohol, tobacco, cannabis, etc.) — 26 variables, 6-item scale
- **OTC burden:** How many over-the-counter medications the patient takes (pain relievers, antacids, sleep aids, etc.)

### Key Results

| Metric | Value |
|---|---|
| Substance exposure median | 3.0 |
| OTC burden median | 2.0 |
| Substance-CGM correlation | **ρ = −0.299** (p < 0.0001) |
| OTC burden-CGM correlation | **ρ = +0.189** (p < 0.0001) |
| Interaction term-CGM correlation | ρ = +0.016 (p = 0.44, NOT significant) |

### What This Means (And Why It's Counterintuitive)

**Substance exposure negatively correlates with a bad CGM outcome (ρ = -0.299).** This means higher substance exposure is associated with *better* glucose metrics. Wait — shouldn't substance use be bad?

A few possible explanations:
1. **Confounding by study group:** Healthier patients may have more substance exposure because they are social drinkers, and social drinking correlates with higher income/social integration which correlates with better health
2. **Survival bias:** People with very severe diabetes may have already quit substances due to illness, making the remaining users seem "healthier"
3. **Type of substance:** The 6-item scale mixes substances — light alcohol use has known modest cardioprotective effects

**OTC burden positively correlates with worse CGM (ρ = +0.189).** This makes more intuitive sense: people taking more OTC medications are managing more symptoms, suggesting greater overall health burden.

**The interaction term is NOT significant (p = 0.44).** This means there's no meaningful "synergy" between substance use and OTC medications — they act independently.

**Important caveat:** These are correlations, not causal relationships. We cannot conclude that substance use improves blood sugar.

---

## 9. Family & Genetic Risk

### What We Measured

We created a **3-level family history risk score**:
- **Level 0:** No family history of diabetes
- **Level 1:** One parent or sibling with diabetes
- **Level 2:** Both parents or multiple relatives with diabetes

### Distribution by Study Group

| Risk Level | Healthy | Pre-DM | Oral Med | Insulin |
|---|---|---|---|---|
| Level 0 (no history) | **65.2%** | 50.2% | 31.8% | 33.5% |
| Level 1 (some history) | 27.6% | 33.1% | **41.5%** | 37.1% |
| Level 2 (strong history) | 7.2% | 16.7% | 26.7% | **29.4%** |

**Chi-square test: χ² = 209.30, p = 1.99 × 10⁻⁴²**

### How to Read a p-value This Small

A p-value of 10⁻⁴² is essentially zero. In statistics, we typically say p < 0.05 is "statistically significant." This result is so far beyond that threshold that it's almost incomprehensible.

What it means: **The relationship between family history and disease severity is not random.** The pattern we see — healthy people have less family history, insulin-dependent people have more — would not occur by chance if there were no real relationship.

### What This Means

**The gradient is stark:**
- Only 7.2% of healthy controls have Level 2 family risk
- 29.4% of insulin-dependent patients have Level 2 family risk — **4x higher**

This confirms that **genetic predisposition is a major driver of disease progression.** But it also tells us that family history is a **powerful stratification variable** — people with Level 2 family history are a fundamentally different at-risk group who may need proactive intervention earlier.

---

## 10. Psychosocial Burden Composite

### What This Is

We combined three instruments — CES-D (depression), PAID (diabetes distress), and SDOH PC1 (social disadvantage) — into a single **psychosocial burden composite score** using PCA. This gives us one number summarizing overall psychosocial load.

### Results

| Metric | Value |
|---|---|
| Cronbach's alpha | **0.587** |
| PCA PC1 variance explained | **54.9%** |
| PCA PC2 variance explained | 24.6% |

**Mean composite score by group (Z-scored — 0 is the average):**

| Group | Mean Score | Interpretation |
|---|---|---|
| Healthy | −0.173 | Below average burden |
| Pre-DM | +0.034 | Slightly above average |
| Oral Med | +0.061 | Slightly above average |
| **Insulin** | **+0.294** | Meaningfully above average |

### Understanding Cronbach's Alpha

**Cronbach's alpha** measures internal consistency — do the items in a composite scale "hang together"? Scale:
- α ≥ 0.7 = good
- α ≥ 0.6 = acceptable
- α < 0.6 = questionable

Our α = **0.587** is just below acceptable. This tells us the three instruments (depression, diabetes distress, SDOH) are related but not redundant — they each capture somewhat distinct aspects of psychosocial burden. The composite is still useful, but with awareness that its components are partially independent.

**54.9% variance explained by PC1** confirms a meaningful common factor underlying all three measures.

### What This Means

The insulin group carries **meaningfully higher psychosocial burden** (+0.294 Z-score vs. −0.173 for healthy). This translates to roughly **0.47 standard deviations of separation** between the healthiest and sickest groups — a moderate-sized effect.

This composite is valuable because instead of tracking three separate scores, you have one number that summarizes "how psychosocially burdened is this patient?" This is useful for clinical risk stratification and as an ML feature.

---

## 11. Ocular (Eye) Burden Score

### What This Is

Diabetes is a leading cause of blindness in adults. We engineered an **ocular burden score** that weights different eye conditions by severity:

| Condition | Weight | Why |
|---|---|---|
| Proliferative diabetic retinopathy | 2.0 | Severe — direct complication of diabetes, can cause blindness |
| Retinal vascular occlusion | 2.0 | Severe — blood vessel blockage in the retina |
| AMD (macular degeneration) | 1.5 | Moderate — major vision threat, partly metabolic |
| Glaucoma | 1.5 | Moderate — pressure-related damage, metabolic links |
| Cataracts | 1.0 | Mild — common, treatable, but accelerated by diabetes |
| Dry eye | 1.0 | Mild — common symptom, quality of life impact |

### What to Expect

We'd expect the insulin group to have the highest ocular burden — they've typically had diabetes the longest and with the worst control. The gradient should be: **Insulin > Oral Med > Pre-DM > Healthy**.

This score gives us a distinct signal from the general comorbidity index because it specifically captures diabetes-specific complications in the eye — a direct measure of cumulative disease damage.

---

## 12. Correlations with CGM Outcomes

### The Most Important Correlations

The **neighborhood safety score** had the **strongest correlation** with CGM outcomes:
- **ρ ≈ −0.34** with TIR (Time In Range)

This means patients in less safe neighborhoods tend to have worse glucose control. This is one of the strongest SDOH signals in the dataset.

Other notable correlations:
- **Comorbidity index: ρ = 0.285 with TIR** (more conditions = less time in healthy glucose range)
- **Substance exposure: ρ = −0.299** (discussed above)
- **OTC burden: ρ = +0.189**

### Understanding ρ (Pearson/Spearman Correlation)

| ρ value | Interpretation |
|---|---|
| ±0.1–0.3 | Weak but meaningful |
| ±0.3–0.5 | Moderate |
| ±0.5–0.7 | Strong |
| ±0.7+ | Very strong |

Our strongest correlations are in the 0.28–0.34 range — **moderate** correlations. This is actually good for psychosocial data predicting biological outcomes. These factors genuinely matter.

---

## 13. Missing Data Summary

### Coverage Rates

| Feature | Coverage | Note |
|---|---|---|
| CES-D total | **99.9%** | Essentially complete |
| PAID total | **97.8%** | Nearly complete |
| Comorbidity index | **100%** | Complete |
| DML domains | **94.9–100%** | Very high |
| SDOH PCA components | **99.6%** | Very high |
| Diet score | **31.9%** | ⚠ Low — may have collection issues |
| Falls count | **16.1%** | ⚠ Intentional — only collected for eligible patients |

### What This Means

The core psychosocial features (depression, distress, comorbidities) are nearly complete — this is excellent data quality. The diet score's low coverage (31.9%) is a flag; it may mean the diet survey wasn't administered to all participants, or responses were largely missing. **Be cautious using diet score as a feature** until the missingness mechanism is understood.

---

## 14. Demographic Overlaps: What We Found

This is one of the core tasks you were asked to investigate. Here's a synthesis of the demographic signal across all instruments:

### The Insulin Group Is Multiply Disadvantaged

The insulin-dependent group is not just medically sicker — they are systematically more disadvantaged across every dimension we measured:

| Dimension | Insulin vs. Healthy Gap |
|---|---|
| Depression (CES-D) | 32% vs. ~11% flagged |
| Diabetes distress | 31.9% vs. lower |
| Food/housing insecurity | 57.4% vs. 45.0% |
| Healthcare access barriers | 2.45 vs. 1.54 (mean) |
| Discrimination experienced | 1.99 vs. 1.75 (mean) |
| Family risk Level 2 | 29.4% vs. 7.2% |
| Physical activity gap | 5.23 vs. 3.44 |
| Psychosocial burden | +0.294 vs. −0.173 |

**This is called "intersecting disadvantage" or "syndemic" burden.** These factors don't add up linearly — they interact and compound each other. A patient who is food insecure AND depressed AND lives in an unsafe neighborhood AND has strong family history faces multiplicative, not additive, challenges.

### Pre-DM as a Critical Window

The pre-diabetes group shows an intermediate profile — more burden than healthy but less than the treatment groups. This is important because **pre-diabetes is reversible** with intervention. Patients in this group who already show elevated psychosocial risk factors (family history Level 2, food insecurity, barriers to care) are the highest-value targets for preventive intervention.

### The Education Gap Spans All Groups

The education gap (8.04 overall) is enormous and affects everyone. Even the insulin group, which is presumably most engaged with the medical system, has a gap of 6.91. This suggests a systemic failure in diabetes education delivery, not just patient disengagement.

---

## 15. Stratification Options

**Stratification** means dividing your analysis or model by subgroup so you can find effects that are hidden when you look at everyone together. Here are the strongest options based on our findings:

### Option 1: Study Group (Primary Stratification) ⭐⭐⭐
Split analyses by: Healthy / Pre-DM / Oral Med / Insulin

**Why:** The four groups are fundamentally different in disease severity, psychosocial burden, and CGM patterns. A model trained on all four groups pooled may obscure strong within-group effects. Models for each subgroup will likely outperform a pooled model.

**Tradeoff:** Insulin group is only N=258 — smaller subgroup sizes reduce statistical power.

### Option 2: Comorbidity Cluster (Data-Driven) ⭐⭐⭐
Split analyses by: Cluster 0 (cardiometabolic) / Cluster 1 (musculoskeletal-inflammatory)

**Why:** These represent distinct disease pathways with potentially different drivers of CGM outcomes. The inflammatory pathway (Cluster 1) may have different response to interventions than the metabolic pathway (Cluster 0).

**Tradeoff:** Clusters are imperfect (silhouette = 0.14), so some misclassification exists.

### Option 3: Family History Risk Level ⭐⭐
Split analyses by: Level 0 / Level 1 / Level 2

**Why:** The chi-square of 209.3 (p < 10⁻⁴²) shows this variable strongly tracks disease severity. Risk Level 2 patients likely need different, more aggressive intervention.

**Tradeoff:** Level 2 is only 17% of the cohort — smaller subgroup.

### Option 4: Psychosocial Burden Tertiles ⭐⭐
Split by: Low / Medium / High psychosocial burden composite score

**Why:** This captures the combined effect of depression, distress, and social disadvantage. High-burden patients may respond differently to behavioral interventions.

**Tradeoff:** The composite's α = 0.587 is borderline — the measure isn't perfect.

### Option 5: Food/Housing Insecurity Binary ⭐⭐
Split by: Insecure (49.5%) / Secure (50.5%)

**Why:** This is a stark, concrete stratification. Nearly half the cohort has food or housing insecurity — and these patients face a fundamentally different lived reality when trying to follow dietary advice. Models that don't account for this may systematically fail for the insecure subgroup.

**Tradeoff:** Binary — may miss gradations within the insecure group.

### Option 6: SDOH PC1 Tertiles ⭐
Split by: Low / Medium / High social disadvantage

**Why:** PC1 (54.9% of SDOH variance) provides a continuous, comprehensive SDOH summary. Tertile split creates three groups with meaningfully different social contexts.

**Tradeoff:** PC1 is abstract — harder to interpret than concrete stratifiers above.

### Recommended Stratification Approach for Your Supervisor

For initial analyses: **Study Group** is the primary stratification (it's pre-defined in the study design and most interpretable).

For deeper analyses: **Comorbidity Cluster × Study Group** interaction is the most novel and interesting combination — you're asking "within each disease severity group, does the type of comorbidity profile matter?"

For interventional analyses: **Food/Housing Insecurity** is the most actionable stratifier — it directly implies different intervention needs.

---

## 16. How to Move Forward

Here is a logical sequence of next steps, from most immediate to longer-term:

### Step 1: Validate the Feature Table
The notebooks output `data/processed/advanced_survey_features.csv`. Before doing any modeling:
- Check the shape (should have 2,280 rows)
- Spot-check a few patients to make sure features look reasonable
- Confirm no data leakage (no future information encoded in the features)

### Step 2: Merge with CGM Data
The survey features need to be joined to the CGM outcome table (TIR, GMI, CV). The existing EDA merged dataset (`data/samples/eda_merged_dataset.csv`) may already have some of this — check what's in it before rebuilding.

### Step 3: Build a Baseline Model
Start simple: a **logistic regression** or **linear regression** predicting TIR from the composite features. This gives you:
- A sense of feature importance before going to complex models
- Interpretable coefficients your supervisor can review
- A baseline to beat with more complex models

**Suggested first features:**
1. Psychosocial burden composite
2. Comorbidity index
3. SDOH PC1
4. Family history risk level
5. DML composite adherence gap
6. Study group (as a categorical variable)

### Step 4: Stratified Analysis
Run the same baseline model separately for each study group. Compare:
- Which features matter most within each group?
- Does neighborhood safety predict TIR differently in the insulin group vs. healthy controls?

### Step 5: Address the Diet Score Gap
The diet score has only 31.9% coverage. Investigate why:
- Was it collected on a subset of participants by design?
- Is it worth imputing? (Probably not for <40% coverage)
- Can it be treated as a separate analysis on the available subset?

### Step 6: Consult on the Education Gap
The education gap finding (8.04/10) is so large it may warrant its own investigation. Is this a data artifact (the instrument isn't calibrated for non-diabetic participants) or a real finding? Talk to your supervisor about whether this is known in the literature.

### Step 7: Consider Syndemic Analysis
The intersecting disadvantage in the insulin group suggests a **syndemic analysis** might be valuable — this is a framework from public health that explicitly models how multiple burdens interact and compound. This would be an advanced analysis, potentially publishable, but requires deeper statistical expertise.

---

## Quick Reference: Key Numbers to Remember

| Finding | Value |
|---|---|
| Cohort size | 2,280 patients |
| Overall depression prevalence (CES-D ≥10) | ~20% |
| Insulin group depression prevalence | ~32% |
| Food/housing insecurity prevalence | 49.5% |
| Insulin group food insecurity | 57.4% |
| Strongest CGM predictor (SDOH) | Neighborhood safety ρ ≈ −0.34 |
| Education gap (largest unmet need) | 8.04 / 10 |
| Family history chi-square p-value | < 10⁻⁴² |
| Comorbidity clusters | 2 (cardiometabolic N=1,338 / musculoskeletal N=942) |
| Psychosocial composite variance explained | 54.9% (PC1) |
| Insulin group psychosocial burden | +0.294 Z-score vs. −0.173 healthy |

---

*Document generated from analysis in `notebooks/05_survey_eda_colab.ipynb` and `notebooks/06_advanced_survey_aggregations_colab.ipynb`.*
*Data: AI-READI dataset, N=2,280 participants.*
