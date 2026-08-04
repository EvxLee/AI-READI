#!/usr/bin/env python3
"""
Probe script: Full observation.csv sanity check
================================================
Pulls the full observation.csv from Azure Blob and does a fast profile of:
- Total rows / unique patients
- Instrument coverage (N patients per survey instrument)
- Special code prevalence (555, 777)
- Sample rows per instrument for column sanity check
- Value distribution per key instrument (CES-D-10, PAID-5, mhoccur, pxrd, dml)
- Whether pxrd1-54 item-level responses actually exist

Run from repo root:
    python scripts/probe_observation_full.py

Output: prints to stdout + saves probe_results.json for downstream use
"""

import sys, os, json
from io import StringIO

import pandas as pd
import numpy as np

# Auth
sys.path.insert(0, os.path.abspath('.'))
from config.azure_config import CONNECTION_STRING, CONTAINER_NAME, STUDY_ID
from azure.storage.blob import BlobServiceClient

# ── Connect ──────────────────────────────────────────────────────────────────
print("Connecting to Azure...")
blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)
container    = blob_service.get_container_client(CONTAINER_NAME)

def load_blob_csv(path, sep=','):
    data = container.get_blob_client(path).download_blob().readall().decode('utf-8')
    return pd.read_csv(StringIO(data), sep=sep, low_memory=False)

print("Loading observation.csv (~108 MB)...")
obs = load_blob_csv(f'{STUDY_ID}/dataset/clinical_data/observation.csv')
print(f"Done. Shape: {obs.shape}")

# ── Parse item key ────────────────────────────────────────────────────────────
obs['item_key'] = (
    obs['observation_source_value']
    .str.strip('"')
    .str.split(',', n=1).str[0]
    .str.strip()
)

SPECIAL_CODES = {555, 777, 555.0, 777.0}
obs['value_clean'] = obs['value_as_number'].replace(
    {555: np.nan, 777: np.nan, 555.0: np.nan, 777.0: np.nan}
)

# ── Instrument definitions ────────────────────────────────────────────────────
INSTRUMENTS = {
    'CES-D-10'         : [f'ces{i}' for i in range(1, 11)] + ['cestl'],
    'PAID-5'           : ['paid_scrd', 'paid_dpr', 'paid_wr', 'paid_eng', 'paid_cml', 'paidscore'],
    'Diet'             : [f'diet{i}' for i in range(1, 10)] + ['dietscore'],
    'DML self-mgmt'    : ['dmlact','dmlvex','dmlhex','dmlsugar','dmlgrain',
                          'dmlpor','dmlfrveg','dmledu','dmlfeet','dmlmd'],
    'Medical history'  : [k for k in obs['item_key'].unique() if k.startswith('mhoccur')],
    'Family history'   : ['fh_dm2pt', 'fh_dm2sb'],
    'Visual impairment': [f'via{i}' for i in range(1, 7)],
    'Substance use'    : [k for k in obs['item_key'].unique()
                          if k.startswith('su') and not any(k.endswith(s) for s in ['mpdat','mpts','startts'])],
    'OTC medications'  : ['cm_act','cm_ant','cm_asp','cm_dcg','cm_ibp','cm_slp'],
    'PhenX SDOH (pxrd)': [k for k in obs['item_key'].unique()
                           if k.startswith('pxrd') and not any(k.endswith(s) for s in ['mpdat','mpts','startts','dat'])],
    'PhenX food insec' : [k for k in obs['item_key'].unique() if k.startswith('pxfi') and not k.endswith(('mpdat','startts'))],
    'PhenX neighborhood':[k for k in obs['item_key'].unique() if k.startswith('pxne') and not k.endswith(('mpdat','startts'))],
}

n_total_patients = obs['person_id'].nunique()

