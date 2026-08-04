# AI-READI Dataset - Initial Data Inspection Guide

## Overview

This project provides a comprehensive initial data inspection workflow for the AI-READI (Artificial Intelligence Ready and Equitable Atlas for Diabetes Insights) dataset stored in Azure Blob Storage.

### Dataset Summary
- **Storage**: Azure Blob Storage (staireadi01/aireadi-raw)
- **Total Size**: 97.54 GB
- **Total Files**: 24,256 blobs
- **Study ID**: 00b62456-0b93-4975-a992-42ba6a50ed5c

### Data Modalities

1. **Clinical Data (OMOP CDM)** - 57.69 GB
   - Format: CSV files
   - Tables: observation, measurement, person, condition_occurrence, etc.
   - Standard: OMOP Common Data Model v5+

2. **ECG Data** - 288 MB
   - Format: WFDB (.dat + .hea files)
   - Count: 2,257 recordings
   - Type: 12-lead ECG
   - Device: Philips TC30
   - Duration: ~11 seconds each
   - Sampling Rate: 500 Hz

3. **Wearable Activity Monitor Data** - 15,245 files
   - Format: JSON
   - Most files in the dataset

4. **Environmental Sensor Data** - 2,232 files
   - Format: CSV (_ENV.csv files)
   - Large files: 50-65 MB each
   - Source: Lee Lab Anura sensors

5. **Wearable Blood Glucose Data** - 2,246 files
   - Format: JSON

## Project Structure

```
ucsf_tech/
├── config/
│   └── azure_config.py          # Azure credentials and connection settings
├── scripts/
│   ├── blob_storage_scanner.py   # Scan and catalog blob storage
│   ├── analyze_structure.py      # Analyze directory structure
│   ├── explore_metadata.py       # Explore dataset metadata
│   ├── explore_clinical_data.py  # Analyze clinical data (OMOP)
│   └── sample_wfdb_data.py       # Sample and visualize ECG data
├── notebooks/
│   └── 01_comprehensive_eda.ipynb # Interactive EDA notebook
├── data/
│   └── samples/                  # Downloaded data samples
├── results/
│   ├── scans/                    # Scan results and metadata
│   └── visualizations/           # Generated plots and charts
└── requirements.txt              # Python dependencies
```

## Getting Started

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Run Complete EDA Workflow

```bash
# Step 1: Scan blob storage
python3 scripts/blob_storage_scanner.py

# Step 2: Analyze structure
python3 scripts/analyze_structure.py

# Step 3: Explore metadata
python3 scripts/explore_metadata.py

# Step 4: Explore clinical data
python3 scripts/explore_clinical_data.py

# Step 5: Sample ECG data
python3 scripts/sample_wfdb_data.py
```

### 3. Interactive Analysis

```bash
# Launch Jupyter notebook
jupyter notebook notebooks/01_comprehensive_eda.ipynb
```

## Key Findings

### File Format Details

#### .dat and .hea files (WFDB Format)
- **What they are**: PhysioNet WFDB (WaveForm DataBase) format for physiological signals
- **.hea file**: Header file containing metadata (text format)
  - Signal names (lead names: I, II, III, aVR, aVL, aVF, V1-V6)
  - Sampling frequency (500 Hz)
  - Duration
  - Units (mV)
  - Gain and baseline values
- **.dat file**: Binary data file containing actual signal values
- **Always paired**: Each recording has both .hea and .dat
- **Library**: Use `wfdb` Python library to read

#### JSON Files (17,494 files, 39.57 GB)
- Most numerous file type
- Contains:
  - Dataset metadata
  - Wearable activity monitor data
  - Blood glucose monitor data
  - Data quality reports
  - Study descriptions

#### CSV Files (2,237 files, 57.69 GB)
- Largest storage consumer (59% of total)
- OMOP CDM tables (clinical data)
- Environmental sensor data
- Some manifest files

### Data Organization Pattern

```
00b62456-0b93-4975-a992-42ba6a50ed5c/
└── dataset/
    ├── clinical_data/          # OMOP CDM tables
    │   ├── person.csv
    │   ├── observation.csv (largest: 108 MB)
    │   ├── measurement.csv
    │   └── ...
    ├── cardiac_ecg/
    │   └── ecg_12lead/
    │       └── philips_tc30/
    │           ├── 1001/       # Patient ID folders
    │           │   ├── 1001_ecg_HASH.dat
    │           │   └── 1001_ecg_HASH.hea
    │           └── ...
    ├── environment/
    │   └── environmental_sensor/
    │       └── leelab_anura/
    │           └── {patient_id}/{patient_id}_ENV.csv
    ├── wearable_activity_monitor/
    │   └── {patient_id}/...
    └── wearable_blood_glucose/
        └── {patient_id}/...
```

