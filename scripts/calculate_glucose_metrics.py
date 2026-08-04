#!/usr/bin/env python3
"""
Calculate Glucose Metrics from CGM Data

Calculates Time in Range (TIR), Time Above/Below Range, Coefficient of Variation,
and other glycemic variability metrics from downloaded CGM JSON files.
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


def parse_cgm_json(filepath):
    """
    Parse Dexcom G6 CGM JSON file in Open mHealth schema format.

    Args:
        filepath: Path to CGM JSON file

    Returns:
        DataFrame with timestamp and glucose value columns
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    # Check for Open mHealth schema format (AI-READI standard)
    if isinstance(data, dict) and 'body' in data and 'cgm' in data['body']:
        # Open mHealth schema: data['body']['cgm'] is list of readings
        cgm_records = data['body']['cgm']

        records = []

        for record in cgm_records:
            # Extract both timestamp and glucose together to keep them paired
            timestamp = None
            glucose_val = None

            # Extract timestamp from effective_time_frame
            if 'effective_time_frame' in record and 'time_interval' in record['effective_time_frame']:
                time_str = record['effective_time_frame']['time_interval'].get('start_date_time')
                if time_str:
                    try:
                        timestamp = pd.to_datetime(time_str)
                    except:
                        pass

            # Extract glucose value from blood_glucose
            if 'blood_glucose' in record and 'value' in record['blood_glucose']:
                try:
                    glucose_val = float(record['blood_glucose']['value'])
                except (ValueError, TypeError):
                    pass

            # Only add if we have both timestamp and glucose value
            if timestamp is not None and glucose_val is not None:
                records.append({'timestamp': timestamp, 'glucose': glucose_val})

        df = pd.DataFrame(records)

        return df

    # Fallback: Try other common formats
    if isinstance(data, list):
        # List of records
        df = pd.DataFrame(data)
    elif isinstance(data, dict):
        # Nested structure - try common patterns
        if 'data' in data:
            df = pd.DataFrame(data['data'])
        elif 'records' in data:
            df = pd.DataFrame(data['records'])
        elif 'egv_records' in data:  # Dexcom specific
            df = pd.DataFrame(data['egv_records'])
        else:
            # Flatten dict
            df = pd.DataFrame([data])

    # Try to find glucose value column (common names)
    glucose_col = None
    for col_name in ['glucose', 'value', 'glucose_value', 'egv_value', 'Value']:
        if col_name in df.columns:
            glucose_col = col_name
            break

    if glucose_col is None:
        raise ValueError(f"Could not find glucose column in {filepath}")

    # Try to find timestamp column
    time_col = None
    for col_name in ['timestamp', 'time', 'datetime', 'display_time', 'system_time']:
        if col_name in df.columns:
            time_col = col_name
            break

    if time_col:
        df['timestamp'] = pd.to_datetime(df[time_col])
    else:
        # Create sequential timestamps
        df['timestamp'] = pd.date_range(start='2024-01-01', periods=len(df), freq='5T')

    # Standardize column names
    df = df.rename(columns={glucose_col: 'glucose'})

    return df[['timestamp', 'glucose']]


def calculate_metrics(glucose_series):
    """
    Calculate comprehensive glucose metrics.

    Args:
        glucose_series: Pandas Series of glucose values (mg/dL)

    Returns:
        Dictionary of calculated metrics
    """
    # Remove NaNs
    glucose = glucose_series.dropna()

    if len(glucose) == 0:
        return None

    # Basic statistics
    mean_glucose = glucose.mean()
    std_glucose = glucose.std()
    cv_glucose = (std_glucose / mean_glucose) * 100 if mean_glucose > 0 else 0

    # Time in Range (TIR): 70-180 mg/dL
    tir = ((glucose >= 70) & (glucose <= 180)).mean() * 100

    # Time Above Range (TAR): > 180 mg/dL
    tar = (glucose > 180).mean() * 100
    tar_level1 = ((glucose > 180) & (glucose <= 250)).mean() * 100  # Moderate
    tar_level2 = (glucose > 250).mean() * 100  # Severe

    # Time Below Range (TBR): < 70 mg/dL
    tbr = (glucose < 70).mean() * 100
    tbr_level1 = ((glucose < 70) & (glucose >= 54)).mean() * 100  # Moderate
    tbr_level2 = (glucose < 54).mean() * 100  # Severe

    # Glucose Management Indicator (GMI)
    # Formula: GMI = 3.31 + 0.02392 × mean_glucose
    gmi = 3.31 + 0.02392 * mean_glucose

    # Additional metrics
    median_glucose = glucose.median()
    min_glucose = glucose.min()
    max_glucose = glucose.max()
    glucose_range = max_glucose - min_glucose

    return {
        'n_readings': len(glucose),
        'mean_glucose': round(mean_glucose, 2),
        'median_glucose': round(median_glucose, 2),
        'std_glucose': round(std_glucose, 2),
        'cv_glucose': round(cv_glucose, 2),
        'min_glucose': round(min_glucose, 2),
        'max_glucose': round(max_glucose, 2),
        'glucose_range': round(glucose_range, 2),
        'tir': round(tir, 2),
        'tar': round(tar, 2),
        'tar_level1': round(tar_level1, 2),
        'tar_level2': round(tar_level2, 2),
        'tbr': round(tbr, 2),
        'tbr_level1': round(tbr_level1, 2),
        'tbr_level2': round(tbr_level2, 2),
        'gmi': round(gmi, 2)
    }


