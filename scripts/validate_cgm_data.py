#!/usr/bin/env python3
"""Validate downloaded CGM data."""

import json
from pathlib import Path

cgm_dir = Path('data/samples/cgm')
json_files = list(cgm_dir.glob('*_DEX.json'))

print(f"Found {len(json_files)} CGM JSON files\n")

total_records = 0
valid_files = 0

for json_file in sorted(json_files)[:5]:  # Check first 5 files
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        # Check structure
        if 'body' in data and 'cgm' in data['body']:
            cgm_data = data['body']['cgm']
            num_records = len(cgm_data)
            total_records += num_records
            valid_files += 1

            # Show sample record
            if num_records > 0:
                sample = cgm_data[0]
                person_id = json_file.stem.split('_')[0]
                start_time = sample.get('effective_time_frame', {}).get('time_interval', {}).get('start_date_time', 'N/A')
                glucose_value = sample.get('blood_glucose', {}).get('value', 'N/A')
                glucose_unit = sample.get('blood_glucose', {}).get('unit', 'N/A')
                print(f"✓ {json_file.name}: {num_records:,} glucose readings")
                print(f"  Person: {person_id}, Start: {start_time}")
                print(f"  Sample glucose: {glucose_value} {glucose_unit}")
            else:
                print(f"✗ {json_file.name}: No data points!")
        else:
            print(f"✗ {json_file.name}: Unexpected structure - keys: {list(data.keys())}")
    except Exception as e:
        print(f"✗ {json_file.name}: Error - {e}")

print(f"\n✓ Validated {valid_files}/{len(json_files[:5])} files")
print(f"✓ Total glucose records in sample: {total_records}")