## EDA Workflow Recommendations

### Phase 1: Understanding the Data Model ✓
- [x] Read dataset_description.json
- [x] Review manifest files
- [x] Understand OMOP CDM structure

### Phase 2: Clinical Data Exploration ✓
- [x] Profile clinical CSV files
- [x] Sample large files (observation.csv)
- [x] Analyze demographics
- [ ] Temporal analysis of measurements
- [ ] Data completeness by patient
- [ ] Comorbidity patterns

### Phase 3: ECG Waveform Analysis ✓
- [x] Sample .dat/.hea files
- [x] Extract signal characteristics
- [x] Visualize sample ECG traces
- [ ] QRS detection and heart rate analysis
- [ ] Signal quality assessment
- [ ] Arrhythmia detection

### Phase 4: Environmental Data Analysis
- [ ] Sample environmental sensor CSV files
- [ ] Understand sensor types
- [ ] Analyze temporal coverage
- [ ] Link to patient IDs

### Phase 5: Wearable Data Analysis
- [ ] Sample activity monitor JSON files
- [ ] Sample blood glucose JSON files
- [ ] Understand data structure
- [ ] Temporal patterns

### Phase 6: Cross-Modal Integration
- [ ] Map patient IDs across modalities
- [ ] Analyze data completeness per patient
- [ ] Temporal alignment
- [ ] Comprehensive patient profiles

## Key Considerations

### Data Size Management
- **Don't download everything**: 97.54 GB is too large
- **Use streaming**: Read CSV files in chunks with pandas
- **Sample strategically**: Download representative samples
- **Leverage blob storage**: Access files on-demand

### OMOP CDM Notes
- Standardized data model for observational healthcare data
- Uses concept IDs for coding (links to OMOP vocabulary)
- Person table contains demographics
- Observation/Measurement tables contain clinical data
- Temporal data with dates

### ECG Data Notes
- Standard 12-lead ECG configuration
- Clinical-grade sampling rate (500 Hz)
- Short duration (~11 seconds) - likely resting ECGs
- WFDB format is widely supported
- Can be processed with standard ECG analysis tools

## Useful Code Snippets

### Download a Specific Blob
```python
from azure.storage.blob import BlobServiceClient
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME

blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)
blob_client = container_client.get_blob_client('path/to/blob')

with open('local_file.csv', 'wb') as f:
    f.write(blob_client.download_blob().readall())
```

### Read Large CSV in Chunks
```python
import pandas as pd
import io

blob_client = container_client.get_blob_client('path/to/large.csv')
csv_data = blob_client.download_blob().readall()

# Read first 10,000 rows
df = pd.read_csv(io.BytesIO(csv_data), nrows=10000)
```

### Read WFDB ECG File
```python
import wfdb
import matplotlib.pyplot as plt

# After downloading .dat and .hea files
record = wfdb.rdrecord('path/to/record_base_name')

# Plot
wfdb.plot_wfdb(record=record, title='ECG Recording')
plt.show()
```

### List Blobs by Prefix
```python
blobs = container_client.list_blobs(name_starts_with='00b62456.../dataset/clinical_data/')

for blob in blobs:
    print(f"{blob.name} - {blob.size / (1024**2):.2f} MB")
```

## Next Steps

1. **Run the scripts** to generate fresh scan results and samples
2. **Open the Jupyter notebook** for interactive analysis
3. **Customize the workflows** for your specific research questions
4. **Extend the analysis** to additional data modalities
5. **Document your findings** as you go

## Resources

- [OMOP CDM Documentation](https://ohdsi.github.io/CommonDataModel/)
- [WFDB Python Library](https://wfdb.readthedocs.io/)
- [AI-READI Project](https://aireadi.org/)
- [PhysioNet](https://physionet.org/)

## Notes

- This is a **diabetes research dataset** (Type 2 Diabetes focus)
- Data collection includes multiple modalities for comprehensive patient assessment
- Dataset follows FAIR principles (Findable, Accessible, Interoperable, Reusable)
- Patient IDs are consistent across modalities (e.g., 1001, 1002, etc.)
