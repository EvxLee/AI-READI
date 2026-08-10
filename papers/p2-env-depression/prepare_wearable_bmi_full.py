#!/usr/bin/env python3
"""
Merge full-cohort wearable (CGM + Garmin activity) and BMI data with
participants, diabetes status, age group, and environmental data for EDA.
"""
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

DATA = Path('data/samples')

group_mapping = {
    'healthy': 'healthy',
    'pre_diabetes_lifestyle_controlled': 'no diabetes',
    'oral_medication_and_or_non_insulin_injectable_medication_controlled': 'controlled diabetes',
    'insulin_dependent': 'insulin dependent',
    'insulin_controlled': 'insulin dependent'
}


def stratify_age(age):
    if age < 55:
        return '40-54'
    elif age < 70:
        return '55-69'
    else:
        return '70+'


def main():
    participants = pd.read_csv(DATA / 'manifests/participants.tsv', sep='\t')
    participants['diabetes_status'] = participants['study_group'].map(group_mapping)
    participants['age_group'] = participants['age'].apply(stratify_age)

    env = pd.read_csv(DATA / 'full_env_processed.csv')
    bmi = pd.read_csv(DATA / 'full_bmi_processed.csv')
    activity = pd.read_csv(DATA / 'manifests/manifest_wearable_activity_monitor.tsv', sep='\t')
    cgm = pd.read_csv(DATA / 'manifests/manifest_wearable_blood_glucose.tsv', sep='\t')

    activity_cols = ['person_id', 'average_heartrate_bpm', 'average_oxygen_saturation_pct',
                      'average_stress_level', 'average_sleep_hours', 'average_respiratory_rate_bpm',
                      'average_daily_activity', 'average_active_calories_kcal',
                      'sensor_sampling_duration_days']
    activity = activity[activity_cols].rename(columns={'average_daily_activity': 'average_daily_steps'})

    cgm_cols = ['person_id', 'average_glucose_level_mg_dl', 'glucose_sensor_sampling_duration_days']
    cgm = cgm[cgm_cols]

    df = participants.merge(env, on='person_id', how='left') \
                      .merge(bmi, on='person_id', how='left') \
                      .merge(activity, on='person_id', how='left') \
                      .merge(cgm, on='person_id', how='left')

    # Clean Garmin sentinel/invalid values (device error codes: -2, and physiologically
    # impossible 0 for HR/SpO2) -> treat as missing rather than real readings.
    for c in ['average_heartrate_bpm', 'average_oxygen_saturation_pct',
              'average_stress_level', 'average_respiratory_rate_bpm']:
        df.loc[df[c] <= 0, c] = np.nan

    # average_sleep_hours in the manifest is actually a day-fraction-asleep (0-1 range,
    # occasional >1 outliers), not literal hours. Convert to hours for interpretability.
    df['average_sleep_hours'] = df['average_sleep_hours'] * 24

    df.to_csv(DATA / 'full_merged_wearable_bmi.csv', index=False)

    diab_order = ['healthy', 'no diabetes', 'controlled diabetes', 'insulin dependent']
    age_order = ['40-54', '55-69', '70+']

    wearable_cols = ['bmi', 'average_glucose_level_mg_dl', 'average_heartrate_bpm',
                      'average_oxygen_saturation_pct', 'average_stress_level', 'average_sleep_hours',
                      'average_respiratory_rate_bpm', 'average_daily_steps', 'average_active_calories_kcal']

    print("="*100)
    print("COVERAGE (non-null N)")
    print("="*100)
    print(df[['person_id'] + wearable_cols].notna().sum())
    print()

    print("="*100)
    print("PART A: OVERALL POPULATION SUMMARY")
    print("="*100)
    print(df[wearable_cols].describe().T.round(3))
    print()

    print("="*100)
    print("PART B: BY DIABETES STATUS (mean [median], N) + Kruskal-Wallis")
    print("="*100)
    for col in wearable_cols:
        print(f"\n--- {col} ---")
        for g in diab_order:
            sub = df[df['diabetes_status'] == g][col].dropna()
            print(f"  {g:22s} N={len(sub):4d}  mean={sub.mean():.3f}  median={sub.median():.3f}")
        groups = [df[df['diabetes_status'] == g][col].dropna().values for g in diab_order]
        groups = [g for g in groups if len(g) > 0]
        if len(groups) > 1:
            stat, p = stats.kruskal(*groups)
            print(f"  Kruskal-Wallis: H={stat:.3f}, p={p:.4e}")

    print()
    print("="*100)
    print("PART C: BY AGE GROUP (mean [median], N) + Kruskal-Wallis")
    print("="*100)
    for col in wearable_cols:
        print(f"\n--- {col} ---")
        for g in age_order:
            sub = df[df['age_group'] == g][col].dropna()
            print(f"  {g:10s} N={len(sub):4d}  mean={sub.mean():.3f}  median={sub.median():.3f}")
        groups = [df[df['age_group'] == g][col].dropna().values for g in age_order]
        groups = [g for g in groups if len(g) > 0]
        if len(groups) > 1:
            stat, p = stats.kruskal(*groups)
            print(f"  Kruskal-Wallis: H={stat:.3f}, p={p:.4e}")

    print()
    print("="*100)
    print("PART D: 12-COMBINATION MATRIX (Diabetes Status x Age Group)")
    print("="*100)
    print("\n-- Sample sizes --")
    n_matrix = df.groupby(['diabetes_status', 'age_group'])['person_id'].count().unstack().reindex(index=diab_order, columns=age_order)
    print(n_matrix)

    for col in wearable_cols:
        print(f"\n-- {col} (mean) --")
        m = df.groupby(['diabetes_status', 'age_group'])[col].mean().unstack().reindex(index=diab_order, columns=age_order)
        print(m.round(2))

    print()
    print("="*100)
    print("PART E: FOCUS - BMI, ACTIVITY, POLLUTION IN INSULIN-DEPENDENT <70 SUBGROUP")
    print("="*100)

    sub = df[(df['diabetes_status'] == 'insulin dependent') & (df['age'] < 70)].copy()
    print(f"\nN = {len(sub)} (insulin dependent, age<70)")
    focus_cols = ['bmi', 'average_daily_steps', 'average_active_calories_kcal', 'mean_pm25',
                  'average_glucose_level_mg_dl', 'average_heartrate_bpm', 'average_sleep_hours',
                  'average_stress_level']
    print(sub[focus_cols].describe().T.round(3))

    print("\n-- Correlation matrix (Spearman) BMI, steps, calories, PM2.5, glucose --")
    corr_cols = ['bmi', 'average_daily_steps', 'average_active_calories_kcal', 'mean_pm25', 'average_glucose_level_mg_dl']
    corr_df = sub[corr_cols].dropna()
    print(f"N with complete data for correlation: {len(corr_df)}")
    if len(corr_df) > 5:
        corr = corr_df.corr(method='spearman')
        print(corr.round(3))
        print("\n-- Pairwise Spearman p-values --")
        for i, c1 in enumerate(corr_cols):
            for c2 in corr_cols[i+1:]:
                d = sub[[c1, c2]].dropna()
                if len(d) > 5:
                    r, p = stats.spearmanr(d[c1], d[c2])
                    print(f"  {c1} vs {c2}: r={r:.3f}, p={p:.4f}, n={len(d)}")

    # Compare to rest of cohort for contrast
    print("\n-- Comparison: insulin-dependent <70 vs rest of cohort --")
    rest = df[~((df['diabetes_status'] == 'insulin dependent') & (df['age'] < 70))]
    for col in ['bmi', 'average_daily_steps', 'mean_pm25']:
        a = sub[col].dropna()
        b = rest[col].dropna()
        if len(a) > 3 and len(b) > 3:
            stat, p = stats.mannwhitneyu(a, b, alternative='two-sided')
            print(f"  {col}: focus mean={a.mean():.2f} (n={len(a)}) vs rest mean={b.mean():.2f} (n={len(b)}) | Mann-Whitney p={p:.4e}")

    # Median split high BMI / low activity
    print("\n-- Median-split: High BMI (>median) & Low Activity (<median) overlap --")
    bmi_med = sub['bmi'].median()
    steps_med = sub['average_daily_steps'].median()
    high_bmi_low_act = sub[(sub['bmi'] > bmi_med) & (sub['average_daily_steps'] < steps_med)]
    print(f"BMI median: {bmi_med:.2f}, Steps median: {steps_med:.2f}")
    print(f"High-BMI & Low-Activity N = {len(high_bmi_low_act)} / {len(sub.dropna(subset=['bmi','average_daily_steps']))}")
    print(f"Mean PM2.5 in High-BMI/Low-Activity subgroup: {high_bmi_low_act['mean_pm25'].mean():.2f}")
    rest_split = sub[~((sub['bmi'] > bmi_med) & (sub['average_daily_steps'] < steps_med))]
    print(f"Mean PM2.5 in rest of focus group: {rest_split['mean_pm25'].mean():.2f}")


if __name__ == '__main__':
    main()
