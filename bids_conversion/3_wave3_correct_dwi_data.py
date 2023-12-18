#!/usr/bin/env python3

"""
This script corrects the dwi data for the VETSA3 dataset. The script does the following:
- Renames the dwi files
- Renames the dwi json files
- Renames the bvals and bvecs files
- Splits off the first two volumes as epi files
- Flips the AP epi file in the phase encoding direction
- Creates json files for the epi files
- Overwrites the single and multi-shell bvals and bvecs files with correct values (dicomes report incorrect values)
- Removes values from the bvecs/bvals files corresponding to epi scans

Usage: python 3_wave3_correct_dwi_data.py <bids_dir> <subject_list_file>

Arguments:
    bids_dir: The path to the BIDS directory
    subject_list_file: The path to a text file containing the list of subjects to process

Note: 
The bvals and bvecs files are overwritten based on custom tensor file. Requires that that template 
bvecs and bvals files are located in the same directory as the script. The bvecs and bvals files are not 
overwritten for the single-shell data because the values reported in the dicom header are correct.
"""

import os
import sys
import shutil
import numpy as np
import nibabel as nib
from glob import glob
import json

def check_dwi_folder(vetsaid, bids_dir):
    """Check if the dwi folder exists"""
    dwi_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi')
    if not os.path.isdir(dwi_dir):
        print('No dwi folder found')
        return False
    return True

def split_epis(dwi_file, epi_pa_file, epi_ap_file):
    """
    Save the first two volumes as epi files in the fmap folder. The first volume is 
    the AP epi file and the second volume is the PA epi file. Remove the first (1)
    volume from the dwi file because it is in the reverse phase encoding direction.
    """
    img = nib.load(dwi_file)
    data = img.get_fdata()
    nib.save(nib.Nifti1Image(data[:, :, :, 0], img.affine), epi_ap_file)
    nib.save(nib.Nifti1Image(data[:, :, :, 1], img.affine), epi_pa_file)
    nib.save(nib.Nifti1Image(data[:, :, :, 1:], img.affine), dwi_file)
    return dwi_file, epi_pa_file, epi_ap_file

def flip_ap_epi(epi_ap_file):
    """Flip the data of the AP epi in the phase encoding direction"""
    epi_ap_img = nib.load(epi_ap_file)
    epi_ap_data = epi_ap_img.get_fdata()
    epi_ap_data_flipped = np.flip(epi_ap_data, axis=1)
    nib.save(nib.Nifti1Image(epi_ap_data_flipped, epi_ap_img.affine), epi_ap_file)
    return epi_ap_file


