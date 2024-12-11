# VETSA BIDS Processing Pipeline

Scripts for converting and preprocessing neuroimaging data from the Vietnam Era Twin Study of Aging (VETSA) into BIDS format across multiple data collection waves.

## Overview

This repository contains scripts to:

1. Convert DICOM files to BIDS format using [dcm2bids](https://github.com/UNFmontreal/Dcm2Bids)
2. Correct DWI data organization and metadata
3. Process fMRI data and metadata  
4. Recode subject IDs

## Requirements

```yml
- python >= 3.10
- dcm2niix
- dcm2bids >= 3.0.1  
- nibabel >= 5.0.1
- nipype >= 1.8.6
- pandas >= 2.1.*
```

## Usage

### 1. DICOM to BIDS Conversion

Convert DICOM files to BIDS format for each wave:

```bash
./1_wave1_bidsconversion.sh  # VETSA1 data
./1_wave2_bidsconversion.sh  # VETSA2 data
./1_wave3_bidsconversion.sh  # VETSA3 data
./1_wave4_bidsconversion.sh  # VETSA4 data
```

Uses wave-specific configuration files: 

```
dcm2bids_config_v1.json 
dcm2bids_config_v2.json
dcm2bids_config_v3.json
dcm2bids_config_v4.json
```

### 2. Delete Excluded Runs

Remove unwanted imaging runs based on a CSV file:

```bash
python 2_delete_excluded_runs.py <csv_file> <bids_directory>
```

### 3. DWI Data Correction 

Process DWI data by wave:

```bash
python 3_wave1_correct_dwi_data.py <bids_dir> <subject_list>
python 3_wave2_correct_dwi_data.py <bids_dir> <subject_list>
python 3_wave3_correct_dwi_data.py <bids_dir> <subject_list>
```

Key DWI processing steps:
- Split files by phase encoding direction (AP/PA)
- Extract b0 volumes for fieldmaps
- Correct bval/bvec files
- Update JSON metadata

### 4. fMRI Processing

Process fMRI data (primarily Wave 2):

```bash
python 4_wave2_prep-fmri.py <bids_dir> <subject_list>
```

Site-specific fMRI processing:
- BU: Update JSON metadata only
- UCSD: Split by phase encoding direction and handle alternating AP/PA volumes

### 5. ID Recoding

Recode subject IDs:

```bash
python 5_recode_to_cid.py -b <bids_dir> -k <key_file> [-s <subjects>]
```

## Implementation Details

- Handles data from multiple sites (BU and UCSD)
- Site-specific processing pipelines 
- Supports both single-shell and multi-shell DWI
- Processes alternating phase encode fMRI
- Maintains BIDS compliance throughout



## Notes

- BU and UCSD data require different processing approaches
- DWI includes both single-shell and multi-shell acquisitions
- fMRI uses different phase encoding schemes across sites