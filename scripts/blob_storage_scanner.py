"""
Azure Blob Storage Scanner
Performs comprehensive analysis of blob container structure and contents.
"""

import os
import sys
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import mimetypes

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.storage.blob import BlobServiceClient, ContainerClient
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME
from tqdm import tqdm


class BlobStorageScanner:
    """Comprehensive scanner for Azure Blob Storage containers."""

    def __init__(self, connection_string, container_name):
        """Initialize scanner with Azure credentials."""
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)

        # Statistics storage
        self.stats = {
            'total_blobs': 0,
            'total_size_bytes': 0,
            'total_size_gb': 0,
            'file_types': defaultdict(lambda: {'count': 0, 'total_size': 0, 'examples': []}),
            'directory_structure': defaultdict(int),
            'top_level_folders': defaultdict(int),
            'largest_files': [],
            'scan_timestamp': datetime.now().isoformat(),
        }

    def human_readable_size(self, size_bytes):
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def extract_file_info(self, blob_name, blob_size):
        """Extract file type and directory information from blob name."""
        # Get file extension
        path_parts = blob_name.split('/')
        filename = path_parts[-1]
        extension = Path(filename).suffix.lower() if '.' in filename else 'NO_EXTENSION'

        # Get directory depth and top-level folder
        directory_depth = len(path_parts) - 1
        top_level_folder = path_parts[0] if len(path_parts) > 1 else 'ROOT'

        # Get directory path
        directory_path = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else 'ROOT'

        return {
            'extension': extension,
            'directory_depth': directory_depth,
            'top_level_folder': top_level_folder,
            'directory_path': directory_path,
            'filename': filename
        }

    def scan_container(self):
        """Perform comprehensive scan of the blob container."""
        print(f"\n{'='*80}")
        print(f"Starting comprehensive scan of container: {self.container_name}")
        print(f"{'='*80}\n")

        try:
            # Test connection
            _ = self.container_client.get_container_properties()
            print("✓ Successfully connected to Azure Blob Storage")
            print(f"✓ Container '{self.container_name}' is accessible\n")
        except Exception as e:
            print(f"✗ Error connecting to container: {e}")
            return None

        # List all blobs with progress bar
        print("Scanning all blobs in container...")
        blob_list = list(self.container_client.list_blobs())

        print(f"Found {len(blob_list)} total blobs. Analyzing...\n")

        for blob in tqdm(blob_list, desc="Analyzing blobs"):
            blob_name = blob.name
            blob_size = blob.size

            # Update total statistics
            self.stats['total_blobs'] += 1
            self.stats['total_size_bytes'] += blob_size

            # Extract file information
            file_info = self.extract_file_info(blob_name, blob_size)

            # Update file type statistics
            ext = file_info['extension']
            self.stats['file_types'][ext]['count'] += 1
            self.stats['file_types'][ext]['total_size'] += blob_size

            # Store example filenames (up to 5 per type)
            if len(self.stats['file_types'][ext]['examples']) < 5:
                self.stats['file_types'][ext]['examples'].append(blob_name)

            # Update directory statistics
            self.stats['directory_structure'][file_info['directory_path']] += 1
            self.stats['top_level_folders'][file_info['top_level_folder']] += 1

            # Track largest files
            self.stats['largest_files'].append({
                'name': blob_name,
                'size': blob_size,
                'size_readable': self.human_readable_size(blob_size)
            })

        # Post-processing
        self.stats['total_size_gb'] = self.stats['total_size_bytes'] / (1024**3)

        # Sort and limit largest files
        self.stats['largest_files'] = sorted(
            self.stats['largest_files'],
            key=lambda x: x['size'],
            reverse=True
        )[:20]

        # Convert defaultdicts to regular dicts for JSON serialization
        self.stats['file_types'] = dict(self.stats['file_types'])
        self.stats['directory_structure'] = dict(self.stats['directory_structure'])
        self.stats['top_level_folders'] = dict(self.stats['top_level_folders'])

        return self.stats

    def print_summary(self):
        """Print human-readable summary of scan results."""
        print(f"\n{'='*80}")
        print("SCAN RESULTS SUMMARY")
        print(f"{'='*80}\n")

        # Overall statistics
        print("📊 OVERALL STATISTICS")
        print(f"  Total blobs: {self.stats['total_blobs']:,}")
        print(f"  Total size: {self.human_readable_size(self.stats['total_size_bytes'])} ({self.stats['total_size_gb']:.2f} GB)")
        print(f"  Unique file types: {len(self.stats['file_types'])}")
        print(f"  Unique directories: {len(self.stats['directory_structure'])}")
        print(f"  Top-level folders: {len(self.stats['top_level_folders'])}")

        # File types breakdown
        print(f"\n📁 FILE TYPES BREAKDOWN (sorted by count)")
        file_types_sorted = sorted(
            self.stats['file_types'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )

        for ext, data in file_types_sorted[:15]:  # Show top 15
            size_readable = self.human_readable_size(data['total_size'])
            print(f"  {ext:20s} | Count: {data['count']:6,} | Size: {size_readable:12s}")

        if len(file_types_sorted) > 15:
            print(f"  ... and {len(file_types_sorted) - 15} more file types")

        # Top-level folders
        print(f"\n📂 TOP-LEVEL FOLDERS")
        folders_sorted = sorted(
            self.stats['top_level_folders'].items(),
            key=lambda x: x[1],
            reverse=True
        )

        for folder, count in folders_sorted[:10]:  # Show top 10
            print(f"  {folder:40s} | Files: {count:6,}")

        # Largest files
        print(f"\n💾 LARGEST FILES (Top 10)")
        for i, file_info in enumerate(self.stats['largest_files'][:10], 1):
            print(f"  {i:2d}. {file_info['size_readable']:12s} | {file_info['name']}")

        # Example files by type
        print(f"\n📝 EXAMPLE FILES BY TYPE")
        for ext, data in file_types_sorted[:5]:  # Show examples for top 5 types
            print(f"\n  {ext} files (showing up to 3 examples):")
            for example in data['examples'][:3]:
                print(f"    - {example}")

        print(f"\n{'='*80}\n")

    def save_results(self, output_dir='results/scans'):
        """Save scan results to JSON file."""
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(output_dir, f'blob_scan_{timestamp}.json')

        with open(output_file, 'w') as f:
            json.dump(self.stats, f, indent=2)

        print(f"✓ Detailed results saved to: {output_file}")
        return output_file


def main():
    """Main execution function."""
    scanner = BlobStorageScanner(CONNECTION_STRING, CONTAINER_NAME)

    # Perform scan
    results = scanner.scan_container()

    if results:
        # Print summary
        scanner.print_summary()

        # Save detailed results
        output_file = scanner.save_results()

        print("\n✓ Scan completed successfully!")
        print(f"✓ Review the JSON file for complete details: {output_file}")
    else:
        print("\n✗ Scan failed. Please check your Azure credentials and connection.")
        sys.exit(1)


if __name__ == "__main__":
    main()
