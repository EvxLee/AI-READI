#!/usr/bin/env python3
"""
Download Missing CGM Data

Downloads CGM JSON files for participants who have ECG and activity data
but are missing CGM data. This ensures we have complete multi-modal data
for EDA analysis.
"""

import os
import sys
import pandas as pd
from azure.storage.blob import BlobServiceClient
from pathlib import Path

# Add config to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME, STUDY_ID


def get_target_participants():
    """Get participant IDs that have ECG and activity but missing CGM."""
    # Load ECG and activity manifests
    ecg = pd.read_csv('results/scans/manifest_cardiac_ecg.tsv', sep='\t')
    activity = pd.read_csv('results/scans/manifest_wearable_activity_monitor.tsv', sep='\t')

    # Get participants with both modalities
    ecg_ids = set(ecg['person_id'])
    activity_ids = set(activity['person_id'])
    target_ids = ecg_ids & activity_ids

    # Check which CGM files we already have
    cgm_dir = Path('data/samples/cgm')
    cgm_dir.mkdir(parents=True, exist_ok=True)
    existing_files = list(cgm_dir.glob('*_DEX.json'))
    existing_ids = {int(f.stem.split('_')[0]) for f in existing_files}

    # Find missing IDs
    missing_ids = sorted(target_ids - existing_ids)

    print(f"Participants with ECG and activity data: {len(target_ids)}")
    print(f"Already have CGM for: {len(existing_ids & target_ids)}")
    print(f"Missing CGM for: {len(missing_ids)}")

    return missing_ids


def download_cgm_files(participant_ids):
    """Download CGM JSON files for specified participants."""
    # Connect to blob storage
    blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    container = blob_service.get_container_client(CONTAINER_NAME)

    # Download CGM manifest
    manifest_blob = f'{STUDY_ID}/dataset/wearable_blood_glucose/manifest.tsv'
    blob_client = container.get_blob_client(manifest_blob)

    from io import BytesIO
    manifest_data = blob_client.download_blob().readall()
    manifest = pd.read_csv(BytesIO(manifest_data), sep='\t')

    # Create output directory
    output_dir = Path('data/samples/cgm')
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nDownloading CGM files for {len(participant_ids)} participants...")
    downloaded = 0
    failed = 0

    for person_id in participant_ids:
        # Find file path in manifest
        person_manifest = manifest[manifest['person_id'] == person_id]
        if len(person_manifest) == 0:
            print(f"  ✗ No CGM data in manifest for participant {person_id}")
            failed += 1
            continue

        # Get file path
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
            if downloaded % 5 == 0 or downloaded == len(participant_ids) - failed:
                print(f"  ✓ Downloaded {downloaded}/{len(participant_ids) - failed} files...")

        except Exception as e:
            print(f"  ✗ Error downloading {person_id}: {e}")
            failed += 1

    print(f"\n✓ Successfully downloaded {downloaded} CGM files")
    if failed > 0:
        print(f"✗ Failed to download {failed} files")

    return downloaded


def main():
    """Main execution function."""
    print("="*80)
    print("DOWNLOAD MISSING CGM DATA")
    print("="*80)
    print()

    # Get target participants
    missing_ids = get_target_participants()

    if len(missing_ids) == 0:
        print("\n✓ All participants with ECG/activity already have CGM data!")
        return

    # Download missing files
    downloaded = download_cgm_files(missing_ids)

    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE")
    print("="*80)
    print(f"\nNew CGM files downloaded: {downloaded}")
    print(f"\nNext steps:")
    print(f"  1. python3 scripts/calculate_glucose_metrics.py")
    print(f"  2. python3 scripts/prepare_eda_dataset.py")
    print()


if __name__ == "__main__":
    main()
