#!/usr/bin/env python3
"""
Prepare EDA Dataset

Merges glucose metrics, ECG data, activity data, and demographics into a single
analysis-ready dataset for exploratory data analysis.
"""

import pandas as pd
from pathlib import Path


def load_glucose_metrics():
    """Load calculated glucose metrics."""
    path = Path('data/samples/glucose_metrics_summary.csv')
    if not path.exists():
        print(f"Warning: {path} not found. Run calculate_glucose_metrics.py first.")
        return None
    return pd.read_csv(path)


def load_ecg_manifest():
    """Load ECG manifest with derived cardiac metrics."""
    path = Path('results/scans/manifest_cardiac_ecg.tsv')
    if not path.exists():
        print(f"Warning: {path} not found.")
        return None

    ecg = pd.read_csv(path, sep='\t')

    # Select relevant columns
    ecg_cols = ['person_id', 'Rate', 'PR', 'QRSD', 'QT', 'QTc', 'P', 'QRS', 'T']
    available = [col for col in ecg_cols if col in ecg.columns]

    return ecg[available]


def load_activity_manifest():
    """Load wearable activity monitor manifest."""
    path = Path('results/scans/manifest_wearable_activity_monitor.tsv')
    if not path.exists():
        print(f"Warning: {path} not found.")
        return None

    activity = pd.read_csv(path, sep='\t')

    # Select summary metrics
    activity_cols = [
        'person_id',
        'average_heartrate_bpm',
        'average_oxygen_saturation_pct',
        'average_stress_level',
        'average_sleep_hours',
        'average_respiratory_rate_bpm',
        'average_daily_activity',
        'average_active_calories_kcal',
        'sensor_sampling_duration_days'
    ]
    available = [col for col in activity_cols if col in activity.columns]

    return activity[available]


def load_participants():
    """Load participant demographics."""
    path = Path('data/samples/cgm_sample_participants.csv')
    if not path.exists():
        # Try from results
        path = Path('results/scans/participants_sample.tsv')
        if not path.exists():
            print(f"Warning: Participants file not found.")
            return None
        df = pd.read_csv(path, sep='\t')
    else:
        df = pd.read_csv(path)

    # Select relevant columns
    demo_cols = ['person_id', 'study_group', 'age', 'clinical_site', 'study_visit_date']
    available = [col for col in demo_cols if col in df.columns]

    return df[available]


def merge_datasets():
    """Merge all data sources into single dataset."""
    print("Loading datasets...")

    # Start with glucose metrics (primary dataset)
    df = load_glucose_metrics()
    if df is None:
        print("Error: Glucose metrics required. Exiting.")
        return None

    print(f"  ✓ Glucose metrics: {len(df)} participants")

    # Merge ECG data
    ecg = load_ecg_manifest()
    if ecg is not None:
        df = df.merge(ecg, on='person_id', how='left')
        print(f"  ✓ ECG data merged: {ecg['person_id'].nunique()} participants")

    # Merge activity data
    activity = load_activity_manifest()
    if activity is not None:
        df = df.merge(activity, on='person_id', how='left')
        print(f"  ✓ Activity data merged: {activity['person_id'].nunique()} participants")

    # Merge demographics (if not already in glucose metrics)
    if 'study_group' not in df.columns:
        participants = load_participants()
        if participants is not None:
            df = df.merge(participants, on='person_id', how='left')
            print(f"  ✓ Demographics merged")

    return df


def main():
    """Main execution function."""
    print("="*80)
    print("EDA DATASET PREPARATION")
    print("="*80)
    print()

    # Merge all datasets
    df = merge_datasets()

    if df is None:
        print("\nError: Could not create merged dataset")
        return

    # Save merged dataset
    output_path = Path('data/samples/eda_merged_dataset.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print("\n" + "="*80)
    print("MERGED DATASET SUMMARY")
    print("="*80)
    print()

    print(f"Total participants: {len(df)}")
    print(f"Total features: {len(df.columns)}")
    print(f"\nColumn groups:")

    # Categorize columns
    glucose_cols = [c for c in df.columns if c in ['mean_glucose', 'std_glucose', 'cv_glucose', 'tir', 'tar', 'tbr', 'gmi']]
    cardiac_cols = [c for c in df.columns if c in ['Rate', 'PR', 'QRSD', 'QT', 'QTc', 'P', 'QRS', 'T']]
    activity_cols = [c for c in df.columns if 'average' in c.lower() or 'sleep' in c.lower() or 'activity' in c.lower()]
    demo_cols = [c for c in df.columns if c in ['person_id', 'study_group', 'age', 'clinical_site']]

    print(f"  Demographics: {len(demo_cols)} columns")
    print(f"  Glucose metrics: {len(glucose_cols)} columns")
    print(f"  Cardiac (ECG): {len(cardiac_cols)} columns")
    print(f"  Activity/wearable: {len(activity_cols)} columns")

    # Data completeness
    print(f"\nData completeness:")
    missing_pct = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    if missing_pct.max() > 0:
        print(f"  Columns with missing data:")
        for col, pct in missing_pct[missing_pct > 0].head(10).items():
            print(f"    {col}: {pct:.1f}% missing")
    else:
        print(f"  ✓ No missing data!")

    # By study group
    if 'study_group' in df.columns:
        print(f"\nParticipants by study group:")
        print(df['study_group'].value_counts())

    print(f"\n✓ Merged dataset saved to: {output_path}")
    print(f"\nNext step: Open notebooks/02_exploratory_data_analysis.ipynb")
    print()


if __name__ == "__main__":
    main()
