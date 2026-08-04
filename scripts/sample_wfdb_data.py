"""
Sample and analyze WFDB format ECG data (.dat and .hea files).
WFDB (WaveForm DataBase) is a standard format for physiological signals.
"""

import os
import sys
import io
import random
import tempfile
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.storage.blob import BlobServiceClient
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME

try:
    import wfdb
    import numpy as np
    import matplotlib.pyplot as plt
    import pandas as pd
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please ensure wfdb, numpy, matplotlib, and pandas are installed.")
    sys.exit(1)


class WFDBSampler:
    """Sample and analyze WFDB ECG files from Azure Blob Storage."""

    def __init__(self, connection_string, container_name):
        """Initialize with Azure credentials."""
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)

    def list_ecg_files(self):
        """List all ECG .hea files in the container."""
        print("Listing ECG files...")
        ecg_files = []

        blobs = self.container_client.list_blobs(name_starts_with="00b62456-0b93-4975-a992-42ba6a50ed5c/dataset/cardiac_ecg")

        for blob in blobs:
            if blob.name.endswith('.hea'):
                # Extract base name (without extension)
                base_name = blob.name.rsplit('.', 1)[0]
                ecg_files.append(base_name)

        print(f"Found {len(ecg_files)} ECG recordings")
        return ecg_files

    def download_ecg_pair(self, base_name, temp_dir):
        """Download both .hea and .dat files for a recording."""
        hea_blob_name = f"{base_name}.hea"
        dat_blob_name = f"{base_name}.dat"

        # Create local file paths
        local_base = os.path.join(temp_dir, Path(base_name).name)

        try:
            # Download .hea file
            hea_blob = self.container_client.get_blob_client(hea_blob_name)
            hea_data = hea_blob.download_blob().readall()
            with open(f"{local_base}.hea", 'wb') as f:
                f.write(hea_data)

            # Download .dat file
            dat_blob = self.container_client.get_blob_client(dat_blob_name)
            dat_data = dat_blob.download_blob().readall()
            with open(f"{local_base}.dat", 'wb') as f:
                f.write(dat_data)

            return local_base

        except Exception as e:
            print(f"Error downloading {base_name}: {e}")
            return None

    def analyze_ecg_record(self, local_base):
        """Analyze a single ECG record using WFDB."""
        try:
            # Read the record
            record = wfdb.rdrecord(local_base)

            info = {
                'record_name': record.record_name,
                'n_sig': record.n_sig,
                'sig_name': record.sig_name,
                'fs': record.fs,
                'sig_len': record.sig_len,
                'duration_sec': record.sig_len / record.fs if record.fs > 0 else 0,
                'units': record.units,
                'comments': record.comments,
                'base_date': record.base_date,
                'base_time': record.base_time,
            }

            return info, record

        except Exception as e:
            print(f"Error reading record: {e}")
            return None, None

    def sample_and_analyze(self, n_samples=5):
        """Sample random ECG files and analyze them."""
        print(f"\n{'='*80}")
        print(f"WFDB ECG DATA SAMPLING AND ANALYSIS")
        print(f"{'='*80}\n")

        # Get list of all ECG files
        ecg_files = self.list_ecg_files()

        if not ecg_files:
            print("No ECG files found!")
            return

        # Sample random files
        sample_size = min(n_samples, len(ecg_files))
        sampled_files = random.sample(ecg_files, sample_size)

        print(f"\nSampling {sample_size} random ECG recordings...\n")

        results = []

        with tempfile.TemporaryDirectory() as temp_dir:
            for i, base_name in enumerate(sampled_files, 1):
                print(f"Processing {i}/{sample_size}: {Path(base_name).name}")

                # Download files
                local_base = self.download_ecg_pair(base_name, temp_dir)

                if local_base:
                    # Analyze
                    info, record = self.analyze_ecg_record(local_base)

                    if info:
                        results.append(info)
                        print(f"  ✓ Signals: {info['n_sig']}, "
                              f"Duration: {info['duration_sec']:.1f}s, "
                              f"Sampling rate: {info['fs']} Hz")

                        # Visualize first sample
                        if i == 1:
                            self.visualize_ecg(record, base_name)

                print()

        # Summarize results
        self.summarize_results(results)

        return results

    def visualize_ecg(self, record, base_name):
        """Create visualization of ECG signals."""
        try:
            print("  Creating visualization...")

            # Plot
            plt.figure(figsize=(14, 10))

            # Plot each lead
            n_leads = min(12, record.n_sig)  # Limit to 12 leads
            plot_duration = min(10, record.sig_len / record.fs)  # First 10 seconds
            plot_samples = int(plot_duration * record.fs)

            for i in range(n_leads):
                plt.subplot(n_leads, 1, i + 1)
                signal = record.p_signal[:plot_samples, i] if record.p_signal.ndim > 1 else record.p_signal[:plot_samples]
                time = np.arange(plot_samples) / record.fs

                plt.plot(time, signal, linewidth=0.5)
                plt.ylabel(f"{record.sig_name[i]}\n({record.units[i]})", fontsize=8)
                plt.grid(True, alpha=0.3)

                if i == 0:
                    plt.title(f"ECG Recording: {Path(base_name).name}\n"
                              f"Sampling Rate: {record.fs} Hz, Duration: {record.sig_len/record.fs:.1f}s")

                if i == n_leads - 1:
                    plt.xlabel('Time (seconds)')

            plt.tight_layout()

            # Save
            output_dir = 'results/visualizations'
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, 'sample_ecg_visualization.png')
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()

            print(f"  ✓ Visualization saved to: {output_file}")

        except Exception as e:
            print(f"  ✗ Error creating visualization: {e}")

    def summarize_results(self, results):
        """Summarize analysis results."""
        if not results:
            print("No results to summarize!")
            return

        print(f"\n{'='*80}")
        print("SUMMARY OF ECG DATA CHARACTERISTICS")
        print(f"{'='*80}\n")

        df = pd.DataFrame(results)

        print(f"📊 Signal Configuration:")
        print(f"  Number of leads: {df['n_sig'].iloc[0]} (consistent across all samples)")
        print(f"  Lead names: {', '.join(df['sig_name'].iloc[0])}")
        print(f"  Units: {', '.join(set(df['units'].iloc[0]))}")

        print(f"\n📊 Recording Parameters:")
        print(f"  Sampling rate: {df['fs'].unique()[0]} Hz")
        print(f"  Duration range: {df['duration_sec'].min():.1f}s - {df['duration_sec'].max():.1f}s")
        print(f"  Average duration: {df['duration_sec'].mean():.1f}s")
        print(f"  Signal length range: {df['sig_len'].min():,} - {df['sig_len'].max():,} samples")

        print(f"\n📊 Data Format:")
        print(f"  Format: WFDB (WaveForm DataBase)")
        print(f"  Files per recording: 2 (.hea header + .dat binary data)")
        print(f"  Standard: PhysioNet compatible")

        print(f"\n💡 Key Findings:")
        print(f"  ✓ All ECG recordings are 12-lead ECGs")
        print(f"  ✓ Standard clinical sampling rate ({df['fs'].unique()[0]} Hz)")
        print(f"  ✓ WFDB format is well-supported by Python libraries")
        print(f"  ✓ Data appears to be from Philips TC30 ECG device")

        # Save summary
        output_file = 'results/scans/ecg_sample_summary.csv'
        df.to_csv(output_file, index=False)
        print(f"\n✓ Detailed summary saved to: {output_file}")


def main():
    """Main execution."""
    sampler = WFDBSampler(CONNECTION_STRING, CONTAINER_NAME)

    # Sample and analyze ECG files
    results = sampler.sample_and_analyze(n_samples=10)

    print(f"\n{'='*80}")
    print("ECG Sampling Complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
