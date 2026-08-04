"""
Explore metadata and JSON files to understand dataset structure.
This is Phase 1 of the initial data inspection workflow.
"""

import os
import sys
import json
from pprint import pprint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.storage.blob import BlobServiceClient
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME, STUDY_ID


class MetadataExplorer:
    """Explore dataset metadata and JSON files."""

    def __init__(self, connection_string, container_name):
        """Initialize with Azure credentials."""
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)
        self.study_id = STUDY_ID

    def download_json(self, blob_name):
        """Download and parse a JSON file."""
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            json_data = blob_client.download_blob().readall()
            return json.loads(json_data)
        except Exception as e:
            print(f"Error downloading {blob_name}: {e}")
            return None

    def explore_dataset_description(self):
        """Explore the main dataset description."""
        print(f"\n{'='*80}")
        print("DATASET DESCRIPTION")
        print(f"{'='*80}\n")

        blob_name = f"{self.study_id}/dataset/dataset_description.json"
        data = self.download_json(blob_name)

        if data:
            print("📋 Dataset Overview:")
            for key, value in data.items():
                if isinstance(value, (str, int, float)):
                    print(f"  {key}: {value}")
                elif isinstance(value, list) and len(value) < 10:
                    print(f"  {key}: {', '.join(map(str, value))}")
                else:
                    print(f"  {key}: <{type(value).__name__}>")

            # Save to file
            output_file = 'results/scans/dataset_description.json'
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n✓ Full dataset description saved to: {output_file}")

        return data

    def explore_participants(self):
        """Explore participant information."""
        print(f"\n{'='*80}")
        print("PARTICIPANT INFORMATION")
        print(f"{'='*80}\n")

        # Try TSV file first
        tsv_blob_name = f"{self.study_id}/dataset/participants.tsv"

        try:
            blob_client = self.container_client.get_blob_client(tsv_blob_name)
            tsv_data = blob_client.download_blob().readall().decode('utf-8')

            lines = tsv_data.strip().split('\n')
            headers = lines[0].split('\t')

            print(f"📊 Participant Data Structure:")
            print(f"  Columns: {', '.join(headers)}")
            print(f"  Total participants: {len(lines) - 1}")

            # Show first few rows
            print(f"\n  First 3 participants:")
            for i, line in enumerate(lines[1:4], 1):
                print(f"    {i}. {line}")

            # Save sample
            output_file = 'results/scans/participants_sample.tsv'
            with open(output_file, 'w') as f:
                f.write('\n'.join(lines[:20]))  # Save first 20 rows
            print(f"\n✓ Sample saved to: {output_file}")

        except Exception as e:
            print(f"Could not load participants.tsv: {e}")

    def explore_manifests(self):
        """Explore manifest files."""
        print(f"\n{'='*80}")
        print("DATA MANIFESTS")
        print(f"{'='*80}\n")

        # Look for manifest files
        manifest_blobs = []
        blobs = self.container_client.list_blobs(name_starts_with=f"{self.study_id}/dataset")

        for blob in blobs:
            if 'manifest' in blob.name.lower() and blob.name.endswith('.tsv'):
                manifest_blobs.append(blob.name)

        print(f"Found {len(manifest_blobs)} manifest files:\n")

        for manifest_name in manifest_blobs:
            print(f"📄 {manifest_name.split('/')[-2:]}")

            try:
                blob_client = self.container_client.get_blob_client(manifest_name)
                manifest_data = blob_client.download_blob().readall().decode('utf-8')

                lines = manifest_data.strip().split('\n')
                headers = lines[0].split('\t')

                print(f"   Columns: {', '.join(headers)}")
                print(f"   Entries: {len(lines) - 1}")

                # Save
                category = manifest_name.split('/')[-2]
                output_file = f'results/scans/manifest_{category}.tsv'
                with open(output_file, 'w') as f:
                    f.write('\n'.join(lines[:50]))  # Save first 50 rows
                print(f"   ✓ Saved to: {output_file}\n")

            except Exception as e:
                print(f"   Error: {e}\n")

    def explore_data_quality(self):
        """Explore data quality metadata."""
        print(f"\n{'='*80}")
        print("DATA QUALITY REPORTS")
        print(f"{'='*80}\n")

        dqd_blob_name = f"{self.study_id}/dataset/clinical_data/dqd_omop.json"
        data = self.download_json(dqd_blob_name)

        if data:
            print("📊 Data Quality Dashboard (OMOP CDM):")

            # Count checks
            if isinstance(data, dict):
                if 'CheckResults' in data:
                    checks = data['CheckResults']
                    print(f"  Total quality checks: {len(checks)}")

                    # Categorize by status
                    passed = sum(1 for c in checks if c.get('passed', False))
                    failed = sum(1 for c in checks if not c.get('passed', False))

                    print(f"  Passed: {passed}")
                    print(f"  Failed: {failed}")

                    # Show some failed checks
                    print(f"\n  Sample failed checks:")
                    failed_checks = [c for c in checks if not c.get('passed', False)][:5]
                    for check in failed_checks:
                        print(f"    - {check.get('checkDescription', 'N/A')}")

            # Save
            output_file = 'results/scans/data_quality_report.json'
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n✓ Full report saved to: {output_file}")


def main():
    """Main execution."""
    print(f"\n{'='*80}")
    print("METADATA EXPLORATION - AI-READI Dataset")
    print(f"{'='*80}")

    explorer = MetadataExplorer(CONNECTION_STRING, CONTAINER_NAME)

    # Explore different metadata sources
    explorer.explore_dataset_description()
    explorer.explore_participants()
    explorer.explore_manifests()
    explorer.explore_data_quality()

    print(f"\n{'='*80}")
    print("Metadata exploration complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
