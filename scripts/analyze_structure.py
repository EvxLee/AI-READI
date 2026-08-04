"""
Detailed structure analysis of the Azure Blob Storage scan results.
Provides insights into data organization and file patterns.
"""

import os
import sys
import json
from collections import defaultdict
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_latest_scan():
    """Load the most recent scan results."""
    scan_dir = 'results/scans'
    scan_files = [f for f in os.listdir(scan_dir) if f.startswith('blob_scan_')]

    if not scan_files:
        print("No scan files found!")
        return None

    latest_scan = sorted(scan_files)[-1]
    scan_path = os.path.join(scan_dir, latest_scan)

    print(f"Loading scan results from: {scan_path}\n")

    with open(scan_path, 'r') as f:
        return json.load(f)


def analyze_directory_structure(scan_data):
    """Analyze the directory structure in detail."""
    print("="*80)
    print("DETAILED DIRECTORY STRUCTURE ANALYSIS")
    print("="*80)

    directories = scan_data['directory_structure']

    # Organize by depth
    depth_analysis = defaultdict(list)

    for dir_path, file_count in directories.items():
        depth = dir_path.count('/') if dir_path != 'ROOT' else 0
        depth_analysis[depth].append((dir_path, file_count))

    print(f"\nDirectory depth analysis:")
    for depth in sorted(depth_analysis.keys()):
        dirs_at_depth = depth_analysis[depth]
        total_files = sum(fc for _, fc in dirs_at_depth)
        print(f"  Depth {depth}: {len(dirs_at_depth)} directories, {total_files} files")

    # Identify main categories
    print("\n" + "="*80)
    print("DATA CATEGORIES (based on directory structure)")
    print("="*80)

    categories = defaultdict(lambda: {'dirs': [], 'files': 0})

    for dir_path, file_count in directories.items():
        if dir_path == 'ROOT':
            continue

        parts = dir_path.split('/')
        if len(parts) >= 2:
            # Extract category from path (e.g., dataset/clinical_data)
            category = '/'.join(parts[1:3]) if len(parts) >= 3 else parts[1]
            categories[category]['dirs'].append(dir_path)
            categories[category]['files'] += file_count

    # Sort by file count
    sorted_categories = sorted(categories.items(), key=lambda x: x[1]['files'], reverse=True)

    for category, data in sorted_categories[:20]:
        print(f"\n📁 {category}")
        print(f"   Files: {data['files']:,}")
        print(f"   Subdirectories: {len(data['dirs'])}")


def analyze_file_patterns(scan_data):
    """Analyze file naming patterns and relationships."""
    print("\n" + "="*80)
    print("FILE PATTERN ANALYSIS")
    print("="*80)

    file_types = scan_data['file_types']

    # Analyze .dat and .hea files (they appear paired)
    print("\n🔍 ECG Data Files (.dat and .hea):")
    if '.dat' in file_types and '.hea' in file_types:
        dat_count = file_types['.dat']['count']
        hea_count = file_types['.hea']['count']
        print(f"   .dat files: {dat_count:,} (binary waveform data)")
        print(f"   .hea files: {hea_count:,} (header metadata)")
        print(f"   Paired: {'YES - Equal counts!' if dat_count == hea_count else 'NO - Mismatch!'}")

        # Show examples
        print("\n   Example paths:")
        for example in file_types['.dat']['examples'][:3]:
            print(f"     {example}")

        # Extract patient IDs from paths
        dat_examples = file_types['.dat']['examples']
        if dat_examples:
            # Pattern: .../patient_id/patient_id_ecg_hash.dat
            sample_path = dat_examples[0]
            parts = sample_path.split('/')
            print(f"\n   Pattern structure:")
            print(f"     Base: {'/'.join(parts[:5])}")
            print(f"     Patient folder: {parts[5] if len(parts) > 5 else 'N/A'}")
            print(f"     Filename: {parts[-1] if parts else 'N/A'}")

    # Analyze JSON files
    print("\n🔍 JSON Files:")
    if '.json' in file_types:
        json_count = file_types['.json']['count']
        json_size = file_types['.json']['total_size'] / (1024**3)
        print(f"   Count: {json_count:,}")
        print(f"   Total size: {json_size:.2f} GB")

        # Categorize JSON files by directory
        json_by_category = defaultdict(int)
        for example in file_types['.json']['examples']:
            parts = example.split('/')
            if len(parts) >= 3:
                category = parts[2]  # e.g., clinical_data, cardiac_ecg, etc.
                json_by_category[category] += 1

        print("\n   Categories found:")
        for category, count in sorted(json_by_category.items(), key=lambda x: x[1], reverse=True):
            print(f"     {category}: examples include metadata files")

    # Analyze CSV files
    print("\n🔍 CSV Files:")
    if '.csv' in file_types:
        csv_count = file_types['.csv']['count']
        csv_size = file_types['.csv']['total_size'] / (1024**3)
        print(f"   Count: {csv_count:,}")
        print(f"   Total size: {csv_size:.2f} GB (59% of total storage!)")

        print("\n   Example files:")
        for example in file_types['.csv']['examples'][:5]:
            filename = example.split('/')[-1]
            print(f"     {filename}")