def remove_first_n_values(file_path, n):
    """Remove the first n values from each row of a file. Can be used to remove the first
    n values from each row of a bvecs file or the first n values from a bvals file."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    new_values_list = []
    for row in lines:
        row_values = row.split()
        row_values_new = ' '.join(row_values[n:])
        new_values_list.append(row_values_new)
    new_values_str = '\n'.join(new_values_list)
    with open(file_path, 'w') as f:
        f.write(new_values_str)
        

def check_dwi_nvols(dwi_file, nvols, alt_nvols=None):
    """Check if the dwi file has the correct number of volumes. nvols is the number of volumes.
    alt_nvols is an alternative number of volumes that is also acceptable. If the dwi file has
    the correct number of volumes, return True. If not, return False."""
    img = nib.load(dwi_file)
    data = img.get_fdata()
    if data.shape[3] == nvols:
        return True
    elif alt_nvols is not None:
        if data.shape[3] == alt_nvols:
            return True
    return False



def check_multi_shell_data(vetsaid, bids_dir):
    """Check if the multi-shell data exists"""
    multi_dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dwi.nii.gz')
    if not os.path.isfile(multi_dwi_file):
        print('No multi-shell data found for subject {vetsaid}')
        return False
    return True

def create_multi_shell_epi_jsons(vetsaid, bids_dir):
    """Create json sidecars for the multi-shell diffusion EPI files"""
    # Create json files for the epi files
    multi_epi_ap_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'fmap', f'sub-{vetsaid}_ses-03_acq-multi_dir-AP_epi.json')
    multi_epi_pa_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'fmap', f'sub-{vetsaid}_ses-03_acq-multi_dir-PA_epi.json')
    # Get the TotalReadoutTime value from the associated dwi.json file
    dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dir-PA_dwi.nii.gz')
    dwi_json_file = os.path.join(os.path.dirname(dwi_file), f'sub-{vetsaid}_ses-03_acq-multi_dir-PA_dwi.json')
    with open(dwi_json_file, 'r') as f:
        dwi_json = json.load(f)
    total_readout_time = dwi_json["TotalReadoutTime"]
    # Fill in the subject ID in the IntendedFor field
    intended_for = f"bids::sub-{vetsaid}/ses-03/dwi/sub-{vetsaid}_ses-03_acq-multi_dir-PA_dwi.nii.gz"
    multi_epi_ap_json_dict = {
        "PhaseEncodingDirection": "j-",
        "TotalReadoutTime": total_readout_time,
        "IntendedFor": intended_for
    }
    multi_epi_pa_json_dict = {
        "PhaseEncodingDirection": "j",
        "TotalReadoutTime": total_readout_time,
        "IntendedFor": intended_for
    }
    with open(multi_epi_ap_json, 'w') as f:
        json.dump(multi_epi_ap_json_dict, f, indent=4)
    with open(multi_epi_pa_json, 'w') as f:
        json.dump(multi_epi_pa_json_dict, f, indent=4)
        
    return multi_epi_ap_json, multi_epi_pa_json


def process_multi_shell_data(vetsaid, bids_dir):
    """Process the multi-shell data. This includes:
    - Renaming the dwi file
    - Renaming the dwi json file
    - Renaming the bvals and bvecs files
    - Save first two volumes as epi files and remove reverse encoded volume from dwi file
    - Flipping the AP epi file in the phase encoding direction
    - Creating json files for the epi files
    - Overwriting the bvals and bvecs files with correct values
    - Removing the first value from the bvecs/bvals files corresponding to reverse encoded scan
    (Note: the bvals and bvecs files are overwritten because the values reported in the
    dicom header are incorrect for the multi-shell data. Requires template bvals and bvecs files in the
    same directory as the script.)
    """
    # Rename dwi file
    multi_dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dwi.nii.gz')
    multi_dwi_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dir-PA_dwi.nii.gz')
    shutil.move(multi_dwi_file, multi_dwi_file_new)
    # Check if the dwi file has the correct number of volumes
    if not check_dwi_nvols(multi_dwi_file_new, 56, 54):
        print(f'Error: Incorrect number of volumes in dwi file for subject {vetsaid}')
        return
    # Rename dwi json file
    multi_dwi_json_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dwi.json')
    multi_dwi_json_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dir-PA_dwi.json')
    shutil.move(multi_dwi_json_file, multi_dwi_json_file_new)
    # Rename bvals and bvecs files
    bvals_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dwi.bval')
    bvecs_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dwi.bvec')
    bvals_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dir-PA_dwi.bval')
    bvecs_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-multi_dir-PA_dwi.bvec')
    shutil.move(bvals_file, bvals_file_new)
    shutil.move(bvecs_file, bvecs_file_new)
    # Split off the first two volumes as epi files
    fmap_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'fmap')
    os.makedirs(fmap_dir, exist_ok=True)
    multi_epi_ap_file = os.path.join(fmap_dir, f'sub-{vetsaid}_ses-03_acq-multi_dir-AP_epi.nii.gz')
    multi_epi_pa_file = os.path.join(fmap_dir, f'sub-{vetsaid}_ses-03_acq-multi_dir-PA_epi.nii.gz')
    multi_dwi_file_new, multi_epi_pa_file, multi_epi_ap_file = split_epis(multi_dwi_file_new, multi_epi_pa_file, multi_epi_ap_file)
    # Flip the AP epi file in the phase encoding direction
    multi_epi_ap_file = flip_ap_epi(multi_epi_ap_file)
    # Create json files for the epi files
    multi_epi_ap_json, multi_epi_pa_json = create_multi_shell_epi_jsons(vetsaid, bids_dir)
    # Overwrite the bvals and bvecs files
    current_dir = os.path.dirname(os.path.abspath(__file__))
    bvals_file_src = os.path.join(current_dir, 'vetsa_ucsd_multiband-dwi_bvals.txt')
    bvecs_file_src = os.path.join(current_dir, 'vetsa_ucsd_multiband-dwi_bvecs.txt')
    shutil.copy(bvals_file_src, bvals_file_new)
    shutil.copy(bvecs_file_src, bvecs_file_new)
    # Remove the first (1) value from the bvals file     
    remove_first_n_values(bvals_file_new, 1)
    # Remove the first (1) value from the bvecs file
    remove_first_n_values(bvecs_file_new, 1)
    # Create json files for the epi files
    multi_epi_ap_json, multi_epi_pa_json = create_multi_shell_epi_jsons(vetsaid, bids_dir)


def check_single_shell_data(vetsaid, bids_dir):
    """Check if the single-shell data exists"""
    single_dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dwi.nii.gz')
    if not os.path.isfile(single_dwi_file):
        print('No single-shell data found for subject {vetsaid}')
        return False
    return True


def create_single_shell_epi_jsons(vetsaid, bids_dir):
    """Create json sidecars for the single-shell diffusion EPI files"""
    # Create json files for the epi files
    single_epi_ap_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'fmap', f'sub-{vetsaid}_ses-03_acq-single_dir-AP_epi.json')
    single_epi_pa_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'fmap', f'sub-{vetsaid}_ses-03_acq-single_dir-PA_epi.json')
    # Get the TotalReadoutTime value from the associated dwi.json file
    dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dir-PA_dwi.nii.gz')
    dwi_json_file = os.path.join(os.path.dirname(dwi_file), f'sub-{vetsaid}_ses-03_acq-single_dir-PA_dwi.json')
    with open(dwi_json_file, 'r') as f:
        dwi_json = json.load(f)
    total_readout_time = dwi_json["TotalReadoutTime"]
    # Fill in the subject ID in the IntendedFor field
    intended_for = f"bids::sub-{vetsaid}/ses-03/dwi/sub-{vetsaid}_ses-03_acq-single_dir-PA_dwi.nii.gz"
    single_epi_ap_json_dict = {
        "PhaseEncodingDirection": "j-",
        "TotalReadoutTime": total_readout_time,
        "IntendedFor": intended_for
    }
    single_epi_pa_json_dict = {
        "PhaseEncodingDirection": "j",
        "TotalReadoutTime": total_readout_time,
        "IntendedFor": intended_for
    }
    with open(single_epi_ap_json, 'w') as f:
        json.dump(single_epi_ap_json_dict, f, indent=4)
    with open(single_epi_pa_json, 'w') as f:
        json.dump(single_epi_pa_json_dict, f, indent=4)
    return single_epi_ap_json, single_epi_pa_json


def process_single_shell_data(vetsaid, bids_dir):
    """Process the single-shell data. This includes:
    - Renaming the dwi file
    - Renaming the dwi json file
    - Renaming the bvals and bvecs files
    - Save first two volumes as epi files and remove reverse encoded volume from dwi file
    - Flipping the AP epi file in the phase encoding direction
    - Creating json files for the epi files
    - Removing the first value from the bvecs/bvals files corresponding to reverse encoded scan
    (Note: the bvals and bvecs files are not overwritten because the values reported in the
    dicom header are correct for the single-shell data)
    """
    # Rename dwi file
    single_dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dwi.nii.gz')
    single_dwi_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dir-PA_dwi.nii.gz')
    shutil.move(single_dwi_file, single_dwi_file_new)
    # Check if the dwi file has the correct number of volumes
    if not check_dwi_nvols(single_dwi_file_new, 53):
        print(f'Error: Incorrect number of volumes in dwi file for subject {vetsaid}')
        return
    # Rename dwi json file
    single_dwi_json_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dwi.json')
    single_dwi_json_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dir-PA_dwi.json')
    shutil.move(single_dwi_json_file, single_dwi_json_file_new)
    # Rename bvals and bvecs files
    bvals_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dwi.bval')
    bvecs_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dwi.bvec')
    bvals_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dir-PA_dwi.bval')
    bvecs_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'dwi', f'sub-{vetsaid}_ses-03_acq-single_dir-PA_dwi.bvec')
    shutil.move(bvals_file, bvals_file_new)
    shutil.move(bvecs_file, bvecs_file_new)
    # Split off the first two volumes as epi files
    fmap_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-03', 'fmap')
    os.makedirs(fmap_dir, exist_ok=True)
    single_epi_ap_file = os.path.join(fmap_dir, f'sub-{vetsaid}_ses-03_acq-single_dir-AP_epi.nii.gz')
    single_epi_pa_file = os.path.join(fmap_dir, f'sub-{vetsaid}_ses-03_acq-single_dir-PA_epi.nii.gz')
    single_dwi_file_new, single_epi_pa_file, single_epi_ap_file = split_epis(single_dwi_file_new, single_epi_pa_file, single_epi_ap_file)
    # Flip the phase encoding direction of the AP epi file
    single_epi_ap_file = flip_ap_epi(single_epi_ap_file)
    # Remove the first (1) value from the bvals file
    remove_first_n_values(bvals_file_new, 1)
    # Remove the first (1) value from the bvecs file
    remove_first_n_values(bvecs_file_new, 1)
    # Create json files for the epi files
    single_epi_ap_json, single_epi_pa_json = create_single_shell_epi_jsons(vetsaid, bids_dir)


def main(bids_dir, subject_list_file):
    # Read the subject list file
    with open(subject_list_file, 'r') as f:
        subject_list = f.read().splitlines()

    # Process each subject in the list
    for vetsaid in subject_list:
        print(f'Processing subject {vetsaid}')

        # Check if the dwi folder exists
        if not check_dwi_folder(vetsaid, bids_dir):
            continue

        # Check if the multi-shell data exists. If so, process it
        if check_multi_shell_data(vetsaid, bids_dir):
            process_multi_shell_data(vetsaid, bids_dir)

        # Check if the single-shell data exists. If so, process it
        if check_single_shell_data(vetsaid, bids_dir):
            process_single_shell_data(vetsaid, bids_dir)


if __name__ == '__main__':
    
    # Check if the correct number of arguments was provided
    if len(sys.argv) != 3:
        print('Usage: python 3_wave3_correct_dwi_data.py <bids_dir> <subject_list_file>')
        sys.exit(1)

    # Get the path to the BIDS data and the subject list file from the command line arguments
    bids_dir = sys.argv[1]
    subject_list_file = sys.argv[2]

    # Run the main function
    main(bids_dir, subject_list_file)