# ── 1. Top-level summary ──────────────────────────────────────────────────────
print("\n" + "="*70)
print("SECTION 1: TOP-LEVEL SUMMARY")
print("="*70)
print(f"Total rows          : {len(obs):,}")
print(f"Unique patients     : {n_total_patients:,}")
print(f"Unique item_keys    : {obs['item_key'].nunique():,}")
n_special = obs['value_as_number'].isin(SPECIAL_CODES).sum()
print(f"Special codes (555/777): {n_special:,} ({n_special/len(obs)*100:.1f}% of rows)")
print(f"Null value_as_number: {obs['value_as_number'].isna().sum():,}")

# ── 2. Instrument coverage ────────────────────────────────────────────────────
print("\n" + "="*70)
print("SECTION 2: INSTRUMENT COVERAGE")
print("="*70)
print(f"{'Instrument':<25} {'Items in data':>13} {'Patients':>9} {'Coverage':>9}")
print("-"*60)

coverage_results = {}
for name, keys in INSTRUMENTS.items():
    present_keys = [k for k in keys if k in obs['item_key'].values]
    mask = obs['item_key'].isin(present_keys)
    n_patients = obs[mask]['person_id'].nunique()
    coverage_results[name] = {
        'defined_keys': len(keys),
        'keys_in_data': len(present_keys),
        'n_patients': int(n_patients),
        'coverage_pct': round(n_patients / n_total_patients * 100, 1),
        'keys_found': present_keys,
    }
    print(f"{name:<25} {len(present_keys):>5}/{len(keys):<7} {n_patients:>9,} {n_patients/n_total_patients*100:>8.1f}%")

# ── 3. Value distribution per instrument ─────────────────────────────────────
print("\n" + "="*70)
print("SECTION 3: VALUE DISTRIBUTIONS PER INSTRUMENT")
print("="*70)

value_profiles = {}
focus_instruments = ['CES-D-10', 'PAID-5', 'DML self-mgmt', 'Medical history',
                     'PhenX SDOH (pxrd)', 'Substance use', 'OTC medications']

for name in focus_instruments:
    info = coverage_results[name]
    if info['n_patients'] == 0:
        print(f"\n{name}: NO DATA IN FULL DATASET")
        value_profiles[name] = 'no_data'
        continue

    keys = info['keys_found']
    sub = obs[obs['item_key'].isin(keys)][['item_key', 'value_as_number', 'value_clean', 'value_as_string']]

    print(f"\n{name} ({info['n_patients']:,} patients, {len(keys)} item keys)")
    print(f"  Raw value_as_number range: [{sub['value_as_number'].min()}, {sub['value_as_number'].max()}]")
    print(f"  value_clean (555/777→NaN) null rate: {sub['value_clean'].isna().mean()*100:.1f}%")
    print(f"  Top value_clean counts:")
    vc = sub['value_clean'].value_counts().head(10)
    for val, cnt in vc.items():
        print(f"    {val:>8.1f} : {cnt:>7,} rows")

    # Per-item stats
    print(f"  Per-item means (value_clean):")
    item_means = sub.groupby('item_key')['value_clean'].agg(['mean','std','count']).round(3)
    print(item_means.to_string())

    # Sample 3 raw rows
    print(f"  Sample rows (3):")
    sample = sub.sample(min(3, len(sub)), random_state=42)[['item_key','value_as_number','value_as_string']]
    print(sample.to_string(index=False))

    value_profiles[name] = {
        'range': [float(sub['value_as_number'].min()), float(sub['value_as_number'].max())],
        'null_rate_after_clean': float(sub['value_clean'].isna().mean()),
        'value_counts_top10': {str(k): int(v) for k, v in vc.items()},
    }

# ── 4. pxrd item-level check ──────────────────────────────────────────────────
print("\n" + "="*70)
print("SECTION 4: pxrd ITEM-LEVEL DETAIL")
print("="*70)
pxrd_keys = [k for k in obs['item_key'].unique()
             if k.startswith('pxrd') and not any(k.endswith(s) for s in ['mpdat','mpts','startts','dat'])]
print(f"pxrd item keys found: {len(pxrd_keys)}")
print(f"Keys: {sorted(pxrd_keys)}")

