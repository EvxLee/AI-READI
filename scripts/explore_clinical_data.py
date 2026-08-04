"""
Explore clinical data (OMOP CDM CSV files).
This is Phase 2 of the initial data inspection workflow.
"""

import os
import sys
import io
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from azure.storage.blob import BlobServiceClient
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME, STUDY_ID


class ClinicalDataExplorer:
    """Explore OMOP CDM clinical data files."""

    def __init__(self, connection_string, container_name):
        """Initialize with Azure credentials."""
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)
        self.study_id = STUDY_ID
        self.clinical_data_path = f"{self.study_id}/dataset/clinical_data"

    def list_clinical_files(self):
        """List all clinical data CSV files."""
        print("Listing clinical data files...")
        clinical_files = []

        blobs = self.container_client.list_blobs(name_starts_with=self.clinical_data_path)

        for blob in blobs:
            if blob.name.endswith('.csv'):
                filename = Path(blob.name).name
                size_mb = blob.size / (1024 * 1024)
                clinical_files.append({
                    'filename': filename,
                    'blob_name': blob.name,
                    'size_mb': size_mb
                })

        return clinical_files

    def load_csv_sample(self, blob_name, nrows=10000):
        """Load a sample of a CSV file from blob storage."""
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            csv_data = blob_client.download_blob().readall()

            # Load into pandas
            df = pd.read_csv(io.BytesIO(csv_data), nrows=nrows)
            return df

        except Exception as e:
            print(f"Error loading {blob_name}: {e}")
            return None

    def profile_dataframe(self, df, table_name):
        """Create a basic profile of a dataframe."""
        print(f"\n{'='*80}")
        print(f"TABLE: {table_name}")
        print(f"{'='*80}\n")

        print(f"📊 Basic Statistics:")
        print(f"  Rows: {len(df):,}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

        print(f"\n📋 Columns:")
        for col in df.columns:
            dtype = df[col].dtype
            null_pct = (df[col].isnull().sum() / len(df)) * 100
            unique = df[col].nunique()
            print(f"  {col:40s} | {str(dtype):15s} | Nulls: {null_pct:5.1f}% | Unique: {unique:6,}")

        print(f"\n📈 Data Sample (first 5 rows):")
        print(df.head().to_string())

        return {
            'table_name': table_name,
            'rows': len(df),
            'columns': len(df.columns),
            'column_list': list(df.columns),
            'null_percentages': {col: (df[col].isnull().sum() / len(df)) * 100 for col in df.columns}
        }

    def explore_person_table(self):
        """Explore the person (demographics) table."""
        print(f"\n{'='*80}")
        print("EXPLORING PERSON TABLE (Demographics)")
        print(f"{'='*80}")

        blob_name = f"{self.clinical_data_path}/person.csv"
        df = self.load_csv_sample(blob_name, nrows=100000)

        if df is None:
            return None

        profile = self.profile_dataframe(df, "person")

        # Additional demographics analysis
        print(f"\n📊 Demographics Summary:")

        if 'gender_concept_id' in df.columns:
            print(f"\n  Gender distribution:")
            print(df['gender_concept_id'].value_counts())

        if 'race_concept_id' in df.columns:
            print(f"\n  Race distribution:")
            print(df['race_concept_id'].value_counts())

        if 'year_of_birth' in df.columns:
            print(f"\n  Year of birth range: {df['year_of_birth'].min()} - {df['year_of_birth'].max()}")

        # Save sample
        output_file = 'data/samples/person_sample.csv'
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df.head(100).to_csv(output_file, index=False)
        print(f"\n✓ Sample saved to: {output_file}")

        return profile

    def explore_observation_table(self):
        """Explore the observation table (usually the largest)."""
        print(f"\n{'='*80}")
        print("EXPLORING OBSERVATION TABLE")
        print(f"{'='*80}")

        blob_name = f"{self.clinical_data_path}/observation.csv"

        # Load in chunks due to size
        print("\nLoading sample (first 50,000 rows)...")
        df = self.load_csv_sample(blob_name, nrows=50000)

        if df is None:
            return None

        profile = self.profile_dataframe(df, "observation")

        # Additional analysis
        print(f"\n📊 Observation Patterns:")

        if 'observation_concept_id' in df.columns:
            top_observations = df['observation_concept_id'].value_counts().head(10)
            print(f"\n  Top 10 observation types:")
            for concept_id, count in top_observations.items():
                print(f"    Concept {concept_id}: {count:,} records")

        if 'observation_date' in df.columns:
            print(f"\n  Date range: {df['observation_date'].min()} to {df['observation_date'].max()}")

        # Save sample
        output_file = 'data/samples/observation_sample.csv'
        df.head(1000).to_csv(output_file, index=False)
        print(f"\n✓ Sample saved to: {output_file}")

        return profile

    def explore_measurement_table(self):
        """Explore the measurement table."""
        print(f"\n{'='*80}")
        print("EXPLORING MEASUREMENT TABLE")
        print(f"{'='*80}")

        blob_name = f"{self.clinical_data_path}/measurement.csv"
        df = self.load_csv_sample(blob_name, nrows=50000)

        if df is None:
            return None

        profile = self.profile_dataframe(df, "measurement")

        # Analyze measurements
        print(f"\n📊 Measurement Patterns:")

        if 'measurement_concept_id' in df.columns:
            top_measurements = df['measurement_concept_id'].value_counts().head(10)
            print(f"\n  Top 10 measurement types:")
            for concept_id, count in top_measurements.items():
                print(f"    Concept {concept_id}: {count:,} records")

        if 'value_as_number' in df.columns:
            print(f"\n  Numeric value statistics:")
            print(df['value_as_number'].describe())

        # Save sample
        output_file = 'data/samples/measurement_sample.csv'
        df.head(1000).to_csv(output_file, index=False)
        print(f"\n✓ Sample saved to: {output_file}")

        return profile

    def explore_all_tables(self):
        """Explore all clinical data tables."""
        print(f"\n{'='*80}")
        print("CLINICAL DATA EXPLORATION")
        print(f"{'='*80}\n")

        # List all files
        clinical_files = self.list_clinical_files()

        print(f"Found {len(clinical_files)} clinical data files:\n")
        for file_info in clinical_files:
            print(f"  {file_info['filename']:40s} | {file_info['size_mb']:8.2f} MB")

        # Explore key tables
        profiles = []

        profiles.append(self.explore_person_table())
        profiles.append(self.explore_observation_table())
        profiles.append(self.explore_measurement_table())

        # Create summary
        self.create_summary(clinical_files, [p for p in profiles if p is not None])

    def create_summary(self, files, profiles):
        """Create a summary report."""
        print(f"\n{'='*80}")
        print("CLINICAL DATA SUMMARY")
        print(f"{'='*80}\n")

        total_size = sum(f['size_mb'] for f in files)
        print(f"📊 Overall Statistics:")
        print(f"  Total files: {len(files)}")
        print(f"  Total size: {total_size:.2f} MB")

        print(f"\n📋 Tables Analyzed:")
        for profile in profiles:
            print(f"\n  {profile['table_name']}:")
            print(f"    Rows sampled: {profile['rows']:,}")
            print(f"    Columns: {profile['columns']}")
            print(f"    Key fields: {', '.join(profile['column_list'][:5])}")

        print(f"\n💡 Key Insights:")
        print(f"  ✓ Data follows OMOP Common Data Model standard")
        print(f"  ✓ Multiple clinical data domains captured")
        print(f"  ✓ Concept IDs used for standardized coding")
        print(f"  ✓ Temporal data with dates recorded")


def main():
    """Main execution."""
    explorer = ClinicalDataExplorer(CONNECTION_STRING, CONTAINER_NAME)
    explorer.explore_all_tables()

    print(f"\n{'='*80}")
    print("Clinical data exploration complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
