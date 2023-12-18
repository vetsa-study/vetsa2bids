#!/usr/bin/env python3

"""
This script corrects the dwi data for the VETSA2 UCSD dataset. The script does the following:
- Renames the dwi files
- Renames the dwi json files
- Renames the bvals and bvecs files
- Splits off the first two volumes as epi files
- Flips the AP epi file in the phase encoding direction
- Creates json files for the epi files
- Overwrites the single-shell bvals and bvecs files with correct values (dicoms report incorrect values)
- Removes values from the bvecs/bvals files corresponding to epi scans
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
    dwi_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi')
    if not os.path.isdir(dwi_dir):
        print('No dwi folder found')
        return False
    return True


def check_single_shell_data(vetsaid, bids_dir):
    """Check if the single-shell data exists"""
    single_dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-AP_dwi.nii.gz')
    if not os.path.isfile(single_dwi_file):
        print('No single-shell data found')
        return False
    return True


def get_site(vetsaid, bids_dir):
    """ 
    Checks dwi json file to determine site of data collection based on manufacturer model.
    BU data was collected on a Siemens TrioTim.
    UCSD data was colected on a GE DISCOVERY MR750. 
    """
    dwi_json_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-AP_dwi.json')
    with open(dwi_json_file, 'r') as f:
        dwi_json = json.load(f)
    dwi_model = dwi_json["ManufacturersModelName"]
    if dwi_model == "TrioTim":
        dwi_site = "BU"
    elif dwi_model == "DISCOVERY MR750":
        dwi_site = "UCSD"
    else:
        print(f'Error in processing sub-{vetsaid}. Unknown manufacturer model: {dwi_model}')
        sys.exit(1)
    return dwi_site


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

def create_single_shell_epi_jsons(vetsaid, bids_dir):
    """Create json sidecars for the single-shell diffusion EPI files"""
    # Create json files for the epi files
    single_epi_ap_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'fmap', f'sub-{vetsaid}_ses-02_acq-single_dir-AP_epi.json')
    single_epi_pa_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'fmap', f'sub-{vetsaid}_ses-02_acq-single_dir-PA_epi.json')
    # Get the TotalReadoutTime value from the associated dwi.json file
    dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-PA_dwi.nii.gz')
    dwi_json_file = os.path.join(os.path.dirname(dwi_file), f'sub-{vetsaid}_ses-02_acq-single_dir-PA_dwi.json')
    with open(dwi_json_file, 'r') as f:
        dwi_json = json.load(f)
    total_readout_time = dwi_json["TotalReadoutTime"]
    # Fill in the subject ID in the IntendedFor field
    intended_for = f"bids::sub-{vetsaid}/ses-02/dwi/sub-{vetsaid}_ses-02_acq-single_dir-PA_dwi.nii.gz"
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


def split_bu_dwi(single_dwi_file_new):
    """
    Split the dwi file into two files (one for each phase encoding direction). BU data was 
    collected with 62 volumes. The first 31 volumes are in the AP direction and final 
    31 volumes are in the PA direction.
    """
    img = nib.load(single_dwi_file_new)
    data = img.get_fdata()
    nib.save(nib.Nifti1Image(data[:, :, :, :31], img.affine), single_dwi_file_new)
    nib.save(nib.Nifti1Image(data[:, :, :, 31:], img.affine), single_dwi_file_new.replace('dir-AP', 'dir-PA'))
    return single_dwi_file_new, single_dwi_file_new.replace('dir-AP', 'dir-PA')

def split_bu_bval_bvec(dwi_file):
    """
    Splits the bvals and bvecs files into two files (one for each phase encoding direction). 
    The first 31 values from each row should be saved out as the AP file and the final 31
    values from each row should be saved out as the PA file. Takes as input the name of 
    the dwi file in the AP direction to determine the names of the bvals and bvecs files.
    """
    bvals_file = dwi_file.replace('dwi.nii.gz', 'dwi.bval')
    bvecs_file = dwi_file.replace('dwi.nii.gz', 'dwi.bvec')
    bvals_file_AP = bvals_file.replace('dir-AP', 'dir-AP')
    bvecs_file_AP = bvecs_file.replace('dir-AP', 'dir-AP')
    bvals_file_PA = bvals_file.replace('dir-AP', 'dir-PA')
    bvecs_file_PA = bvecs_file.replace('dir-AP', 'dir-PA')
    with open(bvals_file, 'r') as f:
        bvals = f.readlines()
    with open(bvecs_file, 'r') as f:
        bvecs = f.readlines()
    bvals_AP = [row.split()[:31] for row in bvals]
    bvals_PA = [row.split()[31:] for row in bvals]
    bvecs_AP = [row.split()[:31] for row in bvecs]
    bvecs_PA = [row.split()[31:] for row in bvecs]
    bvals_AP_str = '\n'.join([' '.join(row) for row in bvals_AP])
    bvals_PA_str = '\n'.join([' '.join(row) for row in bvals_PA])
    bvecs_AP_str = '\n'.join([' '.join(row) for row in bvecs_AP])
    bvecs_PA_str = '\n'.join([' '.join(row) for row in bvecs_PA])
    with open(bvals_file_AP, 'w') as f:
        f.write(bvals_AP_str)
    with open(bvals_file_PA, 'w') as f:
        f.write(bvals_PA_str)
    with open(bvecs_file_AP, 'w') as f:
        f.write(bvecs_AP_str)
    with open(bvecs_file_PA, 'w') as f:
        f.write(bvecs_PA_str)
    return bvals_file_AP, bvals_file_PA, bvecs_file_AP, bvecs_file_PA



def process_single_shell_data_BU(vetsaid, bids_dir):
    """
    Process single-shell data from BU. This includes:
    - Split dwi file into two files (one for each phase encoding direction)
    - Split the bvals and bvecs files into two files (one for each phase encoding direction)
    - Create json file for the new PA dwi file
    - Edit the json file for the PA epi file to include the correct IntendedFor field
    """
    single_dwi_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-AP_dwi.nii.gz')
    # Check if the dwi file has the correct number of volumes
    if not check_dwi_nvols(single_dwi_file_new, 62):
        print(f'Error: Incorrect number of volumes in dwi file for subject {vetsaid}')
        return
    # Split the dwi file into two files (one for each phase encoding direction)
    single_dwi_file_AP, single_dwi_file_PA = split_bu_dwi(single_dwi_file_new)
    # Split the bvals and bvecs files into two files (one for each phase encoding direction)
    bvals_file_AP, bvals_file_PA, bvecs_file_AP, bvecs_file_PA = split_bu_bval_bvec(single_dwi_file_new)
    # Create json file for the new PA dwi file and edit the PhaseEncodingDirection field
    single_dwi_json_file_AP = os.path.join(os.path.dirname(single_dwi_file_PA), f'sub-{vetsaid}_ses-02_acq-single_dir-AP_dwi.json')
    single_dwi_json_file_PA = os.path.join(os.path.dirname(single_dwi_file_PA), f'sub-{vetsaid}_ses-02_acq-single_dir-PA_dwi.json')
    shutil.copy(single_dwi_json_file_AP, single_dwi_json_file_PA)
    with open(single_dwi_json_file_PA, 'r') as f:
        single_dwi_json = json.load(f)
    single_dwi_json["PhaseEncodingDirection"] = "j"
    with open(single_dwi_json_file_PA, 'w') as f:
        json.dump(single_dwi_json, f, indent=4)
    # Edit the json file for the PA epi file to include the correct IntendedFor field
    single_epi_pa_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'fmap', f'sub-{vetsaid}_ses-02_acq-single_dir-PA_epi.json')
    with open(single_epi_pa_json, 'r') as f:
        single_epi_pa_json_dict = json.load(f)
    single_epi_pa_json_dict["IntendedFor"] = f"bids::sub-{vetsaid}/ses-02/dwi/sub-{vetsaid}_ses-02_acq-single_dir-PA_dwi.nii.gz"
    with open(single_epi_pa_json, 'w') as f:
        json.dump(single_epi_pa_json_dict, f, indent=4)



def process_single_shell_data_UCSD(vetsaid, bids_dir):
    """
    Process the single-shell data. This includes:
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
    single_dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-AP_dwi.nii.gz')
    single_dwi_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-PA_dwi.nii.gz')
    shutil.move(single_dwi_file, single_dwi_file_new)
    # Check if the dwi file has the correct number of volumes
    if not check_dwi_nvols(single_dwi_file_new, 53):
        print(f'Error: Incorrect number of volumes in dwi file for subject {vetsaid}')
        return    
    # Rename dwi json file
    single_dwi_json_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-AP_dwi.json')
    single_dwi_json_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-PA_dwi.json')
    shutil.move(single_dwi_json_file, single_dwi_json_file_new)
    # Rename bvals and bvecs files
    bvals_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-AP_dwi.bval')
    bvecs_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-AP_dwi.bvec')
    bvals_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-PA_dwi.bval')
    bvecs_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'dwi', f'sub-{vetsaid}_ses-02_acq-single_dir-PA_dwi.bvec')
    shutil.move(bvals_file, bvals_file_new)
    shutil.move(bvecs_file, bvecs_file_new)
    # Split off the first two volumes as epi files
    fmap_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'fmap')
    os.makedirs(fmap_dir, exist_ok=True)
    single_epi_ap_file = os.path.join(fmap_dir, f'sub-{vetsaid}_ses-02_acq-single_dir-AP_epi.nii.gz')
    single_epi_pa_file = os.path.join(fmap_dir, f'sub-{vetsaid}_ses-02_acq-single_dir-PA_epi.nii.gz')
    single_dwi_file_new, single_epi_pa_file, single_epi_ap_file = split_epis(single_dwi_file_new, single_epi_pa_file, single_epi_ap_file)
    # Flip the phase encoding direction of the AP epi file
    single_epi_ap_file = flip_ap_epi(single_epi_ap_file)
    # Remove the first (1) value from the bvals file
    remove_first_n_values(bvals_file_new, 1)
    # Remove the first (1) value from the bvecs file
    remove_first_n_values(bvecs_file_new, 1)
    # Create json files for the epi files
    single_epi_ap_json, single_epi_pa_json = create_single_shell_epi_jsons(vetsaid, bids_dir)



def process_single_shell_data(vetsaid, bids_dir):
    """Process the single-shell data. The exact steps depend on the site of data collection, either BU or UCSD."""
    # Determine if dwi comes from BU or UCSD
    dwi_site = get_site(vetsaid, bids_dir)
    if dwi_site == "BU":
        process_single_shell_data_BU(vetsaid, bids_dir)
    elif dwi_site == "UCSD":
        process_single_shell_data_UCSD(vetsaid, bids_dir)
    else:
        print(f'Error in processing sub-{vetsaid}. Unknown dwi site: {dwi_site}')
        sys.exit(1)



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

        # Check if the single-shell data exists
        if check_single_shell_data(vetsaid, bids_dir):
            process_single_shell_data(vetsaid, bids_dir)

if __name__ == '__main__':
    
    # Check if the correct number of arguments was provided
    if len(sys.argv) != 3:
        print('Usage: python 3_wave2_correct_dwi_data.py <bids_dir> <subject_list_file>')
        sys.exit(1)

    # Get the path to the BIDS data and the subject list file from the command line arguments
    bids_dir = sys.argv[1]
    subject_list_file = sys.argv[2]

    # Run the main function
    main(bids_dir, subject_list_file)

