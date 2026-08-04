# Quick Start Guide

## 1-Minute Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run complete initial data inspection
python3 run_complete_initial_data_inspection.py
```

That's it! The script will automatically:
1. Scan your Azure Blob Storage container
2. Analyze the directory structure
3. Explore metadata
4. Sample clinical data
5. Sample and visualize ECG data

## Results

After running, check these locations:

- **results/scans/** - Scan results and metadata
- **results/visualizations/** - Charts and ECG plots
- **data/samples/** - Downloaded data samples

## Interactive Analysis

```bash
# Launch Jupyter notebook
jupyter notebook notebooks/01_initial_data_inspection.ipynb
```

## Individual Scripts

Run specific parts of the workflow:

```bash
# Scan blob storage only
python3 scripts/blob_storage_scanner.py

# Analyze structure
python3 scripts/analyze_structure.py

# Explore metadata
python3 scripts/explore_metadata.py

# Explore clinical data
python3 scripts/explore_clinical_data.py

# Sample ECG data
python3 scripts/sample_wfdb_data.py

# Create summary dashboard
python3 scripts/create_summary_report.py
```

## What You'll Learn

After running the workflow, you'll know:

✓ **Dataset size and composition** (97.54 GB, 24,256 files)
✓ **File types** (JSON, CSV, .dat/.hea)
✓ **Data modalities** (Clinical, ECG, Environmental, Wearables)
✓ **File format details** (.dat/.hea are WFDB ECG files)
✓ **Data organization** (Patient-centric, multi-modal)
✓ **Sample data** for each modality
✓ **Data quality** characteristics

## Next Steps

1. Review [INITIAL_DATA_INSPECTION_GUIDE.md](INITIAL_DATA_INSPECTION_GUIDE.md) for detailed documentation
2. Open the Jupyter notebook for interactive analysis
3. Customize scripts for your specific research questions
4. Extend analysis to additional data modalities

## Common Tasks

### Download a specific file
```python
from azure.storage.blob import BlobServiceClient
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME

blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)
container = blob_service.get_container_client(CONTAINER_NAME)
blob = container.get_blob_client('path/to/file.csv')

with open('local_file.csv', 'wb') as f:
    f.write(blob.download_blob().readall())
```

### List files by pattern
```python
blobs = container.list_blobs(name_starts_with='00b62456.../dataset/clinical_data/')
for blob in blobs:
    print(blob.name)
```

### Read ECG file
```python
import wfdb

# After downloading .dat and .hea
record = wfdb.rdrecord('path/to/record_name')
wfdb.plot_wfdb(record=record, title='ECG')
```

## Questions?

- See [INITIAL_DATA_INSPECTION_GUIDE.md](INITIAL_DATA_INSPECTION_GUIDE.md) for comprehensive documentation
- Check [README.md](README.md) for project overview
- Review individual script docstrings for details
