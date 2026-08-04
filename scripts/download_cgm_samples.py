#!/usr/bin/env python3
"""
Download CGM Sample Data

Downloads JSON files for 20-30 participants with complete multi-modal data.
Stratifies by study group to ensure representation across diabetes severity levels.
"""

import os
import sys
import pandas as pd
from azure.storage.blob import BlobServiceClient
from pathlib import Path

# Add config to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME, STUDY_ID


def select_participants(target_per_group=7, min_total=20, max_total=30):
    """
    Select participants with complete multi-modal data.

    Args:
        target_per_group: Target number of participants per study group
        min_total: Minimum total participants
        max_total: Maximum total participants

    Returns:
        DataFrame with selected participants
    """
    print("Loading participant data...")

    # Download participants.tsv from blob storage
    blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    container = blob_service.get_container_client(CONTAINER_NAME)

    participants_blob = f'{STUDY_ID}/dataset/participants.tsv'
    blob_client = container.get_blob_client(participants_blob)

    # Read into pandas
    from io import BytesIO
    blob_data = blob_client.download_blob().readall()
    participants = pd.read_csv(BytesIO(blob_data), sep='\t')

    print(f"Total participants: {len(participants)}")
    print(f"\nStudy group distribution:")
    print(participants['study_group'].value_counts())

    # Filter for complete multi-modal data
    required_modalities = [
        'cardiac_ecg',
        'clinical_data',
        'wearable_blood_glucose',
        'wearable_activity_monitor',
        'environment'
    ]

    complete_data = participants.copy()
    for modality in required_modalities:
        if modality in complete_data.columns:
            complete_data = complete_data[complete_data[modality] == True]

    print(f"\nParticipants with complete multi-modal data: {len(complete_data)}")

    # Stratify by study group
    selected = []
    for group in complete_data['study_group'].unique():
        group_data = complete_data[complete_data['study_group'] == group]
        n_select = min(target_per_group, len(group_data))
        selected.append(group_data.sample(n=n_select, random_state=42))

    selected_df = pd.concat(selected, ignore_index=True)

    # Ensure we're within target range
    if len(selected_df) < min_total:
        print(f"Warning: Only {len(selected_df)} participants selected (< {min_total})")
    if len(selected_df) > max_total:
        selected_df = selected_df.sample(n=max_total, random_state=42)

    print(f"\nFinal selection: {len(selected_df)} participants")
    print("\nSelected participants by study group:")
    print(selected_df['study_group'].value_counts())

    return selected_df


def download_cgm_files(selected_participants):
    """
    Download CGM JSON files for selected participants.

    Args:
        selected_participants: DataFrame with selected participants

    Returns:
        Number of files downloaded
    """
    # Create output directory
    output_dir = Path('data/samples/cgm')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Connect to blob storage
    blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    container = blob_service.get_container_client(CONTAINER_NAME)

    # Download CGM manifest to get file paths
    manifest_blob = f'{STUDY_ID}/dataset/wearable_blood_glucose/manifest.tsv'
    blob_client = container.get_blob_client(manifest_blob)

    from io import BytesIO
    manifest_data = blob_client.download_blob().readall()
    manifest = pd.read_csv(BytesIO(manifest_data), sep='\t')

    print(f"\nDownloading CGM files...")
    downloaded = 0

    for idx, row in selected_participants.iterrows():
        person_id = row['person_id']

        # Find file path in manifest
        person_manifest = manifest[manifest['person_id'] == person_id]
        if len(person_manifest) == 0:
            print(f"  ✗ No CGM data found for participant {person_id}")
            continue

        # Get file path (remove leading slash if present)
        file_path = person_manifest.iloc[0]['glucose_filepath']
        file_path = file_path.lstrip('/')

        # Prepend study ID
        full_path = f'{STUDY_ID}/dataset/{file_path}'

        try:
            # Download file
            blob_client = container.get_blob_client(full_path)
            output_path = output_dir / f'{person_id}_DEX.json'

            with open(output_path, 'wb') as f:
                f.write(blob_client.download_blob().readall())

            downloaded += 1
            print(f"  ✓ Downloaded {person_id}_DEX.json ({downloaded}/{len(selected_participants)})")

        except Exception as e:
            print(f"  ✗ Error downloading {person_id}: {e}")

    print(f"\n✓ Successfully downloaded {downloaded} CGM files")
    return downloaded


def main():
    """Main execution function."""
    print("="*80)
    print("CGM SAMPLE DATA DOWNLOADER")
    print("="*80)
    print()

    # Select participants
    selected = select_participants(target_per_group=7, min_total=20, max_total=30)

    # Save participant list
    output_path = Path('data/samples/cgm_sample_participants.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output_path, index=False)
    print(f"\n✓ Saved participant list to: {output_path}")

    # Download CGM files
    downloaded = download_cgm_files(selected)

    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE")
    print("="*80)
    print(f"\nParticipants selected: {len(selected)}")
    print(f"CGM files downloaded: {downloaded}")
    print(f"\nOutput locations:")
    print(f"  - Participant list: data/samples/cgm_sample_participants.csv")
    print(f"  - CGM JSON files: data/samples/cgm/")
    print()


if __name__ == "__main__":
    main()
