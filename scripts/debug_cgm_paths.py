#!/usr/bin/env python3
"""Debug script to check CGM file paths in blob storage."""

import os
import sys
import pandas as pd
from azure.storage.blob import BlobServiceClient
from io import BytesIO

# Add config to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME, STUDY_ID

# Connect to blob storage
blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)
container = blob_service.get_container_client(CONTAINER_NAME)

# Download CGM manifest
manifest_blob = f'{STUDY_ID}/dataset/wearable_blood_glucose/manifest.tsv'
blob_client = container.get_blob_client(manifest_blob)

manifest_data = blob_client.download_blob().readall()
manifest = pd.read_csv(BytesIO(manifest_data), sep='\t')

print("Manifest columns:", manifest.columns.tolist())
print("\nFirst few rows:")
print(manifest.head())

# Check a specific participant
test_person_id = 1044
person_manifest = manifest[manifest['person_id'] == test_person_id]
print(f"\n\nManifest entry for person {test_person_id}:")
print(person_manifest)

if len(person_manifest) > 0:
    file_path = person_manifest.iloc[0]['glucose_filepath']
    print(f"\nOriginal filepath: {file_path}")

    # Try different path constructions
    paths_to_try = [
        file_path,
        f'{STUDY_ID}/dataset{file_path}',
        f'{STUDY_ID}/dataset/{file_path.lstrip("/")}',
        file_path.lstrip('/'),
    ]

    print("\nTrying different path constructions:")
    for path in paths_to_try:
        print(f"\nTrying: {path}")
        try:
            blob_client = container.get_blob_client(path)
            props = blob_client.get_blob_properties()
            print(f"  ✓ FOUND! Size: {props.size} bytes")
            break
        except Exception as e:
            print(f"  ✗ Not found: {str(e)[:100]}")
