"""
Create a comprehensive summary report with visualizations.
"""

import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def load_scan_data():
    """Load the latest scan results."""
    scan_dir = 'results/scans'
    scan_files = sorted([f for f in os.listdir(scan_dir) if f.startswith('blob_scan_')])

    if not scan_files:
        return None

    latest_scan = scan_files[-1]
    with open(f'{scan_dir}/{latest_scan}', 'r') as f:
        return json.load(f)


def create_visualizations(scan_data):
    """Create summary visualizations."""
    print("Creating summary visualizations...")

    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (16, 10)

    fig = plt.figure(figsize=(16, 12))

    # 1. File type distribution by count
    ax1 = plt.subplot(2, 3, 1)
    file_types = scan_data['file_types']
    file_type_df = pd.DataFrame([
        {'extension': ext, 'count': data['count']}
        for ext, data in file_types.items()
    ]).sort_values('count', ascending=True)

    ax1.barh(file_type_df['extension'], file_type_df['count'], color='steelblue')
    ax1.set_xlabel('File Count', fontsize=10)
    ax1.set_title('File Type Distribution (Count)', fontsize=12, fontweight='bold')
    ax1.set_xscale('log')

    # 2. File type distribution by size
    ax2 = plt.subplot(2, 3, 2)
    file_size_df = pd.DataFrame([
        {'extension': ext, 'size_gb': data['total_size'] / (1024**3)}
        for ext, data in file_types.items()
    ]).sort_values('size_gb', ascending=True)

    ax2.barh(file_size_df['extension'], file_size_df['size_gb'], color='coral')
    ax2.set_xlabel('Size (GB)', fontsize=10)
    ax2.set_title('File Type Distribution (Size)', fontsize=12, fontweight='bold')

    # 3. Top-level folder distribution
    ax3 = plt.subplot(2, 3, 3)
    folders = scan_data['top_level_folders']
    folder_df = pd.DataFrame([
        {'folder': k, 'files': v}
        for k, v in folders.items()
    ]).sort_values('files', ascending=True)

    ax3.barh(folder_df['folder'], folder_df['files'], color='mediumseagreen')
    ax3.set_xlabel('File Count', fontsize=10)
    ax3.set_title('Top-Level Folders', fontsize=12, fontweight='bold')
    ax3.set_xscale('log')

    # 4. Data modality breakdown
    ax4 = plt.subplot(2, 3, 4)
    modalities = {
        'Clinical Data\n(OMOP CDM)': file_types.get('.csv', {}).get('total_size', 0) / (1024**3),
        'Wearable Data\n(JSON)': file_types.get('.json', {}).get('total_size', 0) / (1024**3),
        'ECG Data\n(WFDB)': (file_types.get('.dat', {}).get('total_size', 0) +
                             file_types.get('.hea', {}).get('total_size', 0)) / (1024**3),
        'Other': sum(v.get('total_size', 0) for k, v in file_types.items()
                    if k not in ['.csv', '.json', '.dat', '.hea']) / (1024**3)
    }

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    wedges, texts, autotexts = ax4.pie(modalities.values(), labels=modalities.keys(),
                                         autopct='%1.1f%%', colors=colors, startangle=90)
    ax4.set_title('Storage by Data Modality', fontsize=12, fontweight='bold')

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    # 5. Largest files
    ax5 = plt.subplot(2, 3, 5)
    largest = scan_data['largest_files'][:10]
    sizes_mb = [f['size'] / (1024**2) for f in largest]
    names = [f['name'].split('/')[-1][:30] for f in largest]

    ax5.barh(range(len(names)), sizes_mb, color='mediumpurple')
    ax5.set_yticks(range(len(names)))
    ax5.set_yticklabels(names, fontsize=8)
    ax5.set_xlabel('Size (MB)', fontsize=10)
    ax5.set_title('Top 10 Largest Files', fontsize=12, fontweight='bold')
    ax5.invert_yaxis()

    # 6. Summary statistics
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')

    summary_text = f"""
    AI-READI Dataset Summary

    Total Files: {scan_data['total_blobs']:,}
    Total Size: {scan_data['total_size_gb']:.2f} GB

    File Types: {len(file_types)}
    Directories: {len(scan_data['directory_structure']):,}

    Scan Date: {scan_data['scan_timestamp'][:10]}

    Data Modalities:
    • Clinical Data (OMOP CDM)
    • 12-lead ECG (WFDB)
    • Environmental Sensors
    • Activity Monitors
    • Blood Glucose Monitors

    Key Characteristics:
    • {file_types.get('.json', {}).get('count', 0):,} JSON files
    • {file_types.get('.csv', {}).get('count', 0):,} CSV files
    • {file_types.get('.dat', {}).get('count', 0):,} ECG recordings
    """

    ax6.text(0.1, 0.9, summary_text, fontsize=11, verticalalignment='top',
             fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.suptitle('AI-READI Dataset - Comprehensive Overview',
                 fontsize=16, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    # Save
    output_file = 'results/visualizations/dataset_summary_dashboard.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Saved to: {output_file}")

    plt.close()


def create_text_report(scan_data):
    """Create a text summary report."""
    print("\nCreating text summary report...")

    report = []
    report.append("="*80)
    report.append("AI-READI DATASET - COMPREHENSIVE SUMMARY REPORT")
    report.append("="*80)
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Scan Date: {scan_data['scan_timestamp']}")
    report.append("\n" + "="*80)
    report.append("OVERVIEW")
    report.append("="*80)
    report.append(f"\nTotal Blobs: {scan_data['total_blobs']:,}")
    report.append(f"Total Size: {scan_data['total_size_gb']:.2f} GB")
    report.append(f"Unique File Types: {len(scan_data['file_types'])}")
    report.append(f"Unique Directories: {len(scan_data['directory_structure']):,}")

    report.append("\n" + "="*80)
    report.append("FILE TYPES")
    report.append("="*80)

    file_types = scan_data['file_types']
    file_type_list = sorted(file_types.items(), key=lambda x: x[1]['count'], reverse=True)

    for ext, data in file_type_list:
        size_gb = data['total_size'] / (1024**3)
        report.append(f"\n{ext}:")
        report.append(f"  Count: {data['count']:,}")
        report.append(f"  Size: {size_gb:.2f} GB")
        report.append(f"  Examples: {', '.join(data['examples'][:2])}")

    report.append("\n" + "="*80)
    report.append("DATA MODALITIES")
    report.append("="*80)

    report.append("\n1. Clinical Data (OMOP Common Data Model)")
    csv_size = file_types.get('.csv', {}).get('total_size', 0) / (1024**3)
    csv_count = file_types.get('.csv', {}).get('count', 0)
    report.append(f"   Files: {csv_count:,} CSV files")
    report.append(f"   Size: {csv_size:.2f} GB")
    report.append("   Tables: person, observation, measurement, condition_occurrence, etc.")

    report.append("\n2. ECG Data (WFDB Format)")
    dat_count = file_types.get('.dat', {}).get('count', 0)
    dat_size = file_types.get('.dat', {}).get('total_size', 0) / (1024**2)
    hea_size = file_types.get('.hea', {}).get('total_size', 0) / (1024**2)
    report.append(f"   Recordings: {dat_count:,}")
    report.append(f"   Size: {(dat_size + hea_size):.2f} MB")
    report.append("   Type: 12-lead ECG, 500 Hz, ~11 seconds each")

    report.append("\n3. Wearable & Sensor Data")
    json_count = file_types.get('.json', {}).get('count', 0)
    json_size = file_types.get('.json', {}).get('total_size', 0) / (1024**3)
    report.append(f"   Files: {json_count:,} JSON files")
    report.append(f"   Size: {json_size:.2f} GB")
    report.append("   Includes: Activity monitors, blood glucose, environmental sensors")

    report.append("\n" + "="*80)
    report.append("KEY FINDINGS")
    report.append("="*80)
    report.append("\n✓ Dataset follows FAIR principles")
    report.append("✓ Multiple data modalities for comprehensive analysis")
    report.append("✓ Standardized formats (OMOP CDM, WFDB)")
    report.append("✓ Patient-centric organization")
    report.append("✓ Suitable for multi-modal machine learning")

    report.append("\n" + "="*80)

    # Save report
    output_file = 'results/scans/summary_report.txt'
    with open(output_file, 'w') as f:
        f.write('\n'.join(report))

    print(f"✓ Saved to: {output_file}")

    # Also print to console
    print('\n' + '\n'.join(report))


def main():
    """Main execution."""
    print(f"\n{'='*80}")
    print("CREATING COMPREHENSIVE SUMMARY REPORT")
    print(f"{'='*80}\n")

    scan_data = load_scan_data()

    if not scan_data:
        print("No scan data found. Please run blob_storage_scanner.py first.")
        return

    create_visualizations(scan_data)
    create_text_report(scan_data)

    print(f"\n{'='*80}")
    print("Summary report complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
