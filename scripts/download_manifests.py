#!/usr/bin/env python3
"""
Download manifest files from Azure Blob Storage for data fidelity analysis.
These are small metadata files that contain pre-aggregated statistics.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from azure.storage.blob import BlobServiceClient
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME
import pandas as pd
import io

def download_manifest(container_client, blob_path, local_path):
    """Download a manifest file from Azure Blob Storage."""
    try:
        blob_client = container_client.get_blob_client(blob_path)
        data = blob_client.download_blob().readall()

        # Determine separator (TSV or CSV)
        separator = '\t' if blob_path.endswith('.tsv') else ','

        # Save to local file
        with open(local_path, 'wb') as f:
            f.write(data)

        # Load and display summary
        df = pd.read_csv(io.BytesIO(data), sep=separator)
        print(f"✓ Downloaded: {blob_path}")
        print(f"  → Saved to: {local_path}")
        print(f"  → Rows: {len(df)}, Columns: {len(df.columns)}")
        print()

        return True
    except Exception as e:
        print(f"✗ Failed to download {blob_path}")
        print(f"  Error: {str(e)}")
        print()
        return False

def main():
    print("=" * 80)
    print("AI-READI Dataset - Manifest File Downloader")
    print("=" * 80)
    print()

    # Initialize Azure client
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)

    # Define manifests to download
    manifests = [
        {
            'blob_path': '00b62456-0b93-4975-a992-42ba6a50ed5c/dataset/wearable_blood_glucose/manifest.tsv',
            'local_path': 'data/samples/manifests/manifest_wearable_blood_glucose.tsv',
            'description': 'CGM (Continuous Glucose Monitoring) metadata'
        },
        {
            'blob_path': '00b62456-0b93-4975-a992-42ba6a50ed5c/dataset/cardiac_ecg/manifest.tsv',
            'local_path': 'data/samples/manifests/manifest_cardiac_ecg.tsv',
            'description': '12-Lead ECG metadata and derived metrics'
        },
        {
            'blob_path': '00b62456-0b93-4975-a992-42ba6a50ed5c/dataset/wearable_activity_monitor/manifest.tsv',
            'local_path': 'data/samples/manifests/manifest_wearable_activity_monitor.tsv',
            'description': 'Garmin wearable activity monitor metadata'
        },
        {
            'blob_path': '00b62456-0b93-4975-a992-42ba6a50ed5c/dataset/environment/manifest.tsv',
            'local_path': 'data/samples/manifests/manifest_environment.tsv',
            'description': 'Environmental sensor metadata'
        },
        {
            'blob_path': '00b62456-0b93-4975-a992-42ba6a50ed5c/dataset/participants.tsv',
            'local_path': 'data/samples/manifests/participants.tsv',
            'description': 'Participant demographics and modality flags'
        }
    ]

    # Download each manifest
    success_count = 0
    for manifest_info in manifests:
        print(f"Downloading: {manifest_info['description']}")
        success = download_manifest(
            container_client,
            manifest_info['blob_path'],
            manifest_info['local_path']
        )
        if success:
            success_count += 1

    # Summary
    print("=" * 80)
    print(f"Download complete: {success_count}/{len(manifests)} manifests downloaded successfully")
    print("=" * 80)

    if success_count == len(manifests):
        print("\n✓ All manifests ready for data fidelity analysis!")
        print(f"  Location: data/samples/manifests/")
        return 0
    else:
        print(f"\n⚠️  Some manifests failed to download. Check errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
