# AI-READI Dataset - Exploratory Data Analysis Project

Comprehensive exploratory data analysis tools for the AI-READI diabetes research dataset stored in Azure Blob Storage.

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <this-repo-url> && cd ucsf_tech

# 2. Configure Azure credentials (local only)
cp .env.example .env
# Edit .env and set:
#   AZURE_STORAGE_CONNECTION_STRING=...
#   AZURE_CONTAINER_NAME=aireadi-raw

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run a container scan (optional but recommended)
python3 scripts/blob_storage_scanner.py

# 5. Launch the initial inspection notebook
jupyter notebook notebooks/01_initial_data_inspection.ipynb
```

## Dataset Overview

- **Total Size**: 97.54 GB
- **Total Files**: 24,256 blobs
- **Data Modalities**: Clinical data (OMOP CDM), 12-lead ECG, environmental sensors, wearable activity monitors, blood glucose monitors

## What's Included

### Scripts

- **blob_storage_scanner.py** - Comprehensive container scan and cataloging
- **analyze_structure.py** - Directory structure analysis and insights
- **explore_metadata.py** - Dataset metadata exploration
- **explore_clinical_data.py** - Clinical data (OMOP CDM) analysis
- **sample_wfdb_data.py** - ECG data sampling and visualization

### Notebooks

- **01_initial_data_inspection.ipynb** - Interactive initial data inspection workflow
- **02_exploratory_data_analysis.ipynb** - True exploratory data analysis (coming soon)

### Configuration

- **Environment variables** (via `.env` or your shell)
  - `AZURE_STORAGE_CONNECTION_STRING` – full Azure Blob Storage connection string
  - `AZURE_CONTAINER_NAME` – target container (defaults to `aireadi-raw`)
  - `AZURE_STUDY_ID` (optional) – study identifier used in some scripts/notebooks
- **config/azure_config.py** – small helper that reads these env vars; it contains **no secrets**.

## Key Findings

### File Types

- **JSON** (17,494 files, 39.57 GB) - Wearable data, metadata
- **CSV** (2,237 files, 57.69 GB) - Clinical data (OMOP CDM), environmental sensors
- **.dat/.hea** (2,257 pairs, 288 MB) - 12-lead ECG data (WFDB format)

### Data Modalities

1. **Clinical Data**: OMOP Common Data Model with person, observation, measurement tables
2. **ECG Data**: 2,257 12-lead ECGs, 500 Hz sampling rate, 11-second duration
3. **Environmental Sensors**: Continuous monitoring data from Lee Lab Anura sensors
4. **Wearable Activity**: 15,245 activity monitor files
5. **Blood Glucose**: 2,246 glucose monitor files

### What are .dat and .hea files?

These are **WFDB (WaveForm DataBase)** format files used for physiological signals:

- **.hea** = Header file (text) with metadata (sampling rate, lead names, duration)
- **.dat** = Binary data file with actual ECG signal values
- Always come in pairs (one .hea + one .dat per recording)
- Read using the `wfdb` Python library

## Documentation

See [INITIAL_DATA_INSPECTION_GUIDE.md](guides/INITIAL_DATA_INSPECTION_GUIDE.md) for comprehensive documentation including:

- Detailed data structure
- Analysis workflows
- Code examples
- Best practices for large dataset handling

## Project Structure

```
├── config/           # Config helpers (no secrets; uses env vars)
├── scripts/          # Python analysis scripts and data utilities
├── notebooks/        # Jupyter notebooks for inspection and EDA
├── data/samples/     # Small sample extracts and manifests
└── results/          # Scan results and visualizations
```

## Requirements

- Python 3.9+
- Azure Storage Account access
- Libraries: azure-storage-blob, pandas, wfdb, matplotlib, seaborn, jupyter

## Notes

This is a **Type 2 Diabetes research dataset** from the AI-READI project. The dataset is too large (97.54 GB) for full download - use streaming, chunking, and sampling strategies as demonstrated in the provided scripts.

## Resources

- [Initial Data Inspection Guide](guides/INITIAL_DATA_INSPECTION_GUIDE.md)
- [AI-READI Dataset Introduction](guides/AIREADI_INTRO.md) - Background on diabetes and dataset structure
- [AI-READI Project](https://aireadi.org/)
- [OMOP CDM Documentation](https://ohdsi.github.io/CommonDataModel/)
- [WFDB Documentation](https://wfdb.readthedocs.io/)