def identify_data_types(scan_data):
    """Identify what types of data are stored."""
    print("\n" + "="*80)
    print("DATA TYPE IDENTIFICATION")
    print("="*80)

    print("\n📊 Based on file paths and names, this appears to be:")
    print("\n1. MEDICAL RESEARCH DATA - AI-READI Project")
    print("   - AI-READI: Artificial Intelligence Ready and Equitable Atlas")
    print("   - Focus: Type 2 Diabetes Research")

    print("\n2. DATA MODALITIES PRESENT:")

    print("\n   🫀 CARDIAC DATA (ECG)")
    print("   - Location: dataset/cardiac_ecg/ecg_12lead/philips_tc30/")
    print("   - Format: WFDB format (.dat + .hea files)")
    print("   - Device: Philips TC30")
    print("   - Approx. 2,257 ECG recordings")

    print("\n   🏥 CLINICAL DATA (OMOP CDM)")
    print("   - Location: dataset/clinical_data/")
    print("   - Format: CSV files following OMOP Common Data Model")
    print("   - Files: observation.csv, measurement.csv, condition_occurrence.csv, etc.")
    print("   - Largest file: observation.csv (108 MB)")

    print("\n   🌡️ ENVIRONMENTAL SENSOR DATA")
    print("   - Location: dataset/environment/environmental_sensor/leelab_anura/")
    print("   - Format: CSV files (_ENV.csv)")
    print("   - Many large files (50-65 MB each)")
    print("   - Appears to be continuous monitoring data")

    print("\n   📋 METADATA")
    print("   - Location: Various dataset_description.json, manifest.tsv files")
    print("   - Purpose: Dataset structure, data quality, participant info")

    print("\n3. ORGANIZATION PATTERN:")
    print("   - Single study ID: 00b62456-0b93-4975-a992-42ba6a50ed5c")
    print("   - Organized by data modality (clinical, cardiac, environment)")
    print("   - Patient-level subdirectories (IDs like 1001, 1002, etc.)")
    print("   - Paired files for waveform data (.dat + .hea)")


def generate_recommendations(scan_data):
    """Generate initial data inspection strategy recommendations."""
    print("\n" + "="*80)
    print("RECOMMENDED INITIAL DATA INSPECTION STRATEGY")
    print("="*80)

    print("\n🎯 PHASE 1: Understanding the Data Model")
    print("   1. Read dataset_description.json for study metadata")
    print("   2. Review manifest.tsv files for data catalogs")
    print("   3. Examine OMOP CDM structure in clinical_data/")

    print("\n🎯 PHASE 2: Clinical Data Exploration")
    print("   1. Load and profile clinical CSV files")
    print("   2. Analyze patient demographics and cohort characteristics")
    print("   3. Examine temporal patterns in observations/measurements")
    print("   4. Check data completeness and quality")
    print("   Strategy: Use chunking for large files like observation.csv")

    print("\n🎯 PHASE 3: ECG Waveform Analysis")
    print("   1. Sample .dat/.hea files using WFDB library")
    print("   2. Extract signal characteristics (duration, sampling rate, leads)")
    print("   3. Visualize sample ECG traces")
    print("   4. Check for data quality issues")
    print("   Strategy: Start with small random sample (10-20 files)")

    print("\n🎯 PHASE 4: Environmental Data Analysis")
    print("   1. Sample environmental sensor CSV files")
    print("   2. Understand sensor types and measurements")
    print("   3. Analyze temporal coverage and sampling rates")
    print("   4. Link to patient IDs if possible")

    print("\n🎯 PHASE 5: Cross-Modal Integration")
    print("   1. Map patient IDs across modalities")
    print("   2. Analyze data completeness per patient")
    print("   3. Identify temporal alignment opportunities")

    print("\n💡 KEY CONSIDERATIONS:")
    print("   - Total size: 97.54 GB - too large for full download")
    print("   - Use streaming/chunking for large CSV files")
    print("   - Download representative samples of ECG data")
    print("   - Leverage blob storage for selective data access")
    print("   - Focus on metadata first to understand scope")


def main():
    """Main analysis function."""
    scan_data = load_latest_scan()

    if not scan_data:
        return

    print(f"Scan timestamp: {scan_data['scan_timestamp']}")
    print(f"Total blobs analyzed: {scan_data['total_blobs']:,}\n")

    # Run analyses
    analyze_directory_structure(scan_data)
    analyze_file_patterns(scan_data)
    identify_data_types(scan_data)
    generate_recommendations(scan_data)

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
