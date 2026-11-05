# VETSA DICOM-to-BIDS Processing

This repository contains scripts and `dcm2bids` configurations for converting Vietnam Era Twin Study of Aging (VETSA) imaging data from DICOM into BIDS, followed by project-specific DWI, fMRI, run-selection, and subject-ID processing.

## Waves and sessions

| Wave | BIDS session | DICOM conversion | DWI correction |
|---|---|---|---|
| VETSA 1 | `ses-01` | `1_wave1_bidsconversion.sh`, `dcm2bids_config_v1.json` | `3_wave1_correct_dwi_data.py` |
| VETSA 2 | `ses-02` | `1_wave2_bidsconversion.sh`, `dcm2bids_config_v2.json` | `3_wave2_correct_dwi_data.py` |
| VETSA 3 | `ses-03` | `1_wave3_bidsconversion.sh`, `dcm2bids_config_v3.json` | `3_wave3_correct_dwi_data.py` |
| VETSA 4 | `ses-04` | `1_wave4_bidsconversion.sh`, `dcm2bids_config_v4.json` | `3_wave4_correct_dwi_data.py` |

Review the wave-specific configurations against the DICOM metadata for the data being converted before running a large batch.

## Requirements and setup

The Conda environment is defined in [`environment.yml`](environment.yml) and includes Python 3.10 or later, `dcm2niix`, `dcm2bids`, `nibabel`, `nipype`, and `pandas`.

```bash
conda env create -f environment.yml
conda activate vetsa2bids
```

Run the scripts from this repository with the environment active. Conversion scripts invoke `dcm2bids`; the Python processing scripts use the packages listed in the environment.

## Typical workflow

1. **Configure and run DICOM conversion.** Each `1_wave*_bidsconversion.sh` script contains local paths for its DICOM input, subject list, BIDS output, and configuration. Update these paths and the subject-list file for your environment before running it:

   ```bash
   ./1_wave1_bidsconversion.sh
   ./1_wave2_bidsconversion.sh
   ./1_wave3_bidsconversion.sh
   ./1_wave4_bidsconversion.sh
   ```

   The scripts read subjects from `sublist_v1.txt`, `sublist_v2.txt`, `sublist_v3.txt`, and `sublist_v4.txt` for waves 1 through 4, respectively. Create these newline-delimited lists in the repository directory before running the corresponding wrapper.

2. **Select or remove runs, if needed.** `2_delete_excluded_runs.py` takes a CSV and the BIDS directory. The CSV must contain `SubjectID`, `session`, `data_type`, and `use_run` columns. For example, `SubjectID` is the ID without `sub-`, `session` is `ses-01` through `ses-04`, `data_type` is a BIDS datatype such as `dwi`, and `use_run` contains the selected filename entities and suffix (for example, `acq-1_run-01_T1w`). For each subject/session, the script removes the `run-##_` entity from the selected files and deletes remaining files with run entities. It writes a dated CSV report beside the input CSV.

   ```bash
   python 2_delete_excluded_runs.py <selection.csv> <bids_directory>
   ```

3. **Correct DWI data.** The wave-specific scripts take the BIDS directory and a text file containing one VETSA ID per line:

   ```bash
   python 3_wave1_correct_dwi_data.py <bids_directory> <subject_list.txt>
   python 3_wave2_correct_dwi_data.py <bids_directory> <subject_list.txt>
   python 3_wave3_correct_dwi_data.py <bids_directory> <subject_list.txt>
   python 3_wave4_correct_dwi_data.py <bids_directory> <subject_list.txt>
   ```

   These scripts perform wave-specific operations such as splitting or renaming DWI data by phase-encoding direction, extracting EPI fieldmaps, and updating sidecar metadata and gradient files. The wave 4 script processes multi-shell DWI and uses the `vetsa_ucsd_multiband-dwi_bvals.txt` and `vetsa_ucsd_multiband-dwi_bvecs.txt` templates included beside the script.

4. **Prepare wave 2 fMRI, if applicable.** The script takes the BIDS directory and a newline-delimited subject list:

   ```bash
   python 4_wave2_prep-fmri.py <bids_directory> <subject_list.txt>
   ```

   Processing differs by acquisition site. The script updates task and fieldmap metadata and handles UCSD's alternating AP/PA volumes. It writes `successful_subjects.txt` and `unsuccessful_subjects.txt` in the BIDS directory.

5. **Recode VETSA IDs to CIDs, if required.** Provide a key CSV with `VETSAID` and `CID` columns. By default, all `sub-*` directories are processed; `-s` optionally selects subjects from a text or CSV file containing one subject ID per line (the first CSV column is used). IDs in the list may include or omit the `sub-` prefix.

   ```bash
   python 5_recode_to_cid.py \
     --bids_dir <bids_directory> \
     --key <id_mapping.csv> \
     --subjects_list <subject_list.txt>
   ```

   Omit `--subjects_list` to process every subject directory in the BIDS directory.

## Important notes

- The conversion and post-processing scripts are project-specific. Check their expected paths, subject lists, session labels, and acquisition assumptions against your dataset before use.
- Processing scripts can rename, overwrite, or delete files in the BIDS directory. Keep a backup and test on a small copy before running them on the only copy of your data.
- Review outputs and validate the resulting dataset with the [BIDS Validator](https://bids-standard.github.io/bids-validator/) before downstream analysis. These scripts support the VETSA workflow; they do not replace dataset-specific quality control.

## License

This project is distributed under the MIT License; see [`LICENSE`](LICENSE).
