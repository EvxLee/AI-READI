#!/usr/bin/env python3
"""
Master Initial Data Inspection Runner Script
Executes the complete initial data inspection workflow in sequence.
"""

import os
import sys
import subprocess
from datetime import datetime


def run_script(script_path, description):
    """Run a Python script and handle errors."""
    print(f"\n{'='*80}")
    print(f"RUNNING: {description}")
    print(f"Script: {script_path}")
    print(f"{'='*80}\n")

    start_time = datetime.now()

    try:
        result = subprocess.run(
            ['python3', script_path],
            check=True,
            capture_output=False,
            text=True
        )

        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n✓ Completed in {duration:.1f} seconds")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error running {script_path}")
        print(f"Return code: {e.returncode}")
        return False


def main():
    """Execute complete initial data inspection workflow."""
    print(f"\n{'='*80}")
    print("AI-READI DATASET - COMPLETE INITIAL DATA INSPECTION")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    workflow_start = datetime.now()

    # Define workflow steps
    steps = [
        {
            'script': 'scripts/blob_storage_scanner.py',
            'description': 'Step 1: Scan Azure Blob Storage Container',
            'required': True
        },
        {
            'script': 'scripts/analyze_structure.py',
            'description': 'Step 2: Analyze Directory Structure',
            'required': True
        },
        {
            'script': 'scripts/explore_metadata.py',
            'description': 'Step 3: Explore Dataset Metadata',
            'required': False
        },
        {
            'script': 'scripts/explore_clinical_data.py',
            'description': 'Step 4: Explore Clinical Data (OMOP CDM)',
            'required': False
        },
        {
            'script': 'scripts/sample_wfdb_data.py',
            'description': 'Step 5: Sample and Analyze ECG Data (WFDB)',
            'required': False
        }
    ]

    # Execute workflow
    results = []
    for step in steps:
        success = run_script(step['script'], step['description'])
        results.append({
            'step': step['description'],
            'success': success,
            'required': step['required']
        })

        if not success and step['required']:
            print(f"\n✗ Required step failed. Stopping workflow.")
            break

    # Print summary
    workflow_duration = (datetime.now() - workflow_start).total_seconds()

    print(f"\n{'='*80}")
    print("WORKFLOW SUMMARY")
    print(f"{'='*80}\n")

    successful = sum(1 for r in results if r['success'])
    total = len(results)

    print(f"Steps completed: {successful}/{total}")
    print(f"Total duration: {workflow_duration:.1f} seconds\n")

    print("Step Results:")
    for i, result in enumerate(results, 1):
        status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
        print(f"  {i}. {status} - {result['step']}")

    print(f"\n{'='*80}")

    if successful == total:
        print("🎉 COMPLETE INITIAL DATA INSPECTION FINISHED SUCCESSFULLY!")
        print(f"{'='*80}\n")

        print("Next Steps:")
        print("  1. Review results in results/scans/")
        print("  2. Check visualizations in results/visualizations/")
        print("  3. Examine data samples in data/samples/")
        print("  4. Open Jupyter notebook: jupyter notebook notebooks/01_initial_data_inspection.ipynb")
        print("  5. Read INITIAL_DATA_INSPECTION_GUIDE.md for detailed documentation")

    else:
        print("⚠️  Some steps failed. Please review errors above.")
        print(f"{'='*80}\n")

    print()


if __name__ == "__main__":
    main()