if pxrd_keys:
    pxrd = obs[obs['item_key'].isin(pxrd_keys)]
    print(f"Rows: {len(pxrd):,} | Patients: {pxrd['person_id'].nunique():,}")
    print(f"value_as_number range: [{pxrd['value_as_number'].min()}, {pxrd['value_as_number'].max()}]")
    print(f"Special code rate: {pxrd['value_as_number'].isin(SPECIAL_CODES).mean()*100:.1f}%")
    print(f"Null rate: {pxrd['value_as_number'].isna().mean()*100:.1f}%")
    print(f"\nTop value_as_number counts:")
    print(pxrd['value_as_number'].value_counts().head(15).to_string())
    print(f"\nPer-item patient counts:")
    pxrd_item_patients = pxrd.groupby('item_key')['person_id'].nunique().sort_index()
    print(pxrd_item_patients.to_string())
else:
    print("NO pxrd item-level response data found in full observation.csv")
    print("(Only metadata/timestamp rows may exist for this instrument)")

# ── 5. Unique value_as_string types ──────────────────────────────────────────
print("\n" + "="*70)
print("SECTION 5: value_as_string TYPES (survey rows only)")
print("="*70)
survey_keys = [k for keys in INSTRUMENTS.values() for k in keys]
survey_obs = obs[obs['item_key'].isin(survey_keys)]
print(f"Top 20 value_as_string values across all survey rows:")
print(survey_obs['value_as_string'].value_counts().head(20).to_string())

# ── 6. Response type classification per instrument ────────────────────────────
print("\n" + "="*70)
print("SECTION 6: RESPONSE TYPE CLASSIFICATION")
print("="*70)
print("Classifying each instrument by its dominant value range...")

for name, info in coverage_results.items():
    if info['n_patients'] == 0:
        print(f"  {name:<25}: NO DATA")
        continue
    keys = info['keys_found']
    sub = obs[obs['item_key'].isin(keys)]['value_clean'].dropna()
    if len(sub) == 0:
        print(f"  {name:<25}: all values are special codes/null")
        continue
    unique_vals = sorted(sub.unique())
    if set(unique_vals).issubset({0, 1, 0.0, 1.0}):
        vtype = "BINARY (0/1)"
    elif max(unique_vals) <= 4 and min(unique_vals) >= 0:
        vtype = f"ORDINAL (0–{int(max(unique_vals))})"
    elif max(unique_vals) <= 10 and min(unique_vals) >= 0:
        vtype = f"ORDINAL (0–{int(max(unique_vals))})"
    elif max(unique_vals) > 10:
        vtype = f"CONTINUOUS/SCORED (range {sub.min():.1f}–{sub.max():.1f})"
    else:
        vtype = f"MIXED (range {sub.min():.1f}–{sub.max():.1f})"
    n_unique = len(unique_vals)
    print(f"  {name:<25}: {vtype} | {n_unique} unique vals | N={info['n_patients']:,}")

# ── Save results ──────────────────────────────────────────────────────────────
results = {
    'total_rows': len(obs),
    'total_patients': int(n_total_patients),
    'unique_item_keys': int(obs['item_key'].nunique()),
    'special_code_pct': float(n_special / len(obs) * 100),
    'instrument_coverage': {
        name: {k: v for k, v in info.items() if k != 'keys_found'}
        for name, info in coverage_results.items()
    },
}

out_path = 'data/samples/probe_results.json'
os.makedirs('data/samples', exist_ok=True)
with open(out_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✓ Probe complete. Results saved to {out_path}")
print("\nKEY QUESTIONS THIS ANSWERS:")
print("  1. Does the full dataset actually have all 2,280 patients? (Section 1)")
print("  2. Which instruments have real coverage? (Section 2)")
print("  3. Are pxrd1-54 items populated or just metadata? (Section 4)")
print("  4. What are the actual value ranges — do they match our coding assumptions? (Section 3/6)")
print("  5. Should we use value_as_number or value_as_string for anything? (Section 5)")