def process_cgm_files(cgm_dir='data/samples/cgm'):
    """
    Process all CGM JSON files and calculate metrics.

    Args:
        cgm_dir: Directory containing CGM JSON files

    Returns:
        DataFrame with metrics for all participants
    """
    cgm_path = Path(cgm_dir)

    if not cgm_path.exists():
        print(f"Error: Directory {cgm_dir} does not exist")
        return None

    # Find all JSON files
    json_files = list(cgm_path.glob('*.json'))

    if len(json_files) == 0:
        print(f"Error: No JSON files found in {cgm_dir}")
        return None

    print(f"Found {len(json_files)} CGM files")
    print("\nProcessing CGM data...")

    results = []

    for json_file in json_files:
        # Extract person_id from filename
        person_id = json_file.stem.replace('_DEX', '')

        try:
            # Parse CGM data
            df = parse_cgm_json(json_file)

            # Calculate metrics
            metrics = calculate_metrics(df['glucose'])

            if metrics:
                metrics['person_id'] = int(person_id)
                results.append(metrics)
                print(f"  ✓ Processed {person_id}: {metrics['n_readings']} readings, TIR={metrics['tir']:.1f}%")
            else:
                print(f"  ✗ No valid data for {person_id}")

        except Exception as e:
            print(f"  ✗ Error processing {person_id}: {e}")

    if len(results) == 0:
        print("\nError: No metrics calculated")
        return None

    # Create DataFrame
    metrics_df = pd.DataFrame(results)

    # Sort by person_id
    metrics_df = metrics_df.sort_values('person_id').reset_index(drop=True)

    return metrics_df


def merge_with_participants(metrics_df, participants_file='data/samples/cgm_sample_participants.csv'):
    """
    Merge glucose metrics with participant metadata.

    Args:
        metrics_df: DataFrame with glucose metrics
        participants_file: Path to participant metadata CSV

    Returns:
        Merged DataFrame
    """
    participants_path = Path(participants_file)

    if not participants_path.exists():
        print(f"Warning: Participant file {participants_file} not found")
        print("Returning metrics only (without study_group, age, etc.)")
        return metrics_df

    # Load participants
    participants = pd.read_csv(participants_path)

    # Select relevant columns
    participant_cols = ['person_id', 'study_group', 'age', 'clinical_site', 'study_visit_date']
    available_cols = [col for col in participant_cols if col in participants.columns]

    # Merge
    merged = metrics_df.merge(
        participants[available_cols],
        on='person_id',
        how='left'
    )

    # Reorder columns (person_id, study_group, age first)
    first_cols = ['person_id']
    if 'study_group' in merged.columns:
        first_cols.append('study_group')
    if 'age' in merged.columns:
        first_cols.append('age')

    other_cols = [col for col in merged.columns if col not in first_cols]
    merged = merged[first_cols + other_cols]

    return merged


def main():
    """Main execution function."""
    print("="*80)
    print("GLUCOSE METRICS CALCULATOR")
    print("="*80)
    print()

    # Process CGM files
    metrics_df = process_cgm_files()

    if metrics_df is None:
        print("\nExiting due to errors")
        return

    # Merge with participant metadata
    print("\nMerging with participant metadata...")
    final_df = merge_with_participants(metrics_df)

    # Save results
    output_path = Path('data/samples/glucose_metrics_summary.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_path, index=False)

    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print()

    # Overall statistics
    print(f"Participants processed: {len(final_df)}")
    print(f"\nGlucose Metrics (mean ± std):")
    print(f"  Mean Glucose: {final_df['mean_glucose'].mean():.1f} ± {final_df['mean_glucose'].std():.1f} mg/dL")
    print(f"  Time in Range: {final_df['tir'].mean():.1f} ± {final_df['tir'].std():.1f}%")
    print(f"  Time Above Range: {final_df['tar'].mean():.1f} ± {final_df['tar'].std():.1f}%")
    print(f"  Time Below Range: {final_df['tbr'].mean():.1f} ± {final_df['tbr'].std():.1f}%")
    print(f"  CV (Variability): {final_df['cv_glucose'].mean():.1f} ± {final_df['cv_glucose'].std():.1f}%")
    print(f"  GMI (est. HbA1c): {final_df['gmi'].mean():.2f} ± {final_df['gmi'].std():.2f}%")

    # By study group (if available)
    if 'study_group' in final_df.columns:
        print(f"\nBy Study Group:")
        for group in final_df['study_group'].unique():
            group_data = final_df[final_df['study_group'] == group]
            print(f"\n  {group} (n={len(group_data)}):")
            print(f"    Mean Glucose: {group_data['mean_glucose'].mean():.1f} mg/dL")
            print(f"    TIR: {group_data['tir'].mean():.1f}%")
            print(f"    TAR: {group_data['tar'].mean():.1f}%")
            print(f"    TBR: {group_data['tbr'].mean():.1f}%")

    print(f"\n✓ Results saved to: {output_path}")
    print()


if __name__ == "__main__":
    main()
